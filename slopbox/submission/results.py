import json
import os
import urllib.error
import urllib.request

C3_ACCESS_TOKEN = os.environ.get("C3_ACCESS_TOKEN")
C3_BASE_URL = "https://certification.canonical.com"


def c3_query(url: str):
    """Query the C3 API and yield results, handling pagination."""
    headers = {"Authorization": f"Bearer {C3_ACCESS_TOKEN}"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"C3 API request failed: {exc.code} {exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"C3 API request failed: {exc.reason}") from exc

    yield from data.get("results", [])

    next_url = data.get("next")
    if next_url:
        yield from c3_query(next_url)


def register_parser(subparsers):
    parser = subparsers.add_parser(
        "results",
        help="Fetch test results for a submission.",
    )
    parser.add_argument(
        "submission_id",
        help="Submission ID to query.",
    )
    parser.set_defaults(func=run)
    return parser


def run(args):
    if not C3_ACCESS_TOKEN:
        raise SystemExit("C3_ACCESS_TOKEN environment variable is required.")
    url = f"{C3_BASE_URL}/api/v2/reports/summary/{args.submission_id}/"
    for result in c3_query(url):
        for test_result in result.get("testresult_set", []):
            print(json.dumps(test_result))
