# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

import subprocess as sp
import time

# Time related constants
MINUTE_IN_SECONDS = 60
HOUR_IN_SECONDS = MINUTE_IN_SECONDS * 60
DAY_IN_SECONDS = HOUR_IN_SECONDS * 24


def wait_for_qsub(run_id):
    """
    Wait for the qsub job to terminate.
    """

    while True:
        time.sleep(MINUTE_IN_SECONDS)
        try:
            qsub_out = sp.check_output(["qstat", run_id], stderr=sp.STDOUT)
        except sp.CalledProcessError as err:
            qsub_out = err.output

        qsub_out = qsub_out.decode()

        if "Job has finished" in qsub_out:
            break


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
