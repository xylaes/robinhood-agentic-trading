import base64
from unittest.mock import MagicMock, patch
import httpx
import pytest

from src.crypto_client import RobinhoodCryptoClient

# 32 zero bytes base64 encoded as a valid test Ed25519 private key
TEST_API_KEY = "test_api_key_123"
TEST_PRIVATE_KEY_B64 = base64.b64encode(b"\x00" * 32).decode("utf-8")


def test_get_account_unauthenticated():
    """Test get_account when client is unauthenticated (returns simulated dry-run dictionary)."""
    client = RobinhoodCryptoClient(api_key=None, private_key_b64=None)
    assert not client.is_authenticated()

    result = client.get_account()
    assert result == {
        "status": "dry_run",
        "account_number": "SIMULATED_CRYPTO_ACC",
        "buying_power": "50.00",
        "currency_code": "USD",
    }


def test_get_account_authenticated_success():
    """Test get_account when authenticated and API returns 200 OK."""
    client = RobinhoodCryptoClient(
        api_key=TEST_API_KEY, private_key_b64=TEST_PRIVATE_KEY_B64
    )
    assert client.is_authenticated()

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "account_number": "RH12345678",
        "buying_power": "1500.50",
        "currency_code": "USD",
        "status": "active",
    }

    with patch.object(httpx.Client, "request", return_value=mock_response) as mock_request:
        result = client.get_account()

    assert result == {
        "account_number": "RH12345678",
        "buying_power": "1500.50",
        "currency_code": "USD",
        "status": "active",
    }
    mock_request.assert_called_once()
    call_kwargs = mock_request.call_args.kwargs
    assert call_kwargs["method"] == "GET"
    assert call_kwargs["url"] == "https://trading.robinhood.com/api/v1/crypto/trading/accounts/"


def test_get_account_http_error():
    """Test get_account when API request raises HTTPStatusError."""
    client = RobinhoodCryptoClient(
        api_key=TEST_API_KEY, private_key_b64=TEST_PRIVATE_KEY_B64
    )

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = '{"detail": "Invalid signature"}'

    http_error = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=mock_response,
    )

    with patch.object(httpx.Client, "request", side_effect=http_error):
        result = client.get_account()

    assert result == {
        "error": "401 Unauthorized",
        "status_code": 401,
        "detail": '{"detail": "Invalid signature"}',
    }


def test_get_account_exception():
    """Test get_account when API request raises generic Exception."""
    client = RobinhoodCryptoClient(
        api_key=TEST_API_KEY, private_key_b64=TEST_PRIVATE_KEY_B64
    )

    with patch.object(httpx.Client, "request", side_effect=Exception("Connection timed out")):
        result = client.get_account()

    assert result == {"error": "Connection timed out"}
