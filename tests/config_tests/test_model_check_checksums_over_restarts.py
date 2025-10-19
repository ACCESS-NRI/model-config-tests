import pytest

from model_config_tests.models import index as model_index


@pytest.mark.parametrize("model_name", ["access-om2", "access-om3"])
def test_check_checksums_over_restarts(model_name, capsys):
    model = model_index[model_name]

    checksum_1 = {
        "schema_version": "1.0.0",
        "output": {
            "field1": ["12345678"],
        },
    }

    checksum_2 = {
        "schema_version": "1.0.0",
        "output": {
            "field1": ["87654321"],
        },
    }

    matching_checksums = model.check_checksums_over_restarts(
        model,
        checksum_1,
        checksum_1,
        checksum_1,
    )

    assert matching_checksums is True

    matching_checksums = model.check_checksums_over_restarts(
        model,
        checksum_2,
        checksum_1,
        checksum_1,
    )
    captured = capsys.readouterr()

    assert matching_checksums is False
    assert captured.out == "Unequal checksum: field1: 87654321\n"


def test_check_checksums_over_restarts_om3_pmzeros():
    # Test that OM3 checksums differing by 8 in the first hex digit are considered equal
    model = model_index["access-om3"]

    checksum_1 = {
        "schema_version": "1.0.0",
        "output": {
            "field1": ["C92469973FB18B96"],
        },
    }

    checksum_2 = {
        "schema_version": "1.0.0",
        "output": {
            "field1": ["492469973FB18B96"],
        },
    }

    matching_checksums = model.check_checksums_over_restarts(
        model,
        checksum_1,
        checksum_2,
        checksum_2,
    )

    assert matching_checksums is True

    matching_checksums = model.check_checksums_over_restarts(
        model,
        checksum_2,
        checksum_1,
        checksum_1,
    )

    assert matching_checksums is True
