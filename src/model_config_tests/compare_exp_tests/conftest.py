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
        help="Specify a space separated list of experiment control directories to compare",
    )


def pytest_generate_tests(metafunc):
    """Set up dynamic parametrisation for testing pairwise comparisons
    of input directories"""
    if (
        "experiment_1" in metafunc.fixturenames
        and "experiment_2" in metafunc.fixturenames
    ):
        # Generate pairs of experiments from command input
        input_dirs = metafunc.config.getoption("dirs")
        dir_pairs = get_experiment_pairs(input_dirs)

        # Generate some readable IDs for the pairs
        ids = [f"{exp1.name} vs {exp2.name}" for exp1, exp2 in dir_pairs]
        metafunc.parametrize("experiment_1,experiment_2", dir_pairs, ids=ids)


def get_experiment_pairs(dirs):
    """Generate experiment directory pairs

    Parameters
    ----------
    dirs : str
        Space separated list of directories to compare

    Returns
    -------
    list[tuple[Path, Path]]
        List of pairs of directories to compare
    """
    if dirs is None:
        raise ValueError(
            "No directories specified, use --dirs to specify a space separated list"
        )

    dirs = dirs.split()

    paths = set()
    for dir in dirs:
        # Check if the path exists and is a directory
        path = Path(dir)
        if not path.exists():
            raise ValueError(f"Directory {dir} does not exist")
        if not path.is_dir():
            raise ValueError(f"Path {dir} is not a directory")

        # Resolve to absolute path
        path = path.resolve()
        paths.add(path)

    if len(paths) < 2:
        raise ValueError("Need at least two directories with --dirs to compare")

    paths = sorted(list(paths))
    dir_pairs = list(combinations(paths, 2))
    return dir_pairs
