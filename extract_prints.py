# extract_prints.py
from pydub import AudioSegment
import os

# Create a folder to hold the character voice profiles
os.makedirs("voice_prints", exist_ok=True)
audio = AudioSegment.from_wav("temp_analysis_audio.wav")

# Based on your logs, let's extract a clean chunk for each speaker
# SPEAKER_00 talks cleanly around 39.07s
speaker_00_clip = audio[39070:39650]
speaker_00_clip.export("voice_prints/SPEAKER_00_raw.wav", format="wav")

# SPEAKER_01 talks cleanly around 20.55s
speaker_01_clip = audio[20550:23070]
speaker_01_clip.export("voice_prints/SPEAKER_01_raw.wav", format="wav")

print("[✓] Extracted samples to the 'voice_prints' directory! Check them out.")