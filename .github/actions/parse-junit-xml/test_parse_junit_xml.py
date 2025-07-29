import pytest
from parse_junit_xml import format_test_name_results, parse_pytest_junit_xml

TEST_REPRO_HISTORICAL_XML = """<?xml version="1.0" encoding="utf-8"?>
<testsuites name="pytest tests">
    <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="1" time="262.668" timestamp="2025-07-28T12:05:58.091954+10:00" hostname="gadi-login-03.gadi.nci.org.au">
        <testcase classname="src.model_config_tests.config_tests.test_bit_reproducibility.TestBitReproducibility" name="test_repro_historical" time="260.864" />
    </testsuite>
</testsuites>
"""


@pytest.mark.parametrize(
    "xml_content, expected_result",
    [
        (
            TEST_REPRO_HISTORICAL_XML,
            {
                "passed": ["test_repro_historical"],
                "errors": [],
                "failures": [],
                "skipped": [],
            },
        ),
    ],
)
def test_parse_pytest_junit_xml(xml_content, expected_result, tmp_path):
    input_file = tmp_path / "test_report.xml"
    with open(input_file, "w") as f:
        f.write(xml_content)
    result = parse_pytest_junit_xml(input_file)
    assert result == expected_result


@pytest.mark.parametrize(
    "test_results, expected_summary",
    [
        (
            {
                "passed": ["test_repro_historical"],
                "errors": [],
                "failures": [],
                "skipped": [],
            },
            ":white_check_mark: `test_repro_historical`",
        ),
        (
            {
                "passed": [],
                "errors": ["test_error_case", "test_another_error_case"],
                "failures": ["test_failure_case"],
                "skipped": [],
            },
            ":fire: `test_error_case`\n:fire: `test_another_error_case`\n:x: `test_failure_case`",
        ),
        (
            {
                "passed": [],
                "errors": [],
                "failures": [],
                "skipped": ["test_skipped_case"],
            },
            "",
        ),
    ],
)
def test_format_test_name_results(test_results, expected_summary):
    summary = format_test_name_results(test_results)
    assert summary == expected_summary
