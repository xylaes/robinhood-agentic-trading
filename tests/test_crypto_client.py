import base64
import unittest
from unittest.mock import MagicMock, patch
import httpx

from src.crypto_client import RobinhoodCryptoClient


class TestRobinhoodCryptoClientGetHoldings(unittest.TestCase):

    def setUp(self):
        # 32 bytes valid base64 key
        self.dummy_private_key_b64 = base64.b64encode(b"0" * 32).decode("utf-8")
        self.dummy_api_key = "dummy_api_key"

    def test_get_holdings_unauthenticated_dry_run(self):
        """Test get_holdings returns dry_run data when unauthenticated."""
        client = RobinhoodCryptoClient()
        result = client.get_holdings()

        self.assertEqual(result, {
            "status": "dry_run",
            "results": []
        })

    @patch("src.crypto_client.httpx.Client")
    def test_get_holdings_authenticated_success(self, mock_httpx_client):
        """Test get_holdings when client is authenticated and request succeeds."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "asset_code": "BTC",
                    "quantity": "0.5",
                    "quantity_available_for_trading": "0.5"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.request.return_value = mock_response
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = False
        mock_httpx_client.return_value = mock_client_instance

        client = RobinhoodCryptoClient(
            api_key=self.dummy_api_key,
            private_key_b64=self.dummy_private_key_b64
        )

        result = client.get_holdings()

        self.assertEqual(result, {
            "results": [
                {
                    "asset_code": "BTC",
                    "quantity": "0.5",
                    "quantity_available_for_trading": "0.5"
                }
            ]
        })
        mock_client_instance.request.assert_called_once()
        args, kwargs = mock_client_instance.request.call_args
        self.assertEqual(kwargs.get("method"), "GET")
        self.assertTrue(kwargs.get("url").endswith("/api/v1/crypto/trading/holdings/"))

    @patch("src.crypto_client.httpx.Client")
    def test_get_holdings_http_error(self, mock_httpx_client):
        """Test get_holdings when HTTPStatusError occurs."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        http_error = httpx.HTTPStatusError("401 Unauthorized", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        mock_client_instance = MagicMock()
        mock_client_instance.request.return_value = mock_response
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = False
        mock_httpx_client.return_value = mock_client_instance

        client = RobinhoodCryptoClient(
            api_key=self.dummy_api_key,
            private_key_b64=self.dummy_private_key_b64
        )

        result = client.get_holdings()

        self.assertIn("error", result)
        self.assertEqual(result.get("status_code"), 401)
        self.assertEqual(result.get("detail"), "Unauthorized")

    @patch("src.crypto_client.httpx.Client")
    def test_get_holdings_generic_exception(self, mock_httpx_client):
        """Test get_holdings when a generic exception occurs during request."""
        mock_client_instance = MagicMock()
        mock_client_instance.request.side_effect = Exception("Connection timeout")
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = False
        mock_httpx_client.return_value = mock_client_instance

        client = RobinhoodCryptoClient(
            api_key=self.dummy_api_key,
            private_key_b64=self.dummy_private_key_b64
        )

        result = client.get_holdings()

        self.assertEqual(result, {"error": "Connection timeout"})


if __name__ == "__main__":
    unittest.main()
