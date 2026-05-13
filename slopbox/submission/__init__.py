from slopbox.submission import results


def register_parser(subparsers):
    """Register the 'submission' subcommand and its sub-subcommands."""
    parser = subparsers.add_parser(
        "submission",
        help="Submission-related operations.",
    )
    sub = parser.add_subparsers(dest="submission_command")
    sub.required = True
    results.register_parser(sub)
    return parser
