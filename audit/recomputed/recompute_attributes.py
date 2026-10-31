"""Independent recomputation of the v4 report's attribute statistics and QC statuses.

Usage: python -I recompute_attributes.py <FINAL_DIR> <PRELIM_HEIGHTS_CSV> <OUT_DIR>
Reads (read-only): <FINAL_DIR>/results/{tree_attributes.csv,outliers.csv,summary.json},
<FINAL_DIR>/logs/records.json, <FINAL_DIR>/per_tree/*/{prep.json,result.json}, inherited QC csv.
Writes: <OUT_DIR>/recomputed_stats.json, status_recompute_diff.csv, per_tree_recomputed.csv
Statuses are re-derived from the rules as DOCUMENTED (methods.json + report Table 3), written
independently of all163_postprocess.py; disagreements are listed, not resolved.
"""
import json, sys, math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as ss

final, prelim, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
ta = pd.read_csv(final / 'results/tree_attributes.csv')
ol = pd.read_csv(final / 'results/outliers.csv')
summ = json.loads((final / 'results/summary.json').read_text())
recs = {r['tree']: r for r in json.loads((final / 'logs/records.json').read_text())}
qc = pd.read_csv(prelim).set_index('stable_tree_id')
R = {}

def st(series):
    return series.fillna('N/A').value_counts().to_dict()

# ---- 1. status counts straight from the released CSV
R['csv_status_counts'] = {c: st(ta[c]) for c in ['height_status', 'dbh_status', 'crown_area_status', 'crown_volume_status']}
R['csv_status_column_all_nan'] = bool(ta['status'].isna().all())
R['records_status_counts'] = {k: pd.Series([recs[t][k]['s'] for t in recs]).value_counts().to_dict()
                              for k in ['height', 'dbh', 'crown_base', 'crown_area', 'crown_volume', 'crown_length', 'crown_ratio', 'crown_diameter']}
# csv vs records agreement per tree
dis = []
for _, row in ta.iterrows():
    r = recs[row.tree_id]
    for c, k in [('height_status', 'height'), ('dbh_status', 'dbh'), ('crown_area_status', 'crown_area'), ('crown_volume_status', 'crown_volume')]:
        a = row[c] if isinstance(row[c], str) else 'N/A'
        if a != r[k]['s']:
            dis.append((row.tree_id, k, a, r[k]['s']))
R['csv_vs_records_status_disagreements'] = dis

# ---- 2. all-core-VALID
core = ['height_status', 'dbh_status', 'crown_area_status', 'crown_volume_status']
allv = ta[(ta[core] == 'VALID').all(axis=1)]
R['all_core_valid_from_csv'] = len(allv)
R['all_core_valid_trees'] = sorted(allv.tree_id)
R['all_core_valid_flag_in_records'] = sum(r['all_core_valid'] for r in recs.values())
R['all_core_valid_medians'] = dict(height=allv.height_m.median(), dbh_cm=allv.dbh_cm.median(), volume_m3=allv.crown_volume_m3.median())
stale = sorted(t for t, r in recs.items() if r['all_core_valid'] and t not in set(allv.tree_id))
R['all_core_valid_stale_trees'] = {t: [ (k, recs[t][k]['s'], recs[t][k]['why'][-90:]) for k in ['height','dbh','crown_area','crown_volume'] if recs[t][k]['s']!='VALID'] for t in stale}
ts = pd.Series([r['tree_status'] for r in recs.values()]).value_counts().to_dict()
R['tree_status_records'] = ts
have = ta[core].isin(['VALID', 'REVIEW']).sum(axis=1)
R['tree_status_recomputed_from_csv'] = {'SUCCESS': int((have == 4).sum()), 'PARTIAL': int(((have > 0) & (have < 4)).sum()), 'FAILED': int((have == 0).sum())}

