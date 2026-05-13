import json
from argparse import Namespace
from unittest.mock import patch

import pytest

from slopbox.manifest.generate import (
    parse_llm_response,
    run_prompt,
)

JOB = {
    "id": "com.canonical.plainbox::ethernet/detect",
    "template_id": "",
    "_summary": "Detect ethernet device",
    "command": "network_device_info.py detect NETWORK",
    "description": "Detects ethernet",
}

JOBS = [JOB]


class TestParseLlmResponse:
    """Tests for parse_llm_response."""

    def test_empty_dict_means_no_features(self):
        assert parse_llm_response("{}") == {}

    def test_single_feature(self):
        raw = json.dumps({"has_ethernet_adapter": "Machine has ethernet"})
        result = parse_llm_response(raw)
        assert result == {
            "has_ethernet_adapter": "Machine has ethernet",
        }

    def test_multiple_features(self):
        raw = json.dumps(
            {
                "has_wifi_adapter": "Machine has wifi",
                "has_wifi6": "Machine supports wifi 6",
            }
        )
        result = parse_llm_response(raw)
        assert result == {
            "has_wifi_adapter": "Machine has wifi",
            "has_wifi6": "Machine supports wifi 6",
        }

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_llm_response("not valid json {{{")

    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="JSON object"):
            parse_llm_response('["a list"]')


class TestRunPrompt:
    """Tests for run_prompt which drives the LLM generation."""

    @patch("slopbox.manifest.generate.query_openai_endpoint")
    def test_returns_empty_when_no_feature_needed(self, mock_query):
        mock_query.return_value = "{}"

        result = run_prompt(JOB)

        assert result == {}
        assert mock_query.call_count == 1

    @patch("slopbox.manifest.generate.query_openai_endpoint")
    def test_returns_generated_features(self, mock_query):
        mock_query.return_value = json.dumps(
            {"has_ethernet_adapter": "Machine has ethernet"}
        )

        result = run_prompt(JOB)

        assert result == {
            "has_ethernet_adapter": "Machine has ethernet",
        }
        assert mock_query.call_count == 1

    @patch("slopbox.manifest.generate.query_openai_endpoint")
    def test_retries_on_bad_output(self, mock_query):
        mock_query.side_effect = [
            "not json at all",
            json.dumps(
                {
                    "has_ethernet_adapter": ("Machine has ethernet"),
                }
            ),
        ]

        result = run_prompt(JOB)

        assert result == {
            "has_ethernet_adapter": "Machine has ethernet",
        }
        assert mock_query.call_count == 2

    @patch("slopbox.manifest.generate.query_openai_endpoint")
    def test_exhausts_retries(self, mock_query):
        mock_query.return_value = "always bad output"

        with pytest.raises(ValueError, match="LLM unable to generate"):
            run_prompt(JOB)

        assert mock_query.call_count == 5


class TestRun:
    """Tests for the run() entry point."""

    def _make_args(self, job_id, jobs=None):
        return Namespace(
            job_json=jobs,
            job_id=job_id,
        )

    @patch("slopbox.manifest.generate.run_prompt")
    @patch("slopbox.manifest.generate.checkbox_cli_list")
    def test_job_not_found_raises(self, mock_cli, mock_prompt):
        from slopbox.manifest.generate import run

        mock_cli.return_value = JOBS

        args = self._make_args("nonexistent_job_id")

        with pytest.raises(SystemExit, match="not found"):
            run(args)

        mock_prompt.assert_not_called()

    @patch("slopbox.manifest.generate.run_prompt")
    @patch("slopbox.manifest.generate.checkbox_cli_list")
    def test_features_found(self, mock_cli, mock_prompt, capsys):
        from slopbox.manifest.generate import run

        mock_cli.return_value = JOBS
        mock_prompt.return_value = {
            "has_ethernet_adapter": "Machine has ethernet",
            "has_gigabit": "Machine supports gigabit",
        }

        args = self._make_args("ethernet/detect")
        run(args)

        mock_prompt.assert_called_once_with(JOB)
        captured = capsys.readouterr()
        assert "has_ethernet_adapter" in captured.out
        assert "has_gigabit" in captured.out

    @patch("slopbox.manifest.generate.run_prompt")
    @patch("slopbox.manifest.generate.checkbox_cli_list")
    def test_no_feature_needed(self, mock_cli, mock_prompt, capsys):
        from slopbox.manifest.generate import run

        mock_cli.return_value = JOBS
        mock_prompt.return_value = {}

        args = self._make_args("ethernet/detect")
        run(args)

        captured = capsys.readouterr()
        assert "No feature needed" in captured.out
