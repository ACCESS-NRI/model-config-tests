import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml
from netCDF4 import Dataset

from model_config_tests.exp_test_helper import (
    Experiments,
    ExpTestHelper,
    setup_exp,
)
from model_config_tests.models.accessom3 import AccessOm3
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


@pytest.fixture
def exp_with_restarts(exp, tmp_path):
    """
    Extend the existing `exp` with restart dirs and an rpointer file for AccessOm3.
    """
    restart000 = tmp_path / "restart000"
    restart001 = tmp_path / "restart001"
    restart000.mkdir(parents=True, exist_ok=True)
    restart001.mkdir(parents=True, exist_ok=True)

    exp.restart000 = restart000
    exp.restart001 = restart001

    (restart000 / "rpointer.ocn").write_text("access-om3.mom6.r.1900-01-02-00000.nc\n")
    return exp


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
        "walltime": "00:10:00",
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
        "walltime": "00:10:00",
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
    mock_run.return_value.returncode = 0

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
    mock_run.return_value.returncode = 0

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
def test_experiment_submit_payu_run_setup_error(mock_run, exp):
    """Test that an error is raised when payu setup fails"""
    mock_run.return_value.stdout = "Some output"
    mock_run.return_value.stderr = "Some error"
    mock_run.return_value.returncode = 1

    with pytest.raises(RuntimeError, match="Failed to run payu setup*"):
        exp.submit_payu_run()

    assert exp.run_id is None


@patch("subprocess.run")
def test_experiment_submit_payu_run_error(mock_run, exp):
    """Test that an RuntimeError is raised with CalledProcessError"""
    # Mock the first call to payu setup to succeed
    # and subsequent payu command to fail
    setup_success = Mock()
    setup_success.stdout = "Setup successful"
    setup_success.returncode = 0

    run_return_code = 1
    run_error_stdout = "Example stdout"
    run_error_stderr = "Example stderr"
    mock_run.side_effect = [
        setup_success,
        subprocess.CalledProcessError(
            returncode=run_return_code,
            cmd="payu run",
            output=run_error_stdout,
            stderr=run_error_stderr,
        ),
    ]

    with pytest.raises(RuntimeError, match="Failed to submit payu run.*") as exec_info:
        exp.submit_payu_run()

    assert exp.run_id is None
    assert f"--- stdout ---\n{run_error_stdout}" in str(exec_info.value)
    assert f"--- stderr ---\n{run_error_stderr}" in str(exec_info.value)
    assert f"Return code: {run_return_code}" in str(exec_info.value)



def mock_wait_for_qsub(job_id):
    """
    Mock function to simulate waiting for a qsub job to finish.
    """
    return None



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


def _test_collect_restart_tiles_unified(exp_with_restarts):
    exp_accessom3 = AccessOm3(exp_with_restarts)
    restart = exp_accessom3.output_0 / "access-om3.mom6.r.1900-01-02-00000.nc"
    restart.write_bytes(b"")

    restart_path = AccessOm3.collect_restart_tiles(restart)
    assert restart_path == restart


def test_collect_restart_tiles_split(exp_with_restarts):
    exp_accessom3 = AccessOm3(exp_with_restarts)
    base = exp_accessom3.output_0 / "access-om3.mom6.r.1900-01-02-00000.nc"
    tile0 = Path(str(base) + ".0000")
    tile0.write_bytes(b"")
    tile1 = Path(str(base) + ".0001")
    tile1.write_bytes(b"")

    first_tile_path = AccessOm3._collect_restart_tiles(base)
    assert first_tile_path.name.endswith(".0000")


def test_collect_restart_tiles_when_0000_missing(exp_with_restarts):
    """
    If .nc.0000 is missing, ensure the next available tile is used (eg, .nc.0001)
    This is because the 0000 tile can be completely masked.
    """
    exp_accessom3 = AccessOm3(exp_with_restarts)
    base = exp_accessom3.output_0 / "access-om3.mom6.r.1900-01-02-00000.nc"
    tile1 = Path(str(base) + ".0001")
    tile1.write_bytes(b"")

    first_tile_path = AccessOm3._collect_restart_tiles(base)
    assert first_tile_path.name.endswith(".0001")


