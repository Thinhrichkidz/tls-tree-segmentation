"""Placement A (map 1439 = tree_074, 1435 = tree_103, anchor bases from Tree_inspection_2026-10-30).
Predicts every field tag's position in EPSG:32756, then cuts a 1.2-1.4 m slice of the FULL 3 cm crop
around the predicted 1437 and 1455 positions to look for large trunks, segmented or not. Read-only on inputs.
Run: python -I search_missing_trunks.py"""
import csv, math
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

R = "D:/22083142/"; CH = R + "outputs/WSL_ML2A/55x55/3cm/Codex_help/"
OUT = Path(__file__).resolve().parent
s = 20 / (1597 - 925)  # site map metres per pixel (scale bar)
M = {r["label"]: complex((float(r["px"]) - 1219) * s, -(float(r["py"]) - 590) * s)
     for r in csv.DictReader(open(CH + "field_comparison_20261029/plot_overlay/map_digitised.csv")) if r["kind"] == "tree"}
LOC = complex(261350, 6264460)  # local offset used by the inspection folder
A = {"tree_074": complex(5.3877, 5.0187), "tree_103": complex(20.7836, 2.4253)}  # fitted base centres (local)
k = (A["tree_103"] - A["tree_074"]) / (M["1435"] - M["1439"]); b = LOC + A["tree_074"] - k * M["1439"]
assert abs(abs(k) - 1.13) < 0.01
P = {t: k * m + b for t, m in M.items()}
with open(OUT / "predicted_field_positions_A.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["tag", "utm_e", "utm_n"])
    for t, p in P.items(): w.writerow([t, round(p.real, 2), round(p.imag, 2)])

tls = list(csv.DictReader(open(CH + "measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028/results/tree_attributes.csv", encoding="utf-8")))
crop = R + "data/cropped/WSL_ML2A/55x55/3cm/WSL_ML2A_crop_55x55_3cm.ply"
with open(crop, "rb") as f:
    while b"end_header" not in f.readline(): pass
    off = f.tell()
dt = np.dtype([("x", "<f8"), ("y", "<f8"), ("z", "<f8")] + [(n, "<f4") for n in "abcdef"])
pts = np.memmap(crop, dtype=dt, mode="r", offset=off)
assert len(pts) == 45449820

RAD = 8.0
fig, axes = plt.subplots(1, 2, figsize=(14, 7))
for ax, tag in zip(axes, ("1437", "1455")):
    c = P[tag]; xy = None
    sel = []
    for i in range(0, len(pts), 5_000_000):  # chunked to keep memory low
        ch = pts[i:i + 5_000_000]
        m = (np.abs(ch["x"] - c.real) < RAD) & (np.abs(ch["y"] - c.imag) < RAD)
        sel.append(np.column_stack([ch["x"][m], ch["y"][m], ch["z"][m]]))
    a = np.vstack(sel)
    # ground per 1 m cell = 2nd percentile z (crop includes ground returns)
    ix = np.floor(a[:, 0]).astype(int); iy = np.floor(a[:, 1]).astype(int)
    g = {}
    for key in set(zip(ix, iy)):
        mm = (ix == key[0]) & (iy == key[1]); g[key] = np.percentile(a[mm, 2], 2)
    h = a[:, 2] - np.array([g[(i, j)] for i, j in zip(ix, iy)])
    sl = a[(h > 1.2) & (h < 1.4)]
    ax.scatter(sl[:, 0] - c.real, sl[:, 1] - c.imag, s=0.3, c="k")
    for r in tls:
        d = complex(float(r["stem_x"]), float(r["stem_y"])) - c
        if abs(d.real) < RAD and abs(d.imag) < RAD:
            ax.annotate(r["tree_id"][5:], (d.real, d.imag), color="tab:red", fontsize=8)
    for t, p in P.items():
        d = p - c
        if abs(d.real) < RAD and abs(d.imag) < RAD:
            ax.plot(d.real, d.imag, "o", mfc="none", ms=10, color="tab:blue"); ax.annotate(t, (d.real + .3, d.imag + .3), color="tab:blue", fontsize=8)
    ax.set_title(f"Predicted {tag}: 1.2-1.4 m slice of full 3 cm crop ({len(sl)} pts)\nred = TLS tree id at stem base, blue = predicted field tag")
    ax.set_aspect("equal"); ax.set_xlim(-RAD, RAD); ax.set_ylim(-RAD, RAD); ax.grid(alpha=.3)
    ax.set_xlabel("m east of predicted position"); ax.set_ylabel("m north")
    np.save(OUT / f"slice_{tag}.npy", sl)
fig.tight_layout(); fig.savefig(OUT / "missing_trunk_search.png", dpi=130)
print({t: (round(P[t].real, 2), round(P[t].imag, 2)) for t in ("1437", "1455")})
