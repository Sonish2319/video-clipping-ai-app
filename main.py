#!/usr/bin/env python3
"""
Local AI Video Clipping Application
Entry point for running the complete video clipping pipeline with YouTube download support.
"""

import sys
from pathlib import Path

# Ensure UTF-8 console streams on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add app/core to sys.path
core_dir = Path(__file__).resolve().parent / "app" / "core"
if str(core_dir) not in sys.path:
    sys.path.insert(0, str(core_dir))

from full_pipeline import FullVideoPipeline
from video_downloader import VideoDownloader
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Local AI Video Clipping: Download YouTube video and create vertical shorts with animated subtitles."
    )

    parser.add_argument(
        "video",
        nargs="?",
        default=None,
        help="YouTube URL or path to local video file. If omitted, you will be prompted."
    )

    parser.add_argument(
        "--url",
        default=None,
        help="YouTube video URL to download"
    )

    parser.add_argument(
        "--quality",
        choices=["480p", "720p", "480", "720"],
        default=None,
        help="Video download quality (480p or 720p, default: 720p)"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Frame sampling interval in seconds (default: 0 for dynamic auto-calculation based on video length, e.g. 10s for 5 mins)"
    )

    parser.add_argument(
        "--min-duration",
        type=float,
        default=10.0,
        help="Minimum clip duration in seconds (default: 10.0)"
    )

    parser.add_argument(
        "--max-duration",
        type=float,
        default=20.0,
        help="Maximum clip duration in seconds (default: 20.0)"
    )

    parser.add_argument(
        "--subtitle-mode",
        choices=["animated", "standard"],
        default="animated",
        help="Subtitle style for final clips: 'animated' (word-by-word highlighted) or 'standard' (static SRT). Default: animated"
    )

    args = parser.parse_args()

    downloader = VideoDownloader()
    video_target = args.url or args.video

    if not video_target:
        # Ask user interactively for YouTube link and quality
        video_path, _ = downloader.prompt_user_input()
    elif VideoDownloader.is_url(str(video_target)):
        quality = args.quality or "720p"
        video_path = downloader.download(video_target, quality=quality)
    else:
        video_path = Path(video_target)
        if not video_path.exists():
            if "youtube" in str(video_target) or "youtu.be" in str(video_target):
                quality = args.quality or "720p"
                video_path = downloader.download(video_target, quality=quality)
            else:
                raise FileNotFoundError(f"Video file not found: {video_path}")

    pipeline = FullVideoPipeline(
        video_path,
        frame_interval=args.interval,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        subtitle_mode=args.subtitle_mode
    )

    pipeline.run()


if __name__ == "__main__":
    main()
