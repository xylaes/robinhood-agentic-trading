# 🧠 Multi-Asset Trading Strategy Architecture

This document defines the quantitative strategies, risk parameters, asset allocation buckets, and regulatory compliance rules for the **Robinhood AI Portfolio Manager**.

---

## 📊 Capital Allocation & Tech-Forward Architecture

Capital is systematically partitioned across distinct strategy buckets, leveraging Robinhood's tech-forward features (**24/5 Market**, **Agentic Sandboxing**, **Event Contracts**, and **High-Yield Cash Sweep**):

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
        │                              │                              │
        └──────────────────────────────┼──────────────────────────────┘
                                       ▼
                     ┌──────────────────────────────────┐
                     │ Bucket 4: Event Contracts &      │
                     │ High-Yield Cash Sweep Reserve    │
                     └──────────────────────────────────┘
```

---

## 💡 Strategy Guides & Quantitative Execution Rules

### 1. 📊 Equities Bucket (~$50.00 Allocation) — Buying Quality Stocks & 24/5 Trading
* **Beginner Explanation**: Think of quality stocks (like NVIDIA or the S&P 500 ETF) like items at a store. Sometimes their prices dip temporarily below their true value. We use mathematical meters (**RSI** and **Bollinger Bands**) to find when a stock is temporarily "on sale" (oversold), buy a small fractional position, and automatically lock in profits (+4.0%) when it bounces back.
* **24/5 Extended Hours Trading (Blue Ocean ATS)**:
  - Takes advantage of Robinhood's **24 Hour Market** (Sunday 8:00 PM EST to Friday 8:00 PM EST).
  - Uses Extended Hours Limit Orders (`market_hours="extended_hours"`) to trade breaking earnings reports, macroeconomic releases, and Asian market session opens.
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

### 3. 🪙 Crypto Bucket ($50.00 Allocation) — 24/7 Off-Hours Momentum & Dip-Buying
* **Beginner Explanation**: Traditional stock markets close at 4:00 PM EST and stay shut on weekends. **Crypto markets never close** — they trade 24 hours a day, 7 days a week. When stock markets are closed on evenings and weekends, big price moves happen in crypto. We watch the top 4 digital assets (`BTC`, `ETH`, `SOL`, `DOGE`) around the clock. When a coin dips into oversold territory, the AI buys a $10–$25 slice and automatically sells when it bounces +5% for a fast profit.
* **Asset Categorization**:
  - **Core Trend Leaders**: `BTC-USD` (Bitcoin) & `ETH-USD` (Ethereum) — 70% of crypto capital.
  - **High-Beta Momentum**: `SOL-USD` (Solana) & `DOGE-USD` (Dogecoin) — 30% of crypto capital.
* **Quantitative Execution Rules**:
  - **Indicator Signals**:
    * **RSI Dip Buy**: BUY when 4-hour RSI < 38 (Oversold pullback).
    * **MACD Crossover**: BUY when 1-hour MACD line crosses above Signal line.
  - **Order Sizing**: **$10.00 – $25.00** dollar-based fractional orders.
  - **Take Profit**: **+5.00% to +8.00%** profit target.
  - **Stop Loss**: **-3.00%** loss limit.

---

### 4. 🎯 Bucket 4: Event Contracts & High-Yield Cash Sweep Reserve
* **Event Contracts & Prediction Markets (via Kalshi)**:
  - Trades binary $0.01 – $0.99 "Yes/No" contracts on Federal Reserve interest rate announcements, CPI inflation reports, and macroeconomic events.
  - Acts as a tail-risk macro hedge for equity positions. Realized P&L tracked via `get_pnl_trade_history`.
* **High-Yield Uninvested Cash Sweep**:
  - All uninvested settled cash automatically earns competitive APY interest (4.50%+ for Gold members) in FDIC-insured partner banks while waiting for technical dip-buy signals.

---

### 5. ⚖️ Automated Risk Exposure & Portfolio Rebalancing Engine
* **Target Benchmark**: Equal **33.33% / 33.33% / 33.33%** capital allocation target ($50.00 each across Equities, Options, and Crypto).
* **Drift Tolerance Threshold**: **±10.0%**. An automated rebalancing alert (`rebalance_required: true`) triggers whenever any asset bucket strays > 10% from benchmark.
* **Risk Exposure Metrics**:
  - **Cash Reserve Ratio**: Tracks percentage of uninvested capital.
  - **Concentration Risk**: Monitors active holdings count to prevent single-stock over-concentration.
* **Automated Capital Deployment**: Automatically directs uninvested cash reserves toward undershot buckets when technical dip signals or market opportunities occur.

---

## 🛡️ Regulatory & Legal Compliance Framework

1. **FINRA Rule 4210 (PDT Protection)**: Rolling 5-day day-trade tracking capping intraday roundtrips at a max of 2 per 5 days.
2. **SEC Regulation T (GFV Lock)**: Cash settlement tracking prohibiting same-day liquidation of positions bought with unsettled funds.
3. **IRS Code § 1091 (Wash Sale Disallowance)**: 31-day wash-sale cooldown logging and buy-blocking on loss positions.
4. **Pre-Trade Compliance Disclosures (Robinhood MCP Protocol)**: Mandates order simulation review (`review_equity_order` & `review_option_order`) prior to live execution.
