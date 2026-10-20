"""Figure: ECDF of first-slot diameter (dbh1) by site-ID prefix, excluding
explicit log/stump labels. Same cleaning rules as audit_inventory.py.
Usage: python3 -I make_fig_dbh.py TreeData.csv out.pdf
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

src, dst = sys.argv[1], sys.argv[2]
df = pd.read_csv(src, dtype=str, keep_default_na=False, encoding="utf-8-sig")
df = df.apply(lambda s: s.str.strip())
d = df[(df.site_id != "") & ~df.species.isin(["log", "stump", "stump log"])].copy()
d["prefix"] = d.site_id.str.extract(r"^(DSF|WSF|RF)", expand=False)
d["dbh1"] = pd.to_numeric(d.dbh1.replace("", np.nan))

plt.rcParams.update({"font.family": "serif", "font.size": 8,
                     "axes.edgecolor": "#52514e", "axes.linewidth": 0.6,
                     "xtick.color": "#52514e", "ytick.color": "#52514e"})
fig, ax = plt.subplots(figsize=(3.4, 1.6))
style = {"DSF": ("#2a78d6", "-"), "WSF": ("#eb6834", "--"), "RF": ("#1baf7a", ":")}
for p, (col, ls) in style.items():
    x = np.sort(d.loc[d.prefix == p, "dbh1"].dropna().to_numpy())
    y = np.arange(1, len(x) + 1) / len(x)
    ax.step(x, y, where="post", color=col, ls=ls, lw=1.6,
            label=f"{p} (n={len(x)})")
ax.legend(loc="lower right", frameon=False, fontsize=7, handlelength=2.4)
ax.set_xscale("log")
ax.set_xticks([2, 5, 10, 20, 50, 100, 200])
ax.set_xticklabels(["2", "5", "10", "20", "50", "100", "200"])
ax.set_xlabel("dbh1 (file units, unconfirmed; log scale)")
ax.set_ylabel("Cumulative share")
ax.grid(True, which="major", color="#e6e5e1", lw=0.5)
ax.set_axisbelow(True)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
ax.axvline(10, color="#8a8984", lw=0.6)
fig.tight_layout(pad=0.3)
fig.savefig(dst)
