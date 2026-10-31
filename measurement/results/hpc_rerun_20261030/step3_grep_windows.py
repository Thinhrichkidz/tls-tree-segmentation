"""Step 3 (read only): grep measurement_pipeline/scripts/ (and the v5 template notebook) for Windows-only items.

Run: python -I -B hpc_run_20261030_1715/step3_grep_windows.py
Writes step3_windows_hits.csv into this script's own folder.
"""
import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MP = HERE.parent / 'measurement_pipeline'
CHAIN = {'run_all163_notebook.py', 'all163_env.py', 'prepare_all163.py', 'all163_common.py', 'all163_tree_worker.R',
         'crown_volume_metrics.R', 'dbh_v4.R', 'height_refine_all163.py', 'all163_postprocess.py', 'xlsx_styled.py',
         'xlsx_writer.py', 'verify_all163_independent.py', 'sensitivity_all163.R',
         'ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME_v5.ipynb'}
LATER = {'holdout_dbh_v4.R', 'run_dbh_v4.R', 'run_dbh_v4b.R'}  # likely reused in step 8
PATTERNS = {
    'drive_letter_path': r'\b[A-Za-z]:[/\\]',
    'unc_path': r'\\\\\\\\[A-Za-z]|\\\\[a-z]+\.[a-z]',
    'exe_call': r'\.exe\b',
    'deps_sys_path': r'_deps',
    'powershell_or_cmd': r'\bpowershell\b|\bcmd(\.exe)?\s*/c\b|\.ps1\b|\.cmd\b|\.bat\b',
    'venv_Scripts_dir': r'[/\\"\']Scripts[/\\"\']',
    'program_files': r'Program Files',
    'backslash_path_literal': r'["\'][^"\'\n]*[A-Za-z0-9_]\\\\?[A-Za-z0-9_]+\\\\?[A-Za-z0-9_.]+["\']',
}
files = sorted(p for p in (MP / 'scripts').iterdir() if p.is_file())
files.append(MP / 'notebooks' / 'ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME_v5.ipynb')
rows = []
for p in files:
    try:
        lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError as e:
        rows.append([p.name, 'READ_ERROR', '', '', str(e)])
        continue
    role = 'v6_chain' if p.name in CHAIN else ('later_steps' if p.name in LATER else 'other')
    for i, line in enumerate(lines, 1):
        for name, pat in PATTERNS.items():
            if name == 'backslash_path_literal' and ('\\n' in line or '\\t' in line or '\\d' in line or '\\s' in line):
                continue
            if re.search(pat, line):
                rows.append([p.name, role, name, i, line.strip()[:200]])
with open(HERE / 'step3_windows_hits.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['file', 'role', 'pattern', 'line', 'text'])
    w.writerows(rows)
summary = {}
for r in rows:
    summary.setdefault(r[1], {}).setdefault(r[0], set()).add(r[2])
print(json.dumps({k: {f: sorted(v) for f, v in d.items()} for k, d in summary.items()}, indent=1))
print('files scanned:', len(files), 'hits:', len(rows))
for r in rows:
    if r[1] != 'other':
        print(f'{r[0]}:{r[3]} [{r[2]}] {r[4]}')
