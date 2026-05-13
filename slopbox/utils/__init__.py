import json
import os
import urllib.request
from typing import Any

OPENAI_ENDPOINT = os.environ.get(
    "OPENAI_ENDPOINT",
    "http://localhost:1234/v1/chat/completions",
)
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")


def query_openai_endpoint(prompt_text: str) -> str:
    print(f"Sending: {prompt_text}")
    payload_data: dict[str, Any] = {
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0,
    }
    if OPENAI_MODEL:
        payload_data["model"] = OPENAI_MODEL
    payload = json.dumps(payload_data).encode()
    req = urllib.request.Request(
        OPENAI_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    if "error" in result:
        raise SystemExit(f"API returned an error: {result['error']}")
    if "choices" not in result:
        raise SystemExit(
            f"Unexpected API response (missing 'choices' key): {result}"
        )
    return result["choices"][0]["message"]["content"]
