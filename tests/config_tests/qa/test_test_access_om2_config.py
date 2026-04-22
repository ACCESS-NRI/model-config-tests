import shlex
import shutil
import subprocess

import yaml

from tests.common import clone_config_repo


def test_test_access_om2_config_release_1deg_jra55_ryf(tmp_path):
    """Test ACCESS-OM2 specific config tests"""
    config_dir = tmp_path / "access-om2-configs"
    branch_name = clone_config_repo("om2-1deg", config_dir)

    if not config_dir.exists():
        raise FileNotFoundError(f"The test configuration {config_dir} does not exist.")

    test_cmd = (
        "model-config-tests -s "
        # Run all access_om2 specific tests
        "-m access_om2 "
        f"--control-path {config_dir} "
        # Use target branch as can't mock get_git_branch function in utils
        f"--target-branch {branch_name}"
    )

    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect the tests to have passed
    if result.returncode:
        # Print out test logs if there are errors
        print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")

    assert result.returncode == 0
    shutil.rmtree(tmp_path)


def test_test_access_om2_config_modified_module_version(tmp_path):
    """Test changing model module version in config.yaml,
    will cause tests to fail if paths in exe manifests don't
    match released spack.location file"""
    config_dir = tmp_path / "access-om2-configs"
    branch_name = clone_config_repo("om2-1deg", config_dir)

    mock_config = config_dir / "config.yaml"

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
        f"--control-path {config_dir} "
        # Use target branch as can't mock get_git_branch function in utils
        f"--target-branch {branch_name}"
    )

    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect test to have failed
    assert result.returncode == 1
    error_msg = "Expected exe path in exe manifest to match an install path in released spack.location"
    assert error_msg in result.stdout

    shutil.rmtree(tmp_path)


def test_test_access_om2_config_dev_025deg_jra55_iaf_bgc(tmp_path):
    """Test ACCESS-OM2 specific config tests for
    high-degree (025deg) and BGC configurations"""
    config_dir = tmp_path / "access-om2-configs"
    branch_name = clone_config_repo("om2-025deg", config_dir)

    assert config_dir.exists()

    test_cmd = (
        "model-config-tests -s "
        # Run all access_om2 specific tests
        "-m access_om2 "
        f"--control-path {config_dir} "
        # Use target branch as can't mock get_git_branch function in utils
        f"--target-branch {branch_name}"
    )

    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect the tests to have passed
    if result.returncode:
        # Print out test logs if there are errors
        print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")

    assert result.returncode == 0
    shutil.rmtree(tmp_path)
