import argparse
import os
import re
import shlex

COMMAND_PREFIX = "!test"


def pytest_marker_string(marker: str) -> str:
    # Pytest markers are a subset of python conditionals, so we should accept only
    # valid python identifier values - protects against invalid inputs.
    if not re.fullmatch(r"[a-zA-Z0-9_ ()]*", marker):
        raise argparse.ArgumentTypeError(f"The marker string '{marker}' is not valid.")
    return marker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse !test comment command.")

    parser.add_argument("test_type", help="Test type", choices=["repro"])
    parser.add_argument(
        "-c", "--commit", action="store_true", help="Whether to commit the repro result"
    )
    parser.add_argument(
        "-m",
        "--markers",
        type=pytest_marker_string,
        help="Pytest markers string to override ci.json",
        default="",
    )
    return parser


def parse_command(command_body: str) -> argparse.Namespace:
    """Parse the arguments out of a `!test` comment body."""
    # Take just the first line of the comment body and strip the leading !test
    lines = command_body.splitlines()
    first_line = lines[0] if lines else ""
    command_args = first_line[len(COMMAND_PREFIX) :].strip()

    parser = build_parser()

    # Split the args here rather than in the shell, as they are user-supplied
    argv = shlex.split(command_args)

    return parser.parse_args(argv)


def format_outputs(args: argparse.Namespace) -> str:
    """Render the parsed args as GitHub Actions `key=value` output lines."""
    return (
        f"test-type={args.test_type}\n"
        # We want the outputs to have yaml bools rather than python ones, for GitHub Actions
        f"requires-commit={'true' if args.commit else 'false'}\n"
        f"markers={args.markers}\n"
    )


def main() -> None:
    args = parse_command(os.environ["COMMAND_BODY"])

    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(format_outputs(args))


if __name__ == "__main__":
    main()
