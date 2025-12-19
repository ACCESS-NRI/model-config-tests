# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""ACCESS-OM2 specific configuration tests"""

import re
import warnings

import f90nml
import pytest

from model_config_tests.config_tests.qa.test_config import (
    check_manifest_exes_in_spack_location,
)
from model_config_tests.util import get_git_branch_name

# Mutually exclusive topic keywords
TOPIC_KEYWORDS = {
    "spatial extent": {"global", "regional"},
    "forcing product": {"JRA55", "ERA5"},
    "forcing mode": {
        "repeat-year",
        "ryf",
        "repeat-decade",
        "rdf",
        "interannual",
        "iaf",
    },
    "model": {"access-om2", "access-om2-025", "access-om2-01"},
    "model variant": {"bgc"},
}

# Nominal resolutions are sourced from CMIP6 controlled vocabulary
# https://github.com/WCRP-CMIP/CMIP6_CVs/blob/main/CMIP6_nominal_resolution.json
NOMINAL_RESOLUTION = {"025deg": "25 km", "01deg": "10 km", "1deg": "100 km"}

# Name of modules on NCI
ACCESS_OM2_MODULE_NAME = "access-om2"
ACCESS_OM2_BGC_MODULE_NAME = "access-om2-bgc"

# Name of Model Repositories - used for retrieving spack location files for released versions
ACCESS_OM2_REPOSITORY_NAME = "ACCESS-OM2"
ACCESS_OM2_BGC_REPOSITORY_NAME = "ACCESS-OM2-BGC"

# Expected metadata notes with conditions of use
EXPECTED_METADATA_NOTES = """COSIMA request that users of this or other ACCESS-OM2 model code or output data:
(a) add a project description to COSIMA's list:
https://docs.google.com/spreadsheets/d/18BDyZlHTSy6EOaf_5o9CwGBOu4pBj88XsS2vNW4R_2o
(b) consider citing Kiss et al. (2020) [http://doi.org/10.5194/gmd-13-401-2020] and papers describing relevant
configuration updates - see https://forum.access-hive.org.au/t/access-om2-control-experiments/258
(c) include an acknowledgement such as that suggested here: https://cosima.org.au/index.php/get-involved/
(d) let COSIMA know of any publications which use these models or data so they can add them to their list:
https://scholar.google.com/citations?hl=en&user=inVqu_4AAAAJ
(e) Tell ACCESS-NRI that you are using ACCESS-NRI infrastructure: https://www.access-nri.org.au/resources/user-reporting/"""

# Expected metadata model name
EXPECTED_METADATA_MODEL = "ACCESS-OM2"


class AccessOM2Branch:
    """Use the naming patterns of the branch name to infer information of
    the ACCESS-OM2 config"""

    def __init__(self, branch_name):
        self.branch_name = branch_name
        self.set_resolution()

        self.is_high_resolution = self.resolution in ["025deg", "01deg"]
        self.is_bgc = "bgc" in branch_name

        # Set expected module and model repository names
        if self.is_bgc:
            self.module_name = ACCESS_OM2_BGC_MODULE_NAME
            self.model_repository_name = ACCESS_OM2_BGC_REPOSITORY_NAME
        else:
            self.module_name = ACCESS_OM2_MODULE_NAME
            self.model_repository_name = ACCESS_OM2_REPOSITORY_NAME

    def set_resolution(self):
        # Resolutions are ordered, so the start of the list are matched first
        resolutions = ["025deg", "01deg", "1deg"]
        self.resolution = None
        for res in resolutions:
            if res in self.branch_name:
                self.resolution = res
                return

        pytest.fail(
            f"Branch name {self.branch_name} has an unknown resolution. "
            + f"Current supported resolutions: {', '.join(resolutions)}"
        )


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
            "Target branch is not specified, defaulting to current git branch: "
            f"{branch_name}. As some ACCESS-OM2 tests infer information, "
            "such as resolution, from the target branch name, some tests may "
            "not be run. To set use --target-branch flag in pytest call"
        )

    return AccessOM2Branch(branch_name)


