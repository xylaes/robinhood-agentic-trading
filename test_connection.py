import asyncio
import sys
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_connection():
    """Lightweight dry-run connection test for Robinhood MCP."""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    command = "npx.cmd" if sys.platform == "win32" else "npx"
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "mcp-remote", "https://agent.robinhood.com/mcp/trading"]
    )

    print("Checking connection to Robinhood MCP gateway...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✓ Successfully initialized Robinhood MCP session!")

                acc_res = await session.call_tool("get_accounts", arguments={})
                acc_data = json.loads(acc_res.content[0].text)
                accounts = acc_data.get("data", {}).get("accounts", [])
                
                print(f"✓ Retrieved {len(accounts)} Robinhood account(s).")
                for acc in accounts:
                    acc_num = acc.get("account_number", "")
                    agentic = acc.get("agentic_allowed", False)
                    opt_level = acc.get("option_level", "unknown")
                    print(f"  Account: ...{acc_num[-4:]} | Agentic Allowed: {agentic} | Options Level: {opt_level}")

                print("✓ Diagnostic connection test completed with 0 errors!")
                return True

    except Exception as e:
        print("❌ Diagnostic connection test failed:", e)
        return False

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
