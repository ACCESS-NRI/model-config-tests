"""Test for bit reproducibility tests"""

import shlex
import shutil
import subprocess
from pathlib import Path

import f90nml
import pytest
import yaml

from tests.common import RESOURCES_DIR

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

    def __init__(self, test_name, model_name, tmp_dir):
        self.test_name = test_name
        self.model_name = model_name

        # Output path for storing test output - resolve to a full path
        self.output_path = (tmp_dir / "output").resolve()

        # Test archive and control paths - these are generated in the subprocess
        # pytest calls (Except for the archive path which is provided with
        # mock model output)
        self.lab_path = self.output_path / "lab"
        self.test_control_path = self.output_path / "control" / test_name
        self.test_config_path = self.test_control_path / "config.yaml"
        self.test_archive_path = self.lab_path / "archive" / test_name

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

    def create_mock_output000(self):
        """Copy some expected output in the archive directory"""
        resources_output000 = self.resources_path / "output000"
        mock_output000 = self.test_archive_path / "output000"
        shutil.copytree(resources_output000, mock_output000)
        return mock_output000


def test_test_bit_repro_historical_access_pass(tmp_dir):
    """Test ACCESS-ESM1.5 access class with historical repro test with
    some mock output and configuration directory."""
    test_name = "test_bit_repro_historical"
    model_name = "access"

    # Setup test Helper
    helper = CommonTestHelper(test_name, model_name, tmp_dir)
    helper.write_config()

    # Compare checksums against the existing checksums in resources folder
    checksum_path = helper.resources_path / "checksums" / "1-0-0.json"

    # Put some expected output in the archive directory (as we are skipping
    # the actual payu run step)
    helper.create_mock_output000()

    # Build test command
    test_cmd = (
        f"{helper.base_test_command()} "
        f"--checksum-path {checksum_path} "
        f"--control-path {helper.control_path} "
    )

    # Run test in a subprocess call
    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    if result.returncode:
        # Print out test logs if there are errors
        print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")
    assert result.returncode == 0

    # Check config.yaml file generated for the test
    with helper.test_config_path.open("r") as f:
        test_config = yaml.safe_load(f)

    # Check runtime of 24hr hours is set
    assert test_config["calendar"]["runtime"] == {
        "years": 0,
        "months": 0,
        "days": 0,
        "seconds": 86400,
    }

    # Check general config.yaml settings for test
    assert test_config["experiment"] == test_name
    assert not test_config["runlog"]
    assert not test_config["metadata"]["enable"]
    assert test_config["laboratory"] == str(helper.lab_path)

    # Check name of checksum file written out and contents
    test_checksum = helper.output_path / "checksum" / "historical-24hr-checksum.json"
    assert test_checksum.exists()
    assert test_checksum.read_text() == checksum_path.read_text()


def test_test_bit_repro_historical_access_checksums_saved_on_config(tmp_dir):
    """Check the default settings for checksum path (saved on the
    configuration under testing/checksum), and the default for control
    directory fixture (use current working directory of subprocess call)"""
    test_name = "test_bit_repro_historical"
    model_name = "access"

    # Setup test Helper
    helper = CommonTestHelper(test_name, model_name, tmp_dir)
    helper.write_config()

    # Copy checksums from resources to model configuration
    checksum_path = helper.resources_path / "checksums" / "1-0-0.json"
    config_checksum_path = helper.control_path / "testing" / "checksum"
    config_checksum_path.mkdir(parents=True)
    config_checksums = config_checksum_path / "historical-24hr-checksum.json"
    shutil.copy(checksum_path, config_checksums)

    # Put some expected output in the archive directory (as we are skipping
    # the actual payu run step)
    helper.create_mock_output000()

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


