"""Vertical profile of the full 3 cm crop around the unassigned ~1.1 m ring south of predicted 1437: trunk, stump or log?"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
crop = "D:/22083142/data/cropped/WSL_ML2A/55x55/3cm/WSL_ML2A_crop_55x55_3cm.ply"
with open(crop, "rb") as f:
    while b"end_header" not in f.readline(): pass
    off = f.tell()
dt = np.dtype([("x", "<f8"), ("y", "<f8"), ("z", "<f8")] + [(n, "<f4") for n in "abcdef"])
pts = np.memmap(crop, dtype=dt, mode="r", offset=off)
c = np.array([261362.53, 6264453.48]); sel = []
for i in range(0, len(pts), 5_000_000):
    ch = pts[i:i + 5_000_000]; m = (np.abs(ch["x"] - c[0]) < 3) & (np.abs(ch["y"] - c[1]) < 3)
    sel.append(np.column_stack([ch["x"][m] - c[0], ch["y"][m] - c[1], ch["z"][m]]))
a = np.vstack(sel); r = np.hypot(a[:, 0], a[:, 1]); zg = np.percentile(a[r < 2, 2], 1); h = a[:, 2] - zg
for lo in np.arange(0, 14, 1.0):
    b = (h >= lo) & (h < lo + 1)
    print(f"{lo:4.0f}-{lo+1:.0f} m: pts within 0.8 m = {int((b & (r < 0.8)).sum()):6d}, ring-shaped (0.35-0.75 m) = {int((b & (r > .35) & (r < .75)).sum()):6d}, inside (<0.3 m) = {int((b & (r < .3)).sum()):5d}")
fig, ax = plt.subplots(1, 2, figsize=(11, 7))
k = r < 2.5
ax[0].scatter(a[k, 0], h[k], s=.2, c="k"); ax[0].set_xlabel("m east of ring centre"); ax[0].set_ylabel("m above ground"); ax[0].set_ylim(-0.5, 15)
ax[1].scatter(a[k, 1], h[k], s=.2, c="k"); ax[1].set_xlabel("m north of ring centre"); ax[1].set_ylim(-0.5, 15)
for x in ax: x.axhline(1.3, color="r", lw=.8)
fig.suptitle("Full 3 cm crop within 2.5 m of the unassigned ring (all points, any owner)"); fig.tight_layout(); fig.savefig("ring_side_views.png", dpi=110)
