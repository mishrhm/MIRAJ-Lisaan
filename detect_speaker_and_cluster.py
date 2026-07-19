import os
import gc
import torch
import numpy as np
import soundfile as sf
from resemblyzer import VoiceEncoder, preprocess_wav
from sklearn.cluster import SpectralClustering

# Silero VAD → Detect where speech happens
# Resemblyzer → Cluster speakers based on voice similarity

def extract_character_timelines(video_audio_path, num_speakers=2):
    print("[*] Loading Silero VAD (Speech Detection)...")
    # Load Silero VAD model natively from Torch Hub (lightweight)
    vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      force_reload=False,
                                      trust_repo=True)
    get_speech_timestamps, _, read_audio, _, _ = utils
    
    # Read audio array
    audio = read_audio(video_audio_path, sampling_rate=16000)
    
    # 1. Get exact speech windows
    print("[*] Scanning audio for human speech...")
    speech_timestamps = get_speech_timestamps(audio, vad_model, sampling_rate=16000)
    
    # Unload VAD immediately to preserve unified RAM
    del vad_model
    gc.collect()
    
    # 2. Extract Speaker Embeddings with Resemblyzer
    print("[*] Initializing Resemblyzer (Voice Print Encoder)...")
    encoder = VoiceEncoder("cpu") # Exceptionally fast even on CPU
    
    embeddings = []
    valid_segments = []
    
    # Reload original file for raw segment slicing
    wav = preprocess_wav(video_audio_path)
    sr = 16000
    
    for idx, ts in enumerate(speech_timestamps):
        start_idx = int(ts['start'])
        end_idx = int(ts['end'])
        
        # Resemblyzer needs at least ~0.5s of audio to create a stable voice print
        if (end_idx - start_idx) < (sr * 0.5):
            continue
            
        segment = wav[start_idx:end_idx]
        embed = encoder.embed_utterance(segment)
        embeddings.append(embed)
        valid_segments.append({
            "start_ms": int((start_idx / sr) * 1000),
            "end_ms": int((end_idx / sr) * 1000)
        })
        
    # Unload Encoder
    del encoder
    gc.collect()
    
    # 3. Cluster Embeddings to Separate Characters
    print(f"[*] Clustering voice signatures into {num_speakers} distinct characters...")
    clustering = SpectralClustering(n_clusters=num_speakers, affinity="cosine", random_state=42)
    labels = clustering.fit_predict(np.array(embeddings))
    
    # 4. Map labels back to timelines
    timeline = []
    for i, seg in enumerate(valid_segments):
        timeline.append({
            "start_ms": seg["start_ms"],
            "end_ms": seg["end_ms"],
            "speaker_id": f"SPEAKER_{labels[i]:02d}"
        })
        
    print(f"[✓] Successfully categorized speech into {num_speakers} active roles.")
    return timeline
    
if __name__ == "__main__":
    import subprocess
    import sys
    
    video_file = "raw_video.mp4"
    audio_wav = "temp_analysis_audio.wav"
    
    print("\n=== Initializing Multi-Speaker Diarization Test ===")
    
    # 1. Extract audio if it doesn't exist yet
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", video_file, 
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_wav
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("[!] FFmpeg extraction failed.")
        sys.exit(1)
        
    # 2. Run clustering with an expanded cast size
    # CHANGE: Swapped num_speakers to 5 to capture the wider ensemble cast. 
    # (Tip: Remove 'num_speakers=5' entirely if you want the AI to guess the total count automatically)
    timeline = extract_character_timelines(audio_wav, num_speakers=5)
    
    # 3. Print a larger breakdown from minute 5 onwards to find clean dialogue zones
    print("\n=== Global Cast Timeline Map (Full Episode Scan) ===")
    
    # Group and analyze the longest segments across the entire video
    speaker_blocks = {f"SPEAKER_{i:02d}": [] for i in range(5)}
    
    for entry in timeline:
        start_sec = entry["start_ms"] / 1000
        end_sec = entry["end_ms"] / 1000
        duration = end_sec - start_sec
        speaker = entry['speaker_id']
        
        if speaker in speaker_blocks:
            speaker_blocks[speaker].append({
                "start": start_sec,
                "end": end_sec,
                "duration": duration
            })
            
    # Print the top 5 longest continuous lines for EACH character
    for speaker, blocks in speaker_blocks.items():
        print(f"\n--- Top Longest Blocks for {speaker} ---")
        # Sort by duration descending
        sorted_blocks = sorted(blocks, key=lambda x: x["duration"], reverse=True)
        
        if not sorted_blocks:
            print("No blocks detected for this speaker.")
            continue
            
        for idx, block in enumerate(sorted_blocks[:5]):
            print(f"[{idx+1}] {block['start']:>7.2f}s - {block['end']:>7.2f}s ({block['duration']:.1f}s)")