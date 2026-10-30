"""Locate the 30 m field plot (WSF_ML2A) in the TLS crop, redo the DBH distribution comparison inside it,
match the site-map trees to TLS stems, and compare DBH tree by tree for the confident matches.
Read-only on all inputs; writes only into this folder. Run: python -I locate_plot_and_match.py"""
import ast, csv, json, math, bisect, random, statistics as st
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = "D:/22083142/"
CH = R + "outputs/WSL_ML2A/55x55/3cm/Codex_help/"
V6 = CH + "measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028/results/tree_attributes.csv"
OUT = Path(__file__).resolve().parent
RADIUS, FIELD_MIN = 15.0, 10.0  # plot radius (m); field survey threshold (cm)

# UTM converter already used for the field check sheet (Snyder 1987).
src = open(CH + "measurement_pipeline/scripts/field_check_sheet.py", encoding="utf-8").read()
g = {"math": math}
for n in ast.parse(src).body:
    if isinstance(n, ast.FunctionDef) and n.name in ("latlon_to_utm", "utm_to_latlon"):
        exec(ast.get_source_segment(src, n), g)
to_utm, to_ll = g["latlon_to_utm"], g["utm_to_latlon"]

# 1. GPS centre and posts (GDA94 lon/lat). Treated as WGS84: the GDA94/WGS84 offset (~1.5-1.8 m) is absorbed by the fit below.
xl = __import__("openpyxl").load_workbook(R + "Ecology_Hub_Plot_Data.xlsx", data_only=True).active
hdr = [c.value for c in xl[1]]
row = next(dict(zip(hdr, [c.value for c in r])) for r in xl.iter_rows(min_row=2) if r[0].value == "WSF_ML2A")
gps = {k: to_utm(row[f"coords_{k}_y"], row[f"coords_{k}_x"]) for k in "cnesw"}
for k, (x, y) in gps.items():
    lat, lon = to_ll(x, y)
    assert abs(lat - row[f"coords_{k}_y"]) < 1e-7 and abs(lon - row[f"coords_{k}_x"]) < 1e-7  # round trip < 1 cm
C0 = np.array(gps["c"])

# 2. Field inventory: live tagged trees, largest stem and combined (basal-area-equivalent) DBH.
f = lambda s: float(s) if s not in ("", "NA", None) else None
field = {}
for r in csv.DictReader(open(R + "TreeData.csv", encoding="utf-8-sig")):
    if r["site_id"] == "WSF_ML2A" and r["tag_id"] != "no_tag" and r["live_dead1"].lower() == "l":
        d = [f(r[f"dbh{i}"]) for i in range(1, 12) if f(r.get(f"dbh{i}", ""))]
        field[r["tag_id"]] = dict(species=r["species"], quadrant=r["quadrant_id"], dbh=max(d),
                                  dbh_comb=math.sqrt(sum(x * x for x in d)), n_stems=len(d), notes=r["notes"])
assert len(field) == 26

# 3. Site map (not georeferenced) -> metres, x east / y north, origin at the drawn circle centre.
mp = list(csv.DictReader(open(OUT / "map_digitised.csv", encoding="utf-8")))
cc = next(r for r in mp if r["kind"] == "circle_centre"); sc = next(r for r in mp if r["kind"] == "scale")
s = 20.0 / (float(sc["py"]) - float(sc["px"]))  # m per px from the 20 m scale bar
assert abs(float(cc["r_px"]) * s - RADIUS) < 0.5  # drawn circle radius agrees with the 15 m plot radius
m2 = lambda r: ((float(r["px"]) - float(cc["px"])) * s, -(float(r["py"]) - float(cc["py"])) * s)
mtags = [r["label"] for r in mp if r["kind"] == "tree"]
M = np.array([m2(r) for r in mp if r["kind"] == "tree"])
pegs_map = np.array([m2(r) for r in mp if r["kind"] == "peg"])
assert set(mtags) == set(field)

# 4. TLS stems (v6 FINAL).
tls = list(csv.DictReader(open(V6, encoding="utf-8")))
T = np.array([[float(r["stem_x"]), float(r["stem_y"])] for r in tls])

def rot(t):
    c, s_ = math.cos(t), math.sin(t)
    return np.array([[c, -s_], [s_, c]])

def apply(P, th, t):
    return P @ rot(th).T + t

def dists(P):
    return np.sqrt(((P[:, None, :] - T[None, :, :]) ** 2).sum(-1))

def score(P, cap=2.0):  # truncated least squares on nearest-stem distance
    return float(np.minimum(dists(P).min(1), cap).__pow__(2).sum())

