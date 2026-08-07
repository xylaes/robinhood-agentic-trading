# 🧠 Multi-Asset Trading Strategy Architecture

This document defines the quantitative strategies, risk parameters, asset allocation buckets, and regulatory compliance rules for the **Robinhood AI Portfolio Manager**.

---

## 📊 3-Bucket Capital Allocation Framework

Capital is systematically partitioned across three distinct strategy buckets:

```
                  ┌─────────────────────────────────────────┐
                  │    Robinhood Agentic Portfolio ($150)    │
                  └────────────────────┬────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
┌──────────────┐               ┌──────────────┐               ┌──────────────┐
│  Bucket 1:   │               │  Bucket 2:   │               │  Bucket 3:   │
│   Options    │               │    Crypto    │               │   Equities   │
│  ($50.00)    │               │  ($50.00)    │               │  (~$50.00)   │
└──────────────┘               └──────────────┘               └──────────────┘
```

---

## 💡 Beginner-Friendly Strategy Guides

### 1. 📊 Equities Bucket (~$50.00 Allocation) — Buying Quality Stocks "On Sale"
* **Beginner Explanation**: Think of quality stocks (like NVIDIA or the S&P 500 ETF) like items at a store. Sometimes their prices dip temporarily below their true value. We use mathematical meters (**RSI** and **Bollinger Bands**) to find when a stock is temporarily "on sale" (oversold), buy a small fractional position, and automatically lock in profits (+4%) when it bounces back.
* **Quantitative Rules**:
  - **RSI (14-period)**: BUY when RSI < 35 (Oversold); SELL when RSI > 70 (Overbought).
  - **MACD (12, 26, 9)**: Bullish crossover (`MACD > Signal`) triggers accumulation.
  - **Bollinger Bands (20-period)**: Touch of lower band confirms oversold entry.
* **Risk Boundaries**:
  - **Take Profit**: **+4.00%** gain over cost basis.
  - **Stop Loss**: **-2.00%** loss limit below cost basis.

---

### 2. 🎯 Options Bucket ($50.00 Allocation) — "Discount Coupons" with High Odds
* **Beginner Explanation**: Instead of buying 100 full shares of a stock for $1,000+, we buy a **High-Delta In-The-Money Call Option** for $25 – $35. Think of it like buying a **high-percentage discount coupon** that controls 100 shares for a week. Because the stock is already trading above our coupon's strike price, **over 80% of statistical outcomes end in profit**.
* **Quantitative Rules**:
  - **Account Level**: Robinhood Level 2 Approval (`option_level_2`).
  - **Delta Target**: **0.75 to 0.85+** (75% – 85%+ statistical win rate).
  - **Expiration**: 14 to 45 Days out.
  - **Position Sizing**: **$15.00 – $40.00** total premium per trade (capped max risk).
  - **Target Gain**: **+20% to +35% profit** on contract premium.

---

### 3. 🪙 Crypto Bucket ($50.00 Allocation) — 24/7 Off-Hours Momentum
* **Beginner Explanation**: Traditional stock markets close at 4:00 PM EST and stay shut on weekends. **Crypto markets never close** — they trade 24 hours a day, 7 days a week. The AI agent monitors top-tier digital assets (`BTC`, `ETH`, `SOL`, `DOGE`) around the clock to capture momentum when traditional stock exchanges are offline.
* **Quantitative Rules**:
  - **Watchlist**: Dedicated Robinhood Watchlist **"Agentic Crypto" 🪙** (`235bdcfb-652c-49f8-8733-adce9afafcdf`).
  - **Tracked Assets**: `BTC-USD` (Bitcoin), `ETH-USD` (Ethereum), `SOL-USD` (Solana), `DOGE-USD` (Dogecoin).
  - **Execution**: Continuous quote monitoring and watchlist synchronization via Robinhood MCP.

---

## 🛡️ Regulatory & Legal Compliance Framework

1. **FINRA Rule 4210 (PDT Protection)**:
   - Rolling 5-day day-trade tracking capping intraday roundtrips at a maximum of **2 day-trades per 5 rolling business days**.
2. **SEC Regulation T (GFV Lock)**:
   - Enforces cash-account settlement tracking (`unsettled_buys`), prohibiting same-day liquidation of positions bought with unsettled funds.
3. **IRS Code § 1091 (Wash Sale Disallowance)**:
   - Automatically logs 31-day wash-sale cooldowns on liquidated loss positions and blocks re-entry during cooldown (e.g. QQQ restricted through Aug 17, 2026).
4. **Pre-Trade Compliance Disclosures (Robinhood MCP Protocol)**:
   - Mandates order simulation review (`review_equity_order` & `review_option_order`) inspecting bid/ask spreads, regulatory fees ($0.04 total), and broker compliance alerts (`order_checks`) prior to live execution.
