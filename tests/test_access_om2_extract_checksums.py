import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from model_config_tests.models import AccessOm2
from model_config_tests.models.accessom2 import SUPPORTED_SCHEMA_VERSIONS


@pytest.mark.parametrize("version", SUPPORTED_SCHEMA_VERSIONS)
def test_extract_checksums(version):
    # Mock ExpTestHelper
    mock_experiment = Mock()
    mock_experiment.output000 = Path("tests/resources")
    mock_experiment.control_path = Path("tests/tmp")

    model = AccessOm2(mock_experiment)

    checksums = model.extract_checksums(schema_version=version)

    # Assert version is set as expected
    assert checksums["schema_version"] == version

    # Check the entire checksum file is expected
    with open("tests/resources/access-om2-checksums-1-0-0.json") as file:
        expected_checksums = json.load(file)

    assert checksums == expected_checksums

    # Validate checksum file with schema
    # schema = get_schema_from_url(expected_checksums["schema"])

    # Validate checksums against schema
    # jsonschema.validate(instance=checksums, schema=schema)


def get_schema_from_url(url):
    """Retrieve schema from github"""
    response = requests.get(url)
    assert response.status_code == 200
    return response.json()