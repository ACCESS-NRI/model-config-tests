import json
from unittest.mock import Mock, patch

import pytest

from model_config_tests.util import (
    JobInfoCache,
    extract_job_info,
    qstat_all_jobs,
    wait_for_qsub,
)

# Fake qstat data
TEST_QSTAT_JSON = {
    "timestamp": 1744267002,
    "pbs_version": "some_version",
    "Jobs": {
        "12345.gadi-pbs": {
            "Job_Name": "test_jobname",
            "resources_used": {
                "mem": "75520704kb",
                "walltime": "00:00:21",
            },
            "job_state": "F",
            "queue": "normal-exec",
            "Resource_List": {
                "mem": "1073741823996b",
                "walltime": "03:00:00",
            },
            "comment": "Job run",
            "Exit_status": 0,
            "some_other_info": "some_value",
        },
        "67890.gadi-pbs": {
            "Job_Name": "test_jobname",
            "job_state": "Q",
            "queue": "normal-exec",
            "Resource_List": {
                "jobfs": "629145600b",
                "mem": "1073741823996b",
            },
            "comment": "Not Running: Insufficient amount of resource: ncpus ",
            "project": "test_project",
            "some_other_info": "another_value",
        },
    },
}


@pytest.fixture
def job_info_cache():
    """Fixture to reset the cache after each test"""
    cache = JobInfoCache()
    yield cache
    cache.clear()


def test_qstat_all_jobs():
    """Test qstat query for all jobs"""
    example_output = json.dumps(TEST_QSTAT_JSON)
    with patch("subprocess.run") as mock_run:
        # Patch the subprocess.run stdout to return the example output
        example_result = Mock()
        example_result.stdout = example_output
        mock_run.return_value = example_result

        result = qstat_all_jobs()
        assert result == TEST_QSTAT_JSON
        mock_run.assert_called_once_with(
            ["qstat", "-x", "-f", "-F", "json"],
            capture_output=True,
            text=True,
            check=True,
        )


def test_extract_job_info():
    """Test extracting job info from qstat output"""
    job_info = extract_job_info(TEST_QSTAT_JSON)
    assert "12345.gadi-pbs" in job_info
    assert "67890.gadi-pbs" in job_info
    assert job_info["12345.gadi-pbs"]["job_state"] == "F"
    assert job_info["67890.gadi-pbs"]["job_state"] == "Q"


def test_wait_for_qsub_job_found_in_cache(job_info_cache):
    """Test wait_for_qsub when job is found in cache."""
    job_info_cache.set({"5678": {"job_state": "F"}})
    with (
        patch("model_config_tests.util.qstat_all_jobs") as mock_qstat_all_jobs,
        patch("time.sleep") as mock_sleep,
    ):
        mock_qstat_all_jobs.return_value = TEST_QSTAT_JSON
        result = wait_for_qsub("5678")
        mock_qstat_all_jobs.assert_not_called()
        mock_sleep.assert_not_called()

    assert result == {"job_state": "F"}


def test_wait_for_qsub_job_not_found(job_info_cache):
    """Test wait_for_qsub when job is not found in cache."""
    with (
        patch("model_config_tests.util.qstat_all_jobs") as mock_qstat_all_jobs,
        patch("time.sleep") as mock_sleep,
    ):
        mock_qstat_all_jobs.return_value = TEST_QSTAT_JSON

        with pytest.raises(RuntimeError, match="Job ID 9999 not found in qstat output"):
            wait_for_qsub("9999")

        mock_qstat_all_jobs.assert_called()
        mock_sleep.assert_called()


def test_wait_for_qsub_job_completes(job_info_cache):
    """Test wait_for_qsub when job completes after waiting."""
    with (
        patch("model_config_tests.util.qstat_all_jobs") as mock_qstat_all_jobs,
        patch("time.sleep") as mock_sleep,
    ):
        # Simulate job not found initially, then found and completed
        mock_qstat_all_jobs.side_effect = [
            {"Jobs": {"1234": {"job_state": "R"}}},  # First call
            {"Jobs": {"1234": {"job_state": "F"}}},  # Second call
        ]

        result = wait_for_qsub("1234")
        assert result["job_state"] == "F"

        mock_qstat_all_jobs.assert_called()
        mock_sleep.assert_called()
