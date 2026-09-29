import argparse
import os
import shlex

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse !test comment command.")

    parser.add_argument("test_type", help="Test type", choices=["repro"])
    parser.add_argument(
        "-c", "--commit", action="store_true", help="Whether to commit the repro result"
    )
    parser.add_argument(
        "-m",
        "--markers",
        type=str,
        help="Pytest markers string to override ci.json",
        default="",
    )

    # Split the args here rather than in the shell, as they are user-supplied
    args = parser.parse_args(shlex.split(os.environ["COMMAND_ARGS"]))

    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"test-type={args.test_type}\n")
        # We want the outputs to have yaml bools rather than python ones, for GitHub Actions
        output.write(f"requires-commit={'true' if args.commit else 'false'}\n")
        output.write(f"markers={args.markers}\n")
