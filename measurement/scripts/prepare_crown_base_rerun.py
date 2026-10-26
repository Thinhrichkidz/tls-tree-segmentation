"""Record the user-agreed crown bases (23 Oct 2026) for the 20 test trees in a new batch folder.

Rule: base of the continuous crown from CROWN_BASE_PROPOSAL_20261023_190901 (see its PROPOSAL.md), with the user's
choices for the six uncertain trees. Checks that each tree's current ITSMe run used the current source cloud version.
"""
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

MP = Path(__file__).resolve().parents[1]
ROOT = MP.parent
PROPOSAL = MP / 'results/CROWN_BASE_PROPOSAL_20261023_190901'
USER_CHOICES = {'tree_048': 8.25, 'tree_056': 4.25, 'tree_151': 3.00, 'tree_076': 5.00, 'tree_146': 8.50, 'tree_118': 10.75}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def rows(p):
    with Path(p).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

snap = {r['file'][:8]: r['sha256'] for r in rows(ROOT / 'session3_codex_20261023/state/CloudCompare_review_v2_CURRENT.csv')}
assert all(sha(ROOT / 'CloudCompare_review_v2' / r['file']) == r['sha256']
           for r in rows(ROOT / 'session3_codex_20261023/state/CloudCompare_review_v2_CURRENT.csv')), 'Source clouds changed; stop.'
batch = MP / 'results' / f'CROWN_BASE_RERUN_{datetime.now():%Y%m%d_%H%M%S}'
batch.mkdir(exist_ok=False)
out = []
for r in rows(PROPOSAL / 'crown_base_proposal.csv'):
    tid = r['tree']
    run = MP / 'results' / r['current_run']
    metrics, = rows(run / 'tree_metrics.csv')
    assert metrics['review_sha256'] == snap[tid] == r['source_sha256'], f'{tid}: run is not on the current source version'
    rds = run / f'{tid}_crown_classification.rds'
    base = USER_CHOICES.get(tid, float(r['continuous_crown_base_m']) if r['continuous_crown_base_m'] else None)
    assert base is not None, tid
    out.append(dict(tree=tid, crown_base_m=base,
                    base_source='user choice 23 Oct 2026' if tid in USER_CHOICES else 'continuous-crown rule (agreed 23 Oct 2026)',
                    rule_value_m=r['continuous_crown_base_m'], itsme_crown_start_m=r['itsme_crown_start_m'],
                    run_dir=str(run.relative_to(ROOT).as_posix()), crown_rds=str(rds.relative_to(ROOT).as_posix()),
                    crown_rds_sha256=sha(rds), source_sha256=snap[tid],
                    flag='Source data poor (user); crown kept flagged' if tid == 'tree_033' else ''))
with (batch / 'agreed_crown_bases.csv').open('x', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
(batch / 'batch_config.json').write_text(json.dumps(dict(batch=str(batch), proposal=str(PROPOSAL), user_choices=USER_CHOICES,
    method='ITSMe classify_crown_pc crown points (saved, unchanged run) with Z >= agreed base; projected_area_pc concavity=3; '
           'crown_convex_hull and 0.5/1/2 m slab sensitivity as in the 20-tree notebook.'), indent=2), encoding='utf-8')
print(batch)
