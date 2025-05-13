"""Tests for comparing multiple experiments results"""

import os
import sys
from pathlib import Path

# Running pytests using --pyargs does not run pytest_addoption in conftest.py
# Using workaround as described here:
# https://stackoverflow.com/questions/41270604/using-command-line-parameters-with-pytest-pyargs
HERE = Path(__file__)
COMPARE_EXP_TESTS_DIR = "compare_exp_tests"


def main():
    import pytest

    original_cwd = os.getcwd()

    # Set the current working directory to the test directory
    # so the pytest output uses relative paths to this directory
    test_path = str(HERE.parent.parent / COMPARE_EXP_TESTS_DIR)

    try:
        os.chdir(test_path)

        # Run pytests
        errcode = pytest.main([test_path] + sys.argv[1:] + [f"--cwd={original_cwd}"])
    finally:
        # Restore the original working directory
        os.chdir(original_cwd)

    sys.exit(errcode)


if __name__ == "__main__":
    main()
