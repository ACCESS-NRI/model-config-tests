"""Test for bit reproducibility tests"""

import shlex
import shutil
import subprocess
import warnings
from pathlib import Path
from unittest.mock import Mock, patch

import f90nml
import pytest
import yaml
from netCDF4 import Dataset
from payu.models.cesm_cmeps import Runconfig

from tests.common import RESOURCES_DIR

# Disable unknown marker warnings when importing _experiments
warnings.filterwarnings("ignore", category=pytest.PytestUnknownMarkWarning)
from model_config_tests.config_tests.test_bit_reproducibility import _experiments
from model_config_tests.exp_test_helper import ExpTestHelper
from model_config_tests.models.accessesm1p5 import (
    DEFAULT_RUNTIME_SECONDS as ESM_RUNTIME,
)
from model_config_tests.models.accessom2 import DEFAULT_RUNTIME_SECONDS as OM2_RUNTIME
from model_config_tests.models.accessom3 import DEFAULT_RUNTIME_SECONDS as OM3_RUNTIME
from model_config_tests.util import DAY_IN_SECONDS


def exp_test_helper_factory(*args, **kwargs):
    """Factory function to create a new mock for each ExpTestHelper"""
    mock_instance = Mock(autospec=ExpTestHelper)
    print(f"Creating mock ExpTestHelper instance: {mock_instance}")
    return mock_instance


@pytest.mark.parametrize(
    "requested_markers, expected_experiments",
    [
        (
            [{"exp1": {"n_runs": 1}}],
            {
                "exp1": {
                    "n_runs": 1,
                    "model_runtime": None,  # Expect default model runtime (set by the model class)
                }
            },
        ),
        (
            [{"exp1": {"n_runs": 1}}, {"exp2": {"n_runs": 2, "model_runtime": 86400}}],
            {
                "exp1": {"n_runs": 1, "model_runtime": None},
                "exp2": {
                    "n_runs": 2,
                    "model_runtime": 86400,
                },
            },
        ),
        (
            [{"exp1": {"n_runs": 1}, "exp2": {}}, {"exp1": {"n_runs": 2}}],
            {
                "exp1": {
                    "n_runs": 2,
                    "model_runtime": None,
                },
                "exp2": {
                    "n_runs": 1,
                    "model_runtime": None,
                },
            },
        ),
        (
            [{"exp": {"model_runtime": 100}}, {"exp": {"model_runtime": 100}}],
            {
                "exp": {
                    "n_runs": 1,
                    "model_runtime": 100,
                },
            },
        ),
    ],
)
def test_experiments_fixture(requested_markers, expected_experiments, tmp_path):
    """Test the experiments function for setting up requested experiments,
    including model runtime set and number of seconds for model runtime
    """
    # Create base experiment/config to test
    control_path = tmp_path / "control"
    control_path.mkdir()

    # Create an output path
    output_path = tmp_path / "output"
    output_path.mkdir()

    # Create a mock for each ExpTestHelper instance stored in experiments
    with patch(
        "model_config_tests.exp_test_helper.ExpTestHelper",
        side_effect=exp_test_helper_factory,
    ):
        # Call the experiments function
        exps = _experiments(
            requested_markers, output_path, control_path, keep_archive=True
        )

    # Check that expected experiments were created
    assert len(exps.experiments) == len(expected_experiments)
    for exp_name in expected_experiments:
        assert exp_name in exps.experiments
        exp_mock = exps.experiments[exp_name]

        # Check the n_runs passed to the submit_payu_run method
        exp_mock.submit_payu_run.assert_called_once()
        n_runs = exp_mock.submit_payu_run.call_args[1].get("n_runs", None)
        assert n_runs == expected_experiments[exp_name]["n_runs"]

        # Check model runtime passed to set_model_runtime method
        exp_mock.model.set_model_runtime.assert_called_once()
        runtime = exp_mock.model.set_model_runtime.call_args[1].get("seconds", None)
        assert runtime == expected_experiments[exp_name]["model_runtime"]


