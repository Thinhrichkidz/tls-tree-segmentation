"""Side and top views of tree_081 to see whether the large ring south of predicted 1437 is a trunk inside tree_081."""
import csv, re
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
f = "../../CloudCompare_review_v2/tree_081_MANUAL_REVIEW.ply"
with open(f, "rb") as h:
    hdr = []
    while True:
        l = h.readline().decode(errors="replace").strip(); hdr.append(l)
        if l == "end_header": break
    n = int(re.search(r"element vertex (\d+)", "\n".join(hdr)).group(1))
    tm = {"double": "<f8", "float": "<f4", "uchar": "u1", "uint": "<u4", "int": "<i4"}
    dt = np.dtype([(p.split()[2], tm[p.split()[1]]) for p in hdr if p.startswith("property")])
    d = np.fromfile(h, dtype=dt, count=n)
ring = np.array([261362.53, 6264453.48])
attr = {r["tree_id"]: r for r in csv.DictReader(open("../../measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028/results/tree_attributes.csv", encoding="utf-8"))}["tree_081"]
foot = np.array([float(attr["stem_x"]), float(attr["stem_y"])])
x, y, z = d["x"] - ring[0], d["y"] - ring[1], d["z"]
zg = np.percentile(z[np.hypot(x, y) < 1.5], 1)
fig, ax = plt.subplots(1, 3, figsize=(16, 7))
for a, (u, lab) in zip(ax[:2], ((x, "east"), (y, "north"))):
    a.scatter(u, z - zg, s=0.2, c="k"); a.set_xlabel(f"m {lab} of ring centre"); a.set_ylabel("m above ring ground"); a.set_ylim(-1, 12)
    a.axhline(1.3, color="r", lw=.8); a.set_title(f"tree_081 side view ({lab})")
sl = (z - zg > 1.0) & (z - zg < 1.6)
ax[2].scatter(x[sl], y[sl], s=0.5, c="k"); ax[2].plot(*(foot - ring), "r^", ms=10, label="saved stem foot (DBH 22 cm)")
ax[2].plot(0, 0, "b+", ms=14, label="large ring centre"); ax[2].set_aspect("equal"); ax[2].legend(); ax[2].set_title("tree_081, 1.0-1.6 m above ring ground (top view)")
ax[2].set_xlabel("m east"); ax[2].set_ylabel("m north")
fig.tight_layout(); fig.savefig("tree081_views.png", dpi=110)
print("points", n, "height of cloud above ring ground", round(z.max() - zg, 1), "foot-to-ring", round(np.hypot(*(foot - ring)), 2), "m", "pipeline height", attr["height_m"], "dbh", attr["dbh_cm"], attr["dbh_status"])
