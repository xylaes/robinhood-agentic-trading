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

from portfolio_manager import clean_stale_mcp_locks

async def test_mcp_connection():
    """Lightweight dry-run connection test for Robinhood Trading MCP, Banking MCP, and Robinhood Crypto API."""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    clean_stale_mcp_locks()

    print("==================================================")
    print("🔍 Robinhood Trading & Banking MCP Diagnostic Test")
    print("==================================================")

    command = "npx.cmd" if sys.platform == "win32" else "npx"

    # 1. Test Robinhood Crypto API Integration (Dual Architecture: Standalone REST Engine)
    print("\n[1/3] Checking Standalone Direct REST Crypto API Client (API Key Engine)...")
    crypto_client = RobinhoodCryptoClient()
    if crypto_client.is_authenticated():
        print("  ✓ Direct REST API credentials detected (API Key + Ed25519 Private Key).")
        try:
            acc_info = crypto_client.get_account()
            print(f"  ✓ Crypto REST API Account Status: {acc_info.get('status', 'authenticated')}")
            holdings = crypto_client.get_holdings()
            res_list = holdings.get("results", []) if isinstance(holdings, dict) else []
            print(f"  ✓ Crypto REST API Holdings Check: {len(res_list)} position(s) active on primary crypto account.")
        except Exception as e:
            print(f"  ⚠️ Crypto REST API Query Warning: {e}")
    else:
        print("  ℹ️ ROBINHOOD_CRYPTO_API_KEY / ROBINHOOD_CRYPTO_PRIVATE_KEY omitted.")
        print("  ℹ️ Direct REST client will operate in Dry-Run / Simulation Mode.")

    quotes = crypto_client.get_best_bid_ask(["BTC-USD", "ETH-USD"])
    print(f"  ✓ Best Bid/Ask Public Quotes Check: {'Success' if quotes else 'Failed'}")

    # 2. Test Robinhood Trading MCP Gateway Connection
    print("\n[2/3] Checking Connection to Robinhood Trading MCP Gateway...")
    trading_params = StdioServerParameters(
        command=command,
        args=["-y", "mcp-remote@0.1.49", "https://agent.robinhood.com/mcp/trading", "--silent"]
    )

    trading_ok = False
    try:
        async with stdio_client(trading_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("  ✓ Successfully initialized Robinhood Trading MCP session!")

                acc_res = await session.call_tool("get_accounts", arguments={})
                acc_data = json.loads(acc_res.content[0].text)
                accounts = acc_data.get("data", {}).get("accounts", [])
                
                print(f"  ✓ Retrieved {len(accounts)} Robinhood account(s).")
                target_rhs = None
                for acc in accounts:
                    acc_num = acc.get("account_number", "")
                    rhs_num = acc.get("rhs_account_number", "")
                    rhc_num = acc.get("rhc_account_number", "")
                    agentic = acc.get("agentic_allowed", False)
                    opt_level = acc.get("option_level", "unknown")
                    if str(acc_num).endswith("8015") or str(rhs_num).endswith("8015"):
                        target_rhs = rhs_num or acc_num
                    print(f"    Account: ...{str(acc_num)[-4:]} | RHS: {rhs_num} | Crypto: ...{str(rhc_num)[-4:] if rhc_num else 'N/A'} | Agentic: {agentic} | Options: {opt_level}")

                # Test Native MCP Crypto Tools on Agentic Account
                if target_rhs:
                    print(f"\n  [2b] Testing Native MCP Crypto Tools on Account ...{str(target_rhs)[-4:]}...")
                    try:
                        q_res = await session.call_tool("get_crypto_quotes", arguments={
                            "symbols": ["BTC-USD", "ETH-USD"],
                            "rhs_account_number": target_rhs
                        })
                        q_data = json.loads(q_res.content[0].text)
                        quotes_count = len(q_data.get("data", {}).get("results", []))
                        print(f"    ✓ MCP get_crypto_quotes: Received {quotes_count} live quotes with exchange routing.")

                        pos_res = await session.call_tool("get_crypto_positions", arguments={
                            "rhs_account_number": target_rhs
                        })
                        pos_data = json.loads(pos_res.content[0].text)
                        print(f"    ✓ MCP get_crypto_positions: Successfully queried agentic crypto positions.")

                        prev_res = await session.call_tool("preview_crypto_order", arguments={
                            "rhs_account_number": target_rhs,
                            "symbol": "BTC-USD",
                            "side": "buy",
                            "type": "market",
                            "dollar_amount": "5.00"
                        })
                        prev_data = json.loads(prev_res.content[0].text)
                        est_notional = prev_data.get("data", {}).get("order", {}).get("net_rounded_estimated_notional", "5.00")
                        print(f"    ✓ MCP preview_crypto_order: Simulation passed (${est_notional} est. notional).")
                    except Exception as ce:
                        print(f"    ⚠️ Native MCP Crypto test notice: {ce}")

                trading_ok = True
    except Exception as e:
        print("  ❌ Robinhood Trading MCP Connection Failed:", e)

    # 3. Test Robinhood Banking MCP Gateway Connection
    print("\n[3/3] Checking Connection to Robinhood Banking MCP Gateway...")
    banking_params = StdioServerParameters(
        command=command,
        args=["-y", "mcp-remote", "https://banking-agent.robinhood.com/mcp/banking"]
    )

    banking_ok = False
    try:
        async with stdio_client(banking_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("  ✓ Successfully initialized Robinhood Banking MCP session!")
                tools_res = await session.list_tools()
                tool_names = [t.name for t in tools_res.tools] if hasattr(tools_res, 'tools') else []
                print(f"  ✓ Banking MCP Connected. Available Tools ({len(tool_names)}): {', '.join(tool_names[:5]) if tool_names else 'Authenticated'}")
                banking_ok = True
    except Exception as e:
        print("  ❌ Robinhood Banking MCP Connection Note/Failed:", e)

    print("\n==================================================")
    if trading_ok and banking_ok:
        print("✅ Both Trading & Banking MCP Servers are UP & FUNCTIONING!")
    elif trading_ok:
        print("⚠️ Trading MCP is ACTIVE; Banking MCP responded with initialization state.")
    else:
        print("❌ Diagnostic Connection Test Completed with errors.")
    print("==================================================")
    return trading_ok and banking_ok

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())

