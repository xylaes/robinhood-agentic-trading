# Robinhood Agentic Trading - Workspace Agent Guidelines

## ⚡ Autonomous Execution Guidelines
1. **Python Virtual Environment**:
   - Always run Python scripts using .venv\Scripts\python.exe (Windows) to ensure all MCP and crypto dependencies (mcp, cryptography, requests, dotenv) are available.
2. **Direct Single-Shot Execution**:
   - When requested to run portfolio_manager.py or scheduled cycles, execute the command directly using run_command without creating planning artifacts (implementation_plan.md), blocking for interactive reviews, or prompting for unnecessary intermediate permissions.
3. **Robinhood Account Resolution**:
   - Target the agentic trading sub-account (...8015) automatically.
4. **Exact Command Invariance (Zero-Friction Approval Matching)**:
   - For all scheduled daily briefings and synchronization runs, ALWAYS use the exact command string verbatim:
     `.venv\Scripts\python.exe portfolio_manager.py --branch full`
     Do not vary arguments, formatting, or paths so that Antigravity's "Always Allow" rule permanently matches every daily run.
5. **Interactive Next Steps & Actionable Multiple-Choice Options**:
   - At the conclusion of every portfolio synchronization or scheduled briefing, never conclude with only a passive summary.
   - Always present the user with a clear, actionable multiple-choice menu of next steps (e.g., using `ask_question` or structured selectable options), such as:
     1. 🚀 **Execute Simulated Order(s) Live**: Authorize live trade execution for the current top candidates (e.g., Crypto dip-buy or Equity opportunities).
     2. 🔄 **Trigger Rebalancing Action**: Deploy available uninvested cash reserves into underweight buckets.
     3. 📊 **Inspect Full Executive Digest**: View detailed breakdown in `PORTFOLIO_ANALYSIS.md`.
     4. ⚙️ **Adjust Allocation Targets**: Reconfigure bucket benchmarks (60/40 Equities/Crypto) or risk tolerances.
     5. ⏸️ **Dismiss / Keep Monitoring**: Acknowledge the briefing and resume scheduled hourly tracking.