def test_experiments_fixture_conflict_runtimes(tmp_path):
    """Test the experiments function for setting up requested experiments,
    raises an error if the same experiment name has different runtimes
    """
    request_markers_conflict = [
        {"exp": {"model_runtime": 100}},
        {"exp": {"model_runtime": 86400}},
    ]

    with pytest.raises(
        ValueError,
        match="Experiment exp has conflicting model runtimes: 100 and 86400",
    ):
        # Call the experiments function
        _experiments(
            request_markers_conflict,
            tmp_path / "output",
            tmp_path / "control",
            keep_archive=True,
        )


# Importing the test file test_bit_reproducibility.py, will run all the
# tests in the current pytest session. So to run only one test, and to
# configure fixtures correctly, the `model-config-tests` is called
# in a subprocess call.

# As running pytest to test in a subprocess call, patching the ExpTestHelper
# payu run methods to not run payu is not possible, so have added a new
# flag --keep-archive which leaves the archive unchanged and disables
# running payu.

# So these tests in this file have become wider integration tests rather than,
# testing just one function


@pytest.fixture
def tmp_dir():
    # Create a temporary directory
    directory = Path("tmp")
    directory.mkdir()

    yield directory

    # Teardown
    shutil.rmtree(directory)


class CommonTestHelper:
    """Helper function to store all paths for a test run"""

    def __init__(self, test_name, exp_name, model_name, tmp_dir):
        self.test_name = test_name
        self.exp_name = exp_name
        self.model_name = model_name

        # Output path for storing test output - resolve to a full path
        self.output_path = (tmp_dir / "output").resolve()

        # Test archive and control paths - these are generated in the subprocess
        # pytest calls (Except for the archive path which is provided with
        # mock model output)
        self.lab_path = self.output_path / "lab"
        self.test_control_path = self.output_path / "control" / exp_name
        self.test_config_path = self.test_control_path / "config.yaml"
        self.test_archive_path = self.lab_path / "archive" / exp_name

        # Setup model configuration to run tests from
        self.control_path = tmp_dir / "base-experiment"

        # Pre-generated model test resources
        self.resources_path = RESOURCES_DIR / model_name

    def write_config(self):
        """Create a minimal control directory"""
        self.control_path.mkdir()

        # Create a minimal config file in control directory
        config_file = self.control_path / "config.yaml"
        config_file.write_text(f"model: {self.model_name}")

        # TODO: Could create use a test config.yaml file for each model
        # in test resources? This could be used to test "config" tests too?

    def copy_config(self, configuration):
        """Copy a minimal control directory from RESOURCES_DIR"""
        mock_config = self.resources_path / "configurations" / configuration
        shutil.copytree(mock_config, self.control_path)

    def base_test_command(self):
        """Create a minimal test command"""
        # Minimal test command
        test_cmd = (
            "model-config-tests -s "
            # Use -k to select one test
            f"-k {self.test_name} "
            f"--output-path {self.output_path} "
            # Keep archive flag will keep any pre-existing archive for the test
            # and disable the actual 'payu run' steps
            "--keep-archive "
        )
        return test_cmd

    def create_mock_output(self, output="output000", modify=False):
        """Copy some expected output in the archive directory, optionally modifying the output
        to alter checksums"""
        resources_output = self.resources_path / output
        mock_output = self.test_archive_path / output
        shutil.copytree(resources_output, mock_output)

        if modify:
            if self.model_name in ["access", "access-esm1.6", "access-om2"]:
                with (mock_output / f"{self.model_name}.out").open("a") as f:
                    f.write("[chksum] test_checksum               -1")
            elif self.model_name == "access-om3":
                mom_restart_pointer = mock_output / "rpointer.ocn"
                with open(mom_restart_pointer) as f:
                    restart_file = f.readline().rstrip()

                restart = mom_restart_pointer.parent / restart_file
                rootgrp = Dataset(restart, "a")
                for variable in sorted(rootgrp.variables):
                    # Find the first var with a checksum and subtract 1 from it
                    var = rootgrp[variable]
                    if "checksum" in var.ncattrs():
                        # Subtract 1 from the checksum and return as uppercase
                        var_p1 = format(int(var.checksum, 16) - 1, "X")
                        var.setncattr("checksum", var_p1)
                        break
                rootgrp.close()
            else:
                raise ValueError(f"Unrecognised model: {self.model_name}")