def test_test_bit_repro_historical_access_fail(tmp_dir):
    """Check when checksums do not match, checksum file is still written out"""
    test_name = "test_bit_repro_historical"
    model_name = "access"

    # Setup test Helper
    helper = CommonTestHelper(test_name, model_name, tmp_dir)
    helper.write_config()

    # Compare checksums against the existing checksums in resources folder
    checksum_path = helper.resources_path / "checksums" / "1-0-0.json"

    # Put some expected output in the archive directory (as we are skipping
    # the actual payu run step)
    mock_output000 = helper.create_mock_output000()

    # Modify output file to mimic a change to output file in archive
    with (mock_output000 / "access.out").open("a") as f:
        f.write("[chksum] test_checksum               -1")

    # Build test command
    test_cmd = (
        f"{helper.base_test_command()} "
        f"--checksum-path {checksum_path} "
        f"--control-path {helper.control_path} "
    )

    # Run test in a subprocess call
    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect test to fail
    assert result.returncode == 1

    # Test when checksums aren't matched, that file are still written
    test_checksum = helper.output_path / "checksum" / "historical-24hr-checksum.json"
    assert test_checksum.exists()
    content = test_checksum.read_text()
    assert content != checksum_path.read_text()


def test_test_bit_repro_historical_access_no_reference_checksums(tmp_dir):
    """Check when a reference file for checksums does not exist, that
    checksums from the output are written out"""
    test_name = "test_bit_repro_historical"
    model_name = "access"

    # Setup test Helper
    helper = CommonTestHelper(test_name, model_name, tmp_dir)
    helper.write_config()

    # Put some expected output in the archive directory (as we are skipping
    # the actual payu run step)
    helper.create_mock_output000()

    # Build test command
    test_cmd = f"{helper.base_test_command()} " f"--control-path {helper.control_path} "

    # Run test in a subprocess call
    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect test to fail
    assert result.returncode == 1

    # Test that checksums are still written out
    test_checksum = helper.output_path / "checksum" / "historical-24hr-checksum.json"
    assert test_checksum.exists()

    # Test that they are equal to checksums in resource folder
    checksum_path = helper.resources_path / "checksums" / "1-0-0.json"
    assert test_checksum.read_text() == checksum_path.read_text()


def test_test_bit_repro_historical_access_no_model_output(tmp_dir):
    """Check when a test exits, that there are no checksums in the output
    directory- similar to when payu run exits with an error"""
    test_name = "test_bit_repro_historical"
    model_name = "access"

    # Setup test Helper
    helper = CommonTestHelper(test_name, model_name, tmp_dir)
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


def test_test_bit_repro_historical_access_om2_pass(tmp_dir):
    """Test ACCESS-OM2 class with historical repro test with
    some mock output and configuration directory."""
    test_name = "test_bit_repro_historical"
    model_name = "access-om2"

    # Setup test Helper
    helper = CommonTestHelper(test_name, model_name, tmp_dir)

    # Use config in resources dir
    mock_config = helper.resources_path / "configurations" / "release-1deg_jra55_ryf"
    shutil.copytree(mock_config, helper.control_path)

    # Compare checksums against the existing checksums in resources folder
    checksum_path = helper.resources_path / "checksums" / "1-0-0.json"

    # Put some expected output in the archive directory (as we are skipping
    # the actual payu run step)
    helper.create_mock_output000()

    # Build test command
    test_cmd = (
        f"{helper.base_test_command()} "
        f"--checksum-path {checksum_path} "
        f"--control-path {helper.control_path} "
    )

    # Run test in a subprocess call
    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    if result.returncode:
        # Print out test logs if there are errors
        print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")
    assert result.returncode == 0

    # Check runtime of 3 hours is set
    with open(helper.test_control_path / "accessom2.nml") as f:
        nml = f90nml.read(f)
    years, months, seconds = nml["date_manager_nml"]["restart_period"]
    assert years == 0
    assert months == 0
    assert seconds == 10800

    # Check name of checksum file written out and contents
    test_checksum = helper.output_path / "checksum" / "historical-3hr-checksum.json"
    assert test_checksum.exists()
    assert test_checksum.read_text() == checksum_path.read_text()
