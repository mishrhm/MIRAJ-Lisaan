# extract_final_prints.py
from pydub import AudioSegment
import os

os.makedirs("voice_prints_final", exist_ok=True)

print("[*] Loading primary audio track...")
audio = AudioSegment.from_wav("temp_analysis_audio.wav")

# Mapping the absolute longest, post-intro continuous blocks from your leaderboard
final_targets = {
    # 1051.97s to 1058.81s (6.8s)
    "SPEAKER_00": {"start": 1051970, "end": 1058810},
    
    # 2357.38s to 2363.49s (6.1s)
    "SPEAKER_01": {"start": 2357380, "end": 2363490},
    
    # 872.51s to 881.31s (8.8s) - Excellent length!
    "SPEAKER_02": {"start": 872510, "end": 881310},
    
    # 1194.34s to 1200.45s (6.1s)
    "SPEAKER_03": {"start": 1194340, "end": 1200450},
    
    # 385.51s to 387.52s (2.0s)
    "SPEAKER_04": {"start": 385510, "end": 387520}
}

print("[*] Extracting peak dialogue footprints...")

for speaker, timing in final_targets.items():
    clip = audio[timing["start"]:timing["end"]]
    out_path = f"voice_prints_final/{speaker}_raw.wav"
    clip.export(out_path, format="wav")
    duration = (timing["end"] - timing["start"]) / 1000
    print(f"[✓] Exported {speaker} ({duration:.1f}s from deep timeline)")

print("\n[✓] All reference prints saved! Check your 'voice_prints_final/' directory.")