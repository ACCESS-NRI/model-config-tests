# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""Tests for checking configs and valid metadata files"""

import re
import warnings
from pathlib import Path
from typing import Any

import jsonschema
import pytest
import requests
import yaml
from yamanifest import Manifest

from model_config_tests.util import get_git_branch_name

# Experiment Metadata Schema
BASE_SCHEMA_URL = "https://raw.githubusercontent.com/ACCESS-NRI/schema"
BASE_SCHEMA_PATH = "au.org.access-nri/model/output/experiment-metadata"
SCHEMA_VERSION = "1-0-3"
SCHEMA_COMMIT = "4b7207e47afe402a732c58741ff66acc5f93b8cf"

# CC BY 4.0 License
LICENSE = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/legalcode.txt"

# Release modules location on NCI
RELEASE_MODULE_LOCATION = "/g/data/vk83/modules"

# Model config inputs repository for input file MD5 verification
MODEL_CONFIG_INPUTS_RAW_URL = (
    "https://raw.githubusercontent.com/ACCESS-NRI/model-config-inputs/main"
)

# Model config input location and symlink
MODEL_CONFIG_INPUTS_LOCATION_SYMLINK = "/g/data/vk83/experiments"
MODEL_CONFIG_INPUTS_LOCATION = "/g/data/vk83/configurations"
MODEL_CONFIG_INPUTS_PRERELEASE = "/g/data/vk83/prerelease"
PUBLISH_DATA_LOCATION = [
    "/g/data/qv56/replicas",
    "/g/data/jq44",
]


class ManifestNotFoundError(Exception):
    """Raised when a .manifest.yaml file does not exist (HTTP 404) at the
    expected location in the model-config-inputs repository."""


def insist_array(str_or_array):
    if isinstance(str_or_array, str):
        str_or_array = [
            str_or_array,
        ]
    return str_or_array


@pytest.fixture(scope="class")
def branch_type(control_path, target_branch):
    branch_name = target_branch

    if branch_name is None:
        # Default to current branch name
        branch_name = get_git_branch_name(control_path)
        assert (
            branch_name is not None
        ), f"Failed getting git branch name of control path: {control_path}"
        warnings.warn(
            "Target branch is not specified, defaulting to current git branch: "
            f"{branch_name}. As some config tests infer config type information "
            "from the target branch name, some tests may not be run. To set use "
            "--target-branch flag in pytest call"
        )

    type_match = re.match(r"^(?P<type>release|dev)-.*", branch_name)
    if not type_match or "type" not in type_match.groupdict():
        pytest.fail(
            f"Could not find a type in the branch {branch_name}. "
            + "Branches must be of the form 'type-*'. "
            + "See README.md for more information."
        )
    return type_match.group("type")


@pytest.mark.config
class TestRelConfig:
    """General configuration tests for release branches"""

    def test_runlog_is_on(self, config):
        runlog_config = config.get("runlog", {})
        if isinstance(runlog_config, bool):
            runlog_enabled = runlog_config
        else:
            runlog_enabled = runlog_config.get("enable", True)
        assert runlog_enabled

    def test_restart_freq_is_date_based(self, config):
        assert "restart_freq" in config, "Restart frequency should be defined"
        frequency = config["restart_freq"]
        # String of an integer followed by a YS/MS/W/D/H/T/S unit,
        # e.g. 1YS for 1 year-start
        pattern = r"^\d+(YS|MS|W|D|H|T|S)$"
        assert isinstance(frequency, str) and re.match(pattern, frequency), (
            "Restart frequency should be date-based: " + f"'restart_freq: {frequency}'"
        )

    def test_manifest_reproduce_exe_is_on(self, config):
        manifest_reproduce = config.get("manifest", {}).get("reproduce", {})
        assert "exe" in manifest_reproduce and manifest_reproduce["exe"], (
            "Executable reproducibility should be enforced, e.g set:\n"
            + "manifest:\n    reproduce:\n        exe: True"
        )

    def test_manifest_input_match_repo(self, branch_type, control_path, config):
        """Check that input file MD5 hashes in manifests/input.yaml match
        those from model-config-inputs repository"""
        compare_input_md5_hashes(control_path, config, branch_type=branch_type)

    def test_metadata_is_enabled(self, config):
        if "metadata" in config and "enable" in config["metadata"]:
            assert config["metadata"]["enable"], (
                "Metadata should be enabled, otherwise new UUIDs will not "
                + "be generated and branching in Payu would not work - as "
                + "branch and UUIDs are not used in the name used for archival."
            )

    def test_no_scripts_in_top_level_directory(self, control_path):
        exts = {".py", ".sh"}
        scripts = [p for p in control_path.iterdir() if p.suffix in exts]
        assert scripts == [], (
            "Scripts in top-level directory should be moved to a "
            + "'tools' sub-directory"
        )

    def test_validate_metadata(self, metadata):
        # Get schema from Github
        schema_path = f"{BASE_SCHEMA_PATH}/{SCHEMA_VERSION}.json"
        url = f"{BASE_SCHEMA_URL}/{SCHEMA_COMMIT}/{schema_path}"

        response = requests.get(url)
        assert response.status_code == 200
        schema = response.json()

        # In schema version (1-0-0), required fields are name, experiment_uuid,
        # description and long_description. As name & experiment_uuid are
        # generated for running experiments, the required fields are removed
        # from the schema validation for now
        schema.pop("required")

        # Validate field names and types
        jsonschema.validate(instance=metadata, schema=schema)

    @pytest.mark.parametrize(
        "field",
        [
            "description",
            "notes",
            "keywords",
            "nominal_resolution",
            "version",
            "url",
            "model",
            "realm",
        ],
    )
    def test_metadata_contains_fields(self, field, metadata):
        assert field in metadata, f"{field} field shoud be defined in metadata"

    def test_metadata_license(self, metadata):
        assert (
            "license" in metadata and metadata["license"] == LICENSE
        ), f"The license should be set to {LICENSE}"


