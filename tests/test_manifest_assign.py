from unittest.mock import patch

import pytest

from slopbox.manifest.assign import run_prompt

MANIFESTS = [
    {"id": "com.canonical.plainbox::has_ethernet_adapter", "name": "Eth"},
    {"id": "com.canonical.plainbox::has_wifi_adapter", "name": "WiFi"},
]

JOB = {
    "id": "com.canonical.plainbox::ethernet/detect",
    "template_id": "",
    "_summary": "Detect ethernet device",
    "command": "network_device_info.py detect NETWORK",
    "description": "Detects ethernet",
}

JOBS = [JOB]


class TestRunPrompt:
    """Tests for run_prompt which drives the LLM classification loop."""

    @patch("slopbox.manifest.assign.query_lm_studio")
    def test_valid_tags_returned(self, mock_query):
        """When the model returns valid manifest ids, they are returned."""
        mock_query.return_value = "has_ethernet_adapter"

        result = run_prompt(MANIFESTS, JOB)

        assert result == ["has_ethernet_adapter"]
        assert mock_query.call_count == 1

    @patch("slopbox.manifest.assign.query_lm_studio")
    def test_hallucinated_manifest_triggers_retry(self, mock_query):
        """When the model returns an invalid tag, it retries."""
        mock_query.side_effect = [
            "has_bluetooth",  # hallucinated
            "has_ethernet_adapter",  # valid
        ]

        result = run_prompt(MANIFESTS, JOB)

        assert result == ["has_ethernet_adapter"]
        assert mock_query.call_count == 2

    @patch("slopbox.manifest.assign.query_lm_studio")
    def test_hallucination_exhausts_retries(self, mock_query):
        """When the model always hallucinates, we raise after 5 attempts."""
        mock_query.return_value = "totally_made_up_tag"

        with pytest.raises(ValueError, match="LLM unable to do it"):
            run_prompt(MANIFESTS, JOB)

        assert mock_query.call_count == 5


class TestRun:
    """Tests for the run() entry point."""

    def _make_args(self, job_id, manifests=None, jobs=None):
        """Build a namespace mimicking argparse output."""
        from argparse import Namespace

        return Namespace(
            manifest_json=manifests,
            job_json=jobs,
            job_id=job_id,
        )

    @patch("slopbox.manifest.assign.run_prompt")
    @patch("slopbox.manifest.assign.checkbox_cli_list")
    def test_job_not_found_raises(self, mock_cli, mock_prompt):
        """When the job_id doesn't match any job, SystemExit is raised."""
        from slopbox.manifest.assign import run

        mock_cli.side_effect = lambda expr: {
            "manifest entry": MANIFESTS,
            "all-jobs": JOBS,
        }[expr]

        args = self._make_args("nonexistent_job_id")

        with pytest.raises(SystemExit, match="not found"):
            run(args)

        mock_prompt.assert_not_called()

    @patch("slopbox.manifest.assign.run_prompt")
    @patch("slopbox.manifest.assign.checkbox_cli_list")
    def test_valid_job_calls_prompt_and_prints(
        self, mock_cli, mock_prompt, capsys
    ):
        """When the job exists, run_prompt is called and results printed."""
        from slopbox.manifest.assign import run

        mock_cli.side_effect = lambda expr: {
            "manifest entry": MANIFESTS,
            "all-jobs": JOBS,
        }[expr]
        mock_prompt.return_value = [
            "has_ethernet_adapter",
            "has_wifi_adapter",
        ]

        args = self._make_args("ethernet/detect")
        run(args)

        mock_prompt.assert_called_once_with(MANIFESTS, JOB)
        captured = capsys.readouterr()
        assert "has_ethernet_adapter" in captured.out
        assert "has_wifi_adapter" in captured.out
