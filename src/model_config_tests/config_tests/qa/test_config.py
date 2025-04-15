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

    def test_sync_path_is_not_set(self, config):
        if "sync" in config:
            assert not (
                "path" in config["sync"] and config["sync"]["path"] is not None
            ), "Sync path to remote archive should not be set"

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
