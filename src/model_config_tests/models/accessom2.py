"""Specific Access-OM2 Model setup and post-processing"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from model_config_tests.models.model import Model, SCHEMA_VERSION_1_0_0


class AccessOm2(Model):
    def __init__(self, experiment):
        super().__init__(experiment)
        self.output_file = self.experiment.output000 / "access-om2.out"

        self.accessom2_config = experiment.control_path / 'accessom2.nml'
        self.ocean_config = experiment.control_path / 'ocean' / 'input.nml'

    def set_model_runtime(self, years: int = 0, months: int = 0, seconds: int = 10800):
        """Set config files to a short time period for experiment run.
        Default is 3 hours"""
        with open(self.accessom2_config) as f:
            nml = f90nml.read(f)

        # Check that two of years, months, seconds is zero
        if sum(x == 0 for x in (years, months, seconds)) != 2:
            raise NotImplementedError(
                "Cannot specify runtime in seconds and years and months" +
                " at the same time. Two of which must be zero")

        nml['date_manager_nml']['restart_period'] = [years, months, seconds]
        nml.write(self.accessom2_config, force=True)

    def output_exists(self) -> bool:
        """Check for existing output file"""
        return self.output_file.exists()

    def extract_checksums(
        self, output_directory: Path = None, schema_version: str = None
    ) -> dict[str, Any]:
        """Parse output file and create checksum using defined schema"""
        if output_directory:
            output_filename = output_directory / "access-om2.out"
        else:
            output_filename = self.output_file

        # Regex pattern for checksums in the `<model>.out` file
        # Examples:
        # [chksum] ht              -2390360641069121536
        # [chksum] hu               6389284661071183872
        # [chksum] htr               928360042410663049
        pattern = r"\[chksum\]\s+(.+)\s+(-?\d+)"

        # checksums outputted in form:
        # {
        #   "ht": ["-2390360641069121536"],
        #   "hu": ["6389284661071183872"],
        #   "htr": ["928360042410663049"]
        # }
        # with potential for multiple checksums for one key.
        output_checksums: dict[str, list[any]] = defaultdict(list)

        with open(output_filename) as f:
            for line in f:
                # Check for checksum pattern match
                match = re.match(pattern, line)
                if match:
                    # Extract values
                    field = match.group(1).strip()
                    checksum = match.group(2).strip()

                    output_checksums[field].append(checksum)

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
