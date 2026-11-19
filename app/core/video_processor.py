
import json
import subprocess
from pathlib import Path


class VideoProcessor:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.frame_dir = self.project_root / "output" / "frames"
        self.clip_dir = self.project_root / "output" / "clips"

        self.frame_dir.mkdir(parents=True, exist_ok=True)
        self.clip_dir.mkdir(parents=True, exist_ok=True)

    def _run(self, command):
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout

    def get_metadata(self, video_path):
        video_path = Path(video_path).resolve()

        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        command = [
            "ffprobe",
            "-v", "error",
            "-show_streams",
            "-show_format",
            "-of", "json",
            str(video_path)
        ]

        data = json.loads(self._run(command))

        video_stream = next(
            (
                stream for stream in data["streams"]
                if stream["codec_type"] == "video"
            ),
            None
        )

        audio_stream = next(
            (
                stream for stream in data["streams"]
                if stream["codec_type"] == "audio"
            ),
            None
        )

        if video_stream is None:
            raise ValueError("No video stream found.")

        metadata = {
            "filename": video_path.name,
            "duration": float(data["format"].get("duration", 0)),
            "size_mb": round(
                int(data["format"].get("size", 0)) / (1024 * 1024), 2
            ),
            "video_codec": video_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": video_stream.get("r_frame_rate"),
            "has_audio": audio_stream is not None,
            "audio_codec": (
                audio_stream.get("codec_name")
                if audio_stream else None
            ),
        }

        return metadata

    def extract_frames(self, video_path, timestamps):
        video_path = Path(video_path).resolve()
        extracted = []

        for timestamp in timestamps:
            timestamp = float(timestamp)

            if timestamp < 0:
                raise ValueError("Timestamp cannot be negative.")

            output_file = (
                self.frame_dir /
                f"{video_path.stem}_{timestamp:g}s.jpg"
            )

            command = [
                "ffmpeg",
                "-y",
                "-ss", str(timestamp),
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "2",
                str(output_file)
            ]

            self._run(command)
            extracted.append(str(output_file))

        return extracted

    def extract_clip(self, video_path, start, end, filename):
        video_path = Path(video_path).resolve()

        start = float(start)
        end = float(end)

        if start < 0 or end <= start:
            raise ValueError("Invalid clip timestamps.")

        if end > self.get_metadata(video_path)["duration"]:
            raise ValueError("Clip end exceeds video duration.")

        if Path(filename).name != filename:
            raise ValueError("Filename must not contain directory paths.")

        if not filename.lower().endswith(".mp4"):
            filename += ".mp4"

        output_file = self.clip_dir / filename

        command = [
            "ffmpeg",
            "-y",
            "-ss", str(start),
            "-i", str(video_path),
            "-t", str(end - start),
            "-map", "0:v:0",
            "-map", "0:a:0?",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(output_file)
        ]

        self._run(command)

        return str(output_file)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Local AI Video Processing Foundation"
    )

    parser.add_argument(
        "video",
        help="Path to input video"
    )

    args = parser.parse_args()

    processor = VideoProcessor()

    print("\n===== VIDEO METADATA =====")

    metadata = processor.get_metadata(args.video)

    print(json.dumps(metadata, indent=4))

    print("\n===== FRAME EXTRACTION =====")

    duration = metadata["duration"]

    timestamps = [
        duration * 0.10,
        duration * 0.50,
        duration * 0.90
    ]

    frames = processor.extract_frames(
        args.video,
        timestamps
    )

    for frame in frames:
        print("Extracted:", frame)

    print("\n===== CLIP EXTRACTION =====")

    clip_end = min(10, duration)

    if clip_end > 2:
        clip = processor.extract_clip(
            args.video,
            0,
            clip_end,
            "test_clip.mp4"
        )

        print("Created:", clip)

    print("\nProcessing completed successfully.")
