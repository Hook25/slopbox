import json
from unittest.mock import MagicMock, patch

import pytest

from slopbox.submission.bugs import fetch_bugs, run


class TestFetchBugs:
    """Tests for fetch_bugs which queries Launchpad."""

    @patch("slopbox.submission.bugs.Launchpad")
    def test_bugs_returned(self, mock_launchpad_class):
        """When bugs exist, they are yielded as dicts."""
        mock_launchpad = MagicMock()
        mock_launchpad_class.login_with.return_value = mock_launchpad

        mock_bug1 = MagicMock()
        mock_bug1.id = 12345
        mock_bug1.web_link = "https://bugs.launchpad.net/test/+bug/12345"
        mock_bug1.title = "Bug title one"
        mock_bug1.tags = ["tag1", "tag2"]
        mock_bug1.description = "Description one"

        mock_task1 = MagicMock()
        mock_task1.status = "Confirmed"
        mock_task1.bug = mock_bug1

        mock_bug2 = MagicMock()
        mock_bug2.id = 12346
        mock_bug2.web_link = "https://bugs.launchpad.net/test/+bug/12346"
        mock_bug2.title = "Bug title two"
        mock_bug2.tags = []
        mock_bug2.description = "Description two"

        mock_task2 = MagicMock()
        mock_task2.status = "New"
        mock_task2.bug = mock_bug2

        mock_project = MagicMock()
        mock_project.searchTasks.return_value = [mock_task1, mock_task2]
        mock_launchpad.projects = {"testproj": mock_project}

        results = list(fetch_bugs("testproj"))

        assert len(results) == 2
        assert results[0] == {
            "id": 12345,
            "url": "https://bugs.launchpad.net/test/+bug/12345",
            "status": "Confirmed",
            "title": "Bug title one",
            "tags": ["tag1", "tag2"],
            "description": "Description one",
        }
        assert results[1] == {
            "id": 12346,
            "url": "https://bugs.launchpad.net/test/+bug/12346",
            "status": "New",
            "title": "Bug title two",
            "tags": [],
            "description": "Description two",
        }

    @patch("slopbox.submission.bugs.Launchpad")
    def test_no_bugs(self, mock_launchpad_class):
        """When a project has no bugs, nothing is yielded."""
        mock_launchpad = MagicMock()
        mock_launchpad_class.login_with.return_value = mock_launchpad

        mock_project = MagicMock()
        mock_project.searchTasks.return_value = []
        mock_launchpad.projects = {"emptyproj": mock_project}

        results = list(fetch_bugs("emptyproj"))

        assert results == []

    @patch("slopbox.submission.bugs.Launchpad")
    def test_auth_failure(self, mock_launchpad_class):
        """When Launchpad login fails, the original exception propagates."""
        mock_launchpad_class.login_with.side_effect = RuntimeError(
            "not authenticated"
        )

        with pytest.raises(RuntimeError, match="not authenticated"):
            list(fetch_bugs("testproj"))

    @patch("slopbox.submission.bugs.Launchpad")
    def test_filter_by_single_milestone(self, mock_launchpad_class):
        """Only bugs in the requested milestone are returned."""
        mock_launchpad = MagicMock()
        mock_launchpad_class.login_with.return_value = mock_launchpad

        mock_ms = MagicMock()
        mock_ms.name = "v1.0"
        mock_ms.self_link = (
            "https://api.launchpad.net/1.0/proj/+milestone/v1.0"
        )

        mock_bug = MagicMock()
        mock_bug.id = 100
        mock_bug.web_link = "https://bugs.launchpad.net/test/+bug/100"
        mock_bug.title = "In v1.0"
        mock_bug.tags = []
        mock_bug.description = "desc"

        mock_task = MagicMock()
        mock_task.status = "Confirmed"
        mock_task.bug = mock_bug

        mock_project = MagicMock()
        mock_project.all_milestones = [mock_ms]
        mock_project.searchTasks.return_value = [mock_task]
        mock_launchpad.projects = {"testproj": mock_project}

        results = list(fetch_bugs("testproj", milestones=["v1.0"]))

        assert len(results) == 1
        assert results[0]["id"] == 100
        mock_project.searchTasks.assert_called_once_with(
            milestone=mock_ms.self_link,
            status=[
                "New",
                "Incomplete",
                "Opinion",
                "Invalid",
                "Won't Fix",
                "Expired",
                "Confirmed",
                "Triaged",
                "In Progress",
                "Fix Committed",
                "Fix Released",
            ],
        )

    @patch("slopbox.submission.bugs.Launchpad")
    def test_filter_by_multiple_milestones(self, mock_launchpad_class):
        """Bugs from multiple milestones are merged and deduplicated."""
        mock_launchpad = MagicMock()
        mock_launchpad_class.login_with.return_value = mock_launchpad

        mock_ms1 = MagicMock()
        mock_ms1.name = "v1.0"
        mock_ms1.self_link = (
            "https://api.launchpad.net/1.0/proj/+milestone/v1.0"
        )

        mock_ms2 = MagicMock()
        mock_ms2.name = "v2.0"
        mock_ms2.self_link = (
            "https://api.launchpad.net/1.0/proj/+milestone/v2.0"
        )

        # Bug 100 is in both milestones
        mock_bug = MagicMock()
        mock_bug.id = 100
        mock_bug.web_link = "https://bugs.launchpad.net/test/+bug/100"
        mock_bug.title = "Shared bug"
        mock_bug.tags = []
        mock_bug.description = "desc"

        mock_task = MagicMock()
        mock_task.status = "Confirmed"
        mock_task.bug = mock_bug

        mock_project = MagicMock()
        mock_project.all_milestones = [mock_ms1, mock_ms2]
        mock_project.searchTasks.return_value = [mock_task]
        mock_launchpad.projects = {"testproj": mock_project}

        results = list(fetch_bugs("testproj", milestones=["v1.0", "v2.0"]))

        # Should be deduplicated to 1 bug even though it appears in both
        assert len(results) == 1
        assert results[0]["id"] == 100
        assert mock_project.searchTasks.call_count == 2

    @patch("slopbox.submission.bugs.Launchpad")
    def test_unknown_milestone_warns(self, mock_launchpad_class, capsys):
        """An unknown milestone prints a warning and skips it."""
        mock_launchpad = MagicMock()
        mock_launchpad_class.login_with.return_value = mock_launchpad

        mock_project = MagicMock()
        mock_project.all_milestones = []
        mock_project.searchTasks.return_value = []
        mock_launchpad.projects = {"testproj": mock_project}

        results = list(fetch_bugs("testproj", milestones=["nonexistent"]))

        assert results == []
        captured = capsys.readouterr()
        assert "nonexistent" in captured.err


