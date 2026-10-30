"""Height refinements for the all-163 batch (28 Oct 2026). Read-only on source clouds; writes per_tree/<tree>/height_refine.json.

Usage: python -I height_refine_all163.py --out <all-163 output folder>   (after the R measurement step, before post-processing)

1. Top-edge check. The inherited top rule fails a tree when any of its points is within 0.75 m of the terrain-mesh edge,
   even when the tip itself is far inside. The mesh edge also runs round holes in the terrain inside the plot (unscanned
   ground), which cannot cut a tree. A tree can only be cut at the crop boundary, a rectangle tilted ~12.6 deg (crop_rectangle in
   manifests/roi.json; not the axis-aligned bounding box), so here, on the current points,
   we record the highest point within 0.75 m of the ROI box and how far it lies below the supported tip (v2, 28 Oct 2026).
   Mesh-edge values are still recorded for reference.
1b. Connectivity. The inherited largest-component fraction predates the manual cleaning; it is recomputed on the current
   points with the same method as segmentation_v2_analysis/scripts/checkpoint1_audit.py (voxel = clip(4 x median spacing,
   0.10, 0.25) m, 26-connected voxels, largest component points / all points).
2. Trunk-centre foot. For trees whose stem foot is the lowest observation (fallback), candidate feet under the trunk are
   computed from (a) the stem axis at the local ground level, (b) the v4 DBH circle centre, (c) the v4b RANSAC circle centre
   (b and c only without a stem axis: the fit is then in the unrotated local frame, vertical stem assumed). For each, the
   mesh ground Z and the inherited ground-reliability rule (copied from preliminary_heights.py) are evaluated.
The post-processing decides which candidate may be used (only a released DBH fit or a stem axis).
"""
import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import all163_common as C
import numpy as np
from matplotlib.tri import Triangulation, LinearTriInterpolator
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

MP, ROOT = C.MP, C.ROOT
EDGE_NEAR_M = 0.75   # same distance as the inherited rule (mesh_boundary_min_sample_distance_m >= 0.75)


