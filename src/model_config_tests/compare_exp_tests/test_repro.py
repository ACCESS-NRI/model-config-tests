# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

from model_config_tests.exp_test_helper import ExpTestHelper


def test_pairwise_repro(experiment_1: Path, experiment_2: Path):
    """
    Compare combinations of experiments to check for reproducibility.
    This is parametrised in conftest with pytest_generate_tests to
    dynamically generate pairs of experiments to compare.
    """

    # control/archive symlink points to lab_path/archive/exp_name
    lab_path1 = (experiment_1 / "archive").resolve().parent.parent
    exp1 = ExpTestHelper(
        control_path=experiment_1, lab_path=lab_path1, disable_payu_run=True
    )

    lab_path2 = (experiment_2 / "archive").resolve().parent.parent
    exp2 = ExpTestHelper(
        control_path=experiment_2, lab_path=lab_path2, disable_payu_run=True
    )

    # Compare the two experiments - compare checksums from output000
    exp1_checksums = exp1.extract_checksums()
    exp2_checksums = exp2.extract_checksums()
    assert (
        exp1_checksums == exp2_checksums
    ), f"Checksums do not match for {experiment_1.name} and {experiment_2.name} experiments"

    # Extend extract checksum option to extract all possible checksums from
    # components, e.g. atmosphere and ocean? Extend the model class methods?
