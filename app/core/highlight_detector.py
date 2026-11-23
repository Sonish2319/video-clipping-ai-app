
import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from llm_client import OllamaClient


class HighlightDetector:

    def __init__(self, min_duration=10.0, max_duration=20.0):

        self.project_root = Path(__file__).resolve().parents[2]

        self.transcript_dir = self.project_root / "output" / "transcripts"
        self.visual_dir = self.project_root / "output" / "visual_analysis"
        self.highlight_dir = self.project_root / "output" / "highlights"

        self.highlight_dir.mkdir(parents=True, exist_ok=True)

        self.min_duration = float(min_duration)
        self.max_duration = float(max_duration)

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

    def build_prompt(self, transcript, visual_analysis=None, min_duration=None, max_duration=None):

        min_dur = float(min_duration if min_duration is not None else self.min_duration)
        max_dur = float(max_duration if max_duration is not None else self.max_duration)

        segments = transcript.get("segments", [])
        total_duration = round(float(transcript.get("duration", 0)), 2)

        # Build compact, human-readable timestamped transcript lines
        transcript_lines = []
        for segment in segments:
            start_s = float(segment.get("start", 0))
            end_s = float(segment.get("end", 0))
            text = segment.get("text", "").strip()
            if text:
                transcript_lines.append(f"[{start_s:.2f}s - {end_s:.2f}s] {text}")

        transcript_text = "\n".join(transcript_lines)

        prompt = f"""
You are an expert short-form video editor and content strategist specializing in producing engaging, high-retention clips for YouTube Shorts, TikTok, and Instagram Reels.

Your task is to identify 3 to 8 of the best standalone video highlights strictly from the spoken transcript below, distributed across different parts of the video (beginning, middle, and end).

VIDEO TOTAL DURATION:
{total_duration} seconds

SPOKEN TRANSCRIPT WITH TIMESTAMPS:
{transcript_text}

==================================================
CRITICAL DURATION REQUIREMENT (MANDATORY):
==================================================
- Every single highlight MUST be between {min_dur:.0f} and {max_dur:.0f} seconds long ({min_dur:.0f}s to {max_dur:.0f}s).
- Duration formula: duration = end - start. You must strictly ensure: {min_dur:.0f}.0 <= (end - start) <= {max_dur:.0f}.0.
- NEVER select isolated 1 to 5 second lines or single short sentence fragments. A 2-3 second fragment is NOT a valid clip!
- You MUST combine consecutive transcript lines into a continuous, cohesive spoken thought, insight, or exchange spanning between {min_dur:.0f} and {max_dur:.0f} seconds total.
- Select `start` from the beginning of the opening sentence/segment and `end` from the end of the concluding sentence/segment.

==================================================
SELECTION CRITERIA (ALL VIDEO GENRES):
==================================================
Whether the video is a podcast discussion, educational tutorial, interview, speech, story, or commentary:
1. Complete Standalone Thought: The viewer must understand the premise, context, and takeaway from this 10-20s segment alone without watching the rest of the video.
2. Strong Hook: Begins with an intriguing question, strong opinion, surprising statement, or relatable situation.
3. Punchy Resolution / Value: Ends on an actionable tip, memorable conclusion, humorous punchline, or clear philosophical takeaway.
4. Suitable Categories:
   - educational: Clear tips, how-tos, surprising facts, or explanations.
   - motivational: Inspiring mindsets, strong advice, calls to action.
   - storytelling: A punchy anecdote or personal experience.
   - humor: Entertaining or funny interactions.
   - opinion: A bold perspective, debate, or strong viewpoint.
   - informative: Useful factual insights.

==================================================
STRICT GROUNDING RULES:
==================================================
1. Every highlight MUST be grounded directly in the supplied transcript.
2. Never invent words, quotes, or statements not in the transcript.
3. The `start` and `end` timestamps must be exact timestamps chosen from the transcript lines above.
4. The `transcript` field must contain the exact continuous words spoken between `start` and `end`.
5. Ensure {min_dur:.0f}.0 <= (end - start) <= {max_dur:.0f}.0 for EVERY highlight!
6. Do not create overlapping clips for the same moment.
7. Return an empty array only if no meaningful {min_dur:.0f}-{max_dur:.0f}s highlight exists.

OUTPUT FORMAT (Return valid JSON only):
{{
    "highlights": [
        {{
            "start": 13.16,
            "end": 28.88,
            "title": "Clear concise descriptive title",
            "reason": "Why this 10-20s moment is engaging and works as a standalone short",
            "category": "motivational",
            "score": 9,
            "transcript": "Exact continuous spoken words from 13.16s to 28.88s."
        }},
        {{
            "start": 116.18,
            "end": 131.00,
            "title": "Another standalone insight title",
            "reason": "Why this moment provides immediate value in under 20 seconds",
            "category": "educational",
            "score": 8,
            "transcript": "Exact continuous spoken words from 116.18s to 131.00s."
        }}
    ]
}}

Allowed categories:
educational, funny, emotional, motivational, informative, storytelling, opinion, other

Return valid JSON only.
"""
        return prompt

    def validate_highlights(self, result, video_duration, min_duration=None, max_duration=None):

        if not isinstance(result, dict):
            raise ValueError("AI response must be a JSON object.")

        highlights = result.get("highlights")

        if not isinstance(highlights, list):
            raise ValueError("Missing highlights list.")

        min_dur = float(min_duration if min_duration is not None else self.min_duration)
        max_dur = float(max_duration if max_duration is not None else self.max_duration)

        validated = []

        for item in highlights:

            try:

                start = float(item["start"])
                end = float(item["end"])
                score = int(item["score"])

                if start < 0 or end <= start:
                    continue

                if end > video_duration + 1.0:
                    continue

                if not 1 <= score <= 10:
                    continue

                # Basic plausibility filter: ignore if impossibly short (< 3s)
                # Grounding will expand/trim to [min_dur, max_dur]
                if (end - start) < 3.0:
                    continue

                validated.append({
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "title": str(item["title"]).strip(),
                    "reason": str(item["reason"]).strip(),
                    "category": str(item.get("category", "informative")).lower(),
                    "score": score,
                    "transcript": str(item.get("transcript", "")).strip()
                })

            except (KeyError, TypeError, ValueError):
                continue

        return sorted(
            validated,
            key=lambda item: item["score"],
            reverse=True
        )

    def ground_highlights(self, highlights, transcript, min_duration=None, max_duration=None):

        segments = transcript.get("segments", [])
        if not segments:
            return []

        min_dur = float(min_duration if min_duration is not None else self.min_duration)
        max_dur = float(max_duration if max_duration is not None else self.max_duration)
        total_video_duration = float(transcript.get("duration", 0))

        effective_min = min(min_dur, total_video_duration) if total_video_duration > 0 else min_dur

        continuation_words = {
            "who", "which", "that", "whose",
            "featuring", "including", "maintaining",
            "while", "because", "although", "whereas",
            "where", "when", "and", "or", "so", "but"
        }

        dangling_end_words = {
            "from", "to", "with", "of", "and", "or", "that",
            "which", "in", "at", "as", "is", "are", "was",
            "were", "a", "an", "the", "for", "by", "about",
            "if", "so", "than", "then", "into", "through"
        }

        def starts_with_continuation(text):
            text = text.strip()
            if not text:
                return False
            first_word = text.split()[0].lower().strip(" ,.;:!?-\"'\u201c\u201d")
            return text[0].islower() or first_word in continuation_words

        def ends_with_dangling(text):
            text = text.strip()
            if not text:
                return False
            last_word = text.split()[-1].lower().strip(" ,.;:!?-\"'\u201c\u201d")
            return last_word in dangling_end_words

        grounded = []

        for highlight in highlights:

            start = float(highlight["start"])
            end = float(highlight["end"])

            # Find matching segment indices
            matching_indices = [
                index
                for index, segment in enumerate(segments)
                if (
                    float(segment["end"]) > start
                    and float(segment["start"]) < end
                )
            ]

            if not matching_indices:
                matching_indices = [
                    min(
                        range(len(segments)),
                        key=lambda idx: abs(float(segments[idx]["start"]) - start)
                    )
                ]

            first_index = matching_indices[0]
            last_index = matching_indices[-1]

            # 1. EXPAND if duration is less than effective_min (target 10-20s)
            while True:
                cur_start = float(segments[first_index]["start"])
                cur_end = float(segments[last_index]["end"])
                cur_dur = cur_end - cur_start

                if cur_dur >= effective_min - 0.5:
                    break

                can_fwd = (last_index + 1 < len(segments)) and (
                    (float(segments[last_index + 1]["end"]) - cur_start) <= max_dur + 1.0
                )
                can_bwd = (first_index > 0) and (
                    (cur_end - float(segments[first_index - 1]["start"])) <= max_dur + 1.0
                )

                if can_fwd and can_bwd:
                    gap_fwd = float(segments[last_index + 1]["start"]) - cur_end
                    gap_bwd = cur_start - float(segments[first_index - 1]["end"])
                    if gap_fwd <= gap_bwd:
                        last_index += 1
                    else:
                        first_index -= 1
                elif can_fwd:
                    last_index += 1
                elif can_bwd:
                    first_index -= 1
                else:
                    break

            # 2. TRIM if duration exceeds max_dur
            while True:
                cur_start = float(segments[first_index]["start"])
                cur_end = float(segments[last_index]["end"])
                cur_dur = cur_end - cur_start

                if cur_dur <= max_dur + 0.5 or first_index >= last_index:
                    break

                trimmed_end_dur = float(segments[last_index - 1]["end"]) - cur_start
                if trimmed_end_dur >= effective_min - 1.0:
                    last_index -= 1
                    continue

                trimmed_start_dur = cur_end - float(segments[first_index + 1]["start"])
                if trimmed_start_dur >= effective_min - 1.0:
                    first_index += 1
                    continue

                last_index -= 1

            # 3. CLEAN BOUNDARIES: Avoid starting on a continuation or ending on a preposition
            if starts_with_continuation(segments[first_index]["text"]) and first_index > 0:
                prev_start = float(segments[first_index - 1]["start"])
                cur_end = float(segments[last_index]["end"])
                if (cur_end - prev_start) <= max_dur + 1.0:
                    first_index -= 1

            if ends_with_dangling(segments[last_index]["text"]) and (last_index + 1 < len(segments)):
                next_end = float(segments[last_index + 1]["end"])
                cur_start = float(segments[first_index]["start"])
                if (next_end - cur_start) <= max_dur + 2.0:
                    last_index += 1

            final_start = round(float(segments[first_index]["start"]), 3)
            final_end = round(float(segments[last_index]["end"]), 3)
            final_dur = round(final_end - final_start, 2)

            # Strict duration validation: must satisfy 10-20s (or video duration)
            if total_video_duration >= effective_min and final_dur < (effective_min - 1.5):
                print(
                    f"Skipping highlight '{highlight['title']}': duration {final_dur}s below minimum {effective_min}s."
                )
                continue

            if final_dur > (max_dur + 1.5):
                print(
                    f"Skipping highlight '{highlight['title']}': duration {final_dur}s exceeds maximum {max_dur}s."
                )
                continue

            actual_segments = segments[first_index:last_index + 1]
            actual_transcript = " ".join(
                seg["text"].strip() for seg in actual_segments
            )

            grounded_hl = highlight.copy()
            grounded_hl["start"] = final_start
            grounded_hl["end"] = final_end
            grounded_hl["duration"] = final_dur
            grounded_hl["transcript"] = actual_transcript
            grounded.append(grounded_hl)

        # 4. DEDUPLICATION & OVERLAP REMOVAL (> 50% overlap)
        unique_highlights = []
        grounded.sort(key=lambda h: h.get("score", 0), reverse=True)

        for hl in grounded:
            hl_start = hl["start"]
            hl_end = hl["end"]
            hl_dur = hl_end - hl_start

            is_duplicate = False
            for existing in unique_highlights:
                ex_start = existing["start"]
                ex_end = existing["end"]
                overlap_start = max(hl_start, ex_start)
                overlap_end = min(hl_end, ex_end)
                overlap_dur = max(0.0, overlap_end - overlap_start)

                if overlap_dur > 0.5 * min(hl_dur, ex_end - ex_start):
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_highlights.append(hl)

        return sorted(unique_highlights, key=lambda h: h.get("score", 0), reverse=True)

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