@pytest.mark.access_om2
class TestAccessOM2:
    """ACCESS-OM2 Specific configuration and metadata tests"""

    def test_mppncombine_fast_collate_exe(self, config, branch):
        if branch.is_high_resolution:
            pattern = r".*mppnccombine-fast"
            if "collate" in config:
                assert re.match(
                    pattern, config["collate"]["exe"]
                ), "Expect collate executable set to mppnccombine-fast"

                assert config["collate"][
                    "mpi"
                ], "Expect `mpi: true` when using mppnccombine-fast"

    def test_sync_userscript_ice_concatenation(self, config):
        # This script runs in the sync pbs job before syncing output to a
        # remote location
        script = "/g/data/vk83/apps/om2-scripts/concatenate_ice/concat_ice_daily.sh"
        assert (
            "userscripts" in config
            and "sync" in config["userscripts"]
            and config["userscripts"]["sync"] == script
        ), (
            "Expect sync userscript set to ice-concatenation script."
            + f"\nuserscript:\n  sync: {script}"
        )

    def test_metadata_realm(self, metadata, branch):
        expected_realms = {"ocean", "seaIce"}
        expected_config = "realm:\n - ocean\n - seaIce"
        if branch.is_bgc:
            expected_realms.add("ocnBgchem")
            expected_config += "\n - ocnBgchem"

        assert (
            "realm" in metadata
            and metadata["realm"] is not None
            and set(metadata["realm"]) == expected_realms
        ), ("Expected metadata realm set to:\n" + expected_config)

    def test_restart_period(self, branch, control_path):
        accessom2_nml_path = control_path / "accessom2.nml"
        assert accessom2_nml_path.exists()

        accessom2_nml = f90nml.read(accessom2_nml_path)
        restart_period = accessom2_nml["date_manager_nml"]["restart_period"]

        if branch.resolution == "1deg":
            expected_period = [5, 0, 0]
        elif branch.resolution == "025deg":
            if branch.is_bgc:
                expected_period = [1, 0, 0]
            else:
                expected_period = [2, 0, 0]
        elif branch.resolution == "01deg":
            if branch.is_bgc:
                expected_period = [0, 1, 0]
            else:
                expected_period = [0, 3, 0]
        else:
            pytest.fail(
                f"The expected restart period is not defined for given "
                f"resolution: {branch.resolution}"
            )
        assert restart_period == expected_period

    def test_metadata_keywords(self, metadata):

        assert "keywords" in metadata
        metadata_keywords = set(metadata["keywords"])

        expected_keywords = set()
        for topic, keywords in TOPIC_KEYWORDS.items():
            mutually_exclusive = metadata_keywords.intersection(keywords)
            assert (
                len(mutually_exclusive) <= 1
            ), f"Topic {topic} has multiple mutually exlusive keywords: " + str(
                mutually_exclusive
            )

            expected_keywords = expected_keywords.union(keywords)

        unrecognised_keywords = metadata_keywords.difference(expected_keywords)
        assert (
            len(unrecognised_keywords) == 0
        ), f"Metadata has unrecognised keywords: {unrecognised_keywords}"

    def test_metadata_nominal_resolution(self, metadata, branch):
        assert branch.resolution in NOMINAL_RESOLUTION, (
            "The expected nominal_resolution is not defined for given "
            + f"resolution: {branch.resolution}"
        )

        expected = NOMINAL_RESOLUTION[branch.resolution]
        assert (
            "nominal_resolution" in metadata
            and metadata["nominal_resolution"] == expected
        ), f"Expected nominal_resolution field set to: {expected}"

    def test_access_om2_manifest_exe_in_release_spack_location(
        self, config, branch, control_path
    ):
        # Infer module and repository name from branch - as different for the BGC configuration
        check_manifest_exes_in_spack_location(
            model_module_name=branch.module_name,
            model_repo_name=branch.model_repository_name,
            control_path=control_path,
            config=config,
        )

    def test_access_om2_metadata_model(self, metadata):
        assert (
            "model" in metadata and metadata["model"] == EXPECTED_METADATA_MODEL
        ), f"Expected metadata model field set to: {EXPECTED_METADATA_MODEL}"

    def test_access_om2_metadata_notes(self, metadata):
        assert "notes" in metadata and metadata["notes"] == EXPECTED_METADATA_NOTES, (
            "Expected metadata notes field set to:\n" + EXPECTED_METADATA_NOTES
        )
