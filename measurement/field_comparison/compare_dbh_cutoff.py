"""Way 1: all TLS DBH vs field. Way 2: TLS cut at the field minimum DBH (like-for-like size range).
Reports quantile error and a permutation p-value for the KS distance. Distribution-level only (no tree matching exists)."""
import csv, random, bisect, statistics as st
R = "D:/22083142/"
V6 = R + "outputs/WSL_ML2A/55x55/3cm/Codex_help/measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028/results/tree_attributes.csv"
f = lambda s: float(s) if s.strip() not in ("", "NA") else None
inv = [r for r in csv.DictReader(open(R + "TreeData.csv", encoding="utf-8-sig")) if r["site_id"] == "WSF_ML2A"]
tls = list(csv.DictReader(open(V6, encoding="utf-8")))
field = [f(r["dbh1"]) for r in inv if r["live_dead1"].lower() == "l" and f(r["dbh1"])]
meas = [f(r["dbh_cm"]) for r in tls if f(r["dbh_cm"])]
est = [f(r["dbh_estimated_cm"]) for r in tls if f(r["dbh_estimated_cm"])]
valid = [f(r["dbh_cm"]) for r in tls if r["dbh_status"] == "VALID"]
q = lambda x, p: sorted(x)[round(p * (len(x) - 1))]
def ks(a, b):
    a, b = sorted(a), sorted(b)
    return max(abs(bisect.bisect_right(a, v) / len(a) - bisect.bisect_right(b, v) / len(b)) for v in a + b)
def perm_p(a, b, n=2000):
    random.seed(1); d = ks(a, b); z = a + b; hit = 0
    for _ in range(n):
        random.shuffle(z); hit += ks(z[:len(a)], z[len(a):]) >= d
    return (hit + 1) / (n + 1)
cut = min(field)
out = [["way", "TLS set", "n", "median", "median err %", "p25 err %", "p75 err %", "KS", "perm p"]]
for way, c in (("1 no cutoff", 0), ("2 cutoff %.1f cm" % cut, cut)):
    for name, v in (("measured", meas), ("VALID", valid), ("measured+EST", meas + est)):
        v = [x for x in v if x >= c]
        e = lambda p: round(100 * (q(v, p) - q(field, p)) / q(field, p), 1)
        out.append([way, name, len(v), round(st.median(v), 1), e(.5), e(.25), e(.75), round(ks(v, field), 3), round(perm_p(v, field), 3)])
csv.writer(open("dbh_way1_vs_way2.csv", "w", newline="")).writerows(out)
print("field n=%d median=%.1f" % (len(field), st.median(field)))
for r in out: print(r)
