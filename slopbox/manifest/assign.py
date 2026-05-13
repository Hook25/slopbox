import json
import subprocess
import textwrap
from pathlib import Path

from slopbox.utils import query_openai_endpoint

prompt = textwrap.dedent("""\
    ### SYSTEM
    You are a specialized text classification engine.
    Your task is to analyze the provided test
    and return applicable topic tags.

    ### CONSTRAINTS
    - Output ONLY a comma-separated list of tags.
    - Do NOT provide any preamble, explanation,
      or closing remarks.
    - If no tags apply, output "none".
    - Only use tags from the approved list below.

    ### APPROVED CATEGORIES
    {tags_bullet}

    ### EXAMPLE

    <test>
      {{
        "category_id":
          "com.canonical.plainbox::ethernet",
        "id": "ethernet/detect",
        "command":
          "network_device_info.py detect NETWORK",
        "_summary":
          "Detect if at least one ethernet device"
          " is detected",
        "_purpose":
          "Test to detect and return information"
          " about available network controllers"
          " on\\nthe system under test.",
      }}
    </test>
    Tags: has_ethernet_adapter

    ### TASK
    Analyze the test below and identify the relevant tags.

    <test>
    {test}
    </test>

    ### TAGS:
    """)


def relevant_manifests(manifest) -> bool:
    if manifest["id"].startswith("2021"):
        return False  # metabox
    return not manifest["id"].rsplit(":", 1)[1].startswith("_")


def prune_job(job_dct):
    keep_keys = {
        "partial_id",
        "description",
        "command",
        "purpose",
        "steps",
        "validation",
        "summary",
        "category",
    }
    items = ((x.removeprefix("_"), y) for x, y in job_dct.items())
    items = ((x, y) for x, y in items if x in keep_keys)
    to_r = {x: y for (x, y) in items}
    to_r["name"] = to_r["summary"]
    del to_r["summary"]
    return to_r


def repr_manifest(manifest):
    return f"- {manifest['id'].rsplit(':', 1)[1]}: {manifest['name']}"


def get_manifest_ids(manifests):
    return [x["id"].rsplit(":", 1)[1] for x in manifests]


def run_prompt(manifests, job_dct):
    rel_manifests = list(filter(relevant_manifests, manifests))
    ids = get_manifest_ids(rel_manifests)
    ids += ["none"]
    manifests_bullet = map(repr_manifest, rel_manifests)
    manifests_bullet = "\n".join(manifests_bullet)
    job_dct = prune_job(job_dct)
    test = json.dumps(job_dct)
    for _i in range(5):
        llm_out = query_openai_endpoint(
            prompt.format(test=test, tags_bullet=manifests_bullet)
        )
        tags = [x.strip() for x in llm_out.split(",")]
        if all(tag in ids for tag in tags):
            return tags
        else:
            print(f"LLM spitted out garbage: {llm_out}")
    raise ValueError("LLM unable to do it")


def load_json(path: Path) -> dict:
    with path.open("r") as f:
        return json.load(f)


def checkbox_cli_list(expression: str) -> list:
    result = subprocess.run(
        ["checkbox-cli", "list", "--attrs", "--format", "json", expression],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def register_parser(subparsers):
    parser = subparsers.add_parser(
        "assign",
        help="Classify tests against manifest tags using an LLM.",
    )
    parser.add_argument("job_id", help="Job ID to classify.")
    parser.add_argument(
        "--manifest-json",
        type=Path,
        default=None,
        help="Path to the manifest JSON file",
    )
    parser.add_argument(
        "--job-json",
        type=Path,
        default=None,
        help="Path to the job JSON dump",
    )
    parser.set_defaults(func=run)
    return parser


def run(args):
    if args.manifest_json is not None:
        manifests = load_json(args.manifest_json)
    else:
        manifests = checkbox_cli_list("manifest entry")

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

    manifests = run_prompt(manifests, job)
    for manifest in manifests:
        print(manifest)
