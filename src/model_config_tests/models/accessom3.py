"""Specific Access-OM3 Model setup and post-processing"""

from collections import defaultdict
from pathlib import Path
from typing import Any

from netCDF4 import Dataset
from payu.models.cesm_cmeps import Runconfig

from model_config_tests.models.model import (
    DEFAULT_RUNTIME_SECONDS,
    SCHEMA_VERSION_1_0_0,
    Model,
)


class AccessOm3(Model):
    def __init__(self, experiment):
        super().__init__(experiment)

        # ACCESS-OM3 uses restarts for repro testing
        self.output_0 = self.experiment.restart000
        self.output_1 = self.experiment.restart001

        self.mom_restart_pointer = self.output_0 / "rpointer.ocn"
        self.runconfig = experiment.control_path / "nuopc.runconfig"

    def set_model_runtime(
        self, years: int = 0, months: int = 0, seconds: int = DEFAULT_RUNTIME_SECONDS
    ):
        """Set config files to a short time period for experiment run.
        Default is 3 hours"""
        runconfig = Runconfig(self.runconfig)

        if years == months == 0:
            freq = "nseconds"
            n = str(seconds)

        elif seconds == 0:
            freq = "nmonths"
            n = str(12 * years + months)
        else:
            raise NotImplementedError(
                "Cannot specify runtime in seconds and year/months at the same time"
            )

        runconfig.set("CLOCK_attributes", "restart_n", n)
        runconfig.set("CLOCK_attributes", "restart_option", freq)
        runconfig.set("CLOCK_attributes", "stop_n", n)
        runconfig.set("CLOCK_attributes", "stop_option", freq)

        runconfig.write()

    def output_exists(self) -> bool:
        """Check for existing output file"""
        return self.mom_restart_pointer.exists()

    def extract_checksums(
        self, output_directory: Path = None, schema_version: str = None
    ) -> dict[str, Any]:
        """Parse output file and create checksum using defined schema"""
        if output_directory:
            mom_restart_pointer = output_directory / "rpointer.ocn"
        else:
            mom_restart_pointer = self.mom_restart_pointer

        # MOM6 saves checksums for each variable in its restart files. Extract these
        # attributes for each restart
        output_checksums: dict[str, list[any]] = defaultdict(list)

        mom_restarts = []
        with open(mom_restart_pointer) as f:
            for restart in f.readlines():
                mom_restarts.append(mom_restart_pointer.parent / restart.rstrip())

        for mom_restart in mom_restarts:
            rootgrp = Dataset(mom_restart, "r")
            for v in rootgrp.variables:
                var = rootgrp[v]
                if "checksum" in var.ncattrs():
                    output_checksums[var.long_name.strip()].append(var.checksum.strip())

        if schema_version is None:
            schema_version = self.default_schema_version

        if schema_version == SCHEMA_VERSION_1_0_0:
            checksums = {
                "schema_version": schema_version,
                "output": dict(output_checksums),
            }
        else:
            raise NotImplementedError(
                f"Unsupported checksum schema version: {schema_version}"
            )

        return checksums
