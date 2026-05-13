import json
import os
import textwrap

from slopbox.submission import bugs as bugs_mod
from slopbox.submission import results as results_mod
from slopbox.utils import query_openai_endpoint

C3_ACCESS_TOKEN = os.environ.get("C3_ACCESS_TOKEN")
C3_BASE_URL = "https://certification.canonical.com"

prompt = textwrap.dedent("""\
    ### SYSTEM
    You are a specialized bug-matching engine.
    Your task is to analyze a failed test result and
    return the IDs of related bugs from the list below.

    ### CONSTRAINTS
    - Output ONLY a comma-separated list of bug IDs.
    - Do NOT provide any preamble, explanation,
      or closing remarks.
    - If no bugs are related, output "none".
    - Only use bug IDs from the approved list below.

    ### APPROVED BUGS
    {bugs_bullet}

    ### EXAMPLE

    <test>
      {{
        "name": "ethernet/detect",
        "status": "fail",
        "comment": "No ethernet device found",
        "category": "Network"
      }}
    </test>
    Bug IDs: 12345

    ### TASK
    Analyze the failed test below and identify related bugs.

    <test>
    {test}
    </test>

    ### BUG IDS:
    """)


def fetch_failed_results(submission_id: str):
    """Fetch failed test results from C3 for a submission."""
    if not C3_ACCESS_TOKEN:
        raise SystemExit("C3_ACCESS_TOKEN environment variable is required.")
    url = f"{C3_BASE_URL}/api/v2/reports/summary/{submission_id}/"
    for result in results_mod.c3_query(url):
        for test_result in result.get("testresult_set", []):
            if test_result.get("status") == "fail":
                yield test_result


def repr_bug(bug: dict) -> str:
    return (
        f"- {bug['id']}: {bug['title']} "
        f"(tags: {', '.join(bug['tags']) or 'none'})"
    )


def run_match(test_result: dict, bug_dicts: list[dict]) -> list[int]:
    """Use an LLM to match a failed test to bug IDs."""
    ids = [str(b["id"]) for b in bug_dicts]
    ids.append("none")
    bugs_bullet = "\n".join(map(repr_bug, bug_dicts))

    test = json.dumps(
        {
            "name": test_result.get("name"),
            "status": test_result.get("status"),
            "comment": test_result.get("comment", ""),
            "category": test_result.get("category", ""),
        }
    )

    for _i in range(5):
        llm_out = query_openai_endpoint(
            prompt.format(test=test, bugs_bullet=bugs_bullet)
        )
        raw_ids = [x.strip() for x in llm_out.split(",")]
        if all(tag in ids for tag in raw_ids):
            if raw_ids == ["none"]:
                return []
            return [int(x) for x in raw_ids if x != "none"]
        else:
            print(f"LLM spitted out garbage: {llm_out}")
    raise ValueError("LLM unable to do it")


def register_parser(subparsers):
    parser = subparsers.add_parser(
        "match",
        help="Match failed test results to Launchpad bugs via LLM.",
    )
    parser.add_argument(
        "submission_id",
        help="Submission ID to fetch failed results from.",
    )
    parser.add_argument(
        "launchpad_project",
        help="Launchpad project to fetch bugs from.",
    )
    parser.add_argument(
        "--milestones",
        type=str,
        default=None,
        help=(
            "Comma-separated list of milestone names to filter bugs by. "
            "If omitted, all bugs are returned."
        ),
    )
    parser.add_argument(
        "--statuses",
        type=str,
        default=None,
        help=(
            "Comma-separated list of bug statuses to include. "
            "If omitted, all known statuses are returned."
        ),
    )
    parser.set_defaults(func=run)
    return parser


def run(args):
    milestones = None
    if args.milestones:
        milestones = [m.strip() for m in args.milestones.split(",")]
    statuses = None
    if args.statuses:
        statuses = [s.strip() for s in args.statuses.split(",")]

    failed_tests = list(fetch_failed_results(args.submission_id))
    if not failed_tests:
        print(json.dumps([]))
        return

    bug_dicts = list(
        bugs_mod.fetch_bugs(
            args.launchpad_project,
            milestones=milestones,
            statuses=statuses,
        )
    )
    if not bug_dicts:
        print(json.dumps([]))
        return

    matched = []
    for test_result in failed_tests:
        matched_bugs = run_match(test_result, bug_dicts)
        test_result["bugs"] = matched_bugs
        matched.append(test_result)

    print(json.dumps(matched))
