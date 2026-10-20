"""Reproducible audit of TreeData.csv for the INFO6003 report.

Usage: python3 -I audit_inventory.py path/to/TreeData.csv
Rules:
  * read every cell as a string (no automatic NA conversion), strip whitespace;
  * a "site-linked record" has a non-blank site_id;
  * only dbh1..dbh11 are converted to numbers; blank cells stay missing;
  * log/stump = exact species labels 'log', 'stump', 'stump log';
  * status codes are lower-cased before counting;
  * SD uses n-1; quartiles use linear interpolation (numpy default).
"""
import hashlib
import json
import sys

import numpy as np
import pandas as pd

path = sys.argv[1]
sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
df = raw.apply(lambda s: s.str.strip())
out = {"sha256": sha, "rows_parsed": len(df), "columns": df.shape[1]}

blank_site = df[df.site_id == ""]
out["rows_blank_site"] = len(blank_site)
out["blank_site_nonblank_fields"] = [
    {k: v for k, v in r.items() if v} for _, r in blank_site.iterrows()]
d = df[df.site_id != ""].copy()
out["site_linked"] = len(d)
out["site_ids"] = d.site_id.nunique()

LS = ["log", "stump", "stump log"]
d["is_ls"] = d.species.isin(LS)
out["log_stump_by_label"] = d[d.is_ls].species.value_counts().to_dict()
out["log_stump_total"] = int(d.is_ls.sum())
other = d[~d.is_ls]
out["other_records"] = len(other)
out["other_ident_strings"] = other.species.nunique()
out["other_blank_species"] = int((other.species == "").sum())
out["top_species"] = other.species.value_counts().head(8).to_dict()
out["unresolved_labels"] = {k: int((other.species == k).sum())
                            for k in ["unknown Euc", "Unidentified", "unknown"]}
# case-insensitive near-duplicates (possible spelling variants, not repaired)
low = other.species.str.lower().str.replace(r"\s+", " ", regex=True)
out["ident_strings_casefolded"] = low.nunique()

# log_species column
ls_col = d.log_species != ""
out["log_species_nonblank"] = int(ls_col.sum())
out["log_species_nonblank_on_logstump"] = int((ls_col & d.is_ls).sum())
out["log_species_values"] = d.loc[ls_col, "log_species"].value_counts().to_dict()

# prefixes
d["prefix"] = d.site_id.str.extract(r"^(DSF|WSF|RF)", expand=False).fillna("OTHER")
dbh = [f"dbh{i}" for i in range(1, 12)]
num = d[dbh].apply(lambda s: pd.to_numeric(s.replace("", np.nan), errors="coerce"))
bad = ((d[dbh] != "") & num.isna()).sum().sum()
out["nonblank_dbh_failed_conversion"] = int(bad)
d1 = num["dbh1"]
pref = {}
for p, g in d.groupby("prefix"):
    pref[p] = {"site_ids": g.site_id.nunique(), "records": len(g),
               "log_stump": int(g.is_ls.sum()), "other": int((~g.is_ls).sum()),
               "median_dbh1": float(np.nanmedian(d1[g.index]))}
out["by_prefix"] = pref


def summ(x):
    x = np.asarray(x.dropna(), float)
    return {"n": len(x), "mean": round(x.mean(), 2), "sd": round(x.std(ddof=1), 2),
            "min": x.min(), "q1": round(np.percentile(x, 25), 2),
            "median": round(np.median(x), 2), "q3": round(np.percentile(x, 75), 3),
            "max": x.max()}


out["A_all_dbh1"] = summ(d1)
out["B_dbh1_excl_logstump"] = summ(d1[~d.is_ls])
out["C_all_slots"] = summ(num.stack())

# slot occupancy and status per slot
slots = {}
for i in range(1, 12):
    n = num[f"dbh{i}"].notna()
    st = d.loc[n, f"live_dead{i}"].str.lower()
    slots[i] = {"count": int(n.sum()), **{("code_"+k) if k else "blank": int(v)
                                      for k, v in st.value_counts().items()}}
