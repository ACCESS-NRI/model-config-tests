# Copyright 2024 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

import glob
import os
import re
import shutil
import subprocess as sp
import sys
from pathlib import Path

import yaml

from model_config_tests.models import index as model_index
from model_config_tests.util import wait_for_qsub


class ExpTestHelper:

    def __init__(self, control_path: Path, lab_path: Path, disable_payu_run=False):

        self.exp_name = control_path.name
        self.control_path = control_path
        self.lab_path = lab_path
        self.config_path = control_path / "config.yaml"
        self.archive_path = lab_path / "archive" / self.exp_name
        self.work_path = lab_path / "work" / self.exp_name
        self.output000 = self.archive_path / "output000"
        self.output001 = self.archive_path / "output001"
        self.restart000 = self.archive_path / "restart000"
        self.restart001 = self.archive_path / "restart001"

        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)

        self.set_model()

        self.disable_payu_run = disable_payu_run

    def set_model(self):
        """Set model based on payu config. Currently only setting top-level
        model"""
        self.model_name = self.config.get("model")
        ModelType = model_index[self.model_name]
        self.model = ModelType(self)

    def extract_checksums(
        self, output_directory: Path = None, schema_version: str = None
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

        with open(self.config_path, "w") as f:
            yaml.dump(doc, f)

    def run(self):
        """
        Run the experiment using payu and check output.

        Don't do any work if it has already run.
        """
        # Skip running payu if it's disabled, or if output already exists
        if self.disable_payu_run or self.has_run():
            return 0, None, None, None
        else:
            return self.force_qsub_run()

    def force_qsub_run(self):
        """
        Run using qsub
        """
        if self.disable_payu_run:
            # Skip running payu if it's disabled.
            return 0, None, None, None

        # Change to experiment directory and run.
        owd = Path.cwd()
        try:
            os.chdir(self.control_path)
            sp.check_output(["payu", "sweep", "--lab", self.lab_path])
            run_id = sp.check_output(["payu", "run", "--lab", self.lab_path])
            run_id = run_id.decode().splitlines()[0]
        except sp.CalledProcessError:
            print("Error: call to payu run failed.", file=sys.stderr)
            return 1, None, None, None
        finally:
            os.chdir(owd)

        wait_for_qsub(run_id)
        run_id = run_id.split(".")[0]

        output_files = []
        # Read qsub stdout file
        stdout_filename = glob.glob(str(self.control_path / f"*.o{run_id}"))
        print(stdout_filename)
        if len(stdout_filename) != 1:
            print("Error: there are too many stdout files.", file=sys.stderr)
            return 2, None, None, None

        stdout_filename = stdout_filename[0]
        output_files.append(stdout_filename)
        stdout = ""
        with open(stdout_filename) as f:
            stdout = f.read()

        # Read qsub stderr file
        stderr_filename = glob.glob(str(self.control_path / f"*.e{run_id}"))
        stderr = ""
        if len(stderr_filename) == 1:
            stderr_filename = stderr_filename[0]
            output_files.append(stderr_filename)
            with open(stderr_filename) as f:
                stderr = f.read()

        # TODO: Early return if not collating

        # Read the qsub id of the collate job from the stdout.
        # Payu puts this here.

        # TODO: Fish out the exit code from the run logs and early
        # return if status != 0

        m = re.search(r"(\d+.gadi-pbs)\n", stdout)
        if m is None:
            print("Error: qsub id of collate job.", file=sys.stderr)
            return 3, stdout, stderr, output_files

        # Wait for the collate to complete.
        run_id = m.group(1)
        wait_for_qsub(run_id)

        # Return files created by qsub so caller can read or delete.
        collate_files = self.control_path / f"*.[oe]{run_id}"
        output_files += glob.glob(str(collate_files))

        return 0, stdout, stderr, output_files

    def setup_and_run(self):
        self.setup_for_test_run()
        return self.run()

    def print_run_logs(self, status, stdout, stderr, output_files):
        """Print run information"""
        run_info = (
            f"Experiment run: {self.exp_name}\n"
            f"Status: {status}\n"
            f"Control directory: {self.control_path}\n"
            f"Output files: {output_files}\n"
            f"--- stdout ---\n{stdout}\n"
            f"--- stderr ---\n{stderr}\n"
        )
        print(run_info)


def setup_exp(
    control_path: Path, output_path: Path, exp_name: str, keep_archive: bool = False
):
    """
    Create a exp by copying over base config
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

    return exp
