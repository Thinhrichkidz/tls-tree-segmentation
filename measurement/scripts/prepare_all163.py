"""Prepare current, hash-checked local inputs and per-tree geometry for the all-163 batch (read-only on sources).

Usage: python -I prepare_all163.py --out <output folder> [--workers N] [--trees tree_001,tree_002]
Writes <out>/per_tree/tree_NNN/{tree_NNN_local_xyz.txt, coordinate_transform.json, prep.json} and
<out>/manifests/all163_manifest.csv. A tree whose prep.json already matches its source hash and settings is reused.
"""
import argparse
import csv
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import all163_common as C
import numpy as np

MP, ROOT = C.MP, C.ROOT
PREP_VERSION = 'all163-prep-v2'  # v2: user crown-base choices for 55 more trees
SNAPSHOT = ROOT / 'session3_codex_20261023/state/CloudCompare_review_v2_CURRENT.csv'
HEIGHTS = MP / 'results/all_tree_preliminary_heights.csv'
CORRECTED_MANIFEST = MP / 'environment/CORRECTED_FOUR_TREE_RERUN_20261023_190059_manifest.csv'
CORRECTED_AXIS = MP / 'results/CORRECTED_FOUR_TREE_RERUN_20261023_190059/axis'
TOP20_MANIFEST = MP / 'environment/CROWN_VOLUME_TOP20_20261023_164430_manifest.csv'
TOP20_AXIS = MP / 'results/CROWN_VOLUME_TOP20_20261023_164430/axis'
AGREED_BASES = MP / 'results/CROWN_BASE_RERUN_20261023_191046/agreed_crown_bases.csv'
USER_CHOICES = MP / 'results/CROWN_BASE_REVIEW_ALL163_20261023_194703/user_crown_choices.csv'  # 55 trees, user 23 Oct 2026

_terrain = None


def _init():
    global _terrain
    from matplotlib.tri import Triangulation, LinearTriInterpolator
    mesh = np.load(ROOT / 'verification_output/terrain_arrays.npz')
    mv, mf = mesh['vertices'], mesh['faces']
    offset = mv[:, :2].min(0)
    _terrain = (LinearTriInterpolator(Triangulation(mv[:, 0] - offset[0], mv[:, 1] - offset[1], mf), mv[:, 2]), offset)