out["slots"] = slots
cnt = num.notna().sum(axis=1)
out["records_numeric_dbh"] = {"exactly_one": int((cnt == 1).sum()),
                              "two_or_more": int((cnt >= 2).sum()),
                              "none": int((cnt == 0).sum()),
                              "all_eleven": int((cnt == 11).sum())}
out["record_without_dbh"] = d.loc[cnt == 0, ["site_id", "species", "tag_id",
                                             "live_dead1", "notes"]].to_dict("records")
# status across records
out["live_dead1_all"] = d.live_dead1.str.lower().value_counts().to_dict()
out["live_dead1_raw_case"] = d.live_dead1.value_counts().to_dict()
out["live_dead1_other"] = other.live_dead1.str.lower().value_counts().to_dict()
cells = []
for i in range(1, 12):
    n = num[f"dbh{i}"].notna()
    cells += list(d.loc[n, f"live_dead{i}"].str.lower())
out["status_numeric_cells"] = pd.Series(cells).value_counts().to_dict()
out["canopy_live_dead"] = d.canopy_live_dead.str.lower().value_counts().to_dict()

# quadrants
out["quadrants"] = d.quadrant_id.replace("", "MISSING").value_counts().to_dict()
sq = d[d.quadrant_id != ""].groupby(["site_id", "quadrant_id"]).size()
out["site_quadrant_pairs"] = {"n": len(sq), "median": float(sq.median()),
                              "min": int(sq.min()), "max": int(sq.max())}
miss = d[d.quadrant_id == ""].groupby("site_id").size()
tot = d.groupby("site_id").size()
out["sites_with_missing_quadrants"] = {s: f"{int(miss[s])}/{int(tot[s])}" for s in miss.index}
nq = d[d.quadrant_id != ""].groupby("site_id").quadrant_id.nunique()
out["sites_with_lt4_quadrants"] = nq[nq < 4].to_dict()

# tags
out["tag_no_tag"] = int((d.tag_id == "no_tag").sum())
out["tag_blank"] = int((d.tag_id == "").sum())
real = d[~d.tag_id.isin(["", "no_tag"])]
by_tag = real.groupby("tag_id").site_id.nunique()
rep = by_tag[by_tag > 1].index
out["tags_repeated_across_sites"] = {"identifiers": len(rep),
                                     "records": int(real.tag_id.isin(rep).sum()),
                                     "ids": list(rep)}
out["dup_site_tag_pairs"] = int(real.duplicated(["site_id", "tag_id"]).sum())
out["dup_tag_within_any"] = int(real.duplicated(["tag_id"]).sum())
out["notes_tag_1934"] = d.loc[d.notes.str.contains("1934"), ["site_id", "tag_id", "notes"]].to_dict("records")

# notes
nl = d.notes.str.lower()
out["notes_outside_or_boundary"] = int(nl.str.contains("outside|boundary").sum())
out["notes_stem_terms"] = int(nl.str.contains("stem").sum())
for phrase in ["two stems", "large tree 3 stems", "multi stem", "fork"]:
    out[f"notes_contains::{phrase}"] = int(nl.str.contains(phrase, regex=False).sum())
ms = nl.str.contains("stem") & (cnt >= 2)
out["stem_note_and_multi_slot"] = int(ms.sum())
out["stem_note_records"] = int(nl.str.contains("stem").sum())
for phrase in ["two stems", "large tree 3 stems", "multi stem"]:
    m = nl.str.contains(phrase, regex=False)
    out[f"slots_for::{phrase}"] = cnt[m].tolist()
out["site_ids_without_underscore"] = sorted(s for s in d.site_id.unique() if "_" not in s)
out["coordinate_or_height_columns"] = [c for c in df.columns if any(
    k in c.lower() for k in ["x", "y", "lat", "lon", "east", "north", "height", "coord"])]
out["dbh1_gt_90_file_units"] = int((d1 > 90).sum())
out["dbh1_lt_10_excl_logstump"] = int(((d1 < 10) & ~d.is_ls).sum())
out["dbh1_ge_10_excl_logstump"] = int(((d1 >= 10) & ~d.is_ls).sum())
out["notes_fork"] = int(nl.str.contains("fork").sum())
out["notes_nonblank"] = int((d.notes != "").sum())
print(json.dumps(out, indent=1, default=str))
