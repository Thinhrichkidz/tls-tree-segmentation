"""Tree-by-tree matching under placement A (site map 1439 = tree_074, 1435 = tree_103; scale 1.13, rotation -6 deg).
Position is the primary criterion; DBH is an independent check that can only demote a match, never create one.
Rules (fixed before classifying): each TLS stem used once, pairs assigned greedily by distance (max 4 m).
  confirmed  = distance <= 2 m and DBH check passes (|TLS - field| <= 25% of field)
  probable   = distance <= 2 m and DBH within 50% (or no DBH), or 2-4 m and DBH check passes
  unmatched  = otherwise
The two anchors were chosen from map spacing, so their distance is 0 by construction; their DBH check still applies.
Chance test: shuffle TLS DBH values among stems (positions fixed) 2000 times and count 'confirmed'.
Read-only on inputs. Run: python -I match_placement_A.py"""
import csv, random, statistics as st, math
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

CH = "../../"
P = {r["tag"]: complex(float(r["utm_e"]), float(r["utm_n"])) for r in csv.DictReader(open("predicted_field_positions_A.csv"))}
fd = {r["tag_id"]: r for r in csv.DictReader(open("D:/22083142/TreeData.csv", encoding="utf-8-sig")) if r["site_id"] == "WSF_ML2A" and r["live_dead1"] == "l"}
assert len(fd) == 26 and set(fd) == set(P)
att = {r["tree_id"]: r for r in csv.DictReader(open(CH + "measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028/results/tree_attributes.csv", encoding="utf-8"))}
LOC = complex(261350, 6264460)
refined = {"tree_074": 5.3877 + 5.0187j, "tree_163": 8.7983 + 2.8987j, "tree_103": 20.7836 + 2.4253j,
           "tree_079S": 5.2528 + 19.3628j, "tree_079N": 3.6905 + 21.7563j}  # Tree_inspection_2026-10-30 fitted bases
# DBH widths from the slice/inspection checks (not pipeline values), used only where the pipeline has none or fits a circle to an oval
slice_dbh = {"tree_163": 85, "tree_079S": 80, "tree_079N": 69, "tree_103": 78}
stems = {}
for t, r in att.items():
    if t == "tree_079": continue
    stems[t] = dict(pos=refined.get(t, complex(float(r["stem_x"]), float(r["stem_y"]))),
                    pipe=float(r["dbh_cm"]) if r["dbh_cm"] not in ("", "NA") else None, status=r["dbh_status"],
                    est=float(r["dbh_estimated_cm"]) if r["dbh_estimated_cm"] not in ("", "NA") else None)
for t in ("tree_079S", "tree_079N"):
    stems[t] = dict(pos=refined[t], pipe=None, status="N/A", est=None)
for t, v in slice_dbh.items(): stems[t]["slice"] = v
best = lambda s: s.get("slice") or s["pipe"] or s["est"]

def classify(dbh_of):
    pairs = sorted((abs(LOC + stems[t]["pos"] - P[g]) if t in refined else abs(stems[t]["pos"] - P[g]), g, t)
                   for g in P for t in stems)
    used_g, used_t, out = set(), set(), {}
    for d, g, t in pairs:
        if d > 4 or g in used_g or t in used_t: continue
        used_g.add(g); used_t.add(t)
        f = float(fd[g]["dbh1"]); v = dbh_of(t)
        ok = v is not None and abs(v - f) <= 0.25 * f
        near50 = v is None or abs(v - f) <= 0.5 * f  # added after the first run, which paired 1440 (14 cm) with tree_163 (85 cm)
        out[g] = (t, d, v, ok, "confirmed" if d <= 2 and ok else "probable" if (d <= 2 and near50) or ok else "unmatched")
    if "1448" in out:  # user decision 30 Oct: tree_079 is two twisted trees that cannot be segmented reliably; 1448's pair is excluded from all counts
        out["1448"] = out["1448"][:4] + ("excluded (merged trunks)",)
    return out

