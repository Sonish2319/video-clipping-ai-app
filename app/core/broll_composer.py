
import json
import subprocess
import tempfile
from pathlib import Path



class BrollComposer:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.frames_root = self.project_root / "output" / "frames"

        self.output_root = self.project_root / "output" / "broll"

        self.output_root.mkdir(
            parents=True,
            exist_ok=True
        )

        self.fps = 30
        self.broll_duration = 1.5

    def run_command(self, command):

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg command failed:\n{result.stderr}"
            )

    def get_video_metadata(self, video_path):

        command = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
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

        stream = data["streams"][0]

        return {
            "width": int(stream["width"]),
            "height": int(stream["height"]),
            "duration": float(data["format"]["duration"])
        }

    def get_valid_visuals(
        self,
        selected_visuals,
        clip_start,
        clip_duration
    ):

        valid = []

        for frame in selected_visuals:

            timestamp = frame.get("timestamp")

            filename = frame.get("frame")

            if timestamp is None or not filename:
                continue

            raw_relative = float(timestamp) - clip_start

            # If the frame was captured close to the clip window, clamp inside the clip
            if -3.0 <= raw_relative < (clip_duration + 3.0):
                relative_time = max(0.0, min(max(0.0, clip_duration - self.broll_duration), raw_relative))
            else:
                continue

            image_path = self.frames_root / self.current_video_name / filename

            if not image_path.exists():
                print("Missing frame:", image_path)
                continue

            valid.append({
                "image": image_path,
                "timestamp": relative_time
            })

        valid.sort(key=lambda item: item["timestamp"])

        return valid

    def create_broll_segment(
        self,
        image_path,
        duration,
        width,
        height,
        output_path
    ):

        command = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-framerate", str(self.fps),
            "-i", str(image_path),
            "-t", f"{duration:.3f}",
            "-vf",
            (
                f"scale={width}:{height}:"
                "force_original_aspect_ratio=increase,"
                f"crop={width}:{height},"
                "setsar=1,"
                f"fps={self.fps}"
            ),
            "-an",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            str(output_path)
        ]

        self.run_command(command)

    def create_original_segment(
        self,
        clip_path,
        start,
        duration,
        output_path,
        width,
        height
    ):

        if duration <= 0:
            return

        command = [
            "ffmpeg",
            "-y",
            "-ss", f"{start:.3f}",
            "-i", str(clip_path),
            "-t", f"{duration:.3f}",
            "-an",
            "-vf",
            (
                f"scale={width}:{height},"
                "setsar=1,"
                f"fps={self.fps}"
            ),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            str(output_path)
        ]

        self.run_command(command)

    def compose(
        self,
        clip_path,
        selected_visuals,
        clip_start,
        video_name
    ):

        clip_path = Path(clip_path).resolve()

        if not clip_path.exists():
            raise FileNotFoundError(clip_path)

        self.current_video_name = video_name

        metadata = self.get_video_metadata(clip_path)

        width = metadata["width"]
        height = metadata["height"]
        duration = metadata["duration"]

        visuals = self.get_valid_visuals(
            selected_visuals,
            clip_start,
            duration
        )

        if not visuals:
            print("No valid B-roll frames. Returning original clip.")
            return clip_path

        output_dir = self.output_root / video_name
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = (
            output_dir / f"{clip_path.stem}_broll.mp4"
        )

        print("\n===== B-ROLL COMPOSITION =====")
        print("Clip:", clip_path.name)
        print("Selected visuals:", len(visuals))

        with tempfile.TemporaryDirectory(
            dir=str(output_dir)
        ) as temp_directory:

            temp_dir = Path(temp_directory)

            segments = []
            cursor = 0.0

            for index, visual in enumerate(visuals, start=1):

                center = visual["timestamp"]

                start = max(
                    cursor,
                    center - self.broll_duration / 2
                )

                end = min(
                    duration,
                    center + self.broll_duration / 2
                )

                if end <= start:
                    continue

                # Original footage before the B-roll.
                if start > cursor:

                    segment_path = (
                        temp_dir / f"segment_{len(segments):03d}.mp4"
                    )

                    self.create_original_segment(
                        clip_path,
                        cursor,
                        start - cursor,
                        segment_path,
                        width,
                        height
                    )

                    segments.append(segment_path)

                # Selected visual cutaway.
                broll_path = (
                    temp_dir / f"segment_{len(segments):03d}.mp4"
                )

                self.create_broll_segment(
                    visual["image"],
                    end - start,
                    width,
                    height,
                    broll_path
                )

                segments.append(broll_path)

                cursor = end

                print(
                    f"B-roll {index}: "
                    f"{visual['image'].name} "
                    f"at {center:.2f}s"
                )

            # Remaining original footage.
            if cursor < duration:

                segment_path = (
                    temp_dir / f"segment_{len(segments):03d}.mp4"
                )

                self.create_original_segment(
                    clip_path,
                    cursor,
                    duration - cursor,
                    segment_path,
                    width,
                    height
                )

                segments.append(segment_path)

            if not segments:
                print("No segments created. Returning original clip.")
                return clip_path

            # Create FFmpeg concat list.
            concat_file = temp_dir / "concat.txt"

            with open(
                concat_file,
                "w",
                encoding="utf-8"
            ) as file:

                for segment in segments:
                    safe_path = segment.resolve().as_posix()
                    file.write(
                        f"file '{safe_path}'\n"
                    )

            silent_video = temp_dir / "composed_video.mp4"

            self.run_command([
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-an",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                str(silent_video)
            ])

            # Restore the original audio.
            self.run_command([
                "ffmpeg",
                "-y",
                "-i", str(silent_video),
                "-i", str(clip_path),
                "-map", "0:v:0",
                "-map", "1:a?",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                str(output_path)
            ])

        print("B-roll video saved:", output_path)

        return output_path


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("clip")
    parser.add_argument("selected_visuals")
    parser.add_argument("clip_start", type=float)
    parser.add_argument("video_name")

    args = parser.parse_args()

    with open(
        args.selected_visuals,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    if not data.get("highlights"):
        raise ValueError("No highlights found.")

    highlight = data["highlights"][0]

    composer = BrollComposer()

    result = composer.compose(
        args.clip,
        highlight.get("selected_visuals", {}).get("frames", []),
        args.clip_start,
        args.video_name
    )

    print("\nComposition completed:", result)
