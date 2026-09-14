import json
import subprocess as sp
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from model_config_tests.util import (
    get_latest_run_info,
    payu_status_json,
    wait_for_run_job,
)

def generate_payu_status_output(
    run_number, exit_status=None, model_exit_status=None, update=False
):
    run_info = {
        "experiment_uuid": "test-uuid",
        "runs": {
            str(run_number): {
                "run": [
                    {
                        "job_id": f"17000{run_number}.gadi-pbs",
                        "stage": "queued",
                        "exit_status": exit_status,
                        "stdout_file": f"test-stdout.o17000{run_number}" if exit_status is not None else None,
                        "stderr_file": f"test-stderr.e17000{run_number}" if exit_status is not None else None,
                        "job_file": (
                            f"/scratch/tm70/tmp/test-model-repro/lab/"
                            f"archive/new_expt-exp_1d_runtime_repeat/"
                            f"payu_jobs/{run_number}/run/"
                            f"17000{run_number}.gadi-pbs.json"
                        ),
                        "start_time": None,
                        "depends_on": None,
                        "run_id": None,
                        "model_exit_status": model_exit_status,
                        "model_finish_time": "1951-07-01T00:00:00" if model_exit_status is not None else None,
                    }
                ]
            }
        },
    }

    output = json.dumps(run_info, indent=4)

    if update:
        output = (
            "payu: Found modules in /opt/Modules/v4.3.0\n"
            + output
        )
    return output, run_info


@pytest.fixture
def make_tmp_dirs(tmp_path):
    # Create control and lab directories
    control_path = tmp_path / "control"
    lab_path = tmp_path / "lab"
    control_path.mkdir()
    lab_path.mkdir()

    yield control_path, lab_path


@pytest.mark.parametrize(
    "update",
    [True, False],
)
def test_payu_status_json(make_tmp_dirs, update):
    """Test that payu_status_json parses payu status JSON output."""
    control_path, lab_path = make_tmp_dirs
    mock_status_output, mock_run_info = generate_payu_status_output(0, exit_status=0, model_exit_status=0, update=update)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = mock_status_output
        mock_run.return_value.returncode = 0

        status_data = payu_status_json(control_path, lab_path, run_number=0)

        assert status_data == mock_run_info


def test_payu_status_json_failure(make_tmp_dirs):
    """Test that payu_status_json raises RuntimeError when payu status failed to fetch."""
    control_path, lab_path = make_tmp_dirs

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "test-stdout"
        mock_run.return_value.returncode = 1

        with pytest.raises(RuntimeError, match="payu status command failed"):
            payu_status_json(control_path, lab_path, run_number=0)


def test_wait_for_run_job_succeed(make_tmp_dirs):
    """Test that wait_for_run_job returns run_info when exit_status and model_exit_status are both zero."""
    control_path, lab_path = make_tmp_dirs

    with patch("model_config_tests.util.payu_status_json") as mock_payu_status_json:
        # Simulate payu status output with exit_status=0 and model_exit_status=0
        _, mock_run_info = generate_payu_status_output(0, exit_status=0, model_exit_status=0, update=True)
        mock_payu_status_json.return_value = mock_run_info

        run_info = wait_for_run_job(control_path, lab_path, run_number=0)

        assert run_info == mock_run_info["runs"]["0"]["run"][-1]


@pytest.mark.parametrize(
    "exit_status, model_exit_status",
    [
        (1, 0),  # Non-zero exit_status
        (0, 1),  # Non-zero model_exit_status
        (1, 1),  # Both non-zero
    ],
)
def test_wait_for_run_job_fail_run(make_tmp_dirs, exit_status, model_exit_status):
    """Test that wait_for_run_job raise RuntimeError if exit_status or model_exit_status is not zero."""
    control_path, lab_path = make_tmp_dirs

    with patch("model_config_tests.util.payu_status_json") as mock_payu_status_json:
        # Simulate payu status output with exit_status=0 and model_exit_status=0
        _, mock_run_info = generate_payu_status_output(0, exit_status, model_exit_status, update=True)
        mock_payu_status_json.return_value = mock_run_info

        with pytest.raises(RuntimeError, match="Payu run job failed for run number 0"):
            wait_for_run_job(control_path, lab_path, run_number=0)


def test_wait_for_run_job_no_run_info(make_tmp_dirs):
    """Test that wait_for_run_job raises RuntimeError if no run job information is found."""
    control_path, lab_path = make_tmp_dirs

    with patch("model_config_tests.util.payu_status_json") as mock_payu_status_json:
        # Simulate payu status output with no run job information
        mock_payu_status_json.return_value = {"runs": {}}

        with pytest.raises(RuntimeError, match="No run job information found for run number 0"):
            wait_for_run_job(control_path, lab_path, run_number=0)


def test_get_latest_run_info():
    """Test that get_latest_run_info returns the latest run job information."""
    with patch("model_config_tests.util.payu_status_json") as mock_payu_status_json:
        # Simulate payu status output with multiple run jobs
        _, mock_run_info_0 = generate_payu_status_output(0, exit_status=0, model_exit_status=0, update=True)
        _, mock_run_info_1 = generate_payu_status_output(1, exit_status=0, model_exit_status=0, update=True)
        status_data = {
            "runs": {
                "0": mock_run_info_0["runs"]["0"],
                "1": mock_run_info_1["runs"]["1"],
            }
        }

        latest_run_number, latest_run_info = get_latest_run_info(status_data)

        assert latest_run_number == 1
        assert latest_run_info == mock_run_info_1["runs"]["1"]["run"][-1]