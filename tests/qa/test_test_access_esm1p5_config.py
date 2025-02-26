import shlex
import subprocess

from tests.common import RESOURCES_DIR


def test_test_access_esm1p5_config_release_release_preindustrial():
    """Test ACCESS-ESM1.5 specific config tests"""
    access_esm1p5_configs = RESOURCES_DIR / "access" / "configurations"
    test_config = access_esm1p5_configs / "release-preindustrial+concentrations"

    if not test_config.exists():
        raise FileNotFoundError(f"The test configuration {test_config} does not exist.")

    test_cmd = (
        "model-config-tests -s "
        # Run all access_esm1p5 specific tests
        "-m access_esm1p5 "
        f"--control-path {test_config} "
        # Use target branch as can't mock get_git_branch function in utils
        f"--target-branch release-preindustrial+concentrations"
    )

    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect the tests to have passed
    if result.returncode:
        # Print out test logs if there are errors
        print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")

    assert result.returncode == 0
