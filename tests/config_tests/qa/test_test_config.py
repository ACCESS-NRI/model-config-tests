import shlex
import subprocess
import warnings
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

# Disable specific warnings from test_config tests
warnings.filterwarnings("ignore", category=pytest.PytestUnknownMarkWarning)
from model_config_tests.config_tests.qa.test_config import TestConfig as ConfigValidator
from model_config_tests.config_tests.qa.test_config import (
    compare_input_md5_hashes,
    fetch_input_md5_hashes_from_repo,
    get_spack_location_file,
    read_input_fullpaths_from_config,
    read_manifest_input_hashes,
)

# Import test fixtures
from tests.resources.expected_md5hash import (
    expected_fullpaths,
    expected_hashes_from_repo,
    expected_local_hashes,
    mock_input_response,
)


def test_test_config_access_om2(tmp_path, isolated_config):
    """Test general config tests using a skeleton ACCESS-OM2 configuration"""
    branch_name, config_dir = isolated_config("om2-1deg")

    if not config_dir.exists():
        raise FileNotFoundError(f"The test configuration {config_dir} does not exist.")

    test_cmd = (
        "model-config-tests -s "
        # Run all general config tests
        "-m config "
        f"--control-path {config_dir} "
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


@pytest.fixture
def checker():
    return ConfigValidator()


def test_test_sync_and_base_path(checker):
    """Test that the test checks sync and base_path configurations."""
    config_pass = {
        "sync": {
            "enable": False,
            "base_path": None,
        }
    }
    checker.test_sync_is_not_enabled(config_pass)
    checker.test_sync_base_path_is_not_set(config_pass)

    config_fail = {
        "sync": {
            "enable": True,
            "base_path": "/base_path/to/sync",
        }
    }
    with pytest.raises(
        AssertionError, match="Sync to remote archive should not be enabled"
    ):
        checker.test_sync_is_not_enabled(config_fail)

    with pytest.raises(
        AssertionError,
        match="Sync base path to remote archive should not be configured",
    ):
        checker.test_sync_base_path_is_not_set(config_fail)


def test_test_sync_path_not_exists(checker):
    """Test that the test properly checks sync path is not set."""
    config_fail = {
        "sync": {
            "enable": False,
            "path": "/path/to/sync",
        }
    }
    with pytest.raises(
        AssertionError, match="Sync path should not exist since base_path is preferred"
    ):
        checker.test_sync_path_not_exists(config_fail)

    config_fail2 = {
        "sync": {
            "enable": False,
            "path": None,
        }
    }
    with pytest.raises(
        AssertionError, match="Sync path should not exist since base_path is preferred"
    ):
        checker.test_sync_path_not_exists(config_fail2)


def test_read_input_fullpaths_from_config():
    """Test that the get_input_fullpaths_from_config function properly extracts input full paths from config."""
    # Load example config file
    control_path = (
        Path(__file__).parent.parent.parent / "resources" / "example_control_dir"
    )
    with open(control_path / "config.yaml") as f:
        config = yaml.safe_load(f)

    # Extract fullpaths using the function being tested
    fullpaths = read_input_fullpaths_from_config(config)

    # Assert that the extracted fullpaths match the expected list
    assert fullpaths == expected_fullpaths


def test_fetch_input_md5_hashes_from_repo():
    """Test that the fetch_input_md5_hashes_from_repo function loads the
    correct md5 hashes from model-config-inputs repository."""

    # Mock requests.get to return a predefined manifest response.
    # URLs not present in mock_input_response simulate a missing manifest file (HTTP 404), so that
    # fetch_input_md5_hashes_from_repo falls back to treating the path as a directory.
    def mock_requests_get(manifest_url):
        response = Mock()
        if manifest_url in mock_input_response:
            response.status_code = 200
            response.text = mock_input_response[manifest_url]
        else:
            response.status_code = 404
        return response

    with patch("requests.get", side_effect=mock_requests_get):
        assert expected_hashes_from_repo == fetch_input_md5_hashes_from_repo(
            expected_fullpaths
        )


def test_fetch_input_md5_hashes_from_repo_invalid():
    """Test that the fetch_input_md5_hashes_from_repo() raises an error with an invalid input file."""

    # Mock requests.get to return a 404 for all URLs, simulating missing manifests
    def mock_requests_get(manifest_url):
        response = Mock()
        response.status_code = 502
        return response

    with patch("requests.get", side_effect=mock_requests_get):
        with pytest.raises(RuntimeError, match="Failed to fetch MD5 hash"):
            fetch_input_md5_hashes_from_repo(expected_fullpaths)


def test_read_manifest_input_hashes():
    """Test that the read_manifest_input_hashes function reads
    correct md5 hashes from the manifest file."""
    # Load example manifest file
    control_path = (
        Path(__file__).parent.parent.parent / "resources" / "example_control_dir"
    )

    # Assert that the extracted md5 hashes match the expected dictionary
    assert read_manifest_input_hashes(control_path) == expected_local_hashes


def test_compare_input_md5_hashes():
    """Test that the compare_input_md5_hashes function correctly compares
    MD5 hashes between local manifests and the model-config-inputs repository."""
    control_path = (
        Path(__file__).parent.parent.parent / "resources" / "example_control_dir"
    )
    config_path = control_path / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    compare_input_md5_hashes(control_path, config)
