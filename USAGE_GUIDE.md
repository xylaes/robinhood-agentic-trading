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

## 🔑 Robinhood Crypto API Setup

To enable live 24/7 cryptocurrency trading via the official **Robinhood Crypto REST API**:

1. Run the keypair generator script:
   ```powershell
   .venv\Scripts\python scripts/generate_crypto_keys.py
   ```
2. Copy the printed **Base64 Public Key** and paste it into [Robinhood Crypto API Settings](https://robinhood.com/account/crypto).
3. Save the assigned **API Key** and **Private Key** into your local [`.env`](.env) file:
   ```env
   ROBINHOOD_CRYPTO_API_KEY=rh-api-your_api_key_here
   ROBINHOOD_CRYPTO_PRIVATE_KEY=your_generated_private_key_b64_here
   ```

---

## ⏰ Execution Scheduling (AGY UI)

For complete schedule options, copy-pasteable AGY `/schedule` prompts, and session window breakdowns, see [`SCHEDULE.md`](SCHEDULE.md).

| Strategy Branch | CLI Command | Suggested Frequency | Active Session Hours |
| :--- | :--- | :--- | :--- |
| **🟢 Full-Run (Option 1)** | `python portfolio_manager.py --branch full` | **Every 2 Hours** (`0 */2 * * *`) | Continuous 24/7 |
| **📈 Equities (Option 2)** | `python portfolio_manager.py --branch equities` | **Hourly** (`0 * * * *`) | Mon–Fri 24/5 (Blue Ocean ATS) |
| **🎯 Options (Option 2)** | `python portfolio_manager.py --branch options` | **Every 30 Minutes** | Mon–Fri, 9:30 AM – 4:00 PM EST |
| **🪙 Crypto (Option 2)** | `python portfolio_manager.py --branch crypto` | **Every 2 Hours** | 24 Hours / 7 Days a Week |

---

## 🖥️ How to Showcase to Non-Technical Audiences

### 1. View Live Executive Digest
Open [`PORTFOLIO_ANALYSIS.md`](PORTFOLIO_ANALYSIS.md) for a plain-English summary of portfolio health, asset bucket drift, active holdings, and macro catalysts.

### 2. View Live Portfolio Dashboard
Open [`portfolio_dashboard.html`](portfolio_dashboard.html) in any web browser.
* **Capital Allocation Chart**: Visual breakdown of settled cash vs. equity/crypto positions.
* **Holdings Table**: Real-time unrealized gains and position tracking.
* **Order Audit Cards**: Real-time status of queued pending orders with regulatory fee breakdowns ($0.04 total).

### 3. Inspect AI Decision Logs (Agent Journal)
Open [`agent_journal.example.md`](agent_journal.example.md).
* Demonstrates how the AI agent calculates indicators (RSI, MACD, Bollinger Bands), enforces wash-sale cooldowns, and performs pre-trade compliance reviews (`order_checks: {}`).

---

## 🚀 Workstation Portability & Security

* **Zero PII Exposure**: No account numbers or personal credentials are saved in code. Account IDs resolve dynamically via environment variables (`ROBINHOOD_ACCOUNT_NUMBER`) or MCP token discovery.
* **5-Second Connection Test**: Run `python test_connection.py` on a new workstation to verify Robinhood MCP authorization and Robinhood Crypto API authentication instantly.
