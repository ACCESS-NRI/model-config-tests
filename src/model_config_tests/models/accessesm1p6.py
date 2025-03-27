"""Specific ACCESS-ESM1.6 Model setup and post-processing"""

from model_config_tests.models.accessesm1p5 import AccessEsm1p5


class AccessEsm1p6(AccessEsm1p5):
    def __init__(self, experiment):
        super().__init__(experiment)

        self.set_output_files(model_std_file="access-esm1.6.out")
