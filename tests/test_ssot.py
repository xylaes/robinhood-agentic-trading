import subprocess
from unittest.mock import patch, MagicMock
import pytest
from src.ssot import GitHubSourceOfTruth

def test_verify_alignment_success():
    """Test verify_alignment when git commands execute successfully."""
    def mock_subprocess_run(cmd, capture_output, text, check):
        mock_res = MagicMock()
        if cmd == ["git", "rev-parse", "HEAD"]:
            mock_res.stdout = "1234567890abcdef1234567890abcdef12345678\n"
        elif cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            mock_res.stdout = "main\n"
        else:
            mock_res.stdout = ""
        return mock_res

    with patch("src.ssot.subprocess.run", side_effect=mock_subprocess_run) as mock_run:
        res = GitHubSourceOfTruth.verify_alignment()

        assert res == {
            "aligned": True,
            "branch": "main",
            "commit": "1234567890abcdef1234567890abcdef12345678",
            "repository": "https://github.com/xylaes/robinhood-agentic-trading.git"
        }
        assert mock_run.call_count == 2


def test_verify_alignment_failure():
    """Test verify_alignment when git command fails with exception."""
    error_msg = "git command failed"
    with patch("src.ssot.subprocess.run", side_effect=subprocess.CalledProcessError(1, ["git", "rev-parse", "HEAD"], stderr=error_msg)) as mock_run:
        res = GitHubSourceOfTruth.verify_alignment()

        assert res["aligned"] is False
        assert "Command" in res["error"]
        assert res["repository"] == "https://github.com/xylaes/robinhood-agentic-trading.git"
        mock_run.assert_called_once()
