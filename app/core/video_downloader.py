import argparse
import os
import re
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import yt_dlp


class VideoDownloader:

    def __init__(self, output_dir=None):
        self.project_root = Path(__file__).resolve().parents[2]
        self.input_dir = Path(output_dir) if output_dir else (self.project_root / "input")
        self.input_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_url(string):
        if not string or not isinstance(string, str):
            return False
        pattern = r"^(https?://|www\.)|(youtube\.com|youtu\.be)"
        return bool(re.search(pattern, string.strip(), re.IGNORECASE))

    @staticmethod
    def clean_filename(title):
        # Remove invalid filename characters
        clean = re.sub(r'[<>:"/\\|?*#%&{}\\<>*?/$!\'":@+`|=]', "", title)
        clean = re.sub(r"\s+", "_", clean.strip())
        clean = re.sub(r"_+", "_", clean)
        return clean[:50].strip("._") or "youtube_video"

    @staticmethod
    def normalize_quality(quality_str):
        if not quality_str:
            return "720p"
        q = str(quality_str).strip().lower().replace("p", "")
        if q == "480":
            return "480p"
        return "720p"  # Default / max for now is 720p

    def download(self, url, quality="720p"):
        """
        Download YouTube video at specified quality (480p or 720p max).
        Returns Path to the downloaded .mp4 file in input/.
        """
        quality = self.normalize_quality(quality)
        max_height = 480 if quality == "480p" else 720

        print(f"\n===== YOUTUBE VIDEO DOWNLOADER =====")
        print(f"URL: {url}")
        print(f"Target Quality: {quality} (max height: {max_height}p)")
        print(f"Download Directory: {self.input_dir}")

        # Temporary template using video id to avoid filename encoding collisions
        temp_template = str(self.input_dir / "%(id)s.%(ext)s")

        ydl_opts = {
            "format": (
                f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={max_height}]+bestaudio/"
                f"best[height<={max_height}][ext=mp4]/"
                f"best[height<={max_height}]/"
                f"best"
            ),
            "outtmpl": temp_template,
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": False,
            "no_warnings": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("\nFetching video information...")
            info = ydl.extract_info(url, download=True)
            video_id = info.get("id", "video")
            raw_title = info.get("title", f"video_{video_id}")
            duration = info.get("duration", 0)

            print(f"Title: {raw_title}")
            print(f"Duration: {duration}s (~{round(duration / 60, 1)} mins)")

        # Locate downloaded file (may be .mp4 or merged)
        downloaded_candidates = list(self.input_dir.glob(f"{video_id}.*"))
        if not downloaded_candidates:
            # Fallback check for any matching pattern
            downloaded_candidates = list(self.input_dir.glob(f"*{video_id}*"))

        if not downloaded_candidates:
            raise FileNotFoundError(f"Failed to find downloaded video for ID: {video_id}")

        source_file = downloaded_candidates[0]

        # Rename to clean readable title
        clean_title = self.clean_filename(raw_title)
        target_file = self.input_dir / f"{clean_title}.mp4"

        # If target file exists and differs, remove old or append id
        if target_file.exists() and target_file.resolve() != source_file.resolve():
            target_file = self.input_dir / f"{clean_title}_{video_id}.mp4"

        if source_file.resolve() != target_file.resolve():
            if target_file.exists():
                target_file.unlink()
            source_file.rename(target_file)

        print(f"\n[OK] Video successfully downloaded and saved to:")
        print(f"     {target_file} ({round(target_file.stat().st_size / (1024 * 1024), 2)} MB)")

        return target_file

    def prompt_user_input(self):
        """
        Interactive prompt asking for YouTube link and quality (480p or 720p).
        """
        print("\n" + "=" * 65)
        print("LOCAL AI VIDEO CLIPPING - YOUTUBE INPUT")
        print("=" * 65)

        url = ""
        while not url:
            url_input = input("Enter YouTube video link (or local video path): ").strip()
            if not url_input:
                print("Input cannot be empty. Please enter a valid URL or path.")
                continue

            # Check if user entered a local file path
            local_path = Path(url_input)
            if local_path.exists() and local_path.is_file():
                print(f"Detected existing local video file: {local_path.resolve()}")
                return local_path.resolve(), None

            if not self.is_url(url_input):
                # Try prepending https:// if it looks like youtube or youtu.be
                if "youtube" in url_input or "youtu.be" in url_input:
                    url_input = "https://" + url_input.lstrip(":/")
                else:
                    print("Invalid input: Please enter a valid YouTube URL (e.g. https://www.youtube.com/watch?v=...) or existing local file path.")
                    continue

            url = url_input

        print("\nSelect video quality (max 720p):")
        print("  [1] 720p (Recommended)")
        print("  [2] 480p")
        quality_choice = input("Choice [1/2, default: 1]: ").strip()

        quality = "480p" if quality_choice == "2" else "720p"

        downloaded_file = self.download(url, quality=quality)
        return downloaded_file, quality


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download YouTube video for LocalVideoAI pipeline.")
    parser.add_argument("url", nargs="?", default=None, help="YouTube video URL")
    parser.add_argument("--quality", choices=["480p", "720p", "480", "720"], default="720p", help="Max video quality (480p or 720p)")

    args = parser.parse_args()
    downloader = VideoDownloader()

    if args.url:
        video_path = downloader.download(args.url, quality=args.quality)
    else:
        video_path, _ = downloader.prompt_user_input()

    print(f"\nDownloaded video ready at: {video_path}")