def test_test_repro_historical_access_checksums_saved_on_config(tmp_dir):
    """Check the default settings for checksum path (saved on the
    configuration under testing/checksum), and the default for control
    directory fixture (use current working directory of subprocess call)"""
    test_name = "test_repro_historical"
    exp_name = "exp_default_runtime"
    model_name = "access"

    # Setup test Helper
    helper = CommonTestHelper(test_name, exp_name, model_name, tmp_dir)
    helper.copy_config("release-preindustrial+concentrations")

    # Copy checksums from resources to model configuration
    checksum_path = helper.resources_path / "checksums" / "1-0-0.json"
    config_checksum_path = helper.control_path / "testing" / "checksum"
    config_checksum_path.mkdir(parents=True)
    config_checksums = config_checksum_path / "historical-24hr-checksum.json"
    shutil.copy(checksum_path, config_checksums)

    # Put some expected output in the archive directory (as we are skipping
    # the actual payu run step)
    helper.create_mock_output()

    # Build test command
    test_cmd = helper.base_test_command()

    # Run test - Note also testing control directory defaults to the
    # current working directory
    result = subprocess.run(
        shlex.split(test_cmd),
        capture_output=True,
        text=True,
        cwd=str(helper.control_path),
    )

    # Expect the tests to have passed
    if result.returncode:
        # Print out test logs if there are errors
        print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")
    assert result.returncode == 0


def test_test_repro_historical_access_no_reference_checksums(tmp_dir):
    """Check when a reference file for checksums does not exist, that
    checksums from the output are written out"""
    test_name = "test_repro_historical"
    exp_name = "exp_default_runtime"
    model_name = "access"

    # Setup test Helper
    helper = CommonTestHelper(test_name, exp_name, model_name, tmp_dir)
    helper.copy_config("release-preindustrial+concentrations")

    # Put some expected output in the archive directory (as we are skipping
    # the actual payu run step)
    helper.create_mock_output()

    # Build test command
    test_cmd = f"{helper.base_test_command()} " f"--control-path {helper.control_path} "

    # Run test in a subprocess call
    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect test to fail
    assert result.returncode == 1

    # Test that checksums are still written out
    checksum_path = helper.resources_path / "checksums" / "1-0-0.json"
    check_checksum(helper.output_path, checksum_path, helper.model_name)


def test_test_repro_historical_access_no_model_output(tmp_dir):
    """Check when a test exits, that there are no checksums in the output
    directory- similar to when payu run exits with an error"""
    test_name = "test_repro_historical"
    exp_name = "exp_default_runtime"
    model_name = "access"

    # Setup test Helper
    helper = CommonTestHelper(test_name, exp_name, model_name, tmp_dir)
    helper.write_config()

    # Test any pre-existing test output checksums are removed in test call
    test_checksum_dir = helper.output_path / "checksum"
    test_checksum_dir.mkdir(parents=True)
    test_checksum = test_checksum_dir / "historical-24hr-checksum.json"
    test_checksum.write_text("Pre-existing test output..")

    # Build test command
    test_cmd = f"{helper.base_test_command()} " f"--control-path {helper.control_path} "

    # Run test in a subprocess call
    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect test to fail
    assert result.returncode == 1

    # Test no checksums are written out
    assert not test_checksum.exists()


@pytest.mark.parametrize(
    "model_name, output_0, configuration",
    [
        ("access", "output000", "release-preindustrial+concentrations"),
        ("access-om2", "output000", "release-1deg_jra55_ryf"),
        ("access-om3", "restart000", "om3-dev-1deg_jra55do_ryf"),
        ("access-om3", "restart000", "om3-wav-dev-1deg_jra55do_ryf"),
    ],
)
@pytest.mark.parametrize("fail", [False, True])
def test_test_repro_historical(tmp_dir, model_name, output_0, configuration, fail):
    """Test ACCESS-OM classes with historical repro test with some mock
    output and configuration directory, optionally checking that things
    fail when the outputs are modified to give different checksums"""
    test_name = "test_repro_historical"
    exp_name = "exp_default_runtime"

    # Setup test Helper
    helper = CommonTestHelper(test_name, exp_name, model_name, tmp_dir)

    # Use config in resources dir if provided
    if configuration:
        helper.copy_config(configuration)
    else:
        helper.write_config()

    # Compare checksums against the existing checksums in resources folder
    checksum_path = helper.resources_path / "checksums" / "1-0-0.json"

    # Put some expected output in the archive directory (as we are skipping
    # the actual payu run step) and modify the output if testing failure
    helper.create_mock_output(output_0, modify=fail)

    # Build test command
    test_cmd = (
        f"{helper.base_test_command()} "
        f"--checksum-path {checksum_path} "
        f"--control-path {helper.control_path} "
    )

    # Run test in a subprocess call
    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    assert result.returncode == int(fail)

    # Check runtime is set correctly
    check_runtime(helper.test_control_path, helper.model_name)

    # Check general config.yaml settings for test
    with open(helper.test_control_path / "config.yaml") as f:
        test_config = yaml.safe_load(f)
    assert test_config["experiment"] == exp_name
    assert not test_config["runlog"]
    assert not test_config["metadata"]["enable"]
    assert test_config["laboratory"] == str(helper.lab_path)

    # Check name of checksum file written out and contents
    check_checksum(
        helper.output_path, checksum_path, helper.model_name, match=(not fail)
    )


