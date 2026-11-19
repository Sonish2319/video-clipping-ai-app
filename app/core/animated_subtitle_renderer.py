
import json
import subprocess
import argparse
import tempfile
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


class AnimatedSubtitleRenderer:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.output_root = (
            self.project_root / "output" / "animated_subtitles"
        )

        self.output_root.mkdir(
            parents=True,
            exist_ok=True
        )

        self.width = 1080
        self.height = 1920
        self.fps = 30

        self.font_size = 64
        self.minimum_font_size = 48

        self.active_color = (255, 220, 0, 255)
        self.normal_color = (255, 255, 255, 255)
        self.outline_color = (0, 0, 0, 255)

        self.horizontal_margin = 90
        self.line_spacing = 22
        self.bottom_position = 0.76

        self.animation_duration = 0.15

    def load_caption_data(self, json_path):

        json_path = Path(json_path)

        if not json_path.exists():
            raise FileNotFoundError(json_path)

        with open(json_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def get_font(self, size=None):

        size = size or self.font_size

        font_paths = [
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("C:/Windows/Fonts/Arial.ttf")
        ]

        for font_path in font_paths:

            if font_path.exists():
                return ImageFont.truetype(
                    str(font_path),
                    size
                )

        return ImageFont.load_default()

    def measure_text(self, draw, text, font):

        bbox = draw.textbbox(
            (0, 0),
            text,
            font=font,
            stroke_width=4
        )

        return bbox[2] - bbox[0]

    def wrap_words(self, words, font):

        dummy = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy)

        max_width = self.width - (self.horizontal_margin * 2)

        lines = []
        current_line = []
        current_width = 0

        spacing = 18

        for word in words:

            text = word["text"]

            word_width = self.measure_text(
                draw,
                text,
                font
            )

            required_width = (
                word_width if not current_line
                else word_width + spacing
            )

            if (
                current_line
                and current_width + required_width > max_width
            ):

                lines.append(current_line)
                current_line = []
                current_width = 0
                required_width = word_width

            current_line.append(word)

            current_width += required_width

        if current_line:
            lines.append(current_line)

        return lines

    def get_layout(self, words):

        font_size = self.font_size

        while font_size >= self.minimum_font_size:

            font = self.get_font(font_size)

            lines = self.wrap_words(words, font)

            if len(lines) <= 2:
                return font, lines

            font_size -= 2

        font = self.get_font(self.minimum_font_size)

        return font, self.wrap_words(words, font)

    def render_caption(
        self,
        caption,
        active_word_index,
        output_path,
        scale=1.0
    ):

        image = Image.new(
            "RGBA",
            (self.width, self.height),
            (0, 0, 0, 0)
        )

        draw = ImageDraw.Draw(image)

        words = caption["words"]

        font, lines = self.get_layout(words)

        spacing = 18
        line_height = self.font_size + self.line_spacing

        total_height = (
            len(lines) * line_height
        )

        base_y = int(self.height * self.bottom_position)

        start_y = base_y - total_height // 2

        word_counter = 0

        for line_index, line in enumerate(lines):

            widths = []

            for word in line:

                word_width = self.measure_text(
                    draw,
                    word["text"],
                    font
                )

                widths.append(word_width)

            total_width = (
                sum(widths)
                + spacing * (len(line) - 1)
            )

            x = (self.width - total_width) // 2

            y = start_y + line_index * line_height

            for word_index, word in enumerate(line):

                color = (
                    self.active_color
                    if word_counter == active_word_index
                    else self.normal_color
                )

                word_scale = (
                    scale if word_counter == active_word_index
                    else 1.0
                )

                if word_scale != 1.0:

                    temporary_size = max(
                        1,
                        int(font.size * word_scale)
                    )

                    temporary_font = self.get_font(
                        temporary_size
                    )

                else:
                    temporary_font = font

                draw.text(
                    (x, y),
                    word["text"],
                    font=temporary_font,
                    fill=color,
                    stroke_width=4,
                    stroke_fill=self.outline_color
                )

                x += widths[word_index] + spacing

                word_counter += 1

        image.save(output_path)

    def run_ffmpeg(self, command):

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            raise RuntimeError(
                f"FFmpeg failed:\n{result.stderr}"
            )

    def create_overlay_frames(self, data, temp_dir):

        captions = data.get("captions", [])

        if not captions:
            raise ValueError("No captions found in JSON.")

        duration = float(data["duration"])

        total_frames = math.ceil(duration * self.fps)

        frames_dir = temp_dir / "frames"

        frames_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        frame_index = 0

        for frame_number in range(total_frames):

            timestamp = frame_number / self.fps

            active_caption = None
            active_word_index = -1

            for caption in captions:

                if not (
                    caption["start"]
                    <= timestamp
                    <= caption["end"]
                ):
                    continue

                active_caption = caption

                for index, word in enumerate(caption["words"]):

                    if (
                        word["start"]
                        <= timestamp
                        <= word["end"]
                    ):

                        active_word_index = index
                        break

                break

            frame_path = (
                frames_dir / f"frame_{frame_number:06d}.png"
            )

            if active_caption is None:

                image = Image.new(
                    "RGBA",
                    (self.width, self.height),
                    (0, 0, 0, 0)
                )

                image.save(frame_path)

            else:

                scale = 1.0

                if active_word_index >= 0:

                    active_word = active_caption["words"][
                        active_word_index
                    ]

                    elapsed = timestamp - active_word["start"]

                    if elapsed < self.animation_duration:

                        progress = elapsed / self.animation_duration

                        scale = (
                            1.0 + 0.18 * (1.0 - progress)
                        )

                self.render_caption(
                    active_caption,
                    active_word_index,
                    frame_path,
                    scale=scale
                )

            frame_index += 1

        return frames_dir, frame_index

    def render(
        self,
        video_path,
        caption_json,
        output_filename
    ):

        video_path = Path(video_path).resolve()

        if not video_path.exists():
            raise FileNotFoundError(video_path)

        data = self.load_caption_data(caption_json)

        output_path = self.output_root / output_filename

        with tempfile.TemporaryDirectory(
            dir=self.output_root
        ) as temp_directory:

            temp_dir = Path(temp_directory)

            print("\nGenerating caption animation frames...")

            frames_dir, total_frames = (
                self.create_overlay_frames(
                    data,
                    temp_dir
                )
            )

            print(f"Generated {total_frames} overlay frames.")

            frame_pattern = str(
                frames_dir / "frame_%06d.png"
            )

            command = [

                "ffmpeg",
                "-y",

                "-i", str(video_path),

                "-framerate", str(self.fps),
                "-i", frame_pattern,

                "-filter_complex",
                (
                    "[0:v][1:v]"
                    "overlay=0:0:format=auto"
                    "[outv]"
                ),

                "-map", "[outv]",
                "-map", "0:a?",

                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "20",

                "-c:a", "aac",
                "-b:a", "192k",

                "-shortest",

                str(output_path)
            ]

            print("\nCombining captions with video...")

            self.run_ffmpeg(command)

        return output_path


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("video")
    parser.add_argument("captions")

    parser.add_argument(
        "--output",
        default="animated_subtitles_test.mp4"
    )

    args = parser.parse_args()

    renderer = AnimatedSubtitleRenderer()

    result = renderer.render(
        args.video,
        args.captions,
        args.output
    )

    print("\nAnimated subtitle video created:")
    print(result)
