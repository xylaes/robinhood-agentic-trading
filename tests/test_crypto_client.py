import base64
import pytest
from src.crypto_client import RobinhoodCryptoClient, HAS_CRYPTOGRAPHY

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
except ImportError:
    ed25519 = None


@pytest.fixture(autouse=True)
def clear_env_vars(monkeypatch):
    """Ensure environment variables do not interfere with tests."""
    monkeypatch.delenv("ROBINHOOD_CRYPTO_API_KEY", raising=False)
    monkeypatch.delenv("ROBINHOOD_CRYPTO_PRIVATE_KEY", raising=False)


def test_is_authenticated_no_credentials():
    """Returns False when no credentials are provided."""
    client = RobinhoodCryptoClient()
    assert client.is_authenticated() is False


def test_is_authenticated_only_api_key():
    """Returns False when only API key is provided."""
    client = RobinhoodCryptoClient(api_key="test_api_key")
    assert client.is_authenticated() is False


def test_is_authenticated_only_private_key():
    """Returns False when only Private key is provided."""
    b64_32 = base64.b64encode(b"0" * 32).decode("utf-8")
    client = RobinhoodCryptoClient(private_key_b64=b64_32)
    assert client.is_authenticated() is False


def test_is_authenticated_invalid_key_length():
    """Returns False when private key is not 32 or 64 bytes when base64 decoded."""
    # 16 bytes base64 encoded
    invalid_b64 = base64.b64encode(b"0123456789abcdef").decode("utf-8")
    client = RobinhoodCryptoClient(api_key="test_api_key", private_key_b64=invalid_b64)
    assert client.is_authenticated() is False


def test_is_authenticated_invalid_base64():
    """Returns False when private key is invalid base64."""
    client = RobinhoodCryptoClient(api_key="test_api_key", private_key_b64="!!!invalid_base64!!!")
    assert client.is_authenticated() is False


def test_is_authenticated_without_cryptography_module(monkeypatch):
    """Returns False when HAS_CRYPTOGRAPHY is False."""
    b64_32 = base64.b64encode(b"0" * 32).decode("utf-8")
    monkeypatch.setattr("src.crypto_client.HAS_CRYPTOGRAPHY", False)
    client = RobinhoodCryptoClient(api_key="test_api_key", private_key_b64=b64_32)
    assert client.is_authenticated() is False


@pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography package is not installed")
def test_is_authenticated_valid_32_byte_key():
    """Returns True when valid API key and 32-byte private key are provided."""
    priv_key = ed25519.Ed25519PrivateKey.generate()
    raw_32 = priv_key.private_bytes_raw()
    b64_32 = base64.b64encode(raw_32).decode("utf-8")

    client = RobinhoodCryptoClient(api_key="test_api_key", private_key_b64=b64_32)
    assert client.is_authenticated() is True


@pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography package is not installed")
def test_is_authenticated_valid_64_byte_key():
    """Returns True when valid API key and 64-byte private key (seed + pub key) are provided."""
    priv_key = ed25519.Ed25519PrivateKey.generate()
    raw_32 = priv_key.private_bytes_raw()
    raw_64 = raw_32 + b"0" * 32
    b64_64 = base64.b64encode(raw_64).decode("utf-8")

    client = RobinhoodCryptoClient(api_key="test_api_key", private_key_b64=b64_64)
    assert client.is_authenticated() is True


@pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography package is not installed")
def test_is_authenticated_from_env_vars(monkeypatch):
    """Returns True when valid credentials are set via environment variables."""
    priv_key = ed25519.Ed25519PrivateKey.generate()
    raw_32 = priv_key.private_bytes_raw()
    b64_32 = base64.b64encode(raw_32).decode("utf-8")

    monkeypatch.setenv("ROBINHOOD_CRYPTO_API_KEY", "env_api_key")
    monkeypatch.setenv("ROBINHOOD_CRYPTO_PRIVATE_KEY", b64_32)

    client = RobinhoodCryptoClient()
    assert client.is_authenticated() is True


def test_is_authenticated_with_mocked_private_key():
    """Tests is_authenticated returning True with mocked cryptography / private key loading."""
    b64_32 = base64.b64encode(b"0" * 32).decode("utf-8")
    client = RobinhoodCryptoClient(api_key="test_api_key", private_key_b64=b64_32)

    # Manually assign mock _private_key to verify is_authenticated logic
    client._private_key = object()
    assert client.is_authenticated() is True
