# Auditor recomputation scripts

All scripts are read-only on the project. Run them from `D:\22083142\audit` with `python -I`. They need Python 3.12 with numpy, pandas, scipy and laspy.

Set this first:

```bash
F=../outputs/WSL_ML2A/55x55/3cm/Codex_help/measurement_pipeline/results
```

| Script | Command | Output |
|---|---|---|
| Statuses, Table 5, stats, flags, all-VALID, rule re-derivation | `python -I recomputed/recompute_attributes.py $F/ITSMe_all163_output_v3_FINAL_20261023_201144 $F/all_tree_preliminary_heights.csv recomputed/out_attributes` | `out_attributes/recomputed_stats.json`, `per_tree_recomputed.csv`, `status_recompute_diff.csv` |
| Own DBH circle re-fit + height (80 trees, ~90 s) | `python -I recomputed/independent_dbh_refit.py $F/ITSMe_all163_output_v3_FINAL_20261023_201144 recomputed/out_attributes/independent_dbh_refit.csv` | csv + stdout (saved as `independent_dbh_refit.log`) |
| Cross-run reproducibility | `python -I recomputed/compare_runs.py $F` | stdout |
| Point-cloud headers (LAS/PLY, header only) | `python -I recomputed/data/hdr.py ...` (see its docstring) | `agent_data/hdr_*.csv` |
| Header summaries | `python -I recomputed/data/summ.py agent_data/hdr_*.csv` | stdout |
| CRS WKT | `python -I recomputed/data/wkt.py <las/laz>` | stdout |
| Directory/hash/ID-pairing comparison | `python -I recomputed/data/compare.py agent_data` | stdout |
| TreeData audit | `python -I recomputed/field_fig/audit_treedata_indep.py C:/Users/hoang/Downloads/TreeData.csv agent_field_fig` | `agent_field_fig/treedata_*` |
| Table 5 / Fig. 2 | `python -I recomputed/field_fig/recompute_table5.py` (see docstring) | `agent_field_fig/table5_fig2_recomputed.csv` |
| Key-file inventory | `python -I recomputed/make_inventory.py inventory_keyfiles.csv <paths...>` | `inventory_keyfiles.csv` |
| Claim register + consistency matrix | `python -I recomputed/build_registers.py .` | `claim_register.csv`, `consistency_matrix.csv` |

`itsme_source_dump.txt` holds the ITSMe 2.0.0 `diameter_slice_pc`/`dbh_pc` source. It was printed with local R 4.4.3 from `measurement_pipeline/environment/home-R-library`.
