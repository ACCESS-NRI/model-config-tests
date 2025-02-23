import json

import pytest
from parse_file import get_config_value, parse_ci_config


@pytest.mark.parametrize(
    "config, test_type, reference, key, expected",
    [
        # Test when key is set for reference (e.g. tag or branch)
        (
            {
                "reproducibility": {
                    "branch_name_1": {
                        "payu-version": "1.1.3",
                    },
                    "default": {
                        "payu-version": "1.1.5",
                    },
                },
                "default": {
                    "payu-version": "1.1.6",
                },
            },
            "reproducibility",
            "branch_name_1",
            "payu-version",
            "1.1.3",
        ),
        # Test when key is not set for reference but set in test default
        (
            {
                "reproducibility": {
                    "default": {
                        "payu-version": "1.1.5",
                    }
                },
                "default": {
                    "payu-version": "1.1.6",
                },
            },
            "reproducibility",
            "branch_name_1",
            "payu-version",
            "1.1.5",
        ),
        # Test when the key is not found in the test_type and reference
        (
            {
                "reproducibility": {
                    "default": {
                        "markers": "default-repro",
                    }
                },
                "default": {
                    "payu-version": "1.1.6",
                },
            },
            "reproducibility",
            "branch_name_1",
            "payu-version",
            "1.1.6",
        ),
        # Test when reference matches a regex pattern
        (
            {
                "qa": {
                    "dev-*": {"markers": "dev_config"},
                    "default": {"markers": "config or dev_config"},
                },
            },
            "qa",
            "dev_branch1",
            "markers",
            "dev_config",
        ),
        # Test exact match takes precedence over regex match
        (
            {
                "qa": {
                    "dev-*": {"markers": "dev_config"},
                    "dev_branch1": {"markers": "another_marker"},
                    "default": {"markers": "config or dev_config"},
                },
            },
            "qa",
            "dev_branch1",
            "markers",
            "another_marker",
        ),
        # Test for the longest regex match for the branch name
        (
            {
                "qa": {
                    "dev-*": {"markers": "dev_config"},
                    "dev_branch*": {"markers": "another_marker"},
                    "default": {"markers": "config or dev_config"},
                },
            },
            "qa",
            "dev_branch1",
            "markers",
            "another_marker",
        ),
        # Test if regex match for branch name but payu-version is not found
        (
            {
                "qa": {
                    "dev-*": {"markers": "dev_config"},
                    "dev_branch*": {"markers": "another_marker"},
                    "default": {"markers": "config or dev_config"},
                },
                "default": {"payu-version": "1.0.0"},
            },
            "qa",
            "dev_branch1",
            "payu-version",
            "1.0.0",
        ),
    ],
)
def test_get_config_value(config, test_type, reference, key, expected):
    assert get_config_value(config, test_type, reference, key) == expected


@pytest.fixture
def sample_config():
    return {
        "reproducibility": {
            "release-1deg_jra55_ryf": {
                "markers": "repro or repro_slow",
            },
            "dev-*": {
                "payu-version": "dev",
            },
            "dev-branch-*": {
                "payu-version": "2.0.0",
            },
            "dev-branch-1": {
                "payu-version": "3.0.0",
            },
            "default": {
                "markers": "default-repro",
            },
        },
        "qa": {
            "dev-*": {
                "markers": "config_dev",
            },
            "default": {
                "markers": "config or config_dev",
            },
        },
        "default": {
            "model-config-tests-version": "1.2.0",
            "python-version": "3.10",
            "payu-version": "2.0.0",
        },
    }


def test_parse_ci_config(sample_config, tmp_path):
    config_file = tmp_path / "ci.json"
    with open(config_file, "w") as f:
        json.dump(sample_config, f)

    result = parse_ci_config("reproducibility", "release-1deg_jra55_ryf", config_file)
    assert result == {
        "model-config-tests-version": "1.2.0",
        "python-version": "3.10",
        "markers": "repro or repro_slow",
        "payu-version": "2.0.0",
    }

    result = parse_ci_config("reproducibility", "dev-something", config_file)
    assert result == {
        "model-config-tests-version": "1.2.0",
        "python-version": "3.10",
        "markers": "default-repro",
        "payu-version": "dev",
    }
