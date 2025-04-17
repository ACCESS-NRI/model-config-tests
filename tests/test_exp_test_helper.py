import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

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
def exp(tmp_path):
    # Create control and lab directories
    control_path = tmp_path / "control"
    lab_path = tmp_path / "lab"
    control_path.mkdir()
    lab_path.mkdir()

    # Make a dummy config file for access-om2 model
    config = {"model": "access-om2"}
    with open(control_path / "config.yaml", "w") as f:
        yaml.dump(config, f)

    experiment = ExpTestHelper(control_path=control_path, lab_path=lab_path)
    return experiment


def test_experiment_init(exp, tmp_path):
    assert exp.exp_name == "control"
    assert exp.control_path == tmp_path / "control"
    assert exp.lab_path == tmp_path / "lab"
    assert exp.config_path == tmp_path / "control" / "config.yaml"
    assert exp.archive_path == tmp_path / "lab" / "archive" / "control"
    assert exp.work_path == tmp_path / "lab" / "work" / "control"
    assert exp.output000 == exp.archive_path / "output000"
    assert exp.output001 == exp.archive_path / "output001"
    assert exp.restart000 == exp.archive_path / "restart000"
    assert exp.restart001 == exp.archive_path / "restart001"
    assert not exp.disable_payu_run
    assert exp.run_id is None
    assert exp.config == {"model": "access-om2"}
    assert exp.model_name == "access-om2"


def test_experiment_setup_for_test_run(exp, tmp_path):
    exp.setup_for_test_run()
    with open(exp.control_path / "config.yaml") as f:
        config = yaml.safe_load(f)

    expected_config = {
        "model": "access-om2",
        "runlog": False,
        "metadata": {"enable": False},
        "experiment": "control",
        "laboratory": str(tmp_path / "lab"),
        "collate": {"enable": False},
        "sync": {"enable": False},
    }

    assert config == expected_config


def test_experiment_setup_for_test_run_remove_postprocessing(exp, tmp_path):
    postprocessing_config = {
        "model": "access-om2",
        "collate": {"restart": True, "enable": True},
        "sync": {"enable": True},
        "postscript": "some_postscript.sh",
        "userscripts": {
            "setup": "some_setup.sh",
            "archive": "some_archive.sh",
        },
    }
    with open(exp.control_path / "config.yaml", "w") as f:
        yaml.dump(postprocessing_config, f)

    exp.setup_for_test_run()
    with open(exp.control_path / "config.yaml") as f:
        config = yaml.safe_load(f)

    expected_config = expected_config = {
        "model": "access-om2",
        "runlog": False,
        "metadata": {"enable": False},
        "experiment": "control",
        "laboratory": str(tmp_path / "lab"),
        "collate": {"enable": False},
        "sync": {"enable": False},
        "userscripts": {
            "setup": "some_setup.sh",
        },
    }

    assert config == expected_config


@patch("subprocess.run")
def test_experiment_submit_payu_run(mock_run, exp):
    mock_run.return_value.stdout = "1234567.gadi-pbs\nsome other output"

    current_working_dir = Path.cwd()
    exp.submit_payu_run()

    lab_path = str(exp.lab_path)

    assert mock_run.call_count == 3
    # Check prior calls to setup and sweep
    assert mock_run.call_args_list[0][0][0] == ["payu", "setup", "--lab", lab_path]
    assert mock_run.call_args_list[1][0][0] == ["payu", "sweep", "--lab", lab_path]
    # Latest call
    assert mock_run.call_args[0][0] == ["payu", "run", "--lab", lab_path]

    assert exp.run_id == "1234567.gadi-pbs"

    # Check that the working directory is restored
    assert current_working_dir == Path.cwd()


@patch("subprocess.run")
def test_experiment_submit_payu_run_n_runs(mock_run, exp):
    """Test --n-runs is added to the payu run command"""
    mock_run.return_value.stdout = "1234567.gadi-pbs\nsome other output"

    exp.submit_payu_run(n_runs=2)

    lab_path = str(exp.lab_path)
    expected_run_args = ["payu", "run", "--lab", lab_path, "--nruns", "2"]
    # Payu run is the latest subprocess call
    assert mock_run.call_args[0][0] == expected_run_args


