import sys
from pathlib import Path

# Running pytests using --pyargs does not run pytest_addoption in conftest.py
# Using workaround as described here:
# https://stackoverflow.com/questions/41270604/using-command-line-parameters-with-pytest-pyargs
HERE = Path(__file__).parent
CONFIG_TESTS = HERE / "config_tests"


def main():
    import pytest

    errcode = pytest.main([str(CONFIG_TESTS)] + sys.argv[1:])
    sys.exit(errcode)


if __name__ == "__main__":
    main()
