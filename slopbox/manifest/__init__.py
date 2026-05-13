from slopbox.manifest import assign, generate


def register_parser(subparsers):
    """Register the 'manifest' subcommand and its sub-subcommands."""
    parser = subparsers.add_parser(
        "manifest",
        help="Manifest-related operations.",
    )
    sub = parser.add_subparsers(dest="manifest_command")
    sub.required = True
    assign.register_parser(sub)
    generate.register_parser(sub)
    return parser