def prepare(spec):
    t0 = time.time()
    tid, out = spec['tree'], Path(spec['dir'])
    out.mkdir(parents=True, exist_ok=True)
    prep_path = out / 'prep.json'
    if prep_path.exists():
        old = json.loads(prep_path.read_text())
        if old.get('review_sha256') == spec['review_sha256'] and old.get('settings') == spec['settings'] and \
                Path(old['local_xyz_path']).exists() and C.sha(old['local_xyz_path']) == old['local_xyz_sha256']:
            return dict(old, reused=True)
    src = ROOT / 'CloudCompare_review_v2' / spec['review_ply_filename']
    assert C.sha(src) == spec['review_sha256'], 'source hash changed during preparation'
    p = C.points(src)
    t = np.array(spec['translation'], float)
    local = p - t
    txt = out / f'{tid}_local_xyz.txt'
    np.savetxt(txt, local, fmt='%.12f', header='X Y Z', comments='')
    back = np.loadtxt(txt, skiprows=1)
    err = float(np.abs(back + t - p).max())
    assert back.shape == p.shape and err < 1e-8
    (out / 'coordinate_transform.json').write_text(json.dumps(dict(
        stable_tree_id=tid, source_file=src.relative_to(ROOT).as_posix(), source_sha256=spec['review_sha256'],
        point_count=len(p), absolute_to_local_subtract_xyz=t.tolist(), inverse='absolute = local + subtract_xyz',
        txt_max_roundtrip_error_m=err, translation_source=spec['translation_source'],
        operation='Translation only; no resampling or point changes.'), indent=2), encoding='utf-8')
    top = C.supported_top(p)
    rec = dict(tree=tid, review_sha256=spec['review_sha256'], settings=spec['settings'], point_count=len(p),
               local_xyz_path=str(txt), local_xyz_sha256=C.sha(txt), translation=t.tolist(),
               translation_source=spec['translation_source'], ground_source=spec['ground_source'],
               supported_height_m=float(p[top, 2] - t[2]), full_cloud_height_m=float(p[:, 2].max() - t[2]),
               height_p99_m=float(np.percentile(local[:, 2], 99)),
               lowest_point_above_ground_m=float(local[:, 2].min()))
    # Stem axis: saved (hash-matched) or refitted with the original helper.
    axis = spec.get('axis')
    if axis is None:
        try:
            if _terrain is None:
                _init()
            fit = C.refresh_axis(tid, p, t[2], t[:2], *_terrain)
            axis = dict(stem_axis=fit['stem_axis'], source='refitted on current points (original low-stem helper)',
                        axis_fit_rmse_m=fit['axis_fit_rmse_m'], offset_from_foot_m=fit['offset_from_inherited_foot_m'])
        except AssertionError as e:
            rec['axis_failure'] = str(e)
    if axis is not None:
        o, s = C.local_axis(axis['stem_axis'], t)
        rec.update(axis_o=o.tolist(), axis_s=s.tolist(), axis_source=axis['source'],
                   axis_lean_deg=float(np.degrees(np.arctan(np.hypot(*s)))),
                   axis_fit_rmse_m=axis.get('axis_fit_rmse_m'), axis_offset_from_foot_m=float(np.hypot(*o)))
    else:
        o = s = None
    # Crown base: user-agreed value for the 20 test trees, otherwise the agreed rule.
    rule = C.crown_base_rule(local)
    rec.update(rule_crown_base_m=rule['base'], rule_first_branch_m=rule['first'], rule_crowned_runs_m=rule['runs'],
               rule_trunk_r95_m=rule['trunk_r95'], rule_threshold_m=rule['threshold'], rule_failure=rule['reason'])
    if spec.get('user_no_crown'):
        rec.update(crown_base_m=None, crown_base_source=None, crown_base_failure=spec['user_no_crown'])
    elif spec.get('agreed_base') is not None:
        rec.update(crown_base_m=spec['agreed_base'], crown_base_source=spec['agreed_base_source'])
    else:
        rec.update(crown_base_m=rule['base'], crown_base_source='continuous-crown rule (agreed 23 Oct 2026), automatic' if rule['base'] is not None else None)
    rec.update(C.stem_indicators(local, o, s, rec['crown_base_m']))
    # Stem position (global): axis centre at 1.3 m, else stem foot.
    if o is not None:
        rec.update(stem_xy=(o + s * 1.3 + t[:2]).tolist(), stem_xy_source='stem axis at 1.3 m')
    else:
        rec.update(stem_xy=t[:2].tolist(), stem_xy_source='stem base (foot XY); no stem axis')
    x0, y0, x1, y1 = spec['roi']
    sx, sy = rec['stem_xy']
    rec['dist_to_roi_edge_m'] = float(min(sx - x0, x1 - sx, sy - y0, y1 - sy))
    if rec['crown_base_m'] is not None:
        cp = p[local[:, 2] >= rec['crown_base_m']]
        d = np.minimum.reduce([cp[:, 0] - x0, x1 - cp[:, 0], cp[:, 1] - y0, y1 - cp[:, 1]]) if len(cp) else np.array([np.inf])
        rec['crown_min_dist_to_roi_edge_m'] = float(d.min())
        rec['flag_crown_touches_edge'] = bool(d.min() <= 0.10)
    else:
        rec['crown_min_dist_to_roi_edge_m'] = None
        rec['flag_crown_touches_edge'] = None
    rec.update({k: spec[k] for k in ('dbh_outline_filter', 'dbh_report_mode')})
    rec['prep_seconds'] = time.time() - t0
    prep_path.write_text(json.dumps(rec, indent=1, default=float), encoding='utf-8')
    return dict(rec, reused=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--workers', type=int, default=0)
    ap.add_argument('--trees', default='')
    a = ap.parse_args()
    out = Path(a.out)
    (out / 'manifests').mkdir(parents=True, exist_ok=True)
    (out / 'logs').mkdir(exist_ok=True)
    t0 = time.time()
    snap = C.rows(SNAPSHOT)
    with ThreadPoolExecutor(16) as ex:
        current = list(ex.map(lambda r: C.sha(ROOT / 'CloudCompare_review_v2' / r['file']), snap))
    changed = [r['file'] for r, h in zip(snap, current) if h != r['sha256']]
    assert len(list((ROOT / 'CloudCompare_review_v2').glob('*.ply'))) == len(snap) == 163
    (out / 'manifests/source_state.json').write_text(json.dumps(dict(
        snapshot=str(SNAPSHOT.relative_to(ROOT)), files=len(snap), changed_since_snapshot=changed,
        checked_at=time.strftime('%Y-%m-%dT%H:%M:%S')), indent=1), encoding='utf-8')
    assert not changed, f'Source clouds changed since the Session 3 snapshot: {changed}. Capture a new baseline first.'
    current_hash = {r['file']: r['sha256'] for r in snap}
    roi_path = out / 'manifests/roi.json'
    if not roi_path.exists():
        raw = next((ROOT / 'raw').glob('*.ply'))
        v = C.PlyData.read(str(raw), mmap='r')['vertex'].data
        x, y = np.asarray(v['x']), np.asarray(v['y'])
        roi_path.write_text(json.dumps(dict(roi_id='WSL_ML2A_crop_55x55', source=raw.relative_to(ROOT).as_posix(),
            bbox_xy=[float(x.min()), float(y.min()), float(x.max()), float(y.max())],
            assumption='ROI boundary = axis-aligned XY bounding box of the raw cropped cloud.'), indent=1), encoding='utf-8')
    roi = json.loads(roi_path.read_text())['bbox_xy']
    heights = {r['stable_tree_id']: r for r in C.rows(HEIGHTS)}
    corrected = {r['stable_tree_id']: r for r in C.rows(CORRECTED_MANIFEST)}
    top20 = {r['stable_tree_id']: r for r in C.rows(TOP20_MANIFEST)}
    agreed = {r['tree']: r for r in C.rows(AGREED_BASES)}
    choices = {r['tree']: r for r in C.rows(USER_CHOICES)}
    assert not set(choices) & set(agreed)
    wanted = [t for t in a.trees.split(',') if t] or sorted(heights)
    settings = dict(prep_version=PREP_VERSION, crown_rule=[C.DZ, C.CROWN_FRACTION, C.FACTOR, C.CONTINUITY],
                    circle_source_sha256=C.CIRCLE_SOURCE_SHA256, roi=roi, user_choices_sha256=C.sha(USER_CHOICES))
    specs = []
    for tid in wanted:
        h = heights[tid]
        cur = current_hash[h['review_ply_filename']]
        spec = dict(tree=tid, dir=str(out / 'per_tree' / tid), review_ply_filename=h['review_ply_filename'], review_sha256=cur,
                    settings=settings, roi=roi, dbh_outline_filter=False, dbh_report_mode='STANDARD', axis=None)
        robust = h['foot_method'].startswith('ROBUST')
        if tid in corrected:
            m = corrected[tid]
            assert m['review_sha256'] == cur
            spec['translation'] = [float(m['translation_x_m']), float(m['translation_y_m']), float(m['translation_z_m'])]
            spec['translation_source'] = 'CORRECTED_FOUR_TREE_RERUN_20261023_190059 manifest (user decisions 23 Oct 2026)'
            spec['dbh_outline_filter'] = m['dbh_outline_filter'] == 'TRUE'
            spec['dbh_report_mode'] = m['dbh_report_mode']
            ck = json.loads((CORRECTED_AXIS / f'{tid}_height.json').read_text())
            spec['axis'] = dict(stem_axis=ck['stem_axis'], source='CORRECTED_FOUR_TREE_RERUN axis (' + ck['interpretation'][:80] + ')',
                                axis_fit_rmse_m=ck.get('axis_fit_rmse_m'))
            spec['ground_source'] = ('terrain_mesh at corrected stem base (user-agreed)' if tid in ('tree_103', 'tree_108')
                                     else 'terrain_mesh at stem foot (actual triangle)')
        else:
            if tid == 'tree_102':
                m = top20[tid]
                assert m['review_sha256'] == cur
                spec['translation'] = [float(m['translation_x_m']), float(m['translation_y_m']), float(m['translation_z_m'])]
                spec['translation_source'] = 'CROWN_VOLUME_TOP20 manifest (tree_102 v3 inputs)'
                ck = json.loads((TOP20_AXIS / f'{tid}_height.json').read_text())
                if ck['row']['review_sha256'] == cur:
                    spec['axis'] = dict(stem_axis=ck['stem_axis'], source='CROWN_VOLUME_TOP20 axis (fresh current-point fit)',
                                        axis_fit_rmse_m=ck.get('axis_fit_rmse_m'))
            else:
                spec['translation'] = [float(h['stem_foot_x_m']), float(h['stem_foot_y_m']), float(h['estimated_local_ground_z_m'])]
                spec['translation_source'] = 'all_tree_preliminary_heights.csv stem foot and mesh ground' + (
                    '' if h['review_sha256'] == cur else ' (inherited; cloud edited later)')
                ck = json.loads((MP / 'checkpoints' / f'{tid}_height.json').read_text())
                if ck.get('stem_axis') and ck['row']['review_sha256'] == cur:
                    spec['axis'] = dict(stem_axis=ck['stem_axis'], source='saved height checkpoint (hash-matched)',
                                        axis_fit_rmse_m=float(h['stem_axis_fit_rmse_m']) if h['stem_axis_fit_rmse_m'] else None)
            spec['ground_source'] = ('terrain_mesh at stem foot (actual triangle)' if robust
                                     else 'terrain_mesh at lowest-observation XY (fallback foot; uncertain)')
        if tid in agreed:
            spec['agreed_base'] = float(agreed[tid]['crown_base_m'])
            spec['agreed_base_source'] = agreed[tid]['base_source']
        if tid in choices:
            c = choices[tid]
            if c['crown_base_m']:
                spec['agreed_base'] = float(c['crown_base_m'])
                spec['agreed_base_source'] = f"user choice 23 Oct 2026 (all-163 crown review, option {c['choice']})"
            else:
                spec['user_no_crown'] = 'user decision 23 Oct 2026: no convincing live crown (bare or dead-looking stem)'
        specs.append(spec)
    workers = a.workers or max(1, min(48, os.cpu_count() or 1))
    specs.sort(key=lambda s: -int(heights[s['tree']]['point_count']))  # big trees first for load balance
    results, failures = [], []
    with ProcessPoolExecutor(workers, initializer=_init) as ex:
        futs = {s['tree']: ex.submit(prepare, s) for s in specs}
        for tid, f in futs.items():
            try:
                results.append(f.result())
            except Exception as e:
                failures.append(dict(tree=tid, error=repr(e)))
    results.sort(key=lambda r: r['tree'])
    keys = ['tree', 'review_sha256', 'point_count', 'local_xyz_path', 'local_xyz_sha256', 'translation_source', 'ground_source',
            'axis_source', 'axis_failure', 'crown_base_m', 'crown_base_source', 'dbh_outline_filter', 'dbh_report_mode', 'reused']
    with (out / 'manifests/all163_manifest.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        w.writerows(results)
    log = dict(trees=len(specs), prepared=len(results), reused=sum(r['reused'] for r in results), failures=failures,
               workers=workers, seconds=time.time() - t0)
    (out / 'logs/prepare_log.json').write_text(json.dumps(log, indent=1), encoding='utf-8')
    print(json.dumps(log, indent=1))
    assert not failures


if __name__ == '__main__':
    main()
