"""Fit the large unlabelled ring seen south of predicted 1437 and find which of the 163 tree clouds (if any) owns its points."""
import csv, glob, re
import numpy as np
OUT = "./"
P = {r["tag"]: complex(float(r["utm_e"]), float(r["utm_n"])) for r in csv.DictReader(open("predicted_field_positions_A.csv"))}
sl = np.load("slice_1437.npy")
guess = P["1437"] + complex(1.3, -4.4)
m = np.abs(sl[:, 0] + 1j * sl[:, 1] - guess) < 1.0
x0, y0 = sl[m, 0].mean(), sl[m, 1].mean(); x, y = sl[m, 0] - x0, sl[m, 1] - y0
A = np.column_stack([x, y, np.ones_like(x)]); bb = x**2 + y**2
cx, cy, c = np.linalg.lstsq(A, bb, rcond=None)[0]; cx /= 2; cy /= 2; r = np.sqrt(c + cx**2 + cy**2)
cx += x0; cy += y0; x = x + x0; y = y + y0
res = np.abs(np.hypot(x - cx, y - cy) - r)
print(f"ring: n={m.sum()} centre=({cx:.2f},{cy:.2f}) diameter={2*r*100:.0f} cm rms={np.sqrt((res**2).mean())*100:.1f} cm; "
      f"bbox {np.ptp(x)*100:.0f} x {np.ptp(y)*100:.0f} cm; offset from predicted 1437 = {abs(complex(cx,cy)-P['1437']):.1f} m")
zr = (np.percentile(sl[m, 2], 1), np.percentile(sl[m, 2], 99))
own = {}
for f in glob.glob("../../CloudCompare_review_v2/tree_*.ply"):
    with open(f, "rb") as h:
        hdr = []
        while True:
            line = h.readline().decode(errors="replace").strip(); hdr.append(line)
            if line == "end_header": break
        n = int(re.search(r"element vertex (\d+)", "\n".join(hdr)).group(1))
        props = [l.split() for l in hdr if l.startswith("property")]
        tmap = {"double": "<f8", "float": "<f4", "uchar": "u1", "int": "<i4", "float32": "<f4", "float64": "<f8", "uint8": "u1", "uint": "<u4", "uint32": "<u4", "int32": "<i4", "ushort": "<u2", "short": "<i2", "char": "i1"}
        dt = np.dtype([(p[2], tmap[p[1]]) for p in props])
        d = np.fromfile(h, dtype=dt, count=n)
    near = (np.hypot(d["x"] - cx, d["y"] - cy) < r + 0.3) & (d["z"] > zr[0] - 0.5) & (d["z"] < zr[1] + 0.5)
    if near.any(): own[f.split("\\")[-1].split("/")[-1]] = int(near.sum())
print("tree clouds with points in the ring zone:", own or "NONE (ring is not in any of the 163 trees)")