@pytest.mark.config
@pytest.mark.dev_config
class TestConfig:
    """General configuration tests"""

    @pytest.mark.parametrize("field", ["project", "shortpath"])
    def test_field_is_not_defined(self, config, field):
        assert (
            field not in config
        ), f"{field} should not be defined: '{field}: {config[field]}'"

    def test_absolute_input_paths(self, config):
        for path in insist_array(config.get("input", [])):
            assert Path(path).is_absolute(), f"Input path should be absolute: {path}"

    def test_absolute_submodel_input_paths(self, config):
        for model in config.get("submodels", []):
            for path in insist_array(model.get("input", [])):
                assert Path(path).is_absolute(), (
                    f"Input path for {model['name']} submodel should be "
                    + f" absolute: {path}"
                )

    def test_no_storage_qsub_flags(self, config):
        qsub_flags = config.get("qsub_flags", "")
        assert (
            "storage" not in qsub_flags
        ), "Storage flags defined in qsub_flags will be silently ignored"

    def test_license_file(self, control_path):
        license_path = control_path / "LICENSE"
        assert license_path.exists(), (
            f"LICENSE file should exist and equal to {LICENSE} found here: "
            + LICENSE_URL
        )

        response = requests.get(LICENSE_URL)
        assert response.status_code == 200
        license = response.text

        with open(license_path) as f:
            content = f.read()

        assert content == license, (
            f"LICENSE file should be equal to {LICENSE} found here: " + LICENSE_URL
        )

    def test_model_module_path_is_defined(self, branch_type, config):
        """Check model module path is added to modules in config"""
        if branch_type == "release":
            module_paths = config.get("modules", {}).get("use", {})
            assert RELEASE_MODULE_LOCATION in module_paths, (
                "Expected model module path is added to module config. E.g.\n"
                "  modules:\n"
                "   use:\n"
                f"    - {RELEASE_MODULE_LOCATION}\n"
                "This path is used to find model module files"
            )
        else:
            pytest.skip(
                "The target branch is a dev version and doesn't require a stable module location"
            )

    @pytest.mark.usefixtures("skipif_no_metadata")
    def test_metadata_does_not_contain_UUID(self, metadata):
        assert "experiment_uuid" not in metadata, (
            "`experiment_uuid` should not be defined in metadata, "
            + "as this is a configuration rather than an experiment. "
        )

    def test_sync_is_not_enabled(self, config):
        if "sync" in config and "enable" in config["sync"]:
            assert not config["sync"][
                "enable"
            ], "Sync to remote archive should not be enabled"

    def test_sync_base_path_is_not_set(self, config):
        if "sync" in config:
            assert not (
                "base_path" in config["sync"]
                and config["sync"]["base_path"] is not None
            ), "Sync base path to remote archive should not be configured"

    def test_sync_path_not_exists(self, config):
        if "sync" in config:
            assert (
                "path" not in config["sync"]
            ), "Sync path should not exist since base_path is preferred"

    def test_experiment_name_is_not_defined(self, config):
        assert "experiment" not in config, (
            f"experiment: {config['experiment']} should not set, "
            + "as this over-rides the experiment name used for archival. "
            + "If set, branching in payu would not work."
        )


