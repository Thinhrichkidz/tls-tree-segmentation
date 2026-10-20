# Automated segmentation sample (plot WSL_ML2A, 55x55 crop, 3 cm)

Source: `outputs/WSL_ML2A/55x55/3cm/`

- `trees/clouds/`: 8 per-tree clouds (RayCloudTools output), all under 50 MB. Chosen so that they can be paired with the manual versions (see `../manual_segmentation/SAMPLE_INFO.md`).
- `trees/metadata/`: the matching per-tree `.txt` files (`..._raycloud_trees_<id>.txt`, branch-skeleton segments).
- `segmentation/`: the 11 small `..._seg_vNN.ply` files from the segmentation folder (0 to 1.5 MB each).
- `WSL_ML2A_55x55_3cm_leftover_sample.laz`: crop of `output_script/WSL_ML2A_crop_55x55_3cm_leftover.las` (points not assigned to any tree) to the same box as `../raw` and `../downsampled`: x 261358.0 to 261365.0 m, y 6264492.0 to 6264499.0 m. 263,089 points, 2 MB.

Not included: terrain mesh (38 MB), combined tree TXT (22 MB), `.bin` CloudCompare projects, `temp/`, `mask_plot.npy`, `processed_trees.json` (absolute `D:\` paths).

Tree IDs are not the same in the automated and manual folders; see the pairing table in the manual folder.