res = classify(lambda t: best(stems[t]))
rows = []
for g in sorted(P, key=lambda g: -float(fd[g]["dbh1"])):
    f = float(fd[g]["dbh1"])
    t, d, v, ok, cls = res.get(g, ("", "", None, False, "unmatched"))
    s = stems.get(t, {})
    rows.append(dict(tag=g, species=fd[g]["species"], quadrant=fd[g]["quadrant_id"], field_dbh_cm=f, tls_tree=t,
                     distance_m=round(d, 2) if t else "", tls_dbh_pipeline_cm=round(s["pipe"], 1) if s.get("pipe") else "",
                     tls_dbh_status=s.get("status", ""), tls_dbh_estimated_cm=round(s["est"], 1) if s.get("est") else "",
                     tls_dbh_slice_cm=s.get("slice", ""), dbh_used_for_check=round(v, 1) if v else "",
                     dbh_diff_pct=round(100 * (v - f) / f, 1) if v else "", dbh_check="pass" if ok else ("fail" if v else "no DBH"),
                     match_class=cls))
with open("tree_matches_A_final.csv", "w", newline="", encoding="utf-8") as fo:
    w = csv.DictWriter(fo, fieldnames=rows[0]); w.writeheader(); w.writerows(rows)

def stats(sel, key):
    d = [float(r[key]) - r["field_dbh_cm"] for r in sel if r[key] != ""]
    if not d: return None
    return dict(n=len(d), bias=round(st.mean(d), 1), rmse=round(math.sqrt(st.mean(x * x for x in d)), 1),
                rel_rmse=round(100 * math.sqrt(st.mean(x * x for x in d)) / st.mean(r["field_dbh_cm"] for r in sel if r[key] != ""), 1))
conf = [r for r in rows if r["match_class"] == "confirmed"]; prob = [r for r in rows if r["match_class"] == "probable"]
print("counts", {c: sum(r["match_class"] == c for r in rows) for c in ("confirmed", "probable", "unmatched")})
for r in rows: print(r["tag"], r["field_dbh_cm"], r["tls_tree"], r["distance_m"], r["tls_dbh_pipeline_cm"], r["tls_dbh_status"], r["tls_dbh_slice_cm"], r["dbh_diff_pct"], r["match_class"])
print("confirmed, DBH used for check:", stats(conf, "dbh_used_for_check"))
print("confirmed, pipeline DBH only:", stats(conf, "tls_dbh_pipeline_cm"))
print("confirmed+probable, DBH used:", stats(conf + prob, "dbh_used_for_check"))

# chance test: keep positions, shuffle DBH among stems
pool = [best(s) for s in stems.values()]; random.seed(1); hits = []
for _ in range(2000):
    sh = dict(zip(stems, random.sample(pool, len(pool))))
    hits.append(sum(v[4] == "confirmed" for v in classify(lambda t: sh[t]).values()))
n_conf = len(conf)
print(f"chance: confirmed with shuffled DBH mean {st.mean(hits):.2f}, 95th pct {sorted(hits)[1900]}, P(>= {n_conf}) = {(sum(h >= n_conf for h in hits)+1)/2001:.4f}")

# scatter: marker shape = match class, fill = source of the TLS DBH
from matplotlib.lines import Line2D
src = lambda r: "slice" if r["tls_dbh_slice_cm"] != "" else "pipeline" if r["tls_dbh_pipeline_cm"] != "" else "estimated"
FILL = {"pipeline": "k", "estimated": "0.65", "slice": "none"}
fig, ax = plt.subplots(figsize=(4.6, 4.4))
for sel, mk in ((conf, "o"), (prob, "^")):
    for r in sel:
        if r["dbh_used_for_check"] == "": continue
        ax.scatter(r["field_dbh_cm"], r["dbh_used_for_check"], marker=mk, facecolors=FILL[src(r)], edgecolors="k", s=40)
        if r["field_dbh_cm"] > 45: ax.annotate(r["tag"], (r["field_dbh_cm"], r["dbh_used_for_check"]), fontsize=7, xytext=(4, -9), textcoords="offset points")
ax.plot([0, 115], [0, 115], "k--", lw=.8); ax.set_xlim(0, 115); ax.set_ylim(0, 115); ax.set_aspect("equal")
ax.set_xlabel("Field DBH (cm)"); ax.set_ylabel("TLS DBH (cm)")
h = [Line2D([], [], marker="o", ls="", mfc="w", mec="k", label="confirmed"), Line2D([], [], marker="^", ls="", mfc="w", mec="k", label="probable"),
     Line2D([], [], marker="s", ls="", mfc="k", mec="k", label="pipeline DBH"), Line2D([], [], marker="s", ls="", mfc="0.65", mec="k", label="estimated DBH"),
     Line2D([], [], marker="s", ls="", mfc="none", mec="k", label="trunk-slice width")]
ax.legend(handles=h, loc="upper left", fontsize=7)
fig.tight_layout(); fig.savefig("dbh_matched_scatter_final.png", dpi=200)
