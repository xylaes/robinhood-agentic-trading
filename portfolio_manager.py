import asyncio
import sys
import os
import json
import uuid
import datetime
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import modular components from src package
from src.config import EQUITY_WATCHLIST, CRYPTO_WATCHLIST, SizingEngine
from src.ssot import GitHubSourceOfTruth
from src.macro_hedging import EventContractManager
from src.risk_manager import PortfolioRiskAndRebalanceManager
from src.analysis_digest import PortfolioDigestGenerator
from src.crypto_client import RobinhoodCryptoClient


# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("portfolio_manager.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("portfolio_manager")

async def get_target_account(session):
    """
    Dynamically resolves the target Robinhood account number.
    Uses ROBINHOOD_ACCOUNT_NUMBER from environment/.env if set and valid;
    otherwise queries get_accounts and picks the first agentic_allowed account.
    """
    env_account = os.getenv("ROBINHOOD_ACCOUNT_NUMBER", "").strip()
    if env_account and not env_account.startswith("your_") and "placeholder" not in env_account.lower():
        logger.info(f"Using account number from environment: ...{env_account[-4:]}")
        return env_account

    logger.info("ROBINHOOD_ACCOUNT_NUMBER not set or is placeholder template. Resolving via get_accounts...")
    acc_res = await session.call_tool("get_accounts", arguments={})
    acc_data = json.loads(acc_res.content[0].text)
    accounts = acc_data.get("data", {}).get("accounts", [])

    for acc in accounts:
        if acc.get("agentic_allowed", False):
            acc_num = acc.get("account_number")
            logger.info(f"Selected agentic account: ...{acc_num[-4:]}")
            return acc_num

    if accounts:
        acc_num = accounts[0].get("account_number")
        logger.info(f"Fallback to primary account: ...{acc_num[-4:]}")
        return acc_num

    raise RuntimeError("No valid Robinhood brokerage accounts found.")


