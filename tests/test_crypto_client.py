import pytest
from unittest.mock import MagicMock, patch
from src.crypto_client import RobinhoodCryptoClient

def test_get_best_bid_ask_empty_symbols():
    client = RobinhoodCryptoClient()
    result = client.get_best_bid_ask([])
    assert result == {"results": []}

def test_get_best_bid_ask_unauthenticated_success():
    client = RobinhoodCryptoClient()
    assert not client.is_authenticated()

    mock_response_btc = MagicMock()
    mock_response_btc.status_code = 200
    mock_response_btc.json.return_value = {
        "results": [{"symbol": "BTC-USD", "price": "50000"}]
    }

    mock_response_eth = MagicMock()
    mock_response_eth.status_code = 200
    mock_response_eth.json.return_value = {
        "results": [{"symbol": "ETH-USD", "price": "3000"}]
    }

    def mock_get(url, **kwargs):
        if "BTC-USD" in url:
            return mock_response_btc
        elif "ETH-USD" in url:
            return mock_response_eth
        return MagicMock(status_code=404)

    with patch("httpx.Client") as mock_httpx_client_cls:
        mock_client_inst = MagicMock()
        mock_client_inst.get.side_effect = mock_get
        mock_httpx_client_cls.return_value.__enter__.return_value = mock_client_inst

        res = client.get_best_bid_ask(["BTC-USD", "ETH-USD"])

        assert "results" in res
        assert len(res["results"]) == 2
        assert res["results"][0]["symbol"] == "BTC-USD"
        assert res["results"][1]["symbol"] == "ETH-USD"

def test_get_best_bid_ask_authenticated_success():
    client = RobinhoodCryptoClient(api_key="key", private_key_b64="MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE=")
    assert client.is_authenticated()

    def mock_request(method, path, body_dict=None, client=None):
        if "BTC-USD" in path:
            return {"results": [{"symbol": "BTC-USD", "price": "50000"}]}
        elif "ETH-USD" in path:
            return {"results": [{"symbol": "ETH-USD", "price": "3000"}]}
        return {}

    with patch.object(client, "_request", side_effect=mock_request) as mock_req:
        res = client.get_best_bid_ask(["BTC-USD", "ETH-USD"])
        assert len(res["results"]) == 2
        assert res["results"][0]["symbol"] == "BTC-USD"
        assert res["results"][1]["symbol"] == "ETH-USD"
        assert mock_req.call_count == 2
