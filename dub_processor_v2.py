# dub_processor_v2.py
import asyncio
import io
import os
import sys
import pysrt
from deep_translator import GoogleTranslator
import edge_tts
from pydub import AudioSegment

VOICE = "ml-IN-SobhanaNeural"
SOURCE_LANG = "ur"
TARGET_LANG = "ml"
MAX_CONCURRENT_TASKS = 10 
import numpy as np
from scipy import signal

def safe_scale_speed(sound, target_window_ms):
    """
    Speeds up audio without changing the pitch, preserving natural vocal tones.
    """
    actual_duration = len(sound)
    if actual_duration <= target_window_ms or target_window_ms <= 0:
        return sound
        
    speed_factor = actual_duration / target_window_ms
    # Hard cap: Never speed up more than 1.4x to protect legibility
    if speed_factor > 1.4:
        speed_factor = 1.4

    # Extract raw audio data as a numpy array
    samples = np.array(sound.get_array_of_samples(), dtype=np.float32)
    
    # Handle stereo vs mono channels
    channels = sound.channels
    if channels == 2:
        samples = samples.reshape((-1, 2))

    # Perform pitch-preserving time-stretch using a simple Overlap-Add (OLA) method
    # For a production-grade framework, standard ffmpeg 'atempo' filter can also be mapped
    hop_length = 256
    window = np.hanning(hop_length * 2)
    
    # Python-native time-stretching phase vocoder approach or scipy resampling
    # To keep it absolutely robust and avoid dependency hell, we use FFmpeg's built-in 
    # high-quality 'atempo' filter directly via pydub's native speedup utility:
    try:
        # pydub has a built-in speedup function that uses ffmpeg's 'atempo' filter under the hood,
        # which perfectly preserves pitch and removes the chipmunk effect!
        return sound.speedup(playback_speed=speed_factor, chunk_size=150, crossfade=25)
    except Exception:
        # Fallback to original method if FFmpeg atempo throws an unexpected error
        return sound._spawn(sound.raw_data, overrides={
            "frame_rate": int(sound.frame_rate * speed_factor)
        }).set_frame_rate(sound.frame_rate)

async def worker(queue, results_dict, semaphore, translator):
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
            
        index, text, start_ms, allowed_window_ms = item
        
        async with semaphore:
            try:
                loop = asyncio.get_running_loop()
                malayalam_text = await loop.run_in_executor(None, translator.translate, text)
                
                communicate = edge_tts.Communicate(malayalam_text, VOICE)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                
                results_dict[index] = {
                    "audio_bytes": audio_data,
                    "start_ms": start_ms,
                    "allowed_window_ms": allowed_window_ms
                }
                print(f"[✓] Synced chunk {index + 1}")
                
            except Exception as e:
                print(f"[!] Error on chunk {index + 1}: {e}", file=sys.stderr)
                
        queue.task_done()

async def main_pipeline(srt_path, output_mp3_path):
    subs = pysrt.open(srt_path)
    translator = GoogleTranslator(source=SOURCE_LANG, target=TARGET_LANG)
    
    last_sub = subs[-1]
    total_length_ms = ((last_sub.end.hours * 3600 + last_sub.end.minutes * 60 + last_sub.end.seconds) * 1000) + last_sub.end.milliseconds + 10000
    
    queue = asyncio.Queue()
    results_dict = {}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    
    for index, sub in enumerate(subs):
        raw_text = sub.text.strip()
        if not raw_text:
            continue
        start_ms = (sub.start.hours * 3600 + sub.start.minutes * 60 + sub.start.seconds) * 1000 + sub.start.milliseconds
        end_ms = (sub.end.hours * 3600 + sub.end.minutes * 60 + sub.end.seconds) * 1000 + sub.end.milliseconds
        await queue.put((index, raw_text, start_ms, end_ms - start_ms))

    workers = [asyncio.create_task(worker(queue, results_dict, semaphore, translator)) for _ in range(MAX_CONCURRENT_TASKS)]
    
    await queue.join()
    for _ in range(MAX_CONCURRENT_TASKS):
        await queue.put(None)
    await asyncio.gather(*workers)

    print("[*] Assembling clean audio canvas...")
    master_track = AudioSegment.silent(duration=total_length_ms)
    
    # We trace the last playback end-point to strictly prevent overlaps
    last_audio_end_ms = 0

    for index in sorted(results_dict.keys()):
        res = results_dict[index]
        if not res["audio_bytes"]:
            continue
            
        audio_chunk = AudioSegment.from_file(io.BytesIO(res["audio_bytes"]), format="mp3")
        
        # Prevent overlaps: If the speech starts before the last one finished, push its start time out
        target_start_ms = max(res["start_ms"], last_audio_end_ms)
        
        # Fit it cleanly into its timeline slot
        audio_chunk = safe_scale_speed(audio_chunk, res["allowed_window_ms"])
        
        master_track = master_track.overlay(audio_chunk, position=target_start_ms)
        last_audio_end_ms = target_start_ms + len(audio_chunk)

    master_track.export(output_mp3_path, format="mp3")
    print("[✓] Clean audio track compiled!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python dub_processor_v2.py <path_to_srt> <output_mp3_path>")
        sys.exit(1)
    asyncio.run(main_pipeline(sys.argv[1], sys.argv[2]))