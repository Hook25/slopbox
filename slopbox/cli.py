import argparse

from slopbox import manifest


def main():
    parser = argparse.ArgumentParser(
        prog="slopbox",
        description="Slopbox CLI toolkit.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    manifest.register_parser(subparsers)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
