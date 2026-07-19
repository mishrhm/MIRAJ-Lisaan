# unified_dub_pipeline_v3.py
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

def main():
    # 3. INITIALIZE TRANSLATOR AND F5-TTS
    print("[*] Setting up translation engine (English -> Malayalam)...")
    translator = GoogleTranslator(source="en", target="ml")

    print("[*] Initializing F5-TTS Base Model on Apple Silicon GPU...")
    try:
        f5_engine = F5TTS(device=DEVICE)
    except Exception as e:
        print(f"[!] MPS initialization failed: {e}. Trying CPU fallback...")
        f5_engine = F5TTS(device="cpu")
    
    # 4. CACHE CHARACTER VOICE PRINTS IN MEMORY
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
    
    # 5. GENERATION LOOP
    print(f"\n[*] Step 1: Translating and generating {len(subs)} dialogue assets...")
    for idx, sub in enumerate(subs):
        raw_text = sub.text.strip()
        if not raw_text:
            continue

        start_ms = get_srt_start_ms(sub)
        current_speaker = get_speaker_at_time(start_ms, TIMELINE_DATA)
        
        # FIX: Translate the actual text from the SRT file instead of using a placeholder string
        try:
            malayalam_text = translator.translate(raw_text)
        except Exception as e:
            print(f"[!] Translation failed for line {idx+1}: {e}. Skipping fallback.")
            malayalam_text = raw_text 

        profile = cast_profiles.get(current_speaker)
        if not profile:
            fallback_key = list(cast_profiles.keys())[0]
            profile = cast_profiles[fallback_key]
            current_speaker = fallback_key
        
        print(f"    [{idx+1}/{len(subs)}] Rendering {current_speaker} | Text: {malayalam_text[:30]}...")
        
        with torch.inference_mode():
            audio_data, sample_rate, *_ = f5_engine.infer(
                ref_file=profile["audio"],
                ref_text=profile["text"],
                gen_text=malayalam_text,
                nfe_step=32
            )
        
        out_filename = f"{SEGMENTS_DIR}/line_{idx:04d}_{current_speaker}.wav"
        sf.write(out_filename, audio_data, sample_rate)
        
        if DEVICE == "mps":
            torch.mps.empty_cache()

    print("[✓] Step 1 Complete: All real translated dialogue blocks saved.")

    # 6. STITCHING AND TIMELINE ALIGNMENT
    print(f"\n[*] Step 2: Stitching chunks onto video timeline track...")
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