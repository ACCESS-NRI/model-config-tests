import shutil
from unittest.mock import Mock

import f90nml
import pytest
import yaml
from payu.models.cesm_cmeps import Runconfig

from model_config_tests.models import index as model_index
from model_config_tests.models.accessesm1p5 import (
    DEFAULT_RUNTIME_SECONDS as ESM_RUNTIME,
)
from model_config_tests.models.accessom2 import DEFAULT_RUNTIME_SECONDS as OM2_RUNTIME
from model_config_tests.models.accessom3 import DEFAULT_RUNTIME_SECONDS as OM3_RUNTIME
from model_config_tests.util import DAY_IN_SECONDS
from tests.common import RESOURCES_DIR


@pytest.fixture
def model_factory(isolated_config, tmp_path):
    """Factory fixture to create model instances with an isolated configuration."""

    def factory(model_name, config_name, output):
        resources_dir = RESOURCES_DIR / model_name

        # Mock ExpTestHelper
        mock_experiment = Mock()
        mock_experiment.output000 = resources_dir / output
        mock_experiment.restart000 = resources_dir / "restart000"

        mock_experiment.control_path = tmp_path / "control"
        _, config_dir = isolated_config(config_name)
        shutil.move(config_dir, mock_experiment.control_path)

        mock_experiment.config_path = tmp_path / "control" / "config.yaml"
        with open(mock_experiment.config_path) as f:
            mock_experiment.config = yaml.safe_load(f)

        # Create Model instance
        ModelType = model_index[model_name]
        return ModelType(mock_experiment)

    return factory


@pytest.mark.parametrize(
    "expected_runtime, default",
    [
        ({"years": 1, "months": 2, "days": 3, "seconds": 0}, False),
        ({"years": 0, "months": 1, "days": 5, "seconds": 0}, False),
        (
            {
                "years": 0,
                "months": 0,
                "days": ESM_RUNTIME / DAY_IN_SECONDS,
                "seconds": 0,
            },
            True,
        ),
    ],
)
def test_set_model_runtime_esm1p5(model_factory, expected_runtime, default):
    """Test that ACCESS-ESM1p5 set_model_runtime sets the correct runtime in config.yaml"""
    # Set up ACCESS-ESM1.5 model
    model = model_factory(
        model_name="access", config_name="esm1p5-prein", output="output000"
    )

    # Call set_model_runtime with the expected runtime
    if default:
        # If default is True, we expect the default runtime to be set
        model.set_model_runtime()
    else:
        model.set_model_runtime(
            years=expected_runtime["years"],
            months=expected_runtime["months"],
            seconds=expected_runtime["days"] * DAY_IN_SECONDS,
        )

    # Check that the config.yaml file has been updated with the expected runtime
    with open(model.experiment.config_path) as f:
        updated_config = yaml.safe_load(f)
    assert updated_config["calendar"]["runtime"] == expected_runtime

    # Check that atmosphere has 48 timesteps per day, hard-coded the path to check if the path changes
    atmosphere_config = model.experiment.control_path / "atmosphere" / "namelists"
    with open(atmosphere_config) as f:
        atmosphere_nml = f90nml.read(f)
    assert atmosphere_nml["NLSTCGEN"]["DUMPFREQim"] == [48, 0, 0, 0]

    # Check that ice restarts at daily frequency, hard-coded the path to check if the path changes
    ice_config = model.experiment.control_path / "ice" / "cice_in.nml"
    with open(ice_config) as f:
        ice_nml = f90nml.read(f)
    assert ice_nml["setup_nml"]["dumpfreq"] == "d"


@pytest.mark.parametrize(
    "expected_runtime, raise_error, default",
    [
        # two of years, months, seconds need to be zero
        ([0, 0, 5 * DAY_IN_SECONDS], False, False),  # 5 days in seconds
        ([0, 1, 0], False, False),  # 1 month
        (
            [0, 1, 5 * DAY_IN_SECONDS],
            True,
            False,
        ),  # 1 month and 5 days in seconds (should raise error)
        ([0, 0, OM2_RUNTIME], False, True),  # Default runtime in seconds
    ],
)
def test_set_model_runtime_om2(model_factory, expected_runtime, raise_error, default):
    """Test that ACCESS-OM2 set_model_runtime sets the correct runtime in config.yaml"""
    # Set up ACCESS-OM2 model
    model = model_factory(
        model_name="access-om2", config_name="om2-1deg", output="output000"
    )

    # Call set_model_runtime with the expected runtime
    if raise_error:
        with pytest.raises(
            NotImplementedError,
            match="Cannot specify runtime in seconds and years and months at the same time.",
        ):
            model.set_model_runtime(*expected_runtime)
    else:
        if default:
            model.set_model_runtime()
        else:
            model.set_model_runtime(*expected_runtime)

        # Check that the accessom2_config.yaml file has been updated with the expected runtime
        with open(model.accessom2_config) as f:
            nml = f90nml.read(f)
        assert nml["date_manager_nml"]["restart_period"] == expected_runtime


@pytest.mark.parametrize(
    "expected_runtime, expected_freq, expected_n, raise_error, default",
    [
        ([0, 0, 10 * 3600], "nseconds", "36000", False, False),  # 10 hours in seconds
        ([0, 1, 0], "nmonths", "1", False, False),  # 1 month
        ([1, 0, 0], "nmonths", "12", False, False),  # 1 year
        (
            [0, 1, 10],
            None,
            None,
            True,
            False,
        ),  # Error: Cannot specify runtime in seconds and year/months at the same time
        (
            [0, 0, OM3_RUNTIME],
            "nseconds",
            f"{OM3_RUNTIME}",
            False,
            True,
        ),  # Default runtime in seconds
    ],
)
def test_set_model_runtime_om3(
    model_factory, expected_runtime, expected_freq, expected_n, raise_error, default
):
    """Test that ACCESS-OM3 set_model_runtime sets the correct runtime in config.yaml"""
    # Set up ACCESS-OM3 model
    model = model_factory(
        model_name="access-om3", config_name="om3-100km", output="output000"
    )

    if raise_error:
        with pytest.raises(
            NotImplementedError,
            match="Cannot specify runtime in seconds and year/months at the same time",
        ):
            model.set_model_runtime(*expected_runtime)
    else:
        # Call set_model_runtime with the expected runtime
        if default:
            model.set_model_runtime()
        else:
            model.set_model_runtime(*expected_runtime)

        # Check that the accessom3_config.yaml file has been updated with the expected runtime
        runconfig = Runconfig(model.runconfig)
        assert runconfig.get("CLOCK_attributes", "restart_n") == expected_n
        assert runconfig.get("CLOCK_attributes", "restart_option") == expected_freq
        assert runconfig.get("CLOCK_attributes", "stop_n") == expected_n
        assert runconfig.get("CLOCK_attributes", "stop_option") == expected_freq


def test_set_model_runtime_esm1p6(model_factory):
    """Test that ACCESS-ESM1.6 set_model_runtime updates the config.yaml correctly"""
    # TODO: Update with release esm1.6 configurations when available
    pass
