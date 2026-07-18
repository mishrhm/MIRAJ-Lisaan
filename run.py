# run_pipeline.py
import sys
import os
import subprocess
from downloader import download_assets
import asyncio
from dub_processor_v2 import main_pipeline

def run_ffmpeg_convert():
    """Converts the downloaded VTT subtitle file into an SRT format."""
    print("[*] Step 2: Converting WebVTT subtitles to SubRip (SRT)...")
    vtt_file = "raw_video.en.vtt"
    srt_file = "episode_subs.en.srt"
    
    if not os.path.exists(vtt_file):
        print(f"[!] Error: Expected subtitle file '{vtt_file}' not found.")
        sys.exit(1)
        
    cmd = ["ffmpeg", "-y", "-i", vtt_file, srt_file]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[✓] Subtitles successfully formatted to SRT.")
        return srt_file
    except subprocess.CalledProcessError as e:
        print(f"[!] FFmpeg subtitle conversion failed: {e}")
        sys.exit(1)

def run_ffmpeg_mux(video_input, audio_input, output_file):
    """Muxes the generated audio track back into the video with auto-ducking."""
    print("[*] Step 4: Structuring final media mix and applying audio ducking...")
    
    if not os.path.exists(video_input) or not os.path.exists(audio_input):
        print("[!] Error: Missing media components for final muxing.")
        sys.exit(1)
        
    cmd = [
        "ffmpeg", "-y", 
        "-i", video_input, 
        "-i", audio_input,
        "-filter_complex", "[0:a]volume=0.15[bg_ducked]; [bg_ducked][1:a]amix=inputs=2:duration=first[mixed_audio]",
        "-map", "0:v", 
        "-map", "[mixed_audio]", 
        "-c:v", "copy", 
        "-c:a", "aac", 
        output_file
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\n[✓] PIPELINE COMPLETE! Final screening video saved to: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"[!] Final media muxing failed: {e}")
        sys.exit(1)

async def execution_coordinator(youtube_url, final_output_name):
    print("=== MIRAJ-Lisaan 🎙️ Pipeline Initialization ===")
    
    # Step 1: Scrape Assets
    download_assets(youtube_url)
    
    # Step 2: Format Subtitles
    srt_path = run_ffmpeg_convert()
    
    # Step 3: Synthesize Speech Timeline
    print("[*] Step 3: Translating and synthesizing pitch-preserved Malayalam speech tracks...")
    intermediate_audio = "output_malayalam.mp3"
    await main_pipeline(srt_path, intermediate_audio)
    
    # Step 4: Final Media Muxing
    run_ffmpeg_mux("raw_video.mp4", intermediate_audio, final_output_name)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <YOUTUBE_URL> [OUTPUT_FILENAME.mp4]")
        sys.exit(1)
        
    url = sys.argv[1]
    output_name = sys.argv[2] if len(sys.argv) > 2 else "final_desktop_screening.mp4"
    
    # Execute the asynchronous orchestrator loop
    asyncio.run(execution_coordinator(url, output_name))