# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""ACCESS-ESM1.5 specific configuration tests"""

import re
import warnings
from typing import Any

import pytest

from model_config_tests.qa.test_config import check_manifest_exes_in_spack_location
from model_config_tests.util import get_git_branch_name

# Name of module on NCI
ACCESS_ESM1P5_MODULE_NAME = "access-esm1p5"
# Name of Model Repository - used for retrieving spack location files for released versions
ACCESS_ESM1P5_REPOSITORY_NAME = "ACCESS-ESM1.5"

######################################
# Bunch of expected values for tests #
######################################
VALID_REALMS: set[str] = {"atmosphere", "land", "ocean", "ocnBgchm", "seaIce"}
VALID_KEYWORDS: set[str] = {"global", "access-esm1.5"}
VALID_NOMINAL_RESOLUTION: str = "100 km"
VALID_REFERENCE: str = "https://doi.org/10.1071/ES19035"
VALID_PREINDUSTRIAL_START: dict[str, int] = {"year": 101, "month": 1, "day": 1}
VALID_HISTORICAL_START: dict[str, int] = {"year": 1850, "month": 1, "day": 1}
VALID_RUNTIME: dict[str, int] = {"year": 1, "month": 0, "day": 0}
VALID_RESTART_FREQ: str = "10YS"
VALID_MPPNCCOMBINE_EXE: str = "mppnccombine.spack"


### Some functions to avoid copying assertion error text
def error_field_nonexistence(field: str, file: str) -> str:
    return f"Field '{field}' is null or does not exist in {file}."


def error_field_incorrect(field: str, file: str, expected: Any) -> str:
    return f"Field '{field}' in {file} is not expected value: {expected}"


class AccessEsm1p5Branch:
    """Use the naming patterns of the branch name to infer information of
    the ACCESS-ESM1.5 config"""

    def __init__(self, branch_name):
        self.branch_name = branch_name
        self.config_scenario = self.set_config_scenario()
        self.config_modifiers = self.set_config_modifiers()

    def set_config_scenario(self) -> str:
        # Regex below is split into three sections:
        # Config type start section: '(?:release|dev)-' for 'release-' or 'dev-'
        # Scenario section: '([^+]+)' for 'preindustrial', 'historical'...anything that isn't the '+' modifier sigil
        # Modifiers end section: '(?:\+.+)*' any amount of '+modifer' sections
        scenario_match = re.match(
            r"^(?:release|dev)-(?P<scenario>[^+]+)(?:\+.+)*$", self.branch_name
        )
        if not scenario_match or "scenario" not in scenario_match.groupdict():
            pytest.fail(
                f"Could not find a scenario in the branch {self.branch_name}. "
                + "Branches must be of the form 'type-scenario[+modifier...]'. "
                + "See README.md for more information."
            )
        return scenario_match.group("scenario")

    def set_config_modifiers(self) -> list[str]:
        # Regex below is essentially 'give me the 'modifier' part in all the '+modifier's in the branch name'
        return re.findall(r"\+([^+]+)", self.branch_name)


@pytest.fixture(scope="class")
def branch(control_path, target_branch):
    branch_name = target_branch
    if branch_name is None:
        # Default to current branch name
        branch_name = get_git_branch_name(control_path)
        assert (
            branch_name is not None
        ), f"Failed getting git branch name of control path: {control_path}"
        warnings.warn(
            "Target branch is not specifed, defaulting to current git branch: "
            f"{branch_name}. As some ACCESS-ESM1.5 tests infer information, "
            "such as scenario and modifiers, from the target branch name, some "
            "tests may not be run. To set use --target-branch flag in pytest call"
        )

    return AccessEsm1p5Branch(branch_name)


@pytest.mark.access_esm1p5
class TestAccessEsm1p5:
    """ACCESS-ESM1.5 Specific configuration and metadata tests"""

    def test_access_esm1p5_manifest_exe_in_release_spack_location(
        self, config, control_path
    ):
        check_manifest_exes_in_spack_location(
            model_module_name=ACCESS_ESM1P5_MODULE_NAME,
            model_repo_name=ACCESS_ESM1P5_REPOSITORY_NAME,
            control_path=control_path,
            config=config,
        )

    @pytest.mark.parametrize(
        "field,expected", [("realm", VALID_REALMS), ("keyword", VALID_KEYWORDS)]
    )
    def test_metadata_field_equal_expected_sequence(self, field, expected, metadata):

        assert (
            field in metadata and metadata[field] is not None
        ), error_field_nonexistence(field, "metadata.yaml")

        field_set: set[str] = set(metadata[field])

        assert field_set == expected, error_field_incorrect(
            field, "metadata.yaml", "sequence", expected
        )

    @pytest.mark.parametrize(
        "field,expected",
        [
            ("nominal_resolution", VALID_NOMINAL_RESOLUTION),
            ("reference", VALID_REFERENCE),
        ],
    )
    def test_metadata_field_equal_expected_value(self, field, expected, metadata):
        assert field in metadata and metadata[field] == expected, error_field_incorrect(
            field, "metadata.yaml", expected
        )

    def test_config_start(self, branch, config):
        assert (
            "calendar" in config
            and config["calendar"] is not None
            and "start" in config["calendar"]
            and config["calendar"]["start"] is not None
        ), error_field_nonexistence("calendar.start", "config.yaml")

        start: dict[str, int] = config["calendar"]["start"]

        if branch.config_scenario == "preindustrial":
            assert start == VALID_PREINDUSTRIAL_START, error_field_incorrect(
                "calendar.start", "config.yaml", VALID_PREINDUSTRIAL_START
            )
        elif branch.config_scenario == "historical":
            assert start == VALID_HISTORICAL_START, error_field_incorrect(
                "calendar.start", "config.yaml", VALID_HISTORICAL_START
            )
        else:
            pytest.fail(f"Cannot test unknown scenario {branch.config_scenario}.")

    def test_config_runtime(self, config):
        assert (
            "calendar" in config
            and config["calendar"] is not None
            and "runtime" in config["calendar"]
            and config["calendar"]["runtime"] is not None
        ), error_field_nonexistence("calendar.runtime", "config.yaml")

        runtime: dict[str, int] = config["calendar"]["runtime"]

        assert runtime == VALID_RUNTIME, error_field_incorrect(
            "calendar.runtime", "config.yaml", VALID_RUNTIME
        )

    def test_config_restart_freq(self, config):
        assert (
            "restart_freq" in config and config["restart_freq"] is not None
        ), error_field_nonexistence("restart_freq", "config.yaml")
        assert config["restart_freq"] == VALID_RESTART_FREQ, error_field_incorrect(
            "restart_freq", "config.yaml", VALID_RESTART_FREQ
        )

    def test_mppnccombine_fast_collate_exe(self, config):
        if "collate" in config:
            assert (
                config["collate"]["exe"] == VALID_MPPNCCOMBINE_EXE
            ), error_field_incorrect(
                "collate.exe", "config.yaml", VALID_MPPNCCOMBINE_EXE
            )

            assert config["collate"]["mpi"], error_field_incorrect(
                "collate.mpi", "config.yaml", "true"
            )
