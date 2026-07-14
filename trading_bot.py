import asyncio
import sys
import os
import json
import uuid
import datetime
import argparse
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pandas as pd
import numpy as np

# Load local environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Config
WATCHLIST = ['QQQ', 'SPY', 'NVDA', 'AAPL']
STATE_FILE = "trading_state.json"
LOG_FILE = "trading_log.json"
ALLOCATION_PER_TRADE = 10.00
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.04

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("trading_bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("trading_bot")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

class TradingBot:
    def __init__(self, account_number, dry_run=True):
        self.account_number = account_number
        self.dry_run = dry_run
        self.state = self.load_state()

    def load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    # Validate keys
                    if "wash_sale_cooldowns" not in state: state["wash_sale_cooldowns"] = {}
                    if "unsettled_buys" not in state: state["unsettled_buys"] = {}
                    if "today_sales" not in state: state["today_sales"] = []
                    if "last_reset_date" not in state: state["last_reset_date"] = str(datetime.date.today())
                    return state
            except Exception as e:
                logger.error(f"Error loading state file: {e}. Resetting state.")
        
        return {
            "wash_sale_cooldowns": {},  # ticker -> expiration date (YYYY-MM-DD)
            "unsettled_buys": {},       # ticker -> { "buy_date": YYYY-MM-DD, "amount": float }
            "today_sales": [],          # list of floats (sale proceeds today)
            "last_reset_date": str(datetime.date.today())
        }

    def save_state(self):
        try:
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

    def log_transaction(self, tx):
        tx["timestamp"] = str(datetime.datetime.utcnow().isoformat()) + "Z"
        tx["dry_run"] = self.dry_run
        try:
            logs = []
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            logs.append(tx)
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to log transaction: {e}")

    def check_and_reset_daily_state(self):
        today_str = str(datetime.date.today())
        if self.state["last_reset_date"] != today_str:
            logger.info(f"New day detected. Resetting daily sales state. Old: {self.state['last_reset_date']}, New: {today_str}")
            self.state["today_sales"] = []
            self.state["last_reset_date"] = today_str
            
            # Prune unsettled buys from yesterday (they are now settled)
            self.state["unsettled_buys"] = {}
            self.save_state()

        # Prune expired wash-sale cooldowns
        now_date = datetime.date.today()
        cooldowns_to_remove = []
        for ticker, exp_date_str in self.state["wash_sale_cooldowns"].items():
            try:
                exp_date = datetime.datetime.strptime(exp_date_str, "%Y-%m-%d").date()
                if now_date >= exp_date:
                    cooldowns_to_remove.append(ticker)
            except Exception as e:
                logger.error(f"Error parsing cooldown date for {ticker}: {e}")
                
        if cooldowns_to_remove:
            for ticker in cooldowns_to_remove:
                logger.info(f"Removing wash sale cooldown for {ticker} (expired on {self.state['wash_sale_cooldowns'][ticker]})")
                del self.state["wash_sale_cooldowns"][ticker]
            self.save_state()

    def compute_indicators(self, bars):
        df = pd.DataFrame(bars)
        # Parse prices as floats
        df['close_price'] = df['close_price'].astype(float)
        
        # 9 and 21 EMAs
        df['ema9'] = df['close_price'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['close_price'].ewm(span=21, adjust=False).mean()
        
        # 14 RSI
        delta = df['close_price'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df

    def evaluate_signals(self, df):
        if len(df) < 2:
            return "hold", 0.0, 0.0, 50.0

        # Current and previous bar values
        curr_bar = df.iloc[-1]
        prev_bar = df.iloc[-2]
        
        curr_close = curr_bar['close_price']
        curr_rsi = curr_bar['rsi']
        curr_ema9 = curr_bar['ema9']
        curr_ema21 = curr_bar['ema21']
        
        prev_ema9 = prev_bar['ema9']
        prev_ema21 = prev_bar['ema21']

        # Signal logic
        # 1. EMA Crossover
        bullish_cross = (prev_ema9 <= prev_ema21) and (curr_ema9 > curr_ema21)
        bearish_cross = (prev_ema9 >= prev_ema21) and (curr_ema9 < curr_ema21)

        # 2. Oversold / Overbought RSI
        oversold_rsi = curr_rsi < 35
        overbought_rsi = curr_rsi > 70

        if bullish_cross or oversold_rsi:
            return "buy", curr_close, curr_rsi, curr_ema9 - curr_ema21
        elif bearish_cross or overbought_rsi:
            return "sell", curr_close, curr_rsi, curr_ema9 - curr_ema21
        
        return "hold", curr_close, curr_rsi, curr_ema9 - curr_ema21

    async def resolve_watchlist(self, session):
        """
        Queries the user's watchlists using get_watchlists.
        Looks for a custom watchlist named 'Agentic' (case-insensitive).
        If found, calls get_watchlist_items and returns the list of symbols.
        Otherwise, falls back to the default hardcoded WATCHLIST.
        """
        try:
            logger.info("Resolving trading watchlist...")
            watchlists_res = await session.call_tool("get_watchlists")
            watchlists_data = json.loads(watchlists_res.content[0].text)
            
            target_list_id = None
            target_list_name = None
            for wl in watchlists_data.get("data", {}).get("watchlists", []):
                name = wl.get("display_name", "").strip().lower()
                if name in ("agentic", "agentic watchlist"):
                    target_list_id = wl.get("id")
                    target_list_name = wl.get("display_name")
                    break
            
            if target_list_id:
                logger.info(f"Found custom Robinhood watchlist '{target_list_name}' (ID: {target_list_id}). Fetching items...")
                items_res = await session.call_tool("get_watchlist_items", arguments={"list_id": target_list_id})
                items_data = json.loads(items_res.content[0].text)
                
                resolved_symbols = []
                for item in items_data.get("data", {}).get("items", []):
                    if item.get("object_type") == "instrument" and item.get("symbol"):
                        resolved_symbols.append(item.get("symbol"))
                
                if resolved_symbols:
                    logger.info(f"Dynamically resolved watchlist from Robinhood: {resolved_symbols}")
                    return resolved_symbols
                else:
                    logger.warning(f"Watchlist '{target_list_name}' is empty or contains no equity instruments. Falling back to default list.")
            else:
                logger.info("Custom watchlist 'Agentic' not found in your Robinhood account. Create a watchlist named 'Agentic' to dynamically manage traded symbols. Falling back to default list.")
                
        except Exception as e:
            logger.error(f"Error resolving watchlist from Robinhood: {e}. Falling back to default list.")
            
        logger.info(f"Using default watchlist: {WATCHLIST}")
        return WATCHLIST

    async def is_near_earnings(self, session, symbol):
        """
        Queries upcoming earnings for a symbol using get_earnings_results.
        Checks if there is an upcoming earnings report within the next 3 days.
        """
        try:
            logger.info(f"Checking upcoming earnings for {symbol}...")
            earnings_res = await session.call_tool("get_earnings_results", arguments={"symbol": symbol})
            earnings_data = json.loads(earnings_res.content[0].text)
            
            results = earnings_data.get("data", {}).get("results", [])
            if not results:
                logger.info(f"No earnings data found for {symbol}.")
                return False
            
            today = datetime.date.today()
            blackout_limit = today + datetime.timedelta(days=3)
            
            for report_event in results:
                eps = report_event.get("eps", {})
                actual = eps.get("actual")
                
                if actual is None:
                    report_info = report_event.get("report", {})
                    report_date_str = report_info.get("date")
                    if not report_date_str:
                        continue
                    
                    try:
                        report_date = datetime.datetime.strptime(report_date_str, "%Y-%m-%d").date()
                        if today <= report_date <= blackout_limit:
                            is_verified = report_info.get("verified", False)
                            status_str = "verified" if is_verified else "tentative"
                            logger.warning(
                                f"UPCOMING EARNINGS RISK: {symbol} reports earnings on {report_date_str} ({status_str}), "
                                f"which is within the 3-day blackout window (today is {today})."
                            )
                            return True
                    except Exception as e:
                        logger.error(f"Error parsing report date '{report_date_str}' for {symbol}: {e}")
                        
        except Exception as e:
            logger.error(f"Error checking earnings for {symbol}: {e}")
            
        return False

    async def execute_run(self, session):
        logger.info("=== Starting Bot Trading Run ===")
        self.check_and_reset_daily_state()

        # 1. Get Portfolio & Buying Power
        portfolio_res = await session.call_tool("get_portfolio", arguments={"account_number": self.account_number})
        portfolio_data = json.loads(portfolio_res.content[0].text)["data"]
        
        total_bp = float(portfolio_data["buying_power"]["buying_power"])
        logger.info(f"Total buying power reported by Robinhood: ${total_bp:.2f}")

        # Compute settled buying power
        unsettled_total = sum(self.state["today_sales"])
        settled_bp = total_bp - unsettled_total
        logger.info(f"Unsettled proceeds today: ${unsettled_total:.2f} | Settled buying power: ${settled_bp:.2f}")

        # 2. Get Current Positions
        pos_res = await session.call_tool("get_equity_positions", arguments={"account_number": self.account_number})
        pos_data = json.loads(pos_res.content[0].text)["data"]
        positions = pos_data.get("positions", [])
        
        active_positions = {}
        for pos in positions:
            qty = float(pos["shares_available_for_sells"])
            if qty > 0:
                active_positions[pos["symbol"]] = {
                    "quantity": qty,
                    "avg_cost": float(pos["average_buy_price"])
                }
        
        logger.info(f"Active positions in account: {list(active_positions.keys())}")

        # 3. Resolve Active Watchlist Dynamically
        active_watchlist = await self.resolve_watchlist(session)

        # 4. Get Real-time quotes
        quotes_res = await session.call_tool("get_equity_quotes", arguments={"symbols": active_watchlist})
        quotes_data = json.loads(quotes_res.content[0].text)["data"]["results"]
        quotes = {}
        for item in quotes_data:
            q = item["quote"]
            symbol = q["symbol"]
            # Current price: pick last_trade_price or last_non_reg_trade_price
            price = float(q["last_trade_price"]) if q["last_trade_price"] else float(q["last_non_reg_trade_price"])
            quotes[symbol] = {
                "price": price,
                "bid": float(q["bid_price"]) if q["bid_price"] else price,
                "ask": float(q["ask_price"]) if q["ask_price"] else price
            }

        # 5. Check Risk Management (Stop Loss / Take Profit) on existing positions
        for symbol, pos in active_positions.items():
            # If a held position is not in the active quotes (e.g. removed from watchlist), fetch it individually
            if symbol not in quotes:
                try:
                    q_res = await session.call_tool("get_equity_quotes", arguments={"symbols": [symbol]})
                    q_item = json.loads(q_res.content[0].text)["data"]["results"][0]["quote"]
                    price = float(q_item["last_trade_price"]) if q_item["last_trade_price"] else float(q_item["last_non_reg_trade_price"])
                    quotes[symbol] = {
                        "price": price,
                        "bid": float(q_item["bid_price"]) if q_item["bid_price"] else price,
                        "ask": float(q_item["ask_price"]) if q_item["ask_price"] else price
                    }
                except Exception as e:
                    logger.error(f"Could not retrieve quote for active position {symbol}: {e}")
                    continue

            curr_price = quotes[symbol]["price"]
            avg_cost = pos["avg_cost"]
            pnl_pct = (curr_price - avg_cost) / avg_cost
            
            logger.info(f"Position: {symbol} | Qty: {pos['quantity']} | Avg Cost: ${avg_cost:.2f} | Current: ${curr_price:.2f} | P&L: {pnl_pct*100:.2f}%")

            # Check if this position was bought with unsettled cash today (GFV Lock)
            gfv_locked = symbol in self.state["unsettled_buys"]

            if pnl_pct <= -STOP_LOSS_PCT:
                logger.warning(f"Stop Loss triggered for {symbol} at {pnl_pct*100:.2f}%!")
                if gfv_locked:
                    logger.warning(f"Skipping sell for {symbol} to prevent Good Faith Violation (GFV Lock active today).")
                else:
                    await self.sell_position(session, symbol, pos["quantity"], curr_price, "stop_loss", avg_cost)
            elif pnl_pct >= TAKE_PROFIT_PCT:
                logger.info(f"Take Profit triggered for {symbol} at {pnl_pct*100:.2f}%!")
                if gfv_locked:
                    logger.warning(f"Skipping sell for {symbol} to prevent Good Faith Violation (GFV Lock active today).")
                else:
                    await self.sell_position(session, symbol, pos["quantity"], curr_price, "take_profit", avg_cost)

        # 6. Evaluate watchlisted assets for signals and execute buys/sells
        for symbol in active_watchlist:
            # Check historicals to compute signals
            start_time = (datetime.datetime.utcnow() - datetime.timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
            hist_res = await session.call_tool("get_equity_historicals", arguments={
                "symbols": [symbol],
                "start_time": start_time,
                "interval": "hour"
            })
            hist_data = json.loads(hist_res.content[0].text)["data"]["results"]
            if not hist_data or not hist_data[0].get("bars"):
                logger.warning(f"Could not retrieve historical bars for {symbol}")
                continue
                
            df = self.compute_indicators(hist_data[0]["bars"])
            signal, price, rsi, ema_diff = self.evaluate_signals(df)
            
            logger.info(f"Asset: {symbol} | Price: ${price:.2f} | RSI: {rsi:.2f} | Signal: {signal.upper()}")

            if signal == "buy" and symbol not in active_positions:
                # Check upcoming earnings blackout window
                if await self.is_near_earnings(session, symbol):
                    logger.warning(f"Skipping buy for {symbol} due to upcoming earnings within the blackout window.")
                    continue

                # Check settled buying power
                if settled_bp < ALLOCATION_PER_TRADE:
                    # Check if total buying power permits it (we'd have to buy with unsettled cash)
                    if total_bp >= ALLOCATION_PER_TRADE:
                        logger.warning(f"Settled buying power (${settled_bp:.2f}) insufficient, but total buying power (${total_bp:.2f}) is enough. Executing UNSETTLED BUY (enforcing GFV Lock).")
                        await self.buy_position(session, symbol, ALLOCATION_PER_TRADE, price, is_settled=False)
                    else:
                        logger.warning(f"Insufficient total buying power (${total_bp:.2f}) to buy {symbol}.")
                else:
                    # Check wash-sale cooldown
                    if symbol in self.state["wash_sale_cooldowns"]:
                        logger.warning(f"Skipping buy for {symbol} due to wash-sale cooldown until {self.state['wash_sale_cooldowns'][symbol]}.")
                    else:
                        await self.buy_position(session, symbol, ALLOCATION_PER_TRADE, price, is_settled=True)

            elif signal == "sell" and symbol in active_positions:
                # We want to sell
                pos = active_positions[symbol]
                gfv_locked = symbol in self.state["unsettled_buys"]
                if gfv_locked:
                    logger.warning(f"Skipping sell signal for {symbol} to prevent GFV (GFV Lock active today).")
                else:
                    await self.sell_position(session, symbol, pos["quantity"], price, "signal", pos["avg_cost"])

        logger.info("=== Bot Trading Run Complete ===")


    async def buy_position(self, session, symbol, usd_amount, current_price, is_settled=True):
        logger.info(f"PROPOSED BUY: ${usd_amount} of {symbol} at estimated price ${current_price:.2f} (Settled: {is_settled})")
        
        if self.dry_run:
            logger.info("[DRY RUN] Order simulation complete.")
            self.log_transaction({
                "action": "buy",
                "symbol": symbol,
                "usd_amount": usd_amount,
                "price": current_price,
                "is_settled": is_settled,
                "notes": "Simulated buy order in dry-run mode"
            })
            return

        ref_id = str(uuid.uuid4())
        try:
            logger.info("Placing live market buy order...")
            # For fractional shares we must use market orders and specify dollar_amount
            args = {
                "account_number": self.account_number,
                "symbol": symbol,
                "side": "buy",
                "type": "market",
                "dollar_amount": f"{usd_amount:.2f}",
                "ref_id": ref_id
            }
            order_res = await session.call_tool("place_equity_order", arguments=args)
            logger.info(f"Order placed response: {order_res.content[0].text}")
            
            # Log the purchase
            self.log_transaction({
                "action": "buy",
                "symbol": symbol,
                "usd_amount": usd_amount,
                "price": current_price,
                "is_settled": is_settled,
                "ref_id": ref_id,
                "notes": "Live buy order executed"
            })

            # If this buy was funded with unsettled cash, record it so we lock it from day trades
            if not is_settled:
                today_str = str(datetime.date.today())
                self.state["unsettled_buys"][symbol] = {
                    "buy_date": today_str,
                    "amount": usd_amount
                }
                self.save_state()

        except Exception as e:
            logger.error(f"Error placing buy order: {e}")

    async def sell_position(self, session, symbol, quantity, current_price, reason, avg_cost):
        logger.info(f"PROPOSED SELL: {quantity:.6f} shares of {symbol} at estimated price ${current_price:.2f} (Reason: {reason})")
        
        if self.dry_run:
            logger.info("[DRY RUN] Order simulation complete.")
            self.log_transaction({
                "action": "sell",
                "symbol": symbol,
                "quantity": quantity,
                "price": current_price,
                "reason": reason,
                "notes": "Simulated sell order in dry-run mode"
            })
            return

        ref_id = str(uuid.uuid4())
        try:
            logger.info("Placing live market sell order...")
            # For fractional shares we must use market orders and specify quantity
            args = {
                "account_number": self.account_number,
                "symbol": symbol,
                "side": "sell",
                "type": "market",
                "quantity": f"{quantity:.6f}",
                "ref_id": ref_id
            }
            order_res = await session.call_tool("place_equity_order", arguments=args)
            logger.info(f"Order placed response: {order_res.content[0].text}")

            # Check if this sale was at a loss to trigger wash sale cooldown
            sale_value = quantity * current_price
            cost_basis = quantity * avg_cost
            realized_pnl = sale_value - cost_basis
            
            # Add sale proceeds to today's unsettled cash list
            self.state["today_sales"].append(sale_value)
            
            # If sold at a loss, add to wash-sale cooldown for 31 days
            if realized_pnl < 0:
                cooldown_exp = str(datetime.date.today() + datetime.timedelta(days=31))
                self.state["wash_sale_cooldowns"][symbol] = cooldown_exp
                logger.warning(f"Realized loss of ${abs(realized_pnl):.2f} on {symbol}. Adding to wash-sale cooldown until {cooldown_exp}.")
            
            self.save_state()

            # Log the transaction
            self.log_transaction({
                "action": "sell",
                "symbol": symbol,
                "quantity": quantity,
                "price": current_price,
                "reason": reason,
                "realized_pnl": realized_pnl,
                "ref_id": ref_id,
                "notes": "Live sell order executed"
            })

        except Exception as e:
            logger.error(f"Error placing sell order: {e}")

async def run_bot_once(dry_run, account_number):
    command = "npx.cmd" if sys.platform == "win32" else "npx"
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "mcp-remote", "https://agent.robinhood.com/mcp/trading"]
    )
    
    bot = TradingBot(account_number=account_number, dry_run=dry_run)
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await bot.execute_run(session)
    except Exception as e:
        logger.exception("Fatal error during bot execution:")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Robinhood Agentic Trading Bot")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run bot in simulation mode (no live trades)")
    parser.add_argument("--live", action="store_true", default=False, help="Run bot in live execution mode (real money trades)")
    parser.add_argument("--loop", action="store_true", default=False, help="Run bot in an infinite loop")
    parser.add_argument("--interval-sec", type=int, default=900, help="Loop sleep interval in seconds (default: 900s)")
    parser.add_argument("--account", type=str, default=None, help="Robinhood brokerage account number")
    args = parser.parse_args()

    # Default to dry-run unless --live is explicitly set
    is_dry = not args.live
    if not is_dry:
        logger.warning("!!! WARNING: RUNNING BOT IN LIVE MODE (REAL MONEY TRADING ACTIVE) !!!")
    else:
        logger.info("Running bot in DRY RUN (simulation) mode.")

    account_num = args.account or os.environ.get("ROBINHOOD_ACCOUNT_NUMBER")
    if not account_num:
        logger.error("Robinhood account number must be specified via --account CLI arg or ROBINHOOD_ACCOUNT_NUMBER env variable.")
        sys.exit(1)

    async def loop_runner():
        while True:
            await run_bot_once(is_dry, account_num)
            if not args.loop:
                break
            logger.info(f"Sleeping for {args.interval_sec} seconds before next run...")
            await asyncio.sleep(args.interval_sec)

    asyncio.run(loop_runner())