@patch("subprocess.run")
def test_experiment_submit_payu_run_disabled(mock_run, exp):
    """Payu run is not called when disabled field is set to True"""
    mock_run.return_value.stdout = "1234567.gadi-pbs\nsome other output"

    exp.disable_payu_run = True

    job_id = exp.submit_payu_run()

    assert not mock_run.called
    assert job_id is None


@patch("subprocess.run")
def test_experiment_submit_payu_run_error(mock_run, exp):
    """Test that an error is raised when any payu command fails"""
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd="payu setup", output="Some error"
    )
    mock_run.return_value.stdout = "Some error"

    with pytest.raises(RuntimeError, match="Failed to submit payu run.*"):
        exp.submit_payu_run()

    assert exp.run_id is None


TEST_RUN_STDOUT = """137650670.gadi-pbs
Loading input manifest: manifests/input.yaml
Loading restart manifest: manifests/restart.yaml
Loading exe manifest: manifests/exe.yaml
payu: Found modules in /opt/Modules/v4.3.0
qsub -q express -- /path/to/env/bin/python /path/to/env/bin/payu-run
"""


def test_parse_run_id():
    run_id = parse_run_id(TEST_RUN_STDOUT)
    assert run_id == "137650670.gadi-pbs"


@pytest.mark.parametrize(
    "stdout_filename, expected_ids",
    [
        ("pre-industrial.o137768371", ["137776068.gadi-pbs"]),
        ("pre-industrial.o137776068", []),
    ],
)
def test_parse_gadi_pbs_ids(stdout_filename, expected_ids):
    with open(LOG_DIR / stdout_filename) as f:
        stdout = f.read()
    assert parse_gadi_pbs_ids(stdout) == expected_ids


@pytest.mark.parametrize(
    "stdout_filename, expected_job_id",
    [
        ("pre-industrial.o137768371", "137776068.gadi-pbs"),
        ("pre-industrial.o137776068", None),
    ],
)
def test_parse_pbs_submitted_jobs(stdout_filename, expected_job_id):
    with open(LOG_DIR / stdout_filename) as f:
        stdout = f.read()
    run_id = parse_pbs_submitted_jobs(stdout)
    assert run_id == expected_job_id


@pytest.mark.parametrize(
    "stdout",
    [
        ("qsub -q normal ... - path/to/env/bin/python /path/to/env/bin/payu-run\n"),
        (
            "some test output\n"
            "qsub -q normal ... - path/to/env/bin/python /path/to/env/bin/payu-run\n"
            "exit status: 0"
        ),
    ],
)
def test_parse_pbs_submitted_jobs_no_job_id_error(stdout):
    """
    Test that parse_pbs_submitted_jobs raise an error when there's
    no job_ids for submitted run jobs in the stdout"""
    expected_error = "No job ID found in stdout file for subsequent payu run job"
    with pytest.raises(RuntimeError, match=expected_error):
        parse_pbs_submitted_jobs(stdout)


@pytest.mark.parametrize(
    "stdout, expected_run_id",
    [
        (
            "123456.gadi-pbs\n"
            "qsub -q normal ... - path/to/env/bin/python /path/to/env/bin/payu-run\n"
            "654321.gadi-pbs",
            "654321.gadi-pbs",
        ),
        (
            "qsub -q normal ... - path/to/env/bin/python /path/to/env/bin/payu-run\n"
            "123456.gadi-pbs\n654321.gadi-pbs\n67890.gadi-pbs\n",
            "67890.gadi-pbs",
        ),
    ],
)
def test_parse_pbs_submitted_jobs_more_job_ids(stdout, expected_run_id):
    """
    When there are more job IDs the payu run jobs,
    raise a warning - maybe the setup/run userscripts submitted a PBS job?
    """
    expected_error_msg = r"Found more than 1 job IDs in stdout file .*"
    with pytest.warns(UserWarning, match=expected_error_msg):
        run_id = parse_pbs_submitted_jobs(stdout)
    assert run_id == expected_run_id


