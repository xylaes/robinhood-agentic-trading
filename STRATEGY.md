# 🧠 Multi-Asset Trading Strategy Architecture

This document defines the quantitative strategy, risk parameters, asset allocation buckets, and regulatory compliance rules for the **Robinhood AI Portfolio Manager**.

---

## 📊 3-Bucket Capital Allocation Framework

Capital is systematically partitioned across three distinct strategy buckets to balance steady growth, portfolio protection, and 24/7 momentum:

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

### Bucket 1: Agentic Options Strategy ($50.00 Allocation)

* **Account Requirement**: Robinhood Level 2 Options Approval (`option_level_2`).
* **Core Strategy**: **High-Delta In-The-Money (ITM) Calls** on market leaders (`NVDA`, `SPY`, `QQQ`, `F`, `SOFI`, `INTC`).
* **Selection Criteria**:
  - **Delta Range**: **0.75 to 0.85+** (75% to 85%+ statistical win probability).
  - **Expiration**: 14 to 45 Days out (providing ample time for trend development).
  - **Position Sizing**: **$15.00 – $40.00** total premium per trade (capped max risk).
* **Target Profit & Risk**:
  - **Take Profit Target**: **+20% to +35% gain** on contract premium.
  - **Maximum Risk**: Strictly capped at premium paid ($15 – $40). Zero margin/unlimited loss risk.
* **Pre-Trade Compliance**: Pre-trade order simulation via `review_option_order` inspecting bid/ask spreads, regulatory fees ($0.04 total), and `order_checks`.

---

### Bucket 2: Agentic Crypto Strategy ($50.00 Allocation)

* **Watchlist**: Dedicated Robinhood Watchlist **"Agentic Crypto" 🪙** (ID: `235bdcfb-652c-49f8-8733-adce9afafcdf`).
* **Tracked Currency Pairs**:
  1. `BTC-USD` (Bitcoin)
  2. `ETH-USD` (Ethereum)
  3. `SOL-USD` (Solana)
  4. `DOGE-USD` (Dogecoin)
* **Strategy & Execution**:
  - 24/7 quote monitoring and watchlist synchronization via `search` and `get_watchlist_items`.
  - Captures weekend and off-hours market momentum while traditional equity exchanges are closed.

---

### Bucket 3: Standard Equities Strategy (~$50.00 Total: Cash + Holdings)

* **Watchlist Universe**: `NVDA`, `QQQ`, `SPY`, `AAPL`.
* **Technical Indicator Rules (1-Hour Interval)**:
  - **RSI (14-period)**:
    * **BUY**: RSI < 35 (Oversold setup).
    * **SELL / TAKE PROFIT**: RSI > 70 (Overbought setup).
  - **MACD (12, 26, 9)**:
    * Bullish crossover (`MACD > Signal`) triggers long accumulation.
    * Bearish crossover (`MACD < Signal`) triggers distribution.
  - **Bollinger Bands (20-period, 2 std)**:
    * Lower Band touch: Oversold dip-buy confirmation.
    * Upper Band touch: Overbought profit-taking confirmation.
* **Risk Control Rules**:
  - **Take Profit**: **+4.00%** gain over average cost basis.
  - **Stop Loss**: **-2.00%** loss limit below average cost basis.

---

## 🛡️ Regulatory & Legal Compliance Framework

1. **Pattern Day Trading (PDT) Protection (FINRA Rule 4210)**:
   - Rolling 5-day day-trade tracking for accounts under $25,000 net worth.
   - Caps intraday roundtrips at a maximum of **2 day-trades per 5 business days**.
2. **Good Faith Violation (GFV) Lock (SEC Regulation T)**:
   - Enforces cash-account settlement tracking (`unsettled_buys`).
   - Prohibits same-day liquidation of positions opened with unsettled funds until settlement completes (T+1).
3. **IRS Wash Sale Disallowance (IRS Code § 1091)**:
   - Automatically logs 31-day wash-sale cooldowns on liquidated loss positions.
   - Restricts re-entry on watchlisted assets under active wash-sale cooldowns (e.g., QQQ restricted through Aug 17, 2026).
4. **Pre-Trade Compliance Disclosures (Robinhood MCP Protocol)**:
   - Mandates order simulation review (`review_equity_order` & `review_option_order`) prior to order placement.