# Grid search: rotation +-30 deg, translation +-10 m around the GPS centre (map scale fixed by its scale bar).
best = []
off = np.arange(-10, 10.01, 0.5)
G = np.array([(dx, dy) for dx in off for dy in off])
for deg in range(-30, 31):
    P0 = M @ rot(math.radians(deg)).T + C0  # map trees x translations x TLS stems
    D = np.sqrt(((P0[:, None, None, :] + G[None, :, None, :] - T[None, None, :, :]) ** 2).sum(-1)).min(-1)
    for (dx, dy), v in zip(G, (np.minimum(D, 2.0) ** 2).sum(0)):
        best.append((float(v), deg, float(dx), float(dy)))
best.sort()

def refine(th, t, keep=None, it=20):
    """Least-squares rotation + translation on mutual nearest pairs within 2 m (optionally only the tags in keep)."""
    for _ in range(it):
        P = apply(M, th, t); D = dists(P); j = D.argmin(1); i_of_j = D.argmin(0)
        sel = [i for i in range(len(M)) if D[i, j[i]] <= 2.0 and i_of_j[j[i]] == i and (keep is None or mtags[i] in keep)]
        A, B = M[sel], T[j[sel]]
        a0, b0 = A.mean(0), B.mean(0)
        U, _, Vt = np.linalg.svd((A - a0).T @ (B - b0))
        Rm = (U @ Vt).T
        if np.linalg.det(Rm) < 0:
            continue
        th, t = math.atan2(Rm[1, 0], Rm[0, 0]), b0 - a0 @ Rm.T
    return th, t, len(sel)

v0, deg0, dx0, dy0 = best[0]
th, t, npair = refine(math.radians(deg0), C0 + [dx0, dy0])
fit_score = score(apply(M, th, t))
# Is the solution unique? Best grid solution that is > 3 m or > 5 deg away from the winner.
alt = next(b for b in best if math.hypot(b[2] - dx0, b[3] - dy0) > 3 or abs(b[1] - deg0) > 5)
# Professor's route: anchors only, then see whether the other trees line up.
anchors = {"1437", "1439", "1448", "1455", "1435", "1450"}
th_a, t_a, _ = refine(math.radians(deg0), C0 + [dx0, dy0], keep=anchors)

# 5. Matching on position only. DBH and species are recorded as independent checks, never used to choose a pair.
P = apply(M, th, t); D = dists(P); j1 = D.argmin(1); i_of_j = D.argmin(0)
match = []
for i, tag in enumerate(mtags):
    o = np.sort(D[i]); d1, d2 = float(o[0]), float(o[1]); mutual = i_of_j[j1[i]] == i
    cls = "confirmed" if mutual and d1 <= 1.5 and d2 - d1 >= 1.0 else "probable" if mutual and d1 <= 3.0 else "unmatched"
    r = tls[j1[i]]; fd = field[tag]
    tm, te = f(r["dbh_cm"]), f(r["dbh_estimated_cm"])
    tv = tm if tm is not None else te
    match.append(dict(tag=tag, species=fd["species"], quadrant=fd["quadrant"], field_dbh_cm=fd["dbh"],
                      field_dbh_combined_cm=round(fd["dbh_comb"], 1), field_stems=fd["n_stems"], field_notes=fd["notes"],
                      tls_tree=r["tree_id"] if cls != "unmatched" else "", dist_m=round(d1, 2), second_dist_m=round(d2, 2),
                      mutual_nearest=bool(mutual), match_class=cls,
                      tls_dbh_cm=round(tm, 1) if tm else "", tls_dbh_status=r["dbh_status"],
                      tls_dbh_estimated_cm=round(te, 1) if te else "",
                      dbh_diff_pct=round(100 * (tv - fd["dbh"]) / fd["dbh"], 1) if tv and cls != "unmatched" else "",
                      dbh_check="" if not tv or cls == "unmatched" else "DBH disagrees >40%" if abs(tv - fd["dbh"]) > 0.4 * fd["dbh"] else "ok",
                      map_x_m=round(M[i, 0], 2), map_y_m=round(M[i, 1], 2),
                      utm_e=round(P[i, 0], 2), utm_n=round(P[i, 1], 2)))

# 6. Distribution comparison inside the plot circle (both centre choices).
q = lambda x, p: sorted(x)[round(p * (len(x) - 1))]
def ks(a, b):
    a, b = sorted(a), sorted(b)
    return max(abs(bisect.bisect_right(a, v) / len(a) - bisect.bisect_right(b, v) / len(b)) for v in a + b)