# ---- 3. DBH outcomes
meth = pd.Series({t: (r.get('dbh_method') or '') for t, r in recs.items()})
dbh_ok = ta.set_index('tree_id').dbh_cm.notna()
R['dbh_available'] = int(dbh_ok.sum())
R['dbh_method_counts_available'] = meth[dbh_ok[dbh_ok].index].value_counts().to_dict()
na = ta[ta.dbh_status.isna()].tree_id
whyna = pd.Series({t: recs[t]['dbh']['why'] for t in na})
R['dbh_na_total'] = len(na)
R['dbh_na_no_axis'] = int(whyna.str.startswith('no stem axis').sum())
R['dbh_na_fit_failed'] = int(whyna.str.startswith('fit failed').sum())
R['dbh_na_other'] = whyna[~whyna.str.startswith(('no stem axis', 'fit failed'))].to_dict()
# DBH REVIEW reasons
rv = ta[ta.dbh_status == 'REVIEW'].tree_id
reasons = {}
for t in rv:
    for part in recs[t]['dbh']['why'].split('; '):
        key = part.split(' (')[0]
        key = 'clusters at 1.3 m' if 'point clusters' in key else key
        key = 'axis/foot offset' if key.startswith('stem axis meets') else key
        reasons[key] = reasons.get(key, 0) + 1
R['dbh_review_reason_counts'] = reasons
R['dbh_review_only_fallback'] = int(sum(recs[t]['dbh']['why'] == 'median of accepted 1.1-1.5 m slices, not a direct 1.3 m fit' for t in rv))
# slice point counts among failed fits
pts_failed = ta.loc[ta.dbh_status.isna(), ['tree_id', 'dbh_n_points']]
R['failed_with_slice_points_known'] = int(pts_failed.dbh_n_points.notna().sum())
R['failed_slice_points_lt10'] = int((pts_failed.dbh_n_points < 10).sum())
R['failed_slice_points_describe'] = pts_failed.dbh_n_points.describe().to_dict()
R['fit_failed_trees_points_lt10'] = sorted(pts_failed[pts_failed.dbh_n_points < 10].tree_id)

# ---- 4. H/D and Spearman
both = ta[ta.dbh_cm.notna() & ta.height_m.notna()].copy()
both['hd'] = both.height_m / (both.dbh_cm / 100)
R['hd_n'] = len(both)
R['hd_min_max_median'] = [both.hd.min(), both.hd.max(), both.hd.median()]
R['hd_if_dbh_in_cm_unitless_wrong'] = [ (both.height_m / both.dbh_cm).min(), (both.height_m / both.dbh_cm).max()]
rho, p = ss.spearmanr(both.height_m, both.dbh_cm)
R['spearman_all'] = dict(n=len(both), rho=rho, p=p, ties_h=int(both.height_m.duplicated().sum()), ties_d=int(both.dbh_cm.duplicated().sum()))
vv = both[(both.height_status == 'VALID') & (both.dbh_status == 'VALID')]
rho2, p2 = ss.spearmanr(vv.height_m, vv.dbh_cm)
R['spearman_valid_pairs'] = dict(n=len(vv), rho=rho2, p=p2)
R['pearson_all'] = ss.pearsonr(both.height_m, both.dbh_cm)[0]
R['hd_outside_20_150'] = int(((both.hd < 20) | (both.hd > 150)).sum())

