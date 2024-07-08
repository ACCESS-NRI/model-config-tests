import os
import shlex
import subprocess
from pathlib import Path

HERE = os.path.dirname(__file__)
RESOURCES_DIR = Path(f"{HERE}/resources")


def test_test_access_om2_config_release_jra55_ryf():
    """Test ACCESS-OM2 specific config tests"""
    access_om2_configs = RESOURCES_DIR / "access-om2" / "configurations"
    test_config = access_om2_configs / "release-1deg_jra55_ryf"

    assert test_config.exists()

    test_cmd = (
        "model-config-tests -s "
        # Use -k to select one test
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
