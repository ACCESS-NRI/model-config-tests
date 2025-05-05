import json
from pathlib import Path
from unittest.mock import Mock

import jsonschema
import pytest
import requests
import yaml

from model_config_tests.models import index as model_index
from tests.common import RESOURCES_DIR

MODEL_NAMES = model_index.keys()


# TODO: Update with release esm1.6 configurations when available
# TODO: Is there a way to test checksum extraction for amip configurations?
@pytest.mark.parametrize(
    "model_name, configuration, output, expected_checksum",
    [
        ("access", "release-preindustrial+concentrations", "output000", "checksums"),
        ("access-esm1.6", "dev-amip", "amip-output000", "amip-checksums"),
        ("access-esm1.6", "dev-preindustrial+concentrations", "output000", "checksums"),
        ("access-om2", None, "output000", "checksums"),
        ("access-om3", None, "output000", "checksums"),
    ],
)
def test_extract_checksums(model_name, configuration, output, expected_checksum):
    resources_dir = RESOURCES_DIR / model_name

    # Mock ExpTestHelper
    mock_experiment = Mock()
    mock_experiment.output000 = resources_dir / output
    mock_experiment.restart000 = resources_dir / "restart000"
    mock_experiment.control_path = Path("test/tmp")
    if configuration:
        config_path = resources_dir / "configurations" / configuration / "config.yaml"
        with open(config_path) as f:
            mock_experiment.config = yaml.safe_load(f)

    # Create Model instance
    ModelType = model_index[model_name]
    model = ModelType(mock_experiment)

    # Test extract checksums for each schema version
    for version, url in model.schema_version_to_url.items():
        checksums = model.extract_checksums(schema_version=version)

        # Assert version is set as expected
        assert checksums["schema_version"] == version

        # Check the entire checksum file is expected
        checksum_file = resources_dir / expected_checksum / f"{version}.json"
        with open(checksum_file) as file:
            expected_checksums = json.load(file)

        assert checksums == expected_checksums

        # Validate checksum file with schema
        schema = get_schema_from_url(url)

        # Validate checksums against schema
        jsonschema.validate(instance=checksums, schema=schema)


# TODO: Update with release esm1.6 configurations when available
@pytest.mark.parametrize(
    "model_name, configuration",
    [
        ("access", "release-preindustrial+concentrations"),
        ("access-om2", None),
        ("access-om3", None),
    ],
)
def test_extract_checksums_unsupported_version(model_name, configuration):
    resources_dir = RESOURCES_DIR / model_name

    # Mock ExpTestHelper
    mock_experiment = Mock()
    mock_experiment.output000 = resources_dir / "output000"
    mock_experiment.restart000 = resources_dir / "restart000"
    mock_experiment.control_path = Path("test/tmp")
    if configuration:
        config_path = resources_dir / "configurations" / configuration / "config.yaml"
        with open(config_path) as f:
            mock_experiment.config = yaml.safe_load(f)

    # Create Model instance
    ModelType = model_index[model_name]
    model = ModelType(mock_experiment)

    # Test NotImplementedError gets raised for unsupported versions
    with pytest.raises(NotImplementedError):
        model.extract_checksums(schema_version="test-version")


def get_schema_from_url(url):
    """Retrieve schema from GitHub"""
    response = requests.get(url)
    assert response.status_code == 200
    return response.json()
