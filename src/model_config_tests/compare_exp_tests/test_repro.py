# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

from model_config_tests.exp_test_helper import ExpTestHelper


def get_lab_path(experiment: Path) -> Path:
    """
    Derive the lab path from the experiment configuration directory
    archive symlink
    """
    archive_symlink = experiment / "archive"
    if not archive_symlink.is_symlink():
        raise ValueError(f"Archive symlink does not exist in {experiment}.")

    # experiment/archive symlink points to lab_path/archive/exp_name
    return archive_symlink.resolve().parent.parent


def test_pairwise_repro(experiment_1: Path, experiment_2: Path):
    """
    Compare combinations of experiments to check for reproducibility.
    This is parametrised in conftest with pytest_generate_tests to
    dynamically generate pairs of experiments to compare.
    """

    lab_path1 = get_lab_path(experiment_1)
    exp1 = ExpTestHelper(
        control_path=experiment_1, lab_path=lab_path1, disable_payu_run=True
    )

    lab_path2 = get_lab_path(experiment_2)
    exp2 = ExpTestHelper(
        control_path=experiment_2, lab_path=lab_path2, disable_payu_run=True
    )

    # Compare the two experiments - compares checksums from output000
    exp1_checksums = exp1.model.extract_full_checksums()
    exp2_checksums = exp2.model.extract_full_checksums()
    assert (
        exp1_checksums == exp2_checksums
    ), f"Checksums do not match for {experiment_1.name} and {experiment_2.name} experiments"
