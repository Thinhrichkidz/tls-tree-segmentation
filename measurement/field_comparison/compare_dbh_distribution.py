"""Distribution-level DBH comparison: field inventory (TreeData.csv, site WSF_ML2A) vs TLS v6 FINAL.
Not tree-by-tree: the inventory has quadrant + tag only, no coordinates or heights."""
import csv, statistics as st, bisect
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "D:/22083142/"
V6 = R + "outputs/WSL_ML2A/55x55/3cm/Codex_help/measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028/results/tree_attributes.csv"
f = lambda s: float(s) if s.strip() not in ("", "NA") else None
inv = [r for r in csv.DictReader(open(R + "TreeData.csv", encoding="utf-8-sig")) if r["site_id"] == "WSF_ML2A"]
tls = list(csv.DictReader(open(V6, encoding="utf-8")))
live = [f(r["dbh1"]) for r in inv if r["live_dead1"].lower() == "l" and f(r["dbh1"])]
allf = [f(r["dbh1"]) for r in inv if f(r["dbh1"])]
meas = [f(r["dbh_cm"]) for r in tls if f(r["dbh_cm"])]
est = [f(r["dbh_estimated_cm"]) for r in tls if f(r["dbh_estimated_cm"])]
valid = [f(r["dbh_cm"]) for r in tls if r["dbh_status"] == "VALID"]
def q(x, p): x = sorted(x); return x[round(p * (len(x) - 1))]
def ks(a, b):
    a, b = sorted(a), sorted(b)
    return max(abs(bisect.bisect_right(a, v) / len(a) - bisect.bisect_right(b, v) / len(b)) for v in a + b)
sets = {"field all stems1 (n=%d)" % len(allf): allf, "field live dbh1": live,
        "TLS measured (VALID+REVIEW)": meas, "TLS VALID only": valid, "TLS measured + ESTIMATED": meas + est}
rows = [["set", "n", "min", "p25", "median", "p75", "max", "KS vs field-live"]]
for k, v in sets.items():
    rows.append([k, len(v), min(v), q(v, .25), st.median(v), q(v, .75), max(v), round(ks(v, live), 3)])
w = csv.writer(open("dbh_distribution_summary.csv", "w", newline="")); w.writerows(rows)
for r in rows: print(r)
print("field dbh>=10:", sum(x >= 10 for x in live), " TLS meas>=10:", sum(x >= 10 for x in meas), " TLS any>=10:", sum(x >= 10 for x in meas + est))
plt.figure(figsize=(6, 4))
for k, v in list(sets.items())[1:]:
    v = sorted(v); plt.step(v, [(i + 1) / len(v) for i in range(len(v))], where="post", label=k)
plt.xlabel("DBH (cm)"); plt.ylabel("ECDF"); plt.legend(fontsize=7); plt.tight_layout(); plt.savefig("dbh_ecdf.png", dpi=200)

# --- Way B: combined stems (basal-area-equivalent diameter) vs Way A: largest stem (dbh1 above) ---
def stems(r): return [f(r["dbh%d" % i]) for i in range(1, 12) if f(r["dbh%d" % i]) and r["live_dead%d" % i].lower() == "l"]
comb = [sum(d * d for d in s) ** .5 for s in map(stems, inv) if s]
print("multi-stem live trees:", sum(len(stems(r)) > 1 for r in inv), "of", len(comb))
out = [["way", "n", "p25", "median", "p75", "max", "KS vs TLS measured", "KS vs TLS meas+EST", "KS vs TLS VALID"]]
for k, v in {"A largest stem (dbh1, live)": live, "B combined stems": comb}.items():
    out.append([k, len(v), q(v, .25), st.median(v), q(v, .75), max(v), round(ks(v, meas), 3), round(ks(v, meas + est), 3), round(ks(v, valid), 3)])
csv.writer(open("dbh_way_A_vs_B.csv", "w", newline="")).writerows(out)
for r in out: print(r)
