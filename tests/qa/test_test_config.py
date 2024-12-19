import shlex
import subprocess

from tests.common import RESOURCES_DIR


def test_test_config_access_om2():
    """Test general config tests using a skeleton ACCESS-OM2 configuration"""
    branch_name = "release-1deg_jra55_ryf"
    access_om2_configs = RESOURCES_DIR / "access-om2" / "configurations"
    test_config = access_om2_configs / branch_name

    assert test_config.exists()

    test_cmd = (
        "model-config-tests -s "
        # Run all general config tests
        "-m config "
        f"--control-path {test_config} "
        f"--target-branch {branch_name}"
    )

    result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # Expect the tests to have passed
    if result.returncode:
        # Print out test logs if there are errors
        print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")

    assert result.returncode == 0