def largest_component_fraction(p, seed):
    """Same as checkpoint1_audit.geometry(): voxel connectivity at clip(4 x spacing, 0.10, 0.25) m, 26-neighbourhood."""
    kt = cKDTree(p)
    ix = np.random.default_rng(seed).choice(len(p), min(4096, len(p)), replace=False)
    nn = kt.query(p[ix], k=2, workers=-1)[0][:, 1]
    spacing = float(np.median(nn[nn > 0])) if (nn > 0).any() else .03
    voxel = float(np.clip(4 * spacing, .10, .25))
    vox, vi = np.unique(np.floor((p - p.min(axis=0)) / voxel).astype(np.int32), axis=0, return_inverse=True)
    pairs = cKDTree(vox).query_pairs(np.sqrt(3) + 1e-8, output_type='ndarray')
    nc, lab = connected_components(coo_matrix((np.ones(len(pairs), dtype=np.uint8), (pairs[:, 0], pairs[:, 1])),
                                              shape=(len(vox), len(vox))).tocsr(), directed=False)
    sizes = np.bincount(lab[np.ravel(vi)], minlength=nc)
    return float(sizes.max() / len(p)), voxel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    out = Path(ap.parse_args().out)
    mesh = np.load(ROOT / 'verification_output/terrain_arrays.npz')
    mv, mf = mesh['vertices'], mesh['faces']
    offset = mv[:, :2].min(0)
    tri = Triangulation(mv[:, 0] - offset[0], mv[:, 1] - offset[1], mf)
    finder, interp = tri.get_trifinder(), LinearTriInterpolator(tri, mv[:, 2])
    raw = C.PlyData.read(str(next((ROOT / 'raw').glob('*.ply'))), mmap='r')['vertex'].data
    gp = np.column_stack([raw[k] for k in ('x', 'y', 'z')])[raw['scalar_Classification'] == 2].astype('f8')
    gt = cKDTree(gp[:, :2])
    bt = cKDTree(mv[np.unique(np.load(ROOT / 'verification_output/mesh_boundary_edges.npy')), :2])
    heights = {r['stable_tree_id']: r for r in C.rows(MP / 'results/all_tree_preliminary_heights.csv')}
    rect = json.loads((out / 'manifests/roi.json').read_text())['crop_rectangle']   # true tilted crop footprint

    def ground_test(foot):
        """Inherited ground-reliability rule (preliminary_heights.py), evaluated at a new foot XY (global)."""
        gz = float(np.ma.filled(interp(foot[0] - offset[0], foot[1] - offset[1]), np.nan))
        gz = gz if np.isfinite(gz) else None
        t = int(finder(foot[0] - offset[0], foot[1] - offset[1]))
        edge_max = float(max(np.linalg.norm(mv[mf[t], :2][i] - mv[mf[t], :2][(i + 1) % 3]) for i in range(3))) if t >= 0 else None
        gg = gp[np.array(gt.query_ball_point(foot, 1.0), dtype=int)]
        gg = gg[np.linalg.norm(gg[:, :2] - foot, axis=1) >= .30]
        plane_z = plane_rmse = None
        plane_n, sectors = len(gg), 0
        if len(gg) >= 20:
            delta = gg[:, :2] - foot
            A = np.c_[np.ones(len(gg)), delta]
            fit = least_squares(lambda c: A @ c - gg[:, 2], np.linalg.lstsq(A, gg[:, 2], rcond=None)[0], loss='soft_l1', f_scale=.04)
            ok = np.abs(A @ fit.x - gg[:, 2]) < .10
            if ok.sum() >= 20:
                co = np.linalg.lstsq(A[ok], gg[ok, 2], rcond=None)[0]
                plane_z, plane_rmse, plane_n = float(co[0]), float(np.sqrt(np.mean((A[ok] @ co - gg[ok, 2]) ** 2))), int(ok.sum())
                ang = np.arctan2(delta[ok, 1], delta[ok, 0])
                sectors = len(np.unique(np.floor((ang + np.pi) / (np.pi / 4)).astype(int)))
        dis = None if plane_z is None or gz is None else plane_z - gz
        ground_ok = bool(gz is not None and plane_z is not None and abs(dis) <= .15 and plane_rmse <= .07 and plane_n >= 40
                         and sectors >= 5 and edge_max is not None and edge_max <= 2.)
        return dict(ground_z=gz, ground_ok=ground_ok, plane_minus_mesh_m=dis, plane_rmse_m=plane_rmse, plane_inlier_n=plane_n,
                    sectors_of_8=sectors, foot_triangle_max_edge_m=edge_max)

    rows = []
    for m in C.rows(out / 'manifests/all163_manifest.csv'):
        tid = m['tree']
        d = out / 'per_tree' / tid
        prep = json.loads((d / 'prep.json').read_text())
        res = json.loads((d / 'result.json').read_text())
        p = C.points(ROOT / 'CloudCompare_review_v2' / heights[tid]['review_ply_filename'])
        t = np.array(prep['translation'], float)
        # 1. top-edge check on the current points
        top = C.supported_top(p)
        tip = p[top]
        dist = bt.query(p[:, :2], workers=-1)[0]
        near = dist < EDGE_NEAR_M
        rec = dict(tree=tid, review_sha256=prep['review_sha256'], tip_local_z_m=float(tip[2] - t[2]),
                   tip_to_mesh_edge_m=float(bt.query(tip[:2])[0]), top_drop_m=float(p[:, 2].max() - tip[2]),
                   min_dist_to_mesh_edge_m=float(dist.min()), points_near_mesh_edge=int(near.sum()),
                   edge_near_max_local_z_m=float(p[near, 2].max() - t[2]) if near.any() else None)
        rec['edge_near_gap_below_tip_m'] = None if rec['edge_near_max_local_z_m'] is None else rec['tip_local_z_m'] - rec['edge_near_max_local_z_m']
        # crop boundary (ROI box): the only place a tree can be cut
        droi = C.dist_to_crop_edge(p, rect)
        nroi = droi < EDGE_NEAR_M
        rec.update(tip_to_roi_edge_m=float(C.dist_to_crop_edge(tip, rect)[0]), min_dist_to_roi_edge_m=float(droi.min()),
                   points_near_roi_edge=int(nroi.sum()), roi_near_max_local_z_m=float(p[nroi, 2].max() - t[2]) if nroi.any() else None)
        rec['roi_near_gap_below_tip_m'] = None if rec['roi_near_max_local_z_m'] is None else rec['tip_local_z_m'] - rec['roi_near_max_local_z_m']
        rec['largest_component_fraction'], rec['connectivity_voxel_m'] = largest_component_fraction(p, 6003 + int(tid[5:]))
        # 2. trunk-centre foot candidates for fallback-foot trees
        if not heights[tid]['foot_method'].startswith('ROBUST'):
            cands = {}
            if prep.get('axis_o') is not None:
                cands['stem axis'] = np.array(prep['axis_o'], float)
            else:
                if res.get('dbh_v4_cx') is not None:
                    cands['v4 DBH circle centre'] = np.array([res['dbh_v4_cx'], res['dbh_v4_cy']], float)
                if res.get('dbh_v4b_ransac_cx') is not None:
                    cands['v4b RANSAC circle centre'] = np.array([res['dbh_v4b_ransac_cx'], res['dbh_v4b_ransac_cy']], float)
            rec['current_foot'] = dict(xy=t[:2].tolist(), ground_z=float(t[2]), **{k: v for k, v in ground_test(t[:2]).items() if k != 'ground_z'})
            rec['foot_candidates'] = {}
            for name, local_xy in cands.items():
                g = ground_test(local_xy + t[:2])
                g.update(xy=(local_xy + t[:2]).tolist(), offset_from_current_foot_m=float(np.hypot(*local_xy)),
                         dz_m=None if g['ground_z'] is None else g['ground_z'] - float(t[2]))
                rec['foot_candidates'][name] = g
        (d / 'height_refine.json').write_text(json.dumps(rec, indent=1), encoding='utf-8')
        rows.append(rec)
    keys = ['tree', 'tip_local_z_m', 'top_drop_m', 'tip_to_roi_edge_m', 'min_dist_to_roi_edge_m', 'points_near_roi_edge',
            'roi_near_max_local_z_m', 'roi_near_gap_below_tip_m', 'largest_component_fraction', 'connectivity_voxel_m',
            'tip_to_mesh_edge_m', 'min_dist_to_mesh_edge_m', 'points_near_mesh_edge', 'edge_near_max_local_z_m', 'edge_near_gap_below_tip_m']
    (out / 'results').mkdir(exist_ok=True)
    with (out / 'results/height_refine.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=keys + ['foot_candidates'], extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(dict(r, foot_candidates=json.dumps(r.get('foot_candidates', {}))))
    print(json.dumps(dict(trees=len(rows), fallback_trees=sum('foot_candidates' in r for r in rows),
                          with_candidates=sum(bool(r.get('foot_candidates')) for r in rows))))


if __name__ == '__main__':
    main()
