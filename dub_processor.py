# dub_processor.py
import asyncio
import os
import sys
import pysrt
from deep_translator import GoogleTranslator
import edge_tts
from pydub import AudioSegment

VOICE = "ml-IN-SobhanaNeural"  # Highest-quality Malayalam profile available via Edge
SOURCE_LANG = "ur"
TARGET_LANG = "ml"

def scale_audio_speed(sound, speed=1.0):
    """Adjusts speech rate of an AudioSegment without altering pitch."""
    if speed == 1.0:
        return sound
    return sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * speed)
    }).set_frame_rate(sound.frame_rate)

async def generate_dubbed_track(srt_path, output_mp3_path):
    print(f"[*] Reading subtitle file: {srt_path}")
    subs = pysrt.open(srt_path)
    translator = GoogleTranslator(source=SOURCE_LANG, target=TARGET_LANG)
    
    # Check the absolute final timestamp to size our master canvas correctly
    last_sub = subs[-1]
    end_time_ms = ((last_sub.end.hours * 3600 + last_sub.end.minutes * 60 + last_sub.end.seconds) * 1000) + last_sub.end.milliseconds
    total_length_ms = end_time_ms + 5000  # 5-second structural buffer
    
    print(f"[*] Initializing silent audio timeline ({total_length_ms / 1000 / 60:.2f} minutes)...")
    master_track = AudioSegment.silent(duration=total_length_ms)

    print("[*] Beginning translation and voice synthesis pipeline...")
    for index, sub in enumerate(subs):
        raw_text = sub.text.strip()
        if not raw_text:
            continue
            
        # Parse frame timestamps
        start_ms = (sub.start.hours * 3600 + sub.start.minutes * 60 + sub.start.seconds) * 1000 + sub.start.milliseconds
        end_ms = (sub.end.hours * 3600 + sub.end.minutes * 60 + sub.end.seconds) * 1000 + sub.end.milliseconds
        allowed_window_ms = end_ms - start_ms

        try:
            # 1. Translate string
            malayalam_text = translator.translate(raw_text)
            print(f"[{index + 1}/{len(subs)}] Syncing timeline frame: {malayalam_text}")

            # 2. Compile chunk to temporary file
            temp_chunk_path = f"chunk_{index}.mp3"
            communicate = edge_tts.Communicate(malayalam_text, VOICE)
            await communicate.save(temp_chunk_path)

            # 3. Read generated chunk metrics
            audio_chunk = AudioSegment.from_mp3(temp_chunk_path)
            actual_duration_ms = len(audio_chunk)

            # 4. Fit text-to-speech to character timeline windows
            if actual_duration_ms > allowed_window_ms and allowed_window_ms > 0:
                needed_speed_factor = actual_duration_ms / allowed_window_ms
                # Cap speech modifications to 1.45x so it remains perfectly legible to ears
                target_speed = min(needed_speed_factor, 1.45)
                audio_chunk = scale_audio_speed(audio_chunk, target_speed)

            # 5. Paste chunk onto master track
            master_track = master_track.overlay(audio_chunk, position=start_ms)
            
            # Disk cleanup
            os.remove(temp_chunk_path)

        except Exception as e:
            print(f"[!] Error handling index {index}: {e}", file=sys.stderr)
            if os.path.exists(f"chunk_{index}.mp3"):
                os.remove(f"chunk_{index}.mp3")

    print(f"[*] Exporting complete voice track to: {output_mp3_path}")
    master_track.export(output_mp3_path, format="mp3")
    print("[✓] Process complete. Audio generated successfully.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python dub_processor.py <path_to_srt> <output_mp3_path>")
        sys.exit(1)
        
    asyncio.run(generate_dubbed_track(sys.argv[1], sys.argv[2]))
    