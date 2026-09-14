# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
import subprocess as sp
from pathlib import Path
from typing import Optional

import yaml

from model_config_tests.models import index as model_index
from model_config_tests.util import (
    get_latest_run_info,
    payu_status_json,
    wait_for_run_job,
)


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
        exp_name: Optional[str] = None,
    ):

        if exp_name:
            self.exp_name = exp_name
        else:
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
        self.run_number = None
        self.n_runs = None

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

    def setup(self, reproduce=False):
        """
        Run payu setup command. If reproduce is True, run with --reproduce flag
        to check if md5 hashes have changed in the manifests.
        """
        owd = Path.cwd()
        # Change to experiment directory and run.
        os.chdir(self.control_path)

        try:
            setup_command = [
                "payu",
                "setup",
                "--lab",
                str(self.lab_path),
            ]
            if reproduce:
                setup_command.append("--reproduce")
            print(f"Running payu setup command: {setup_command}")
            result = sp.run(setup_command, capture_output=True, text=True)

        finally:
            # Change back to original working directory
            os.chdir(owd)

        if result.returncode != 0:
            raise RuntimeError(
                "Failed to run payu setup"
                + (" with --reproduce.\n" if reproduce else ".\n")
                + f"{'='*10}STDOUT{'='*10}\n {result.stdout}\n"
                f"{'='*10}STDERR{'='*10}\n {result.stderr}\n"
            )

    def run_git_diff(self, path, extra_args=None):
        """
        Run git diff command on the given path and return the output.
        """
        command = ["git", "-C", str(path), "diff"] + extra_args if extra_args else []

        result = sp.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                f"Git command failed with exit code {result.returncode}.\n"
                f"{'='*10}STDOUT{'='*10}\n {result.stdout}\n"
                f"{'='*10}STDERR{'='*10}\n {result.stderr}\n"
            )

        return result.stdout

    def setup_reproduce(self):
        """
        Run payu setup with `--repro` flag to check if md5 hashes have changed in the manifests.
        """
        self.setup(reproduce=True)

    def setup_manifests_unchanged(self):
        """
        Run payu setup command and check if manifests files have been changed with `git diff`.
        """
        self.setup(reproduce=False)

        result = self.run_git_diff(
            self.control_path, extra_args=["--name-only", "manifests/"]
        )
        if result != "":
            # Collect and display the top 10 lines of the diff for each modified file
            files = result.strip().split("\n")
            error_message = "Modifications are detected in file:\n"
            error_message += "\n".join(" - " + file for file in files) + "\n"
            error_message += "\nIf md5 hashes have changed, this indicates file contents being different."
            error_message += """
If binhashes/paths have changed but md5's are the same,
this will mean the configuration can reproduce the manifests
but `payu setup` will take longer to run as it needs to re-calculate all the md5 hashes.
            """
            for file in files:
                diff_details = self.run_git_diff(
                    self.control_path, extra_args=[f"{file}"]
                )
                diff_lines = diff_details.splitlines()
                top_lines = "\n".join(diff_lines[2:12])
                if len(diff_lines) > 12:
                    top_lines += "\n... (truncated)"
                error_message += f"\n{'='*10} Diff for {file} {'='*10}\n{top_lines}\n"
            raise RuntimeError(f"{error_message}")

    def setup_for_test_run(self):
        """
        Various config.yaml settings need to be modified in order to run in the
        test environment.
        """

        with open(self.config_path) as f:
            doc = yaml.safe_load(f)

        # Disable git runlog
        doc["runlog"] = False

        # Reduce walltime for test runs to 10 minutes
        doc["walltime"] = "00:10:00"

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
        self.n_runs = n_runs if n_runs is not None else 1

        if self.disable_payu_run:
            return

        owd = Path.cwd()
        try:
            # Change to experiment directory and run.
            os.chdir(self.control_path)

            # Run payu setup command
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

            # Run payu sweep command
            print("Running payu sweep")
            sp.run(
                ["payu", "sweep", "--lab", str(self.lab_path)],
                capture_output=True,
                text=True,
                check=True,
            )

            # Run payu run command
            run_command = ["payu", "run", "--lab", str(self.lab_path)]
            if self.n_runs > 1:
                run_command.extend(["--nruns", str(self.n_runs)])
            print(f"Running payu run command: {' '.join(run_command)}")
            sp.run(run_command, capture_output=True, text=True, check=True)

            # Query payu status
            status_data = payu_status_json(self.control_path, self.lab_path)

            # Store the run number and job id
            self.run_number, run_info = get_latest_run_info(status_data)
            self.run_id = run_info.get("job_id")
            print(f"Run Job ID: {self.run_id}")

        except sp.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to submit payu run:\n"
                f"Return code: {e.returncode}\n"
                f"--- stdout ---\n{e.stdout}\n"
                f"--- stderr ---\n{e.stderr}"
            )
        finally:
            # Change back to original working directory
            os.chdir(owd)

    def wait_for_payu_run(self) -> list[str]:
        """Wait for the submitted payu run job(s) to finish, querying
        `payu status --json` for job status rather than parsing stdout/log
        files.

        Returns
        ----------
        list[str]
            A list of filepaths to the output log files created by the run jobs
        """
        if self.disable_payu_run:
            return

        # Wait for initial run and subsequent run jobs to complete
        # A RuntimeRrror is raised if exit_status/model_exit_status is non-zero
        for current_run_number in range(self.run_number, self.run_number + self.n_runs):
            print(f"Waiting for run job to finish. Run number: {current_run_number}")
            run_info = wait_for_run_job(
                self.control_path, self.lab_path, current_run_number
            )
            print(
                f"Job {run_info.get('job_id')} for run {current_run_number} finished successfully."
            )

        return


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
