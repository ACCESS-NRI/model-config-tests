"""Generic Model class"""

from pathlib import Path

SCHEMA_VERSION_1_0_0 = "1-0-0"
SCHEMA_1_0_0_URL = "https://raw.githubusercontent.com/ACCESS-NRI/schema/7666d95967de4dfd19b0d271f167fdcfd3f46962/au.org.access-nri/model/reproducibility/checksums/1-0-0.json"
SCHEMA_VERSION_TO_URL = {SCHEMA_VERSION_1_0_0: SCHEMA_1_0_0_URL}
DEFAULT_SCHEMA_VERSION = "1-0-0"


class Model:
    def __init__(self, experiment):
        self.experiment = experiment

        self.default_schema_version = DEFAULT_SCHEMA_VERSION
        self.schema_version_to_url = SCHEMA_VERSION_TO_URL

    def extract_checksums(self, output_directory: Path, schema_version: str):
        """Extract checksums from output directory"""
        raise NotImplementedError

    def set_model_runtime(self, years: int = 0, months: int = 0, seconds: int = 10800):
        """Configure model runtime"""
        raise NotImplementedError

    def output_exists(self):
        """Check for existing output files"""
        raise NotImplementedError

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
                if (
                    field not in short_run_checksums
                    or checksum not in short_run_checksums[field]
                ):
                    print(f"Unequal checksum: {field}: {checksum}")
                    matching_checksums = False

        return matching_checksums