def perm_p(a, b, n=4000):
    random.seed(1); d = ks(a, b); z = a + b; hit = 0
    for _ in range(n):
        random.shuffle(z); hit += ks(z[:len(a)], z[len(a):]) >= d
    return (hit + 1) / (n + 1)
fdbh = [v["dbh"] for v in field.values()]
centre_fit = apply(np.zeros((1, 2)), th, t)[0]
dist_rows = [["plot centre", "TLS set", "TLS trees in circle", "n (>=10 cm)", "TLS median", "field median",
              "median err %", "p25 err %", "p75 err %", "max TLS", "max field", "KS", "perm p"]]
inside = {}
for cname, c in (("GPS centre", C0), ("fitted map centre", centre_fit)):
    ins = [r for r, xy in zip(tls, T) if math.dist(xy, c) <= RADIUS]
    inside[cname] = ins
    meas = [f(r["dbh_cm"]) for r in ins if f(r["dbh_cm"])]
    sets = (("measured", meas), ("VALID", [f(r["dbh_cm"]) for r in ins if r["dbh_status"] == "VALID"]),
            ("measured+EST", meas + [f(r["dbh_estimated_cm"]) for r in ins if f(r["dbh_estimated_cm"])]))
    for name, v in sets:
        v = [x for x in v if x >= FIELD_MIN]
        e = lambda p: round(100 * (q(v, p) - q(fdbh, p)) / q(fdbh, p), 1)
        dist_rows.append([cname, name, len(ins), len(v), round(st.median(v), 1), round(st.median(fdbh), 1),
                          e(.5), e(.25), e(.75), round(max(v), 1), max(fdbh), round(ks(v, fdbh), 3), round(perm_p(v, fdbh), 3)])

# 7. Tree-by-tree DBH (largest field stem vs TLS measured DBH; estimated DBH reported separately).
def tbt(rows, key):
    d = [(float(m[key]) - m["field_dbh_cm"]) for m in rows if m[key] != ""]
    pc = [100 * x / m["field_dbh_cm"] for x, m in zip(d, [m for m in rows if m[key] != ""])]
    if not d:
        return [0, "", "", "", "", ""]
    return [len(d), round(st.mean(d), 1), round(math.sqrt(st.mean([x * x for x in d])), 1), round(st.median(pc), 1),
            round(min(pc), 1), round(max(pc), 1)]
tbt_rows = [["matches used", "TLS DBH", "n", "bias cm (TLS-field)", "RMSE cm", "median diff %", "min diff %", "max diff %"]]
conf = [m for m in match if m["match_class"] == "confirmed"]
both = [m for m in match if m["match_class"] in ("confirmed", "probable")]
for name, rows_ in (("confirmed", conf), ("confirmed+probable", both)):
    tbt_rows.append([name, "measured (VALID+REVIEW)"] + tbt(rows_, "tls_dbh_cm"))
    tbt_rows.append([name, "VALID only"] + tbt([m for m in rows_ if m["tls_dbh_status"] == "VALID"], "tls_dbh_cm"))
    tbt_rows.append([name, "ESTIMATED"] + tbt(rows_, "tls_dbh_estimated_cm"))

# 8. Write outputs.
def wcsv(name, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)
wcsv("plot_posts_utm.csv", [["post", "lon_gda94", "lat_gda94", "utm56s_e", "utm56s_n", "dist_from_centre_m", "bearing_deg"]] +
     [[k, row[f"coords_{k}_x"], row[f"coords_{k}_y"], round(x, 2), round(y, 2), round(math.dist((x, y), C0), 2),
       round(math.degrees(math.atan2(x - C0[0], y - C0[1])) % 360, 1)] for k, (x, y) in gps.items()])
wcsv("tree_matches.csv", [list(match[0])] + [list(m.values()) for m in match])
wcsv("dbh_in_plot_distribution.csv", dist_rows)
wcsv("dbh_tree_by_tree.csv", tbt_rows)
ins_ids = {r["tree_id"] for r in inside["fitted map centre"]}
wcsv("tls_trees_in_plot.csv", [["tree_id", "utm_e", "utm_n", "dist_from_fitted_centre_m", "dist_from_gps_centre_m", "inside_fitted", "inside_gps",
                                "dbh_cm", "dbh_status", "dbh_estimated_cm", "height_m", "matched_tag"]] +
     [[r["tree_id"], round(xy[0], 2), round(xy[1], 2), round(math.dist(xy, centre_fit), 2), round(math.dist(xy, C0), 2),
       r["tree_id"] in ins_ids, math.dist(xy, C0) <= RADIUS, r["dbh_cm"], r["dbh_status"], r["dbh_estimated_cm"], r["height_m"],
       next((m["tag"] for m in match if m["tls_tree"] == r["tree_id"]), "")]
      for r, xy in zip(tls, T) if min(math.dist(xy, centre_fit), math.dist(xy, C0)) <= RADIUS + 3])
