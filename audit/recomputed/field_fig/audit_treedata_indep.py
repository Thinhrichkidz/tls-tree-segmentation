"""Independent recomputation of TreeData.csv claims (audit). Usage: python -I this.py TreeData.csv outdir"""
import sys, hashlib, json, re, pandas as pd, numpy as np
path, outdir = sys.argv[1], sys.argv[2]
raw_bytes = open(path, "rb").read()
o = {"sha256": hashlib.sha256(raw_bytes).hexdigest(), "bytes": len(raw_bytes),
     "physical_lines": raw_bytes.count(b"\n")}
df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig").apply(lambda s: s.str.strip())
o["columns"] = df.shape[1]; o["data_rows"] = len(df)
empty = (df == "").all(axis=1)
o["fully_empty_rows"] = int(empty.sum()); o["blank_site_rows"] = int((df.site_id == "").sum())
o["blank_site_row_nonblank_fields"] = df[df.site_id == ""].apply(lambda r: {k: v for k, v in r.items() if v}, axis=1).tolist()
d = df[df.site_id != ""].copy()
o["site_linked"] = len(d); o["n_sites"] = d.site_id.nunique()
o["sites"] = sorted(d.site_id.unique())
o["site_prefix_counts"] = d.site_id.str.extract(r"^([A-Z]+)")[0].value_counts().to_dict()
# plot-name search across every cell
allcells = df.astype(str)
for pat in ["ML2A", "WSL"]:
    hits = allcells.apply(lambda s: s.str.contains(pat, case=False)).any(axis=1)
    o[f"rows_with_{pat}"] = int(hits.sum())
    o[f"site_ids_with_{pat}"] = sorted(df.loc[hits, "site_id"].unique())
o["raw_text_contains_WSL_ML2A"] = b"WSL_ML2A" in raw_bytes
o["raw_text_contains_WSF_ML2A"] = b"WSF_ML2A" in raw_bytes
cols = list(df.columns)
o["dbh_columns"] = [c for c in cols if re.fullmatch(r"dbh\d+", c)]
o["columns_matching_coord_or_height"] = [c for c in cols if re.search(r"(^|_)(x|y|z|lat|lon|long|easting|northing|coord|height|ht)($|_)", c.lower())]
o["all_columns"] = cols
# definitions
sp = d.species.str.lower()
LS = sp.isin(["log", "stump", "stump log"])
o["log_stump_exact_labels"] = d.loc[LS, "species"].value_counts().to_dict(); o["log_stump_total"] = int(LS.sum())
o["log_stump_alt_regex_log_or_stump_anywhere"] = int(sp.str.contains(r"\b(log|stump)\b").sum())
o["stump_height_nonblank"] = int((d.stump_height_m != "").sum()); o["log_length_nonblank"] = int((d.log_length_m != "").sum())
o["log_species_nonblank"] = int((d.log_species != "").sum())
fern = sp.str.match(r"^(dicksonia|cyathea)\b")
o["fern_labels"] = d.loc[fern, "species"].value_counts().to_dict(); o["fern_total"] = int(fern.sum())
# climber candidates: genus list by botanical knowledge (Cissus/Apocissus water vine, Parsonsia silkpod, Celastrus staff vine)
clim_core = sp.str.match(r"^(cissus|apocissus|parsonsia)\b")
clim_cel = sp.str.match(r"^(celestrus|celastrus)\b")
o["climber_core_labels"] = d.loc[clim_core, "species"].value_counts().to_dict(); o["climber_core_total"] = int(clim_core.sum())
o["climber_plus_celastrus_total"] = int((clim_core | clim_cel).sum())
o["ficus_rubiginosa"] = int(sp.str.startswith("ficus").sum())
o["species_blank"] = int((d.species == "").sum())
qm = d.quadrant_id == ""
o["quadrant_missing_site_linked"] = int(qm.sum()); o["quadrant_missing_all_rows"] = int((df.quadrant_id == "").sum())
o["quadrant_values"] = d.quadrant_id.replace("", "MISSING").value_counts().to_dict()
o["quadrant_missing_by_site"] = d[qm].site_id.value_counts().to_dict()
# tags
real = d[~d.tag_id.str.lower().isin(["", "no_tag"])]
o["tag_blank"] = int((d.tag_id == "").sum()); o["tag_no_tag"] = int((d.tag_id.str.lower() == "no_tag").sum())
ns = real.groupby("tag_id").site_id.nunique(); rep = ns[ns > 1]
o["tags_recurring_across_sites"] = len(rep)
o["tags_recurring_detail"] = {t: sorted(real.loc[real.tag_id == t, "site_id"].unique()) for t in rep.index}
o["tags_recurring_across_sites_incl_no_tag"] = int((d[d.tag_id != ""].groupby("tag_id").site_id.nunique() > 1).sum())
o["tag_dup_within_site_pairs"] = int(real.duplicated(["site_id", "tag_id"]).sum())
# diameters
dbh = o["dbh_columns"]
num = d[dbh].apply(lambda s: pd.to_numeric(s.replace("", np.nan), errors="coerce"))
o["nonblank_dbh_nonnumeric"] = int(((d[dbh] != "") & num.isna()).sum().sum())
d1 = num["dbh1"]; nls = ~LS
o["nonLS_records"] = int(nls.sum()); o["nonLS_with_numeric_dbh1"] = int((nls & d1.notna()).sum())
o["nonLS_dbh1_lt10"] = int((nls & (d1 < 10)).sum()); o["nonLS_dbh1_ge10"] = int((nls & (d1 >= 10)).sum())
o["nonLS_dbh1_lt10_values"] = d1[nls & (d1 < 10)].tolist()
o["nonLS_dbh1_min_median_max"] = [float(d1[nls].min()), float(d1[nls].median()), float(d1[nls].max())]
o["stems_per_record"] = num.notna().sum(axis=1).value_counts().sort_index().to_dict()
json.dump(o, open(f"{outdir}/treedata_recomputed.json", "w"), indent=1, default=str)
pd.Series({k: v for k, v in o.items() if not isinstance(v, (list, dict))}).to_csv(f"{outdir}/treedata_recomputed_scalars.csv", header=["value"])
d.groupby("site_id").agg(records=("species", "size"), log_stump=("species", lambda s: int(s.str.lower().isin(["log","stump","stump log"]).sum())),
    quadrant_missing=("quadrant_id", lambda s: int((s == "").sum()))).to_csv(f"{outdir}/treedata_by_site.csv")
# self-check: partition consistency
assert o["site_linked"] + o["blank_site_rows"] == o["data_rows"]
assert o["nonLS_records"] + o["log_stump_total"] == o["site_linked"]
print(json.dumps(o, indent=1, default=str))
