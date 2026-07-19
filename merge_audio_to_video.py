# merge_audio_to_video.py
import os
import ffmpeg

def merge_dub_to_video(video_in, audio_in, video_out):
    print("[*] Merging Malayalam master track with the original video...")
    
    if not os.path.exists(video_in):
        print(f"[!] Error: Original video file '{video_in}' not found.")
        return
    if not os.path.exists(audio_in):
        print(f"[!] Error: Audio track '{audio_in}' not found. Run the stitch script first.")
        return

    try:
        # Stream specifiers: take video from input 0, take audio from input 1
        input_video = ffmpeg.input(video_in)
        input_audio = ffmpeg.input(audio_in)
        
        # Output configuration: copy video codec directly, mux with new audio
        stream = ffmpeg.output(
            input_video['v'], 
            input_audio['a'], 
            video_out, 
            vcodec='copy', 
            acodec='aac'
        )
        
        # Run the command silently unless there's an error
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
        print(f"[✓] Success! Final dubbed video saved as: {video_out}")
        
    except ffmpeg.Error as e:
        print(f"[!] FFmpeg error encountered: {e.stderr.decode('utf8')}")

if __name__ == "__main__":
    # Change these names to match your actual filenames
    ORIGINAL_VIDEO = "raw_video.mp4" 
    AUDIO_TRACK = "final_malayalam_dub_track.wav"
    OUTPUT_VIDEO = "final_dubbed_video.mp4"
    
    merge_dub_to_video(ORIGINAL_VIDEO, AUDIO_TRACK, OUTPUT_VIDEO)