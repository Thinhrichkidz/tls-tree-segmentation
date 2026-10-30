"""Labelled TLS stem map beside the field site map, both north-up and at the same metre scale, so anchor trees
can be picked by eye. Circle radius uses the field map's own symbol scale (radius about 0.02 m per cm DBH).
Read-only on all inputs; writes only into this folder. Run: python -I make_stem_map.py"""
import csv, math
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

R = "D:/22083142/"
V6 = R + "outputs/WSL_ML2A/55x55/3cm/Codex_help/measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028/results/tree_attributes.csv"
OUT = Path(__file__).resolve().parent
posts = list(csv.DictReader(open(OUT.parent / "plot_posts_utm.csv", encoding="utf-8")))
C = next((float(p["utm56s_e"]), float(p["utm56s_n"])) for p in posts if p["post"] == "c")
VIEW, RADIUS, NBIG = 24.0, 15.0, 25

# Field map scale, from the digitised scale bar and circle (coordinates in the 2000 px display of the 7015 px image).
mp = {r["kind"]: r for r in csv.DictReader(open(OUT.parent / "map_digitised.csv", encoding="utf-8")) if r["kind"] in ("scale", "circle_centre")}
m_per_px = 20.0 / (float(mp["scale"]["py"]) - float(mp["scale"]["px"]))
ccx, ccy = float(mp["circle_centre"]["px"]), float(mp["circle_centre"]["py"])
# Symbol scale on the field map: radius (px) / DBH (cm), from 1437 (72 px, 107.5 cm) and 1439 (60 px, 90 cm).
r_per_cm = m_per_px * (72 / 107.5 + 60 / 90) / 2

f = lambda s: float(s) if s not in ("", "NA") else None
tls = list(csv.DictReader(open(V6, encoding="utf-8")))
near = [r for r in tls if math.dist((float(r["stem_x"]), float(r["stem_y"])), C) <= VIEW + 4]
big = {r["tree_id"] for r in sorted(near, key=lambda r: -int(r["n_points"]))[:NBIG]}

with open(OUT / "tls_stems_near_plot.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["tree_id", "east_of_gps_centre_m", "north_of_gps_centre_m", "dist_from_gps_centre_m", "dbh_cm", "dbh_status",
                "dbh_estimated_cm", "height_m", "n_points", f"top{NBIG}_by_points"])
    for r in sorted(near, key=lambda r: r["tree_id"]):
        x, y = float(r["stem_x"]) - C[0], float(r["stem_y"]) - C[1]
        w.writerow([r["tree_id"], round(x, 2), round(y, 2), round(math.hypot(x, y), 2), r["dbh_cm"], r["dbh_status"],
                    r["dbh_estimated_cm"], round(float(r["height_m"]), 1), r["n_points"], r["tree_id"] in big])

def tls_panel(ax, fs=7):
    for r in near:
        x, y = float(r["stem_x"]) - C[0], float(r["stem_y"]) - C[1]
        d = f(r["dbh_cm"]); e = f(r["dbh_estimated_cm"])
        if d:
            ax.add_patch(Circle((x, y), max(d * r_per_cm, 0.15), fc="#4daf4a" if r["dbh_status"] == "VALID" else "#a6d96a", ec="k", lw=0.6))
        elif e:
            ax.add_patch(Circle((x, y), max(e * r_per_cm, 0.15), fc="#fee08b", ec="k", lw=0.6, ls="--"))
        else:
            ax.add_patch(Circle((x, y), 0.35, fc="white", ec="k", lw=0.8))
        ax.annotate(r["tree_id"][5:], (x, y), xytext=(3, 3), textcoords="offset points", fontsize=fs,
                    fontweight="bold" if r["tree_id"] in big else "normal", color="#b2182b" if r["tree_id"] in big else "0.25")
    for p in posts:
        x, y = float(p["utm56s_e"]) - C[0], float(p["utm56s_n"]) - C[1]
        ax.plot(x, y, "*", ms=13, color="gold", mec="k", zorder=5)
        ax.annotate("GPS " + p["post"].upper(), (x, y), xytext=(5, -10), textcoords="offset points", fontsize=fs, color="0.1")
    ax.add_patch(Circle((0, 0), RADIUS, fill=False, ls="--", ec="tab:blue", lw=1.5))
    ax.set_xlim(-VIEW, VIEW); ax.set_ylim(-VIEW, VIEW); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_xlabel("East of GPS centre (m)"); ax.set_ylabel("North of GPS centre (m)")

legend = [Circle((0, 0), 1, fc="#4daf4a", ec="k"), Circle((0, 0), 1, fc="#a6d96a", ec="k"),
          Circle((0, 0), 1, fc="#fee08b", ec="k", ls="--"), Circle((0, 0), 1, fc="white", ec="k")]
labels = ["DBH VALID", "DBH REVIEW", "DBH ESTIMATED only", "no DBH (size unknown)"]
note = f"Number = tree_NNN. Bold red = {NBIG} largest TLS trees by point count. Dashed circle = 15 m on GPS centre (GPS may be several m off)."

# 1. Side by side: TLS (left), field map (right), same metres and same symbol scale.
img = plt.imread(R + "Bullaburra site layout amd1.jpeg")
k = 2000 / img.shape[1]  # display px per original px
fig, (a1, a2) = plt.subplots(1, 2, figsize=(20, 10.5))
tls_panel(a1)
a1.set_title("TLS stems (v6 FINAL), EPSG:32756, north up")
a1.legend(legend, labels, loc="lower left", fontsize=8)
h, w_ = img.shape[:2]
a2.imshow(img, extent=[(0 - ccx) * m_per_px, (w_ * k - ccx) * m_per_px, -(h * k - ccy) * m_per_px, -(0 - ccy) * m_per_px])
a2.set_xlim(-VIEW, VIEW); a2.set_ylim(-VIEW, VIEW); a2.set_aspect("equal"); a2.grid(alpha=0.3)
a2.set_xlabel("East of map circle centre (m)"); a2.set_title("Field site map (approximate, not georeferenced), same scale")
fig.suptitle("WSF_ML2A: pick 2-3 anchor trees that clearly correspond. " + note, fontsize=10)
fig.tight_layout(); fig.savefig(OUT / "stem_map_side_by_side.png", dpi=150)

# 2. TLS stem map alone, large, for printing or zooming.
fig, ax = plt.subplots(figsize=(14, 14))
tls_panel(ax, fs=9)
ax.legend(legend, labels, loc="lower left", fontsize=10)
ax.set_title("WSF_ML2A TLS stem map (v6 FINAL). " + note, fontsize=10)
fig.tight_layout(); fig.savefig(OUT / "tls_stem_map.png", dpi=150)
print(len(near), "TLS stems shown;", "m/px", round(m_per_px, 5), "radius m/cm", round(r_per_cm, 4))
