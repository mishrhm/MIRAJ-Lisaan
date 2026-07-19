# MIRAJ-Lisaan 🎙️ (Project Post-Mortem & Archive)

An open-source automation pipeline designed to translate and dynamically dub Urdu YouTube videos (such as Pakistani Serials) into Malayalam speech tracks using neural text-to-speech engine workflows.

Built to help family members enjoy content seamlessly on desktop platforms with natural localized voiceovers.

> ⚠️ **Project Status: Archived / Completed Post-Mortem**  
> This repository represents a complete engineering journey exploring automated local video dubbing. While the single-voice concurrent pipeline was successfully achieved, the advanced phase of multi-character deep voice-cloning proved unfeasible on localized consumer-grade hardware (M2 MacBook Air). This README serves as a documentation of our technical triumphs, architectural realizations, and the fundamental limitations that led to halting further development[cite: 10].

---

## 📜 The Journey: Retrospective & Engineering Realizations

### 🟢 What Worked (The Triumphs)

- **Concurrency & In-Memory Processing:** Our initial pipeline took **over an hour** to process a single 40-minute episode due to sequential disk I/O and network blocks[cite: 9]. By rewriting the engine (`dub_processor_v2.py`) to use an asynchronous worker pool via `asyncio.Queue`/`Semaphore` and streaming raw audio arrays entirely **in-memory via Python's `io.BytesIO`**, we slashed total execution time down to just **10–15 minutes**[cite: 9].
- **Bypassing Rate Limits (429 Errors):** We successfully mitigated strict platform anti-scraping blocks by pairing `yt-dlp` with the **Deno JS runtime** to handle secure modern player handshakes, mimicking explicit browser client headers, and enforcing a strict **65-second sleep buffer**[cite: 9].
- **Timeline Collision Defense:** Simple subtitle parsing causes overlapping text clusters. We built an intentional timeline tracker that calculates explicit dialogue windows, pushes overlapping segments down the sequence using a `last_audio_end` tracker, and utilizes **FFmpeg’s `atempo` filter** (capped at 1.4x) to accelerate speech without causing a pitch-ruining "chipmunk effect"[cite: 9].
- **Audio Ducking:** A single-line complex FFmpeg multiplexer command beautifully ducks the native Urdu background noise down to 15% (preserving the original atmospheric score and foley effects) while overlaying the generated Malayalam speech track at full volume[cite: 9].

### 🔴 What Didn't Work (The Brick Walls)

- **Auto-Generated Captions:** Relying on automatically transcribed speech tokens resulted in broken, fragmented timestamp intervals that ruined downstream translation fluidity[cite: 9]. _Solution used:_ We pivoted to fetching official, human-curated English subtitle files via `downloader.py`[cite: 9].
- **Virtual Environment Fragility:** Renaming or shifting directory structures immediately breaks Python's hardcoded absolute paths inside `venv/bin/`[cite: 9]. The workaround requires a full environment wipe (`rm -rf venv`) and standard re-installation from `requirements.txt`[cite: 9].
- **The Fatal Bottleneck—Multi-Character Voice Cloning:** The ultimate goal was to move past a single robotic narrator (`ml-IN-SobhanaNeural`) into true multi-character voice matching[cite: 9]. However, attempting to run speaker diarization (`pyannote.audio`) alongside zero-shot voice cloning (`F5-TTS`) triggered severe **Out-Of-Memory (OOM) failures** and brutal thermal throttling on our target 8GB unified memory M2 MacBook Air hardware[cite: 9]. Splitting the execution into separate isolated execution phases proved too brittle for practical, consumer-grade use[cite: 9].

### 🧠 Key Engineering Lessons

1. **Network-bound processing must be asynchronous.** Sequential network requests over thousands of dialogue chunks will kill any pipeline's performance[cite: 9].
2. **Human Metadata > AI Inference.** Curated, structural subtitle assets provide fundamentally superior timestamp blocks compared to raw AI speech-to-text algorithms[cite: 9].
3. **Hardware Boundaries Dictate Software Architecture.** Deep neural voice cloning models require heavy VRAM footprints that are still deeply impractical for instantaneous execution on everyday consumer laptops without massive cloud infrastructure dependencies[cite: 9].

---

## 🛠️ System Architecture & Stack

