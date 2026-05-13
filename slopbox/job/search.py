import json  # noqa: I001
import subprocess
import textwrap
from pathlib import Path
import re

from slopbox.utils import query_openai_endpoint

splitter = re.compile(r"[\W_]")

KEYWORDS_PROMPT = textwrap.dedent("""\
    ### SYSTEM
    You are a keyword extraction engine.
    Given a user's natural language search query about test jobs,
    output ONLY domain-specific keywords and abbreviations that
    would appear in matching job IDs, summaries, purposes,
    or commands.

    ### CONSTRAINTS
    - Output ONLY a comma-separated list of lowercase keywords.
    - Include abbreviations, acronyms, and alternate spellings.
    - Do NOT include generic QA/testing terms that would match
      almost any job (e.g. test, check, verify, result, pass,
      fail, run, background, qa, manual, automated, ensure).
    - Only include terms specific to the DOMAIN being searched.
    - Do NOT provide any preamble, explanation,
      or closing remarks.

    ### EXAMPLE
    Query: "tests that check if bluetooth audio works"
    Keywords: bluetooth, bt, audio, a2dp, pulseaudio, pipewire, \
bluez, hsp, hfp

    Query: "wifi connectivity tests"
    Keywords: wifi, wlan, wireless, ssid, 802, iwconfig, \
networkmanager, nm, wpasupplicant

    ### QUERY
    {query}

    ### KEYWORDS:
    """)

VERIFY_PROMPT = textwrap.dedent("""\
    ### SYSTEM
    You are a strict relevance judge for test jobs.
    Your task is to determine whether the provided job is
    SPECIFICALLY and DIRECTLY about what the user is searching for.

    ### CONSTRAINTS
    - Output ONLY "yes" or "no".
    - Do NOT provide any preamble, explanation,
      or closing remarks.
    - Answer "yes" ONLY if the job's primary purpose is to test
      exactly what the query describes.
    - Answer "no" if the job merely mentions the topic in passing,
      uses it as a dependency, or is only tangentially related.
    - When in doubt, answer "no".

    ### QUERY
    {query}

    ### JOB
    {job}

    ### MATCHES (yes/no):
    """)


def extract_keywords(query):
    """Ask the LLM to generate search keywords from the query."""
    response = query_openai_endpoint(KEYWORDS_PROMPT.format(query=query))
    return [k.strip().lower() for k in response.split(",") if k.strip()]


def job_tokens(job):
    """Tokenize searchable fields of a job into a set of words."""
    fields = (
        "id",
        "template_id",
        "partial_id",
        "_summary",
        "summary",
        "_purpose",
        "purpose",
        "_verification",
        "verification",
        "command",
        "category_id",
        "description",
    )
    parts = []
    for f in fields:
        val = job.get(f)
        if val:
            parts.append(val)
    blob = "\n".join(parts).lower()
    return set(splitter.split(blob)) - {""}


def keyword_filter(jobs, keywords):
    """Pre-filter jobs, ordered by number of matching keywords.

    If any job scores above the median, only return those.
    """
    scored = []
    for job in jobs:
        tokens = job_tokens(job)
        score = sum(1 for kw in keywords if kw in tokens)
        if score > 0:
            scored.append((score, job))
    if not scored:
        return []
    scored.sort(key=lambda x: x[0], reverse=True)
    scores = [s for s, _ in scored]
    mid = len(scores) // 2
    if len(scores) % 2 == 1:
        median = scores[mid]
    else:
        median = (scores[mid - 1] + scores[mid]) / 2
    above = [(s, job) for s, job in scored if s > median]
    if above:
        return [job for _, job in above]
    return [job for _, job in scored]


def full_job_repr(job):
    """Create a detailed representation of a job for verification."""
    keep_keys = {
        "id",
        "template_id",
        "partial_id",
        "summary",
        "purpose",
        "description",
        "command",
        "steps",
        "verification",
        "category",
    }
    items = ((k.removeprefix("_"), v) for k, v in job.items() if v)
    pruned = {k: v for k, v in items if k in keep_keys}
    return json.dumps(pruned, indent=2)


def verify_job(job, query):
    """Ask the LLM to verify a single job against the query."""
    job_text = full_job_repr(job)
    response = query_openai_endpoint(
        VERIFY_PROMPT.format(query=query, job=job_text)
    )
    return response.strip().lower() == "yes"


def search_jobs(jobs, query, *, precise=False):
    """Search over jobs.

    Pass 1: LLM generates keywords, then string-match pre-filter.
    Pass 2 (precise only): Verify each candidate one-by-one with
    full details via LLM.
    """
    # Pass 1: keyword extraction + string filtering
    keywords = extract_keywords(query)
    print(f"Keywords: {', '.join(keywords)}")
    candidates = keyword_filter(jobs, keywords)
    print(f"Pre-filter matched {len(candidates)} jobs.")

    if not candidates:
        return []

    if not precise:
        return candidates

    # Pass 2: one-by-one verification
    verified = []
    for job in candidates:
        if verify_job(job, query):
            print(job.get("template_id") or job["id"])
            verified.append(job)

    return verified


def load_json(path: Path) -> list:
    with path.open("r") as f:
        return json.load(f)


def checkbox_cli_list(expression: str) -> list:
    result = subprocess.run(
        [
            "checkbox-cli",
            "list",
            "--attrs",
            "--format",
            "json",
            expression,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def register_parser(subparsers):
    parser = subparsers.add_parser(
        "search",
        help="Search for jobs matching a natural language query.",
    )
    parser.add_argument(
        "query",
        help="Natural language search query.",
    )
    parser.add_argument(
        "--job-json",
        type=Path,
        default=None,
        help="Path to the job JSON dump.",
    )
    parser.add_argument(
        "--precise",
        action="store_true",
        default=False,
        help="Run a second LLM pass to verify each candidate.",
    )
    parser.set_defaults(func=run)
    return parser


def run(args):
    if args.job_json is not None:
        jobs = load_json(args.job_json)
    else:
        jobs = checkbox_cli_list("all-jobs")

    results = search_jobs(jobs, args.query, precise=args.precise)

    if not results:
        print("No matching jobs found.")
        return

    for job in results:
        print(job.get("template_id") or job["id"])