class TestRun:
    """Tests for the run() entry point."""

    def _make_args(self, launchpad_project, milestones=None, statuses=None):
        """Build a namespace mimicking argparse output."""
        from argparse import Namespace

        return Namespace(
            launchpad_project=launchpad_project,
            milestones=milestones,
            statuses=statuses,
        )

    @patch("slopbox.submission.bugs.fetch_bugs")
    def test_bugs_printed(self, mock_fetch, capsys):
        """Bug dicts are printed as a single JSON list."""
        mock_fetch.return_value = [
            {
                "id": 1,
                "url": "https://bugs.launchpad.net/test/+bug/1",
                "status": "New",
                "title": "Bug one",
                "tags": [],
                "description": "Desc one",
            },
            {
                "id": 2,
                "url": "https://bugs.launchpad.net/test/+bug/2",
                "status": "Confirmed",
                "title": "Bug two",
                "tags": ["test"],
                "description": "Desc two",
            },
        ]

        args = self._make_args("testproj")
        run(args)

        captured = capsys.readouterr()
        results = json.loads(captured.out)
        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[1]["id"] == 2

    @patch("slopbox.submission.bugs.fetch_bugs")
    def test_no_bugs(self, mock_fetch, capsys):
        """When there are no bugs, an empty JSON list is printed."""
        mock_fetch.return_value = []

        args = self._make_args("testproj")
        run(args)

        captured = capsys.readouterr()
        assert json.loads(captured.out) == []

    @patch("slopbox.submission.bugs.fetch_bugs")
    def test_milestones_passed_through(self, mock_fetch):
        """The --milestones value is split and passed to fetch_bugs."""
        mock_fetch.return_value = []

        args = self._make_args("testproj", milestones="ms1, ms2")
        run(args)

        mock_fetch.assert_called_once_with(
            "testproj",
            milestones=["ms1", "ms2"],
            statuses=None,
        )

    @patch("slopbox.submission.bugs.fetch_bugs")
    def test_statuses_passed_through(self, mock_fetch):
        """The --statuses value is split and passed to fetch_bugs."""
        mock_fetch.return_value = []

        args = self._make_args("testproj", statuses="Fix Released, Invalid")
        run(args)

        mock_fetch.assert_called_once_with(
            "testproj",
            milestones=None,
            statuses=["Fix Released", "Invalid"],
        )
