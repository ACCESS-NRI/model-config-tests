# import shlex
# import shutil
# import subprocess

# from tests.common import clone_config_repo


# TODO: Add back when we have a sufficient test config released
def test_test_access_esm1p6_config_release_release_preindustrial(tmp_path):
    """Test ACCESS-ESM1.6 specific config tests"""
    pass
    # config_dir = tmp_path / "access-esm1p6-configs"
    # branch_name = clone_config_repo("esm1p6-amip", config_dir)
    # # access_esm1p6_configs = RESOURCES_DIR / "access" / "configurations"
    # # test_config = access_esm1p6_configs / "release-preindustrial+concentrations"

    # if not config_dir.exists():
    #     raise FileNotFoundError(f"The test configuration {config_dir} does not exist.")

    # test_cmd = (
    #     "model-config-tests -s "
    #     # Run all access_esm1p6 specific tests
    #     "-m access_esm1p6 "
    #     f"--control-path {config_dir} "
    #     # Use target branch as can't mock get_git_branch function in utils
    #     f"--target-branch {branch_name}"
    # )

    # result = subprocess.run(shlex.split(test_cmd), capture_output=True, text=True)

    # # Expect the tests to have passed
    # if result.returncode:
    #     # Print out test logs if there are errors
    #     print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")

    # assert result.returncode == 0
    # shutil.rmtree(tmp_path)
