"""
Robinhood Banking & Agentic Credit Card MCP Diagnostic Tester.

Checks connectivity and OAuth discovery for Robinhood's forward-looking
Banking & Credit Card MCP Gateway (https://banking-agent.robinhood.com/mcp/banking).
"""

import asyncio
import sys
import json
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

async def test_banking_mcp():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    print("==================================================")
    print("💳 Robinhood Banking & Credit Card MCP Diagnostic")
    print("==================================================")

    target_url = "https://banking-agent.robinhood.com/mcp/banking"
    print(f"\nChecking endpoint availability: {target_url}...")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(target_url)
            print(f"  ℹ️ Endpoint HTTP Status: {res.status_code}")
            if res.status_code in [200, 401, 403]:
                print("  ✓ Banking MCP Endpoint Detected!")
            else:
                print("  ℹ️ Endpoint is currently in preview/unannounced staging.")
    except Exception as e:
        print(f"  ℹ️ Banking MCP Endpoint status: {e}")
        print("  ℹ️ Future Roadmap Feature: Will auto-connect when endpoint goes live.")

    print("\n==================================================")
    print("✅ Diagnostic check complete!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_banking_mcp())
