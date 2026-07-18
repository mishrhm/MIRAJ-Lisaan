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
    
    # Unified command to fetch the high-quality MP4 stream AND the official English track together
    download_command = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "--write-subs",            # Download the official uploaded subtitles
        "--sub-lang", "en",        # Look specifically for the English track
        "-o", "raw_video.mp4",     # Name the raw video stream output
        "--sleep-subtitles", "65"  # Safeguard delay to protect against immediate 429 locks
    ] + header_args + [youtube_url]
    
    try:
        print("[*] Fetching raw video file along with official English subtitles...")
        print("[*] (Includes an intentional 65s pause before processing to bypass strict rate limit barriers)")
        subprocess.run(download_command, check=True)
        
        print("[✓] All video and subtitle assets downloaded successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"[!] Error executing yt-dlp: {e}")
        print("[!] Note: If the subtitle portion failed, ensure the video actually has a dedicated English track uploaded.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python downloader.py <YOUTUBE_URL>")
        sys.exit(1)
        
    url = sys.argv[1]
    download_assets(url)