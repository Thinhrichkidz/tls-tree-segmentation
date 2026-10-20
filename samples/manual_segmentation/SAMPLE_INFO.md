# Manual (corrected) segmentation sample

Source: `outputs/WSL_ML2A/55x55/3cm/trees/cloud_correct/` (199 corrected `demo_<id>_<timestamp>.ply` clouds, exported from CloudCompare).

## How the trees were matched

The corrected files are numbered `demo_<id>`, and these IDs are **not** the automated IDs (the same ID never refers to the same tree). They were matched geometrically: for each automated tree the corrected cloud whose axis-aligned bounding box overlaps best (IoU) was taken. 104 of 162 automated trees have a match with IoU > 0.99; the other 58 were not matched (presumably split, merged or removed during correction) and are not in this sample.

## Pairs in this sample

| Auto ID | Automated file (`../automated_segmentation/trees/clouds/`) | Corrected file (`trees/cloud_correct/`) | Points before | Points after | Change |
|---|---|---|---|---|---|
| 79 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_79.ply` | `demo_95_2026-10-19_00h38_55_465.ply` | 52,504 | 48,251 | edited |
| 76 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_76.ply` | `demo_91_2026-10-19_00h38_54_524.ply` | 174,636 | 185,171 | edited |
| 126 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_126.ply` | `demo_152_2026-10-19_00h39_03_402.ply` | 222,367 | 209,366 | edited |
| 77 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_77.ply` | `demo_92_2026-10-19_00h38_54_678.ply` | 339,283 | 328,748 | edited |
| 4 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_4.ply` | `demo_7_2026-10-19_00h38_46_515.ply` | 50,283 | 50,283 | unchanged |
| 14 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_14.ply` | `demo_19_2026-10-19_00h38_47_053.ply` | 75,479 | 75,479 | unchanged |
| 66 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_66.ply` | `demo_76_2026-10-19_00h38_52_195.ply` | 73,409 | 73,409 | unchanged |
| 56 | `WSL_ML2A_crop_55x55_3cm_raycloud_segmented_56.ply` | `demo_65_2026-10-19_00h38_50_948.ply` | 60,288 | 60,288 | unchanged |

"edited" means the point count changed during manual correction; "unchanged" means the corrected cloud has the same point count (bounding boxes match with IoU > 0.99; point content was not compared).
