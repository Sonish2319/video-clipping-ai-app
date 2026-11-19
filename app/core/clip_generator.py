
import json
import re
import shutil
from pathlib import Path

from video_processor import VideoProcessor


class ClipGenerator:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.output_dir = (
            self.project_root / "output" / "clips"
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.video_processor = VideoProcessor()

    def load_highlights(self, highlights_path):

        highlights_path = Path(highlights_path)

        if not highlights_path.exists():
            raise FileNotFoundError(highlights_path)

        with open(
            highlights_path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    def clean_filename(self, value):

        value = re.sub(
            r'[<>:"/\\|?*]',
            "",
            value
        )

        value = re.sub(
            r"\s+",
            "_",
            value.strip()
        )

        return value[:70] or "highlight"

    def get_selected_visuals(self, highlight):

        selected_visuals = highlight.get(
            "selected_visuals",
            {}
        )

        frames = selected_visuals.get("frames", [])

        result = []

        for frame in frames:

            result.append({
                "frame": frame.get("frame"),
                "timestamp": frame.get("timestamp"),
                "topic_match_score": frame.get("topic_match_score"),
                "contextual_match_score": frame.get("contextual_match_score"),
                "visual_contradiction_score": frame.get("visual_contradiction_score"),
                "relevance_score": frame.get("relevance_score"),
                "selection_score": frame.get("selection_score"),
                "explanation": frame.get("explanation")
            })

        return result

    def generate(self, video_path, highlights):

        video_path = Path(video_path).resolve()

        if not video_path.exists():
            raise FileNotFoundError(video_path)

        video_output_dir = self.output_dir / video_path.stem

        video_output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        metadata = self.video_processor.get_metadata(
            str(video_path)
        )

        video_duration = float(metadata["duration"])

        generated_clips = []

        for index, highlight in enumerate(
            highlights.get("highlights", []),
            start=1
        ):

            start = float(highlight["start"])
            end = float(highlight["end"])

            if start < 0 or end <= start:
                print(f"Skipping invalid highlight #{index}")
                continue

            if end > video_duration:
                print(f"Skipping out-of-range highlight #{index}")
                continue

            title = self.clean_filename(
                highlight.get("title", f"highlight_{index}")
            )

            filename = f"{index:02d}_{title}.mp4"

            output_path = video_output_dir / filename

            print(f"\nGenerating clip #{index}")
            print("Title:", highlight.get("title"))
            print(f"Time: {start:.2f}s - {end:.2f}s")

            self.video_processor.extract_clip(
                str(video_path),
                start,
                end,
                filename
            )

            generated_path = self.output_dir / filename

            if not generated_path.exists():
                raise FileNotFoundError(
                    f"Generated clip not found: {generated_path}"
                )

            shutil.move(
                str(generated_path),
                str(output_path)
            )

            clip_metadata = self.video_processor.get_metadata(
                str(output_path)
            )

            selected_visuals = self.get_selected_visuals(
                highlight
            )

            clip_result = {
                "filename": filename,
                "path": str(output_path),
                "title": highlight.get("title"),
                "start": start,
                "end": end,
                "duration": clip_metadata["duration"],
                "category": highlight.get("category"),
                "score": highlight.get("score"),
                "transcript": highlight.get("transcript", ""),
                "selected_visuals": selected_visuals,
                "total_selected_visuals": len(selected_visuals)
            }

            generated_clips.append(clip_result)

            print("Generated:", output_path)
            print("Selected visuals:", len(selected_visuals))

            for frame in selected_visuals:

                print(
                    f"  {frame['frame']} | "
                    f"Time: {frame['timestamp']}s | "
                    f"Relevance: {frame['relevance_score']}/10"
                )

        return generated_clips


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "video",
        help="Original video path"
    )

    parser.add_argument(
        "highlights",
        help="Selected visuals JSON path"
    )

    args = parser.parse_args()

    generator = ClipGenerator()

    print("\n===== LOADING SELECTED HIGHLIGHTS =====")

    highlights = generator.load_highlights(
        args.highlights
    )

    print(
        "Total highlights:",
        highlights.get("total_highlights", 0)
    )

    print("\n===== GENERATING VIDEO CLIPS =====")

    clips = generator.generate(
        args.video,
        highlights
    )

    print("\n===== GENERATION SUMMARY =====")

    print("Generated clips:", len(clips))

    for clip in clips:

        print("\nFile:", clip["filename"])
        print("Duration:", clip["duration"])
        print("Category:", clip["category"])
        print("Score:", clip["score"])
        print("Selected visuals:", clip["total_selected_visuals"])

    print("\nClip generation completed.")
