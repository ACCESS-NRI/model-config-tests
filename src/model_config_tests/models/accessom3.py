"""Specific Access-OM3 Model setup and post-processing"""

from collections import defaultdict
from pathlib import Path
from typing import Any

import f90nml
from netCDF4 import Dataset
from payu.models.cesm_cmeps import Runconfig

from model_config_tests.models.model import SCHEMA_VERSION_1_0_0, Model
from model_config_tests.util import HOUR_IN_SECONDS

# Default model runtime (6 hrs)
DEFAULT_RUNTIME_SECONDS = 6 * HOUR_IN_SECONDS


class AccessOm3(Model):
    def __init__(self, experiment):
        super().__init__(experiment)

        # Override model default runtime
        self.default_runtime_seconds = DEFAULT_RUNTIME_SECONDS

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
        Default is 6 hours"""
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
        self,
        output_directory: Path = None,
        schema_version: str = None,
    ) -> dict[str, Any]:
        """Parse output file and create checksum using defined schema"""
        if output_directory:
            mom_restart_pointer = output_directory / self.mom_restart_pointer_filename
        else:
            mom_restart_pointer = self.mom_restart_pointer

        # MOM6 saves checksums for each variable in its restart files.
        # In unified (collated) restart files, the checksum is stored once per variable.
        # In split (per-processor) restarts, the global checksum is duplicated
        # into every tile file, hence reading one tile (e.g. .0000) is sufficient.
        output_checksums: dict[str, list[any]] = defaultdict(list)

        with open(mom_restart_pointer) as f:
            for restart_file in f.readlines():
                restart = mom_restart_pointer.parent / restart_file.rstrip()
                # collect restart file / the first tile
                restart_output = self._collect_restart_tiles(restart)
                with Dataset(restart_output, "r") as rootgrp:
                    for vname in sorted(rootgrp.variables):
                        var = rootgrp[vname]
                        if "checksum" in var.ncattrs():
                            output_checksums[vname.strip()].append(var.checksum.strip())

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

    def extract_full_checksums(self, output_directory: Path = None) -> dict[str, Any]:
        """Parse output file for all available checksums"""
        return self.extract_checksums(
            output_directory=output_directory,
            schema_version=SCHEMA_VERSION_1_0_0,
        )["output"]

    def check_checksums_over_restarts(
        self, long_run_checksum, short_run_checksum_0, short_run_checksum_1
    ) -> bool:
        """Compare a checksums from a long run (e.g. 2 days) against
        checksums from 2 short runs (e.g. 1 day)"""
        short_run_checksums = short_run_checksum_0["output"]
        for field, checksums in short_run_checksum_1["output"].items():
            if field not in short_run_checksums:
                short_run_checksums[field] = checksums
            else:
                short_run_checksums[field].extend(checksums)

        matching_checksums = True
        for field, checksums in long_run_checksum["output"].items():
            for checksum in checksums:
                if field not in short_run_checksums:
                    print(
                        f"Checksum field for {field} found in long run but not in short runs"
                    )
                    matching_checksums = False
                else:
                    if checksum not in short_run_checksums[field]:
                        # Allow for checksums to differ by 8 in the first hex digit to allow
                        # for differences in the sign of zero between restart arrays
                        # See https://github.com/ACCESS-NRI/access-om3-configs/issues/823
                        first_digit = int(checksum[0], 16)
                        pmzeros_digit = (first_digit + 8) % 16
                        pmzeros_checksum = f"{pmzeros_digit:X}" + checksum[1:]
                        if pmzeros_checksum not in short_run_checksums[field]:
                            print(f"Unequal checksum: {field}: {checksum}")
                            matching_checksums = False

        return matching_checksums

    @staticmethod
    def _collect_restart_tiles(restart: Path) -> list[Path]:
        """
        Return the first restart tile:
        - If a unified (collated) restart file exists, return it.
        - If split into tiles, return the tile with the lowest numeric suffix.
          We use the tile with the lowest numeric suffix because tiles that are
          completely masked are not written.

        MOM6 stores the same global checksum in all tiles, so only the first tile
        is needed when extracting checksums.
        """
        if restart.exists():
            return restart

        # any restart tiles
        parent = restart.parent
        tiles = sorted(
            parent.glob(restart.name + ".[0-9][0-9][0-9][0-9]"),
            key=lambda x: int(x.suffix[1:]),
        )
        if not tiles:
            raise FileNotFoundError(f"No restart tiles found for {restart}")

        return tiles[0]
