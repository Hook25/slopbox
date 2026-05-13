import pytest

from slopbox.cli import main


def test_main_requires_subcommand(capsys):
    """Running with no arguments should exit with an error."""
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 2
