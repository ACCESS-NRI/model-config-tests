# import shlex
# import subprocess

# from tests.common import RESOURCES_DIR


# TODO: Add back when we have a sufficient test config released
def test_test_access_esm1p6_config_release_release_preindustrial():
    """Test ACCESS-ESM1.6 specific config tests"""
    pass
    # access_esm1p6_configs = RESOURCES_DIR / "access" / "configurations"
    # test_config = access_esm1p6_configs / "release-preindustrial+concentrations"

    # assert test_config.exists()

    # test_cmd = (
    #     "model-config-tests -s "
    #     # Run all access_esm1p6 specific tests
    #     "-m access_esm1p6 "
    #     f"--control-path {test_config} "
    #     # Use target branch as can't mock get_git_branch function in utils
    #     f"--target-branch release-preindustrial+concentrations"
    # )

    # result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # # Expect the tests to have passed
    # if result.returncode:
    #     # Print out test logs if there are errors
    #     print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")

    # assert result.returncode == 0
