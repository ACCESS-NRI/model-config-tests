# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

import pytest
import yaml
from ruamel.yaml import YAML


@pytest.fixture(scope="session")
def output_path(request):
    """Set the output path: This contains control and lab directories for each
    test and test output files - e.g. CHECKSUMS
    """
    path = request.config.getoption("--output-path")
    if path is None:
        # Set default to $TMPDIR/test-model-repro/
        tmp_dir = os.environ.get("TMPDIR")
        path = f"{tmp_dir}/test-model-repro"
    return Path(path)


@pytest.fixture(scope="session")
def control_path(request):
    """Set the path of the model configuration directory to test"""
    path = request.config.getoption("--control-path")
    if path is None:
        # Set default to current working directory
        path = Path.cwd()
    return Path(path)


@pytest.fixture(scope="session")
def checksum_path(request):
    """Set the path of the model configuration directory to test"""
    path = request.config.getoption("--checksum-path")
    return Path(path) if path else None


@pytest.fixture(scope="session")
def metadata(control_path: Path):
    """Read the metadata file in the control directory"""
    metadata_path = control_path / "metadata.yaml"
    # Use ruamel.yaml as that is what is used to read metadata files in Payu
    # It also errors out if there are duplicate keys in metadata
    content = YAML().load(metadata_path)
    return content


@pytest.fixture(scope="session")
def skipif_no_metadata(control_path):
    metadata_path = control_path / "metadata.yaml"
    if not metadata_path.exists():
        pytest.skip("No metadata.yaml file exists")


@pytest.fixture(scope="session")
def config(control_path: Path):
    """Read the config file in the control directory"""
    config_path = control_path / "config.yaml"
    with open(config_path) as f:
        config_content = yaml.safe_load(f)
    return config_content


@pytest.fixture(scope="session")
def target_branch(request):
    """Set the target branch - i.e., the branch the configuration will be
    merged into. This used is to infer configuration information, if the
    configuration branches follow a common naming scheme (e.g. ACCESS-OM2)"""
    return request.config.getoption("--target-branch")


@pytest.fixture(scope="session")
def keep_archive(request):
    """Set keep_archive boolean flag. Enabling this will keep a
    pre-existing archive from a previous test run and disable running
    payu run again. This is useful for testing the test code when the output
    has already been generated."""
    return request.config.getoption("--keep-archive")


# Set up command line options and default for directory paths
def pytest_addoption(parser):
    """Attaches optional command line arguments"""
    parser.addoption(
        "--output-path",
        action="store",
        help="Specify the output directory path for test output",
    )

    parser.addoption(
        "--control-path",
        action="store",
        help="Specify the model configuration path to test",
    )

    parser.addoption(
        "--checksum-path",
        action="store",
        help="Specify the checksum file to compare against",
    )

    parser.addoption(
        "--target-branch", action="store", help="Specify the target branch name"
    )

    parser.addoption(
        "--keep-archive",
        action="store_true",
        help="Keep archive from previous test run and disable running payu",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "repro: mark tests to run as part of reproducibility tests"
    )
    config.addinivalue_line(
        "markers", "repro_historical: mark tests that check historical reproducibility"
    )
    config.addinivalue_line(
        "markers", "repro_repeat: mark tests that check repeat reproducibility"
    )
    config.addinivalue_line(
        "markers", "repro_restart: mark tests that check restart reproducibility"
    )
    config.addinivalue_line("markers", "slow: mark tests that are slow to run")
    config.addinivalue_line(
        "markers",
        "config: mark as configuration tests for release branches in quick QA CI checks",
    )
    config.addinivalue_line(
        "markers", "dev_config: mark as configuration tests in quick QA CI checks"
    )
    config.addinivalue_line(
        "markers", "access_om2: mark as ACCESS-OM2 specific tests in quick QA CI checks"
    )
    config.addinivalue_line(
        "markers",
        "access_esm1p5: mark as ACCESS-ESM1.5 specific tests in quick QA CI checks",
    )
    config.addinivalue_line(
        "markers", "access_om3: mark as access-om3 specific tests in quick QA CI checks"
    )
    config.addinivalue_line(
        "markers",
        "access_esm1p6: mark as access-esm1.6 specific tests in quick QA CI checks",
    )