def read_exe_manifest_fullpaths(control_path: Path):
    """Return the full paths to the executables in the executable manifest file"""
    manifest_path = control_path / "manifests" / "exe.yaml"
    with open(manifest_path) as f:
        _, data = yaml.safe_load_all(f)
    exe_fullpaths = {item["fullpath"] for item in data.values()}
    return exe_fullpaths


def read_config_model_exes(config: dict[str, Any]):
    """Return the exe values of the model and sub-model defined in config.yaml"""
    exes = []
    if "exe" in config:
        exes.append(config["exe"])
    for model in config.get("submodels", []):
        if "exe" in model:
            exes.append(model["exe"])
    return exes


def get_spack_location_file(model_repo_name, model_version):
    """Return the spack.location file for the model version
    from a Github release artefact. Raises an AssertionError if the
    release artefact or spack.location file is not found."""
    base_url = f"https://github.com/ACCESS-NRI/{model_repo_name}/releases"
    # Check whether there is a release artefact for the model version
    release_url = f"{base_url}/tag/{model_version}"
    assert (
        requests.get(release_url).status_code == 200
    ), f"Failed to find release artefact for model version at {release_url}"

    # Urls for spack.location file in release artefacts assets,
    # Note: Gadi.spack.location filename is used for models built with
    # access-nri/build-cd version v4 and later
    urls = [
        f"{base_url}/download/{model_version}/spack.location",
        f"{base_url}/download/{model_version}/Gadi.spack.location",
    ]

    # Attempt to download a spack.location file
    spack_location = None
    for url in urls:
        response = requests.get(url)
        if response.status_code == 200:
            spack_location = str(response.content)

    assert spack_location is not None, (
        "Failed to download a spack.location or Gadi.spack.location file in "
        f"the release artefact for model version {model_version}. "
        f"Checked urls: {(', ').join(urls)}"
    )
    return spack_location


def check_manifest_exes_in_spack_location(
    model_module_name, model_repo_name, control_path, config
):
    """This compares executable paths in the executable manifest, and checks
    they match an install path in the spack.location release artefact. The
    version defined in the module configuration in config.yaml, is used
    to find the relevant release version.

    This is called in model-specific config tests.

    Parameters
    ----------
    model_module_name: str
        Expected module name in the config.yaml file. This is used to find the version of the model
    model_repo_name: str
        Name of the ACCESS-NRI model repository. This is used to retrieve released spack.location
    control_path: Path
        The path to configuration directory
    config: Dict[str, Any]
        The contents of the config.yaml file
    """
    help_msg = (
        "Expected module for the model is added to loaded modules in config.yaml. "
        "The module also requires a released version. E.g.\n"
        "   modules:\n"
        "     use:\n"
        f"       - {RELEASE_MODULE_LOCATION}\n"
        "     load:\n"
        f"       - {model_module_name}/<version>\n"
        "Model executable paths can then be filenames that found in paths added by loaded module"
    )

    # Check module is defined in configuration file
    assert "modules" in config and "load" in config["modules"], help_msg
    loaded_modules = config["modules"]["load"]
    modules = [m for m in loaded_modules if m.startswith(f"{model_module_name}/")]
    assert len(modules) == 1, help_msg

    # Extract out the version
    _, module_version = modules[0].split("/")

    # Use the module version to download spack.location file
    spack_location = get_spack_location_file(model_repo_name, module_version)

    # Read exe full paths in the manifests
    exe_paths = read_exe_manifest_fullpaths(control_path)

    # Read exe values from the configuration file
    config_exes = read_config_model_exes(config)

    for exe_path in exe_paths:
        install_path, exe_name = exe_path.split("/bin/")
        assert install_path in spack_location, (
            "Expected exe path in exe manifest to match an install path in released spack.location "
            f"for {model_module_name}/{module_version}.\n"
            f"Executable path: {exe_path}\n"
            f"----spack.location---\n{spack_location}"
        )

        assert exe_name in config_exes, (
            f"Expected 'exe: {exe_name}' for model/submodel in config.yaml. "
            "Only the name of the executable is needed, as the full path is "
            f"determined by payu (which searches PATHs added by {model_module_name} module)"
        )


