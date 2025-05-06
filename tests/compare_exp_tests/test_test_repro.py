"""Integration style test for comparing multiple experiments"""

import shlex
import subprocess

import yaml


def setup_exp(tmp_path, exp_name):
    """Create a temporary experiment directory for testing"""
    exp_path = tmp_path / exp_name
    exp_path.mkdir(parents=True)

    # Create an archive
    archive_path = tmp_path / "lab" / "archive" / exp_name
    output_path = archive_path / "output000"
    output_path.mkdir(parents=True)

    # Create control dir archive symlink
    (exp_path / "archive").symlink_to(archive_path, target_is_directory=True)

    # Create a config.yaml file
    config_file = exp_path / "config.yaml"
    with config_file.open("w") as f:
        yaml.dump(
            {"model": "access-om2"},
            f,
        )

    # Create an access-om2.out file
    (output_path / "access-om2.out").write_text(
        """[chksum] test_checksum               0"""
    )

    return exp_path


def test_test_pairwise_repro(tmp_path):
    """Test for pairwise reproducibility of two experiments"""
    # Create two temporary experiment directories
    setup_exp(tmp_path, "exp1")
    setup_exp(tmp_path, "exp2")

    test_cmd = "compare-exp-tests " "-k test_pairwise_repro " '--dirs "exp1 exp2"'

    # Run test
    result = subprocess.run(
        shlex.split(test_cmd),
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )

    # Expect the tests to have passed
    if result.returncode:
        # Print out test logs if there are errors
        print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")
    assert result.returncode == 0

    # Tests have passed, but how to check what tests were run?
    # Could parse the xml output files for the test results
