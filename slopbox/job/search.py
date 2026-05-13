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

NARROW_KEYWORDS_PROMPT = textwrap.dedent("""\
    ### SYSTEM
    You are a keyword extraction engine for narrowing search
    results. The user query has both a general context and a
    specific focus. You must output keywords ONLY for the
    specific focus, ignoring the general context entirely.

    ### CONSTRAINTS
    - Output ONLY a comma-separated list of lowercase keywords.
    - Include abbreviations, acronyms, and alternate spellings.
    - IGNORE the general/broad context of the query. Assume all
      results already match the broad topic.
    - Only output keywords for the SPECIFIC sub-topic or detail
      the user is asking about.
    - Do NOT include generic QA/testing terms.
    - Do NOT provide any preamble, explanation,
      or closing remarks.

    ### EXAMPLE
    Query: "wifi ac scanning tests"
    Narrow keywords: ac 802.11ac
    -> Note: general topic is wifi, don't include it

    Query: "bluetooth audio A2DP codec tests"
    Narrow keywords: a2dp

    ### QUERY
    {query}

    ### NARROW KEYWORDS:
    """)


def extract_narrow_keywords(query):
    """Ask the LLM to generate narrow/specific keywords from the query."""
    response = query_openai_endpoint(
        NARROW_KEYWORDS_PROMPT.format(query=query),
        thinking=False,
    )
    return [k.strip().lower() for k in response.split(",") if k.strip()]


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


def keyword_matches(kw, tokens):
    """Check if a keyword matches the token set.

    If the keyword contains a space, all parts must be present.
    """
    if " " in kw:
        return all(part in tokens for part in kw.split())
    return kw in tokens


def keyword_filter(jobs, keywords):
    """Pre-filter jobs, ordered by number of matching keywords.

    If any job scores above the median, only return those.
    """
    scored = []
    for job in jobs:
        tokens = job_tokens(job)
        score = sum(1 for kw in keywords if keyword_matches(kw, tokens))
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


def search_jobs(jobs, query, *, precise=False):
    """Search over jobs.

    Pass 1: LLM generates broad keywords, then token-match filter.
    Pass 2 (precise only): LLM generates narrow keywords specific
    to the sub-topic, then further filters by those.
    """
    # Pass 1: keyword extraction + string filtering
    print("Extracting keywords...")
    keywords = extract_keywords(query)
    print(f"Keywords: {', '.join(keywords)}")
    print(f"Filtering {len(jobs)} jobs...")
    candidates = keyword_filter(jobs, keywords)
    print(f"Pre-filter matched {len(candidates)} jobs.")

    if not candidates:
        return []

    if not precise:
        return candidates

    # Pass 2: narrow keyword filtering
    print("Extracting narrow keywords...")
    narrow_kws = extract_narrow_keywords(query)
    print(f"Narrow keywords: {', '.join(narrow_kws)}")
    print(f"Narrowing {len(candidates)} candidates...")
    narrowed = keyword_filter(candidates, narrow_kws)
    print(f"Narrow filter matched {len(narrowed)} jobs.")

    return narrowed if narrowed else candidates


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
