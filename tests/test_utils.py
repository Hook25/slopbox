import json
from io import BytesIO
from unittest.mock import patch

import pytest

from slopbox.utils import query_openai_endpoint


def _mock_response(body: dict):
    """Return a context-manager-compatible mock for urlopen."""
    return BytesIO(json.dumps(body).encode())


class TestQueryOpenaiEndpointErrors:
    """Tests for error handling in query_openai_endpoint."""

    @patch("slopbox.utils.urllib.request.urlopen")
    def test_api_error_raises_system_exit(self, mock_urlopen):
        """When the response contains an 'error' key, SystemExit is raised."""
        mock_urlopen.return_value.__enter__ = lambda s: _mock_response(
            {"error": "rate limit exceeded"}
        )
        mock_urlopen.return_value.__exit__ = lambda *a: False

        with pytest.raises(SystemExit, match="rate limit exceeded"):
            query_openai_endpoint("hello")

    @patch("slopbox.utils.urllib.request.urlopen")
    def test_missing_choices_raises_system_exit(self, mock_urlopen):
        """When the response lacks a 'choices' key, SystemExit is raised."""
        mock_urlopen.return_value.__enter__ = lambda s: _mock_response(
            {"id": "abc", "object": "chat.completion"}
        )
        mock_urlopen.return_value.__exit__ = lambda *a: False

        with pytest.raises(SystemExit, match="missing 'choices' key"):
            query_openai_endpoint("hello")

    @patch("slopbox.utils.urllib.request.urlopen")
    def test_connection_error_raises_system_exit(self, mock_urlopen):
        """When connection is refused, a clear SystemExit is raised."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        with pytest.raises(SystemExit, match="Could not connect"):
            query_openai_endpoint("hello")
