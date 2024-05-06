"""Specific Access-OM3 Model setup and post-processing"""

import hashlib
from pathlib import Path
from payu.models.cesm_cmeps import Runconfig
from typing import Dict, Any

from models.model import Model

BASE_SCHEMA_URL = "https://raw.githubusercontent.com/ACCESS-NRI/schema/main/au.org.access-nri/model/access-om2/experiment/reproducibility/checksums"

SCHEMA_VERSION_1_0_0 = "1-0-0"
DEFAULT_SCHEMA_VERSION = SCHEMA_VERSION_1_0_0
SUPPORTED_SCHEMA_VERSIONS = [SCHEMA_VERSION_1_0_0]

class AccessOm3(Model):
    def __init__(self, experiment):
        super(AccessOm3, self).__init__(experiment)
        self.output_file = self.experiment.output000 / 'ocean.stats'

        self.runconfig = experiment.control_path / 'nuopc.runconfig'
        self.ocean_config = experiment.control_path / 'input.nml'
        self.default_schema_version = DEFAULT_SCHEMA_VERSION

    def set_model_runtime(self,
                          years: int = 0,
                          months: int = 0,
                          seconds: int = 10800):
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
                f"Cannot specify runtime in seconds and year/months at the same time")

        runconfig.set("CLOCK_attributes", "restart_n", n)
        runconfig.set("CLOCK_attributes", "restart_option", freq)
        runconfig.set("CLOCK_attributes", "stop_n", n)
        runconfig.set("CLOCK_attributes", "stop_option", freq)

        runconfig.write()

    def output_exists(self) -> bool:
        """Check for existing output file"""
        return self.output_file.exists()

    def extract_checksums(self,
                          output_directory: Path = None,
                          schema_version: str = None) -> Dict[str, Any]:
        """Parse output file and create checksum using defined schema"""
        if output_directory:
            output_filename = output_directory / 'ocean.stats'
        else:
            output_filename = self.output_file

        # ocean.stats is used for regression testing in MOM6's own test suite
        # See https://github.com/mom-ocean/MOM6/blob/2ab885eddfc47fc0c8c0bae46bc61531104428d5/.testing/Makefile#L495-L501
        # Here we calculate the md5 hash of ocean.stats
        with open(output_filename, 'rb') as f:
            contents = f.read()
            md5_hash = hashlib.md5(contents).hexdigest()

        output_checksums = {"ocean.stats": [md5_hash]}

        if schema_version is None:
            schema_version = DEFAULT_SCHEMA_VERSION

        if schema_version == SCHEMA_VERSION_1_0_0:
            checksums = {
                "schema_version": schema_version,
                "output": dict(output_checksums)
            }
        else:
            raise NotImplementedError(
                f"Unsupported checksum schema version: {schema_version}")

        return checksums

