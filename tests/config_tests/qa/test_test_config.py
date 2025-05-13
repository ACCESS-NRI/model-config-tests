import shlex
import subprocess
import warnings
from unittest.mock import Mock, patch

import pytest

from tests.common import RESOURCES_DIR

# Disable specific warnings from test_config tests
warnings.filterwarnings("ignore", category=pytest.PytestUnknownMarkWarning)
from model_config_tests.config_tests.qa.test_config import get_spack_location_file


def test_test_config_access_om2():
    """Test general config tests using a skeleton ACCESS-OM2 configuration"""
    branch_name = "release-1deg_jra55_ryf"
    access_om2_configs = RESOURCES_DIR / "access-om2" / "configurations"
    test_config = access_om2_configs / branch_name

    if not test_config.exists():
        raise FileNotFoundError(f"The test configuration {test_config} does not exist.")

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


@pytest.mark.parametrize(
    "repo_name, model_version, test_content",
    [
        # Release with spack.location file
        ("ACCESS-OM2", "2024.03.0", "access-om2-2024_03_0"),
        # Release with Gadi.spack.location file
        ("ACCESS-OM3", "2025.01.1", "access-om3-2025_01_1"),
    ],
)
def test_get_spack_location_file(repo_name, model_version, test_content):
    """
    Test to check that get_spack_location_file runs without error
    for a couple ACCESS-NRI releases
    """
    spack_location = get_spack_location_file(repo_name, model_version)
    assert test_content in spack_location


def test_get_spack_location_file_no_release_artefact():
    """
    Test that an error is raised when the release artefact is not found
    """
    with pytest.raises(AssertionError, match=r"Failed to find release .*"):
        get_spack_location_file("fake-repo-name", "fake.module.version")


def mock_request_get(url, *args, **kwargs):
    """Custom side effect function for mocking requests.get to pass the initial
    initial request (e.g that a release artefact exists)
    but returns a 404 status for subsequent requests.get calls
    """
    response = Mock()
    if url == "https://github.com/ACCESS-NRI/fake-repo/releases/tag/fake-version":
        response.status_code = 200
    else:
        response.status_code = 404
    return response


def test_get_spack_location_file_no_spack_location():
    """
    Test that an error is raised when the spack.location
    or Gadi.spack.location file is not found in the release artefact
    """
    with patch("requests.get", side_effect=mock_request_get):
        error_msg = r"Failed to download a spack\.location .*"
        with pytest.raises(AssertionError, match=error_msg):
            get_spack_location_file("fake-repo", "fake-version")
