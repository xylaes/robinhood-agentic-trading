# 📖 Operational Showcase & Usage Guide

This guide explains how technical and non-technical stakeholders can deploy, monitor, and showcase the **Robinhood Agentic Portfolio Manager**.

---

## ⚠️ Financial & Legal Disclaimer (Use at Your Own Risk)

> **DISCLAIMER**: This repository, software, and documentation are provided strictly for **educational, portfolio showcase, and research purposes only**.
>
> * **No Financial Advice**: Nothing contained in this codebase, documentation, or generated reports constitutes financial, investment, legal, or tax advice.
> * **High-Risk Investment Warning**: All trading across equities, options, and cryptocurrencies involves significant risk of monetary loss. Extended-hours trading (24/5 Blue Ocean sessions) and cryptocurrency markets carry heightened volatility and liquidity risks.
> * **Provided "AS IS" Without Warranty**: As set forth in the MIT License, this software is provided "AS IS", without warranty of any kind, express or implied. The authors and contributors assume **zero responsibility or legal liability** for any financial losses, execution errors, broker outages, API failures, or damages resulting from the use or misuse of this software.
> * **User Responsibility**: Users are solely responsible for validating order parameters, conducting independent research, and complying with all applicable FINRA, SEC, and local financial regulations.

---

## ⏰ Recommended Execution Schedules

When running the AI agent automatically, set schedule frequencies based on asset class volatility and market operating hours:

| Asset Class / Bucket | Recommended Schedule Frequency | Active Session Hours | Objective |
| :--- | :--- | :--- | :--- |
| **Equities & 24/5 ETFs** | **Hourly** (`0 * * * *`) | Mon–Fri 24/5 (Blue Ocean ATS Session) | Monitor RSI oversold setups & take-profit / stop-loss boundaries |
| **Level 2 Options** | **Hourly or Pre-Market** | Mon–Fri, 9:30 AM – 4:00 PM EST | Scan High-Delta ITM Calls & manage option expirations |
| **24/7 Crypto** | **Every 4 Hours** (`0 */4 * * *`) | 24 Hours / 7 Days a Week | Track Bitcoin, Ethereum, Solana, and Dogecoin momentum |

---

## 🖥️ How to Showcase to Non-Technical Audiences

### 1. View Live Portfolio Metrics (HTML Dashboard)
Open [**`portfolio_dashboard.html`**](file:///c:/Users/danny/OneDrive/Desktop/my-first-project/portfolio_dashboard.html) in any web browser.
* **Capital Allocation Chart**: Visual breakdown of settled cash ($139.30) vs. equity positions ($10.37).
* **Holdings Table**: Real-time unrealized gains (e.g. `NVDA` **+17.80%**, `SPY` **+3.73%**).
* **Order Audit Cards**: Real-time status of queued pending orders with total fees ($0.04).

### 2. Inspect AI Decision Logs (Agent Journal)
Open [**`agent_journal.md`**](file:///c:/Users/danny/OneDrive/Desktop/my-first-project/agent_journal.md).
* Demonstrates how the AI agent calculates indicators (RSI 69.97, MACD), enforces wash-sale cooldowns, and performs pre-trade compliance reviews (`order_checks: {}`).

---

## 🚀 Workstation Portability & Security

* **Zero PII Exposure**: No account numbers or personal credentials are saved in code. Account IDs resolve dynamically via environment variables (`ROBINHOOD_ACCOUNT_NUMBER`) or MCP token discovery.
* **5-Second Connection Test**: Run `python test_connection.py` on a new workstation to verify Robinhood MCP authorization without submitting trades.
