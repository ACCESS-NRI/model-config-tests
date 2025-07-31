# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""Tests for model reproducibility"""

import json
from pathlib import Path
from typing import Optional

import pytest

from model_config_tests.exp_test_helper import Experiments, ExpTestHelper
from model_config_tests.util import DAY_IN_SECONDS, HOUR_IN_SECONDS

# Names of shared experiments
EXP_DEFAULT_RUNTIME = "exp_default_runtime"
EXP_1D_RUNTIME = "exp_1d_runtime"
EXP_2D_RUNTIME = "exp_2d_runtime"
EXP_1D_RUNTIME_REPEAT = "exp_1d_runtime_repeat"


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


def _experiments(
    markers: list, output_path: Path, control_path: Path, keep_archive: Optional[bool]
) -> Experiments:
    """
    Run all requested experiments

    Parameters
    ----------
    markers: list
        A list of requested experiments markers
    output_path: Path
        Output directory for test output and where the control and
        lab directories are stored for the payu experiments.
    control_path: Path
        Path to the model configuration to test. This is copied for
        control directories in experiments.
    keep_archive: Optional[bool]
        Whether to keep the previous archive for each experiment and
        disable calls to payu run. This is used in testing.

    Returns
    -------
    Experiments
        Object that stores the shared experiments
    """
    # Check for common experiments
    requested_experiments = {}
    for marker in markers:
        for exp_name, config in marker.items():
            n_runs = config.get("n_runs", 1)
            model_runtime = config.get("model_runtime", None)

            if exp_name not in requested_experiments:
                requested_experiments[exp_name] = {
                    "n_runs": n_runs,
                    "model_runtime": model_runtime,
                }
            else:
                requested_experiment = requested_experiments[exp_name]
                # Check model runtime is the same for all experiments
                # with the same name
                if requested_experiment["model_runtime"] != model_runtime:
                    raise ValueError(
                        f"Experiment {exp_name} has conflicting model runtimes: "
                        f"{requested_experiment['model_runtime']} and {model_runtime}"
                    )

                # Set the max number of runs
                requested_experiments[exp_name]["n_runs"] = max(
                    requested_experiment["n_runs"], n_runs
                )

    # Cleaning up any pre-existing historical checksums output first
    # incase there's failures in setup
    set_checksum_output_dir(output_path=output_path)

    print("Submitting all requested experiments")
    experiments = Experiments(control_path, output_path, keep_archive)
    for exp_name, config in requested_experiments.items():
        experiments.setup_and_submit(
            exp_name=exp_name,
            model_runtime=config["model_runtime"],
            n_runs=config["n_runs"],
        )

    # Wait for experiments to finish here and catching errors as some
    # some experiments may finish without errors so errors will be raised
    # instead in the tests if an dependent experiment fails
    experiments.wait_for_all_experiments(catch_errors=True)

    return experiments


@pytest.fixture(scope="class")
def experiments(
    request, output_path: Path, control_path: Path, keep_archive: Optional[bool]
):
    """
    Parse the experiments markers from the requested tests and
    submit all necessary experiments at the same time.

    The scope is class so the experiments are only run once before all repro
    tests.
    """

    # Parse the experiments markers from the requested tests
    experiments_markers = []
    for item in request.session.items:
        if item.parent == request.node:
            marker = item.get_closest_marker("experiments")
            if marker:
                experiments_markers.append(marker.args[0])

    return _experiments(experiments_markers, output_path, control_path, keep_archive)


@pytest.fixture
def requested_experiments(request, experiments: Experiments):
    """Fixture to check that requested experiments have run successfully
    and return a dictionary of ExpTestHelper instances for each experiment."""
    exp_marker = request.node.get_closest_marker("experiments").args[0]
    requested_exps = {}
    for exp_name in exp_marker:
        # Check experiment has run successfully - this will raise an
        # error if there are any non-zero exit codes in the outputs
        experiments.check_experiment(exp_name)
        requested_exps[exp_name] = experiments.get_experiment(exp_name)
    return requested_exps


