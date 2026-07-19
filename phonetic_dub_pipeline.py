import os
import sys

# 1. ENVIRONMENT SETUP (Fixes macOS Apple Silicon background worker crash)
os.environ["PYTHONHASHSEED"] = str(0)

import torch
import soundfile as sf
import pysrt
from pydub import AudioSegment
from f5_tts.api import F5TTS
from deep_translator import GoogleTranslator
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Force Apple Silicon GPU acceleration
DEVICE = "mps"

if __name__ == "__main__":
    try:
        import multiprocessing
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

# 2. CONFIGURATION & DIALOGUE TIMELINE DATA
SRT_FILE = "episode_subs.en.srt"
SEGMENTS_DIR = "dubbed_segments"
OUTPUT_MASTER_TRACK = "final_malayalam_dub_track.wav"

TIMELINE_DATA = [
    {"start_ms": 17730, "end_ms": 18750, "speaker_id": "SPEAKER_04"},
    {"start_ms": 19300, "end_ms": 20090, "speaker_id": "SPEAKER_04"},
    {"start_ms": 20550, "end_ms": 23070, "speaker_id": "SPEAKER_00"},
    {"start_ms": 23620, "end_ms": 25180, "speaker_id": "SPEAKER_00"},
    {"start_ms": 28420, "end_ms": 30210, "speaker_id": "SPEAKER_00"},
    {"start_ms": 39070, "end_ms": 39650, "speaker_id": "SPEAKER_04"},
    {"start_ms": 53310, "end_ms": 55680, "speaker_id": "SPEAKER_02"},
    {"start_ms": 55970, "end_ms": 56700, "speaker_id": "SPEAKER_04"},
    {"start_ms": 56800, "end_ms": 58880, "speaker_id": "SPEAKER_00"},
    {"start_ms": 59140, "end_ms": 64220, "speaker_id": "SPEAKER_00"},
]

def load_transcript(txt_path):
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def get_speaker_at_time(start_ms, timeline_data):
    for entry in timeline_data:
        if entry["start_ms"] - 200 <= start_ms <= entry["end_ms"] + 200:
            return entry["speaker_id"]
    return "SPEAKER_00"

def get_srt_start_ms(sub):
    return (sub.start.hours * 3600 + 
            sub.start.minutes * 60 + 
            sub.start.seconds) * 1000 + sub.start.milliseconds

def clean_romanized_text(text):
    """Cleans up formal scientific transliteration markers into flat english letters."""
    replacements = {
        'ā': 'a', 'ī': 'i', 'ū': 'u', 'ṛ': 'r', 'e̅': 'e', 'o̅': 'o',
        'ṅ': 'n', 'ñ': 'n', 'ṭ': 't', 'ḍ': 'd', 'ṇ': 'n', 't̪': 't',
        'd̪': 'd', 'n̪': 'n', 'ḷ': 'l', 'ḻ': 'l', 'ṟ': 'r', 'ṃ': 'm', 'ḥ': 'h'
    }
    for special, flat in replacements.items():
        text = text.replace(special, flat)
        text = text.replace(special.upper(), flat.upper())
    return text

def main():
    # 3. INITIALIZE PIPELINES
    print("[*] Connecting to translation engine (English -> Malayalam)...")
    translator = GoogleTranslator(source="en", target="ml")

    print("[*] Initializing F5-TTS Engine on Apple Silicon GPU...")
    try:
        f5_engine = F5TTS(device=DEVICE)
    except Exception as e:
        print(f"[!] MPS initialization failed: {e}. Falling back to CPU...")
        f5_engine = F5TTS(device="cpu")
    
    # 4. CACHE CHARACTER VOICE PRINTS
    print("[*] Loading character voice prints into cache...")
    cast_profiles = {}
    for i in range(5):
        spk_id = f"SPEAKER_{i:02d}"
        ref_audio = f"voice_prints_final/{spk_id}_raw.wav"
        ref_txt_path = f"voice_prints_final/{spk_id}_transcript.txt"
        
        if os.path.exists(ref_audio):
            cast_profiles[spk_id] = {
                "audio": ref_audio,
                "text": load_transcript(ref_txt_path)
            }
            
    if not cast_profiles:
        print("[!] Error: No voice profiles found in 'voice_prints_final/'.")
        sys.exit(1)

    if not os.path.exists(SRT_FILE):
        print(f"[!] Subtitle file '{SRT_FILE}' not found.")
        sys.exit(1)
        
    subs = pysrt.open(SRT_FILE)
    os.makedirs(SEGMENTS_DIR, exist_ok=True)
    
    # 5. TRANSLATE, ROMANIZE, AND GENERATE AUDIO LOOP
    print(f"\n[*] Step 1: Processing {len(subs)} lines...")
    for idx, sub in enumerate(subs):
        raw_text = sub.text.strip()
        if not raw_text:
            continue

        start_ms = get_srt_start_ms(sub)
        current_speaker = get_speaker_at_time(start_ms, TIMELINE_DATA)
        
        # A. Get Malayalam translation
        try:
            malayalam_text = translator.translate(raw_text)
        except Exception as e:
            print(f"[!] Translation failed for line {idx+1}: {e}")
            continue

        # B. Transliterate Malayalam Script to Romanized Script
        romanized_raw = transliterate(malayalam_text, sanscript.MALAYALAM, sanscript.ITRANS)
        romanized_text = clean_romanized_text(romanized_raw.lower())

        profile = cast_profiles.get(current_speaker)
        if not profile:
            fallback_key = list(cast_profiles.keys())[0]
            profile = cast_profiles[fallback_key]
            current_speaker = fallback_key
        
        print(f"    [{idx+1}/{len(subs)}] Cloned {current_speaker} -> Text: \"{romanized_text[:40]}...\"")
        
        with torch.inference_mode():
            audio_data, sample_rate, *_ = f5_engine.infer(
                ref_file=profile["audio"],
                ref_text=profile["text"],
                gen_text=romanized_text, # Valid Latin text tokens for F5 vocabulary
                nfe_step=32
            )
        
        out_filename = f"{SEGMENTS_DIR}/line_{idx:04d}_{current_speaker}.wav"
        sf.write(out_filename, audio_data, sample_rate)
        
        if DEVICE == "mps":
            torch.mps.empty_cache()

    print("[✓] Step 1 Complete: All phonetic voice models generated.")

    # 6. STITCHING AND TIMELINE ALIGNMENT
    print(f"\n[*] Step 2: Stitching chunks onto timeline track...")
    master_timeline = AudioSegment.silent(duration=0)
    
    for idx, sub in enumerate(subs):
        start_ms = get_srt_start_ms(sub)
        matching_files = [f for f in os.listdir(SEGMENTS_DIR) if f.startswith(f"line_{idx:04d}_")]
        
        if not matching_files:
            continue
            
        segment_file = os.path.join(SEGMENTS_DIR, matching_files[0])
        segment_audio = AudioSegment.from_wav(segment_file)
        
        if len(master_timeline) < start_ms:
            silence_gap = start_ms - len(master_timeline)
            master_timeline += AudioSegment.silent(duration=silence_gap)
            
        master_timeline = master_timeline.overlay(segment_audio, position=start_ms, gain_during_overlay=0)
    
    print(f"[*] Exporting complete master timeline to '{OUTPUT_MASTER_TRACK}'...")
    master_timeline.export(OUTPUT_MASTER_TRACK, format="wav")
    print(f"[✓] Pipeline complete! Track length: {len(master_timeline) / 1000:.2f} seconds.")

if __name__ == "__main__":
    main()