from model_config_tests.models.accessesm1p5 import AccessEsm1p5
from model_config_tests.models.accessesm1p6 import AccessEsm1p6
from model_config_tests.models.accessom2 import AccessOm2
from model_config_tests.models.accessom3 import AccessOm3

# Mapping payu configuration model name to class
index = {
    "access-om2": AccessOm2,
    "access-om3": AccessOm3,
    "access": AccessEsm1p5,
    "access-esm1.6": AccessEsm1p6,
}
