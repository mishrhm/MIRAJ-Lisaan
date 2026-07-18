# MIRAJ-Lisaan 🎙️

An open-source automation pipeline designed to translate and dynamically dub Urdu YouTube videos (such as Pakistani Serials) into Malayalam speech tracks using neural text-to-speech engine workflows.

Built to help family members enjoy content seamlessly on desktop platforms with natural localized voiceovers.

---

## 🛠️ System Architecture & Stack

The pipeline works by decoupling the video, scraping and time-shifting subtitle data structures, and reconstructing a synchronized audio overlay:

- **Asset Extraction:** `yt-dlp` paired with `Deno` (JS Runtime) to handle secure YouTube signatures and safely fetch auto-generated captions.
- **Translation Engine:** `deep-translator` wrapper interacting with semantic localization interfaces.
- **Speech Synthesis:** `edge-tts` leveraging high-quality Microsoft Edge Neural Voice assets (`ml-IN-SobhanaNeural`).
- **Audio Composition:** `pydub` and `FFmpeg` for automated time-stretching, pitch-preservation scaling, and track muxing.

---

## 🚀 Getting Started

### Prerequisites

Ensure you have **FFmpeg** and **Deno** installed on your host system. On macOS, you can fetch these via Homebrew:

```bash
brew install ffmpeg deno node
```

# Miraj Dubs

## Installation

Clone this repository and navigate to the project directory:

```bash
git clone https://github.com/yourusername/miraj-dubs.git
cd miraj-dubs
```

Initialize and activate an isolated Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the required dependencies along with the TLS fingerprinting extras:

```bash
pip install -r requirements.txt
pip install -U "yt-dlp[default,curl-cffi]"
```

## 📦 Pipeline Workflow

### Step 1: Scrape Assets

Download the raw target video and Urdu auto-captions, safely bypassing burst-protection gates:

```bash
python downloader.py "YOUR_YOUTUBE_URL"
```

### Step 2: Format Subtitles

Convert the native WebVTT layout to standard SubRip captions using FFmpeg:

```bash
ffmpeg -i episode_subs.ur.vtt episode_subs.ur.srt
```

### Step 3: Synthesize Speech Timeline

Parse, translate, and structurally stretch the synthetic Malayalam vocal track to map perfectly against character dialogue windows:

```bash
python dub_processor.py episode_subs.ur.srt output_malayalam.mp3
```

### Step 4: Final Media Muxing

Stitch the completed voiceover back onto the original file, ducking the native background audio to 15% to maintain ambient music and sound effects:

```bash
ffmpeg -i raw_video.mp4 -i output_malayalam.mp3 \
  -filter_complex "[0:a]volume=0.15[bg_ducked]; [bg_ducked][1:a]amix=inputs=2:duration=first[mixed_audio]" \
  -map 0:v -map "[mixed_audio]" -c:v copy -c:a aac final_desktop_screening.mp4
```

### RUN BY USING

python run.py "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"

## ⚙️ Upcoming Roadmap

- [ ] Optimize compilation pipeline using asynchronous I/O and concurrent in-memory tasks.
- [ ] Port execution layers to an Android TV framework using localized ExoPlayer hooks and proxy TTS systems.

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
