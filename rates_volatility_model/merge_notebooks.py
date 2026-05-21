"""Merge all parts into single notebook"""

import nbformat as nbf

BASE = "/home/kazumasa/projects/rates_volatility_model"

parts = [
    ("Part 1 (Ch0-Ch2)", f"{BASE}/rates_volatility_models_part1.ipynb"),
    ("Part 2 (Ch3-Ch6)", f"{BASE}/rates_volatility_models_part2.ipynb"),
    ("Part 3 (Ch7-Ch10+Final)", f"{BASE}/rates_volatility_models_part3.ipynb"),
    ("Ch11 (Smile/Skew)", f"{BASE}/rates_volatility_models_smile.ipynb"),
]

all_cells = []
for label, path in parts:
    with open(path) as f:
        nb = nbf.read(f, as_version=4)
    all_cells += nb.cells
    print(f"  {label}: {len(nb.cells)} cells")

nb_final = nbf.v4.new_notebook()
nb_final.cells = all_cells

output_path = f"{BASE}/rates_volatility_models.ipynb"
with open(output_path, "w") as f:
    nbf.write(nb_final, f)

print(f"✓ Merged notebook created: {output_path}")
print(f"  Total: {len(all_cells)} cells")
