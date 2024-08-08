# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""ACCESS-ESM1.5 specific configuration tests"""

import pytest

from model_config_tests.qa.test_config import check_manifest_exes_in_spack_location

# Name of module on NCI
ACCESS_ESM1P5_MODULE_NAME = "access-esm1p5"

# Name of Model Repository - used for retrieving spack location files for released versions
ACCESS_ESM1P5_REPOSITORY_NAME = "ACCESS-ESM1.5"


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
