# All-163 TLS visualisations (v6): summary

Generated 28 October 2026 by Claude. **This folder supersedes** `ITSMe_all163_visualisations_20261023_202459/` (v3 values; kept unchanged).

- **Numbers source:** `ITSMe_all163_output_v6_FINAL_20261028/ITSMe_all163_results.xlsx`, read only; its hash is the same before and after rendering.
- **Point source:** the 163 clouds in `CloudCompare_review_v2`. Each hash is checked against the current baseline
  `session4_claude_20261028/state/CloudCompare_review_v2_CURRENT.csv`.
- **Scripts:** `scripts/render_all163_figures.py` (style `all163-figures-v3`) and `scripts/validate_all163_visualisations.py`.

## Result

| Output | Count | Status |
|---|---|---|
| Individual 3-panel figures (3D, XZ, YZ), 300 dpi, 4800 x 1920 px | **163 of 163** | all opened and validated; 0 failures |
| Comparison grids | 8 | shortest 8, tallest 8, largest / smallest DBH, largest / smallest crown area, quality comparison, unusual structures |
| Report figures (PNG 300 dpi + PDF) | **9** | 5 distributions (new: crown slab volume), 3 scatter plots, status counts |

All 9 validation checks pass (`logs/visualisation_validation.json`).
- Titles and statuses match the workbook.
- Sources match the current baseline.
- Rankings use VALID values only.
- The workbook was unchanged.
- New checks:
  - the ESTIMATED DBH appears in the subtitle wherever the DBH column is N/A;
  - no estimate is shown next to a measured DBH;
  - the slab volume status is in every subtitle.

## What changed from the 23 Oct figures
- **Values:** all values come from v6. Heights changed on many trees; for example 100, 124, 137 and 083 fell 4-9.5 m after the floating points above the crown were removed. Edited clouds show their current points.
- **Subtitle:** adds the gap-aware crown volume ("crown slab volume", sum of 1 m slab hulls). Where the DBH column is N/A, it also shows the ESTIMATED DBH in brackets.
- **New report chart:** `crown_slab_volume_distribution` (VALID 130, REVIEW 26, N/A 7).
- **Style:** unchanged otherwise (viridis by height, terrain-mesh vertices in sienna, red stem-centre marker, 70,000-point display sample, seed 6003).

## Reading notes
- The Z axis is height above the ground at the original (translation) foot. For the 18 trees whose height foot was moved under the trunk, that ground differs from the height's ground by -0.42 to +0.30 m (most by a few cm). The reported height in the title is the corrected one.
- The comparison grids draw fitted stem-section centres only for trees whose stem axis came from a saved axis file. Trees with an axis refitted on edited points still get the red stem marker in their individual figure.
- Human approval is PENDING on every figure. Nothing is field-validated.
