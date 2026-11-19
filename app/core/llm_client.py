
import json
import urllib.request
import urllib.error


class OllamaClient:

    def __init__(
        self,
        model="qwen3:4b",
        base_url="http://localhost:11434"
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt):

        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.2
            }
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=180
            ) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

                return result["response"]

        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Unable to connect to Ollama: {error}"
            )


    def generate_json(self, prompt):

        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "format": "json",
            "options": {
                "temperature": 0.2
            }
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=180
            ) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

                raw_response = result.get("response", "").strip()

                # Extract JSON if additional text exists.
                start = raw_response.find("{")
                end = raw_response.rfind("}")

                if start == -1 or end == -1:
                    raise RuntimeError(
                        f"No JSON object found: {raw_response}"
                    )

                json_text = raw_response[start:end + 1]

                return json.loads(json_text)

        except urllib.error.URLError as error:

            raise RuntimeError(
                f"Unable to connect to Ollama: {error}"
            )

        except json.JSONDecodeError as error:

            raise RuntimeError(
                f"Invalid JSON returned by Ollama: {error}"
            )

if __name__ == "__main__":

    client = OllamaClient()

    print("Testing Ollama connection...")

    response = client.generate(
        "Explain in two sentences what makes a video moment interesting."
    )

    print("\nOllama response:")
    print(response)
