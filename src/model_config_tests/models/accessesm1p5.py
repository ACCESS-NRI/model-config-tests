"""Specific ACCESS-ESM1.5 Model setup and post-processing"""

from pathlib import Path
from typing import Any

import f90nml
import yaml

from model_config_tests.models.model import SCHEMA_VERSION_1_0_0, Model
from model_config_tests.models.mom5 import mom5_extract_checksums
from model_config_tests.models.um7 import um7_extract_norms
from model_config_tests.util import DAY_IN_SECONDS

# Default model runtime (24 hrs)
DEFAULT_RUNTIME_SECONDS = DAY_IN_SECONDS


class AccessEsm1p5(Model):
    def __init__(self, experiment):
        super().__init__(experiment)
        # Override model default runtime
        self.default_runtime_seconds = DEFAULT_RUNTIME_SECONDS

        self.submodels = {
            submodel["model"]: submodel["name"]
            for submodel in self.experiment.config["submodels"]
        }

        self.set_output_files(model_std_file="access.out")

    def set_output_files(self, model_std_file: str):
        """
        Set paths for output files used for extracting checksums, depending on
        available submodels.
        """
        if "mom" in self.submodels:
            self.output_filename = model_std_file
        elif "um" in self.submodels:
            # UM output is stored in submodel ouptut sub-directory
            self.output_filename = Path(self.submodels["um"]) / "atm.fort6.pe0"
        else:
            raise RuntimeError(
                "Failed to find suitable submodel for checksum extraction."
                "Required 'mom' or 'um' submodels not present in config.yaml."
            )

        self.output_file = self.output_0 / self.output_filename

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

        # Write UM and CICE restarts at daily frequency.
        # Only set when these components are present to allow for
        # amip configurations.

        if "um" in self.submodels:
            atmosphere_config = (
                self.experiment.control_path / self.submodels["um"] / "namelists"
            )
            # Write atmosphere restarts at daily frequency
            with open(atmosphere_config) as f:
                atmosphere_nml = f90nml.read(f)
            # 48 timesteps per day
            atmosphere_nml["NLSTCGEN"]["DUMPFREQim"] = [48, 0, 0, 0]
            atmosphere_nml.write(atmosphere_config, force=True)

        if "cice" in self.submodels:
            # Write ice restarts at daily frequency
            ice_config = (
                self.experiment.control_path / self.submodels["cice"] / "cice_in.nml"
            )
            with open(ice_config) as f:
                ice_nml = f90nml.read(f)
            ice_nml["setup_nml"]["dumpfreq"] = "d"
            ice_nml.write(ice_config, force=True)

    def output_exists(self) -> bool:
        """Check for existing output file"""
        return self.output_file.exists()

    def extract_checksums(
        self, output_directory: Path = None, schema_version: str = None
    ) -> dict[str, Any]:
        """Parse output file and create checksum using defined schema"""
        if output_directory is not None:
            output_filepath = output_directory / self.output_filename
        else:
            output_filepath = self.output_file

        # Extract checksums from output, preferentially using mom5
        submodel_extract_checksums = None
        if "mom" in self.submodels:
            submodel_extract_checksums = mom5_extract_checksums
        elif "um" in self.submodels:
            # UM output is stored in submodel ouptut sub-directory
            submodel_extract_checksums = um7_extract_norms

        output_checksums = submodel_extract_checksums(output_filepath)

        # Format checksums
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
