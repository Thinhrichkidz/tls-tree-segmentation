# Terrestrial laser scanning tree segmentation

Tree segmentation of terrestrial laser scanning (TLS) point clouds of plot **WSL_ML2A** (scan 2025-05-12, 1 cm raw resolution). The plot was cropped to 35 m x 35 m and 55 m x 55 m areas, downsampled to 2 cm and 3 cm, segmented automatically into individual trees (RayCloudTools raycloud/terrain/segmentation outputs), and the 55x55 / 3 cm segmentation was then corrected manually in CloudCompare.

This repository holds the scripts, documentation and **small samples** of each stage. The full data (about 82 GiB) is not in the repo, see [Where the full data is](#where-the-full-data-is).

**Project context.** INFO6003 Postgraduate Research Project (School of Computer, Data and Mathematical Sciences, Western Sydney University, Spring 2026) by Hoang Truong Thinh Nguyen (22083142). Supervisors: Prof. Brendan Choat (principal) and Dr. Chng Wei Lau (co-supervisor), in collaboration with Erick Calderon-Morales. The scan is of a Blue Mountains eucalypt plot, provided by the Hawkesbury Institute for the Environment (I did not collect it). The project tests a semi-automated workflow: automatic individual-tree segmentation, manual correction, and height, DBH and crown measurements under predefined quality criteria. The final report is INFO6003 Final Report v13 (submitted separately).

## Repository layout

```text
docs/             Reports (latest: INFO6003_report_v11), proposal, notes; reorganization_notes.md describes how the full data folder was reorganised
audit/            Independent audit: claim register, recomputed values, DBH re-fit and run-comparison scripts (see audit/AUDIT_REPORT.md)
scripts/
  tree_extraction.py       Step 3: transfer tree labels onto a plot cloud (see below)
  reorganize-project.ps1   Helper that reorganised / can undo the full data folder layout
samples/          Small crops and subsets of every stage (each folder has a SAMPLE_INFO.md)
  raw/                     7 m x 7 m crop of the 1 cm raw cloud
  downsampled/             Same box from the 55x55 / 3 cm cloud
  automated_segmentation/  8 per-tree clouds + metadata, small seg_vNN.ply files, leftover crop
  manual_segmentation/     Manually corrected versions of the same 8 trees
logs/             reorganization-2026-10-02.json (original to current path mapping of the full data)
environment/      requirements.txt
```

## Samples

All samples are from plot WSL_ML2A, 55x55 crop, 3 cm. Raw and downsampled samples share the bounding box x 261358 to 261365 m, y 6264492 to 6264499 m (7 m x 7 m; shrunk from 10 m x 10 m to keep the 1 cm file under 40 MB). The automated and manual tree samples are paired so that you can compare before and after correction: see [samples/manual_segmentation/SAMPLE_INFO.md](samples/manual_segmentation/SAMPLE_INFO.md). Corrected files use different IDs from the automated ones, so they were paired geometrically.

`.laz` files need `laspy` with `lazrs`; `.ply` files open in CloudCompare, MeshLab or Open3D.

## Workflow

1. Raw scan (1 cm) cropped to 35x35 and 55x55 areas, in full resolution and downsampled to 2 cm and 3 cm.
2. Automatic segmentation (RayCloudTools): raycloud, terrain mesh, segmented cloud, individual trees, branch-skeleton metadata. The tool was run from a container image; the version and parameters used for this plot were not recorded.
3. Manual correction in CloudCompare of the 55x55 / 3 cm trees (`trees/cloud_correct`). The 162 automatic trees became 163 corrected trees; 86 are unchanged. Time spent was about 106 hours (my own per-tree estimate).
4. **Step 3: label transfer** with `scripts/tree_extraction.py`. TODO: which cloud was used as `plot_file` and the parameters used.

### scripts/tree_extraction.py

For every per-tree cloud in `trees_folder`, finds the points of `plot_file` that lie within `--distance_th` of any tree point (bounding-box prefilter, then Open3D nearest-point distance), writes them as `<tree name>_propagated.las` in `opath_folder`, and removes them from the plot so no point is assigned twice. The points left over are written to `opath_plot`.

```bash
python scripts/tree_extraction.py plot_file trees_folder opath_folder opath_plot [--distance_th 0.01]
```

| Argument | Meaning |
|---|---|
| `plot_file` | Plot point cloud (.las, .laz or .ply) |
| `trees_folder` | Folder of per-tree clouds |
| `opath_folder` | Output folder for the `_propagated.las` files (created if missing) |
| `opath_plot` | Output file for the leftover plot points |
| `--distance_th` | Distance threshold in metres, default 0.01 |

Packages: `open3d`, `numpy`, `laspy`, plus `lazrs` or `laszip` for `.laz` input. Install with `pip install -r environment/requirements.txt`.

The script resumes interrupted runs through `mask_plot.npy` and `processed_trees.json` in the **current working directory**; delete both before starting a new run from a different folder.

## Where the full data is

Not in the repo (sizes are approximate, GiB):

| Plot | Crop | Resolution | Folder | Size |
|---|---|---|---|---|
| WSF_ML1C | raw | 1 cm | `data/raw/WSF_ML1C` | 2.1 |
| WSL_ML2A | raw | 1 cm | `data/raw/WSL_ML2A` | 2.3 |
| WSL_ML2A | 35x35 | full | `data/cropped/WSL_ML2A/35x35/full` | 5.7 |
| WSL_ML2A | 35x35 | 2 cm | `data/cropped/WSL_ML2A/35x35/2cm` | 3.0 |
| WSL_ML2A | 35x35 | 3 cm | `data/cropped/WSL_ML2A/35x35/3cm` | 1.6 |
| WSL_ML2A | 55x55 | full | `data/cropped/WSL_ML2A/55x55/full` | 12.0 |
| WSL_ML2A | 55x55 | 2 cm | `data/cropped/WSL_ML2A/55x55/2cm` | 6.4 |
| WSL_ML2A | 55x55 | 3 cm | `data/cropped/WSL_ML2A/55x55/3cm` | 3.5 |
| WSL_ML2A | 35x35 | 2 cm | `outputs/WSL_ML2A/35x35/2cm` (60 trees) | 5.4 |
| WSL_ML2A | 35x35 | 3 cm | `outputs/WSL_ML2A/35x35/3cm` (60 trees) | 2.9 |
| WSL_ML2A | 55x55 | 2 cm | `outputs/WSL_ML2A/55x55/2cm` (161 trees) | 11.6 |
| WSL_ML2A | 55x55 | 3 cm | `outputs/WSL_ML2A/55x55/3cm` (162 automated trees, 199 corrected clouds, propagated trees, CloudCompare `.bin` projects, temp) | 25.3 |

Total outside the repo: about 82 GiB (`data/` 36.5 GiB, `outputs/` 45.2 GiB). The 67.3 GB in docs/reorganization_notes.md predates the manual corrections (files added after 2026-10-02).

The full data is not hosted publicly. The scan belongs to the Hawkesbury Institute for the Environment, and public release needs the custodian's permission, which has not been confirmed. Contact the author or supervisors for access.
