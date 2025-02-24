import argparse
import json
import re


def get_config_value(config, test_type, reference, key):
    """
    Retrieve the value for a given key from the nested structure of the JSON file.
    It first checks the specific 'test_type' and 'reference', then checks
    for a regex match with the 'reference', and then falls back to the default
    values if key is not found.

    Parameters:
    config (dict): The dictionary containing the CI configuration.
    test_type (str): Type of check/test to run (e.g., "reproducibility", "qa", or "scheduled").
    reference (str): Name of Git branch or tag to run CI testing on.
    key (str): The key to retrieve the value for (e.g. "python-version").

    Returns:
    str: The value associated with the key.
    """
    # Check for exact match of test_type and reference
    value = config.get(test_type, {}).get(reference, {}).get(key)
    if value:
        return value

    # Check for reference regex match with a key defined with priority given
    # to the first match found (so top-down order matters)
    for pattern in config.get(test_type, {}):
        # Use fullmatch to require entire string to match pattern exactly
        match = re.fullmatch(pattern, reference)
        if match and config[test_type][pattern].get(key):
            return config[test_type][pattern].get(key)

    # Check for default values for test type and the top-level default
    return config.get(test_type, {}).get("default", {}).get(key) or config.get(
        "default", {}
    ).get(key)


def parse_ci_config(test_type, reference, filepath):
    """
    Parse the CI configuration file and extract the test configuration
    for a given test type and reference.

    Parameters:
    test_type (str): Type of check/test to run (e.g., "reproducibility", "qa", or "scheduled").
    reference (str): Name of Git branch or tag to run CI testing on.
    filepath (str): Path to the CI configuration file.

    Returns:
    dict: A dictionary containing the extracted values for 'model-config-tests-version',
          'python-version', 'markers', and 'payu-version'.
    """
    with open(filepath) as file:
        config = json.load(file)

    model_config_tests_version = get_config_value(
        config, test_type, reference, "model-config-tests-version"
    )
    python_version = get_config_value(config, test_type, reference, "python-version")
    markers = get_config_value(config, test_type, reference, "markers")
    payu_version = get_config_value(config, test_type, reference, "payu-version")

    return {
        "model-config-tests-version": model_config_tests_version,
        "python-version": python_version,
        "markers": markers,
        "payu-version": payu_version,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse CI configuration file.")
    parser.add_argument(
        "--test-type",
        required=True,
        help="Type of check/test to run (e.g., 'reproducibility', 'qa', or 'scheduled').",
    )
    parser.add_argument(
        "--reference",
        required=True,
        help="Name of Git branch or tag to run CI testing on.",
    )
    parser.add_argument(
        "--config-filepath", required=True, help="Path to the CI configuration file."
    )
    parser.add_argument(
        "--output-filepath",
        required=False,
        help="Path to the output file to save the results.",
    )

    args = parser.parse_args()

    test_type = args.test_type
    reference = args.reference
    filepath = args.config_filepath
    output_filepath = args.output_filepath

    result = parse_ci_config(test_type, reference, filepath)

    if output_filepath:
        with open(output_filepath, "w") as output_file:
            json.dump(result, output_file, indent=4)
    else:
        for key, value in result.items():
            print(f"{key}: {value}")