# ---- 5. crown derived values
cb = ta.set_index('tree_id').crown_base_height_m
H = ta.set_index('tree_id').height_m
hs = ta.set_index('tree_id').height_status
cbs = pd.Series({t: recs[t]['crown_base']['s'] for t in recs})
mask = (hs == 'VALID') & (cbs[hs.index] == 'VALID')
cl = (H - cb)[mask]
R['crown_length_valid'] = dict(n=int(mask.sum()), median=cl.median())
R['crown_ratio_valid'] = dict(n=int(mask.sum()), median=(cl / H[mask]).median())
ca = ta.set_index('tree_id')
dmask = ca.crown_area_status == 'VALID'
R['crown_eq_diam_valid'] = dict(n=int(dmask.sum()), median=(2 * np.sqrt(ca.crown_area_m2[dmask] / math.pi)).median())
R['crown_base_stats'] = dict(n=int(cb.notna().sum()), median=cb.median(), min=cb.min(), max=cb.max(), review=int((cbs == 'REVIEW').sum()))
R['largest_volume'] = [ca.crown_volume_m3.idxmax(), ca.crown_volume_m3.max(), ca.crown_volume_status[ca.crown_volume_m3.idxmax()]]
R['largest_area'] = [ca.crown_area_m2.idxmax(), ca.crown_area_m2.max(), ca.crown_area_status[ca.crown_area_m2.idxmax()]]
top5v = ca.crown_volume_m3.sort_values(ascending=False).head(10)
R['top10_volume_status'] = {t: [round(v, 1), ca.crown_volume_status[t]] for t, v in top5v.items()}
R['valid_volume_max'] = [ca.crown_volume_m3[ca.crown_volume_status == 'VALID'].idxmax(), ca.crown_volume_m3[ca.crown_volume_status == 'VALID'].max()]

# ---- 6. Table 5 medians/ranges
def mmm(s):
    s = s.dropna()
    return [len(s), s.median(), s.min(), s.max()]
T5 = {}
for name, vcol, scol in [('height', 'height_m', 'height_status'), ('dbh', 'dbh_cm', 'dbh_status'),
                         ('crown_area', 'crown_area_m2', 'crown_area_status'), ('crown_volume', 'crown_volume_m3', 'crown_volume_status')]:
    T5[name] = dict(valid=mmm(ta.loc[ta[scol] == 'VALID', vcol]), all=mmm(ta.loc[ta[scol].isin(['VALID', 'REVIEW']), vcol]))
T5['crown_base'] = dict(valid=mmm(cb[cbs == 'VALID']))
R['table5'] = T5

# ---- 7. outliers
R['outliers_rows'] = len(ol)
R['outliers_reason_counts'] = ol.reason.value_counts().to_dict()
R['outliers_distinct_trees'] = ol.tree_id.nunique()
# ---- 8. structure flags
R['n_stems_dist'] = ta.n_stems_at_1_3m.value_counts().sort_index().to_dict()
R['n_stems_ge2'] = int((ta.n_stems_at_1_3m >= 2).sum())
R['fork'] = int(ta.flag_fork_near_dbh.sum())
R['lean'] = ta.flag_lean.fillna('NA').astype(str).value_counts().to_dict()
R['truncated_top'] = int(ta.flag_truncated_top.sum())
R['crown_touches_edge'] = ta.flag_crown_touches_edge.fillna('NA').astype(str).value_counts().to_dict()
R['stem_dist_to_edge_lt'] = {f'<{d} m': int((ta.dist_to_roi_edge_m < d).sum()) for d in (1, 2, 5)}
R['stem_completeness_lt_0_5'] = int((ta.stem_completeness < 0.5).sum())
# ---- 9. height foot
R['ground_source_counts'] = ta.ground_source.value_counts().to_dict()
R['stem_xy_source_counts'] = ta.stem_xy_source.value_counts().to_dict()
R['fallback_foot_inherited'] = int(qc.foot_method.str.startswith('LOWEST').sum())
R['n_points_total_163'] = int(ta.n_points.sum())
R['crs_column'] = ta.crs.unique().tolist()

