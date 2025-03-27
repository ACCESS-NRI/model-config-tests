"""Specific ACCESS-ESM1.6 Model setup and post-processing"""

from pathlib import Path

from model_config_tests.models.accessesm1p5 import AccessEsm1p5


class AccessEsm1p6(AccessEsm1p5):
    def __init__(self, experiment):
        super().__init__(experiment)

        if "mom" in self.submodels:
            self.output_filename = "access-esm1.6.out"
        elif "um" in self.submodels:
            # UM output is stored in submodel ouptut sub-directory
            self.output_filename = Path(self.submodels["um"]) / "atm.fort6.pe0"

        self.output_file = self.output_0 / self.output_filename
