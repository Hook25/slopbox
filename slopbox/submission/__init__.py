from slopbox.submission import bugs, match, results


def register_parser(subparsers):
    """Register the 'submission' subcommand and its sub-subcommands."""
    parser = subparsers.add_parser(
        "submission",
        help="Submission-related operations.",
    )
    sub = parser.add_subparsers(dest="submission_command")
    sub.required = True
    bugs.register_parser(sub)
    match.register_parser(sub)
    results.register_parser(sub)
    return parser
