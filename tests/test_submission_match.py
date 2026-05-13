import json
from unittest.mock import patch

import pytest

from slopbox.submission.match import (
    fetch_failed_results,
    register_parser,
    repr_bug,
    run,
    run_match,
)


class TestFetchFailedResults:
    """Tests for fetch_failed_results which filters C3 data."""

    @patch("slopbox.submission.match.results_mod.c3_query")
    def test_only_failed_returned(self, mock_c3_query):
        """Only test results with status 'fail' are yielded."""
        mock_c3_query.return_value = [
            {
                "testresult_set": [
                    {"name": "t1", "status": "pass"},
                    {"name": "t2", "status": "fail"},
                    {"name": "t3", "status": "skip"},
                    {"name": "t4", "status": "fail"},
                ]
            }
        ]

        with patch("slopbox.submission.match.C3_ACCESS_TOKEN", "test-token"):
            results = list(fetch_failed_results("12345"))

        assert len(results) == 2
        assert results[0]["name"] == "t2"
        assert results[1]["name"] == "t4"

    @patch("slopbox.submission.match.results_mod.c3_query")
    def test_no_failed(self, mock_c3_query):
        """When no tests failed, nothing is yielded."""
        mock_c3_query.return_value = [
            {
                "testresult_set": [
                    {"name": "t1", "status": "pass"},
                    {"name": "t2", "status": "skip"},
                ]
            }
        ]

        with patch("slopbox.submission.match.C3_ACCESS_TOKEN", "test-token"):
            results = list(fetch_failed_results("12345"))

        assert results == []

    def test_missing_token(self):
        """When C3_ACCESS_TOKEN is missing, SystemExit is raised."""
        with (
            patch("slopbox.submission.match.C3_ACCESS_TOKEN", None),
            pytest.raises(SystemExit, match="C3_ACCESS_TOKEN"),
        ):
            list(fetch_failed_results("12345"))


class TestReprBug:
    """Tests for repr_bug formatting."""

    def test_with_tags(self):
        bug = {"id": 123, "title": "A bug", "tags": ["tag1", "tag2"]}
        assert repr_bug(bug) == "- 123: A bug (tags: tag1, tag2)"

    def test_without_tags(self):
        bug = {"id": 456, "title": "No tags", "tags": []}
        assert repr_bug(bug) == "- 456: No tags (tags: none)"


class TestRunMatch:
    """Tests for run_match which drives the LLM matching loop."""

    @patch("slopbox.submission.match.query_openai_endpoint")
    def test_valid_bug_ids(self, mock_query):
        """When the model returns valid bug IDs, they are returned."""
        mock_query.return_value = "123, 456"

        bug_dicts = [
            {"id": 123, "title": "B1", "tags": []},
            {"id": 456, "title": "B2", "tags": []},
            {"id": 789, "title": "B3", "tags": []},
        ]
        test = {"name": "t1", "status": "fail", "comment": "c1"}

        result = run_match(test, bug_dicts)

        assert result == [123, 456]
        assert mock_query.call_count == 1

    @patch("slopbox.submission.match.query_openai_endpoint")
    def test_none_means_empty(self, mock_query):
        """When the model returns 'none', an empty list is returned."""
        mock_query.return_value = "none"

        bug_dicts = [{"id": 123, "title": "B1", "tags": []}]
        test = {"name": "t1", "status": "fail", "comment": "c1"}

        result = run_match(test, bug_dicts)

        assert result == []

    @patch("slopbox.submission.match.query_openai_endpoint")
    def test_hallucinated_id_triggers_retry(self, mock_query):
        """When the model returns an invalid bug ID, it retries."""
        mock_query.side_effect = ["99999", "123"]

        bug_dicts = [{"id": 123, "title": "B1", "tags": []}]
        test = {"name": "t1", "status": "fail", "comment": "c1"}

        result = run_match(test, bug_dicts)

        assert result == [123]
        assert mock_query.call_count == 2

    @patch("slopbox.submission.match.query_openai_endpoint")
    def test_hallucination_exhausts_retries(self, mock_query):
        """When the model always hallucinates, we raise after 5 attempts."""
        mock_query.return_value = "totally_made_up"

        bug_dicts = [{"id": 123, "title": "B1", "tags": []}]
        test = {"name": "t1", "status": "fail", "comment": "c1"}

        with pytest.raises(ValueError, match="LLM unable"):
            run_match(test, bug_dicts)

        assert mock_query.call_count == 5


