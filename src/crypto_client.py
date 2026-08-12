"""
Robinhood Crypto Trading API Client.

Provides direct access to Robinhood's official Crypto Trading REST API
(https://trading.robinhood.com/api/v1/crypto/) using API Key + Ed25519 signature authentication.

Supports dry-run fallback when credentials are not configured or explicitly disabled.
"""

import os
import time
import json
import base64
import uuid
import logging
import httpx
from typing import Optional, Dict, Any, List

logger = logging.getLogger("robinhood_crypto_client")

# Optional cryptography import for Ed25519 signature generation
try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class RobinhoodCryptoClient:
    BASE_URL = "https://trading.robinhood.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        private_key_b64: Optional[str] = None,
        dry_run: bool = False
    ):
        self.api_key = api_key or os.getenv("ROBINHOOD_CRYPTO_API_KEY")
        self.private_key_b64 = private_key_b64 or os.getenv("ROBINHOOD_CRYPTO_PRIVATE_KEY")
        self.dry_run = dry_run
        self._private_key = None

        if self.api_key and self.private_key_b64 and HAS_CRYPTOGRAPHY:
            try:
                raw_key = base64.b64decode(self.private_key_b64)
                if len(raw_key) == 32:
                    self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_key)
                elif len(raw_key) == 64:
                    self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_key[:32])
                else:
                    logger.warning("Robinhood Crypto private key must be 32 or 64 bytes base64 decoded.")
            except Exception as e:
                logger.error(f"Failed to load Robinhood Crypto Ed25519 private key: {e}")

    def is_authenticated(self) -> bool:
        """Returns True if valid API Key and Private Key are configured."""
        return bool(self.api_key and self._private_key)

    def _generate_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Generates required authentication headers for Robinhood Crypto API requests."""
        if not self.is_authenticated():
            return {}

        timestamp = str(int(time.time()))
        message = f"{self.api_key}{timestamp}{path}{method.upper()}{body}"
        signature_bytes = self._private_key.sign(message.encode("utf-8"))
        signature_b64 = base64.b64encode(signature_bytes).decode("utf-8")

        return {
            "x-api-key": self.api_key,
            "x-signature": signature_b64,
            "x-timestamp": timestamp,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _request(self, method: str, path: str, body_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes signed HTTP request to Robinhood Crypto API."""
        if not self.is_authenticated():
            return {
                "error": "Authentication not configured. Please set ROBINHOOD_CRYPTO_API_KEY and ROBINHOOD_CRYPTO_PRIVATE_KEY.",
                "status": "unauthenticated"
            }

        url = f"{self.BASE_URL}{path}"
        body_str = json.dumps(body_dict) if body_dict else ""
        headers = self._generate_headers(method, path, body_str)

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    content=body_str if body_str else None
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Robinhood Crypto API HTTP Error {e.response.status_code}: {e.response.text}")
            return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.text}
        except Exception as e:
            logger.error(f"Robinhood Crypto API Client error: {e}")
            return {"error": str(e)}

    def get_account(self) -> Dict[str, Any]:
        """Queries Robinhood Crypto trading account status and buying power."""
        if not self.is_authenticated():
            return {
                "status": "dry_run",
                "account_number": "SIMULATED_CRYPTO_ACC",
                "buying_power": "50.00",
                "currency_code": "USD"
            }
        return self._request("GET", "/api/v1/crypto/trading/accounts/")

    def get_holdings(self) -> Dict[str, Any]:
        """Queries active crypto asset holdings."""
        if not self.is_authenticated():
            return {
                "status": "dry_run",
                "results": []
            }
        return self._request("GET", "/api/v1/crypto/trading/holdings/")

    def get_best_bid_ask(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetches best bid and ask quotes for crypto symbols (e.g. ['BTC-USD', 'ETH-USD'])."""
        results = []
        for symbol in symbols:
            path = f"/api/v1/crypto/marketdata/best_bid_ask/?symbol={symbol.upper()}"
            if not self.is_authenticated():
                try:
                    with httpx.Client(timeout=5.0) as client:
                        res = client.get(f"{self.BASE_URL}{path}")
                        if res.status_code == 200:
                            data = res.json()
                            if "results" in data:
                                results.extend(data["results"])
                except Exception as e:
                    logger.warning(f"Public crypto quote fetch warning for {symbol}: {e}")
            else:
                data = self._request("GET", path)
                if isinstance(data, dict) and "results" in data:
                    results.extend(data["results"])

        return {"results": results}


    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str = "market",
        dollar_amount: Optional[float] = None,
        asset_quantity: Optional[float] = None,
        limit_price: Optional[float] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Places a market or limit order via Robinhood Crypto API.
        
        Args:
            symbol: Pair ticker, e.g. "BTC-USD"
            side: "buy" or "sell"
            order_type: "market" or "limit"
            dollar_amount: Order amount in USD (market orders)
            asset_quantity: Quantity of crypto asset
            limit_price: Limit price for limit orders
            dry_run: If True, simulates order creation without sending to Robinhood
        """
        order_id = str(uuid.uuid4())
        payload = {
            "client_order_id": order_id,
            "side": side.lower(),
            "type": order_type.lower(),
            "symbol": symbol.upper()
        }

        if order_type.lower() == "market":
            config = {}
            if dollar_amount is not None:
                config["dollar_amount"] = f"{dollar_amount:.2f}"
            elif asset_quantity is not None:
                config["asset_quantity"] = f"{asset_quantity:.8f}"
            payload["market_order_config"] = config
        elif order_type.lower() == "limit":
            config = {
                "time_in_force": "gtc"
            }
            if asset_quantity is not None:
                config["asset_quantity"] = f"{asset_quantity:.8f}"
            if limit_price is not None:
                config["limit_price"] = f"{limit_price:.2f}"
            payload["limit_order_config"] = config

        if dry_run or self.dry_run or not self.is_authenticated():
            logger.info(f"[CRYPTO SIMULATION] {side.upper()} {symbol} | Type: {order_type} | USD: ${dollar_amount} | Qty: {asset_quantity}")
            return {
                "status": "simulated",
                "id": order_id,
                "client_order_id": order_id,
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "state": "unconfirmed",
                "dollar_amount": dollar_amount,
                "asset_quantity": asset_quantity,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

        return self._request("POST", "/api/v1/crypto/trading/orders/", body_dict=payload)

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Fetches status of a crypto order by ID."""
        if not self.is_authenticated():
            return {"status": "dry_run", "id": order_id, "state": "filled"}
        return self._request("GET", f"/api/v1/crypto/trading/orders/{order_id}/")
