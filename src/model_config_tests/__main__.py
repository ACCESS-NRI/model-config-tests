import os
import sys

# Running pytests using --pyargs does not run pytest_addoption in conftest.py
# Using workaround as described here:
# https://stackoverflow.com/questions/41270604/using-command-line-parameters-with-pytest-pyargs
HERE = os.path.dirname(__file__)


def main():
    import pytest

    errcode = pytest.main([HERE] + sys.argv[1:])
    sys.exit(errcode)


if __name__ == "__main__":
    main()
