
import subprocess
from pathlib import Path


class VideoFormatter:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.output_root = (
            self.project_root / "output" / "formatted"
        )

        self.output_root.mkdir(parents=True, exist_ok=True)

    def format_video(
        self,
        input_path,
        output_filename,
        mode="blur",
        width=1080,
        height=1920,
        video_name=None
    ):

        input_path = Path(input_path).resolve()

        if not input_path.exists():
            raise FileNotFoundError(input_path)

        output_dir = self.output_root

        if video_name:
            output_dir = output_dir / video_name

        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / output_filename

        if mode == "crop":

            video_filter = (
                f"scale={width}:{height}:"
                "force_original_aspect_ratio=increase,"
                f"crop={width}:{height},"
                "setsar=1"
            )

        elif mode == "fit":

            video_filter = (
                f"scale={width}:{height}:"
                "force_original_aspect_ratio=decrease,"
                "setsar=1,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:"
                "color=black"
            )

        elif mode == "blur":

            video_filter = (
                f"[0:v]split=2[bg][fg];"
                f"[bg]scale={width}:{height}:"
                "force_original_aspect_ratio=increase,"
                f"crop={width}:{height},"
                "boxblur=20:10[bg];"
                f"[fg]scale={width}:{height}:"
                "force_original_aspect_ratio=decrease,"
                "setsar=1[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                "setsar=1[v]"
            )

        else:
            raise ValueError("Mode must be crop, fit, or blur.")

        command = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-filter_complex" if mode == "blur" else "-vf",
            video_filter,
        ]

        if mode == "blur":
            command.extend(["-map", "[v]", "-map", "0:a?"])

        command.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path)
        ])

        print(f"Formatting video using '{mode}' mode...")

        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        print("Formatted video:", output_path)

        return output_path


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("video")
    parser.add_argument(
        "--mode",
        choices=["crop", "fit", "blur"],
        default="blur"
    )

    args = parser.parse_args()

    formatter = VideoFormatter()

    output = formatter.format_video(
        args.video,
        f"{Path(args.video).stem}_vertical.mp4",
        mode=args.mode,
        video_name=Path(args.video).stem
    )

    print("\nFormatting completed successfully.")
    print("Output:", output)
