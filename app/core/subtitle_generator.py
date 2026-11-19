
import json
import argparse
import re
from pathlib import Path


class SubtitleGenerator:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.output_root = (
            self.project_root / "output" / "subtitles"
        )

        self.output_root.mkdir(
            parents=True,
            exist_ok=True
        )

        self.default_max_words = 5

    def load_transcript(self, transcript_path):

        transcript_path = Path(transcript_path)

        if not transcript_path.exists():
            raise FileNotFoundError(transcript_path)

        with open(
            transcript_path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    def format_timestamp(self, seconds):

        milliseconds = round(seconds * 1000)

        hours = milliseconds // 3600000
        milliseconds %= 3600000

        minutes = milliseconds // 60000
        milliseconds %= 60000

        secs = milliseconds // 1000
        milliseconds %= 1000

        return (
            f"{hours:02}:"
            f"{minutes:02}:"
            f"{secs:02},"
            f"{milliseconds:03}"
        )

    def extract_clip_words(
        self,
        transcript,
        clip_start,
        clip_end
    ):

        words = []

        for segment in transcript.get("segments", []):

            for word in segment.get("words", []):

                start = float(word["start"])
                end = float(word["end"])

                if end <= clip_start or start >= clip_end:
                    continue

                text = word.get("word", "").strip()

                if not text:
                    continue

                words.append({

                    "word": text,

                    "start": round(
                        max(start, clip_start) - clip_start,
                        3
                    ),

                    "end": round(
                        min(end, clip_end) - clip_start,
                        3
                    )

                })

        words.sort(key=lambda item: item["start"])

        return words

    def group_words(self, words, max_words=5):

        subtitles = []
        current_group = []

        for word in words:

            current_group.append(word)

            text = " ".join(
                item["word"] for item in current_group
            )

            has_punctuation = text.endswith(
                (".", "!", "?", ",", ";", ":")
            )

            if (
                len(current_group) >= max_words
                or has_punctuation
            ):

                subtitles.append(current_group)
                current_group = []

        if current_group:
            subtitles.append(current_group)

        return subtitles

    def build_subtitles(
        self,
        transcript,
        clip_start,
        clip_end,
        max_words=5
    ):

        words = self.extract_clip_words(
            transcript,
            clip_start,
            clip_end
        )

        groups = self.group_words(
            words,
            max_words=max_words
        )

        entries = []

        for group in groups:

            text = " ".join(
                item["word"] for item in group
            ).strip()

            start = group[0]["start"]
            end = group[-1]["end"]

            if not text or end <= start:
                continue

            entries.append({

                "index": len(entries) + 1,

                "start": start,

                "end": end,

                "text": text

            })

        return entries

    def build_animated_subtitles(
        self,
        transcript,
        clip_start,
        clip_end,
        max_words=5
    ):

        words = self.extract_clip_words(
            transcript,
            clip_start,
            clip_end
        )

        groups = self.group_words(
            words,
            max_words=max_words
        )

        captions = []

        for group in groups:

            text = " ".join(
                item["word"] for item in group
            ).strip()

            start = group[0]["start"]
            end = group[-1]["end"]

            if not text or end <= start:
                continue

            animated_words = []

            for word_index, word in enumerate(group):

                animated_words.append({

                    "index": word_index,

                    "text": word["word"],

                    "start": word["start"],

                    "end": word["end"],

                    "highlight": True

                })

            captions.append({

                "index": len(captions) + 1,

                "start": start,

                "end": end,

                "text": text,

                "words": animated_words,

                "style": {

                    "font": "Arial",

                    "font_size": 64,

                    "font_color": "white",

                    "highlight_color": "yellow",

                    "outline_color": "black",

                    "outline_width": 4,

                    "position": "bottom_center"

                },

                "animation": {

                    "type": "word_pop",

                    "duration": 0.15,

                    "highlight_active_word": True

                }

            })

        return {

            "version": 1,

            "clip_start": clip_start,

            "clip_end": clip_end,

            "duration": round(clip_end - clip_start, 3),

            "total_captions": len(captions),

            "captions": captions

        }

    def save_srt(
        self,
        entries,
        filename,
        video_name=None
    ):

        output_dir = self.output_root

        if video_name:
            output_dir = output_dir / video_name

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        output_file = output_dir / filename

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            for entry in entries:

                file.write(f"{entry['index']}\n")

                file.write(
                    f"{self.format_timestamp(entry['start'])}"
                    f" --> "
                    f"{self.format_timestamp(entry['end'])}\n"
                )

                file.write(f"{entry['text']}\n\n")

        return output_file

    def save_animated_json(
        self,
        animated_data,
        filename,
        video_name=None
    ):

        output_dir = self.output_root

        if video_name:
            output_dir = output_dir / video_name

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        output_file = output_dir / filename

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                animated_data,
                file,
                indent=4,
                ensure_ascii=False
            )

        return output_file


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "transcript",
        help="Transcript JSON file"
    )

    parser.add_argument(
        "--start",
        type=float,
        required=True
    )

    parser.add_argument(
        "--end",
        type=float,
        required=True
    )

    parser.add_argument(
        "--video-name",
        default=None
    )

    args = parser.parse_args()

    generator = SubtitleGenerator()

    transcript = generator.load_transcript(
        args.transcript
    )

    entries = generator.build_subtitles(
        transcript,
        args.start,
        args.end
    )

    animated_data = generator.build_animated_subtitles(
        transcript,
        args.start,
        args.end
    )

    video_name = args.video_name

    srt_output = generator.save_srt(
        entries,
        "test_subtitles.srt",
        video_name=video_name
    )

    json_output = generator.save_animated_json(
        animated_data,
        "test_animated_subtitles.json",
        video_name=video_name
    )

    print("\n===== GENERATED SUBTITLES =====")

    for entry in entries:

        print(
            f"{entry['start']:.2f}s - "
            f"{entry['end']:.2f}s: "
            f"{entry['text']}"
        )

    print("\n===== ANIMATED CAPTIONS =====")

    print("Total captions:", animated_data["total_captions"])

    print("\nSRT saved:", srt_output)
    print("Animated JSON saved:", json_output)
