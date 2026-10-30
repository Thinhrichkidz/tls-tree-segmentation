"""Ellipse fits for the large trunks whose 1.3 m slice is a clean ring (chosen by eye from slice_images/).
A horizontal cut through a leaning round trunk is an ellipse whose short axis is the trunk diameter; an oval trunk
is reported as its area-equivalent diameter. Read-only on the clouds; writes ellipse_key_trees.csv here.
Run: python -I ellipse_key_trees.py"""
import csv, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I drops the script folder from the path
from measure_trunks import read_ply, groups, ATT, CLOUDS, OUT, HALF  # same reader and grouping as the batch

# tree -> how many separate trunk rings to fit (079 is two trunks twisted together, checked by the user)
KEY = {"tree_163": 1, "tree_079": 2, "tree_074": 1, "tree_103": 1, "tree_120": 1, "tree_089": 1}

def ellipse(xy):
    """Least-squares conic fit; returns (major, minor) full axis lengths, or None if not an ellipse."""
    m = xy.mean(0); x, y = (xy - m).T
    D = np.column_stack([x * x, x * y, y * y, x, y])
    a, b, c, d, e = np.linalg.lstsq(D, np.ones(len(x)), rcond=None)[0]
    if b * b - 4 * a * c >= 0:
        return None
    M = np.array([[a, b / 2], [b / 2, c]]); x0 = np.linalg.solve(2 * M, [-d, -e])
    k = 1 + x0 @ M @ x0
    w = np.linalg.eigvalsh(M)
    if k <= 0 or min(w) <= 0:
        return None
    ax = 2 * np.sqrt(k / w)
    return float(ax.max()), float(ax.min()), m + x0

def robust_ellipse(xy):
    """Fit, drop points far from the ring (branches, stray points), refit."""
    r = ellipse(xy)
    if r is None:
        return None
    for _ in range(2):
        A, B, c = r
        q = xy - c
        rad = np.hypot(*q.T)
        keep = np.abs(rad - np.median(rad)) <= 2.5 * np.median(np.abs(rad - np.median(rad))) + 0.03
        r2 = ellipse(xy[keep])
        if r2 is None:
            break
        r = r2
    return r

att = {r["tree_id"]: r for r in csv.DictReader(open(ATT, encoding="utf-8"))}
rows = []
for t, nring in KEY.items():
    a = att[t]; P = read_ply(CLOUDS / a["source_file"]); gz = float(a["ground_z"])
    per = {k: [] for k in range(nring)}
    for h in (1.2, 1.3, 1.4):
        s = P[(P[:, 2] >= gz + h - HALF) & (P[:, 2] < gz + h + HALF)]
        gs = sorted(groups(s[:, :2])[:nring], key=lambda g: tuple(s[g, :2].mean(0)))  # stable ring order
        for k, g in enumerate(gs):
            e = robust_ellipse(s[g, :2])
            if e:
                per[k].append(e[:2])
    for k, v in per.items():
        if not v:
            rows.append(dict(tree_id=t, trunk=k + 1, note="no ellipse fit")); continue
        major = float(np.median([x[0] for x in v])); minor = float(np.median([x[1] for x in v]))
        rows.append(dict(tree_id=t, trunk=k + 1, slices=len(v), major_cm=round(100 * major, 1), minor_cm=round(100 * minor, 1),
                         area_eq_cm=round(100 * math.sqrt(major * minor), 1), pipeline_dbh_cm=a["dbh_cm"], pipeline_status=a["dbh_status"]))
for r in rows:
    print(r)
with open(OUT / "ellipse_key_trees.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, list(dict.fromkeys(k for r in rows for k in r))); w.writeheader(); w.writerows(rows)
