# 📖 Robinhood Agentic Trading: User & Showcase Operational Guide

Welcome to the **Robinhood Agentic Trading Portfolio Manager** showcase guide. This document provides non-technical explanations, recommended execution schedules, and step-by-step instructions for showcasing and deploying this project.

---

## 🎯 Executive Project Overview (For Non-Technical Readers)

The **Robinhood Agentic Portfolio Manager** is an autonomous AI investment manager powered by **Google Antigravity (AGY)** and the **Robinhood MCP Trading Gateway**.

Rather than relying on emotional human trading or basic rule-based bots, this agent uses institutional quantitative analysis (RSI, MACD, Bollinger Bands) and strict regulatory safeguards to manage capital across **Equities**, **Options**, and **Crypto**.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Google Antigravity (AGY) AI Engine                    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                        (Model Context Protocol IPC)
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Robinhood MCP Trading Gateway                       │
└────────┬───────────────────────────┬───────────────────────────┬────────┘
         │                           │                           │
         ▼                           ▼                           ▼
 📊 Equities Bucket          🎯 Options Bucket           🪙 Crypto Bucket
 (~$50.00 Allocation)        ($50.00 Allocation)         ($50.00 Allocation)
```

---

## ⏰ Recommended Execution Schedules

To optimize performance and comply with broker rate limits and market hours, the AI Portfolio Manager operates on the following recommended schedule frequencies:

| Asset Class / Bucket | Recommended Schedule Frequency | Operational Hours | Objective |
| :--- | :--- | :--- | :--- |
| **Equities & ETFs** | **Hourly** (`0 * * * *`) | Mon–Fri, 9:30 AM – 4:00 PM EST | Monitor RSI oversold bounces & take-profit (+4.0%) / stop-loss (-2.0%) targets |
| **Level 2 Options** | **Hourly or Pre-Market** | Mon–Fri, 9:30 AM – 4:00 PM EST | Scan High-Delta ITM Calls (80%+ win rate) & manage option expirations |
| **24/7 Crypto** | **Every 4 Hours** (`0 */4 * * *`) | 24 Hours / 7 Days a Week | Track Bitcoin, Ethereum, Solana, and Dogecoin off-hours momentum |

---

## 🛡️ Regulatory Compliance & Risk Protection Matrix

This project enforces 4 mandatory financial regulatory protection rules directly inside the AI execution pipeline:

1. **FINRA Rule 4210 (Pattern Day Trading Protection)**:
   - Rolling 5-day day-trade tracking for accounts under $25,000 net worth.
   - Caps intraday buy-and-sell roundtrips at a maximum of **2 day-trades per 5 rolling business days**.
2. **SEC Regulation T (Good Faith Violation Lock)**:
   - Enforces cash-account settlement tracking (`unsettled_buys`).
   - Strictly blocks same-day liquidation of assets bought with unsettled proceeds until settlement completes (T+1).
3. **IRS Code § 1091 (Wash Sale Disallowance Protection)**:
   - Automatically logs 31-day wash-sale cooldowns whenever a position is closed at a loss.
   - Blocks new buy orders on watchlisted assets under active wash-sale cooldowns (e.g., QQQ restricted through Aug 17, 2026).
4. **Pre-Trade Compliance Preview (Robinhood MCP Regulations)**:
   - Mandates order simulation review (`review_equity_order` & `review_option_order`) prior to order placement.
   - Verifies bid/ask spreads, regulatory fees ($0.04 total), and broker compliance alerts (`order_checks`).

---

## 🖥️ Interactive Visual Dashboard & Journaling

* **Visual Health & Performance Dashboard**: Open [**`portfolio_dashboard.html`**](file:///c:/Users/danny/OneDrive/Desktop/my-first-project/portfolio_dashboard.html) directly in any browser to view live capital allocation charts, P&L tables, and queued order audits.
* **Chronological Agent Journal**: Open [**`agent_journal.md`**](file:///c:/Users/danny/OneDrive/Desktop/my-first-project/agent_journal.md) to inspect timestamped logs of every technical scan, simulation preview, and trade execution.
