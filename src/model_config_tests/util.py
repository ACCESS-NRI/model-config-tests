# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

import json
import os
import subprocess as sp
import time
from pathlib import Path
from typing import Optional

# Time related constants
MINUTE_IN_SECONDS = 60
HOUR_IN_SECONDS = MINUTE_IN_SECONDS * 60
DAY_IN_SECONDS = HOUR_IN_SECONDS * 24


def payu_status_json(
    control_path: Path,
    lab_path: Path,
    run_number: Optional[int] = None,
    update: bool = False,
) -> dict:
    """
    Run `payu status --json` for the experiment in the given control
    directory, and return the parsed JSON output. This is a machine-readable
    interface for querying job IDs and experiment run status, rather than
    parsing payu stdout/log files.

    Parameters
    ----------
    control_path: Path
        The path to the payu control directory
    lab_path: Path
        The path to the payu lab directory
    run_number: int
        Only query information for the given run number. If None, query the
        latest run
    update: bool
        Update the job files with the latest data from the scheduler before
        returning the status

    Returns
    -------
    dict
        The parsed JSON output of `payu status`
    """
    owd = Path.cwd()
    # Change to experiment directory and run.
    os.chdir(control_path)
    try:
        status_cmd = ["payu", "status", "--lab", str(lab_path), "--json"]
        if update:
            status_cmd.append("--update")
        if run_number is not None:
            status_cmd.extend(["-n", str(run_number)])

        print(f"Checking payu status with command: {' '.join(status_cmd)}")
        result = sp.run(status_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                "payu status command failed:\n"
                f"Return code: {result.returncode}\n"
                f"--- stdout ---\n{result.stdout}\n"
                f"--- stderr ---\n{result.stderr}"
            )

    finally:
        # Change back to original working directory
        os.chdir(owd)

    stdout = result.stdout
    json_output = stdout[stdout.index("{"):]
    return json.loads(json_output)


def wait_for_run_job(control_path: Path, lab_path: Path, run_number: int) -> dict:
    """
    Call `payu status --json` until the run job for the given run number has
    an exit code.
    Return job information if exit code and model exit code are both zero, 
    otherwise raise a RuntimeError.

    Parameters
    ----------
    control_path: Path
        The path to the payu control directory
    lab_path: Path
        The path to the payu lab directory
    run_number: int
        The run number of the run job to wait for
    """
    while True:
        # Call payu status --update
        status_data = payu_status_json(
            control_path, lab_path, run_number=run_number, update=True
        )

        run_jobs = status_data.get("runs", {}).get(str(run_number), {}).get("run")
        if not run_jobs:
            raise RuntimeError(
                f"No run job information found for run number {run_number} "
                f"in payu status output: {status_data}"
            )
        
        run_info = run_jobs[-1]
        exit_status = run_info.get("exit_status", None)

        # If exit_status exists, 
        # return run_info if both exit_status and model_exit_status are zero,
        # otherwise raise a RuntimeError.
        if exit_status is not None:
            model_exit_status = run_info.get("model_exit_status", None)

            if exit_status == 0 and model_exit_status == 0:
                return run_info

            raise RuntimeError(
                f"Payu run job failed for run number {run_number}:\n"
                f"Job ID: {run_info.get('job_id')}\n"
                f"Exit status: {exit_status}\n"
                f"Model exit status: {model_exit_status}\n"
                f"Output Log: {run_info.get('stdout_file')}\n"
                f"Error Log: {run_info.get('stderr_file')}\n"
            )

        # Wait for a minute if no exit_status yet
        time.sleep(MINUTE_IN_SECONDS) 

def get_latest_run_info(status_data: dict) -> tuple:
    """
    Return the (run_number, run job info) for the latest run in
    `payu status --json` output.

    Parameters
    ----------
    status_data: dict
        The parsed JSON output of `payu status`
    """
    runs = status_data.get("runs", {})
    if not runs:
        raise RuntimeError(
            f"No run information found in payu status output: {status_data}"
        )

    latest_run_number = max(int(run_number) for run_number in runs.keys())
    run_jobs = runs[str(latest_run_number)].get("run")
    if not run_jobs:
        raise RuntimeError(
            f"No run job information found for run number {latest_run_number} "
            f"in payu status output: {status_data}"
        )
    return latest_run_number, run_jobs[-1]


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
