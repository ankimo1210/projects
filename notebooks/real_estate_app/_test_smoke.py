"""Quick smoke test for the real_estate_app package."""
import json
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import sim_engine
import charts

# Load default params
with open("config/default_params.json", "r") as f:
    raw = json.load(f)

# Convert string keys to int keys
for key in ("capex_schedule", "capex_expense_schedule",
            "capex_capital_schedule", "prepayment_schedule"):
    if key in raw and isinstance(raw[key], dict):
        raw[key] = {int(k): v for k, v in raw[key].items()}

# Run full analysis
results = sim_engine.run_full_analysis(raw)

m = results["metrics"]
print(f"Cap Rate:       {m['cap_rate']:.2%}")
print(f"Equity IRR:     {m['equity_irr']:.2%}")
print(f"Equity Multiple:{m['equity_multiple']:.2f}x")
print(f"Min DSCR:       {m['min_dscr']:.2f}")
print(f"Total Tax:      {m['total_tax_paid']:,.0f}")
print(f"Tax Drag:       {m['tax_drag_ratio']:.2%}")
print(f"annual_df rows: {len(results['annual_df'])}")
print(f"pl_df rows:     {len(results['pl_df'])}")
print(f"nav_df rows:    {len(results['nav_df'])}")
print()

# Test scenario analysis
scenario_df = sim_engine.run_scenario_analysis(results["params"])
print(f"Scenarios:      {len(scenario_df)} rows")

# Test ownership comparison
own = sim_engine.run_ownership_comparison(results["params"])
own_summary = sim_engine.build_ownership_comparison_summary(own)
print(f"Ownership comp: {len(own_summary)} rows")

# Test chart generation (no display)
import matplotlib
matplotlib.use("Agg")

fig = charts.plot_cumulative_cashflow_components(results["annual_df"])
print(f"Chart test:     OK (cumulative CF)")
import matplotlib.pyplot as plt
plt.close(fig)

print("\nAll tests passed!")