def test_collect_restart_tiles_missing(exp_with_restarts):
    exp_accessom3 = AccessOm3(exp_with_restarts)
    missing = exp_accessom3.output_0 / "access-om3.mom6.r.1900-01-02-00000.nc"

    with pytest.raises(FileNotFoundError):
        AccessOm3._collect_restart_tiles(missing)


def _create_nc_with_checksum(path, varname="v", checksum="2C6888522FC609AA"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with Dataset(path, "w") as ds:
        ds.createDimension("x", 1)
        v = ds.createVariable(varname, "f4", ("x",))
        v[:] = 0.0
        v.setncattr("checksum", checksum)


def test_extract_checksums_unified(exp_with_restarts):
    exp_accessom3 = AccessOm3(exp_with_restarts)
    nc_path = exp_accessom3.output_0 / "access-om3.mom6.r.1900-01-02-00000.nc"
    _create_nc_with_checksum(nc_path, varname="u", checksum="FF24B558B5C5561D")

    checksums = exp_accessom3.extract_checksums(output_directory=exp_accessom3.output_0)
    assert checksums["output"]["u"][0] == "FF24B558B5C5561D"


def test_extract_checksums_split_uses_first_tile(exp_with_restarts):
    exp_accessom3 = AccessOm3(exp_with_restarts)
    # Ensure rpointer points to the base (no suffix); we already set that in the fixture
    base = exp_accessom3.output_0 / "access-om3.mom6.r.1900-01-02-00000.nc"
    tile0 = Path(str(base) + ".0000")
    tile1 = Path(str(base) + ".0001")

    _create_nc_with_checksum(tile0, varname="DTBT", checksum="AC87F8AC28BD1436")
    _create_nc_with_checksum(tile1, varname="DTBT", checksum="ignored")

    checksums = exp_accessom3.extract_checksums(output_directory=exp_accessom3.output_0)
    assert checksums["output"]["DTBT"][0] == "AC87F8AC28BD1436"


def test_experiments_check_experiment_error(tmp_path):
    with patch("model_config_tests.exp_test_helper.setup_exp") as mock_setup_exp:
        # Create an experiment that will error later on
        mock_error_exp = Mock(autospec=ExpTestHelper)
        mock_setup_exp.return_value = mock_error_exp
        mock_error_exp.wait_for_payu_run.side_effect = RuntimeError(
            "Payu run job failed with exit status 1"
        )

        exps = Experiments(
            control_path=tmp_path / "control",
            output_path=tmp_path / "output",
            keep_archive=True,
        )
        exps.setup_and_submit(exp_name="error_exp")
        assert exps.experiments["error_exp"] == mock_error_exp

        # Add a second experiment that will succeed
        mock_success_exp = Mock(autospec=ExpTestHelper)
        mock_success_exp.wait_for_payu_run.return_value = None
        mock_setup_exp.return_value = mock_success_exp

        exps.setup_and_submit(exp_name="success_exp")
        assert exps.experiments["success_exp"] == mock_success_exp

    # Check no errors are raised here
    exps.wait_for_all_experiments(catch_errors=True)
    assert exps.experiment_errors == {
        "error_exp": "Payu run job failed with exit status 1"
    }

    # Check no errors with successful experiment
    exps.check_experiment("success_exp")

    # Check error raised for the failed experiment
    error_msg = (
        "There was an error running experiment error_exp: "
        "Payu run job failed with exit status 1"
    )
    with pytest.raises(RuntimeError, match=error_msg):
        exps.check_experiment("error_exp")


@patch("subprocess.run")
def test_setup_reproduce_error(mock_run, exp):
    """Test that payu setup --repro fails raises an error and return to original work directory"""
    # Mock the payu setup --repro to fail
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "MD5 mismatch"
    mock_result.stdout = "Check manifest"
    mock_run.return_value = mock_result

    # Store original current working directory
    owd = Path.cwd()

    with pytest.raises(RuntimeError) as excinfo:
        exp.setup_reproduce()

    assert "Failed to run payu setup with --reproduce.\n" in str(excinfo.value)
    assert f"{'='*10}STDOUT{'='*10}\n {mock_result.stdout}\n" in str(excinfo.value)

    # assert returning to the original work directory
    assert Path.cwd() == owd


@patch("subprocess.run")
def test_setup_manifests_unchanged_fail_setup(mock_run, exp):
    """Test that an error is raised when payu setup fails in setup_manifests_unchanged()"""
    # Mock the payu setup --repro to fail with unchanged manifests
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Setup failed"
    mock_result.stdout = "Payu setup output"
    mock_run.return_value = mock_result

    # Store original current working directory
    owd = Path.cwd()

    with pytest.raises(RuntimeError) as excinfo:
        exp.setup_manifests_unchanged()

    assert "Failed to run payu setup" in str(excinfo.value)
    assert f"{'='*10}STDOUT{'='*10}\n {mock_result.stdout}\n" in str(excinfo.value)

    # assert returning to the original work directory
    assert Path.cwd() == owd


@patch("subprocess.run")
def test_setup_manifests_unchanged_show_changes(mock_run, exp):
    """Test that when manifests are changed, the `git diff` results are printed to stdout"""
    # Mock the `payu setup` succeed first
    setup_success = MagicMock(returncode=0, stdout="Payu setup succeeded")

    top_lines = """--- a/{diff_file}
+++ b/{diff_file}
+new line
-old line
    """
    diff_file = "manifests/input.yaml"
    # Then mock the `git diff --name-only` to show which files are changed
    git_diff_name_only = MagicMock(returncode=0, stdout=diff_file)

    # Mock the `git diff` to show the detailed changes in the file
    git_diff_run = MagicMock(
        returncode=0,
        stdout=(
            f"""diff --git a/{diff_file} b/{diff_file}
index abc123...zyx789 100111
"""
        )
        + top_lines,
    )

    # Run these mocks in sequence
    mock_run.side_effect = [setup_success, git_diff_name_only, git_diff_run]

    # Store original current working directory
    owd = Path.cwd()

    with pytest.raises(RuntimeError) as excinfo:
        exp.setup_manifests_unchanged()

    assert "Modifications are detected in file:\n" in str(excinfo.value)
    assert f"\n{'='*10} Diff for {diff_file} {'='*10}\n{top_lines}\n" in str(
        excinfo.value
    )

    # assert returning to the original work directory
    assert Path.cwd() == owd


@pytest.mark.parametrize(
    "config_name, control_name, expected_exp_name",
    [
        # Use ACCESS-ESM1.5 models. Since there is no model-specifi logic, only pick one model to test
        ("esm1p5-prein", "control", "control-test_exp"),
        ("esm1p5-prein", "base-experiment", "test_exp"),
    ],
)
def test_setup_exp_correct_config(
    tmp_path, isolated_config, config_name, control_name, expected_exp_name
):
    """Test that setup_exp writes correct information into the config file"""
    # Set up control and output directories
    control_path = tmp_path / control_name
    control_path.mkdir()
    output_path = tmp_path / "output"
    output_path.mkdir()

    # Copy the config.yaml from the isolated config directory to the control path
    _, config_dir = isolated_config(config_name)
    shutil.move(str(config_dir / "config.yaml"), control_path / "config.yaml")

    # Run the setup_exp function
    exp = setup_exp(
        control_path=control_path, output_path=output_path, exp_name="test_exp"
    )

    # Check that the config file has the expected values
    config = yaml.safe_load(exp.config_path.open())
    assert config["experiment"] == expected_exp_name
    assert not config["runlog"]
    assert not config["metadata"]["enable"]
    assert config["laboratory"] == str(exp.lab_path)