The stable pipeline works by decoupling the video, scraping and time-shifting subtitle data structures, and reconstructing a synchronized audio overlay:

- **Asset Extraction:** `yt-dlp` paired with `Deno` (JS Runtime) to handle secure YouTube signatures and safely fetch captions[cite: 9].
- **Translation Engine:** `deep-translator` wrapper interacting with semantic localization interfaces[cite: 9].
- **Speech Synthesis:** `edge-tts` leveraging high-quality Microsoft Edge Neural Voice assets (`ml-IN-SobhanaNeural`)[cite: 9].
- **Audio Composition:** `pydub` and `FFmpeg` for automated time-stretching, pitch-preservation scaling, and track muxing[cite: 9].

---

## 🚀 Getting Started (Stable Single-Voice Pipeline)

### Prerequisites

Ensure you have **FFmpeg** and **Deno** installed on your host system. On macOS, you can fetch these via Homebrew:

```bash
brew install ffmpeg deno node
```

Initialize and activate an isolated Python virtual environment:

```
python3 -m venv venv
source venv/bin/activate
```

Install the required dependencies along with the TLS fingerprinting extras:

```
pip install -r requirements.txt
pip install -U "yt-dlp[default,curl-cffi]"
```

### 📦 Pipeline Workflow

- Step 1: Scrape AssetsDownload the raw target video and Urdu captions, safely bypassing platform rate-limit gates: Bashpython downloader.py "YOUR_YOUTUBE_URL"
- Step 2: Format SubtitlesConvert the native WebVTT layout to standard SubRip (SRT) captions using FFmpeg: Bashffmpeg -i episode_subs.ur.vtt episode_subs.ur.srt
- Step 3: Synthesize Speech TimelineParse, translate, and structurally stretch the synthetic Malayalam vocal track to map perfectly against character dialogue windows: Bashpython dub_processor.py episode_subs.ur.srt output_malayalam.mp3
- Step 4: Final Media MuxingStitch the completed voiceover back onto the original file, ducking the native background audio to 15% to maintain ambient music and sound effects: Bashffmpeg -i raw_video.mp4 -i output_malayalam.mp3 \
  -filter_complex "[0:a]volume=0.15[bg_ducked]; [bg_ducked][1:a]amix=inputs=2:duration=first[mixed_audio]" \
  -map 0:v -map "[mixed_audio]" -c:v copy -c:a aac final_desktop_screening.mp4

### ⚡ Run Entire Automated Loop

Alternatively, you can execute the entire end-to-end extraction, translation, and synthesis pipeline via the single orchestrator script

```
python run.py "[https://www.youtube.com/watch?v=YOUR_VIDEO_ID](https://www.youtube.com/watch?v=YOUR_VIDEO_ID)"
```

## ⚖️ Legal & Responsible Use

### License

This project is licensed under the [MIT License](LICENSE). You are free to use, modify, and distribute this software for lawful purposes.

### Disclaimer

**This tool is provided for educational and personal use only.** Users are solely responsible for ensuring their use complies with all applicable laws, regulations, and third-party terms of service.

### Important Considerations

- **Copyright & Intellectual Property**: Do not use this tool to create derivatives of copyrighted content without explicit permission from the copyright holder. Unauthorized remixing, dubbing, or redistribution of copyrighted material violates intellectual property laws in most jurisdictions.

- **Platform Terms of Service**: Many video hosting platforms (including YouTube) prohibit automated downloading in their Terms of Service. Verify you have the right to download and modify any source material before using this tool. The authors assume no liability for users' violations of platform policies.

- **Fair Use**: While fair use may apply in limited educational or transformative contexts, it is narrow and fact-specific. Do not assume fair use protects your use case—consult legal counsel if in doubt.

- **Intended Use Cases**: This tool is designed for:
  - Personal archival of content you own or have permission to modify
  - Educational experiments with audio/video processing
  - Remixing of original or licensed content
  - Testing and development in controlled environments

### No Warranty

This software is provided "as-is" without warranty of any kind. The authors are not liable for misuse, legal consequences, platform bans, data loss, or any other damages arising from the use of this tool.

### Attribution

If you use this tool, attribution to the original authors is appreciated but not required.

---

**By using this software, you acknowledge that you have read and understood these terms and accept full responsibility for your use.**
