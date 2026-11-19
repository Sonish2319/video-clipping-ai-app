
import argparse
import json
import logging
import subprocess
import sys
import time

from datetime import datetime
from pathlib import Path


class FullVideoPipeline:

    def __init__(self, video_path, frame_interval=2):

        self.project_root = Path(__file__).resolve().parents[2]
        self.video_path = Path(video_path).resolve()

        self.video_name = self.video_path.stem
        self.frame_interval = frame_interval

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

        result = subprocess.run(
            command,
            cwd=self.project_root,
            text=True,
            capture_output=True
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
                    self.visual_analysis_path
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
                    self.selected_visuals_path
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
            print(f"Results: {final_results}")

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
        default=2,
        help="Frame sampling interval in seconds (default: 2)"
    )

    args = parser.parse_args()

    pipeline = FullVideoPipeline(
        args.video,
        frame_interval=args.interval
    )

    pipeline.run()
