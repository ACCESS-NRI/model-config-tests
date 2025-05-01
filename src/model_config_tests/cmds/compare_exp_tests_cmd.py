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

    test_path = str(HERE.parent.parent / COMPARE_EXP_TESTS_DIR)
    os.chdir(test_path)

    errcode = pytest.main([test_path] + sys.argv[1:] + [f"--cwd={original_cwd}"])

    os.chdir(original_cwd)

    sys.exit(errcode)


if __name__ == "__main__":
    main()
