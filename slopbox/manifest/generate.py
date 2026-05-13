import json
import os
import textwrap
import urllib.request
from pathlib import Path

from slopbox.manifest.assign import (
    checkbox_cli_list,
    load_json,
    prune_job,
)

OPENAI_ENDPOINT = os.environ.get(
    "OPENAI_ENDPOINT",
    "http://localhost:1234/v1/chat/completions",
)

prompt = textwrap.dedent("""\
    You are a JSON-only output engine. You MUST output
    raw JSON and nothing else. No explanations, no
    markdown, no code fences, no preamble, no comments.

    Your task: given a test job, return a JSON object
    mapping feature names to descriptions.
    If no features apply, return exactly: {{}}

    ### WHAT IS A FEATURE

    A "feature" is a hardware or firmware capability of
    a device. It describes what a device CAN DO, not
    what software is installed.

    Good features:
    - has_ethernet_adapter (hardware present)
    - has_wifi6 (firmware/hardware capability)
    - has_h265_encoding (hardware encoding)
    - has_thunderbolt (port present)

    NOT features (do not use these):
    - has_ping_command (software tool)
    - has_fwts_installed (software tool)

    Features must be specific. A wifi6 test needs both
    has_wifi_adapter AND has_wifi6.
    Names MUST start with "has_" and be snake_case.

    ### OUTPUT FORMAT

    Your entire response must be a single JSON object.
    Example output for a wifi6 test:
    {{
        "has_wifi_adapter": "Machine has a wifi adapter",
        "has_wifi6": "Machine supports wifi 6"
    }}

    Example output when no feature applies:
    {{}}

    ### TEST JOB
    {test}

    ### JSON OUTPUT:
    """)


def query_openai_endpoint(prompt_text: str) -> str:
    """Send a prompt to the OpenAI-compatible endpoint."""
    payload = json.dumps(
        {
            "messages": [
                {"role": "user", "content": prompt_text},
            ],
            "temperature": 0,
        }
    ).encode()
    req = urllib.request.Request(
        OPENAI_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    return result["choices"][0]["message"]["content"]


def parse_llm_response(
    response: str,
) -> dict[str, str]:
    """Parse the LLM response.

    Returns a dict mapping feature names to descriptions.
    An empty dict means no features are needed.
    Raises ValueError if the format is invalid.
    """
    stripped = response.strip()
    result = json.loads(stripped)
    if not isinstance(result, dict):
        raise ValueError(f"Expected a JSON object, got: {type(result)}")
    return result


def run_prompt(job_dct: dict, max_retries: int = 5) -> dict[str, str]:
    """Drive the LLM to decide if a job needs features.

    Returns a dict mapping feature names to descriptions.
    An empty dict means no features are needed.
    """
    job_dct = prune_job(job_dct)
    test_repr = json.dumps(job_dct)
    for _i in range(max_retries):
        llm_out = query_openai_endpoint(prompt.format(test=test_repr))
        try:
            return parse_llm_response(llm_out)
        except (ValueError, json.JSONDecodeError):
            print(f"LLM returned unparseable output: {llm_out}")
    raise ValueError("LLM unable to generate a valid feature")


def register_parser(subparsers):
    parser = subparsers.add_parser(
        "generate",
        help=("Decide if a job needs a feature and generate one."),
    )
    parser.add_argument("job_id", help="Job ID to evaluate.")
    parser.add_argument(
        "--job-json",
        type=Path,
        default=None,
        help="Path to the job JSON dump.",
    )
    parser.set_defaults(func=run)
    return parser


def run(args):
    if args.job_json is not None:
        jobs = load_json(args.job_json)
    else:
        jobs = checkbox_cli_list("all-jobs")

    job_id = args.job_id
    try:
        job = next(
            job
            for job in jobs
            if job["id"].endswith(job_id)
            or job.get("template_id", "").endswith(job_id)
        )
    except StopIteration:
        raise SystemExit(f"Job '{args.job_id}' not found") from None

    result = run_prompt(job)
    if not result:
        print("No feature needed for this job.")
    else:
        print(json.dumps(result, indent=2))