async def run_portfolio_cycle(target_branch: str = "full"):
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    target_branch = target_branch.lower().strip()
    logger.info(f"Initiating Portfolio Manager Run (Target Branch: '{target_branch.upper()}')")

    # Step 0: Verify GitHub Single Source of Truth (SSOT) Alignment
    ssot_status = GitHubSourceOfTruth.verify_alignment()

    command = "npx.cmd" if sys.platform == "win32" else "npx"
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "mcp-remote@0.1.38", "https://agent.robinhood.com/mcp/trading"]
    )

    cycle_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    results = {
        "timestamp": cycle_time,
        "github_ssot": ssot_status,
        "target_branch": target_branch,
        "equities": {},
        "options": {},
        "crypto": {},
        "event_contracts": {},
        "risk_and_rebalance": {},
        "simulations": {},
        "executed_trades": []
    }

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logger.info("Connected to Robinhood MCP gateway.")

                account_num = await get_target_account(session)
                results["account_number"] = account_num

                # 1. Synchronize Accounts & Portfolio
                logger.info("Step 1: Synchronizing Account & Portfolio Metrics...")
                portfolio_res = await session.call_tool("get_portfolio", arguments={"account_number": account_num})
                portfolio_data = json.loads(portfolio_res.content[0].text)
                results["portfolio"] = portfolio_data

                pos_res = await session.call_tool("get_equity_positions", arguments={"account_number": account_num})
                pos_data = json.loads(pos_res.content[0].text)
                results["positions"] = pos_data

                p_info = portfolio_data.get("data", {})
                equity_val = float(p_info.get("equity", 0) or p_info.get("total_value", 0) or 0)
                buying_power = float(p_info.get("buying_power", {}).get("buying_power", 0) or 0)
                logger.info(f"Net Worth: ${equity_val:.2f} | Buying Power: ${buying_power:.2f}")

                # Calculate dynamic order sizes based on net worth
                stock_order_size = SizingEngine.get_equity_order_size(equity_val, buying_power)
                logger.info(f"Scaled Stock Order Sizing: ${stock_order_size:.2f} per trade")

                # 2. Check Equities & Technical Indicators
                if target_branch in ["full", "equities"]:
                    logger.info("Step 2: Checking Equities & Technical Indicators...")
                    quotes_res = await session.call_tool("get_equity_quotes", arguments={"symbols": EQUITY_WATCHLIST})
                    results["quotes"] = json.loads(quotes_res.content[0].text)

                    start_time = (datetime.datetime.utcnow() - datetime.timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
                    indicators = {}
                    for symbol in EQUITY_WATCHLIST:
                        try:
                            rsi_res = await session.call_tool("get_equity_technical_indicators", arguments={"symbol": symbol, "type": "rsi", "interval": "hour", "start_time": start_time, "output": "last:2"})
                            macd_res = await session.call_tool("get_equity_technical_indicators", arguments={"symbol": symbol, "type": "macd", "interval": "hour", "start_time": start_time, "output": "last:2"})
                            bb_res = await session.call_tool("get_equity_technical_indicators", arguments={"symbol": symbol, "type": "bollinger_bands", "interval": "hour", "start_time": start_time, "output": "last:2"})
                            indicators[symbol] = {
                                "rsi": json.loads(rsi_res.content[0].text),
                                "macd": json.loads(macd_res.content[0].text),
                                "bollinger_bands": json.loads(bb_res.content[0].text)
                            }
                        except Exception as e:
                            logger.warning(f"Indicator notice for {symbol}: {e}")
                    results["indicators"] = indicators

                # 3. Check Crypto Watchlist & Quotes via Robinhood Crypto API
                if target_branch in ["full", "crypto"]:
                    logger.info("Step 3: Checking Crypto Watchlist & Quotes (Robinhood Crypto API)...")
                    crypto_client = RobinhoodCryptoClient()
                    crypto_quotes = {}
                    
                    # Fetch quotes via Robinhood Crypto API
                    api_quotes = crypto_client.get_best_bid_ask(CRYPTO_WATCHLIST)
                    if api_quotes and "results" in api_quotes and api_quotes["results"]:
                        crypto_quotes["api_best_bid_ask"] = api_quotes
                    else:
                        # Fallback search via MCP
                        for pair in CRYPTO_WATCHLIST:
                            try:
                                c_res = await session.call_tool("search", arguments={"query": pair, "asset_type": "currency_pair"})
                                crypto_quotes[pair] = json.loads(c_res.content[0].text)
                            except Exception as e:
                                crypto_quotes[pair] = {"error": str(e)}

                    crypto_account = crypto_client.get_account()
                    results["crypto_quotes"] = crypto_quotes
                    results["crypto_account"] = crypto_account

                # 4. Evaluate Event Contracts & Macro Hedges
                if target_branch in ["full", "events"]:
                    logger.info("Step 4: Evaluating Event Contracts & Macro Hedges...")
                    event_hedges = EventContractManager.evaluate_macro_hedges(equity_val, buying_power)
                    results["event_contracts"] = event_hedges

                # 5. Pre-Trade Simulation Reviews
                logger.info("Step 5: Running Pre-Trade Simulation Reviews...")
                if target_branch in ["full", "equities"]:
                    try:
                        eq_sim = await session.call_tool("review_equity_order", arguments={
                            "account_number": account_num,
                            "symbol": "NVDA",
                            "side": "buy",
                            "type": "market",
                            "dollar_amount": f"{stock_order_size:.2f}"
                        })
                        results["simulations"]["equity_review"] = json.loads(eq_sim.content[0].text)
                    except Exception as e:
                        logger.warning(f"Equity simulation notice: {e}")

                if target_branch in ["full", "options"]:
                    try:
                        opt_sim = await session.call_tool("review_option_order", arguments={
                            "account_number": account_num,
                            "chain_symbol": "F",
                            "underlying_type": "equity",
                            "type": "limit",
                            "quantity": "1",
                            "price": "0.35",
                            "legs": [
                                {
                                    "option_id": "150a3cae-bed2-406b-8d0b-27714de083ca",
                                    "side": "buy",
                                    "position_effect": "open",
                                    "ratio_quantity": 1
                                }
                            ]
                        })
                        results["simulations"]["option_review"] = json.loads(opt_sim.content[0].text)
                    except Exception as e:
                        logger.warning(f"Option simulation notice: {e}")

                if target_branch in ["full", "crypto"]:
                    try:
                        crypto_client = RobinhoodCryptoClient()
                        crypto_order_size = SizingEngine.get_crypto_order_size(equity_val, buying_power)
                        crypto_sim = crypto_client.place_order(
                            symbol="BTC-USD",
                            side="buy",
                            order_type="market",
                            dollar_amount=crypto_order_size,
                            dry_run=True
                        )
                        results["simulations"]["crypto_review"] = crypto_sim
                    except Exception as e:
                        logger.warning(f"Crypto simulation notice: {e}")

                # 6. Automated Risk Exposure Analysis & Rebalancing
                logger.info("Step 6: Running Automated Risk Exposure & Rebalancing Analysis...")
                risk_rebalance = PortfolioRiskAndRebalanceManager.analyze_risk_and_rebalance(portfolio_data, pos_data)
                results["risk_and_rebalance"] = risk_rebalance

                # 7. Generate Human-Readable Executive Portfolio Digest
                logger.info("Step 7: Generating Human-Readable Executive Portfolio Digest (PORTFOLIO_ANALYSIS.md)...")
                PortfolioDigestGenerator.generate_digest(results)

                # Save results state
                with open("system_full_state.json", "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2)
                logger.info("State synchronized and saved to system_full_state.json")

                return results

    except Exception as e:
        logger.error(f"Fatal error in portfolio manager cycle: {e}")
        raise e

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Robinhood Agentic Trading Portfolio Manager")
    parser.add_argument(
        "--branch",
        type=str,
        default="full",
        choices=["full", "equities", "options", "crypto", "events"],
        help="Target specific strategy branch to run (default: full)"
    )
    args = parser.parse_args()
    asyncio.run(run_portfolio_cycle(target_branch=args.branch))

