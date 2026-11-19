
import argparse
import json
import re
from pathlib import Path

from clip_generator import ClipGenerator
from video_formatter import VideoFormatter
from subtitle_generator import SubtitleGenerator
from subtitle_burner import SubtitleBurner
from broll_composer import BrollComposer
from animated_subtitle_renderer import AnimatedSubtitleRenderer


class ClipPipeline:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.transcript_dir = (
            self.project_root / "output" / "transcripts"
        )

        self.highlight_dir = (
            self.project_root / "output" / "highlights"
        )

        self.subtitle_generator = SubtitleGenerator()
        self.video_formatter = VideoFormatter()
        self.subtitle_burner = SubtitleBurner()
        self.broll_composer = BrollComposer()

        self.animated_subtitle_renderer = (
            AnimatedSubtitleRenderer()
        )

        self.clip_generator = ClipGenerator()

    def clean_filename(self, value):

        value = re.sub(r'[<>:"/\\|?*]', "", value)
        value = re.sub(r"\s+", "_", value.strip())

        return value[:60] or "highlight"

    def verify_output(self, path, step_name):

        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(
                f"{step_name} did not produce an output file: {path}"
            )

        if path.stat().st_size == 0:
            raise RuntimeError(
                f"{step_name} produced an empty file: {path}"
            )

        return path

    def run(self, video_path, transcript_path, highlights_path):

        video_path = Path(video_path).resolve()
        transcript_path = Path(transcript_path).resolve()
        highlights_path = Path(highlights_path).resolve()

        for path in [video_path, transcript_path, highlights_path]:
            if not path.exists():
                raise FileNotFoundError(path)

        video_name = video_path.stem

        with open(transcript_path, "r", encoding="utf-8") as file:
            transcript = json.load(file)

        with open(highlights_path, "r", encoding="utf-8") as file:
            highlights = json.load(file)

        print(f"\nSOURCE VIDEO: {video_name}")

        # STEP 1: CLIP EXTRACTION
        print("\n===== STEP 1: CLIP EXTRACTION =====")

        clips = self.clip_generator.generate(
            str(video_path),
            highlights
        )

        if not clips:
            print("No clips generated.")
            return []

        final_results = []

        for index, clip in enumerate(clips, start=1):

            print(
                f"\n===== PROCESSING CLIP {index}/{len(clips)} ====="
            )

            clip_name = Path(clip["filename"]).stem
            safe_name = self.clean_filename(clip_name)

            # STEP 2: B-ROLL COMPOSITION
            print("\nSTEP 2: B-ROLL COMPOSITION")

            source_clip_path = self.verify_output(
                clip["path"],
                "Clip extraction"
            )

            selected_visuals = clip.get("selected_visuals", [])

            broll_path = self.broll_composer.compose(
                clip_path=str(source_clip_path),
                selected_visuals=selected_visuals,
                clip_start=clip["start"],
                video_name=video_name
            )

            broll_path = self.verify_output(
                broll_path,
                "B-roll composition"
            )

            print(f"B-roll video: {broll_path}")

            # STEP 3: VERTICAL FORMATTING
            print("\nSTEP 3: VERTICAL FORMATTING")

            vertical_name = f"{safe_name}_vertical.mp4"

            vertical_path = self.video_formatter.format_video(
                str(broll_path),
                vertical_name,
                mode="blur",
                video_name=video_name
            )

            vertical_path = self.verify_output(
                vertical_path,
                "Vertical formatting"
            )

            # STEP 4: STANDARD SUBTITLE GENERATION
            print("\nSTEP 4: STANDARD SUBTITLE GENERATION")

            entries = self.subtitle_generator.build_subtitles(
                transcript,
                clip["start"],
                clip["end"]
            )

            subtitle_name = f"{safe_name}.srt"

            subtitle_path = self.subtitle_generator.save_srt(
                entries,
                subtitle_name,
                video_name=video_name
            )

            subtitle_path = self.verify_output(
                subtitle_path,
                "Subtitle generation"
            )

            # STEP 5: ANIMATED CAPTION DATA GENERATION
            print("\nSTEP 5: ANIMATED CAPTION GENERATION")

            animated_data = (
                self.subtitle_generator.build_animated_subtitles(
                    transcript,
                    clip["start"],
                    clip["end"]
                )
            )

            animated_json_name = (
                f"{safe_name}_animated.json"
            )

            animated_json_path = (
                self.subtitle_generator.save_animated_json(
                    animated_data,
                    animated_json_name,
                    video_name=video_name
                )
            )

            animated_json_path = self.verify_output(
                animated_json_path,
                "Animated caption generation"
            )

            # STEP 6: ANIMATED SUBTITLE RENDERING
            print("\nSTEP 6: ANIMATED SUBTITLE RENDERING")

            final_name = f"{safe_name}_final.mp4"

            final_path = self.animated_subtitle_renderer.render(
                str(vertical_path),
                str(animated_json_path),
                final_name
            )

            final_path = self.verify_output(
                final_path,
                "Animated subtitle rendering"
            )

            # COLLECT RESULTS
            final_results.append({

                "source_video": video_name,

                "title": clip.get("title", safe_name),

                "source_clip": str(source_clip_path),

                "start": clip["start"],

                "end": clip["end"],

                "duration": clip["duration"],

                "transcript": clip.get("transcript", ""),

                "category": clip.get("category"),

                "score": clip.get("score"),

                "selected_visuals": selected_visuals,

                "total_selected_visuals": clip.get(
                    "total_selected_visuals",
                    len(selected_visuals)
                ),

                "broll_video": str(broll_path),

                "vertical_video": str(vertical_path),

                "subtitle_file": str(subtitle_path),

                "animated_subtitle_file": str(animated_json_path),

                "final_video": str(final_path)

            })

        # STEP 7: SAVE PIPELINE RESULTS
        print("\n===== SAVING PIPELINE RESULTS =====")

        results_dir = (
            self.project_root / "output" / "pipeline_results"
        )

        results_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        results_path = (
            results_dir / f"{video_name}_pipeline_results.json"
        )

        with open(
            results_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "source_video": video_name,
                    "transcript_file": str(transcript_path),
                    "highlights_file": str(highlights_path),
                    "total_clips": len(final_results),
                    "results": final_results
                },
                file,
                indent=4,
                ensure_ascii=False
            )

        print("\n===== PIPELINE RESULTS SAVED =====")
        print(results_path)

        print("\n===== PIPELINE COMPLETED =====")
        print(f"Source video: {video_name}")
        print(f"Total final videos: {len(final_results)}")

        return final_results


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Local AI Video Clipping Pipeline"
    )

    parser.add_argument("video")
    parser.add_argument("transcript")
    parser.add_argument("highlights")

    args = parser.parse_args()

    pipeline = ClipPipeline()

    print("\n===================================")
    print(" LOCAL AI VIDEO CLIPPING PIPELINE")
    print("===================================")

    results = pipeline.run(
        args.video,
        args.transcript,
        args.highlights
    )

    print("\n===== FINAL PRODUCTION SUMMARY =====")

    print("Total final videos:", len(results))

    for result in results:

        print("\nTitle:", result["title"])
        print("Final video:", result["final_video"])
        print("Duration:", result["duration"])
        print("Category:", result["category"])
        print("Score:", result["score"])
        print("B-roll:", result["broll_video"])

    print("\nPipeline completed.")
