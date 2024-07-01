"""Specific ACCESS-ESM1.5 Model setup and post-processing"""

from pathlib import Path
from typing import Any

import yaml

from model_config_tests.models.model import SCHEMA_VERSION_1_0_0, Model
from model_config_tests.models.mom import mom5_extract_checksums


class Access(Model):
    def __init__(self, experiment):
        super().__init__(experiment)

        self.output_file = self.experiment.output000 / "access.out"

    def set_model_runtime(self, years: int = 0, months: int = 0, seconds: int = 10800):
        """Set config files to a short time period for experiment run.
        Default is 3 hours"""
        with open(self.experiment.config_path) as f:
            doc = yaml.safe_load(f)

        # Set runtime in config.yaml
        doc["calendar"]["runtime"] = {
            "year": years,
            "month": months,
            "days": 0,
            "seconds": seconds,
        }

        with open(self.experiment.config_path, "w") as f:
            yaml.dump(doc, f)

    def output_exists(self) -> bool:
        """Check for existing output file"""
        return self.output_file.exists()

    def extract_checksums(
        self, output_directory: Path = None, schema_version: str = None
    ) -> dict[str, Any]:
        """Parse output file and create checksum using defined schema"""
        if output_directory:
            output_filename = output_directory / "access.out"
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
