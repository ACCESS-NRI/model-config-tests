"""Specific Mom5 postprocessing"""

import re
from collections import defaultdict
from pathlib import Path

FINAL_ABSOLUTE_NORM = "Final Absolute Norm"


def um7_extract_norms(output_filename: Path) -> dict[str, list[any]]:
    """
    Given an atm.fort6.pe0 log file, extract the solver statistics generated
    by the UM7 model.

    UM7 writes the 'Final Absolute Norm' during each timestep. This statistic
    from the UM solver is sensitive to the atmosphere state, and will capture
    simulation divergence. For atmosphere only runs, the 'Final Absolute Norm'
    from the last timestep can be used in place of the MOM5 checksums.
    """
    # Regex pattern for final absolute norms in the `atm.fort6.pe0` file
    # Examples:
    # Final Absolute Norm :   9.735899063190541E-003
    pattern = rf"\s*{FINAL_ABSOLUTE_NORM}\s+:\s+\d+\.?(\d*E?-?\d*)"

    # checksums outputted in form:
    # {
    #   "Final Absolute Norm": ["9.735899063190541E-003"],
    # }

    output_norms: dict[str, list[any]] = defaultdict(list)

    with open(output_filename) as f:
        for line in f:
            # Check for checksum pattern match
            match = re.match(pattern, line)
            if match:
                absolute_norm = match.group(1).strip()

        # Save the absolute norm from the last timestep
        last_ts_final_absolute_norm = absolute_norm

        output_norms[FINAL_ABSOLUTE_NORM].append(last_ts_final_absolute_norm)

    return output_norms
