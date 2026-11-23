
import json
import argparse
from pathlib import Path

from llm_client import OllamaClient
# from app.core.llm_client import OllamaClient


class VisualRelevanceAnalyzer:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]
        self.llm = OllamaClient()


    def build_prompt(self, highlight, frame):

        frame_data = frame.get("analysis", frame)

        return f"""
        You are an expert video editor and visual relevance evaluator.

        Your task is to determine how accurately a video frame visually
        supports the spoken content of a highlight.

        Evaluate ONLY the evidence provided in the frame information.
        Do not invent objects, landmarks, locations, or relationships.

        HIGHLIGHT TITLE:
        {highlight['title']}

        SPOKEN CONTENT:
        {highlight['transcript']}

        FRAME INFORMATION:

        Scene description:
        {frame_data.get('scene_description', '')}

        Visual context:
        {frame_data.get('visual_context', '')}

        Visible objects:
        {json.dumps(frame_data.get('objects', []), ensure_ascii=False)}

        People:
        {json.dumps(frame_data.get('people', []), ensure_ascii=False)}

        ==================================================
        EVALUATION DIMENSIONS
        ==================================================

        DIMENSION 1: TOPIC MATCH

        Evaluate how directly the visible content represents
        the actual subject discussed in the speech.

        0-2: No visible connection to the main topic.
        3-5: Weak or partial representation.
        6-8: Clear visual representation of the topic.
        9-10: Direct and unmistakable representation.

        IMPORTANT:
        - Base this score purely on what is visibly present in the frame.
        - Superficial or accidental similarity does not mean a topic match.
        - In talking-head or podcast videos, the speaker visible on camera talking provides a natural anchor, but topic_match_score measures whether the specific topic/entity being talked about is shown.
        - Generic scenery or unrelated backgrounds without visible connection must receive low topic match scores (0-3).

        DIMENSION 2: CONTEXTUAL MATCH

        Evaluate whether the frame provides useful supporting
        visual context for the spoken content.

        0-2: No useful contextual connection.
        3-5: General background or indirect association.
        6-8: Strong supporting context (e.g., studio setting supporting a conversation, screen recording supporting a tech demo, gym setting supporting fitness).
        9-10: Highly relevant contextual representation.

        Consider geographical, historical, cultural, environmental,
        and situational context ONLY when supported by visible evidence.

        DIMENSION 3: VISUAL CONTRADICTION

        Determine whether the visible content conflicts with
        or misrepresents the spoken topic.

        0-2: No meaningful contradiction.
        3-5: Some misleading or questionable visual information.
        6-8: Strong contradiction.
        9-10: Completely misleading or contradictory visuals.

        ==================================================
        OVERALL RELEVANCE
        ==================================================

        Give one overall relevance score from 0 to 10.

        Consider:
        - Direct topic match.
        - Useful contextual support.
        - Visual contradictions.
        - Whether the visible evidence genuinely supports the speech.

        A frame may be contextually relevant without directly
        showing the exact subject.

        However, contextual relevance must be supported by
        identifiable visual evidence, not assumptions.

        ==================================================
        STRICT VISUAL EVIDENCE RULES
        ==================================================

        1. Similar appearance does not mean identical subject.

        2. Cultural association alone is insufficient.

        3. General geographical scenery cannot prove historical claims.

        4. Evaluate the actual visible subject, not assumptions
        about the location.

        5. Do not trust a visual_context description blindly.
        Cross-check it against the scene description and
        visible objects.

        6. Do not treat a text overlay as proof that the
        underlying scene represents that topic.

        7. A frame may support one part of a highlight without
        supporting the entire highlight.

        8. If the frame does not show the actual subject,
        keep topic_match_score low even when contextual
        relevance is moderate or high.

        9. Never give a high score simply because the frame
        looks attractive, culturally interesting, or cinematic.

        10. If evidence is uncertain, use a lower score and
            explain what cannot be confirmed.

        ==================================================
        UNIVERSAL EXAMPLES ACROSS VIDEO GENRES
        ==================================================

        1. Educational / Tech Tutorial:
           Speech: "Using Python list comprehensions to filter data efficiently."
           Visual: Screen capture showing Python code in an editor.
           -> High topic match (9-10), high contextual match (9-10), contradiction: 0.

        2. Podcast / Interview Discussion:
           Speech: "Building consistent habits requires doing 10 minutes every single day."
           Visual: Host and guest speaking at a table with studio microphones.
           -> Moderate topic match (3-4), high contextual match (7-8), contradiction: 0.

        3. Misleading / Unrelated Scenery:
           Speech: "The company reported quarterly revenue growth in European markets."
           Visual: Unrelated mountain landscape with clouds.
           -> Low topic match (0-1), low contextual match (1-2), contradiction: 3.

        4. Practical Demonstration:
           Speech: "Keep your back straight and feet shoulder-width apart when squatting."
           Visual: Trainer demonstrating squat form in an exercise studio.
           -> High topic match (9-10), high contextual match (9-10), contradiction: 0.

        5. Documentary / Archival:
           Speech: "The historic treaty was signed in the grand hall of the palace."
           Visual: Historical photograph or footage of leaders inside the ornate hall.
           -> High topic match (8-9), high contextual match (9-10), contradiction: 0.

        ==================================================
        OUTPUT REQUIREMENTS
        ==================================================

        Return ONLY valid JSON.

        All scores must be integers from 0 to 10.

        The explanation must:
        - Identify the actual visible evidence.
        - Explain how it relates to the spoken topic.
        - Distinguish direct evidence from contextual evidence.
        - Mention uncertainty or unsupported assumptions.
        - Never claim an object or landmark is visible unless
        the supplied frame information supports that claim.

        JSON FORMAT:

        {{
            "topic_match_score": 0,
            "contextual_match_score": 0,
            "visual_contradiction_score": 0,
            "relevance_score": 0,
            "explanation": "Explain the visual evidence and scoring."
        }}
        """



    def analyze_frame(self, highlight, frame):

        prompt = self.build_prompt(highlight, frame)

        result = self.llm.generate_json(prompt)

        topic_score = max(
            0, min(10, int(result.get("topic_match_score", 0)))
        )

        context_score = max(
            0, min(10, int(result.get("contextual_match_score", 0)))
        )

        contradiction_score = max(
            0, min(10, int(result.get("visual_contradiction_score", 0)))
        )

        relevance_score = max(
            0, min(10, int(result.get("relevance_score", 0)))
        )

        return {
            "frame": frame.get("frame"),
            "timestamp": frame.get("timestamp"),

            "topic_match_score": topic_score,
            "contextual_match_score": context_score,
            "visual_contradiction_score": contradiction_score,

            "relevance_score": relevance_score,
            "is_relevant": relevance_score >= 7,

            "explanation": result.get("explanation", "")
        }


    def enrich(self, data):

        for highlight in data.get("highlights", []):

            print(f"\nAnalyzing: {highlight['title']}")

            frames = highlight.get(
                "visual_analysis", {}
            ).get("frames", [])

            relevance_results = []

            for index, frame in enumerate(frames, start=1):

                print(
                    f"  Frame {index}/{len(frames)}: "
                    f"{frame.get('frame')}"
                )

                try:

                    result = self.analyze_frame(
                        highlight,
                        frame
                    )

                    relevance_results.append(result)

                    print(
                        f"    Relevance: "
                        f"{result['relevance_score']}/10"
                    )

                except Exception as error:

                    print(f"    Analysis failed: {error}")

            scores = [
                item["relevance_score"]
                for item in relevance_results
            ]

            average_score = (
                round(sum(scores) / len(scores), 2)
                if scores else 0
            )

            relevant_frames = [
                item
                for item in relevance_results
                if item["is_relevant"]
            ]

            highlight["visual_analysis"]["semantic_relevance"] = {
                "frames_evaluated": len(relevance_results),
                "relevant_frames": len(relevant_frames),
                "average_relevance_score": average_score,
                "results": relevance_results
            }

        return data

    def run(self, input_path):

        print("\n===== LOADING ENRICHED HIGHLIGHTS =====")

        with open(input_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        print("\n===== ANALYZING SEMANTIC VISUAL RELEVANCE =====")

        enriched_data = self.enrich(data)

        output_dir = self.project_root / "output" / "enriched"
        output_dir.mkdir(parents=True, exist_ok=True)

        video_name = Path(input_path).stem.replace(
            "_enriched", ""
        )

        output_path = output_dir / f"{video_name}_semantic.json"

        with open(output_path, "w", encoding="utf-8") as file:

            json.dump(
                enriched_data,
                file,
                indent=4,
                ensure_ascii=False
            )

        print("\n===== ANALYSIS COMPLETED =====")
        print(f"Saved: {output_path}")

        return enriched_data


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Analyze semantic relevance of video frames."
    )

    parser.add_argument("input_json")

    args = parser.parse_args()

    analyzer = VisualRelevanceAnalyzer()

    analyzer.run(args.input_json)
