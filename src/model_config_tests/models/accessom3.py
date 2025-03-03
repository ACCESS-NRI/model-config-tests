"""Specific Access-OM3 Model setup and post-processing"""

from collections import defaultdict
from pathlib import Path
from typing import Any

import f90nml
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

        self.mom_restart_pointer_filename = "rpointer.ocn"
        self.mom_restart_pointer = self.output_0 / self.mom_restart_pointer_filename
        self.runconfig = experiment.control_path / "nuopc.runconfig"
        self.wav_in = experiment.control_path / "wav_in"

    def set_model_runtime(
        self, years: int = 0, months: int = 0, seconds: int = DEFAULT_RUNTIME_SECONDS
    ):
        """Set config files to a short time period for experiment run.
        Default is 3 hours"""
        runconfig = Runconfig(self.runconfig)

        # Check that ocean model component is MOM since checksums are obtained from
        # MOM6 restarts. Fail early if not
        ocn_model = runconfig.get("ALLCOMP_attributes", "OCN_model")
        if ocn_model != "mom":
            raise ValueError(
                "ACCESS-OM3 reproducibility checks utilize checksums written in MOM6 "
                "restarts and hence can only be used with ACCESS-OM3 configurations that "
                f"use MOM6. This configuration uses OCN_model = {ocn_model}."
            )

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

        # Unfortunately WW3 doesn't (yet) obey the nuopc.runconfig. This should change in a
        # future release, but for now we have to set WW3 runtime in wav_in. See
        # https://github.com/COSIMA/access-om3/issues/239
        if self.wav_in.exists():
            with open(self.wav_in) as f:
                nml = f90nml.read(f)

            nml["output_date_nml"]["date"]["restart"]["stride"] = int(n)
            nml.write(self.wav_in, force=True)

    def output_exists(self) -> bool:
        """Check for existing output file"""
        return self.mom_restart_pointer.exists()

    def extract_checksums(
        self, output_directory: Path = None, schema_version: str = None
    ) -> dict[str, Any]:
        """Parse output file and create checksum using defined schema"""
        if output_directory:
            mom_restart_pointer = output_directory / self.mom_restart_pointer_filename
        else:
            mom_restart_pointer = self.mom_restart_pointer

        # MOM6 saves checksums for each variable in its restart files. Extract these
        # attributes for each restart
        output_checksums: dict[str, list[any]] = defaultdict(list)

        with open(mom_restart_pointer) as f:
            for restart_file in f.readlines():
                restart = mom_restart_pointer.parent / restart_file.rstrip()
                rootgrp = Dataset(restart, "r")
                for variable in sorted(rootgrp.variables):
                    var = rootgrp[variable]
                    if "checksum" in var.ncattrs():
                        output_checksums[variable.strip()].append(var.checksum.strip())
                rootgrp.close()

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
