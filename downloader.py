# downloader.py
import subprocess
import sys

def download_assets(youtube_url):
    print(f"[*] Starting asset download for: {youtube_url}")
    
    header_args = [
        "--impersonate", "chrome",
        "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "--referer", "https://www.youtube.com/",
    ]
    
    # 1. Subtitle extraction command with strict rate limit throttling
    sub_command = [
        "yt-dlp",
        "--write-auto-subs",
        "--sub-lang", "ur",
        "--skip-download",
        "-o", "episode_subs",
        "--sleep-subtitles", "65"  # Crucial buffer to bypass the immediate 429 subtitle block
    ] + header_args + [youtube_url]
    
    # 2. Main video stream command
    video_command = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "-o", "raw_video.mp4"
    ] + header_args + [youtube_url]
    
    try:
        print("[*] Fetching Urdu subtitles (This will introduce a intentional 65s pause to avoid 429 blocks)...")
        subprocess.run(sub_command, check=True)
        
        print("[*] Downloading raw video assets...")
        subprocess.run(video_command, check=True)
        
        print("[✓] All assets downloaded successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"[!] Error executing yt-dlp: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python downloader.py <YOUTUBE_URL>")
        sys.exit(1)
        
    url = sys.argv[1]
    download_assets(url)