class TestRun:
    """Tests for the run() entry point."""

    def _make_args(
        self, submission_id, project, milestones=None, statuses=None
    ):
        """Build a namespace mimicking argparse output."""
        from argparse import Namespace

        return Namespace(
            submission_id=submission_id,
            launchpad_project=project,
            milestones=milestones,
            statuses=statuses,
        )

    @patch("slopbox.submission.match.run_match")
    @patch("slopbox.submission.match.bugs_mod.fetch_bugs")
    @patch("slopbox.submission.match.fetch_failed_results")
    def test_end_to_end(
        self, mock_fetch_results, mock_fetch_bugs, mock_match, capsys
    ):
        """Failed tests are fetched, matched to bugs, and printed."""
        mock_fetch_results.return_value = [
            {"name": "t1", "status": "fail"},
            {"name": "t2", "status": "fail"},
        ]
        mock_fetch_bugs.return_value = [
            {"id": 1, "title": "B1", "tags": []},
        ]
        mock_match.side_effect = [[1], []]

        args = self._make_args("12345", "proj")
        with patch("slopbox.submission.match.C3_ACCESS_TOKEN", "test-token"):
            run(args)

        captured = capsys.readouterr()
        results = json.loads(captured.out)
        assert len(results) == 2
        assert results[0]["bugs"] == [1]
        assert results[1]["bugs"] == []

    @patch("slopbox.submission.match.bugs_mod.fetch_bugs")
    @patch("slopbox.submission.match.fetch_failed_results")
    def test_no_failed_tests(
        self, mock_fetch_results, mock_fetch_bugs, capsys
    ):
        """When there are no failed tests, an empty list is printed."""
        mock_fetch_results.return_value = []

        args = self._make_args("12345", "proj")
        with patch("slopbox.submission.match.C3_ACCESS_TOKEN", "test-token"):
            run(args)

        captured = capsys.readouterr()
        assert json.loads(captured.out) == []
        mock_fetch_bugs.assert_not_called()

    @patch("slopbox.submission.match.bugs_mod.fetch_bugs")
    @patch("slopbox.submission.match.fetch_failed_results")
    def test_no_bugs(self, mock_fetch_results, mock_fetch_bugs, capsys):
        """When there are no bugs, an empty list is printed."""
        mock_fetch_results.return_value = [{"name": "t1", "status": "fail"}]
        mock_fetch_bugs.return_value = []

        args = self._make_args("12345", "proj")
        with patch("slopbox.submission.match.C3_ACCESS_TOKEN", "test-token"):
            run(args)

        captured = capsys.readouterr()
        assert json.loads(captured.out) == []

    @patch("slopbox.submission.match.bugs_mod.fetch_bugs")
    @patch("slopbox.submission.match.fetch_failed_results")
    def test_statuses_passed_through(
        self, mock_fetch_results, mock_fetch_bugs, capsys
    ):
        """The --statuses value is split and passed to fetch_bugs."""
        mock_fetch_results.return_value = [{"name": "t1", "status": "fail"}]
        mock_fetch_bugs.return_value = []

        args = self._make_args(
            "12345", "proj", statuses="Fix Released, Invalid"
        )
        with patch("slopbox.submission.match.C3_ACCESS_TOKEN", "test-token"):
            run(args)

        mock_fetch_bugs.assert_called_once_with(
            "proj", milestones=None, statuses=["Fix Released", "Invalid"]
        )

    def test_parser(self, capsys):
        """The parser registers correctly with required args."""
        import argparse

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        register_parser(sub)
        args = parser.parse_args(
            ["match", "123", "proj", "--statuses", "Fix Released"]
        )
        assert args.submission_id == "123"
        assert args.launchpad_project == "proj"
        assert args.statuses == "Fix Released"