def test_test_access_om3_ocean_model(tmp_dir):
    """Test that an error is thrown when the ocean model is not MOM. This should be moved into
    dedicated tests for experiment setup when they exist. See
    https://github.com/ACCESS-NRI/model-config-tests/issues/115"""
    test_name = "test_repro_historical"
    exp_name = "exp_default_runtime"

    # Setup test Helper
    helper = CommonTestHelper(test_name, exp_name, "access-om3", tmp_dir)

    helper.copy_config("om3-dev-1deg_jra55do_ryf")

    # Set ocean model in nuopc.runconfig to something other than mom
    mock_runconfig = Runconfig(helper.control_path / "nuopc.runconfig")
    mock_runconfig.set("ALLCOMP_attributes", "OCN_model", "docn")
    mock_runconfig.write()

    # Put some expected output in the archive directory (as we are skipping
    # the actual payu run step)
    helper.create_mock_output("restart000")

    # Build test command
    test_cmd = f"{helper.base_test_command()} " f"--control-path {helper.control_path} "

    # Run test in a subprocess call
    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect test to have failed
    assert result.returncode == 1
    error_msg = (
        "ACCESS-OM3 reproducibility checks utilize checksums written in MOM6 restarts"
    )
    assert error_msg in result.stdout


def check_runtime(control_path, model_name):
    if model_name in ["access", "access-esm1.6"]:
        with open(control_path / "config.yaml") as f:
            test_config = yaml.safe_load(f)
        assert test_config["calendar"]["runtime"] == {
            "years": 0,
            "months": 0,
            "days": ESM_RUNTIME / DAY_IN_SECONDS,
            "seconds": 0,
        }
    elif model_name == "access-om2":
        with open(control_path / "accessom2.nml") as f:
            nml = f90nml.read(f)
        years, months, seconds = nml["date_manager_nml"]["restart_period"]
        assert years == 0
        assert months == 0
        assert seconds == OM2_RUNTIME
    elif model_name == "access-om3":
        runconfig = Runconfig(control_path / "nuopc.runconfig")
        assert runconfig.get("CLOCK_attributes", "restart_option") == "nseconds"
        assert int(runconfig.get("CLOCK_attributes", "restart_n")) == OM3_RUNTIME
        assert runconfig.get("CLOCK_attributes", "stop_option") == "nseconds"
        assert int(runconfig.get("CLOCK_attributes", "stop_n")) == OM3_RUNTIME

        wav_in = control_path / "wav_in"
        if wav_in.exists():
            with open(wav_in) as f:
                nml = f90nml.read(f)
            assert nml["output_date_nml"]["date"]["restart"]["stride"] == OM3_RUNTIME
    else:
        raise ValueError(f"Unrecognised model: {model_name}")


def check_checksum(output_path, checksum_path, model_name, match=True):
    if model_name in ["access", "access-esm1.6"]:
        test_checksum = output_path / "checksum" / "historical-24hr-checksum.json"
    elif model_name in ["access-om2", "access-om3"]:
        test_checksum = output_path / "checksum" / "historical-3hr-checksum.json"
    else:
        raise ValueError(f"Unrecognised model: {model_name}")
    assert test_checksum.exists()

    if match:
        assert test_checksum.read_text() == checksum_path.read_text()
    else:
        assert test_checksum.read_text() != checksum_path.read_text()
