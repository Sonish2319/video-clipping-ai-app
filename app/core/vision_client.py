
import base64
import json
import urllib.request
import urllib.error
from pathlib import Path


class VisionClient:

    def __init__(
        self,
        model="qwen3-vl:4b",
        base_url="http://localhost:11434"
    ):

        self.project_root = Path(__file__).resolve().parents[2]

        self.model = model
        self.api_url = f"{base_url}/api/generate"

    def analyze_image(self, image_path):

        image_path = Path(image_path)

        if not image_path.is_absolute():
            image_path = self.project_root / image_path

        image_path = image_path.resolve()

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        # Encode image as Base64.
        with open(image_path, "rb") as image_file:
            image_base64 = base64.b64encode(
                image_file.read()
            ).decode("utf-8")

        prompt = """
Analyze this video frame for an AI video clipping application.

Identify:

1. What is visibly happening?
2. Are people visible? What are they doing?
3. What important objects are visible?
4. What is the overall scene context?
5. How visually interesting is this frame?

Do not invent details.

Return valid JSON with this structure:

{
    "scene_description": "Description of the scene",
    "people": [
        {
            "description": "Visible appearance",
            "action": "Visible action"
        }
    ],
    "objects": [],
    "visual_context": "Overall scene context",
    "visual_interest": 7,
    "reason": "Explanation of the score"
}

visual_interest must be an integer between 1 and 10.
"""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "think": False,
            "format": "json"
        }

        request = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        print(f"\nAnalyzing image: {image_path.name}")
        print(f"Using model: {self.model}")

        try:

            with urllib.request.urlopen(
                request,
                timeout=300
            ) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

            # First, try the normal response field.
            model_response = result.get("response", "")

            # Fallback to chat-style response.
            if not model_response:
                message = result.get("message", {})
                model_response = message.get("content", "")

            # Qwen3-VL may return its generated JSON in the thinking field.
            if not model_response:
                model_response = result.get("thinking", "")

            if not model_response:

                print("\nOllama returned an empty text response.")
                print("\nRaw Ollama response:")
                print(json.dumps(
                    result,
                    indent=4,
                    ensure_ascii=False
                ))

                raise RuntimeError(
                    "Vision model returned an empty response."
                )

            try:
                return json.loads(model_response)

            except json.JSONDecodeError:

                print("\nModel returned non-JSON content:")
                print(model_response)

                raise RuntimeError(
                    "Could not parse vision model JSON."
                )

        except urllib.error.URLError as error:

            raise RuntimeError(
                f"Could not connect to Ollama: {error}"
            )


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("image")

    args = parser.parse_args()

    client = VisionClient()

    analysis = client.analyze_image(args.image)

    print("\nVisual Analysis Result:")
    print(json.dumps(
        analysis,
        indent=4,
        ensure_ascii=False
    ))
