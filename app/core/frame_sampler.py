
import subprocess
from pathlib import Path


class FrameSampler:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.output_dir = self.project_root / "output" / "frames"

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def sample_frames(
        self,
        video_path,
        interval=5,
        image_width=640
    ):

        video_path = Path(video_path).resolve()

        if not video_path.exists():
            raise FileNotFoundError(video_path)

        if interval <= 0:
            raise ValueError("Interval must be greater than zero.")

        video_name = video_path.stem

        frame_dir = self.output_dir / video_name

        frame_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        # Remove previously generated frames.
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

        print("Extracting representative video frames...")

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            print(result.stderr)

            raise RuntimeError("Frame extraction failed.")

        frames = sorted(frame_dir.glob("frame_*.jpg"))

        print(f"Successfully extracted {len(frames)} frames.")

        for index, frame in enumerate(frames):
            timestamp = index * interval

            print(f"{frame.name} -> {timestamp:.2f} seconds")

        return frames


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("video")

    parser.add_argument(
        "--interval",
        type=int,
        default=5
    )

    args = parser.parse_args()

    sampler = FrameSampler()

    frames = sampler.sample_frames(
        args.video,
        interval=args.interval
    )

    print("\nFrame sampling completed.")
    print("Total frames:", len(frames))
