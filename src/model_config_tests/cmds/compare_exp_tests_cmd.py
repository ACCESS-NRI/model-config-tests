"""Tests for comparing multiple experiments results"""

import sys
from pathlib import Path

# Running pytests using --pyargs does not run pytest_addoption in conftest.py
# Using workaround as described here:
# https://stackoverflow.com/questions/41270604/using-command-line-parameters-with-pytest-pyargs
HERE = Path(__file__)
COMPARE_EXP_TESTS_DIR = "compare_exp_tests"


def main():
    import pytest

    test_path = str(HERE.parent.parent / COMPARE_EXP_TESTS_DIR)

    # Specify --rootdir to shorten relative paths in displayed test output
    errcode = pytest.main([test_path] + sys.argv[1:] + [f"--rootdir={test_path}"])

    sys.exit(errcode)


if __name__ == "__main__":
    main()
