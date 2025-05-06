# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0
from itertools import combinations
from pathlib import Path


# Set up command line options and default for directory paths
def pytest_addoption(parser):
    """Attaches custom command line arguments"""
    parser.addoption(
        "--dirs",
        action="store",
        help="Specify a space separated list of experiment control dirctories to compare",
    )
    parser.addoption("--cwd", action="store", default=None)


import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def restore_cwd(request):
    orig_cwd = request.config.getoption("--cwd")
    if orig_cwd:
        os.chdir(orig_cwd)


def pytest_generate_tests(metafunc):
    # Set up dynamic parametrisation for testing pairwise comparisons
    if (
        "experiment_1" in metafunc.fixturenames
        and "experiment_2" in metafunc.fixturenames
    ):
        # Generate pairs of experiments from command input
        input_dirs = metafunc.config.getoption("dirs")
        cwd = Path(metafunc.config.getoption("--cwd"))
        dir_pairs = get_experiment_pairs(input_dirs, cwd)

        # Generate some readable IDs for the pairs
        ids = [f"{exp1.name} vs {exp2.name}" for exp1, exp2 in dir_pairs]
        metafunc.parametrize("experiment_1,experiment_2", dir_pairs, ids=ids)


def get_experiment_pairs(dirs, cwd):
    """Return a set of absolute paths to directories to compare"""
    if dirs is None:
        raise ValueError(
            "No directories specified, use --dirs to specify a space separated list"
        )

    dirs = dirs.split(" ")

    paths = set()
    for dir in dirs:
        # Check if the path exists and is a directory
        path = Path(dir)
        if not path.is_absolute():
            # Assume path is relative to the original current working directory
            path = cwd / path
        if not path.exists():
            raise ValueError(f"Directory {dir} does not exist")
        if not path.is_dir():
            raise ValueError(f"Path {dir} is not a directory")

        # Resolve to absolute path
        path = path.resolve()
        paths.add(path)

    if len(paths) < 2:
        raise ValueError("Need at least two directories with --dirs to compare")

    dir_pairs = list(combinations(paths, 2))
    return dir_pairs
