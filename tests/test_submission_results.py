import json
from unittest.mock import patch

import pytest

from slopbox.submission.results import c3_query, run


class TestC3Query:
    """Tests for c3_query which drives paginated API requests."""

    @patch("slopbox.submission.results.urllib.request.urlopen")
    def test_single_page(self, mock_urlopen):
        """When there is only one page, all results are yielded."""
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            json.dumps(
                {
                    "count": 2,
                    "next": None,
                    "previous": None,
                    "results": [
                        {"id": 1, "testresult_set": []},
                        {"id": 2, "testresult_set": []},
                    ],
                }
            ).encode()
        )

        results = list(c3_query("https://example.com/api/"))

        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[1]["id"] == 2

    @patch("slopbox.submission.results.urllib.request.urlopen")
    def test_pagination(self, mock_urlopen):
        """When there are multiple pages, all results are yielded."""
        page1 = json.dumps(
            {
                "count": 3,
                "next": "https://example.com/api/?page=2",
                "previous": None,
                "results": [{"id": 1, "testresult_set": []}],
            }
        ).encode()
        page2 = json.dumps(
            {
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {"id": 2, "testresult_set": []},
                    {"id": 3, "testresult_set": []},
                ],
            }
        ).encode()

        mock_urlopen.return_value.__enter__.return_value.read.side_effect = [
            page1,
            page2,
        ]

        results = list(c3_query("https://example.com/api/"))

        assert len(results) == 3
        assert [r["id"] for r in results] == [1, 2, 3]
        assert mock_urlopen.call_count == 2

    @patch("slopbox.submission.results.urllib.request.urlopen")
    def test_http_error(self, mock_urlopen):
        """When the API returns an HTTP error, SystemExit is raised."""
        from email.message import Message
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            url="https://example.com/api/",
            code=404,
            msg="Not Found",
            hdrs=Message(),
            fp=None,
        )

        with pytest.raises(SystemExit, match="404"):
            list(c3_query("https://example.com/api/"))


class TestRun:
    """Tests for the run() entry point."""

    @pytest.fixture(autouse=True)
    def _patch_token(self, monkeypatch):
        """Ensure C3_ACCESS_TOKEN is set for all tests in this class."""
        monkeypatch.setattr(
            "slopbox.submission.results.C3_ACCESS_TOKEN",
            "test-token",
        )

    def _make_args(self, submission_id):
        """Build a namespace mimicking argparse output."""
        from argparse import Namespace

        return Namespace(submission_id=submission_id)

    @patch("slopbox.submission.results.c3_query")
    def test_results_printed(self, mock_query, capsys):
        """Test results are printed as JSON lines."""
        mock_query.return_value = [
            {
                "testresult_set": [
                    {"name": "test1", "status": "pass"},
                    {"name": "test2", "status": "fail"},
                ]
            },
            {
                "testresult_set": [
                    {"name": "test3", "status": "skip"},
                ]
            },
        ]

        args = self._make_args("12345")
        run(args)

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert len(lines) == 3
        assert json.loads(lines[0]) == {"name": "test1", "status": "pass"}
        assert json.loads(lines[1]) == {"name": "test2", "status": "fail"}
        assert json.loads(lines[2]) == {"name": "test3", "status": "skip"}

    @patch("slopbox.submission.results.c3_query")
    def test_empty_testresult_set(self, mock_query, capsys):
        """When testresult_set is empty, nothing is printed."""
        mock_query.return_value = [{"testresult_set": []}]

        args = self._make_args("12345")
        run(args)

        captured = capsys.readouterr()
        assert captured.out == ""

    @patch("slopbox.submission.results.c3_query")
    def test_missing_testresult_set(self, mock_query, capsys):
        """When testresult_set key is missing, nothing is printed."""
        mock_query.return_value = [{"id": 1}]

        args = self._make_args("12345")
        run(args)

        captured = capsys.readouterr()
        assert captured.out == ""
