# run_final_dub.py
import os
import sys

# FIX 1: Prevent the macOS config_init_hash_seed multiprocessing crash
os.environ["PYTHONHASHSEED"] = "0"

import soundfile as sf
import pysrt
from f5_tts.api import F5TTS

# Force Apple Silicon GPU acceleration
DEVICE = "mps"

# Your VAD timeline matrix mapping active speakers
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

def main():
    print("[*] Initializing F5-TTS Base Model on Apple Silicon GPU...")
    try:
        f5_engine = F5TTS(device=DEVICE)
    except Exception as e:
        print(f"[!] MPS initialization failed: {e}. Trying CPU fallback...")
        f5_engine = F5TTS(device="cpu")
    
    print("[*] Loading character voice prints...")
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
            
    missing_txt = [k for k, v in cast_profiles.items() if not v["text"]]
    if missing_txt:
        print(f"[!] Warning: Missing transcript files for: {missing_txt}.")
        sys.exit(1)

    srt_path = "episode_subs.en.srt"
    if not os.path.exists(srt_path):
        print(f"[!] Subtitle file '{srt_path}' not found.")
        sys.exit(1)
        
    subs = pysrt.open(srt_path)
    os.makedirs("dubbed_segments", exist_ok=True)
    
    print(f"\n[*] Starting multi-speaker dubbing pipeline for {len(subs)} lines...")
    
    for idx, sub in enumerate(subs):
        start_ms = (sub.start.hours * 3600 + sub.start.minutes * 60 + sub.start.seconds) * 1000 + sub.start.milliseconds
        current_speaker = get_speaker_at_time(start_ms, TIMELINE_DATA)
        
        # Placeholder for translation integration
        malayalam_text = "ഇവിടെ നിങ്ങളുടെ വിവർത്തനം ചെയ്ത വാചകം വരും." 
        
        profile = cast_profiles.get(current_speaker)
        if not profile:
            fallback_key = list(cast_profiles.keys())[0]
            profile = cast_profiles[fallback_key]
            current_speaker = fallback_key
        
        print(f"[{idx+1}/{len(subs)}] Generation line for {current_speaker}...")
        
        # FIX 2: Added `*_` variable unpacking to elegantly catch the returned spectrogram data 
        # and prevent the ValueError crash
        audio_data, sample_rate, *_ = f5_engine.infer(
            ref_file=profile["audio"],
            ref_text=profile["text"],
            gen_text=malayalam_text,
            nfe_step=32
        )
        
        out_filename = f"dubbed_segments/line_{idx:04d}_{current_speaker}.wav"
        sf.write(out_filename, audio_data, sample_rate)
        
    print("\n[✓] All dialogue assets generated successfully inside 'dubbed_segments/'!")

if __name__ == "__main__":
    main()