# ---- 10. independent status re-derivation from documented rules
rows = []
for t in sorted(recs):
    prep = json.loads((final / 'per_tree' / t / 'prep.json').read_text())
    res = json.loads((final / 'per_tree' / t / 'result.json').read_text())
    q = qc.loc[t]
    hv = res.get('itsme_height_m')
    off = prep.get('axis_offset_from_foot_m')
    # Height: methods.json VALID definition + Table 3 axis-foot rule
    h_doc = 'VALID'
    if q.ground_reference_reliability != 'LOCALLY_SUPPORTED' or not str(q.foot_method).startswith('ROBUST') \
       or q.tree_top_reliability != 'LOCALLY_SUPPORTED_OBSERVED_TIP' or abs(hv - prep['supported_height_m']) > 0.5 \
       or isinstance(q.visual_exclusion_reason, str) or (off is not None and off > 0.25):
        h_doc = 'REVIEW'
    # Height per report Table 3 only (ground or top not locally supported, or axis-foot offset > 0.25)
    h_t3 = 'REVIEW' if (q.ground_reference_reliability != 'LOCALLY_SUPPORTED' or q.tree_top_reliability != 'LOCALLY_SUPPORTED_OBSERVED_TIP'
                         or (off is not None and off > 0.25)) else 'VALID'
    # DBH per report Table 3 only: N/A if no axis or no accepted fit; REVIEW if slice-median fallback
    dm = res.get('dbh_m')
    if prep.get('axis_o') is None:
        d_t3 = 'N/A'
    elif dm is None:
        d_t3 = 'N/A'
    else:
        d_t3 = 'REVIEW' if str(res.get('dbh_method', '')).startswith('median') else 'VALID'
    # Recheck the acceptance rule on the raw 1.3 m fit
    raw = res.get('dbh13_m'); arc = res.get('dbh13_arc'); r2 = res.get('dbh13_R2')
    rule_pass = None
    if raw is not None and arc is not None and r2 is not None:
        rule_pass = (0.03 < raw < 2) and arc >= 0.6 and math.sqrt(r2) <= min(0.04, max(0.01, 0.1 * raw))
    rows.append(dict(tree=t, height_stored=recs[t]['height']['s'], height_documented_rule=h_doc, height_table3_rule=h_t3,
                     dbh_stored=recs[t]['dbh']['s'], dbh_table3_rule=d_t3, dbh_method=res.get('dbh_method'),
                     raw13_cm=None if raw is None else 100 * raw, arc=arc, rmse_cm=None if r2 is None else 100 * math.sqrt(r2),
                     rule_pass_recomputed=rule_pass, dbh13_passes_stored=res.get('dbh13_passes'),
                     edited_after_qc=q.review_sha256 != prep['review_sha256'], axis_foot_offset=off))
pt = pd.DataFrame(rows)
pt.to_csv(out / 'per_tree_recomputed.csv', index=False)
R['height_doc_rule_disagree'] = pt[pt.height_stored != pt.height_documented_rule][['tree', 'height_stored', 'height_documented_rule']].values.tolist()
R['height_table3_rule_disagree_n'] = int((pt.height_stored != pt.height_table3_rule).sum())
R['height_table3_rule_counts'] = pt.height_table3_rule.value_counts().to_dict()
R['dbh_table3_rule_counts'] = pt.dbh_table3_rule.value_counts().to_dict()
R['dbh_table3_vs_stored_disagree_n'] = int((pt.dbh_stored != pt.dbh_table3_rule).sum())
R['edited_after_inherited_qc'] = pt[pt.edited_after_qc].tree.tolist()
m = pt[pt.rule_pass_recomputed.notna() & pt.dbh13_passes_stored.notna()]
R['dbh13_rule_recheck_mismatch'] = m[m.rule_pass_recomputed.astype(bool) != m.dbh13_passes_stored.astype(bool)].tree.tolist()
R['dbh13_rule_checked_n'] = len(m)
pt[(pt.height_stored != pt.height_documented_rule) | (pt.dbh_stored != pt.dbh_table3_rule)].to_csv(out / 'status_recompute_diff.csv', index=False)

# ---- 11. summary.json vs recomputed
R['summary_json_claims'] = dict(trees_all_core_valid=summ['trees_all_core_valid'], tree_status=summ['tree_status'],
                                dbh_fit_ok_false=summ['dbh_fit_ok_false'], edge=summ['edge_affected_trees'])
(out / 'recomputed_stats.json').write_text(json.dumps(R, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o)))
print(json.dumps(R, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o)))
