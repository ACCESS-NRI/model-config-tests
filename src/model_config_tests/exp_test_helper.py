# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

import glob
import os
import re
import shutil
import subprocess as sp
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Optional

import yaml

from model_config_tests.models import index as model_index
from model_config_tests.util import wait_for_qsub


class ExpTestHelper:
    """
    Helper class to manage a payu experiment

    Parameters
    ----------
    control_path: Path
        The path to the payu control directory
    lab_path: Path
        The path to the payu lab directory
    disable_payu_run: bool
        Whether to disable the payu run. This is useful for testing
        where we don't want to submit any PBS jobs
    """

    def __init__(
        self,
        control_path: Path,
        lab_path: Path,
        disable_payu_run: Optional[bool] = False,
    ):

        self.exp_name = control_path.name
        self.control_path = control_path
        self.lab_path = lab_path
        self.config_path = control_path / "config.yaml"
        self.archive_path = lab_path / "archive" / self.exp_name
        self.work_path = lab_path / "work" / self.exp_name

        # Output directories that are accessed in tests
        self.output000 = self.archive_path / "output000"
        self.output001 = self.archive_path / "output001"
        self.restart000 = self.archive_path / "restart000"
        self.restart001 = self.archive_path / "restart001"

        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)

        self.set_model()

        self.disable_payu_run = disable_payu_run

        self.run_id = None

    def set_model(self):
        """Set model based on payu config. Currently only setting top-level
        model"""
        self.model_name = self.config.get("model")
        ModelType = model_index[self.model_name]
        self.model = ModelType(self)

    def extract_checksums(
        self,
        output_directory: Path = None,
        schema_version: str = None,
    ):
        """Use model subclass to extract checksums from output"""
        return self.model.extract_checksums(output_directory, schema_version)

    def has_run(self):
        """
        See whether this experiment has been run.
        """
        return self.model.output_exists()

    def setup_for_test_run(self):
        """
        Various config.yaml settings need to be modified in order to run in the
        test environment.
        """

        with open(self.config_path) as f:
            doc = yaml.safe_load(f)

        # Disable git runlog
        doc["runlog"] = False

        # Disable metadata and set override experiment name for work/archive
        # directories
        doc["metadata"] = {"enable": False}
        doc["experiment"] = self.exp_name

        # Set laboratory path
        doc["laboratory"] = str(self.lab_path)

        # Disable post-processing
        doc["collate"] = {"enable": False}
        doc["sync"] = {"enable": False}
        if "postscript" in doc:
            doc.pop("postscript")
        if "userscripts" in doc:
            if "archive" in doc["userscripts"]:
                doc["userscripts"].pop("archive")

        with open(self.config_path, "w") as f:
            yaml.dump(doc, f)

    def submit_payu_run(self, n_runs: int = None) -> str:
        """
        Submit a payu run job.

        Parameters
        ----------
        n_runs: int
            The number of runs to submit with --nruns.

        Returns
        ----------
        str
            The job ID of the submitted payu run job
        """
        if self.disable_payu_run:
            return

        owd = Path.cwd()
        try:
            # Change to experiment directory and run.
            os.chdir(self.control_path)

            print("Running payu setup")
            result = sp.run(
                ["payu", "setup", "--lab", str(self.lab_path)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                # Add additional error messaging for debugging
                error_msg = (
                    "Failed to run payu setup:\n"
                    f"Return code: {result.returncode}\n"
                    f"--- stdout ---\n{result.stdout}\n"
                    f"--- stderr ---\n{result.stderr}"
                )
                print(error_msg)
                raise RuntimeError(error_msg)

            print("Running payu sweep")
            sp.run(
                ["payu", "sweep", "--lab", str(self.lab_path)],
                capture_output=True,
                text=True,
                check=True,
            )

            run_command = ["payu", "run", "--lab", str(self.lab_path)]
            if n_runs:
                run_command.extend(["--nruns", str(n_runs)])
            print(f"Running payu run command: {' '.join(run_command)}")
            result = sp.run(run_command, capture_output=True, text=True, check=True)
            self.run_id = parse_run_id(result.stdout)
            print(f"Run Job ID: {self.run_id}")
        except sp.CalledProcessError as e:
            raise RuntimeError(f"Failed to submit payu run. Error: {e}")
        finally:
            # Change back to original working directory
            os.chdir(owd)

    def wait_for_payu_run(self, run_id: str = None) -> list[str]:
        """Given a run ID, wait for all the payu run jobs to finish.

        Parameters
        ----------
        run_id: str
            The job ID of the payu run job to wait for. If None, use the
            run ID saved in the class.

        Returns
        ----------
        list[str]
            A list of filepaths to the output log files created by the run jobs
        """
        if self.disable_payu_run:
            return

        if run_id is None:
            run_id = self.run_id

        # Wait for payu PBS jobs to complete
        output_files = wait_for_payu_jobs(
            control_path=self.control_path,
            run_id=run_id,
            wait_for_qsub_func=wait_for_qsub,
        )
        return output_files


class Experiments:
    """
    Class to manage the shared payu experiments

    Parameters
    ----------
    control_path: Path
        The path to the configuration to that is being tested - this will
        be copied to the control directory for the test experiments
    output_path: Path
        The path to store all test output. e.g. control and lab directories
        for the test experiments
    keep_archive: bool
        Whether to keep previous test output. This is useful for testing
    """

    def __init__(
        self,
        control_path: Path,
        output_path: Path,
        keep_archive: Optional[bool] = False,
    ):
        self.control_path = control_path
        self.output_path = output_path
        self.keep_archive = keep_archive
        self.experiments = {}
        self.experiment_errors = {}

    def setup_and_submit(
        self,
        exp_name: str,
        model_runtime: Optional[int] = None,
        n_runs: Optional[int] = None,
    ) -> ExpTestHelper:
        """Setup and submit a payu experiment

        Parameters
        ----------
        exp_name: str
            The name of the experiment to run
        model_runtime: int
            The model runtime in seconds. If None, use the default
            model runtime defined in the model class
        n_runs: int
            The number of runs to submit with --nruns. If None, submit once

        Returns
        ----------
        ExpTestHelper
            The experiment helper object for the submitted experiment
        """
        # Setup experiment
        exp = setup_exp(
            self.control_path, self.output_path, exp_name, self.keep_archive
        )

        print(f"-----Setting up experiment {exp_name}-----")
        print(f"Control path: {exp.control_path}")
        print(f"Lab path: {exp.lab_path}")
        print(f"Archive path: {exp.archive_path}")

        if model_runtime is not None:
            # Set model runtime in seconds
            exp.model.set_model_runtime(seconds=model_runtime)
        else:
            # Set the default model runtime defined in the model class
            exp.model.set_model_runtime()

        # Add experiment  to dictionary of saved experiments
        self.experiments[exp_name] = exp

        # Submit the experiment
        if n_runs is not None:
            exp.submit_payu_run(n_runs=n_runs)
        else:
            exp.submit_payu_run()

        return exp

    def get_experiment(self, exp_name: str) -> ExpTestHelper:
        """
        Return the experiment object for the given experiment name
        """
        return self.experiments.get(exp_name)

    def wait_for_all_experiments(self, catch_errors=True) -> None:
        """
        Wait for all experiments to finish

        Parameters
        ----------
        catch_errors: bool
            Whether to catch errors and continue waiting for other test
            experiments, or raise an error and stop the tests. Default is True.
        """
        for exp_name, exp in self.experiments.items():
            print(f"-----Waiting for experiment {exp_name} to complete-----")
            try:
                exp.wait_for_payu_run()
                print(f"Experiment {exp_name} completed successfully")
            except RuntimeError as e:
                self.experiment_errors[exp_name] = str(e)
                if catch_errors:
                    print(f"Error running experiment {exp_name}: {e}")
                else:
                    raise

    def check_experiment(self, exp_name: str) -> None:
        """
        Check whether given experiment name has run successfully
        """
        if exp_name in self.experiment_errors:
            raise RuntimeError(
                f"There was an error running experiment {exp_name}:"
                f" {self.experiment_errors[exp_name]}"
            )

        # Double check if the required experiment output exists
        exp = self.experiments.get(exp_name)
        if not exp.model.output_exists():
            raise RuntimeError(f"Experiment {exp_name} output file does not exist.")


def setup_exp(
    control_path: Path, output_path: Path, exp_name: str, keep_archive: bool = False
) -> ExpTestHelper:
    """
    Create a experiment by copying over a base configuration to the control
    directory, and setting up the lab and archive directories, and
    the config.yaml file
    """
    # Set experiment control path
    if control_path.name != "base-experiment":
        exp_name = f"{control_path.name}-{exp_name}"

    exp_control_path = output_path / "control" / exp_name

    # Copy over base control directory (e.g. model configuration)
    if exp_control_path.exists():
        shutil.rmtree(exp_control_path)
    shutil.copytree(control_path, exp_control_path, symlinks=True)

    exp_lab_path = output_path / "lab"

    exp = ExpTestHelper(
        control_path=exp_control_path,
        lab_path=exp_lab_path,
        disable_payu_run=keep_archive,
    )

    # Remove any pre-existing archive or work directories for the experiment
    if not keep_archive:
        try:
            shutil.rmtree(exp.archive_path)
        except FileNotFoundError:
            pass
        try:
            shutil.rmtree(exp.work_path)
        except FileNotFoundError:
            pass

    # Set up experiment config
    exp.setup_for_test_run()

    return exp


def parse_run_id(stdout: str) -> str:
    """Parses the Gadi PBS run ID from the subprocess stdout that submits payu
    run"""
    ids = parse_gadi_pbs_ids(stdout)
    if len(ids) != 1:
        raise RuntimeError(
            "Expected 1 job ID in payu run submission, "
            f"but found {len(ids)}. IDs: {ids}"
        )
    return ids[0]


def parse_gadi_pbs_ids(stdout: str) -> list[str]:
    """
    Parse all Gadi PBS job IDs that are printed out in to a line
    in the payu stdout file

    Parameters
    ----------
    stdout: str
        The contents of a payu PBS job stdout file

    Returns
    ----------
    list[str]
        A list of jobs IDs printed out to a line
    """
    # Define the regex pattern, e.g. 137776067.gadi-pbs
    pattern = r"^(\d+\.gadi-pbs)$"

    # Find all matches in the text
    matches = re.findall(pattern, stdout, re.MULTILINE)
    return matches


def parse_exit_status_from_file(stdout: str) -> Optional[int]:
    """
    Parse the exit status from the payu stdout file

    Parameters
    ----------
    stdout: str
        The contents of a payu PBS job stdout file

    Returns
    ----------
    int
        The exit status of the job. If not found, return None.
    """
    # Regex pattern for exit status - allow spaces before and after
    pattern = r"^\s*Exit Status:\s*(\d+)\s*$"

    # Find all matches in the text
    matches = re.findall(pattern, stdout, re.MULTILINE)
    if len(matches) == 0:
        return None
    return int(matches[-1])


def parse_pbs_submitted_jobs(stdout: str) -> Optional[str]:
    """
    Parse a payu STDOUT file for run job ID. If there are multiple job IDs,
    assume payu run is the last one found.

    Parameters
    ----------
    stdout: str
        The contents of a payu job stdout file

    Returns
    ----------
    Optional[str]
        Any submitted payu run ID. If a subsequent run job was
        not submitted, the id will be None.
    """
    run_pattern = r"^qsub.*/bin/payu-run$"
    run_submitted = re.search(run_pattern, stdout, re.MULTILINE) is not None

    job_ids = parse_gadi_pbs_ids(stdout)

    run_id = None
    if run_submitted:
        if len(job_ids) < 1:
            raise RuntimeError(
                "No job ID found in stdout file for subsequent payu run job"
            )
        elif len(job_ids) > 1:
            # Warning as post-processing is currently disabled
            warnings.warn(f"Found more than 1 job IDs in stdout file (IDs: {job_ids})")
        run_id = job_ids[-1]

    return run_id


def read_job_output_file(
    control_path: Path, job_id: str, file_type: str = "stdout"
) -> tuple[str, str]:
    """
    Read the output file of a job

    Parameters
    ----------
    control_path: str
        The path to the control directory
    job_id: str
        The ID of the job to read the output file for.
    file_type: str
        The type of file to read ("stdout" or "stderr")

    Returns
    ----------
    tuple[str, str]
        A tuple of (contents, filename) where contents of the stdout/stderr
        file and filename is the path to the file.
    """
    job_id = job_id.split(".")[0]
    if file_type == "stdout":
        filename = glob.glob(str(control_path / f"*.o{job_id}"))
    elif file_type == "stderr":
        filename = glob.glob(str(control_path / f"*.e{job_id}"))
    else:
        raise ValueError("file_type must be 'stdout' or 'stderr'")

    if len(filename) != 1:
        raise RuntimeError(
            f"Expected 1 {file_type} file for job ID {job_id}, "
            f"but found {len(filename)}. Files: {filename}"
        )

    with open(filename[0]) as f:
        contents = f.read()

    return contents, filename[0]


def wait_for_qsub_job(
    control_path: Path,
    job_id: str,
    wait_for_qsub_func: Callable[[str], None],
    job_type: str = "run",
) -> tuple[str, str, list]:
    """
    Wait for a qsub job to finish, checks the exit status,
    and returns the job output files.

    Parameters
    ----------
    control_path: str
        The path to the control directory
    job_id: str
        The ID of the job to wait for.
    wait_for_qsub_func: Callable[[str], None]
        A function that waits for a PBS job to complete
    job_type: str
        The type of job to wait for - e.g. "run"

    Returns
    ----------
    tuple[str, str, list]
        A tuple of (stdout, stderr, output_files) where stdout and stderr
        are the contents of the stdout and stderr files, and output_files
        is a list of filepaths to the output files
    """
    # Wait for job to complete
    print(f"Waiting for {job_type} job to finish. Job ID: {job_id}")
    wait_for_qsub_func(job_id)

    # Read stdout/stderr files
    stdout, stdout_filename = read_job_output_file(control_path, job_id, "stdout")
    stderr, stderr_filename = read_job_output_file(control_path, job_id, "stderr")
    output_files = [stdout_filename, stderr_filename]

    # Check whether the run job was successful
    exit_status = parse_exit_status_from_file(stdout)
    if exit_status != 0:
        raise RuntimeError(
            f"Payu {job_type} job failed with exit status {exit_status}:\n"
            f"Job_ID: {job_id}\n"
            f"Output files: {output_files}\n"
            f"--- stdout ---\n{stdout}\n"
            f"--- stderr ---\n{stderr}\n"
        )

    return stdout, stderr, output_files


def wait_for_payu_jobs(
    control_path: Path, run_id: str, wait_for_qsub_func: Callable[[str], None]
) -> list[str]:
    """
    Wait for a initial payu run PBS job to finsh, then waits
    for any subsequent run jobs.

    Raises an Runtime Error if any of the jobs fail, or unable to parse
    STDOUT/STDERR files for job IDs.

    Parameters
    ----------
    control_path: str
        The path to the control directory. This is where to find the
        STDOUT/STDERR files for the jobs.
    run_id: str
        The ID of the run job to wait for.
    wait_for_qsub_func: Callable[[str], None]
        A function that waits for a PBS job to complete

    Returns
    ----------
    list[str]
        A list of filepaths to the output log files created by the run jobs.
    """
    output_files = []
    run_count = 0
    while run_id is not None:
        # Wait for run to complete
        run_stdout, _, run_output_files = wait_for_qsub_job(
            control_path, run_id, wait_for_qsub_func
        )
        output_files.extend(run_output_files)

        # Check whether a job job was submitted
        next_run_id = parse_pbs_submitted_jobs(run_stdout)

        if next_run_id is not None:
            run_count += 1
            print(
                f"Waiting for subsequent submitted payu run job (run_count: {run_count})"
            )

        run_id = next_run_id
    return output_files
