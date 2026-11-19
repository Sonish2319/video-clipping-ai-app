
import json
from pathlib import Path


class ContextBuilder:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]

    def build_context(self, transcript_path, visual_analysis_path):
        transcript_file = Path(transcript_path)
        visual_file = Path(visual_analysis_path)

        if not transcript_file.is_absolute():
            transcript_file = self.project_root / transcript_file

        if not visual_file.is_absolute():
            visual_file = self.project_root / visual_file

        with open(transcript_file, "r", encoding="utf-8") as file:
            transcript_data = json.load(file)

        with open(visual_file, "r", encoding="utf-8") as file:
            visual_data = json.load(file)

        context = {
            "video_duration": transcript_data.get("duration"),
            "transcript_segments": transcript_data.get("segments", []),
            "visual_frames": []
        }

        for frame in visual_data.get("frames", []):
            analysis = frame.get("analysis")

            if not analysis:
                continue

            context["visual_frames"].append({
                "timestamp": frame.get("timestamp"),
                "scene_description": analysis.get("scene_description", ""),
                "people": analysis.get("people", []),
                "objects": analysis.get("objects", []),
                "visual_context": analysis.get("visual_context", ""),
                "visual_interest": analysis.get("visual_interest", 0),
                "reason": analysis.get("reason", "")
            })

        return context

    def save_context(self, context, output_path):
        output_file = Path(output_path)

        if not output_file.is_absolute():
            output_file = self.project_root / output_file

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(context, file, indent=4, ensure_ascii=False)

        print(f"Combined context saved: {output_file}")

    def process(self, transcript_path, visual_analysis_path):
        context = self.build_context(
            transcript_path,
            visual_analysis_path
        )

        video_name = Path(transcript_path).stem
        output_path = (
            self.project_root
            / "output"
            / "context"
            / f"{video_name}_context.json"
        )

        self.save_context(context, output_path)

        print(f"Transcript segments: {len(context['transcript_segments'])}")
        print(f"Visual frames: {len(context['visual_frames'])}")

        return context


if __name__ == "__main__":
    builder = ContextBuilder()

    builder.process(
        "output/transcripts/test_video_with_speech.json",
        "output/visual_analysis/test_video_with_speech_visual_analysis.json"
    )
