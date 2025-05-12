import pytest

from model_config_tests.compare_exp_tests.conftest import get_experiment_pairs


@pytest.mark.parametrize(
    "dirs, expected_pairs_names",
    [
        ("exp1 exp2", [("exp1", "exp2")]),
        (
            "exp1 exp2 exp3 exp4",
            [
                ("exp1", "exp2"),
                ("exp1", "exp3"),
                ("exp1", "exp4"),
                ("exp2", "exp3"),
                ("exp2", "exp4"),
                ("exp3", "exp4"),
            ],
        ),
        # Test duplicates are removed
        ("exp1 exp2 exp1 exp2", [("exp1", "exp2")]),
    ],
)
def test_get_experiment_pairs_relative_paths(tmp_path, dirs, expected_pairs_names):
    """
    Test the get_experiment_pairs function to ensure it correctly
    generates pairs of experiment directories for comparison.
    """
    # Create temporary directories for testing
    for dir in dirs.split():
        exp_path = tmp_path / dir
        if not exp_path.exists():
            exp_path.mkdir()

    # Call the function to get experiment pairs
    pairs = get_experiment_pairs(dirs, tmp_path)

    # Check that the pairs are generated correctly
    assert len(pairs) == len(expected_pairs_names)
    for exp1, exp2 in pairs:
        assert exp1.is_absolute()
        assert exp2.is_absolute()
        assert (exp1.name, exp2.name) in expected_pairs_names


def test_get_experiment_pairs_absolute_paths(tmp_path):
    exp1 = (tmp_path / "exp1").resolve()
    exp2 = (tmp_path / "exp2").resolve()
    exp1.mkdir()
    exp2.mkdir()

    # Test dirs is a space-separated string of absolute paths
    pairs = get_experiment_pairs(f"{exp1} {exp2}", tmp_path)
    assert len(pairs) == 1
    assert pairs[0] == (exp1, exp2)


def test_get_experiment_pairs_nonexistent_dir(tmp_path):
    with pytest.raises(ValueError, match="Directory exp1 does not exist"):
        get_experiment_pairs("exp1", tmp_path)


def test_get_experiment_pairs_invalid_dir(tmp_path):
    file_path = tmp_path / "exp1.txt"
    file_path.touch()
    with pytest.raises(ValueError, match=f"Path {file_path} is not a directory"):
        get_experiment_pairs(str(file_path), tmp_path)


def test_get_experiment_pairs_not_enough_dirs(tmp_path):
    exp1 = tmp_path / "exp1"
    exp1.mkdir()
    with pytest.raises(
        ValueError, match="Need at least two directories with --dirs to compare"
    ):
        get_experiment_pairs("exp1", tmp_path)
