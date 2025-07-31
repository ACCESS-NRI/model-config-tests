import argparse
import xml.etree.ElementTree as ET


def parse_pytest_junit_xml(filepath: str) -> dict:
    """
    Parse a pytest junit XML file and extract the test results.

    Parameters:
    filepath (str): Path to the pytest junit XML file.

    Returns:
    dict: A dictionary containing the test results split into passed, errors,
    failures, and skipped.
    """

    tree = ET.parse(filepath)
    root = tree.getroot()

    results = {
        "passed": [],
        "errors": [],
        "failures": [],
        "skipped": [],
    }

    for testcase in root.iter("testcase"):
        name = testcase.get("name")
        if testcase.find("error") is not None:
            results["errors"].append(name)
        elif testcase.find("failure") is not None:
            results["failures"].append(name)
        elif testcase.find("skipped") is not None:
            results["skipped"].append(name)
        else:
            results["passed"].append(name)
    return results


def format_test_name_results(test_results: dict) -> str:
    """
    Format the test results into a readable string.

    Parameters:
    test_results (dict): The dictionary containing the test results.

    Returns:
    str: A formatted string listing the test names of test errors, failures
    and passed (leaving skipped tests out of the summary).
    """
    summary = []
    for test in test_results["errors"]:
        summary.append(f":fire: `{test}`")
    for test in test_results["failures"]:
        summary.append(f":x: `{test}`")
    for test in test_results["passed"]:
        summary.append(f":white_check_mark: `{test}`")
    return "\n".join(summary)


if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Parse CI configuration file.")
    parser.add_argument(
        "--filepath",
        required=True,
        help="Path to pytest junit XML file to parse",
    )
    parser.add_argument(
        "--output-filepath",
        required=False,
        help="Path to the output file to save the results.",
    )
    args = parser.parse_args()
    filepath = args.filepath
    output_filepath = args.output_filepath

    # Parse the XML file and format the results
    result = parse_pytest_junit_xml(filepath)
    formatted_results = format_test_name_results(result)

    # Save the summary to a file
    if output_filepath:
        with open(output_filepath, "w") as output_file:
            # Github output multiline strings needs a trailing newline
            output_file.write(formatted_results.rstrip() + "\n")

    print(formatted_results)
