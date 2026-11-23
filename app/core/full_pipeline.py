
import argparse
import json
import logging
import os
import subprocess
import sys
import time

from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class FullVideoPipeline:

    def __init__(self, video_path, frame_interval=None, min_duration=10.0, max_duration=20.0, subtitle_mode="animated"):

        self.project_root = Path(__file__).resolve().parents[2]
        self.video_path = Path(video_path).resolve()

        self.video_name = self.video_path.stem
        self.frame_interval = int(frame_interval) if frame_interval is not None and int(frame_interval) > 0 else None
        self.min_duration = float(min_duration)
        self.max_duration = float(max_duration)
        self.subtitle_mode = subtitle_mode

        self.core_dir = self.project_root / "app" / "core"
        self.output_dir = self.project_root / "output"
        self.log_dir = self.project_root / "logs"

        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.transcript_path = (
            self.output_dir / "transcripts" / f"{self.video_name}.json"
        )

        self.visual_frames_dir = (
            self.output_dir / "frames" / self.video_name
        )

        self.visual_analysis_path = (
            self.output_dir / "visual_analysis" /
            f"{self.video_name}_visual_analysis.json"
        )

        self.highlight_path = (
            self.output_dir / "highlights" /
            f"{self.video_name}_highlights.json"
        )

        self.enriched_path = (
            self.output_dir / "enriched" /
            f"{self.video_name}_semantic.json"
        )

        self.selected_visuals_path = (
            self.output_dir / "selected_visuals" /
            f"{self.video_name}_selected_visuals.json"
        )

        self.log_path = (
            self.log_dir / f"{self.video_name}_pipeline.log"
        )

        self.stage_results = []

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(message)s",
            handlers=[
                logging.FileHandler(
                    self.log_path,
                    encoding="utf-8"
                ),
                logging.StreamHandler()
            ],
            force=True
        )

        self.logger = logging.getLogger("FullVideoPipeline")

    def validate(self):

        if not self.video_path.exists():
            raise FileNotFoundError(
                f"Video not found: {self.video_path}"
            )

        if self.video_path.suffix.lower() not in {
            ".mp4", ".mov", ".mkv", ".avi", ".webm"
        }:
            raise ValueError("Unsupported video format.")

    def get_video_duration(self):

        command = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(self.video_path)
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True
        )

        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    @staticmethod
    def calculate_dynamic_interval(duration_seconds):
        """
        Dynamically determine frame sampling interval based on video duration:
        - <= 60s (under 1 min):   2s interval  (~15-30 frames, e.g. 50s -> 25 frames)
        - <= 180s (1 - 3 mins):   5s interval  (~15-36 frames, e.g. 2 mins -> 24 frames)
        - <= 360s (3 - 6 mins):   10s interval (~20-36 frames, e.g. 5 mins -> 30 frames)
        - <= 900s (6 - 15 mins):  15s interval (~24-60 frames, e.g. 10 mins -> 40 frames)
        - <= 1800s (15 - 30 mins): 25s interval (~36-72 frames, e.g. 20 mins -> 48 frames)
        - > 1800s (> 30 mins):    30s - 60s interval (max ~60 frames)
        """
        d = float(duration_seconds)
        if d <= 60:
            return 2
        elif d <= 180:
            return 5
        elif d <= 360:
            return 10
        elif d <= 900:
            return 15
        elif d <= 1800:
            return 25
        else:
            return max(30, min(60, int(round(d / 45))))

    def run_command(self, stage, script, arguments):

        script_path = self.core_dir / script

        if not script_path.exists():
            raise FileNotFoundError(script_path)

        command = [
            sys.executable,
            str(script_path),
            *[str(arg) for arg in arguments]
        ]

        self.logger.info("=" * 60)
        self.logger.info("STARTING: %s", stage)
        self.logger.info("COMMAND: %s", " ".join(command))

        start_time = time.time()

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        result = subprocess.run(
            command,
            cwd=self.project_root,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )

        elapsed = round(time.time() - start_time, 2)

        if result.stdout:
            self.logger.info("%s", result.stdout)

        if result.stderr:
            if result.returncode == 0:
                self.logger.info("%s", result.stderr)
            else:
                self.logger.error("%s", result.stderr)

        if result.returncode != 0:
            raise RuntimeError(
                f"{stage} failed with exit code "
                f"{result.returncode}"
            )

        self.stage_results.append({
            "stage": stage,
            "status": "success",
            "duration_seconds": elapsed
        })

        self.logger.info(
            "COMPLETED: %s (%.2f seconds)",
            stage,
            elapsed
        )

    def verify_file(self, path):

        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(
                f"Expected output was not created: {path}"
            )

        if path.is_file() and path.stat().st_size == 0:
            raise RuntimeError(
                f"Output file is empty: {path}"
            )

        return path

    def verify_directory(self, path):

        path = Path(path)

        if not path.exists() or not any(path.iterdir()):
            raise RuntimeError(
                f"Expected output directory is empty: {path}"
            )

        return path

    def save_report(self, total_duration, status):

        report_dir = self.output_dir / "pipeline_results"
        report_dir.mkdir(parents=True, exist_ok=True)

        report_path = (
            report_dir /
            f"{self.video_name}_full_pipeline_report.json"
        )

        report = {
            "source_video": str(self.video_path),
            "video_name": self.video_name,
            "status": status,
            "started_at": self.started_at,
            "completed_at": datetime.now().isoformat(),
            "total_processing_seconds": round(total_duration, 2),
            "stages": self.stage_results,
            "outputs": {
                "transcript": str(self.transcript_path),
                "visual_analysis": str(self.visual_analysis_path),
                "highlights": str(self.highlight_path),
                "enriched_visuals": str(self.enriched_path),
                "selected_visuals": str(self.selected_visuals_path),
                "final_clips": str(self.output_dir / "final" / self.video_name),
                "pipeline_results": str(
                    self.output_dir /
                    "pipeline_results" /
                    f"{self.video_name}_pipeline_results.json"
                )
            }
        }

        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(report, file, indent=4, ensure_ascii=False)

        self.logger.info("Processing report: %s", report_path)

    def run(self):

        self.started_at = datetime.now().isoformat()
        start_time = time.time()

        try:

            self.validate()

            video_dur = self.get_video_duration()
            if self.frame_interval is None or self.frame_interval <= 0:
                self.frame_interval = self.calculate_dynamic_interval(video_dur)
                print(
                    f"\nDynamic frame sampling interval: {self.frame_interval}s "
                    f"(based on video duration {video_dur:.1f}s / {video_dur/60:.1f} mins)"
                )
                self.logger.info(
                    "Dynamic frame interval selected: %ds (video duration: %.1fs)",
                    self.frame_interval,
                    video_dur
                )
            else:
                print(f"\nManual frame sampling interval: {self.frame_interval}s")
                self.logger.info("Manual frame interval specified: %ds", self.frame_interval)

            print("\n" + "=" * 65)
            print("LOCAL AI VIDEO CLIPPING - FULL PIPELINE")
            print("=" * 65)
            print(f"Video: {self.video_path.name}")

            # 1. Audio transcription

            self.run_command(
                "Audio transcription",
                "audio_processor.py",
                [self.video_path]
            )

            self.verify_file(self.transcript_path)

            # 2. Frame sampling

            self.run_command(
                "Frame sampling",
                "frame_sampler.py",
                [
                    self.video_path,
                    "--interval",
                    self.frame_interval
                ]
            )

            self.verify_directory(self.visual_frames_dir)

            # 3. Visual frame analysis

            self.run_command(
                "Visual frame analysis",
                "frame_analyzer.py",
                [
                    self.visual_frames_dir,
                    "--interval",
                    self.frame_interval
                ]
            )

            self.verify_file(self.visual_analysis_path)

            # 4. AI highlight detection

            self.run_command(
                "AI highlight detection",
                "highlight_detector.py",
                [
                    self.transcript_path,
                    "--visual",
                    self.visual_analysis_path,
                    "--min-duration",
                    self.min_duration,
                    "--max-duration",
                    self.max_duration
                ]
            )

            self.verify_file(self.highlight_path)

            # 5. Visual enrichment

            self.run_command(
                "Visual enrichment",
                "visual_enricher.py",
                [
                    self.highlight_path,
                    self.visual_analysis_path
                ]
            )

            enriched_base = (
                self.output_dir / "enriched" /
                f"{self.video_name}_enriched.json"
            )

            self.verify_file(enriched_base)

            # 6. Semantic visual relevance

            self.run_command(
                "Semantic visual relevance",
                "visual_relevance.py",
                [enriched_base]
            )

            semantic_path = (
                self.output_dir / "enriched" /
                f"{self.video_name}_semantic.json"
            )

            self.verify_file(semantic_path)

            # 7. Visual selection

            self.run_command(
                "Visual selection",
                "visual_selector.py",
                [semantic_path]
            )

            self.verify_file(self.selected_visuals_path)

            # 8. Clip generation, B-roll, formatting and subtitles

            self.run_command(
                "Final clip production",
                "clip_pipeline.py",
                [
                    self.video_path,
                    self.transcript_path,
                    self.selected_visuals_path,
                    "--subtitle-mode",
                    self.subtitle_mode
                ]
            )

            final_results = (
                self.output_dir / "pipeline_results" /
                f"{self.video_name}_pipeline_results.json"
            )

            self.verify_file(final_results)

            total_duration = time.time() - start_time

            self.save_report(
                total_duration,
                "success"
            )

            self.logger.info("=" * 60)
            self.logger.info("FULL PIPELINE COMPLETED SUCCESSFULLY")
            self.logger.info(
                "Total processing time: %.2f seconds",
                total_duration
            )

            print("\nVIDEO PROCESSING COMPLETED!")
            print(f"Final clipped videos with {self.subtitle_mode} subtitles: {self.output_dir / 'final' / self.video_name}")
            print(f"Results summary: {final_results}")

        except Exception as error:

            total_duration = time.time() - start_time

            self.logger.exception(
                "PIPELINE FAILED: %s",
                error
            )

            self.stage_results.append({
                "stage": "pipeline",
                "status": "failed",
                "error": str(error)
            })

            self.save_report(
                total_duration,
                "failed"
            )

            raise


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Run the complete local AI video clipping pipeline."
    )

    parser.add_argument(
        "video",
        help="Path to source video"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Frame sampling interval in seconds (default: 0 for dynamic auto-calculation based on video length, e.g. 10s for 5 mins)"
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

    parser.add_argument(
        "--subtitle-mode",
        choices=["animated", "standard"],
        default="animated",
        help="Subtitle style to merge into final clips: 'animated' (word-by-word highlighted) or 'standard' (static SRT). Default: animated"
    )

    args = parser.parse_args()

    pipeline = FullVideoPipeline(
        args.video,
        frame_interval=args.interval,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        subtitle_mode=args.subtitle_mode
    )

    pipeline.run()
