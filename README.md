# 🤖 Robinhood Agentic Trading Bot

An automated, risk-managed trading bot designed to trade fractional shares of highly liquid equities/ETFs on a Robinhood cash account, using the **Model Context Protocol (MCP)**. 

The bot runs as a **lightweight local Python script** to avoid running AI token costs, while utilizing a reasoning LLM Agent (via Antigravity Scheduled Tasks) to act as a discretionary portfolio manager.

---

## 🎯 Key Features

* **Dual EMA & RSI Strategy**: Computes 9/21 EMA crossovers and 14-period Relative Strength Index (RSI) on 1-hour historical bars to identify market trends and capitulation bottoms.
* **Capital-Efficient Fractional Trading**: Uses Robinhood's fractional market order API to trade precise USD amounts (e.g., $10.00/trade) of premium assets (SPY, QQQ, NVDA, AAPL).
* **Dynamic Watchlist Loading**: Dynamically loads the list of assets to trade from a custom Robinhood watchlist named `"Agentic"`. This allows you to add or remove assets for the bot to trade directly from your Robinhood mobile/web app without editing code. If not found, it falls back to the default list (`QQQ`, `SPY`, `NVDA`, `AAPL`).
* **Earnings Blackout Risk Guardrail**: Automatically queries upcoming earnings dates and blocks new buy orders if a company reports earnings within the next 3 days (72 hours), protecting the account from high-volatility overnight gap risk.
* **Good Faith Violation (GFV) Lock**: Restricts trades to settled cash only. If an asset is bought with unsettled proceeds, it applies a strict selling lock until the next business day ($T+1$ settlement), completely avoiding cash account violations.
* **Wash-Sale Protection**: Automatically triggers a 31-day re-buy cooldown on any ticker sold at a loss to protect tax write-off eligibility.
* **Idempotency Safeguard**: Employs UUID-based `ref_id` keys on all trade executions to prevent double-order placement during network drops.
* **Local Auditing**: Appends all decisions, charts, and market assessments chronologically to a central `agent_journal.md` file.

---

## 📂 Repository Structure

```text
├── trading_bot.py       # Core bot execution script
├── run_bot.bat          # Batch runner for Windows
├── requirements.txt     # Python dependencies (mcp, pandas, numpy)
├── .gitignore           # Ignores local logs and state files
└── README.md            # Project documentation (this file)
```

---

## ⚙️ Setup Instructions

### 1. Prerequisites
Ensure you have Python 3.10+ and Node.js (v18+) installed.

### 2. Configure Virtual Environment & Dependencies
```bash
# Initialize venv
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows

# Install requirements
pip install -r requirements.txt
```

### 3. Connect to the Robinhood MCP
Run the initial connection using `mcp-remote` to link your credentials. A secure browser window will open automatically to approve access:
```bash
npx -y -p mcp-remote@latest mcp-remote-client https://agent.robinhood.com/mcp/trading
```
*Note: Tokens are saved securely in `~/.mcp-auth/` so you do not need to re-authenticate on subsequent runs.*

### 4. Running the Bot
* **Dry-Run (Simulation)**: Check signals without placing real money orders:
  ```bash
  .\run_bot.bat --dry-run
  ```
* **Live Execution**: Place market orders using your account balance:
  ```bash
  .\run_bot.bat --live
  ```
* **Continuous Monitoring Loop**: Set the bot to run indefinitely every 15 minutes:
  ```bash
  .\run_bot.bat --live --loop --interval-sec 900
  ```

---

## ⚠️ Risk & Tax Disclosures

1. **Financial Risk**: Quantitative swing-trading carries risks. Assets can gap down or experience high slippage. Do not fund your agentic account with more capital than you are prepared to lose.
2. **Short-Term Capital Gains**: Frequent swing trading realizes short-term gains, which are taxed as ordinary income rather than lower long-term capital gains rates.
3. **PFOF Execution**: Robinhood uses a Payment for Order Flow model. Market orders are routed to market makers who profit from the bid-ask spread. We trade highly liquid large-cap tickers (SPY, QQQ) to keep spread costs to a fraction of a cent.
