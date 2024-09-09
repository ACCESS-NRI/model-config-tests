# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""ACCESS-OM3 specific configuration tests"""

import re
from pathlib import Path

import pytest
from payu.models.cesm_cmeps import Runconfig

#########################
# Valid field constants #
#########################

# Error message functions


def error_runconfig_variable_none(section: str, variable: str) -> str:
    return f"nuopc.runconfig: section '{section}' variable {variable} does not exist."


def error_runseq_variable_none(variable: str) -> str:
    return f"nuopc.runseq: {variable} does not exist."


################################
# ACCESS-OM3-specific Fixtures #
################################


@pytest.fixture(scope="class")
def nuopc_runconfig(control_path: Path) -> Runconfig:
    runconfig_path: Path = control_path / "nuopc.runconfig"

    return Runconfig(runconfig_path)


@pytest.fixture(scope="class")
def nuopc_runseq(control_path: Path) -> list[str]:
    runseq_path: Path = control_path / "nuopc.runseq"

    with open(runseq_path) as f:
        # FIXME: Find something better
        return f.readlines()


#########
# Tests #
#########


@pytest.mark.access_om3
class TestAccessOM3:
    """ACCESS-OM3 Specific configuration and metadata tests"""

    def test_runconfig_ocn_cpl_dt_equals_runseq_coupling_timestep(
        self, nuopc_runconfig: Runconfig, nuopc_runseq: list[str]
    ):
        # Setup runconfig variable
        rcfg_section = "CLOCK_attributes"
        rcfg_variable = "ocn_cpl_dt"
        rcfg_ocn_cpl_dt = nuopc_runconfig.get(rcfg_section, rcfg_variable)

        assert rcfg_ocn_cpl_dt, error_runconfig_variable_none(
            rcfg_section, rcfg_variable
        )

        # Setup runseq variable
        rseq_cpl_ts_match: str = [
            line for line in nuopc_runseq if re.match(r"@(\S*)", line)
        ][0]
        rseq_cpl_ts = rseq_cpl_ts_match.group(1)

        assert rseq_cpl_ts, error_runseq_variable_none("coupling timestep")

        assert rcfg_ocn_cpl_dt == rseq_cpl_ts
