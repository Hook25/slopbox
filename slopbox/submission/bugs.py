import json
import sys
from collections.abc import Iterable

from launchpadlib.launchpad import Launchpad

ALL_STATUSES: list[str] = [
    "New",
    "Incomplete",
    "Opinion",
    "Invalid",
    "Won't Fix",
    "Expired",
    "Confirmed",
    "Triaged",
    "In Progress",
    "Fix Committed",
    "Fix Released",
]


def _get_launchpad():
    """Log in to Launchpad via cached credentials."""
    return Launchpad.login_with("slopbox", "production", version="devel")


def _task_to_dict(task):
    """Convert a Launchpad bug task to a plain dict."""
    bug = task.bug
    return {
        "id": bug.id,
        "url": bug.web_link,
        "status": task.status,
        "title": bug.title,
        "tags": list(bug.tags),
        "description": bug.description,
    }


def _find_milestone_url(project, name: str) -> str | None:
    """Look up a milestone URL by name on a project."""
    for milestone in project.all_milestones:
        if milestone.name == name:
            return milestone.self_link
    return None


def _search_tasks(
    project,
    *,
    statuses: Iterable[str] | None = None,
    milestone: str | None = None,
):
    """Call project.searchTasks() with the full status list by default."""
    kwargs = {}
    if milestone is not None:
        kwargs["milestone"] = milestone
    if statuses is not None:
        kwargs["status"] = list(statuses)
    else:
        kwargs["status"] = ALL_STATUSES
    return project.searchTasks(**kwargs)


def fetch_bugs(
    project_name: str,
    milestones: list[str] | None = None,
    statuses: list[str] | None = None,
):
    """Fetch bugs for a Launchpad project and yield bug dicts."""
    launchpad = _get_launchpad()
    project = launchpad.projects[project_name]

    if not milestones:
        for task in _search_tasks(project, statuses=statuses):
            yield _task_to_dict(task)
        return

    seen_ids: set[int] = set()
    for ms_name in milestones:
        ms_url = _find_milestone_url(project, ms_name)
        if ms_url is None:
            print(
                f"Warning: milestone '{ms_name}' not found",
                file=sys.stderr,
            )
            continue
        for task in _search_tasks(
            project, statuses=statuses, milestone=ms_url
        ):
            bug_id = task.bug.id
            if bug_id not in seen_ids:
                seen_ids.add(bug_id)
                yield _task_to_dict(task)


def register_parser(subparsers):
    parser = subparsers.add_parser(
        "bugs",
        help="Fetch bugs for a Launchpad project.",
    )
    parser.add_argument(
        "launchpad_project",
        help="Launchpad project name to query.",
    )
    parser.add_argument(
        "--milestones",
        type=str,
        default=None,
        help=(
            "Comma-separated list of milestone names to filter by. "
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
    bugs = list(
        fetch_bugs(
            args.launchpad_project,
            milestones=milestones,
            statuses=statuses,
        )
    )
    print(json.dumps(bugs))
