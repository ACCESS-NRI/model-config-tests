# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

import json
import subprocess as sp
import time

# Time related constants
MINUTE_IN_SECONDS = 60
HOUR_IN_SECONDS = MINUTE_IN_SECONDS * 60
DAY_IN_SECONDS = HOUR_IN_SECONDS * 24


class JobInfoCache:
    """Singleton class to store PBS job information"""

    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get(self):
        return self._cache

    def set(self, job_info):
        self._cache = job_info

    def clear(self):
        self._cache.clear()


def qstat_all_jobs() -> dict:
    """
    Query PBS scheduler for all job information (including queued and
    finished jobs)

    Returns
    -------
    dict
        A dictionary containing the qstat output in json format
    """
    try:
        qstat_out = sp.run(
            ["qstat", "-x", "-f", "-F", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
    except sp.CalledProcessError as e:
        raise RuntimeError(f"qstat command failed: {e}")

    return json.loads(qstat_out.stdout)


def extract_job_info(qstat_json: dict) -> dict:
    """
    Extract job information from qstat json output. Full output can be
    reasonably large, so only keeping some key fields (e.g. job_state)
    """
    if "Jobs" not in qstat_json or len(qstat_json["Jobs"]) == 0:
        raise RuntimeError("No jobs found in qstat output")

    jobs = qstat_json["Jobs"]
    job_info = {}
    for job_id, info in jobs.items():
        if "job_state" not in info:
            raise RuntimeError(
                f"job_state not found in qstat output for job ID: {job_id}"
            )
        job_info[job_id] = {
            "job_state": info["job_state"],
            "Exit_status": info.get("Exit_status", None),
            # "Resource_List": info.get("Resource_List", {}),
            # "resources_used": info.get("resources_used", {}),
        }
    return job_info


def wait_for_qsub(run_id) -> dict:
    """
    Wait for the qsub job to terminate.

    Parameters
    ----------
    run_id : str
        The job ID of the qsub job to wait for.

    Returns
    -------
    dict
        A dictionary containing partial job information
    """
    job_info_cache = JobInfoCache()

    # Check if the job is already in last qstat output and has completed
    job_info = job_info_cache.get()
    if run_id in job_info:
        if job_info[run_id]["job_state"] == "F":
            return job_info[run_id]

    # Wait for job
    while True:
        time.sleep(MINUTE_IN_SECONDS)
        # Query qstat for all jobs and save output to qstat_output_cache
        qstat_json = qstat_all_jobs()
        job_info = extract_job_info(qstat_json)

        if run_id not in job_info:
            raise RuntimeError(f"Job ID {run_id} not found in qstat output")

        # Update the job info cache
        job_info_cache.set(job_info)

        if job_info[run_id]["job_state"] == "F":
            return job_info[run_id]

        # TODO: Are there other job states should check for?


def get_git_branch_name(path):
    """Get the git branch name of the given git directory"""
    try:
        cmd = "git rev-parse --abbrev-ref HEAD"
        result = sp.check_output(cmd, shell=True, cwd=path).strip()
        # Decode byte string to string
        branch_name = result.decode("utf-8")
        return branch_name
    except sp.CalledProcessError:
        return None
