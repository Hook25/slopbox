import argparse

from slopbox import job, manifest, submission


def main():
    parser = argparse.ArgumentParser(
        prog="slopbox",
        description="Slopbox CLI toolkit.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    job.register_parser(subparsers)
    manifest.register_parser(subparsers)
    submission.register_parser(subparsers)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
