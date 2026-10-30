"""Step 2: match the site map to TLS stems by testing pair hypotheses, with a chance baseline.

Each hypothesis pairs two large field trees (DBH >= 50 cm) with two large TLS trees (top by point count; tree_085
excluded after the user's check). The two pairs fix a similarity transform (rotation, scale, shift). Support = how many
of the 26 field trees then have their own TLS stem within 1.5 m (one-to-one). Position only: DBH is never used to choose.
Chance baseline: the same search on TLS stems moved to random positions in the same area, repeated N_NULL times.
Read-only on all inputs; writes only into this folder. Run: python -I pair_hypothesis_match.py"""
import csv, json, math, random
from pathlib import Path
import numpy as np

R = Path("D:/22083142")
CH = R / "outputs/WSL_ML2A/55x55/3cm/Codex_help"
ATT = CH / "measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028/results/tree_attributes.csv"
FC = CH / "field_comparison_20261029"
OUT = Path(__file__).resolve().parent
TOL, MAXROT, SCALE, NBIG, N_NULL, AREA_R = 1.5, 20, (0.8, 1.4), 25, 20, 26.0
NOT_LARGE = {"tree_085"}  # user CloudCompare check: thin stem
# Best DBH where the trunk-slice eye check (../trunk_slices/eye_check_verdicts.csv) gave a firmer value; else pipeline.
SLICE_DBH = {"tree_163": 85, "tree_079": 90, "tree_103": 78, "tree_074": 63, "tree_120": 43, "tree_089": 38.5, "tree_095": 35,
             "tree_099": 37, "tree_094": 30, "tree_132": 30, "tree_123": 15, "tree_115": 18, "tree_100": 20}

f = lambda s: float(s) if s not in ("", "NA", None) else None
posts = {p["post"]: (float(p["utm56s_e"]), float(p["utm56s_n"])) for p in csv.DictReader(open(FC / "plot_overlay/plot_posts_utm.csv"))}
C0 = np.array(posts["c"])

# Field trees: live tagged, largest stem; map positions in metres from the drawn circle centre.
field = {}
for r in csv.DictReader(open(R / "TreeData.csv", encoding="utf-8-sig")):
    if r["site_id"] == "WSF_ML2A" and r["tag_id"] != "no_tag" and r["live_dead1"].lower() == "l":
        field[r["tag_id"]] = dict(dbh=max(f(r[f"dbh{i}"]) for i in range(1, 12) if f(r.get(f"dbh{i}", ""))), species=r["species"])
mp = list(csv.DictReader(open(FC / "plot_overlay/map_digitised.csv", encoding="utf-8")))
cc = next(r for r in mp if r["kind"] == "circle_centre"); sc = next(r for r in mp if r["kind"] == "scale")
s_px = 20.0 / (float(sc["py"]) - float(sc["px"]))
tags = [r["label"] for r in mp if r["kind"] == "tree"]
M = np.array([((float(r["px"]) - float(cc["px"])) * s_px, -(float(r["py"]) - float(cc["py"])) * s_px) for r in mp if r["kind"] == "tree"])
assert set(tags) == set(field) and len(tags) == 26
anchors = [i for i, t in enumerate(tags) if field[t]["dbh"] >= 50]

# TLS stems near the plot (local metres from the GPS centre).
tls = [r for r in csv.DictReader(open(ATT, encoding="utf-8"))
       if math.dist((float(r["stem_x"]), float(r["stem_y"])), C0) <= AREA_R]
T = np.array([[float(r["stem_x"]), float(r["stem_y"])] for r in tls]) - C0
big = [i for i in sorted(range(len(tls)), key=lambda i: -int(tls[i]["n_points"])) if tls[i]["tree_id"] not in NOT_LARGE][:NBIG]

def best_dbh(r):
    return SLICE_DBH.get(r["tree_id"]) or f(r["dbh_cm"]) or f(r["dbh_estimated_cm"])

def support(P, Tp):
    """One-to-one greedy matching of transformed field points P to stems Tp within TOL; returns list of (i, j, d)."""
    D = np.sqrt(((P[:, None] - Tp[None]) ** 2).sum(-1))
    pairs, used_i, used_j = [], set(), set()
    for k in np.argsort(D, axis=None):
        i, j = divmod(int(k), D.shape[1])
        if D[i, j] > TOL:
            break
        if i not in used_i and j not in used_j:
            pairs.append((i, j, float(D[i, j]))); used_i.add(i); used_j.add(j)
    return pairs

def sim_from_pairs(a, b):
    """Similarity transform mapping map points a (k x 2) onto TLS points b (least squares, no reflection)."""
    a0, b0 = a.mean(0), b.mean(0); A, B = a - a0, b - b0
    za, zb = A[:, 0] + 1j * A[:, 1], B[:, 0] + 1j * B[:, 1]
    q = (np.conj(za) @ zb) / (np.conj(za) @ za)
    return abs(q), math.degrees(np.angle(q)), q, a0, b0

