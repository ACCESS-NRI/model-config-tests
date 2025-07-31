import pytest
from parse_junit_xml import format_test_name_results, parse_pytest_junit_xml

# Example XML content
TEST_REPRO_HISTORICAL_XML = """<?xml version="1.0" encoding="utf-8"?>
<testsuites name="pytest tests">
    <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="1" time="262.668" timestamp="2025-07-28T12:05:58.091954+10:00" hostname="gadi-login-03.gadi.nci.org.au">
        <testcase classname="src.model_config_tests.config_tests.test_bit_reproducibility.TestBitReproducibility" name="test_repro_historical" time="260.864" />
    </testsuite>
</testsuites>
"""

TEST_REPRO_XML_WITH_ERRORS = """<?xml version="1.0" encoding="utf-8"?>
<testsuites name="pytest tests">
    <testsuite name="pytest" errors="2" failures="0" skipped="0" tests="3" time="180.228" timestamp="2025-07-30T17:29:58.776839+10:00" hostname="gadi-login-09.gadi.nci.org.au">
        <testcase classname="src.model_config_tests.config_tests.test_bit_reproducibility.TestBitReproducibility" name="test_repro_historical" time="176.479" />
        <testcase classname="src.model_config_tests.config_tests.test_bit_reproducibility.TestBitReproducibility" name="test_repro_determinism" time="0.000"><error message="failed on setup with &quot;RuntimeError: There was an error running experiment exp_1d_runtime...."></error></testcase>
        <testcase classname="src.model_config_tests.config_tests.test_bit_reproducibility.TestBitReproducibility" name="test_repro_restart" time="0.000"><error message="failed on setup with &quot;RuntimeError: There was an error running experiment exp_1d_runtime...."></error></testcase>
    </testsuite>
</testsuites>"""

TEST_REPRO_XML_WITH_FAILURES = """<?xml version="1.0" encoding="utf-8"?>
<testsuites name="pytest tests">
    <testsuite name="pytest" errors="0" failures="1" skipped="0" tests="2" time="336.880" timestamp="2025-07-31T09:40:22.320395+10:00" hostname="gadi-login-03.gadi.nci.org.au">
        <testcase classname="src.model_config_tests.config_tests.test_bit_reproducibility.TestBitReproducibility" name="test_repro_historical" time="335.281" />
        <testcase classname="src.model_config_tests.config_tests.test_bit_reproducibility.TestBitReproducibility" name="test_repro_determinism" time="0.001"><failure message="AssertionError: some example repro test failed">python code snippet</failure></testcase>
    </testsuite>
</testsuites>
"""

TEST_EXAMPLE_XML_WITH_SKIPPED = """<?xml version="1.0" encoding="utf-8"?>
<testsuites name="pytest tests">
    <testsuite name="pytest" errors="0" failures="0" skipped="1" tests="1" time="0.001" timestamp="2025-07-31T09:40:22.320395+10:00">
        <testcase classname="TestExample" name="test_example_skipped" time="0.000"><skipped message="This test is skipped"></skipped></testcase>
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
        (
            TEST_REPRO_XML_WITH_ERRORS,
            {
                "passed": ["test_repro_historical"],
                "errors": ["test_repro_determinism", "test_repro_restart"],
                "failures": [],
                "skipped": [],
            },
        ),
        (
            TEST_REPRO_XML_WITH_FAILURES,
            {
                "passed": ["test_repro_historical"],
                "errors": [],
                "failures": ["test_repro_determinism"],
                "skipped": [],
            },
        ),
        (
            TEST_EXAMPLE_XML_WITH_SKIPPED,
            {
                "passed": [],
                "errors": [],
                "failures": [],
                "skipped": ["test_example_skipped"],
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
