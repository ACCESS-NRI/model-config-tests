import shlex
import shutil
import subprocess


def test_test_access_esm1p5_config_release_release_preindustrial(
    tmp_path, isolated_config
):
    """Test ACCESS-ESM1.5 specific config tests"""
    branch_name, config_dir = isolated_config("esm1p5-prein")

    if not config_dir.exists():
        raise FileNotFoundError(f"The test configuration {config_dir} does not exist.")

    test_cmd = (
        "model-config-tests -s "
        # Run all access_esm1p5 specific tests
        "-m access_esm1p5 "
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
