"""Run the crown-volume notebook on a versioned 20-tree selection; retain partial scientific failures."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import time

import nbformat
from nbclient import NotebookClient

ap = argparse.ArgumentParser()
ap.add_argument('config', type=Path)
ap.add_argument('--workers', type=int, default=2)
ap.add_argument('--retry-input-errors', action='store_true', help='Preserve and rerun attempts affected by the corrected numeric manifest formatting.')
a = ap.parse_args()
config = json.loads(a.config.read_text())
batch = Path(config['batch'])
root = Path(config['project_root'])
mp = root / 'measurement_pipeline'
source = mp / 'notebooks/ITSMe_HEIGHT_DBH_CROWN_VOLUME.ipynb'
os.environ['INFO6003_PROJECT_ROOT'] = str(root)
(batch / 'executed_notebooks').mkdir(exist_ok=True)
(batch / 'tree_logs').mkdir(exist_ok=True)

def readrows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

manifest = {r['stable_tree_id']: r for r in readrows(mp / 'environment' / config['manifest_name'])}

QC_CODE = r'''
# Diagnostic sensitivity, not a replacement crown-volume estimate or an accuracy test.
# Convex envelopes fitted separately inside 0.5, 1 and 2 m vertical slabs bridge fewer inter-layer gaps.
# Values depend on slab thickness and may miss volume between sparse observations.
slab_rows <- list()
if (!is.null(crown1) && !is.null(crown_volume)) {
  for (thickness in c(0.5, 1, 2)) {
    bins <- floor(crown1$Z / thickness)
    vol <- 0; sparse <- 0L; failures <- 0L
    all_bins <- seq(min(bins), max(bins))
    for (b in all_bins) {
      p <- crown1[bins == b, c("X", "Y", "Z")]
      if (nrow(p) < 4) { sparse <- sparse + 1L; next }
      h <- tryCatch(crown_convex_hull(p), error=function(e) NULL)
      if (is.null(h)) failures <- failures + 1L else vol <- vol + h$volume_m3
    }
    slab_rows[[length(slab_rows)+1L]] <- data.frame(thickness_m=thickness,
      sum_separate_slab_hulls_m3=vol, total_slabs=length(all_bins), sparse_or_empty_slabs=sparse,
      degenerate_slabs=failures, full_envelope_to_slab_ratio=if (vol > 0) crown_volume$volume_m3 / vol else NA_real_)
  }
  write.csv(do.call(rbind, slab_rows), file.path(RUN_DIR, "crown_volume_slab_sensitivity.csv"), row.names=FALSE)
}
ratio <- if (length(slab_rows)) slab_rows[[2]]$full_envelope_to_slab_ratio else NA_real_
quality <- data.frame(
  stable_tree_id=TREE_ID,
  crown_min_z_m=if (is.null(crown1)) NA_real_ else min(crown1$Z),
  crown_max_z_m=if (is.null(crown1)) NA_real_ else max(crown1$Z),
  crown_vertical_extent_m=if (is.null(crown1)) NA_real_ else diff(range(crown1$Z)),
  full_envelope_to_1m_slab_ratio=ratio,
  gap_bridging_screen=if (!is.finite(ratio)) "UNAVAILABLE" else if (ratio > 2) "STRONG_SENSITIVITY_REVIEW" else "NO_LARGE_RATIO_NOT_VALIDATION",
  dbh13_points=scalar(lean_result, "dbh13_points"),
  dbh13_arc=scalar(lean_result, "dbh13_arc"),
  dbh13_rmse_m=sqrt(scalar(lean_result, "dbh13_R2")),
  axis_lean_degrees=scalar(lean_result, "axis_lean_deg"),
  accepted_dbh_slices=scalar(lean_result, "accepted_slices"),
  axis_offset_at_foot_m=scalar(lean_result, "axis_offset_at_foot_m"))
write.csv(quality, file.path(RUN_DIR, "batch_quality_diagnostics.csv"), row.names=FALSE)
'''

def run(tid):
    record_path = batch / 'tree_logs' / f'{tid}.json'
    if record_path.exists():
        previous = json.loads(record_path.read_text())
        if previous.get('execution_error') is None and previous.get('metrics'):
            print('RESUME', tid, flush=True)
            return previous
        raise RuntimeError(f'{tid} already has a failed attempt; preserve it and use a new batch for reruns.')
    before = set((mp / 'results').glob(f'ITSMe_metrics_{tid}_*'))
    n = nbformat.read(source, as_version=4)
    replacements = {
        'TREE_ID <- "tree_146"': 'TREE_ID <- ' + json.dumps(tid),
        '"home_selection_manifest_CURRENT_20261023.csv"': json.dumps(config['manifest_name']),
        '"human_review_template_CURRENT_20261023.csv"': json.dumps(config['review_name']),
        'file.path(WORK, "checkpoints", paste0(tid, "_height.json"))':
            f'file.path(ROOT, {json.dumps(config["axis_relative"])}, paste0(tid, "_height.json"))',
        'file.path(WORK, "checkpoints", paste0(TREE_ID, "_height.json"))':
            f'file.path(ROOT, {json.dumps(config["axis_relative"])}, paste0(TREE_ID, "_height.json"))',
    }
    used = set()
    for cell in n.cells:
        if cell.cell_type == 'code':
            for old, new in replacements.items():
                if old in cell.source:
                    cell.source = cell.source.replace(old, new)
                    used.add(old)
    assert used == set(replacements), set(replacements)-used
    n.cells.append(nbformat.v4.new_code_cell(QC_CODE))
    log_path = batch / 'tree_logs' / f'{tid}_cells.txt'
    def started(cell, cell_index):
        with log_path.open('a', encoding='utf-8') as f:
            f.write(f'{time.strftime("%H:%M:%S")} cell {cell_index+1}/{len(n.cells)}\n')
    print('START', tid, manifest[tid]['selection_group'], manifest[tid]['rank'], flush=True)
    start = time.monotonic()
    error = None
    try:
        NotebookClient(n, kernel_name='info6003-ir', timeout=1800, on_cell_start=started,
                       resources={'metadata': {'path': str(source.parent)}}).execute()
    except Exception as exc:
        error = repr(exc)
    executed = batch / 'executed_notebooks' / f'{tid}_EXECUTED.ipynb'
    nbformat.write(n, executed)
    created = set((mp / 'results').glob(f'ITSMe_metrics_{tid}_*'))-before
    directory = created.pop() if len(created) == 1 else None
    metrics = readrows(directory / 'tree_metrics.csv')[0] if directory and (directory / 'tree_metrics.csv').exists() else {}
    qc = readrows(directory / 'batch_quality_diagnostics.csv')[0] if directory and (directory / 'batch_quality_diagnostics.csv').exists() else {}
    record = dict(tree=tid, group=manifest[tid]['selection_group'], rank=manifest[tid]['rank'],
                  seconds=round(time.monotonic()-start, 2), execution_error=error,
                  executed_notebook=str(executed), run_dir=str(directory) if directory else None,
                  source_notebook_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), metrics=metrics, qc=qc)
    record_path.write_text(json.dumps(record, indent=2), encoding='utf-8')
    print('DONE', tid, f'{record["seconds"]}s', 'ERROR' if error else 'executed',
          'DBH', metrics.get('dbh_cm'), 'volume', metrics.get('crown_volume_m3'),
          'gap ratio', qc.get('full_envelope_to_1m_slab_ratio'), flush=True)
    return record

trees_to_run = config['trees']
if a.retry_input_errors:
    archive = batch / 'earlier_attempts_before_numeric_fix'
    archive.mkdir(exist_ok=False)
    for filename in ['all_runs.json', 'all_20_tree_results.csv', 'progress.json']:
        if (batch / filename).exists():
            shutil.copy2(batch / filename, archive / filename)
    trees_to_run = []
    for tid in config['trees']:
        record_path = batch / 'tree_logs' / f'{tid}.json'
        prior = json.loads(record_path.read_text())
        if prior.get('metrics', {}).get('dbh_status') == 'non-numeric argument to binary operator':
            trees_to_run.append(tid)
            shutil.move(str(record_path), str(archive / record_path.name))
            executed = batch / 'executed_notebooks' / f'{tid}_EXECUTED.ipynb'
            shutil.move(str(executed), str(archive / executed.name))
            cells = batch / 'tree_logs' / f'{tid}_cells.txt'
            shutil.move(str(cells), str(archive / cells.name))
    print('RERUN AFTER INPUT FIX', trees_to_run, flush=True)

records = []
with ThreadPoolExecutor(max_workers=max(1, min(2, a.workers))) as pool:
    futures = {pool.submit(run, tid): tid for tid in trees_to_run}
    for future in as_completed(futures):
        records.append(future.result())
        (batch / 'progress.json').write_text(json.dumps(records, indent=2), encoding='utf-8')

records = [json.loads((batch / 'tree_logs' / f'{tid}.json').read_text()) for tid in config['trees']]
combined = []
for r in records:
    combined.append(dict(selection_group=r['group'], group_rank=r['rank'],
                         stable_tree_id=r['tree'], seconds=r['seconds'], execution_error=r['execution_error'] or '',
                         **{k:v for k,v in r['metrics'].items() if k != 'stable_tree_id'},
                         **{k:v for k,v in r['qc'].items() if k != 'stable_tree_id'}, run_directory=r['run_dir']))
fields = list(dict.fromkeys(k for row in combined for k in row))
with (batch / 'all_20_tree_results.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(combined)

before = readrows(batch / 'protected_inputs_before.csv')
after = []
for r in before:
    actual = hashlib.sha256((root / 'CloudCompare_review_v2' / r['file']).read_bytes()).hexdigest()
    after.append(dict(file=r['file'], before=r['sha256'], after=actual, unchanged=actual == r['sha256']))
assert all(r['unchanged'] for r in after)
(batch / 'protected_inputs_after.json').write_text(json.dumps(after, indent=2), encoding='utf-8')
(batch / 'all_runs.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
print('COMPLETE', batch, 'all 163 protected files unchanged', flush=True)
