"""Compare released tree_attributes.csv across the all-163 runs (reproducibility claim).
Usage: python -I compare_runs.py <results_dir> ; prints max abs numeric diff and status diffs vs FINAL."""
import sys
from pathlib import Path
import pandas as pd, numpy as np
B = Path(sys.argv[1])
runs = {'v1_194253': 'ITSMe_all163_output_20261023_194253', 'v2_195000': 'ITSMe_all163_output_v2_20261023_195000',
        'v3audit_200244': '_superseded_all163_audit_intermediate_runs/ITSMe_all163_output_v3_audit_20261023_200244',
        'v3final_200555': '_superseded_all163_audit_intermediate_runs/ITSMe_all163_output_v3_final_20261023_200555'}
F = pd.read_csv(B / 'ITSMe_all163_output_v3_FINAL_20261023_201144/results/tree_attributes.csv').set_index('tree_id')
num = [c for c in F.columns if F[c].dtype.kind == 'f' and c != 'status']
sts = [c for c in F.columns if c.endswith('_status')]
for k, d in runs.items():
    R = pd.read_csv(B / d / 'results/tree_attributes.csv').set_index('tree_id').reindex(F.index)
    common = [c for c in num if c in R.columns]
    diffs = {c: float(np.nanmax(np.abs(R[c] - F[c]))) for c in common if np.nanmax(np.abs(R[c] - F[c])) > 0 or (R[c].isna() != F[c].isna()).any()}
    nan_mismatch = {c: int((R[c].isna() != F[c].isna()).sum()) for c in common if (R[c].isna() != F[c].isna()).any()}
    sdiff = {c: int((R[c].fillna('NA') != F[c].fillna('NA')).sum()) for c in sts if c in R.columns}
    print(k, '| numeric cols with any diff:', diffs, '| NaN-pattern mismatches:', nan_mismatch, '| status diffs:', sdiff, '| missing cols:', [c for c in F.columns if c not in R.columns])
