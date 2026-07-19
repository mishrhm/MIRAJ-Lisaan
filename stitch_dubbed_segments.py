import os
import pysrt
from pydub import AudioSegment

def get_srt_start_ms(sub):
    """Converts an SRT subtitle timestamp into absolute milliseconds."""
    return (sub.start.hours * 3600 + 
            sub.start.minutes * 60 + 
            sub.start.seconds) * 1000 + sub.start.milliseconds

def stitch_audio_segments(srt_path, segments_dir, output_path):
    print(10 * "-" + " STITCHING PIPELINE " + 10 * "-")
    
    if not os.path.exists(srt_path):
        print(f"[!] Error: Subtitle file '{srt_path}' not found.")
        return
        
    subs = pysrt.open(srt_path)
    
    # Initialize an empty, silent base audio track
    # We start with 0ms and dynamically grow it as we place segments
    master_timeline = AudioSegment.silent(duration=0)
    
    print(f"[*] Processing {len(subs)} segments from '{segments_dir}'...")
    
    for idx, sub in enumerate(subs):
        start_ms = get_srt_start_ms(sub)
        
        # Hunt down the specific file for this index block
        # Looks for files formatted like: line_0000_SPEAKER_00.wav
        matching_files = [f for f in os.listdir(segments_dir) if f.startswith(f"line_{idx:04d}_")]
        
        if not matching_files:
            print(f"[!] Warning: Missing audio chunk for line {idx:04d}. Skipping.")
            continue
            
        segment_file = os.path.join(segments_dir, matching_files[0])
        segment_audio = AudioSegment.from_wav(segment_file)
        
        # If our master timeline is shorter than the starting mark of the current line,
        # we append a calculated chunk of perfect digital silence to pad the gap.
        if len(master_timeline) < start_ms:
            silence_gap = start_ms - len(master_timeline)
            master_timeline += AudioSegment.silent(duration=silence_gap)
            
        # Overlay the generated audio segment onto the timeline at the precise timestamp.
        # gain_during_overlay=0 ensures the clip volume isn't altered during the merge.
        master_timeline = master_timeline.overlay(segment_audio, position=start_ms, gain_during_overlay=0)
    
    # Export the final master track
    print(f"[*] Exporting complete timeline to '{output_path}'...")
    master_timeline.export(output_path, format="wav")
    print(f"[✓] Success! Final master track duration: {len(master_timeline) / 1000:.2f} seconds.")

if __name__ == "__main__":
    SRT_FILE = "episode_subs.en.srt"
    SEGMENTS_DIR = "dubbed_segments"
    OUTPUT_FILE = "final_malayalam_dub_track.wav"
    
    stitch_audio_segments(SRT_FILE, SEGMENTS_DIR, OUTPUT_FILE)