from pathlib import Path

import pytest
import yaml

from model_config_tests.exp_test_helper import (
    ExpTestHelper,
    parse_exit_status_from_file,
    parse_gadi_pbs_ids,
    parse_pbs_submitted_jobs,
    parse_run_id,
    wait_for_payu_jobs,
)
from tests.common import RESOURCES_DIR

LOG_DIR = RESOURCES_DIR / "experiment-logs"


@pytest.fixture
def experiment(tmpdir):
    # Create control and lab directories
    control_path = tmpdir / "control"
    lab_path = tmpdir / "lab"
    control_path.mkdir()
    lab_path.mkdir()

    # Make a dummy config file
    config = {"model": "access-om2"}
    with open(control_path / "config.yaml", "w") as f:
        yaml.dump(config, f)

    exp = ExpTestHelper(control_path=control_path, lab_path=lab_path)

    assert exp.exp_name == "control"
    assert exp.control_path == control_path
    assert exp.lab_path == lab_path
    assert exp.config_path == control_path / "config.yaml"
    assert exp.archive_path == lab_path / "archive" / "control"
    assert exp.work_path == lab_path / "work" / "control"
    assert exp.output000 == exp.archive_path / "output000"
    assert exp.output001 == exp.archive_path / "output001"
    assert exp.restart000 == exp.archive_path / "restart000"
    assert exp.restart001 == exp.archive_path / "restart001"
    assert not exp.disable_payu_run
    assert exp.run_id is None
    assert exp.config == {}
    assert exp.model_name == "access-om2"

    return exp


TEST_RUN_STDOUT = "137650670.gadi-pbs\nLoading input manifest: manifests/input.yaml\nLoading restart manifest: manifests/restart.yaml\nLoading exe manifest: manifests/exe.yaml\npayu: Found modules in /opt/Modules/v4.3.0\nqsub -q express -- /path/to/env/bin/python /path/to/env/bin/payu-run\n"


def test_parse_run_id():
    run_id = parse_run_id(TEST_RUN_STDOUT)
    assert run_id == "137650670.gadi-pbs"


@pytest.mark.parametrize(
    "stdout_filename, expected_ids",
    [
        ("pre-industrial.o137768371", ["137776067.gadi-pbs", "137776068.gadi-pbs"]),
        ("pre-industrial.o137776068", ["137777140.gadi-pbs"]),
        ("pre-industria_c.o137776067", []),
    ],
)
def test_parse_gadi_pbs_ids(stdout_filename, expected_ids):
    with open(LOG_DIR / stdout_filename) as f:
        stdout = f.read()
    assert parse_gadi_pbs_ids(stdout) == expected_ids


@pytest.mark.parametrize(
    "stdout_filename, expected_job_id, expected_collate_id",
    [
        (
            "pre-industrial.o137768371",
            "137776068.gadi-pbs",
            "137776067.gadi-pbs",
        ),
        ("pre-industrial.o137776068", None, "137777140.gadi-pbs"),
        ("pre-industria_c.o137776067", None, None),
    ],
)
def test_parse_pbs_submitted_jobs(
    stdout_filename, expected_job_id, expected_collate_id
):
    with open(LOG_DIR / stdout_filename) as f:
        stdout = f.read()
    run_id, collate_id = parse_pbs_submitted_jobs(stdout)
    assert run_id == expected_job_id
    assert collate_id == expected_collate_id


@pytest.mark.parametrize(
    "stdout_filename, expected_exit_status",
    [
        ("pre-industrial.o137768371", 0),
        ("pre-industrial.o137776068", 0),
        ("pre-industria_c.o137776067", 0),
        ("example_failed_job.o1234", 1),
    ],
)
def test_parse_exit_status_from_file(stdout_filename, expected_exit_status):
    with open(LOG_DIR / stdout_filename) as f:
        stdout = f.read()
    assert parse_exit_status_from_file(stdout) == expected_exit_status


def mock_wait_for_qsub(job_id):
    """
    Mock function to simulate waiting for a qsub job to finish.
    """
    return None


@pytest.mark.parametrize(
    "job_id, expected_output_filenames",
    [
        # Test two sequential payu run cycles
        (
            "137768371.gadi-pbs",
            [
                "pre-industrial.o137768371",
                "pre-industrial.e137768371",
                "pre-industria_c.o137776067",
                "pre-industria_c.e137776067",
                "pre-industrial.o137776068",
                "pre-industrial.e137776068",
                "pre-industria_c.o137777140",
                "pre-industria_c.e137777140",
            ],
        ),
        # Test with job_id of the second payu run
        (
            "137776068.gadi-pbs",
            [
                "pre-industrial.o137776068",
                "pre-industrial.e137776068",
                "pre-industria_c.o137777140",
                "pre-industria_c.e137777140",
            ],
        ),
    ],
)
def test_wait_for_payu_jobs(job_id, expected_output_filenames):
    mock_wait_for_qsub_func = mock_wait_for_qsub
    control_path = LOG_DIR
    output_files = wait_for_payu_jobs(control_path, job_id, mock_wait_for_qsub_func)
    output_filenames = [Path(filepath).name for filepath in output_files]
    assert output_filenames == expected_output_filenames
