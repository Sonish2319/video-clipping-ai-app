
import subprocess
from pathlib import Path
import shutil


class SubtitleBurner:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.output_root = (
            self.project_root / "output" / "final"
        )

        self.temp_root = (
            self.project_root / "output" / "subtitles" / "temp"
        )

        self.output_root.mkdir(parents=True, exist_ok=True)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def burn(
        self,
        video_path,
        subtitle_path,
        output_filename,
        video_name=None
    ):

        video_path = Path(video_path).resolve()
        subtitle_path = Path(subtitle_path).resolve()

        if not video_path.exists():
            raise FileNotFoundError(video_path)

        if not subtitle_path.exists():
            raise FileNotFoundError(subtitle_path)

        output_dir = self.output_root

        if video_name:
            output_dir = output_dir / video_name

        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / output_filename

        temp_subtitle = (
            self.temp_root / "subtitle_temp.srt"
        )

        shutil.copy2(subtitle_path, temp_subtitle)

        relative_subtitle_path = temp_subtitle.relative_to(
            self.project_root
        ).as_posix()

        relative_subtitle_path = relative_subtitle_path.replace(
            ":", r"\:"
        )

        subtitle_filter = (
            f"subtitles=filename={relative_subtitle_path}:"
            "force_style='"
            "FontName=Arial,"
            "FontSize=18,"
            "Bold=1,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "BorderStyle=1,"
            "Outline=2,"
            "Shadow=1,"
            "Alignment=2,"
            "MarginV=140"
            "'"
        )

        command = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vf", subtitle_filter,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(output_path)
        ]

        print("Burning styled subtitles into video...")

        try:

            result = subprocess.run(
                command,
                cwd=str(self.project_root),
                capture_output=True,
                text=True
            )

            if result.returncode != 0:

                print("\nFFmpeg error:")
                print(result.stderr)

                raise RuntimeError(
                    "Subtitle burning failed."
                )

            print("\nFinal video created:", output_path)

            return output_path

        finally:

            if temp_subtitle.exists():
                temp_subtitle.unlink()


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("video")
    parser.add_argument("subtitles")

    args = parser.parse_args()

    burner = SubtitleBurner()

    output = burner.burn(
        args.video,
        args.subtitles,
        "test_final.mp4",
        video_name=Path(args.video).stem
    )

    print("\nSubtitle burning completed.")
    print("Output:", output)
