"""Specific Mom5 postprocessing"""

import re
from collections import defaultdict
from pathlib import Path


def mom5_extract_checksums(output_filename: Path) -> dict[str, list[any]]:
    """Given an <model>.out file, extract the checksums generated by the mom5 model"""
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

    return output_checksums