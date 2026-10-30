"""Report figure: the 30 m field plot located in the TLS crop, with the final tree matches (placement A).
Read-only on inputs. Run: python -I make_plot_location_map.py -> plot_location_map.png"""
import csv
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

CH = "../../"
att = list(csv.DictReader(open(CH + "measurement_pipeline/results/ITSMe_all163_output_v6_FINAL_20261028/results/tree_attributes.csv", encoding="utf-8")))
posts = {r["post"]: complex(float(r["utm56s_e"]), float(r["utm56s_n"])) for r in csv.DictReader(open("../plot_overlay/plot_posts_utm.csv"))}
C0 = posts["c"]; FIT = complex(261365.71, 6264469.80)  # north-up map fit (sensitivity centre)
P = {r["tag"]: complex(float(r["utm_e"]), float(r["utm_n"])) for r in csv.DictReader(open("predicted_field_positions_A.csv"))}
M = list(csv.DictReader(open("tree_matches_A_final.csv", encoding="utf-8")))
LOC = complex(261350, 6264460)  # same anchor-base refinements as match_placement_A_final.py
pos = {r["tree_id"]: complex(float(r["stem_x"]), float(r["stem_y"])) for r in att}
pos.update({k: LOC + v for k, v in {"tree_074": 5.3877 + 5.0187j, "tree_163": 8.7983 + 2.8987j, "tree_103": 20.7836 + 2.4253j,
                                    "tree_079S": 5.2528 + 19.3628j, "tree_079N": 3.6905 + 21.7563j}.items()})
rel = lambda z: ((z - C0).real, (z - C0).imag)

fig, ax = plt.subplots(figsize=(3.3, 3.3))
R = 24
for r in att:
    x, y = rel(pos[r["tree_id"]]); d = r["dbh_cm"] if r["dbh_cm"] not in ("", "NA") else r["dbh_estimated_cm"]
    if abs(x) < R and abs(y) < R:
        ax.scatter(x, y, s=(float(d) / 5) ** 2 if d not in ("", "NA") else 6, c="0.75", edgecolors="0.45", lw=.4, zorder=1)
for c, ls, lab in ((C0, "--", "15 m circle, GPS centre"), (FIT, ":", "15 m circle, map-fitted centre")):
    ax.add_patch(plt.Circle(rel(c), 15, fill=False, ls=ls, color="k", lw=1, label=lab))
for k in "nesw":
    ax.plot(*rel(posts[k]), "k^", ms=5, zorder=3)
ax.plot(0, 0, "k^", ms=5, label="GPS centre and posts", zorder=3)
style = {"confirmed": dict(color="k", lw=1.6), "probable": dict(color="0.5", lw=1.2)}
for m in M:
    p = rel(P[m["tag"]]); cls = m["match_class"]
    if cls in style:
        t = rel(pos[m["tls_tree"]]); ax.plot([p[0], t[0]], [p[1], t[1]], **style[cls], zorder=2)
        ax.plot(*p, "o", mfc="w" if cls == "probable" else "k", mec=style[cls]["color"], ms=4, zorder=4)
    else:
        ax.plot(*p, "x", color="k", ms=4, zorder=4)
OFF = {"1437": (-8, -11), "1448": (-6, -11)}  # keep labels off neighbouring matches
for tag in ("1439", "1435", "1437", "1455", "1448"):
    x, y = rel(P[tag]); ax.annotate(tag, (x, y), fontsize=6.5, xytext=OFF.get(tag, (3, 3)), textcoords="offset points")
ax.plot([], [], "o-", color="k", mfc="k", ms=4, label="confirmed (field to TLS)")
ax.plot([], [], "o-", color="0.5", mfc="w", ms=4, label="probable")
ax.plot([], [], "x", color="k", ms=4, label="unmatched / excluded")
ax.set_xlim(-R, R); ax.set_ylim(-R, R); ax.set_aspect("equal"); ax.grid(alpha=.25)
ax.set_xlabel("m east of GPS centre", fontsize=8); ax.set_ylabel("m north of GPS centre", fontsize=8); ax.tick_params(labelsize=7)
ax.legend(fontsize=5.6, loc="upper left", framealpha=.9)
fig.tight_layout(); fig.savefig("plot_location_map.png", dpi=220)
print("ok")
