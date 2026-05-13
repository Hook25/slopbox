from slopbox.job import search


def register_parser(subparsers):
    """Register the 'job' subcommand and its sub-subcommands."""
    parser = subparsers.add_parser(
        "job",
        help="Job-related operations.",
    )
    sub = parser.add_subparsers(dest="job_command")
    sub.required = True
    search.register_parser(sub)
    return parser
