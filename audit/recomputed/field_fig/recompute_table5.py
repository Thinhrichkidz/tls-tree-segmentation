"""Recompute Fig.2 status counts and Table 5 from tree_attributes.csv. Usage: python -I this.py tree_attributes.csv outdir"""
import sys, hashlib, pandas as pd, numpy as np
p, out = sys.argv[1], sys.argv[2]
print("sha256", hashlib.sha256(open(p, "rb").read()).hexdigest())
d = pd.read_csv(p); n = len(d)
M = [("Height (m)", "height_m", "height_status"), ("DBH (cm)", "dbh_cm", "dbh_status"),
     ("Crown base (m)", "crown_base_height_m", None),  # no status column exists: status = VALID if value present
     ("Crown area (m2)", "crown_area_m2", "crown_area_status"), ("Crown volume (m3)", "crown_volume_m3", "crown_volume_status")]
def s(x):
    x = x.dropna()
    return f"{x.median():.4f} ({x.min():.4f}-{x.max():.4f})" if len(x) else "-"
rows = []
for name, v, st in M:
    lab = d[st].fillna("N/A") if st else np.where(d[v].notna(), "VALID(no status col)", "N/A")
    lab = pd.Series(lab, index=d.index)
    val_ok = lab.str.startswith("VALID"); rev = lab == "REVIEW"; na = lab == "N/A"
    # consistency: status present iff value present
    mism = int((d[v].notna() != (lab != "N/A")).sum())
    rows.append(dict(metric=name, VALID=int(val_ok.sum()), REVIEW=int(rev.sum()), NA=int(na.sum()),
                     total=int(val_ok.sum() + rev.sum() + na.sum()), value_status_mismatch=mism,
                     valid_median_min_max=s(d.loc[val_ok, v]), all_median_min_max=s(d.loc[val_ok | rev, v]),
                     n_value_nonnull=int(d[v].notna().sum())))
t = pd.DataFrame(rows); t.to_csv(f"{out}/table5_fig2_recomputed.csv", index=False)
assert (t.total == n).all()
print(t.to_string())
print("unique crown_base values:", d.crown_base_height_m.nunique(), "rows with status col 'status' non-null:", d.status.notna().sum())
print("dbh REVIEW notes containing 'fallback':", int(d.loc[d.dbh_status=="REVIEW","notes"].str.contains("fallback|slice-median", case=False).sum()))
print("height VALID == 53 & truncated flag count:", int(d.flag_truncated_top.sum()))