@pytest.mark.parametrize(
    "stdout_filename, expected_exit_status",
    [
        ("pre-industrial.o137768371", 0),
        ("pre-industrial.o137776068", 0),
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
                "pre-industrial.o137776068",
                "pre-industrial.e137776068",
            ],
        ),
        # Test with job_id of the second payu run
        (
            "137776068.gadi-pbs",
            [
                "pre-industrial.o137776068",
                "pre-industrial.e137776068",
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


def test_read_job_output_file_no_stdout_files(tmp_path):
    """Test error raised when there is no stdout files."""
    job_id = "1234.gadi-pbs"
    expected_msg = r"Expected 1 stdout file for job ID 1234, but found 0.*"
    with pytest.raises(RuntimeError, match=expected_msg):
        wait_for_payu_jobs(tmp_path, job_id, mock_wait_for_qsub)


def test_read_job_output_file_multiple_stdout_files(tmp_path):
    """Test error raised when there is multiple stdout files."""
    job_id = "1234.gadi-pbs"
    # Create multiple stdout files with the same job ID
    stdout_file_1 = tmp_path / "example_job.o1234"
    stdout_file_1.write_text("Test stdout file 1", encoding="utf-8")
    stdout_file_2 = tmp_path / "example_job2.o1234"
    stdout_file_2.write_text("Test stdout file 2", encoding="utf-8")
    expected_msg = r"Expected 1 stdout file for job ID 1234, but found 2.*"
    with pytest.raises(RuntimeError, match=expected_msg):
        wait_for_payu_jobs(tmp_path, job_id, mock_wait_for_qsub)


def test_wait_for_qsub_job_exited_with_error(tmp_path):
    """
    Test that the wait_for_qsub function raises an exception when the job exits with an error.
    """
    failed_job_id = "1234.gadi-pbs"
    failed_job_stdout = "example_failed_job.o1234"
    # Copy failed job stdout file to the tmp directory
    shutil.copy(LOG_DIR / failed_job_stdout, tmp_path)
    # Create an stderr file
    stderr_file = tmp_path / "example_failed_job.e1234"
    stderr_file.write_text("Test stderr file", encoding="utf-8")

    expected_msg = "Payu run job failed with exit status 1"
    with pytest.raises(RuntimeError, match=expected_msg):
        wait_for_payu_jobs(tmp_path, failed_job_id, mock_wait_for_qsub)


def test_experiment_wait_for_payu_run(exp, tmp_path):
    """
    Test that wait_for_payu_run waits for the payu run to finish.
    """
    # Copy a example stdout/stderr files to the control path
    test_files = [
        "pre-industrial.o137776068",
        "pre-industrial.e137776068",
    ]
    for file in test_files:
        shutil.copy(LOG_DIR / file, tmp_path / "control")

    # Mock the wait_for_qsub function so it returns immediately
    with patch(
        "model_config_tests.exp_test_helper.wait_for_qsub"
    ) as mock_wait_for_qsub:
        mock_wait_for_qsub.return_value = None

        exp.run_id = "137776068.gadi-pbs"
        output_files = exp.wait_for_payu_run()

        output_filenames = [Path(filepath).name for filepath in output_files]
        assert output_filenames == test_files


def test_experiment_wait_for_payu_run_disabled(exp):
    """
    Test that wait_for_payu_run doesn't run when disabled field is set to True
    """
    exp.disable_payu_run = True

    # Mock the wait_for_qsub function so it returns immediately
    with patch(
        "model_config_tests.exp_test_helper.wait_for_qsub"
    ) as mock_wait_for_qsub:
        mock_wait_for_qsub.return_value = None

        exp.wait_for_payu_run("137776068.gadi-pbs")

        assert not mock_wait_for_qsub.called
