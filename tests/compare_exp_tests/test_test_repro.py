"""Integration style test for comparing multiple experiments"""

import shlex
import subprocess
import xml.etree.ElementTree as ET

import yaml


def setup_exp(tmp_path, exp_name, fake_output):
    """Create a temporary experiment directory for testing"""
    exp_path = tmp_path / exp_name
    exp_path.mkdir(parents=True)

    # Create an archive
    archive_path = tmp_path / "lab" / "archive" / exp_name
    output_path = archive_path / "output000"
    output_path.mkdir(parents=True)

    # Create control dir archive symlink
    (exp_path / "archive").symlink_to(archive_path, target_is_directory=True)

    # Create a config.yaml file
    config_file = exp_path / "config.yaml"
    with config_file.open("w") as f:
        yaml.dump(
            {"model": "access-om2"},
            f,
        )

    # Create a fake access-om2.out file
    (output_path / "access-om2.out").write_text(fake_output)

    return exp_path


def parse_pytest_xml(xml_file):
    """
    Parse pytest XML output to extract test names, and statuses.

    Parameters
    ----------
    xml_file : str
        Path to the pytest XML output file.

    Returns
    -------
    dict[str, str]
        Mapping of test names to test status (passed, failed, error, skipped).
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    test_results = {}
    for testcase in root.iter("testcase"):
        test_name = testcase.attrib.get("name")
        status = "passed"

        # Check for failure, error, or skipped status
        if testcase.find("failure") is not None:
            status = "failed"
        elif testcase.find("error") is not None:
            status = "error"
        elif testcase.find("skipped") is not None:
            status = "skipped"

        test_results[test_name] = status

    return test_results


def test_test_pairwise_repro(tmp_path):
    """Test for pairwise reproducibility of 3 experiments"""
    # Create two temporary experiment directories
    setup_exp(tmp_path, "exp1", "[chksum] test_checksum               0")
    setup_exp(tmp_path, "exp2", "[chksum] test_checksum               0")
    setup_exp(tmp_path, "exp3", "[chksum] test_checksum               1")

    test_cmd = (
        'compare-exp-tests -k test_pairwise_repro --dirs "exp1 exp2 exp3" -vvv'
        f" --junit-xml {tmp_path}/test_results.xml"
    )

    # Run test
    subprocess.run(
        shlex.split(test_cmd),
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )

    # To print out test results, uncomment the following line and assign
    # the above subprocess to a result variable
    # print(f"Test stdout: {result.stdout}\nTest stderr: {result.stderr}")

    # Parse xml output file from the tests to check generated test results
    test_results = parse_pytest_xml(tmp_path / "test_results.xml")

    assert len(test_results) == 3
    assert "test_pairwise_repro[exp1 vs exp2]" in test_results
    assert test_results["test_pairwise_repro[exp1 vs exp2]"] == "passed"

    assert "test_pairwise_repro[exp1 vs exp3]" in test_results
    assert test_results["test_pairwise_repro[exp1 vs exp3]"] == "failed"

    assert "test_pairwise_repro[exp2 vs exp3]" in test_results
    assert test_results["test_pairwise_repro[exp2 vs exp3]"] == "failed"
