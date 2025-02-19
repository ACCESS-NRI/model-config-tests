# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""ACCESS-OM3 specific configuration tests"""

import pytest

from model_config_tests.qa.test_config import check_manifest_exes_in_spack_location


@pytest.mark.access_om3
class TestAccessOM3:
    """ACCESS-OM3 Specific configuration and metadata tests"""

    def test_access_om3_manifest_exe_in_release_spack_location(
        self, config, control_path
    ):

        check_manifest_exes_in_spack_location(
            model_module_name="access-om3",
            model_repo_name="ACCESS-OM3",
            control_path=control_path,
            config=config,
        )
