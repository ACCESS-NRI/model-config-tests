"""Tests for a singular model configuration"""

import sys
from pathlib import Path

# Running pytests using --pyargs does not run pytest_addoption in conftest.py
# Using workaround as described here:
# https://stackoverflow.com/questions/41270604/using-command-line-parameters-with-pytest-pyargs
HERE = Path(__file__)
CONFIG_TESTS_DIR = "config_tests"


def main():
    import pytest

    test_path = str(HERE.parent.parent / CONFIG_TESTS_DIR)

    errcode = pytest.main([test_path] + sys.argv[1:])
    sys.exit(errcode)


if __name__ == "__main__":
    main()
