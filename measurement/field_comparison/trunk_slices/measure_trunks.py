"""Independent trunk-slice DBH for every TLS tree in or near the 30 m field plot (WSF_ML2A).
Aimed at the large trees the pipeline could not measure well (leaning, oval, two trunks), and run on all trees
near the plot so the method can be checked against the pipeline DBH on clean VALID trunks.
Read-only on the review clouds and results; writes only into this folder. Run: python -I measure_trunks.py

Per tree: 10 cm horizontal slices at 1.2, 1.3 and 1.4 m above the pipeline ground; largest connected point group
in each slice = the trunk. Slice DBH rule (median over the three heights):
  lean > 20 deg          -> narrow width (across the lean; a horizontal cut through a leaning trunk is an oval)
  circle rms <= 3 cm     -> circle fit
  otherwise (oval/rough) -> area-equivalent diameter of the convex hull
A second group at least 30% the size of the trunk group and >= 15 cm wide is flagged as a possible second trunk."""
import csv, math
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull

CH = Path("D:/22083142/outputs/WSL_ML2A/55x55/3cm/Codex_help")
ATT = CH / "measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028/results/tree_attributes.csv"
CLOUDS = CH / "CloudCompare_review_v2"
OUT = Path(__file__).resolve().parent
GPS_C = (261366.0, 6264476.4)            # field plot centre (GPS), ../plot_overlay/plot_posts_utm.csv
FIT_C = (261365.71, 6264469.80)          # north-up anchor fit centre, ../plot_overlay/north_up_fit/fit_summary.json
REACH = 16.0                             # 15 m plot radius + 1 m for boundary trees
HEIGHTS, HALF = (1.2, 1.3, 1.4), 0.05
PLY_T = {"double": "<f8", "float": "<f4", "uchar": "u1", "uint": "<u4", "int": "<i4", "ushort": "<u2", "short": "<i2", "char": "i1"}

def read_ply(p):
    """Binary little-endian PLY, vertex layout taken from the header (the review clouds do not all share one layout)."""
    raw = p.read_bytes()
    end = raw.find(b"end_header\n") + len(b"end_header\n")
    lines = raw[:end].decode("latin1").splitlines()
    assert "format binary_little_endian 1.0" in lines, p
    n = int(next(l for l in lines if l.startswith("element vertex")).split()[-1])
    assert sum(l.startswith("element ") for l in lines) == 1, f"{p}: only a single vertex element is supported"
    dt = np.dtype([(l.split()[2], PLY_T[l.split()[1]]) for l in lines if l.startswith("property ")])
    assert end + n * dt.itemsize == len(raw), f"{p}: header layout does not match the file size"
    v = np.frombuffer(raw, dtype=dt, count=n, offset=end)
    return np.column_stack([v["x"], v["y"], v["z"]])

def groups(xy, cell=0.06):
    """Connected components on a 2D occupancy grid (8-neighbour), largest first."""
    ij = np.floor((xy - xy.min(0)) / cell).astype(int)
    cells = {}
    for k, c in enumerate(map(tuple, ij)):
        cells.setdefault(c, []).append(k)
    seen, out = set(), []
    for c in cells:
        if c in seen:
            continue
        stack, comp = [c], []
        seen.add(c)
        while stack:
            a = stack.pop(); comp += cells[a]
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    b = (a[0] + dx, a[1] + dy)
                    if b in cells and b not in seen:
                        seen.add(b); stack.append(b)
        out.append(np.array(comp))
    return sorted(out, key=len, reverse=True)