fit = dict(rotation_deg=round(math.degrees(th), 2), map_centre_utm=[round(v, 2) for v in centre_fit],
           shift_from_gps_centre_m=[round(v, 2) for v in centre_fit - C0], shift_length_m=round(float(np.linalg.norm(centre_fit - C0)), 2),
           pairs_used=npair, score=round(fit_score, 2), grid_best=[deg0, dx0, dy0, round(v0, 2)],
           next_distinct_grid_solution=dict(deg=alt[1], dx=alt[2], dy=alt[3], score=round(alt[0], 2)),
           anchors_only_fit=dict(rotation_deg=round(math.degrees(th_a), 2),
                                 centre_utm=[round(v, 2) for v in apply(np.zeros((1, 2)), th_a, t_a)[0]],
                                 centre_diff_from_full_fit_m=round(float(np.linalg.norm(apply(np.zeros((1, 2)), th_a, t_a)[0] - centre_fit)), 2)),
           counts={c: sum(m["match_class"] == c for m in match) for c in ("confirmed", "probable", "unmatched")},
           tls_trees_in_circle={k: len(v) for k, v in inside.items()},
           map_m_per_px=round(s, 5))
(OUT / "fit_summary.json").write_text(json.dumps(fit, indent=2))

# 9. Overlay figure (local metres from the GPS centre).
col = {"confirmed": "#1a9850", "probable": "#fdae61", "unmatched": "#d73027"}
fig, ax = plt.subplots(figsize=(9, 9))
L = T - C0
dm = [f(r["dbh_cm"]) or f(r["dbh_estimated_cm"]) for r in tls]
ax.scatter(L[:, 0], L[:, 1], s=[(d or 8) ** 1.3 for d in dm], facecolors=["0.6" if d else "none" for d in dm],
           edgecolors="0.35", lw=0.6, label="TLS stem (size = DBH; hollow = no DBH)", zorder=2)
for k, (x, y) in gps.items():
    ax.plot(x - C0[0], y - C0[1], "*", ms=14, color="gold", mec="k", zorder=5)
    ax.annotate(k.upper(), (x - C0[0], y - C0[1]), xytext=(5, 5), textcoords="offset points", fontsize=9)
ax.add_patch(plt.Circle((0, 0), RADIUS, fill=False, ls="--", color="tab:blue", label="15 m circle on GPS centre"))
ax.add_patch(plt.Circle(tuple(centre_fit - C0), RADIUS, fill=False, color="tab:blue", lw=2, label="15 m circle, fitted map position"))
Pl = P - C0
for i, m in enumerate(match):
    ax.scatter(*Pl[i], s=m["field_dbh_cm"] ** 1.3, facecolors="none", edgecolors=col[m["match_class"]], lw=2, zorder=4)
    ax.annotate(m["tag"], Pl[i], xytext=(6, -10), textcoords="offset points", fontsize=8, color=col[m["match_class"]])
    if m["match_class"] != "unmatched":
        ax.plot([Pl[i, 0], L[j1[i], 0]], [Pl[i, 1], L[j1[i], 1]], color=col[m["match_class"]], lw=1)
for c, lab in col.items():
    ax.scatter([], [], facecolors="none", edgecolors=lab, lw=2, label=f"field tree, {c}")
pm = apply(pegs_map, th, t) - C0
ax.plot(pm[:, 0], pm[:, 1], "+", color="k", ms=10, label="map pegs (fitted)")
ax.set_aspect("equal"); ax.set_xlim(-22, 22); ax.set_ylim(-22, 22); ax.grid(alpha=0.3)
ax.set_xlabel("East of GPS centre (m)"); ax.set_ylabel("North of GPS centre (m)")
ax.set_title("WSF_ML2A: field plot located in the TLS crop (EPSG:32756)")
ax.legend(loc="lower left", fontsize=7, framealpha=0.9)
fig.tight_layout(); fig.savefig(OUT / "plot_overlay.png", dpi=160)

print(json.dumps(fit, indent=1))
for r in dist_rows: print(r)
for r in tbt_rows: print(r)
for m in match: print(m["tag"], m["species"][:10], m["field_dbh_cm"], m["match_class"], m["tls_tree"], m["dist_m"], m["second_dist_m"],
                      m["tls_dbh_cm"], m["tls_dbh_status"], m["tls_dbh_estimated_cm"], m["dbh_diff_pct"], m["dbh_check"])
