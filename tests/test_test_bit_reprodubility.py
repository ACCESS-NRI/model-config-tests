"""Test for bit reproducibility tests"""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = os.path.dirname(__file__)
RESOURCES_DIR = Path(f"{HERE}/resources")

# Importing the test file test_bit_reproducibility.py, will run all the
# tests in the current pytest session. So to run only one test, and to
# configure fixtures correctly, the `model-config-tests` is called
# in a subprocess call.

# As running pytest to test in a subprocess call, patching the ExpTestHelper
# payu run methods to not run payu isn't possible, so have added a new
# flag --keep-archive which leaves the archive unchanged and disables
# running payu


@pytest.fixture
def tmp_dir():
    directory = Path("tmp")
    directory.mkdir()

    yield directory

    shutil.rmtree(directory)


def test_test_bit_repro_historical_access(tmp_dir):
    """Integration test though without the payu run part so tests can run
    not on NCI. It uses some pre-generated output in resources dir,
    along with some expected checksums to compare against.
    """
    # Experiment name is the name of the test
    experiment_name = "test_bit_repro_historical"

    # Output path for storing test output
    output_path = tmp_dir / "output"
    archive_path = output_path / "lab" / "archive"

    # Setup model configuration to run experiment from
    control_path = tmp_dir / "base-experiment"
    control_path.mkdir()

    # Create a minimal config file in control directory
    config_file = control_path / "config.yaml"
    config_file.write_text("model: access")

    model_resources_path = RESOURCES_DIR / "access"

    # Compare checksums against the existing checksums in resources folder
    checksum_path = model_resources_path / "checksums" / "1-0-0.json"

    # Put some expected output in the archive directory (as we are skipping
    # the actual payu run step)
    resources_output000 = model_resources_path / "output000"
    test_output000 = archive_path / experiment_name / "output000"
    shutil.copytree(resources_output000, test_output000)

    # Build test command
    test_cmd = (
        "model-config-tests -s "
        # Use -k to select one test
        f"-k {experiment_name} "
        f"--output-path {output_path} "
        f"--checksum-path {checksum_path} "
        f"--control-path {control_path} "
        # Keep archive flag will keep any pre-existing archive for the test
        # and disable payu run steps
        "--keep-archive"
    )
    # Run test in a subprocess call
    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    if result.returncode:
        # Print out test logs if there are errors
        print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")
    assert result.returncode == 0

    # Check config.yaml file has 24hr hours set

    # Check config.yaml experiment values have been set

    # Check name of checksum file written out and contents

    # Test everything im checksum was removed prior to the test

    # Test when checksums aren't matched, that file are still written.

    # Test checksums compared with checksums on the model configuration
    # directory