def shape(xy):
    m = xy.mean(0); q = xy - m
    A = np.column_stack([2 * q, np.ones(len(q))])
    cx, cy, c = np.linalg.lstsq(A, (q ** 2).sum(1), rcond=None)[0]
    r = math.sqrt(max(c + cx ** 2 + cy ** 2, 0))
    rms = float(np.sqrt(np.mean((np.hypot(q[:, 0] - cx, q[:, 1] - cy) - r) ** 2)))
    pr = q @ np.linalg.eigh(np.cov(q.T))[1]
    narrow = np.percentile(pr[:, 0], 98) - np.percentile(pr[:, 0], 2)
    long_ = np.percentile(pr[:, 1], 98) - np.percentile(pr[:, 1], 2)
    area_d = 2 * math.sqrt(ConvexHull(q).volume / math.pi) if len(q) >= 5 else float("nan")
    ang = np.degrees(np.arctan2(q[:, 1] - cy, q[:, 0] - cx)) % 360
    cover = len(set((ang // 10).astype(int))) / 36  # share of 10-degree sectors with points
    return dict(centre=m + [cx, cy], circle=2 * r, rms=rms, narrow=narrow, long=long_, area=area_d, cover=cover, n=len(xy))

def slice_at(P, z, foot):
    s = P[(P[:, 2] >= z - HALF) & (P[:, 2] < z + HALF)]
    if len(s) < 15:
        return None, None
    gs = [g for g in groups(s[:, :2]) if len(g) >= 8]
    if not gs:
        return None, None
    main = shape(s[gs[0], :2])
    second = shape(s[gs[1], :2]) if len(gs) > 1 and len(gs[1]) >= 0.3 * len(gs[0]) else None
    if second and max(second["narrow"], second["circle"] if second["rms"] < 0.05 else 0) < 0.15:
        second = None
    return main, second

def picture(P, gz, tid, rec):
    """Top view of the 1.3 m slice (trunk group in red) and a side view of the bottom 3 m, for checking by eye."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    (OUT / "slice_images").mkdir(exist_ok=True)
    s = P[(P[:, 2] >= gz + 1.3 - HALF) & (P[:, 2] < gz + 1.3 + HALF)]
    low = P[P[:, 2] < gz + 3.0]
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(15, 5))
    if len(s):
        o = s[:, :2].mean(0); gs = groups(s[:, :2])
        a.scatter(*(s[:, :2] - o).T, s=3, c="0.6")
        a.scatter(*(s[gs[0], :2] - o).T, s=4, c="tab:red")
        a.set_aspect("equal"); a.grid(alpha=0.3)
    a.set_title(f"top view, slice at 1.3 m (red = trunk group)\nslice DBH {rec.get('slice_dbh_cm')} cm, {rec.get('rule')}", fontsize=9)
    o = low[:, :2].mean(0) if len(low) else np.zeros(2)
    for ax, k, lab in ((b, 0, "east (m)"), (c, 1, "north (m)")):
        ax.scatter(low[:, k] - o[k], low[:, 2] - gz, s=0.5, c="0.3")
        ax.axhline(1.3, color="tab:red", lw=1); ax.set_aspect("equal"); ax.set_xlabel(lab); ax.set_ylabel("height above ground (m)")
        ax.grid(alpha=0.3)
    b.set_title(f"side view looking north; pipeline DBH {rec['pipeline_dbh_cm'][:5] or 'NA'} {rec['pipeline_status']}", fontsize=9)
    c.set_title(f"side view looking east; lean {rec.get('lean_deg')} deg; {rec.get('flags', '')}", fontsize=9)
    fig.suptitle(tid); fig.tight_layout(); fig.savefig(OUT / "slice_images" / f"{tid}.png", dpi=110); plt.close(fig)

f = lambda s: float(s) if s not in ("", "NA") else None


def main():
    rows = [r for r in csv.DictReader(open(ATT, encoding="utf-8"))
            if min(math.dist((float(r["stem_x"]), float(r["stem_y"])), c) for c in (GPS_C, FIT_C)) <= REACH]
    out = []
    for r in rows:
        P = read_ply(CLOUDS / r["source_file"])
        gz, foot = float(r["ground_z"]), (float(r["stem_x"]), float(r["stem_y"]))
        per_h, seconds = [], []
        for h in HEIGHTS:
            m, s2 = slice_at(P, gz + h, foot)
            if m:
                per_h.append(m)
            if s2:
                seconds.append(s2)
        lo, hi = slice_at(P, gz + 1.0, foot)[0], slice_at(P, gz + 1.9, foot)[0]
        lean = math.degrees(math.atan2(np.linalg.norm(hi["centre"] - lo["centre"]), 0.9)) if lo and hi else float("nan")
        rec = dict(tree_id=r["tree_id"], dist_gps_m=round(math.dist(foot, GPS_C), 1), dist_fit_m=round(math.dist(foot, FIT_C), 1),
                   pipeline_dbh_cm=r["dbh_cm"], pipeline_status=r["dbh_status"], pipeline_est_cm=r["dbh_estimated_cm"],
                   height_m=round(float(r["height_m"]), 1), ground_source=r["ground_source"][:40], n_slices=len(per_h))
        if per_h:
            med = lambda k: float(np.median([p[k] for p in per_h]))
            rms, cover = med("rms"), med("cover")
            if lean > 20:
                rule, d = "narrow width (leaning)", med("narrow")
            elif rms <= 0.03:
                rule, d = "circle", med("circle")
            else:
                rule, d = "area-equivalent (oval/rough)", med("area")
            sec = (len(seconds) >= 2)
            d2 = float(np.median([s["narrow"] for s in seconds])) if sec else None
            rec.update(slice_dbh_cm=round(100 * d, 1), rule=rule, circle_cm=round(100 * med("circle"), 1), circle_rms_cm=round(100 * rms, 1),
                       narrow_cm=round(100 * med("narrow"), 1), long_cm=round(100 * med("long"), 1), area_eq_cm=round(100 * med("area"), 1),
                       coverage=round(cover, 2), lean_deg=round(lean, 0) if lean == lean else "",
                       second_trunk_cm=round(100 * d2, 1) if d2 else "",
                       combined_cm=round(100 * math.hypot(d, d2), 1) if d2 else "",
                       flags="; ".join(x for x in ("partial scan (coverage < 0.6)" if cover < 0.6 else "",
                                                    "possible second trunk" if sec else "",
                                                    "ground is a fallback" if "fallback" in r["ground_source"] else "") if x))
        pd_ = f(r["dbh_cm"])
        if rec.get("rule") != "circle" or pd_ is None or abs(rec["slice_dbh_cm"] - pd_) > 0.2 * pd_:
            rec["needs_eye_check"] = True
            picture(P, gz, r["tree_id"], rec)
        out.append(rec)
        print(rec["tree_id"], rec.get("slice_dbh_cm"), rec.get("rule"), "| pipeline", r["dbh_cm"][:5], r["dbh_status"], "|", rec.get("flags", ""))

    keys = list(dict.fromkeys(k for o in out for k in o))
    with open(OUT / "trunk_slice_dbh.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, keys); w.writeheader(); w.writerows(out)

    # Method check: VALID pipeline trunks that are round, upright and well covered.
    chk = [(o["slice_dbh_cm"], float(o["pipeline_dbh_cm"])) for o in out
           if o["pipeline_status"] == "VALID" and o.get("rule") == "circle" and o.get("coverage", 0) >= 0.6]
    d = [a - b for a, b in chk]
    assert chk, "no VALID trunks to check the method on"
    print(f"\nmethod check on {len(chk)} VALID round trunks: mean diff {np.mean(d):+.1f} cm, RMSE {math.sqrt(np.mean(np.square(d))):.1f} cm, max |diff| {max(map(abs, d)):.1f} cm")


if __name__ == "__main__":
    main()