def read_input_fullpaths_from_config(config: dict[str, Any]) -> list[str]:
    """Extract all input file fullpaths from config.yaml.

    Parameters
    ----------
    config : Dict[str, Any]
        The contents of the config.yaml file

    Returns
    -------
    list[str]
        List of fullpaths to input files
    """
    fullpaths = []

    # Get top-level input paths and submodel input paths
    for model in [config] + config.get("submodels", []):
        if "input" in model:
            input_paths = insist_array(model["input"])
            input_paths = [
                p.replace(
                    MODEL_CONFIG_INPUTS_LOCATION_SYMLINK, MODEL_CONFIG_INPUTS_LOCATION
                )
                for p in input_paths
            ]
            fullpaths.extend(input_paths)

    return fullpaths


def read_manifest_input_hashes(control_path: Path) -> dict[str, str]:
    """Read MD5 hashes from manifests/input.yaml.

    Parameters
    ----------
    control_path : Path
        Path to the local control directory containing the manifest file

    Returns
    -------
    dict[str, str]
        Dictionary mapping fullpath to MD5 hash
    """
    local_input = {}

    manifest = Manifest(control_path / "manifests" / "input.yaml").load()

    for filepath in manifest:

        fullpath = manifest.fullpath(filepath)
        fullpath = fullpath.replace(
            MODEL_CONFIG_INPUTS_LOCATION_SYMLINK, MODEL_CONFIG_INPUTS_LOCATION
        )

        local_input[fullpath] = manifest.get(filepath, "md5")

    return local_input


def _cache_manifest_from_input_repo(manifest_url, manifest_cache, fullpath):
    """Fetch and cache the manifest file from model-config-inputs repository."""
    # Only fetch the manifest file if it is not already cached
    if manifest_url not in manifest_cache:
        try:
            response = requests.get(manifest_url, timeout=10)
        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"Timeout (10s) while fetching manifest file from {manifest_url}"
            )

        if response.status_code == 404:
            raise ManifestNotFoundError(
                f"While checking input file: {fullpath},\n URL not found at {manifest_url}"
            )
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch manifest file from {manifest_url}: "
                f"HTTP {response.status_code}"
            )
        assert response.text, f"Manifest file from {manifest_url} is empty."

        # YAML manifest files have headers and data, separated by `---`
        # The actual data is after the --- separator
        docs = list(yaml.safe_load_all(response.text))
        manifest_cache[manifest_url] = docs[-1]

    return manifest_cache


def _extract_md5_from_repo_response(fullpath, file_info, manifest_url):
    """Extract the md5 hash for a given fullpath from the manifest file fetched from the model-config-inputs repository."""
    # Check if the fullpath in the input repo matches the fullpath from config.yaml
    if fullpath == file_info.get("fullpath"):
        return file_info.get("hashes", {}).get("md5", None)

    else:
        # If fullpath not matching, raise an error
        raise RuntimeError(
            f"Fullpath in config.yaml \"{fullpath}\" does not match the one \"{file_info.get('fullpath')}\" in model-config-inputs repo {manifest_url}."
        )


