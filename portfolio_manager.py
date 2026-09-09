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

def clean_stale_mcp_locks():
    """Cleans up stale mcp-remote lock and verifier files to prevent port conflict re-registration prompts."""
    import glob
    import shutil
    auth_dir = os.path.expanduser("~/.mcp-auth")
    if os.path.exists(auth_dir):
        # Remove stale lockfiles
        for lock_file in glob.glob(os.path.join(auth_dir, "**", "*_lock.json"), recursive=True):
            try:
                os.remove(lock_file)
            except Exception:
                pass
        
        # Mirror valid auth tokens from 0.1.49 to other versions if present
        source_dir = os.path.join(auth_dir, "mcp-remote-0.1.49")
        if os.path.exists(source_dir):
            for target_dir_name in os.listdir(auth_dir):
                target_path = os.path.join(auth_dir, target_dir_name)
                if os.path.isdir(target_path) and target_path != source_dir:
                    for token_file in glob.glob(os.path.join(source_dir, "*.json")):
                        fname = os.path.basename(token_file)
                        dest = os.path.join(target_path, fname)
                        if not os.path.exists(dest):
                            try:
                                shutil.copy2(token_file, dest)
                            except Exception:
                                pass

def send_desktop_notification(title: str, message: str):
    """Fires a native Windows desktop balloon/toast notification on live trades."""
    if sys.platform == "win32":
        try:
            import subprocess
            ps_script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            $notify = New-Object System.Windows.Forms.NotifyIcon
            $notify.Icon = [System.Drawing.SystemIcons]::Information
            $notify.Visible = $true
            $notify.ShowBalloonTip(10000, '{title}', '{message}', [System.Windows.Forms.ToolTipIcon]::Info)
            Start-Sleep -Seconds 2
            $notify.Dispose()
            """
            subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.debug(f"Desktop notification notice: {e}")

async def get_target_account(session):
    """
    Dynamically resolves the target Robinhood account number and rhs_account_number.
    Target the agentic trading sub-account (...8015) automatically.
    """
    logger.info("Resolving Robinhood accounts via get_accounts...")
    acc_res = await session.call_tool("get_accounts", arguments={})
    acc_data = json.loads(acc_res.content[0].text)
    accounts = acc_data.get("data", {}).get("accounts", [])

    target_acc = None
    # 1. Target sub-account ending in 8015
    for acc in accounts:
        acc_num = str(acc.get("account_number", ""))
        rhs_num = str(acc.get("rhs_account_number", ""))
        if acc_num.endswith("8015") or rhs_num.endswith("8015"):
            target_acc = acc
            break

    # 2. Target agentic_allowed account
    if not target_acc:
        for acc in accounts:
            if acc.get("agentic_allowed", False):
                target_acc = acc
                break

    # 3. Fallback to first available account
    if not target_acc and accounts:
        target_acc = accounts[0]

    if not target_acc:
        raise RuntimeError("No valid Robinhood brokerage accounts found.")

    acc_num = target_acc.get("account_number")
    rhs_acc_num = target_acc.get("rhs_account_number", acc_num)
    rhc_acc_num = target_acc.get("rhc_account_number", "")
    logger.info(f"Selected agentic account: ...{str(acc_num)[-4:]} (RHS: {rhs_acc_num}, Crypto: ...{str(rhc_acc_num)[-4:] if rhc_acc_num else 'N/A'})")
    return acc_num, rhs_acc_num


async def run_portfolio_cycle(target_branch: str = "full", execute_live: bool = None):
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    target_branch = target_branch.lower().strip()
    if execute_live is None:
        execute_live = os.getenv("ROBINHOOD_AUTO_EXECUTE", "false").lower() in ("true", "1", "yes")

    mode_label = "⚡ LIVE EXECUTION AUTHORIZED" if execute_live else "🛡️ SAFE AUDIT & SIMULATION MODE (Authorization Required)"
    logger.info(f"Initiating Portfolio Manager Run (Target Branch: '{target_branch.upper()}', Mode: {mode_label})")

    # Step 0: Verify GitHub Single Source of Truth (SSOT) Alignment
    ssot_status = GitHubSourceOfTruth.verify_alignment()

    clean_stale_mcp_locks()

    command = "npx.cmd" if sys.platform == "win32" else "npx"

    server_params = StdioServerParameters(
        command=command,
        args=["-y", "mcp-remote@0.1.49", "https://agent.robinhood.com/mcp/trading", "--silent"]
    )

    cycle_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    results = {
        "timestamp": cycle_time,
        "github_ssot": ssot_status,
        "target_branch": target_branch,
        "execute_live": execute_live,
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

                account_num, rhs_account_num = await get_target_account(session)
                results["account_number"] = account_num
                results["rhs_account_number"] = rhs_account_num

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
                crypto_order_size = SizingEngine.get_crypto_order_size(equity_val, buying_power)
                logger.info(f"Scaled Dynamic Sizing -> Equity: ${stock_order_size:.2f} | Crypto: ${crypto_order_size:.2f}")

                # 2. Check Equities & Technical Indicators Across Expanded Watchlist
                best_equity_symbol = "NVDA"
                if target_branch in ["full", "equities"]:
                    logger.info("Step 2: Scanning Equities & Computing Technical Indicators...")
                    quotes_res = await session.call_tool("get_equity_quotes", arguments={"symbols": EQUITY_WATCHLIST})
                    results["quotes"] = json.loads(quotes_res.content[0].text)

                    start_time = (datetime.datetime.utcnow() - datetime.timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
                    indicators = {}
                    symbol_scores = {}

                    for symbol in EQUITY_WATCHLIST:
                        try:
                            rsi_res = await session.call_tool("get_equity_technical_indicators", arguments={"symbol": symbol, "type": "rsi", "interval": "hour", "start_time": start_time, "output": "last:2"})
                            macd_res = await session.call_tool("get_equity_technical_indicators", arguments={"symbol": symbol, "type": "macd", "interval": "hour", "start_time": start_time, "output": "last:2"})
                            bb_res = await session.call_tool("get_equity_technical_indicators", arguments={"symbol": symbol, "type": "bollinger_bands", "interval": "hour", "start_time": start_time, "output": "last:2"})
                            
                            rsi_json = json.loads(rsi_res.content[0].text)
                            rsi_val = 50.0
                            if "data" in rsi_json and "results" in rsi_json["data"]:
                                r_res = rsi_json["data"]["results"]
                                if r_res and "indicator" in r_res[0]:
                                    rsi_val = float(r_res[0]["indicator"].get("rsi", 50.0))

                            indicators[symbol] = {
                                "rsi": rsi_json,
                                "macd": json.loads(macd_res.content[0].text),
                                "bollinger_bands": json.loads(bb_res.content[0].text),
                                "latest_rsi": rsi_val
                            }
                            symbol_scores[symbol] = rsi_val
                        except Exception as e:
                            logger.warning(f"Indicator notice for {symbol}: {e}")
                    
                    results["indicators"] = indicators
                    if symbol_scores:
                        # Pick the symbol with the lowest RSI (best dip-buy opportunity)
                        best_equity_symbol = min(symbol_scores, key=symbol_scores.get)
                        logger.info(f"Top Equity Opportunity Candidate: {best_equity_symbol} (RSI: {symbol_scores[best_equity_symbol]:.2f})")

                # 3. Check Crypto Watchlist, Quotes & Positions via Robinhood MCP (Dual Engine)
                best_crypto_symbol = "BTC-USD"
                if target_branch in ["full", "crypto"]:
                    logger.info("Step 3: Checking Crypto Watchlist & Quotes via Native Robinhood MCP...")
                    crypto_quotes = {}
                    crypto_holdings = []
                    
                    # 3a. Native Robinhood Trading MCP Quotes
                    try:
                        mcp_quotes = await session.call_tool("get_crypto_quotes", arguments={
                            "symbols": CRYPTO_WATCHLIST,
                            "rhs_account_number": rhs_account_num
                        })
                        c_data = json.loads(mcp_quotes.content[0].text)
                        crypto_quotes["mcp_quotes"] = c_data.get("data", {}).get("results", [])
                        logger.info(f"Retrieved {len(crypto_quotes.get('mcp_quotes', []))} live crypto quotes via Robinhood MCP.")
                    except Exception as e:
                        logger.warning(f"MCP crypto quotes notice: {e}. Falling back to direct REST client...")
                        crypto_client = RobinhoodCryptoClient()
                        api_quotes = crypto_client.get_best_bid_ask(CRYPTO_WATCHLIST)
                        crypto_quotes["api_best_bid_ask"] = api_quotes

                    # 3b. Native Robinhood MCP Positions (Account 8015)
                    try:
                        pos_res = await session.call_tool("get_crypto_positions", arguments={
                            "rhs_account_number": rhs_account_num
                        })
                        c_pos = json.loads(pos_res.content[0].text)
                        crypto_holdings = c_pos.get("data", {}).get("results", [])
                        logger.info(f"Retrieved {len(crypto_holdings)} crypto positions for account ...{rhs_account_num[-4:]} via Robinhood MCP.")
                    except Exception as e:
                        logger.warning(f"MCP crypto positions notice: {e}. Falling back to direct REST client...")
                        crypto_client = RobinhoodCryptoClient()
                        crypto_holdings = crypto_client.get_holdings() if crypto_client.is_authenticated() else {"results": []}

                    results["crypto_quotes"] = crypto_quotes
                    results["crypto_holdings"] = crypto_holdings

                    # Select active crypto opportunity (e.g. BTC, ETH, SOL, or DOGE)
                    if CRYPTO_WATCHLIST:
                        best_crypto_symbol = CRYPTO_WATCHLIST[0]

                # 4. Evaluate Event Contracts & Macro Hedges
                if target_branch in ["full", "events"]:
                    logger.info("Step 4: Evaluating Event Contracts & Macro Hedges...")
                    event_hedges = EventContractManager.evaluate_macro_hedges(equity_val, buying_power)
                    results["event_contracts"] = event_hedges

                # 5. Pre-Trade Simulation Reviews & Automated Execution
                logger.info("Step 5: Running Pre-Trade Reviews & Execution Engine...")
                
                # --- Equities Execution ---
                if target_branch in ["full", "equities"]:
                    try:
                        logger.info(f"Auditing Equity Market Buy for {best_equity_symbol} (${stock_order_size:.2f})...")
                        eq_sim = await session.call_tool("review_equity_order", arguments={
                            "account_number": account_num,
                            "symbol": best_equity_symbol,
                            "side": "buy",
                            "type": "market",
                            "dollar_amount": f"{stock_order_size:.2f}"
                        })
                        eq_sim_data = json.loads(eq_sim.content[0].text)
                        results["simulations"]["equity_review"] = eq_sim_data

                        # Check Bucket Allocation & Concentration Guardrails
                        equity_target_val = (equity_val * 0.3333) if equity_val > 0 else 50.00
                        held_symbols = [p.get("symbol") for p in pos_data.get("data", {}).get("positions", [])]
                        
                        if equity_val > 0 and (equity_val - buying_power) >= equity_target_val:
                            logger.info(f"🛡️ Guardrail: Equity allocation already at/exceeding 33.33% target (${equity_target_val:.2f}). Skipping equity buy to avoid over-allocation.")
                        elif best_equity_symbol in held_symbols and len(held_symbols) >= 3:
                            logger.info(f"🛡️ Guardrail: {best_equity_symbol} is already held in portfolio. Skipping duplicate stacking buy.")
                        elif execute_live and buying_power >= stock_order_size:
                            logger.info(f"🚀 Placing LIVE Equity Order: {best_equity_symbol} (${stock_order_size:.2f})...")
                            place_res = await session.call_tool("place_equity_order", arguments={
                                "account_number": account_num,
                                "symbol": best_equity_symbol,
                                "side": "buy",
                                "type": "market",
                                "dollar_amount": f"{stock_order_size:.2f}",
                                "time_in_force": "gfd"
                            })
                            place_data = json.loads(place_res.content[0].text)
                            logger.info(f"✓ Equity Order Placed: {json.dumps(place_data)}")
                            send_desktop_notification(
                                "🤖 Robinhood Agentic Trader",
                                f"Live Equity Buy Submitted: {best_equity_symbol} (${stock_order_size:.2f})"
                            )
                            results["executed_trades"].append({
                                "asset_class": "equity",
                                "symbol": best_equity_symbol,
                                "side": "buy",
                                "dollar_amount": stock_order_size,
                                "status": "SUBMITTED",
                                "details": place_data
                            })
                        else:
                            logger.info(f"🛡️ Simulation audit completed for {best_equity_symbol}. Execution requires explicit authorization (--execute-live).")
                    except Exception as e:
                        logger.warning(f"Equity execution notice: {e}")

                # --- Options Simulation ---
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

                # --- Crypto Execution (Dual Engine: Native MCP with REST Fallback) ---
                if target_branch in ["full", "crypto"]:
                    is_dry_run = not execute_live
                    logger.info(f"Evaluating Crypto Order for {best_crypto_symbol} (${crypto_order_size:.2f}, DryRun: {is_dry_run})...")
                    mcp_order_success = False

                    # 1. Attempt Native MCP Preview & Placement
                    try:
                        ref_uuid = str(uuid.uuid4())
                        preview_res = await session.call_tool("preview_crypto_order", arguments={
                            "rhs_account_number": rhs_account_num,
                            "symbol": best_crypto_symbol,
                            "side": "buy",
                            "type": "market",
                            "dollar_amount": f"{crypto_order_size:.2f}"
                        })
                        preview_data = json.loads(preview_res.content[0].text)
                        results["simulations"]["crypto_review"] = preview_data
                        logger.info(f"✓ Crypto Order Preview Successful via MCP (Account: ...{rhs_account_num[-4:]}, Notional: ${crypto_order_size:.2f})")

                        if execute_live and not is_dry_run:
                            logger.info(f"Placing Live Crypto Order for {best_crypto_symbol} (${crypto_order_size:.2f}) via MCP...")
                            order_res = await session.call_tool("place_crypto_order", arguments={
                                "rhs_account_number": rhs_account_num,
                                "symbol": best_crypto_symbol,
                                "side": "buy",
                                "type": "market",
                                "dollar_amount": f"{crypto_order_size:.2f}",
                                "ref_id": ref_uuid
                            })
                            order_data = json.loads(order_res.content[0].text)
                            logger.info(f"✓ Crypto Order Placed via MCP: {order_data}")
                            send_desktop_notification(
                                "🪙 Robinhood Crypto Trader",
                                f"Live Crypto Buy Executed: {best_crypto_symbol} (${crypto_order_size:.2f})"
                            )
                            results["executed_trades"].append({
                                "asset_class": "crypto",
                                "symbol": best_crypto_symbol,
                                "side": "buy",
                                "dollar_amount": crypto_order_size,
                                "status": "SUBMITTED",
                                "details": order_data
                            })
                        mcp_order_success = True
                    except Exception as e:
                        logger.warning(f"MCP crypto execution notice: {e}. Falling back to direct REST client...")

                    # 2. Fallback to Direct REST API Client if MCP did not complete
                    if not mcp_order_success:
                        try:
                            crypto_client = RobinhoodCryptoClient()
                            crypto_res = crypto_client.place_order(
                                symbol=best_crypto_symbol,
                                side="buy",
                                order_type="market",
                                dollar_amount=crypto_order_size,
                                dry_run=is_dry_run
                            )
                            results["simulations"]["crypto_review"] = crypto_res
                            if execute_live and not is_dry_run and crypto_res and "id" in crypto_res:
                                logger.info(f"✓ Crypto Order Placed via Direct REST: {json.dumps(crypto_res)}")
                                send_desktop_notification(
                                    "🪙 Robinhood Crypto Trader",
                                    f"Live Crypto Buy Executed: {best_crypto_symbol} (${crypto_order_size:.2f})"
                                )
                                results["executed_trades"].append({
                                    "asset_class": "crypto",
                                    "symbol": best_crypto_symbol,
                                    "side": "buy",
                                    "dollar_amount": crypto_order_size,
                                    "status": "FILLED",
                                    "details": crypto_res
                                })
                        except Exception as fb_err:
                            logger.error(f"Direct crypto client fallback error: {fb_err}")

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
    parser.add_argument(
        "--execute-live",
        action="store_true",
        default=False,
        help="Explicitly authorize live order execution for passing simulation reviews (default: False)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Force simulation-only dry run mode"
    )
    args = parser.parse_args()
    live_mode = args.execute_live and not args.dry_run
    asyncio.run(run_portfolio_cycle(target_branch=args.branch, execute_live=live_mode))

