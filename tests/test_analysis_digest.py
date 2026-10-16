import os
import pytest
from src.analysis_digest import PortfolioDigestGenerator


def test_generate_digest_happy_path(tmp_path):
    """Test digest generation with a complete results dictionary."""
    results = {
        "timestamp": "2025-01-01T12:00:00Z",
        "account_number": "12345678",
        "portfolio": {
            "data": {
                "total_value": 1500.50,
                "cash": 500.25,
                "buying_power": {"buying_power": 450.00},
                "equity_value": 1000.25,
            }
        },
        "risk_and_rebalance": {
            "current_allocations_pct": {
                "equities": 66.66,
                "options": 0.0,
                "crypto": 0.0,
                "cash": 33.34,
            },
            "allocation_drifts_pct": {
                "equities": 33.33,
                "options": -33.33,
                "crypto": -33.33,
            },
            "dynamic_scaling_parameters": {
                "scaled_stock_order_size": 15.00,
                "scaled_max_option_premium": 50.00,
                "scaled_crypto_order_size": 15.00,
            },
            "rebalance_actions": [
                "Buy $10.00 SPY equity to rebalance.",
                "Deposit additional cash sweep reserve.",
            ],
        },
        "github_ssot": {
            "commit": "abcdef1234567890",
            "branch": "feature/testing",
        },
    }

    output_file = str(tmp_path / "PORTFOLIO_ANALYSIS_TEST.md")
    digest = PortfolioDigestGenerator.generate_digest(results, output_file=output_file)

    # Check returned content
    assert "`5678`" in digest
    assert "`feature/testing` (`abcdef12`)" in digest
    assert "$1500.50" in digest
    assert "$500.25" in digest
    assert "$450.00" in digest
    assert "$1000.25" in digest
    assert "66.66%" in digest
    assert "+33.33%" in digest
    assert "$15.00" in digest
    assert "$50.00" in digest
    assert "- Buy $10.00 SPY equity to rebalance." in digest
    assert "- Deposit additional cash sweep reserve." in digest

    # Verify file was written properly
    assert os.path.exists(output_file)
    with open(output_file, "r", encoding="utf-8") as f:
        file_content = f.read()
    assert file_content == digest


def test_generate_digest_missing_and_empty_fields(tmp_path):
    """Test digest generation when results dictionary is empty or contains None values."""
    results = {}
    output_file = str(tmp_path / "PORTFOLIO_ANALYSIS_EMPTY.md")
    digest = PortfolioDigestGenerator.generate_digest(results, output_file=output_file)

    # Check fallbacks
    assert "`ount`" in digest  # "AgenticAccount"[-4:] -> "ount"
    assert "`main` (`N/A`)" in digest
    assert "$0.00" in digest
    assert "0.00%" in digest
    assert "$9.98" in digest
    assert "$34.92" in digest

    assert os.path.exists(output_file)


def test_generate_digest_fallback_total_value_from_equity(tmp_path):
    """Test that total_value falls back to equity when total_value is 0 or None."""
    results = {
        "portfolio": {
            "data": {
                "total_value": None,
                "equity": 250.75,
                "cash": None,
                "buying_power": None,
                "equity_value": None,
            }
        }
    }
    output_file = str(tmp_path / "PORTFOLIO_ANALYSIS_FALLBACK.md")
    digest = PortfolioDigestGenerator.generate_digest(results, output_file=output_file)

    assert "$250.75" in digest
    assert os.path.exists(output_file)


def test_generate_digest_default_filename(tmp_path, monkeypatch):
    """Test generating digest using default output filename."""
    monkeypatch.chdir(tmp_path)
    results = {"account_number": "ACC9999"}
    digest = PortfolioDigestGenerator.generate_digest(results)

    default_file = tmp_path / "PORTFOLIO_ANALYSIS.md"
    assert default_file.exists()
    assert default_file.read_text(encoding="utf-8") == digest
