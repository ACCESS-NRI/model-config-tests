"""Specific ACCESS-ESM1.5 Model setup and post-processing"""

from pathlib import Path
from typing import Any

import yaml

from model_config_tests.models.model import SCHEMA_VERSION_1_0_0, Model
from model_config_tests.models.mom5 import mom5_extract_checksums
from model_config_tests.util import DAY_IN_SECONDS

# Default model runtime (24 hrs)
DEFAULT_RUNTIME_SECONDS = DAY_IN_SECONDS


class AccessEsm1p5(Model):
    def __init__(self, experiment):
        super().__init__(experiment)
        # Override model default runtime
        self.default_runtime_seconds = DEFAULT_RUNTIME_SECONDS

        self.output_file = self.experiment.output000 / "access.out"

    def set_model_runtime(
        self, years: int = 0, months: int = 0, seconds: int = DEFAULT_RUNTIME_SECONDS
    ):
        """Set config files to a short time period for experiment run.
        Default is 24 hours"""
        with open(self.experiment.config_path) as f:
            doc = yaml.safe_load(f)

        assert (
            seconds % DAY_IN_SECONDS == 0
        ), "Only days are supported in payu UM driver"

        # Set runtime in config.yaml
        runtime_config = {
            "years": years,
            "months": months,
            "days": 0,
            "seconds": seconds,
        }
        if "calendar" in doc:
            doc["calendar"]["runtime"] = runtime_config
        else:
            doc["calendar"] = {"runtime": runtime_config}

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
