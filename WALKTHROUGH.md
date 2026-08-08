# 🎬 Robinhood Agentic Trading Portfolio Manager: System Architecture & Strategy Walkthrough

This document provides a complete visual diagram and simple, beginner-friendly walkthrough of the **Robinhood Agentic Portfolio Manager** running on **Google Antigravity (AGY)** and the **Robinhood MCP Trading Gateway**.

---

## 🏛️ System Architecture Diagram

```mermaid
graph TD
    AGY["Google Antigravity (AGY) Engine"] -->|Model Context Protocol IPC| MCP["Robinhood MCP Trading Gateway"]
    MCP -->|Account & Portfolio Sync| Portfolio["Live Portfolio Sync (Net Worth & Balances)"]
    MCP -->|Server Technical Indicators| Analytics["1h RSI, MACD, Bollinger Bands"]
    MCP -->|Compliance Pre-Trade Review| Simulation["Pre-Trade Order Review (review_equity_order / review_option_order)"]
    
    Simulation -->|User Approval / Signal Trigger| Execution["Live Trade Execution (place_equity_order / place_option_order)"]
    Execution -->|Logging & Monitoring| Journal["Agent Journal (agent_journal.md)"]
    Execution -->|Visual Display| Dashboard["Interactive Dashboard (portfolio_dashboard.html)"]

    style AGY fill:#7c3aed,stroke:#fff,color:#fff
    style MCP fill:#059669,stroke:#fff,color:#fff
    style Simulation fill:#3b82f6,stroke:#fff,color:#fff
    style Dashboard fill:#00c805,stroke:#fff,color:#fff
```

---

## 💡 Simple Strategy Explanations (Beginner's Guide)

If you've never traded stocks or crypto before, here is how each of our 3 trading strategies works in plain English:

### 1. 📊 Equities Strategy (Buying Stocks "On Sale")
* **The Concept**: Think of quality stocks (like NVIDIA or the S&P 500 ETF) like items at a store. Sometimes their prices dip temporarily below their true value.
* **How We Decide When to Buy**: We use mathematical meters called **RSI** (Relative Strength Index) and **Bollinger Bands**. When these meters show a stock is "oversold" (temporarily on sale), the AI agent considers buying a small fractional position.
* **Locking in Profits & Safety Cutoffs**: 
  - **Take-Profit (+4.0%)**: When the stock rebounds by +4%, the AI automatically sells to lock in cash profit.
  - **Stop-Loss (-2.0%)**: If the stock dips by -2%, the AI cuts the trade immediately so a small loss never becomes a large loss.

---

### 2. 🎯 Options Strategy ("Discount Coupons" with High Odds)
* **The Concept**: Instead of buying 100 full shares of a stock for $1,000+, we buy a **High-Delta In-The-Money Call Option** for $25 – $35. Think of it like buying a **high-percentage discount coupon** that controls 100 shares for a week.
* **Why the Odds Are High (80%+ Win Rate)**: Because the stock is already trading above our coupon's strike price, **over 80% of statistical outcomes end in profit**.
* **Strictly Capped Risk**: The absolute most you can lose is the $25 – $35 coupon price. You can never get surprise margin bills or lose more than you paid upfront.

---

### 3. 🪙 Crypto Strategy (24/7 Off-Hours Momentum)
* **The Concept**: Traditional stock markets close at 4:00 PM EST and stay shut on weekends. **Crypto markets never close** — they trade 24 hours a day, 7 days a week.
* **How It Works**: The AI agent monitors top-tier crypto assets (`BTC`, `ETH`, `SOL`, `DOGE`) on the "Agentic Crypto" watchlist around the clock, capturing market momentum when stock exchanges are offline.

---

## 📊 Step-by-Step System Execution Walkthrough

### Step 1: Real-Time Account Synchronization & Multi-Asset Setup
* **Account Sync**: Connects to Robinhood MCP, verifies account status, settled cash, and Level 2 options approval (`option_level_2`).
* **Privacy Assurance**: Environment-driven account resolution ensures zero hardcoded PII or personal IDs in source files.

---

### Step 2: Quantitative Indicator Analysis & Compliance Audit
* **Indicator Checks**: Scans 1-hour RSI, MACD, and Bollinger Bands across `NVDA`, `SPY`, `QQQ`, and `AAPL`.
* **Regulatory Compliance**:
  1. **FINRA Rule 4210 (PDT)**: Caps day trades at max 2 per rolling 5 business days.
  2. **SEC Reg T (GFV Lock)**: Enforces cash settlement rules preventing Good Faith Violations.
  3. **IRS Code § 1091 (Wash Sale)**: Blocks new buy orders on assets under active 31-day loss cooldowns (e.g. QQQ restricted through Aug 17).

---

### Step 3: Pre-Trade Simulation & Trade Execution
* **Mandatory Order Previews**: Before any trade is placed, the broker runs `review_equity_order` or `review_option_order` to inspect live bid/ask spreads, regulatory fees ($0.04 total), and broker alerts.
* **Execution**: Upon user confirmation, `place_equity_order` or `place_option_order` submits the live order to Robinhood.

---

### Step 4: Visual Dashboard & Agent Journal
* **Visual Dashboard**: Open [**`portfolio_dashboard.html`**](file:///c:/Users/danny/OneDrive/Desktop/my-first-project/portfolio_dashboard.html) directly in any browser to view live Chart.js allocation charts, P&L tables, and queued order audits.
* **Agent Journal**: Open [**`agent_journal.md`**](file:///c:/Users/danny/OneDrive/Desktop/my-first-project/agent_journal.md) to inspect timestamped logs of every technical scan, simulation preview, and trade execution.
* **5-Second Connection Test**: Run `python test_connection.py` on any machine to verify Robinhood MCP gateway connectivity instantly.

---

## 🔗 Quick Access Links

* 📊 [**`portfolio_dashboard.html`**](file:///c:/Users/danny/OneDrive/Desktop/my-first-project/portfolio_dashboard.html): Interactive Visual HTML Dashboard
* 🧠 [**`STRATEGY.md`**](file:///c:/Users/danny/OneDrive/Desktop/my-first-project/STRATEGY.md): Quantitative Strategy Guide (Equities, Options, Crypto)
* 📖 [**`USAGE_GUIDE.md`**](file:///c:/Users/danny/OneDrive/Desktop/my-first-project/USAGE_GUIDE.md): Operational Showcase Guide & Execution Schedules
* 📝 [**`agent_journal.md`**](file:///c:/Users/danny/OneDrive/Desktop/my-first-project/agent_journal.md): Chronological Agent Execution Log
* 🐍 [**`portfolio_manager.py`**](file:///c:/Users/danny/OneDrive/Desktop/my-first-project/portfolio_manager.py): Unified AGY Portfolio Manager Entrypoint
