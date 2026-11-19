
import json
import argparse
import re
from pathlib import Path


class VisualSelector:

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]

        # Selection limits
        self.minimum_relevance = 7
        self.minimum_topic_match = 6
        self.maximum_frames = 3

        # Diversity controls
        self.minimum_frame_spacing = 4
        self.similarity_threshold = 0.55

        self.stopwords = {
            "the", "a", "an", "and", "or", "of", "in", "on",
            "at", "to", "with", "from", "is", "are", "this",
            "that", "it", "its", "shows", "showing", "visible"
        }

    def calculate_score(self, frame):

        topic = frame.get("topic_match_score", 0)
        context = frame.get("contextual_match_score", 0)
        contradiction = frame.get("visual_contradiction_score", 10)

        # Direct topic evidence receives the highest weight.
        score = (
            (topic * 0.65) +
            (context * 0.25) +
            ((10 - contradiction) * 0.10)
        )

        return round(score, 2)

    def is_valid(self, frame):

        return (
            frame.get("relevance_score", 0) >= self.minimum_relevance
            and frame.get("topic_match_score", 0) >= self.minimum_topic_match
            and frame.get("visual_contradiction_score", 10) <= 3
        )


    def get_scene_text(self, frame):

        # Support both original visual-analysis structure
        # and semantic-relevance result structure.
        frame_data = frame.get("analysis", frame)

        parts = []

        for key in (
            "scene_description",
            "visual_context"
        ):
            value = frame_data.get(key)

            if isinstance(value, str):
                parts.append(value)

        for key in ("objects", "people"):

            values = frame_data.get(key, [])

            if isinstance(values, list):
                parts.extend(str(item) for item in values)

        return " ".join(parts).lower()


    def get_scene_tokens(self, frame):

        text = self.get_scene_text(frame)

        words = re.findall(r"\b[a-z0-9]+\b", text)

        return {
            word for word in words
            if len(word) > 2 and word not in self.stopwords
        }


    def are_scenes_similar(self, frame_a, frame_b):

        tokens_a = self.get_scene_tokens(frame_a)
        tokens_b = self.get_scene_tokens(frame_b)

        # Without actual visual descriptions, rely on timestamp spacing.
        if not tokens_a or not tokens_b:
            return False

        # Jaccard similarity compares shared visual-description terms.
        intersection = len(tokens_a.intersection(tokens_b))
        union = len(tokens_a.union(tokens_b))

        if union == 0:
            return False

        similarity = intersection / union

        return similarity >= self.similarity_threshold


    def is_too_close(self, candidate, selected):

        candidate_time = candidate.get("timestamp", 0)

        return any(
            abs(
                candidate_time - existing.get("timestamp", 0)
            ) < self.minimum_frame_spacing
            for existing in selected
        )

    def select_frames(self, frames):

        candidates = []

        for frame in frames:

            if not self.is_valid(frame):
                continue

            frame_copy = frame.copy()
            frame_copy["selection_score"] = self.calculate_score(frame)

            candidates.append(frame_copy)

        # Strongest direct topic matches are considered first.
        candidates.sort(
            key=lambda frame: (
                frame["selection_score"],
                frame.get("topic_match_score", 0),
                frame.get("relevance_score", 0)
            ),
            reverse=True
        )

        selected = []

        for candidate in candidates:

            if len(selected) >= self.maximum_frames:
                break

            # Avoid frames from nearly identical timestamps.
            if self.is_too_close(candidate, selected):
                continue

            # Avoid selecting visually repetitive scenes.
            visually_repetitive = any(
                self.are_scenes_similar(candidate, existing)
                for existing in selected
            )

            if visually_repetitive:
                continue

            selected.append(candidate)

        return selected

    def run(self, input_path):

        input_path = Path(input_path)

        print("\n===== LOADING SEMANTIC VISUAL ANALYSIS =====")

        with open(input_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        print("\n===== SELECTING DIVERSE VISUAL FRAMES =====")

        total_selected = 0

        for highlight in data.get("highlights", []):

            visual_analysis = highlight.get("visual_analysis", {})

            frames = (
                visual_analysis
                .get("semantic_relevance", {})
                .get("results", [])
            )

            selected = self.select_frames(frames)

            highlight["selected_visuals"] = {
                "total_evaluated": len(frames),
                "total_selected": len(selected),
                "frames": selected
            }

            total_selected += len(selected)

            print(f"\nHighlight: {highlight.get('title')}")

            print(
                f"  Evaluated: {len(frames)} | "
                f"Selected: {len(selected)}"
            )

            for frame in selected:

                print(
                    f"  {frame.get('frame')} | "
                    f"Time: {frame.get('timestamp')}s | "
                    f"Topic: {frame.get('topic_match_score')}/10 | "
                    f"Score: {frame.get('selection_score')}"
                )

        video_name = input_path.stem.replace("_semantic", "")

        output_dir = self.project_root / "output" / "selected_visuals"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{video_name}_selected_visuals.json"

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        print("\n===== SELECTION COMPLETED =====")
        print(f"Total selected frames: {total_selected}")
        print(f"Saved: {output_path}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Select relevant and visually diverse frames for each highlight."
    )

    parser.add_argument(
        "input",
        help="Path to semantic visual analysis JSON"
    )

    args = parser.parse_args()

    selector = VisualSelector()
    selector.run(args.input)
