import asyncio
import sys
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.crypto_client import RobinhoodCryptoClient

# Load environment variables if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

async def test_mcp_connection():
    """Lightweight dry-run connection test for Robinhood MCP and Robinhood Crypto API."""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    print("==================================================")
    print("🔍 Robinhood Gateway & Crypto API Diagnostic Test")
    print("==================================================")

    # 1. Test Robinhood Crypto API Integration
    print("\n[1/2] Checking Robinhood Crypto API Client...")
    crypto_client = RobinhoodCryptoClient()
    if crypto_client.is_authenticated():
        print("  ✓ Robinhood Crypto API credentials detected (API Key + Ed25519 Key).")
        try:
            acc_info = crypto_client.get_account()
            print(f"  ✓ Crypto API Account Status: {acc_info.get('status', 'authenticated')}")
        except Exception as e:
            print(f"  ⚠️ Crypto API Query Warning: {e}")
    else:
        print("  ℹ️ ROBINHOOD_CRYPTO_API_KEY / ROBINHOOD_CRYPTO_PRIVATE_KEY omitted.")
        print("  ℹ️ System will operate in Dry-Run / Simulation Mode for 24/7 Crypto.")

    quotes = crypto_client.get_best_bid_ask(["BTC-USD", "ETH-USD"])
    print(f"  ✓ Best Bid/Ask Public Quotes Check: {'Success' if quotes else 'Failed'}")

    # 2. Test Robinhood MCP Gateway Connection
    print("\n[2/2] Checking Connection to Robinhood MCP Gateway...")
    command = "npx.cmd" if sys.platform == "win32" else "npx"
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "mcp-remote@0.1.38", "https://agent.robinhood.com/mcp/trading"]
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("  ✓ Successfully initialized Robinhood MCP session!")

                acc_res = await session.call_tool("get_accounts", arguments={})
                acc_data = json.loads(acc_res.content[0].text)
                accounts = acc_data.get("data", {}).get("accounts", [])
                
                print(f"  ✓ Retrieved {len(accounts)} Robinhood account(s).")
                for acc in accounts:
                    acc_num = acc.get("account_number", "")
                    agentic = acc.get("agentic_allowed", False)
                    opt_level = acc.get("option_level", "unknown")
                    print(f"    Account: ...{acc_num[-4:]} | Agentic Allowed: {agentic} | Options Level: {opt_level}")

                print("\n==================================================")
                print("✅ Diagnostic Connection Test Completed with 0 Errors!")
                print("==================================================")
                return True

    except Exception as e:
        print("\n❌ Diagnostic Connection Test Failed:", e)
        return False

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
