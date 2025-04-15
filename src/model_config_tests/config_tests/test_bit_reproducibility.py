# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""Tests for model reproducibility"""

import json
from pathlib import Path
from typing import Optional

import pytest

from model_config_tests.exp_test_helper import setup_exp
from model_config_tests.util import DAY_IN_SECONDS, HOUR_IN_SECONDS


def set_checksum_output_dir(output_path: Path):
    """Create an output directory for checksums and remove any pre-existing
    historical checksums. Note: The checksums stored in this directory are
    used in Reproducibility CI workflows, and are copied up to Github"""
    output_dir = output_path / "checksum"
    output_dir.mkdir(parents=True, exist_ok=True)

    pre_existing_files = output_dir.glob("historical-*hr-checksum.json")
    for file in pre_existing_files:
        file.unlink()

    return output_dir


def read_historical_checksums(
    control_path: Path, checksum_filename: str, checksum_path: Optional[Path] = None
):
    """Read a historical checksum file"""
    if checksum_path is None:
        # Default to testing/checksum/historical-*hr-checksums.json
        # stored on model configuration directory
        config_checksum_dir = control_path / "testing" / "checksum"
        checksum_path = config_checksum_dir / checksum_filename

    hist_checksums = None
    if checksum_path.exists():
        with open(checksum_path) as file:
            hist_checksums = json.load(file)

    return hist_checksums


class TestBitReproducibility:

    @pytest.mark.repro
    @pytest.mark.repro_historical
    def test_bit_repro_historical(
        self,
        output_path: Path,
        control_path: Path,
        checksum_path: Optional[Path],
        keep_archive: Optional[bool],
    ):
        """
        Test that a run reproduces historical checksums

        Parameters (these are fixtures defined in conftest.py)
        ----------
        output_path: Path
            Output directory for test output and where the control and
            lab directories are stored for the payu experiments. Default is
            set in conftest.py
        control_path: Path
            Path to the model configuration to test. This is copied for
            for control directories in experiments. Default is set in
            conftests.py
        checksum_path: Optional[Path]
            Path to checksums to compare model output against. Default is
            set to checksums saved on model configuration (set in )
        keep_archive: Optional[bool]
            This flag is used in testing for test code to use a previous test
            archive, and to disable running the model with payu
        """
        # Setup checksum output directory
        checksum_output_dir = set_checksum_output_dir(output_path=output_path)

        # Setup experiment
        exp = setup_exp(
            control_path, output_path, "test_bit_repro_historical", keep_archive
        )

        # Set model runtime using the configured default
        exp.model.set_model_runtime()

        # Run the experiment using payu
        status, stdout, stderr, output_files = exp.setup_and_run()

        if status != 0 or not exp.model.output_exists():
            # Log the run information
            exp.print_run_logs(status, stdout, stderr, output_files)

        assert status == 0, (
            "There was an error running the experiment. "
            "See the logs for more infomation on the experiment run"
        )

        assert exp.model.output_exists(), (
            "Output file for the model does not exist. "
            "See the logs for more information on the experiment run"
        )

        # Set the checksum output filename using the model default runtime
        runtime_hours = exp.model.default_runtime_seconds // HOUR_IN_SECONDS
        checksum_filename = f"historical-{runtime_hours}hr-checksum.json"

        # Read the historical checksum file
        hist_checksums = read_historical_checksums(
            control_path, checksum_filename, checksum_path
        )

        # Use historical file checksums schema version for parsing checksum,
        # otherwise use the model default, if file does not exist
        schema_version = (
            hist_checksums["schema_version"]
            if hist_checksums
            else exp.model.default_schema_version
        )

        # Extract checksums
        checksums = exp.extract_checksums(schema_version=schema_version)

        # Write out checksums to output file
        checksum_output_file = checksum_output_dir / checksum_filename
        with open(checksum_output_file, "w") as file:
            json.dump(checksums, file, indent=2)

        assert (
            hist_checksums == checksums
        ), f"Checksums were not equal. The new checksums have been written to {checksum_output_file}."

    @pytest.mark.repro
    @pytest.mark.repro_repeat
    @pytest.mark.slow
    def test_bit_repro_repeat(self, output_path: Path, control_path: Path):
        """
        Test that a run has same checksums when ran twice
        """
        exp_bit_repo1 = setup_exp(control_path, output_path, "test_bit_repro_repeat_1")
        exp_bit_repo2 = setup_exp(control_path, output_path, "test_bit_repro_repeat_2")

        # Reconfigure to the default model runtime and run
        for exp in [exp_bit_repo1, exp_bit_repo2]:
            exp.model.set_model_runtime()
            exp.setup_and_run()

        # Compare expected to produced.
        assert exp_bit_repo1.model.output_exists()
        expected = exp_bit_repo1.extract_checksums()

        assert exp_bit_repo2.model.output_exists()
        produced = exp_bit_repo2.extract_checksums()

        assert produced == expected

    @pytest.mark.repro
    @pytest.mark.repro_restart
    @pytest.mark.slow
    def test_restart_repro(self, output_path: Path, control_path: Path):
        """
        Test that a run reproduces across restarts.
        """
        # First do two short (1 day) runs.
        exp_2x1day = setup_exp(control_path, output_path, "test_restart_repro_2x1day")

        # Reconfigure to a 1 day run.
        exp_2x1day.model.set_model_runtime(seconds=DAY_IN_SECONDS)

        # Now run twice.
        exp_2x1day.setup_and_run()
        exp_2x1day.force_qsub_run()

        # Now do a single 2 day run
        exp_2day = setup_exp(control_path, output_path, "test_restart_repro_2day")
        # Reconfigure
        exp_2day.model.set_model_runtime(seconds=(2 * DAY_IN_SECONDS))

        # Run once.
        exp_2day.setup_and_run()

        # Now compare the output between our two short and one long run.
        checksums_1d_0 = exp_2x1day.extract_checksums()
        checksums_1d_1 = exp_2x1day.extract_checksums(exp_2x1day.model.output_1)

        checksums_2d = exp_2day.extract_checksums()

        # Use model specific comparision method for checksums
        model = exp_2day.model
        matching_checksums = model.check_checksums_over_restarts(
            long_run_checksum=checksums_2d,
            short_run_checksum_0=checksums_1d_0,
            short_run_checksum_1=checksums_1d_1,
        )

        if not matching_checksums:
            # Write checksums out to file
            with open(output_path / "restart-1d-0-checksum.json", "w") as file:
                json.dump(checksums_1d_0, file, indent=2)
            with open(output_path / "restart-1d-1-checksum.json", "w") as file:
                json.dump(checksums_1d_1, file, indent=2)
            with open(output_path / "restart-2d-0-checksum.json", "w") as file:
                json.dump(checksums_2d, file, indent=2)

        assert matching_checksums
