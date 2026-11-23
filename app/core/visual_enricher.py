
import json
import argparse
from pathlib import Path


class VisualEnricher:

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]

    def load_json(self, file_path):

        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def enrich(self, highlights_data, visual_data):

        frames = visual_data.get("frames", [])
        sampling_interval = float(visual_data.get("sampling_interval", 2))
        tolerance = min(5.0, sampling_interval * 0.5)

        enriched_highlights = []

        for highlight in highlights_data.get("highlights", []):

            start = float(highlight["start"])
            end = float(highlight["end"])

            # 1. Match frames strictly inside the highlight window
            matched_frames = [
                frame
                for frame in frames
                if start <= float(frame.get("timestamp", -1)) <= end
            ]

            # 2. If no frames strictly inside, expand by tolerance (for higher sampling intervals)
            if not matched_frames and frames:
                matched_frames = [
                    frame
                    for frame in frames
                    if (start - tolerance) <= float(frame.get("timestamp", -1)) <= (end + tolerance)
                ]

            # 3. If still none, match the single nearest frame within one sampling interval
            if not matched_frames and frames:
                midpoint = (start + end) / 2.0
                closest = min(
                    frames,
                    key=lambda f: abs(float(f.get("timestamp", -999)) - midpoint)
                )
                if abs(float(closest.get("timestamp", -999)) - midpoint) <= sampling_interval:
                    matched_frames = [closest]

            if matched_frames:

                scores = [
                    float(frame["analysis"].get("visual_interest", 0))
                    for frame in matched_frames
                ]

                average_score = round(
                    sum(scores) / len(scores), 2
                )

                maximum_score = max(scores)

                visual_summary = [
                    {
                        "frame": frame["frame"],
                        "timestamp": frame["timestamp"],
                        "scene_description": frame["analysis"].get(
                            "scene_description", ""
                        ),
                        "visual_context": frame["analysis"].get(
                            "visual_context", ""
                        ),
                        "visual_interest": frame["analysis"].get(
                            "visual_interest", 0
                        ),
                        "reason": frame["analysis"].get("reason", "")
                    }
                    for frame in matched_frames
                ]

            else:

                average_score = 0
                maximum_score = 0
                visual_summary = []

            enriched = highlight.copy()

            enriched["visual_analysis"] = {
                "frames_analyzed": len(matched_frames),
                "average_visual_interest": average_score,
                "maximum_visual_interest": maximum_score,
                "frames": visual_summary
            }

            enriched_highlights.append(enriched)

        return {
            "video_duration": highlights_data.get("video_duration"),
            "total_highlights": len(enriched_highlights),
            "visual_sampling_interval": visual_data.get(
                "sampling_interval"
            ),
            "highlights": enriched_highlights
        }

    def run(self, highlight_path, visual_path):

        print("\n===== LOADING HIGHLIGHTS =====")

        highlights_data = self.load_json(highlight_path)

        print("\n===== LOADING VISUAL ANALYSIS =====")

        visual_data = self.load_json(visual_path)

        print("\n===== ENRICHING HIGHLIGHTS =====")

        enriched_data = self.enrich(
            highlights_data,
            visual_data
        )

        output_dir = self.project_root / "output" / "enriched"
        output_dir.mkdir(parents=True, exist_ok=True)

        video_name = Path(highlight_path).stem.replace(
            "_highlights", ""
        )

        output_path = output_dir / f"{video_name}_enriched.json"

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(
                enriched_data,
                file,
                indent=4,
                ensure_ascii=False
            )

        print("\n===== ENRICHMENT SUMMARY =====")

        for index, highlight in enumerate(
            enriched_data["highlights"], start=1
        ):

            visual = highlight["visual_analysis"]

            print(f"\nHighlight #{index}")
            print(f"Title: {highlight['title']}")
            print(f"Frames matched: {visual['frames_analyzed']}")
            print(
                f"Average visual interest: "
                f"{visual['average_visual_interest']}/10"
            )

        print(f"\nSaved: {output_path}")

        return enriched_data


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Enrich AI highlights with visual analysis."
    )

    parser.add_argument("highlight_json")
    parser.add_argument("visual_json")

    args = parser.parse_args()

    enricher = VisualEnricher()

    enricher.run(
        args.highlight_json,
        args.visual_json
    )
