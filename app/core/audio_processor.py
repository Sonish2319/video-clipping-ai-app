
import json
import subprocess
from pathlib import Path

from faster_whisper import WhisperModel


class AudioProcessor:

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]

        self.audio_dir = self.project_root / "output" / "audio"
        self.transcript_dir = self.project_root / "output" / "transcripts"

        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_dir.mkdir(parents=True, exist_ok=True)

        self.model = None

    def extract_audio(self, video_path):

        video_path = Path(video_path).resolve()

        if not video_path.exists():
            raise FileNotFoundError(video_path)

        output_file = self.audio_dir / f"{video_path.stem}.wav"

        command = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "pcm_s16le",
            str(output_file)
        ]

        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        return output_file

    def load_model(self):

        if self.model is None:

            print("Loading Whisper Small INT8 model...")

            self.model = WhisperModel(
                "small",
                device="cpu",
                compute_type="int8",
                cpu_threads=8,
                num_workers=1
            )

            print("Whisper model loaded.")

        return self.model

    def transcribe(self, audio_path):

        audio_path = Path(audio_path).resolve()

        if not audio_path.exists():
            raise FileNotFoundError(audio_path)

        model = self.load_model()

        print("Starting transcription...")

        segments, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            vad_filter=True,
            word_timestamps=True
        )

        results = []

        for segment in segments:

            words = []

            if segment.words:
                words = [
                    {
                        "word": word.word,
                        "start": round(word.start, 3),
                        "end": round(word.end, 3)
                    }
                    for word in segment.words
                ]

            results.append({
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "text": segment.text.strip(),
                "words": words
            })

            print(
                f"[{segment.start:.2f}s - {segment.end:.2f}s] "
                f"{segment.text.strip()}"
            )

        transcript = {
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": results
        }

        return transcript

    def save_transcript(self, transcript, filename):

        json_file = self.transcript_dir / f"{filename}.json"
        text_file = self.transcript_dir / f"{filename}.txt"

        with open(json_file, "w", encoding="utf-8") as file:
            json.dump(
                transcript,
                file,
                indent=4,
                ensure_ascii=False
            )

        with open(text_file, "w", encoding="utf-8") as file:

            for segment in transcript["segments"]:

                file.write(
                    f"[{segment['start']:.2f}s - "
                    f"{segment['end']:.2f}s] "
                    f"{segment['text']}\n"
                )

        return json_file, text_file


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("video", help="Input video path")

    args = parser.parse_args()

    processor = AudioProcessor()

    print("\n===== AUDIO EXTRACTION =====")

    audio = processor.extract_audio(args.video)

    print("Audio extracted:", audio)

    print("\n===== SPEECH TRANSCRIPTION =====")

    transcript = processor.transcribe(audio)

    print("\n===== TRANSCRIPT SAVING =====")

    filename = Path(args.video).stem

    json_file, text_file = processor.save_transcript(
        transcript,
        filename
    )

    print("JSON:", json_file)
    print("TXT:", text_file)

    print("\nProcessing completed successfully.")
