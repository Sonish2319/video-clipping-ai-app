
import json
from pathlib import Path

from vision_client import VisionClient


class FrameAnalyzer:

    def __init__(self):

        self.project_root = Path(__file__).resolve().parents[2]

        self.vision_client = VisionClient()

        self.output_dir = (
            self.project_root / "output" / "visual_analysis"
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def analyze_frames(self, frame_directory, interval=5):

        frame_directory = Path(frame_directory)

        if not frame_directory.is_absolute():
            frame_directory = self.project_root / frame_directory

        frame_directory = frame_directory.resolve()

        if not frame_directory.exists():
            raise FileNotFoundError(frame_directory)

        frames = sorted(frame_directory.glob("frame_*.jpg"))

        if not frames:
            raise ValueError("No extracted frames found.")

        video_name = frame_directory.name

        print(f"\nFound {len(frames)} frames.")
        print("Starting visual analysis...\n")

        results = []

        for index, frame_path in enumerate(frames):

            timestamp = index * interval

            print(
                f"\nProcessing frame {index + 1}/{len(frames)}"
                f" at {timestamp:.2f}s"
            )

            try:

                analysis = self.vision_client.analyze_image(
                    frame_path
                )

                results.append({
                    "frame": frame_path.name,
                    "timestamp": timestamp,
                    "analysis": analysis
                })

                print("Analysis completed.")

            except Exception as error:

                print(
                    f"Failed to analyze {frame_path.name}: {error}"
                )

                results.append({
                    "frame": frame_path.name,
                    "timestamp": timestamp,
                    "error": str(error)
                })

        report = {
            "video_name": video_name,
            "sampling_interval": interval,
            "total_frames": len(frames),
            "successful_analyses": sum(
                1 for item in results if "analysis" in item
            ),
            "failed_analyses": sum(
                1 for item in results if "error" in item
            ),
            "frames": results
        }

        output_path = (
            self.output_dir /
            f"{video_name}_visual_analysis.json"
        )

        with open(output_path, "w", encoding="utf-8") as file:

            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

        print("\nVisual analysis completed.")
        print("Report saved:", output_path)

        return report


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("frame_directory")

    parser.add_argument(
        "--interval",
        type=int,
        default=5
    )

    args = parser.parse_args()

    analyzer = FrameAnalyzer()

    report = analyzer.analyze_frames(
        args.frame_directory,
        interval=args.interval
    )

    print("\nSummary:")
    print("Total frames:", report["total_frames"])
    print("Successful:", report["successful_analyses"])
    print("Failed:", report["failed_analyses"])
