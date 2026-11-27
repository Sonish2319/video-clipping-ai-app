
import json
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class FrameSampler:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.output_dir = self.project_root / "output" / "frames"

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def get_video_duration(self, video_path):

        command = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(video_path)
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True
        )

        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    @staticmethod
    def calculate_dynamic_interval(duration_seconds, target_max_frames=30):
        """
        Dynamically determine frame sampling interval based on video duration
        to prevent local Ollama vision model processing bottlenecks:
        - <= 60s (under 1 min):    3s interval  (~10-20 frames)
        - <= 180s (1 - 3 mins):    6s interval  (~20-30 frames, e.g. 2 mins -> 20 frames)
        - <= 360s (3 - 6 mins):    10s interval (~18-36 frames, e.g. 5 mins -> 30 frames)
        - <= 600s (6 - 10 mins):   20s interval (~18-30 frames, e.g. 10 mins -> 30 frames)
        - <= 900s (10 - 15 mins):  30s interval (~20-30 frames, e.g. 15 mins -> 30 frames)
        - <= 1800s (15 - 30 mins): 45s interval (~20-40 frames, e.g. 20 mins -> 26 frames)
        - > 1800s (> 30 mins):     60s - 120s interval (capped at ~30 frames)
        """
        d = float(duration_seconds)
        if d <= 60:
            return 3
        elif d <= 180:
            return 6
        elif d <= 360:
            return 10
        elif d <= 600:
            return 20
        elif d <= 900:
            return 30
        elif d <= 1800:
            return 45
        else:
            return max(60, int(round(d / target_max_frames)))

    def sample_frames(
        self,
        video_path,
        interval=None,
        image_width=640
    ):

        video_path = Path(video_path).resolve()

        if not video_path.exists():
            raise FileNotFoundError(video_path)

        duration = self.get_video_duration(video_path)

        if interval is None or interval <= 0:
            interval = self.calculate_dynamic_interval(duration)
            print(
                f"Dynamic frame interval selected: {interval}s "
                f"(video duration: {duration:.1f}s / {duration/60:.1f} mins)"
            )
        else:
            print(f"Using specified frame interval: {interval}s")

        video_name = video_path.stem

        frame_dir = self.output_dir / video_name

        frame_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        # Remove previously generated frames and sampling info
        for old_frame in frame_dir.glob("frame_*.jpg"):
            old_frame.unlink()

        output_pattern = frame_dir / "frame_%03d.jpg"

        command = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vf", f"fps=1/{interval},scale={image_width}:-1",
            "-q:v", "3",
            str(output_pattern)
        ]

        print(f"Extracting representative video frames every {interval}s...")

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        if result.returncode != 0:
            print(result.stderr)
            raise RuntimeError("Frame extraction failed.")

        frames = sorted(frame_dir.glob("frame_*.jpg"))

        print(f"Successfully extracted {len(frames)} frames.")

        for index, frame in enumerate(frames):
            timestamp = index * interval
            print(f"{frame.name} -> {timestamp:.2f} seconds")

        # Save sampling metadata so downstream tools know the exact interval
        info_path = frame_dir / "sampling_info.json"
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump({
                "video_name": video_name,
                "video_duration": round(duration, 2),
                "sampling_interval": interval,
                "total_frames": len(frames)
            }, f, indent=4)

        return frames


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="Extract video frames with dynamic or manual interval.")

    parser.add_argument("video", help="Path to video file")

    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Frame sampling interval in seconds (default: 0 for dynamic auto-calculation based on video length)"
    )

    args = parser.parse_args()

    sampler = FrameSampler()

    frames = sampler.sample_frames(
        args.video,
        interval=args.interval
    )

    print("\nFrame sampling completed.")
    print("Total frames:", len(frames))