def fetch_input_md5_hashes_from_repo(fullpaths: list[str]) -> dict[str, str]:
    """Fetch MD5 hashes for input files from model-config-inputs repository.

    The repo contains .manifest.yaml files that store MD5 hashes for input files.
    Path mapping: /g/data/vk83/configurations/inputs/access-om2/subdir/file.nc
    maps to: access-om2/subdir/.manifest.yaml

    Parameters
    ----------
    fullpaths : list[str]
        List of fullpaths to input files

    Returns
    -------
    dict[str, str]
        Dictionary mapping fullpath to MD5 hash from repo
    """
    model_config_input = {}
    manifest_cache = (
        {}
    )  # {manifest_url1: manifest_data1, manifest_url2: manifest_data2, ...}, cached from input repo

    for fullpath in fullpaths:
        # Try treating fullpath as a file first: the manifest lives in its
        # parent directory. If no manifest is found there (404), fall back to
        # treating fullpath as a directory where manifest lives.
        try:
            # Build the manifest file url on the model-config-inputs repo
            path = fullpath.split("/inputs/")[-1]
            manifest_url = (
                f"{MODEL_CONFIG_INPUTS_RAW_URL}/{Path(path).parent}/.manifest.yaml"
            )

            # Cache the manifest file from model-config-inputs repo
            manifest_cache = _cache_manifest_from_input_repo(
                manifest_url, manifest_cache, fullpath
            )

            # Extract the input information for the current fullpath
            file_name = Path(fullpath).name
            file_info = manifest_cache[manifest_url].get(file_name, {})

            # Extract the md5 hash for the current fullpath file
            md5hash = _extract_md5_from_repo_response(fullpath, file_info, manifest_url)
            model_config_input[fullpath] = {
                "md5hash": md5hash,
                "repo_url": manifest_url,
            }

        # If no manifest was found assuming fullpath is a file, treat it as a directory
        except ManifestNotFoundError:
            path = fullpath.split("/inputs/")[-1]
            manifest_url = f"{MODEL_CONFIG_INPUTS_RAW_URL}/{path}/.manifest.yaml"

            # Cache the manifest file from model-config-inputs repo
            manifest_cache = _cache_manifest_from_input_repo(
                manifest_url, manifest_cache, fullpath
            )

            # Extract all fullpath and md5 hashes in this manifest file
            for file_name, file_info in manifest_cache[manifest_url].items():
                # Build the complete fullpath for each file in the directory
                complete_fullpath = f"{fullpath}/{file_name}"

                # Extract the md5 hash for each file in the directory
                md5hash = _extract_md5_from_repo_response(
                    complete_fullpath, file_info, manifest_url
                )
                model_config_input[complete_fullpath] = {
                    "md5hash": md5hash,
                    "repo_url": manifest_url,
                }

        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch MD5 hash for {fullpath} from model-config-inputs repo: {e}"
            )

    return model_config_input


def compare_input_md5_hashes(
    control_path: Path, config: dict[str, Any], branch_type: str = "release"
):
    """Check that input file MD5 hashes match those in manifests/input.yaml
    and from model-config-inputs repository.

    Parameters
    ----------
    control_path : Path
        Path to the model configuration directory
    config : Dict[str, Any]
        The contents of the config.yaml file

    Raises
    ------
    AssertionError
        If MD5 hashes do not match or files are not found
    """
    # Get input fullpaths from config.yaml
    fullpaths = read_input_fullpaths_from_config(config)

    # Check if all input files are in vk83 or published data project location
    fullpaths = check_allowed_config_location(fullpaths, branch_type=branch_type)

    # Read local MD5 hashes from manifests/input.yaml
    local_input = read_manifest_input_hashes(control_path)

    # Fetch MD5 hashes from model-config-inputs repo
    repo_hashes = fetch_input_md5_hashes_from_repo(fullpaths)

    # Compare hashes for each input file
    for fullpath, repo_response in repo_hashes.items():
        assert (
            fullpath in local_input
        ), f"Expected local input manifest to include input file:  {fullpath}"
        local_hash = local_input.get(fullpath)

        repo_hash = repo_response.get("md5hash")
        assert repo_hash == local_hash, (
            f"MD5 hash mismatch for {fullpath}: "
            f"local manifest hash: {local_hash}, repo hash: {repo_hash} from {repo_response.get('repo_url')}"
        )


def check_allowed_config_location(
    fullpaths: list[str], branch_type: str = "release"
) -> list[str]:
    """
    Picks out input files in /g/data/vk83/configurations for furture md5 hash checking.
    It raises a RuntimeError if:
    - any input file is not in /g/data/vk83 or a published data project location,
    - a release branch uses prerelease input files.
    """

    filter_fps = []

    for path in fullpaths:
        # Pick up input files in /g/data/vk83/configurations(experiments) for md5 hash checking
        if path.startswith(MODEL_CONFIG_INPUTS_LOCATION):
            filter_fps.append(path)
            # Skip following checks
            continue

        # Check if a release branch is using prerelease input files
        if path.startswith(MODEL_CONFIG_INPUTS_PRERELEASE):
            assert (
                branch_type != "release"
            ), f"Input file {path} is in prerelease location, which is not allowed for release branches. "
        else:
            # Check if input file is in a published data project location
            assert any(
                path.startswith(loc) for loc in PUBLISH_DATA_LOCATION
            ), f"Input file {path} is not in vk83 or a published data project location: {PUBLISH_DATA_LOCATION}. "

    return filter_fps
