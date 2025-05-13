import shlex
import shutil
import subprocess

import yaml

from tests.common import RESOURCES_DIR


def test_test_access_om3_config_release_1deg_jra55_ryf():
    """Test ACCESS-OM3 specific config tests"""
    access_om3_configs = RESOURCES_DIR / "access-om3" / "configurations"
    test_config = access_om3_configs / "om3-dev-1deg_jra55do_ryf"

    if not test_config.exists():
        raise FileNotFoundError(f"The test configuration {test_config} does not exist.")

    test_cmd = (
        "model-config-tests -s "
        # Run all access_om3 specific tests
        "-m access_om3 "
        f"--control-path {test_config} "
        # Use target branch as can't mock get_git_branch function in utils
        f"--target-branch om3-dev-1deg_jra55do_ryf"
    )

    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect the tests to have passed
    if result.returncode:
        # Print out test logs if there are errors
        print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")

    assert result.returncode == 0


def test_test_access_om3_config_modified_module_version(tmp_path):
    """Test changing model module version in config.yaml,
    will cause tests to fail if paths in exe manifests don't
    match released spack.location file"""
    access_om3_configs = RESOURCES_DIR / "access-om3" / "configurations"

    # Copy test configuration
    test_config = access_om3_configs / "om3-dev-1deg_jra55do_ryf"
    mock_control_path = tmp_path / "mock_control_path"
    shutil.copytree(test_config, mock_control_path)

    mock_config = mock_control_path / "config.yaml"

    with open(mock_config) as f:
        config = yaml.safe_load(f)

    # Use a different released version of access-om3 module
    config["modules"]["load"] = ["access-om3/2024.09.0"]

    with open(mock_config, "w") as f:
        yaml.dump(config, f)

    test_cmd = (
        "model-config-tests -s "
        # Only test the manifest exe in release spack location test
        "-k test_access_om3_manifest_exe_in_release_spack_location "
        f"--control-path {mock_control_path} "
        # Use target branch as can't mock get_git_branch function in utils
        f"--target-branch om3-dev-1deg_jra55do_ryf"
    )

    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect test to have failed
    assert result.returncode == 1
    error_msg = "Expected exe path in exe manifest to match an install path in released spack.location"
    assert error_msg in result.stdout
