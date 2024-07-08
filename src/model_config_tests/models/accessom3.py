"""Specific Access-OM3 Model setup and post-processing"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from payu.models.cesm_cmeps import Runconfig

from model_config_tests.models.model import (
    DEFAULT_RUNTIME_SECONDS,
    SCHEMA_VERSION_1_0_0,
    Model,
)


class AccessOm3(Model):
    def __init__(self, experiment):
        super().__init__(experiment)
        self.output_file = self.experiment.output000 / "ocean.stats"

        self.runconfig = experiment.control_path / "nuopc.runconfig"
        self.ocean_config = experiment.control_path / "input.nml"

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
        return self.output_file.exists()

    def extract_checksums(
        self, output_directory: Path = None, schema_version: str = None
    ) -> dict[str, Any]:
        """Parse output file and create checksum using defined schema"""
        if output_directory:
            output_filename = output_directory / "ocean.stats"
        else:
            output_filename = self.output_file

        # ocean.stats is used for regression testing in MOM6's own test suite
        # See https://github.com/mom-ocean/MOM6/blob/2ab885eddfc47fc0c8c0bae46bc61531104428d5/.testing/Makefile#L495-L501
        # Rows in ocean.stats look like:
        #      0,  693135.000,     0, En 3.0745627134675957E-23, CFL  0.00000, ...
        # where the first three columns are Step, Day, Truncs and the remaining
        # columns include a label for what they are (e.g. En = Energy/Mass)
        # Header info is only included for new runs so can't be relied on
        output_checksums: dict[str, list[any]] = defaultdict(list)

        with open(output_filename) as f:
            lines = f.readlines()
            # Skip header if it exists (for new runs)
            istart = 2 if "Step" in lines[0] else 0
            for line in lines[istart:]:
                for col in line.split(","):
                    # Only keep columns with labels (ie not Step, Day, Truncs)
                    col = re.split(" +", col.strip().rstrip("\n"))
                    if len(col) > 1:
                        output_checksums[col[0]].append(col[-1])

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
