import base64
import time
import pytest
from unittest.mock import patch, MagicMock
from cryptography.hazmat.primitives.asymmetric import ed25519
import httpx

from src.crypto_client import RobinhoodCryptoClient, HAS_CRYPTOGRAPHY


@pytest.fixture
def keypair():
    """Generates a fresh Ed25519 private key and public key pair for testing."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    raw_private_bytes = private_key.private_bytes_raw()
    b64_private_key = base64.b64encode(raw_private_bytes).decode("utf-8")
    public_key = private_key.public_key()
    return private_key, public_key, b64_private_key


def test_generate_headers_unauthenticated():
    """Verify that _generate_headers returns an empty dict if the client is unauthenticated."""
    client = RobinhoodCryptoClient()
    assert not client.is_authenticated()
    headers = client._generate_headers("GET", "/api/v1/crypto/trading/accounts/")
    assert headers == {}


def test_generate_headers_authenticated(keypair):
    """Verify that _generate_headers produces expected header structure and valid Ed25519 signature."""
    _, public_key, b64_private_key = keypair
    api_key = "test_api_key_123"

    client = RobinhoodCryptoClient(
        api_key=api_key,
        private_key_b64=b64_private_key
    )
    assert client.is_authenticated()

    method = "post"
    path = "/api/v1/crypto/trading/orders/"
    body = '{"symbol":"BTC-USD","side":"buy"}'

    test_timestamp = 1700000000
    with patch("time.time", return_value=test_timestamp):
        headers = client._generate_headers(method, path, body)

    # Check required headers exist
    assert headers["x-api-key"] == api_key
    assert headers["x-timestamp"] == str(test_timestamp)
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"
    assert "x-signature" in headers

    # Verify signature algorithm & content match specifications
    expected_message = f"{api_key}{test_timestamp}{path}POST{body}"
    signature_bytes = base64.b64decode(headers["x-signature"])

    # This should not raise an InvalidSignature exception
    public_key.verify(signature_bytes, expected_message.encode("utf-8"))


def test_generate_headers_64byte_key():
    """Verify that 64-byte raw keys (e.g. key + public key extension) are truncated to 32 bytes and work properly."""
    raw_key_32 = ed25519.Ed25519PrivateKey.generate().private_bytes_raw()
    raw_key_64 = raw_key_32 + b"\x00" * 32  # pad to 64 bytes
    b64_key_64 = base64.b64encode(raw_key_64).decode("utf-8")

    client = RobinhoodCryptoClient(api_key="key", private_key_b64=b64_key_64)
    assert client.is_authenticated()

    headers = client._generate_headers("GET", "/test")
    assert "x-signature" in headers


def test_invalid_private_key_initialization(caplog):
    """Verify that invalid private key length or bad base64 handles exceptions gracefully."""
    # Invalid length (e.g. 10 bytes)
    short_key_b64 = base64.b64encode(b"1234567890").decode("utf-8")
    client = RobinhoodCryptoClient(api_key="key", private_key_b64=short_key_b64)
    assert not client.is_authenticated()

    # Invalid Base64 string
    client2 = RobinhoodCryptoClient(api_key="key", private_key_b64="!!!not_base64!!!")
    assert not client2.is_authenticated()


def test_generate_headers_method_normalization(keypair):
    """Verify that HTTP method is always converted to uppercase in signature message construction."""
    _, public_key, b64_private_key = keypair
    api_key = "test_key"
    client = RobinhoodCryptoClient(api_key=api_key, private_key_b64=b64_private_key)

    test_timestamp = 1700000000
    with patch("time.time", return_value=test_timestamp):
        headers_lower = client._generate_headers("get", "/api/v1/test", "")
        headers_upper = client._generate_headers("GET", "/api/v1/test", "")

    assert headers_lower["x-signature"] == headers_upper["x-signature"]


def test_request_uses_generated_headers(keypair):
    """Verify that _request method attaches generated headers to httpx request."""
    _, _, b64_private_key = keypair
    client = RobinhoodCryptoClient(api_key="test_api_key", private_key_b64=b64_private_key)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": "success"}

    mock_httpx_client = MagicMock()
    mock_httpx_client.request.return_value = mock_response

    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value = mock_httpx_client
        res = client._request("POST", "/api/v1/crypto/trading/orders/", {"symbol": "BTC-USD"})

        assert res == {"results": "success"}
        mock_httpx_client.request.assert_called_once()
        kwargs = mock_httpx_client.request.call_args.kwargs

        headers = kwargs["headers"]
        assert headers["x-api-key"] == "test_api_key"
        assert "x-signature" in headers
        assert kwargs["method"] == "POST"