def apply(q, a0, b0, P):
    z = (P[:, 0] - a0[0]) + 1j * (P[:, 1] - a0[1])
    w = q * z
    return np.column_stack([w.real, w.imag]) + b0

def search(Tp, bigp):
    best = []
    for ia in anchors:
        for ib in anchors:
            if ia == ib:
                continue
            dm = np.linalg.norm(M[ia] - M[ib])
            for ja in bigp:
                for jb in bigp:
                    if ja == jb:
                        continue
                    dt = np.linalg.norm(Tp[ja] - Tp[jb])
                    if not SCALE[0] <= dt / dm <= SCALE[1]:
                        continue
                    s, rot, q, a0, b0 = sim_from_pairs(M[[ia, ib]], Tp[[ja, jb]])
                    if abs(rot) > MAXROT:
                        continue
                    centre = apply(q, a0, b0, np.zeros((1, 2)))[0]
                    if np.linalg.norm(centre) > 15:
                        continue
                    P = apply(q, a0, b0, M)
                    sup = support(P, Tp)
                    if len(sup) >= 6:  # refine on the supporting pairs
                        ii = [p[0] for p in sup]; jj = [p[1] for p in sup]
                        s2, rot2, q2, a02, b02 = sim_from_pairs(M[ii], Tp[jj])
                        if SCALE[0] <= s2 <= SCALE[1] and abs(rot2) <= MAXROT:
                            sup2 = support(apply(q2, a02, b02, M), Tp)
                            if len(sup2) >= len(sup):
                                sup, s, rot, q, a0, b0 = sup2, s2, rot2, q2, a02, b02
                    best.append((len(sup), -sum(p[2] for p in sup), s, rot, q, a0, b0, sup))
    best.sort(key=lambda b: (b[0], b[1]), reverse=True)
    return best

res = search(T, big)
top = res[0]
# Distinct runner-up: a solution whose centre is > 3 m from the winner's.
cen = lambda b: apply(b[4], b[5], b[6], np.zeros((1, 2)))[0]
runner = next((b for b in res if np.linalg.norm(cen(b) - cen(top)) > 3), None)

# Chance baseline: same search, TLS stems at random positions in the same disc (same count; same "big" ranks).
rng = random.Random(1); null = []
for _ in range(N_NULL):
    rr = np.sqrt([rng.random() for _ in T]) * AREA_R; th = [rng.random() * 2 * math.pi for _ in T]
    Tn = np.column_stack([rr * np.cos(th), rr * np.sin(th)])
    null.append(search(Tn, big)[0][0])

# Outputs.
P = apply(top[4], top[5], top[6], M)
pairs = {i: (j, d) for i, j, d in top[7]}
rows = []
for i, t in enumerate(tags):
    j, d = pairs.get(i, (None, None))
    r = tls[j] if j is not None else None
    bd = best_dbh(r) if r else None
    fd = field[t]["dbh"]
    rows.append(dict(tag=t, species=field[t]["species"], field_dbh_cm=fd, anchor=i in anchors,
                     tls_tree=r["tree_id"] if r else "", dist_m=round(d, 2) if d is not None else "",
                     tls_dbh_cm=bd if bd is not None else "", tls_dbh_source=("slice (eye-checked)" if r and r["tree_id"] in SLICE_DBH else
                                                                        "pipeline" if r and f(r["dbh_cm"]) else "estimated" if r and f(r["dbh_estimated_cm"]) else ""),
                     diff_pct=round(100 * (bd - fd) / fd, 1) if bd else "",
                     east_m=round(P[i, 0], 2), north_m=round(P[i, 1], 2)))
with open(OUT / "pair_hypothesis_matches.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
summary = dict(best=dict(matched=top[0], scale=round(top[2], 3), rotation_deg=round(top[3], 1),
                         centre_east_north_of_gps_m=[round(v, 2) for v in cen(top)]),
               runner_up=dict(matched=runner[0], scale=round(runner[2], 3), rotation_deg=round(runner[3], 1),
                              centre_east_north_of_gps_m=[round(v, 2) for v in cen(runner)]) if runner else None,
               chance_best_scores=sorted(null), chance_mean=round(float(np.mean(null)), 1), chance_max=max(null),
               settings=dict(tol_m=TOL, max_rot_deg=MAXROT, scale_range=SCALE, n_large_tls=NBIG, area_radius_m=AREA_R))
(OUT / "pair_hypothesis_summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=1))
for r in rows:
    print(r["tag"], r["field_dbh_cm"], r["tls_tree"], r["dist_m"], r["tls_dbh_cm"], r["tls_dbh_source"], r["diff_pct"])