Compare the AI-generated highlight title and reason against the actual speech.

HIGHLIGHT TITLE:
{highlight['title']}

HIGHLIGHT REASON:
{highlight['reason']}

ACTUAL SPOKEN CONTENT:
{actual_speech}

Determine whether the title and reason accurately reflect or summarize the spoken content.

Rules:
- The title must truthfully describe or summarize the actual spoken topic.
- The reason must be supported by the actual speech.
- Reject completely unrelated, fabricated, or misleading descriptions.
- Allow natural summary titles and conversational takeaways.

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
                # If LLM check fails for connection or format, keep highlight if speech exists
                if actual_speech.strip():
                    highlight["validation"] = "Fallback: speech verified directly."
                    verified.append(highlight)

        return verified

    def detect(self, transcript, visual_analysis=None, min_duration=None, max_duration=None):

        min_dur = float(min_duration if min_duration is not None else self.min_duration)
        max_dur = float(max_duration if max_duration is not None else self.max_duration)
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

        prompt = self.build_prompt(transcript, visual_analysis, min_dur, max_dur)

        print("\nSending context to Qwen3:4b...")
        print(f"Target clip duration: {min_dur:.0f}s - {max_dur:.0f}s")
        print("Analyzing speech for engaging standalone highlights...\n")

        result = self.llm.generate_json(prompt)

        highlights = self.validate_highlights(result, duration, min_dur, max_dur)

        # Ground AI-generated highlights against actual Whisper segments and enforce duration bounds.
        highlights = self.ground_highlights(
            highlights,
            transcript,
            min_dur,
            max_dur
        )

        highlights = self.validate_semantic_relevance(
            highlights,
            transcript
        )

        return {
            "video_duration": duration,
            "min_duration": min_dur,
            "max_duration": max_dur,
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

    parser = argparse.ArgumentParser(description="Multimodal AI Highlight Detection")

    parser.add_argument(
        "transcript",
        help="Path to transcript JSON file"
    )

    parser.add_argument(
        "--visual",
        help="Path to visual analysis JSON file",
        default=None
    )

    parser.add_argument(
        "--min-duration",
        type=float,
        default=10.0,
        help="Minimum clip duration in seconds (default: 10.0)"
    )

    parser.add_argument(
        "--max-duration",
        type=float,
        default=20.0,
        help="Maximum clip duration in seconds (default: 20.0)"
    )

    args = parser.parse_args()

    detector = HighlightDetector(
        min_duration=args.min_duration,
        max_duration=args.max_duration
    )

    print("\n===== LOADING TRANSCRIPT =====")

    transcript = detector.load_transcript(args.transcript)

    visual_analysis = None

    if args.visual:
        print("\n===== LOADING VISUAL ANALYSIS =====")
        visual_analysis = detector.load_visual_analysis(args.visual)

    print("\n===== MULTIMODAL AI HIGHLIGHT DETECTION =====")

    result = detector.detect(
        transcript,
        visual_analysis,
        min_duration=args.min_duration,
        max_duration=args.max_duration
    )

    print("\n===== DETECTED HIGHLIGHTS =====")

    for index, highlight in enumerate(result["highlights"], start=1):

        dur = highlight.get("duration", round(highlight["end"] - highlight["start"], 2))
        print(f"\nHighlight #{index}")
        print("Title:", highlight["title"])
        print(f"Time: {highlight['start']}s - {highlight['end']}s (Duration: {dur}s)")
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
