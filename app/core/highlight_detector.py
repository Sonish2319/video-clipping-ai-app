
import json
from pathlib import Path

from llm_client import OllamaClient


class HighlightDetector:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.transcript_dir = self.project_root / "output" / "transcripts"
        self.visual_dir = self.project_root / "output" / "visual_analysis"
        self.highlight_dir = self.project_root / "output" / "highlights"

        self.highlight_dir.mkdir(parents=True, exist_ok=True)

        self.llm = OllamaClient()

    def load_json(self, file_path):

        file_path = Path(file_path)

        if not file_path.is_absolute():
            file_path = self.project_root / file_path

        if not file_path.exists():
            raise FileNotFoundError(file_path)

        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def load_transcript(self, transcript_path):
        return self.load_json(transcript_path)

    def load_visual_analysis(self, visual_path):

        if not visual_path:
            return None

        return self.load_json(visual_path)

   
    # def build_prompt(self, transcript, visual_analysis=None):

    #     segments = transcript.get("segments", [])

    #     transcript_text = [
    #         {
    #             "start": segment["start"],
    #             "end": segment["end"],
    #             "text": segment["text"]
    #         }
    #         for segment in segments
    #     ]

    #     visual_frames = []

    #     if visual_analysis:
    #         for frame in visual_analysis.get("frames", []):

    #             analysis = frame.get("analysis")

    #             if not analysis:
    #                 continue

    #             visual_frames.append({
    #                 "timestamp": frame.get("timestamp"),
    #                 "scene_description": analysis.get(
    #                     "scene_description", ""
    #                 ),
    #                 "visual_context": analysis.get(
    #                     "visual_context", ""
    #                 ),
    #                 "people": analysis.get("people", []),
    #                 "objects": analysis.get("objects", []),
    #                 "visual_interest": analysis.get(
    #                     "visual_interest", 0
    #                 )
    #             })

    #     prompt = f"""
    # You are an expert short-form video editor and spoken-content analyst.

    # Your PRIMARY task is to identify engaging video highlights
    # from the actual spoken transcript.

    # Visual information is SECONDARY and must never determine
    # what the speaker is supposedly discussing.

    # VIDEO DURATION:
    # {transcript.get("duration", 0)} seconds

    # SPOKEN TRANSCRIPT WITH TIMESTAMPS:
    # {json.dumps(transcript_text, ensure_ascii=False)}

    # VISUAL ANALYSIS WITH TIMESTAMPS:
    # {json.dumps(visual_frames, ensure_ascii=False)}

    # IMPORTANT: FOLLOW THESE STAGES IN ORDER.

    # STAGE 1 — TRANSCRIPT-ONLY ANALYSIS

    # First, analyze ONLY the spoken transcript.

    # Identify moments containing:

    # - Interesting facts or surprising information.
    # - Strong opinions or memorable statements.
    # - Humor and entertaining moments.
    # - Emotional or motivational content.
    # - Useful educational explanations.
    # - Questions followed by interesting answers.
    # - Strong storytelling and engaging conclusions.
    # - Complete thoughts that can stand alone.

    # For every candidate, determine:

    # - What is the speaker actually discussing?
    # - Why would someone watch this moment?
    # - Does the moment contain a complete and understandable thought?
    # - Which transcript segments contain the moment?

    # Generate the title and reason exclusively from the actual speech.

    # STAGE 2 — VISUAL ENRICHMENT

    # After identifying transcript-based candidates, inspect the visual frames.

    # Use visuals only to determine:

    # - What is visibly present during the candidate's timestamps?
    # - Whether the visuals support the spoken topic.
    # - Whether the visuals make the clip more engaging.
    # - Whether the visual context adds useful information.

    # Never change the spoken topic based on visual appearance.

    # For example:

    # If the speaker discusses Mount Everest while a stupa
    # appears on screen, the highlight must discuss Mount Everest.

    # Do not create a stupa-related title or explanation.

    # STAGE 3 — STRICT GROUNDING

    # Follow these rules:

    # 1. Every highlight must originate from actual transcript segments.
    # 2. The title must accurately describe the spoken topic.
    # 3. The reason must be supported by the actual speech.
    # 4. The transcript field must contain only actual supplied transcript words.
    # 5. Never invent quotations or spoken explanations.
    # 6. Never assume the speaker discusses something simply because it appears on screen.
    # 7. Never combine unrelated speech and visual scenes.
    # 8. Use actual transcript timestamps for clip boundaries.
    # 9. Never invent historical, spiritual, cultural, or factual explanations.
    # 10. If speech and visuals conflict, prioritize speech completely.

    # STAGE 4 — CLIP QUALITY

    # - Prefer complete thoughts rather than incomplete sentences.
    # - Generally prefer clips between 10 and 60 seconds.
    # - For shorter videos, select shorter meaningful moments.
    # - Avoid duplicate or nearly identical highlights.
    # - Do not include long periods of silence.
    # - A highlight must provide value independently of the full video.
    # - Return an empty array if no meaningful moment exists.

    # STAGE 5 — SCORING

    # Evaluate each highlight:

    # 1. Spoken content quality (40%):
    # Interesting, useful, emotional, funny, or memorable speech.

    # 2. Visual interest (25%):
    # Visually engaging and relevant sampled frames.

    # 3. Speech-visual relevance (25%):
    # Whether visuals support the actual spoken topic.

    # 4. Standalone clip potential (10%):
    # Whether viewers can understand the clip independently.

    # Calculate a weighted score from 1 to 10.

    # If visuals are unrelated or unavailable, do not artificially
    # increase the score.

    # A visually simple but valuable spoken explanation
    # can still receive a strong score.

    # Return the overall score as an integer from 1 to 10.

    # OUTPUT FORMAT:

    # Return valid JSON using exactly this structure:

    # {{
    #     "highlights": [
    #         {{
    #             "start": 0.0,
    #             "end": 20.0,
    #             "title": "A title describing the actual spoken topic",
    #             "reason": "Why this spoken moment is worth clipping",
    #             "category": "educational",
    #             "score": 8,
    #             "transcript": "The relevant actual spoken words"
    #         }}
    #     ]
    # }}

    # Allowed categories:
    # educational, funny, emotional, motivational,
    # informative, storytelling, opinion, other

    # Return JSON only.
    # """

    #     return prompt



    def build_prompt(self, transcript, visual_analysis=None):

        segments = transcript.get("segments", [])

        transcript_text = [
            {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"]
            }
            for segment in segments
        ]

        prompt = f"""
    You are an expert short-form video editor.

    Your task is to identify engaging video highlights
    STRICTLY from the spoken transcript.

    You must completely ignore visual information.
    Do not infer topics from images, scenes, objects, or surroundings.

    VIDEO DURATION:
    {transcript.get("duration", 0)} seconds

    SPOKEN TRANSCRIPT WITH TIMESTAMPS:
    {json.dumps(transcript_text, ensure_ascii=False)}

    ANALYSIS INSTRUCTIONS:

    1. Read and understand the complete transcript.
    2. Identify interesting and engaging spoken moments.
    3. Select moments containing:
    - Interesting facts or surprising information.
    - Strong opinions or memorable statements.
    - Humor and entertaining moments.
    - Emotional or motivational content.
    - Useful educational explanations.
    - Interesting storytelling.
    - Questions followed by meaningful answers.
    4. Every title must describe the actual spoken topic.
    5. Every reason must be supported by actual spoken words.
    6. The transcript field must contain only words from the supplied transcript.
    7. Never invent facts, quotations, or explanations.
    8. Use actual transcript timestamps.
    9. Prefer complete thoughts and standalone moments.
    10. Avoid duplicate or nearly identical highlights.
    11. Generally prefer clips between 10 and 60 seconds.
    12. Return shorter meaningful moments for shorter videos.
    13. Return an empty highlights array if nothing is worth clipping.

    SCORING:

    Evaluate each highlight:

    - Spoken content quality: 60%
    - Educational or entertainment value: 20%
    - Standalone clip potential: 20%

    Return an integer score from 1 to 10.

    OUTPUT FORMAT:

    {{
        "highlights": [
            {{
                "start": 0.0,
                "end": 20.0,
                "title": "A title describing the actual spoken topic",
                "reason": "Why this spoken moment is worth clipping",
                "category": "educational",
                "score": 8,
                "transcript": "Actual spoken words"
            }}
        ]
    }}

    Allowed categories:
    educational, funny, emotional, motivational,
    informative, storytelling, opinion, other

    Return valid JSON only.
    """

        return prompt



    def validate_highlights(self, result, duration):

        if not isinstance(result, dict):
            raise ValueError("AI response must be a JSON object.")

        highlights = result.get("highlights")

        if not isinstance(highlights, list):
            raise ValueError("Missing highlights list.")

        validated = []

        for item in highlights:

            try:

                start = float(item["start"])
                end = float(item["end"])
                score = int(item["score"])

                if start < 0 or end <= start:
                    continue

                if end > duration:
                    continue

                if not 1 <= score <= 10:
                    continue

                validated.append({
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "title": str(item["title"]),
                    "reason": str(item["reason"]),
                    "category": str(item["category"]).lower(),
                    "score": score,
                    "transcript": str(item["transcript"])
                })

            except (KeyError, TypeError, ValueError):
                continue

        return sorted(
            validated,
            key=lambda item: item["score"],
            reverse=True
        )

    

    def ground_highlights(self, highlights, transcript):

        segments = transcript.get("segments", [])
        grounded = []

        continuation_words = {
            "who", "which", "that", "whose",
            "featuring", "including", "maintaining",
            "while", "because", "although",
            "where", "when"
        }

        def is_continuation(text):
            text = text.strip()

            if not text:
                return False

            first_word = text.split()[0].lower().strip(" ,.;:")

            return (
                text[0].islower()
                or first_word in continuation_words
            )

        def can_connect(previous, current):

            gap = (
                float(current["start"])
                - float(previous["end"])
            )

            if gap < 0 or gap > 1.5:
                return False

            previous_text = previous["text"].strip()

            # Never merge across a completed sentence.
            if previous_text.endswith((".", "!", "?")):
                return False

            # Explicit continuation punctuation.
            if previous_text.endswith((",", ":", ";", "-", "—")):
                return True

            return is_continuation(current["text"])

        for highlight in highlights:

            start = highlight["start"]
            end = highlight["end"]

            matching_indices = [
                index
                for index, segment in enumerate(segments)
                if (
                    float(segment["end"]) > start
                    and float(segment["start"]) < end
                )
            ]

            if not matching_indices:
                print(
                    f"Skipping highlight without speech: "
                    f"{highlight['title']}"
                )
                continue

            first_index = matching_indices[0]
            last_index = matching_indices[-1]

            # Expand backward when the selected segment
            # begins with an incomplete continuation.
            while first_index > 0:

                previous = segments[first_index - 1]
                current = segments[first_index]

                if not can_connect(previous, current):
                    break

                first_index -= 1

            # Expand forward when the selected segment
            # ends before the spoken thought is complete.
            while last_index < len(segments) - 1:

                current = segments[last_index]
                following = segments[last_index + 1]

                if not can_connect(current, following):
                    break

                last_index += 1

            final_segments = segments[first_index:last_index + 1]

            actual_transcript = " ".join(
                segment["text"].strip()
                for segment in final_segments
            )

            grounded_highlight = highlight.copy()

            grounded_highlight["start"] = round(
                float(final_segments[0]["start"]), 3
            )

            grounded_highlight["end"] = round(
                float(final_segments[-1]["end"]), 3
            )

            grounded_highlight["transcript"] = actual_transcript

            grounded.append(grounded_highlight)

        # Remove duplicate clips created when two AI candidates
        # refer to the same expanded spoken thought.
        unique_highlights = {}

        for highlight in grounded:

            key = (
                highlight["start"],
                highlight["end"]
            )

            existing = unique_highlights.get(key)

            if (
                existing is None
                or highlight.get("score", 0) > existing.get("score", 0)
            ):
                unique_highlights[key] = highlight

        return list(unique_highlights.values())


    
    def validate_semantic_relevance(self, highlights, transcript):

        segments = transcript.get("segments", [])

        verified = []

        for highlight in highlights:

            matching_segments = [
                segment for segment in segments
                if (
                    float(segment["end"]) > highlight["start"]
                    and float(segment["start"]) < highlight["end"]
                )
            ]

            actual_speech = " ".join(
                segment["text"].strip()
                for segment in matching_segments
            )

            prompt = f"""
You are a strict video highlight fact checker.

Compare the AI-generated highlight against the actual speech.

HIGHLIGHT TITLE:
{highlight['title']}

HIGHLIGHT REASON:
{highlight['reason']}

ACTUAL SPOKEN CONTENT:
{actual_speech}

Determine whether the title and reason accurately describe the spoken content.

Rules:
- Do not use visual context to justify an incorrect speech description.
- The title must describe the actual spoken topic.
- The reason must be supported by the actual speech.
- Reject unrelated or misleading descriptions.
- Do not assume that two topics are related merely because they appear in the same video.

Return JSON only:

{{
    "valid": true,
    "explanation": "Short explanation"
}}
"""

            try:

                result = self.llm.generate_json(prompt)

                if result.get("valid") is True:

                    highlight["validation"] = result.get(
                        "explanation", ""
                    )

                    verified.append(highlight)

                else:

                    print(
                        "\nRejected misleading highlight:",
                        highlight["title"]
                    )

                    print(
                        "Reason:",
                        result.get("explanation", "Semantic mismatch")
                    )

            except Exception as error:

                print("Semantic validation failed:", error)

        return verified



    def detect(self, transcript, visual_analysis=None):

        duration = float(transcript.get("duration", 0))

        if not transcript.get("segments"):
            raise ValueError("Transcript contains no speech segments.")

        print("\nPreparing multimodal context...")

        if visual_analysis:
            print(
                "Visual frames:",
                visual_analysis.get("total_frames", 0)
            )
        else:
            print("No visual analysis supplied. Using transcript only.")

        prompt = self.build_prompt(transcript, visual_analysis)

        print("\nSending context to Qwen3:4b...")
        print("Analyzing speech and visual information...\n")

        result = self.llm.generate_json(prompt)

        highlights = self.validate_highlights(result, duration)

        # Verify AI-generated highlights against actual Whisper segments.
        highlights = self.ground_highlights(
            highlights,
            transcript
        )

        highlights = self.validate_semantic_relevance(
                        highlights,
                        transcript
                    )

        return {
            "video_duration": duration,
            "total_highlights": len(highlights),
            "highlights": highlights
        }

    def save_highlights(self, result, filename):

        output_file = self.highlight_dir / f"{filename}_highlights.json"

        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(result, file, indent=4, ensure_ascii=False)

        return output_file


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "transcript",
        help="Path to transcript JSON file"
    )

    parser.add_argument(
        "--visual",
        help="Path to visual analysis JSON file",
        default=None
    )

    args = parser.parse_args()

    detector = HighlightDetector()

    print("\n===== LOADING TRANSCRIPT =====")

    transcript = detector.load_transcript(args.transcript)

    visual_analysis = None

    if args.visual:
        print("\n===== LOADING VISUAL ANALYSIS =====")
        visual_analysis = detector.load_visual_analysis(args.visual)

    print("\n===== MULTIMODAL AI HIGHLIGHT DETECTION =====")

    result = detector.detect(transcript, visual_analysis)

    print("\n===== DETECTED HIGHLIGHTS =====")

    for index, highlight in enumerate(result["highlights"], start=1):

        print(f"\nHighlight #{index}")
        print("Title:", highlight["title"])
        print(f"Time: {highlight['start']}s - {highlight['end']}s")
        print("Category:", highlight["category"])
        print("Score:", highlight["score"])
        print("Reason:", highlight["reason"])
        print("Transcript:", highlight["transcript"])

    print("\n===== SAVING RESULTS =====")

    filename = Path(args.transcript).stem

    if filename.endswith("_highlights"):
        filename = filename[:-len("_highlights")]

    output_file = detector.save_highlights(result, filename)

    print("Saved:", output_file)
    print("\nHighlight detection completed.")
