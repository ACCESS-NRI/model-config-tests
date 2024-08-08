import os
import shlex
import shutil
import subprocess
from pathlib import Path

import yaml

HERE = os.path.dirname(__file__)
RESOURCES_DIR = Path(f"{HERE}/resources")


def test_test_access_om2_config_release_1deg_jra55_ryf():
    """Test ACCESS-OM2 specific config tests"""
    access_om2_configs = RESOURCES_DIR / "access-om2" / "configurations"
    test_config = access_om2_configs / "release-1deg_jra55_ryf"

    assert test_config.exists()

    test_cmd = (
        "model-config-tests -s "
        # Run all access_om2 specific tests
        "-m access_om2 "
        f"--control-path {test_config} "
        # Use target branch as can't mock get_git_branch function in utils
        f"--target-branch release-1deg_jra55_ryf"
    )

    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect the tests to have passed
    if result.returncode:
        # Print out test logs if there are errors
        print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")

    assert result.returncode == 0


def test_test_access_om2_config_modified_module_version(tmp_path):
    """Test changing model module version in config.yaml,
    will cause tests to fail if paths in exe manifests don't
    match released spack.location file"""
    access_om2_configs = RESOURCES_DIR / "access-om2" / "configurations"

    # Copy test configuration
    test_config = access_om2_configs / "release-1deg_jra55_ryf"
    mock_control_path = tmp_path / "mock_control_path"
    shutil.copytree(test_config, mock_control_path)

    mock_config = mock_control_path / "config.yaml"

    with open(mock_config) as f:
        config = yaml.safe_load(f)

    # Use a different released version of access-om2 module
    config["modules"]["load"] = ["access-om2/2023.11.23"]

    with open(mock_config, "w") as f:
        yaml.dump(config, f)

    test_cmd = (
        "model-config-tests -s "
        # Only test the manifest exe in release spack location test
        "-k test_access_om2_manifest_exe_in_release_spack_location "
        f"--control-path {mock_control_path} "
        # Use target branch as can't mock get_git_branch function in utils
        f"--target-branch release-1deg_jra55_ryf"
    )

    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect test to have failed
    assert result.returncode == 1
    error_msg = "Expected exe path in exe manifest to match an install path in released spack.location"
    assert error_msg in result.stdout


def test_test_access_om2_config_dev_025deg_jra55_iaf_bgc():
    """Test ACCESS-OM2 specific config tests for
    high-degree (025deg) and BGC configurations"""
    access_om2_configs = RESOURCES_DIR / "access-om2" / "configurations"
    test_config = access_om2_configs / "dev-025deg_jra55_iaf_bgc"

    assert test_config.exists()

    test_cmd = (
        "model-config-tests -s "
        # Run all access_om2 specific tests
        "-m access_om2 "
        f"--control-path {test_config} "
        # Use target branch as can't mock get_git_branch function in utils
        f"--target-branch release-025deg_jra55_iaf_bgc"
    )

    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect the tests to have passed
    if result.returncode:
        # Print out test logs if there are errors
        print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")

    assert result.returncode == 0
