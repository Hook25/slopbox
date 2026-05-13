import json
import os
import urllib.error
import urllib.request
from typing import Any

OPENAI_ENDPOINT = os.environ.get(
    "OPENAI_ENDPOINT",
    "http://localhost:1234/v1/chat/completions",
)
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")


def query_openai_endpoint(prompt_text: str, *, thinking: bool = True) -> str:
    payload_data: dict[str, Any] = {
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0,
        "thinking": thinking,
    }
    if OPENAI_MODEL:
        payload_data["model"] = OPENAI_MODEL
    payload = json.dumps(payload_data).encode()
    req = urllib.request.Request(
        OPENAI_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not connect to LLM endpoint "
            f"{OPENAI_ENDPOINT}: {exc.reason}"
        ) from exc

    if "error" in result:
        raise SystemExit(f"API returned an error: {result['error']}")
    if "choices" not in result:
        raise SystemExit(
            f"Unexpected API response (missing 'choices' key): {result}"
        )
    return result["choices"][0]["message"]["content"]
