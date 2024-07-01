# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""Tests for model reproducibility"""

import json
from pathlib import Path

import pytest

from model_config_tests.exp_test_helper import setup_exp


class TestBitReproducibility:

    @pytest.mark.checksum
    def test_bit_repro_historical(
        self, output_path: Path, control_path: Path, checksum_path: Path
    ):
        """
        Test that a run reproduces historical checksums
        """
        # Setup checksum output directory
        # NOTE: The checksum output file is used as part of `repro-ci` workflows
        output_dir = output_path / "checksum"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Setup experiment
        exp = setup_exp(control_path, output_path, "test_bit_repro_historical")

        # Get model checksum output filename
        runtime_hours = exp.model.default_runtime_seconds // 3600
        checksum_filename = f"historical-{runtime_hours}hr-checksum.json"

        # Remove any pre-existing checksums files from output directory
        checksum_output_file = output_dir / checksum_filename
        if checksum_output_file.exists():
            checksum_output_file.unlink()

        # Set model runtime using the configured default
        exp.model.set_model_runtime()

        # Run Experiment
        exp.setup_and_run()

        assert exp.model.output_exists(), "Output file for model does not exist"

        # Check checksum against historical checksum file
        hist_checksums = None
        hist_checksums_schema_version = None

        if checksum_path is None:
            # Default to testing/checksum/historical-*hr-checksums.json
            # stored on model configuration directory
            config_checksum_dir = control_path / "testing" / "checksum"
            checksum_path = config_checksum_dir / checksum_filename

        # Get checksum file version
        if (
            not checksum_path.exists()
        ):  # AKA, if the config branch doesn't have a checksum, or the path is misconfigured
            hist_checksums_schema_version = exp.model.default_schema_version
        else:  # we can use the historic-*hr-checksum that is in the testing directory
            with open(checksum_path) as file:
                hist_checksums = json.load(file)

                # Parse checksums using the same version
                hist_checksums_schema_version = hist_checksums["schema_version"]

        checksums = exp.extract_checksums(schema_version=hist_checksums_schema_version)

        # Write out checksums to output file
        with open(checksum_output_file, "w") as file:
            json.dump(checksums, file, indent=2)

        assert (
            hist_checksums == checksums
        ), f"Checksums were not equal. The new checksums have been written to {checksum_output_file}."

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

    @pytest.mark.checksum
    def test_restart_repro(self, output_path: Path, control_path: Path):
        """
        Test that a run reproduces across restarts.
        """
        # First do two short (1 day) runs.
        exp_2x1day = setup_exp(control_path, output_path, "test_restart_repro_2x1day")

        # Reconfigure to a 1 day run.
        exp_2x1day.model.set_model_runtime(seconds=86400)

        # Now run twice.
        exp_2x1day.setup_and_run()
        exp_2x1day.force_qsub_run()

        # Now do a single 2 day run
        exp_2day = setup_exp(control_path, output_path, "test_restart_repro_2day")
        # Reconfigure
        exp_2day.model.set_model_runtime(seconds=172800)

        # Run once.
        exp_2day.setup_and_run()

        # Now compare the output between our two short and one long run.
        checksums_1d_0 = exp_2x1day.extract_checksums()
        checksums_1d_1 = exp_2x1day.extract_checksums(exp_2x1day.output001)

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
