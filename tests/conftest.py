import shutil

import pytest

from tests.common import CLONE_CONFIGS, clone_config_repo


@pytest.fixture(scope="session")
def config_cache(tmp_path_factory):
    """Fixture to cache cloned configurations across tests in the session."""
    # Set up a cache directory in tmp_path_factory
    cache_root = tmp_path_factory.mktemp("config_cache")
    cache = {}

    def _get_config_cache(config_name):
        if config_name not in cache:
            # Clone the remote repository into the cache directory
            dest = cache_root / config_name
            dest.mkdir(parents=True, exist_ok=True)
            clone_config_repo(config_name, dest)
            cache[config_name] = dest
        return CLONE_CONFIGS[config_name]["branch"], cache[config_name]

    return _get_config_cache


@pytest.fixture
def isolated_config(config_cache, tmp_path):
    """Fixture to copy of the test configuration from the cache to tmp_path/config_name."""

    def _prepare_isolated_config(config_name):
        # Get the cached configuration directory
        branch_name, cached = config_cache(config_name)

        # Copy the cached configuration to the tmp_path/config_name directory
        dest = tmp_path / config_name
        shutil.copytree(cached, dest)

        return branch_name, dest

    return _prepare_isolated_config