class TestBitReproducibility:

    @pytest.mark.repro
    @pytest.mark.repro_historical
    @pytest.mark.experiments(
        {
            EXP_DEFAULT_RUNTIME: {"n_runs": 1},
        }
    )
    def test_repro_historical(
        self,
        output_path: Path,
        control_path: Path,
        requested_experiments: dict[str, ExpTestHelper],
        checksum_path: Optional[Path],
    ):
        """
        Historical reproducibility test that confirms results from a model
        run match a stored previous result. Any generated results are
        added to a "checksum" subdirectory in the output directory.

        Parameters
        ----------
        output_path: Path
            Output directory for test output and where the control and
            lab directories are stored for the payu experiments. Default is
            set in conftest.py.
        control_path: Path
            Path to the model configuration to test. This is copied for
            for control directories in experiments. Default is set in
            conftests.py.
        requested_experiments: dict[str, ExpTestHelper]
            A dictionary of requested experiments, where the key is the
            experiment name and the value is an instance of ExpTestHelper.
        checksum_path: Optional[Path]
            Path to checksums to compare model output against. Default is
            set to checksums saved on model configuration. This is a
            fixture defined in conftests.py
        """
        # Get output directory for the checksums
        checksum_output_dir = set_checksum_output_dir(output_path=output_path)

        # Use default runtime experiment to get the historical checksums
        exp = requested_experiments.get(EXP_DEFAULT_RUNTIME)

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
    @pytest.mark.repro_determinism
    @pytest.mark.slow
    @pytest.mark.experiments(
        {
            EXP_1D_RUNTIME: {"n_runs": 1, "model_runtime": DAY_IN_SECONDS},
            EXP_1D_RUNTIME_REPEAT: {"n_runs": 1, "model_runtime": DAY_IN_SECONDS},
        }
    )
    def test_repro_determinism(self, requested_experiments: dict[str, ExpTestHelper]):
        """
        Determinism test that confirms repeated model runs for 1 day
        give the same results
        """
        exp_1d_runtime = requested_experiments.get(EXP_1D_RUNTIME)
        exp_1d_runtime_repeat = requested_experiments.get(EXP_1D_RUNTIME_REPEAT)

        # Compare expected to produced.
        expected = exp_1d_runtime.extract_checksums()
        produced = exp_1d_runtime_repeat.extract_checksums()

        assert produced == expected

    @pytest.mark.repro
    @pytest.mark.repro_restart
    @pytest.mark.slow
    @pytest.mark.experiments(
        {
            EXP_1D_RUNTIME: {"n_runs": 2, "model_runtime": DAY_IN_SECONDS},
            EXP_2D_RUNTIME: {"n_runs": 1, "model_runtime": 2 * DAY_IN_SECONDS},
        }
    )
    def test_repro_restart(
        self, output_path: Path, requested_experiments: dict[str, ExpTestHelper]
    ):
        """
        Restart reproducibility test that confirms two short consecutive
        1-day model runs give the same results as a longer single 2-day model
        run.
        """
        # Get experiments with 2x1 day and 2 day runtimes
        exp_1d_runtime = requested_experiments.get(EXP_1D_RUNTIME)
        exp_2d_runtime = requested_experiments.get(EXP_2D_RUNTIME)

        # Now compare the output between our two short and one long run.
        checksums_1d_0 = exp_1d_runtime.extract_checksums()
        checksums_1d_1 = exp_1d_runtime.extract_checksums(exp_1d_runtime.model.output_1)

        checksums_2d = exp_2d_runtime.extract_checksums()

        # Use model specific comparision method for checksums
        model = exp_2d_runtime.model
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

    @pytest.mark.repro_determinism_restart
    @pytest.mark.experiments(
        {
            EXP_1D_RUNTIME: {"n_runs": 2, "model_runtime": DAY_IN_SECONDS},
            EXP_1D_RUNTIME_REPEAT: {"n_runs": 2, "model_runtime": DAY_IN_SECONDS},
        }
    )
    def test_repro_determinism_restart(
        self, requested_experiments: dict[str, ExpTestHelper]
    ):
        """
        Determinism test that confirms repeated experiments with two
        consecutive 1-day model runs give the same results
        """
        exp_1d_runtime = requested_experiments.get(EXP_1D_RUNTIME)
        exp_1d_runtime_repeat = requested_experiments.get(EXP_1D_RUNTIME_REPEAT)

        # Extract checksums, using the output from the second model run
        expected = exp_1d_runtime.extract_checksums(exp_1d_runtime.model.output_1)
        produced = exp_1d_runtime_repeat.extract_checksums(
            exp_1d_runtime_repeat.model.output_1
        )

        assert produced == expected
