import pytest
from unittest.mock import MagicMock, patch
from src.crypto_client import RobinhoodCryptoClient

def test_get_order_unauthenticated():
    """Test get_order when client is not authenticated (dry_run fallback)."""
    client = RobinhoodCryptoClient()
    order_id = "test-order-123"
    res = client.get_order(order_id)
    assert res == {
        "status": "dry_run",
        "id": order_id,
        "state": "filled"
    }

def test_get_order_authenticated_success():
    """Test get_order when client is authenticated and request succeeds."""
    client = RobinhoodCryptoClient()
    order_id = "test-order-456"

    mock_response = {
        "id": order_id,
        "state": "filled",
        "symbol": "BTC-USD",
        "side": "buy",
        "type": "market"
    }

    with patch.object(client, "is_authenticated", return_value=True), \
         patch.object(client, "_request", return_value=mock_response) as mock_req:
        res = client.get_order(order_id)
        mock_req.assert_called_once_with("GET", f"/api/v1/crypto/trading/orders/{order_id}/")
        assert res == mock_response

def test_get_order_authenticated_error():
    """Test get_order when client is authenticated but API returns an error response."""
    client = RobinhoodCryptoClient()
    order_id = "test-order-error"

    mock_error_response = {
        "error": "Client error: 404 Not Found",
        "status_code": 404,
        "detail": "Order not found"
    }

    with patch.object(client, "is_authenticated", return_value=True), \
         patch.object(client, "_request", return_value=mock_error_response) as mock_req:
        res = client.get_order(order_id)
        mock_req.assert_called_once_with("GET", f"/api/v1/crypto/trading/orders/{order_id}/")
        assert res == mock_error_response
