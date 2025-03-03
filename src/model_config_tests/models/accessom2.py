"""Specific Access-OM2 Model setup and post-processing"""

from pathlib import Path
from typing import Any

import f90nml

from model_config_tests.models.model import (
    DEFAULT_RUNTIME_SECONDS,
    SCHEMA_VERSION_1_0_0,
    Model,
)
from model_config_tests.models.mom5 import mom5_extract_checksums


class AccessOm2(Model):
    def __init__(self, experiment):
        super().__init__(experiment)
        self.output_filename = "access-om2.out"
        self.output_file = self.output_0 / self.output_filename

        self.accessom2_config = experiment.control_path / "accessom2.nml"
        self.ocean_config = experiment.control_path / "ocean" / "input.nml"

    def set_model_runtime(
        self, years: int = 0, months: int = 0, seconds: int = DEFAULT_RUNTIME_SECONDS
    ):
        """Set config files to a short time period for experiment run.
        Default is 3 hours"""
        with open(self.accessom2_config) as f:
            nml = f90nml.read(f)

        # Check that two of years, months, seconds is zero
        if sum(x == 0 for x in (years, months, seconds)) != 2:
            raise NotImplementedError(
                "Cannot specify runtime in seconds and years and months"
                + " at the same time. Two of which must be zero"
            )

        nml["date_manager_nml"]["restart_period"] = [years, months, seconds]
        nml.write(self.accessom2_config, force=True)

    def output_exists(self) -> bool:
        """Check for existing output file"""
        return self.output_file.exists()

    def extract_checksums(
        self, output_directory: Path = None, schema_version: str = None
    ) -> dict[str, Any]:
        """Parse output file and create checksum using defined schema"""
        if output_directory:
            output_filename = output_directory / self.output_filename
        else:
            output_filename = self.output_file

        # Extract mom5 checksums
        output_checksums = mom5_extract_checksums(output_filename)

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
