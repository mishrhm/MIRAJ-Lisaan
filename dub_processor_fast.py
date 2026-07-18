# dub_processor_fast.py
import asyncio
import io
import sys
import pysrt
from deep_translator import GoogleTranslator
import edge_tts
from pydub import AudioSegment

VOICE = "ml-IN-SobhanaNeural"
SOURCE_LANG = "ur"
TARGET_LANG = "ml"
MAX_CONCURRENT_TASKS = 15  # Adjust based on your network strength

def scale_audio_speed(sound, speed=1.0):
    if speed == 1.0:
        return sound
    return sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * speed)
    }).set_frame_rate(sound.frame_rate)

async def worker(queue, results_dict, semaphore, translator):
    """Worker task to process translation and TTS concurrently."""
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
            
        index, text, start_ms, allowed_window_ms = item
        
        async with semaphore:
            try:
                # 1. Network-bound Translation (Run in executor to keep loop free)
                loop = asyncio.get_running_loop()
                malayalam_text = await loop.run_in_executor(None, translator.translate, text)
                
                # 2. Network-bound Text-to-Speech
                communicate = edge_tts.Communicate(malayalam_text, VOICE)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                
                # 3. Store result payload in memory
                results_dict[index] = {
                    "audio_bytes": audio_data,
                    "start_ms": start_ms,
                    "allowed_window_ms": allowed_window_ms,
                    "text": malayalam_text
                }
                print(f"[✓] Processed chunk {index + 1}")
                
            except Exception as e:
                print(f"[!] Error on chunk {index + 1}: {e}", file=sys.stderr)
                
        queue.task_done()

async def generate_dubbed_track_fast(srt_path, output_mp3_path):
    print(f"[*] Reading subtitle file: {srt_path}")
    subs = pysrt.open(srt_path)
    translator = GoogleTranslator(source=SOURCE_LANG, target=TARGET_LANG)
    
    # Calculate master canvas limits
    last_sub = subs[-1]
    end_time_ms = ((last_sub.end.hours * 3600 + last_sub.end.minutes * 60 + last_sub.end.seconds) * 1000) + last_sub.end.milliseconds
    total_length_ms = end_time_ms + 5000
    
    queue = asyncio.Queue()
    results_dict = {}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    
    # Enqueue valid subtitle payloads
    valid_count = 0
    for index, sub in enumerate(subs):
        raw_text = sub.text.strip()
        if not raw_text:
            continue
        start_ms = (sub.start.hours * 3600 + sub.start.minutes * 60 + sub.start.seconds) * 1000 + sub.start.milliseconds
        end_ms = (sub.end.hours * 3600 + sub.end.minutes * 60 + sub.end.seconds) * 1000 + sub.end.milliseconds
        allowed_window_ms = end_ms - start_ms
        
        await queue.put((index, raw_text, start_ms, allowed_window_ms))
        valid_count += 1

    print(f"[*] Spawning worker pool to fetch {valid_count} chunks concurrently...")
    
    # Create worker consumers
    tasks = []
    for _ in range(MAX_CONCURRENT_TASKS):
        task = asyncio.create_task(worker(queue, results_dict, semaphore, translator))
        tasks.append(task)
        
    # Wait for queue to drain completely
    await queue.join()
    
    # Shutdown workers cleanly
    for _ in range(MAX_CONCURRENT_TASKS):
        await queue.put(None)
    await asyncio.gather(*tasks)

    # Compile-phase: Assemble everything sequentially on the audio canvas
    print(f"[*] Compiling master audio track in-memory...")
    master_track = AudioSegment.silent(duration=total_length_ms)
    
    for index in sorted(results_dict.keys()):
        res = results_dict[index]
        if not res["audio_bytes"]:
            continue
            
        # Read from raw memory buffer instead of disk storage
        audio_chunk = AudioSegment.from_file(io.BytesIO(res["audio_bytes"]), format="mp3")
        actual_duration_ms = len(audio_chunk)
        
        if actual_duration_ms > res["allowed_window_ms"] and res["allowed_window_ms"] > 0:
            target_speed = min(actual_duration_ms / res["allowed_window_ms"], 1.45)
            audio_chunk = scale_audio_speed(audio_chunk, target_speed)
            
        master_track = master_track.overlay(audio_chunk, position=res["start_ms"])

    print(f"[*] Saving master copy to: {output_mp3_path}")
    master_track.export(output_mp3_path, format="mp3")
    print("[✓] Process complete!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python dub_processor_fast.py <path_to_srt> <output_mp3_path>")
        sys.exit(1)
    asyncio.run(generate_dubbed_track_fast(sys.argv[1], sys.argv[2]))