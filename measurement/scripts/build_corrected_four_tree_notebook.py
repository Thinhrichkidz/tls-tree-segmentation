"""Write a new notebook copy for the four corrected trees. The top-20 notebook is read, never modified.

Changes against ITSMe_HEIGHT_DBH_CROWN_VOLUME_TOP20_20261023.ipynb:
  * manifest, human-review sheet and axis folder point at the CORRECTED_FOUR_TREE_RERUN batch;
  * optional outer-outline filter for DBH (manifest column dbh_outline_filter, in memory only);
  * extra DBH outputs: raw circle fit with its screen result, ellipse axes and area-equivalent diameter.
Algorithms, thresholds and crown/height stages are otherwise unchanged.
"""
import argparse
import json
from pathlib import Path

import nbformat

parser = argparse.ArgumentParser()
parser.add_argument('--config', required=True)
args = parser.parse_args()
mp = Path(__file__).resolve().parents[1]
root = mp.parent
config = json.loads(Path(args.config).read_text())
tag = Path(config['batch']).name
src = mp / 'notebooks' / 'ITSMe_HEIGHT_DBH_CROWN_VOLUME_TOP20_20261023.ipynb'
dst = mp / 'notebooks' / f'ITSMe_HEIGHT_DBH_CROWN_VOLUME_{tag}.ipynb'
assert not dst.exists()
nb = nbformat.read(src, as_version=4)

def replace(old, new, count=None):
    hits = sum(c.source.count(old) for c in nb.cells)
    assert hits and (count is None or hits == count), (old, hits)
    for c in nb.cells:
        c.source = c.source.replace(old, new)

replace('CROWN_VOLUME_TOP20_20261023_164430_manifest.csv', config['manifest_name'])
replace('CROWN_VOLUME_TOP20_20261023_164430_human_review.csv', config['review_name'])
replace('measurement_pipeline/results/CROWN_VOLUME_TOP20_20261023_164430/axis', config['axis_relative'], 2)
replace('TREE_ID <- "tree_146"', 'TREE_ID <- "tree_103"', 1)

nb.cells[0].source = f"""# Height, DBH and crown-envelope volume: four cleaned trees with corrected references
Prepared 23 October 2026 from `ITSMe_HEIGHT_DBH_CROWN_VOLUME_TOP20_20261023.ipynb` (unchanged). Inputs: `{config['manifest_name']}`.
Set `TREE_ID` to tree_103, tree_108, tree_067 or tree_033 and run all cells with the R (INFO6003 ITSMe) kernel.

User decisions applied (23 Oct 2026, after `CLEANED_TRUNK_DIAGNOSIS_20261023_185259`):
* **103, 108**: corrected stem base. The inherited foot lay beside the trunk; the local origin is now where the stem line meets the preserved terrain mesh (+0.18 m and +0.12 m higher).
* **033**: earlier near-vertical axis kept; source data poor, DBH not released.
* **067**: DBH uses an *outer-outline filter*: in each 10 cm layer between 0.8 and 1.8 m along the stem, points more than 3 cm inside the convex outline are set aside **in memory only** before the circle fit. They are not bark and pulled the circle small.
* **103**: the trunk is oval, so both a circle-fit DBH and an **area-equivalent diameter** (ellipse fitted to the 1.3 m slice, `sqrt(major x minor)`) are reported. The circle is reported even if it fails the screen, labelled as such.
* **108**: DBH stays provisional (the cloud's 3 cm spacing is coarser than the screen allows for a 9 cm stem).

The acceptance screen is unchanged. Nothing here approves a tree; all human decisions stay PENDING.
"""

# Helpers: outline filter and ellipse axes.
cell19 = next(c for c in nb.cells if c.cell_type == 'code' and 'rotation_to_vertical <- function' in c.source)
cell19.source += '''
# Outer-outline filter (user decision for tree_067): per 10 cm layer, drop points > 3 cm inside the convex outline.
outline_filter <- function(rc, z_from = 0.8, z_to = 1.8, inside_m = 0.03) {
  keep <- rep(TRUE, nrow(rc)); lay <- floor(rc$Z / 0.10)
  for (L in unique(lay[rc$Z > z_from & rc$Z < z_to])) {
    i <- which(lay == L); if (length(i) < 10) next
    h <- grDevices::chull(rc$X[i], rc$Y[i]); hx <- rc$X[i][h]; hy <- rc$Y[i][h]; n <- length(h)
    d <- vapply(seq_along(i), function(j) { p <- c(rc$X[i][j], rc$Y[i][j]); min(vapply(1:n, function(k) {
      a <- c(hx[k], hy[k]); ab <- c(hx[k %% n + 1], hy[k %% n + 1]) - a
      t <- max(0, min(1, sum((p - a) * ab) / sum(ab^2))); sqrt(sum((p - a - t * ab)^2)) }, numeric(1))) }, numeric(1))
    keep[i[d > inside_m]] <- FALSE
  }
  rc[keep, ]
}
# Full ellipse axis lengths (m), algebraic fit; NA if the fit is not an ellipse.
ellipse_axes <- function(x, y) {
  if (length(x) < 8) return(c(NA_real_, NA_real_))
  a <- qr.solve(cbind(x * x, x * y, y * y, x, y), rep(1, length(x)))
  M <- matrix(c(a[1], a[2] / 2, a[2] / 2, a[3]), 2)
  w <- eigen(M, symmetric = TRUE)$values
  if (any(w <= 0)) return(c(NA_real_, NA_real_))
  c0 <- solve(2 * M, -a[4:5]); F <- 1 + drop(t(c0) %*% M %*% c0)
  sort(2 * sqrt(F / w))
}
'''

cell20 = next(c for c in nb.cells if c.cell_type == 'code' and 'lean_failure <- "NOT_COMPLETED"' in c.source)
old = '  row$crop_radius_m <- crop_r\n'
assert cell20.source.count(old) == 1
cell20.source = cell20.source.replace(old, old + '''  # Shape descriptor from a wider crop (oval trunks reach beyond the circle crop)
  shape_r <- max(crop_r, 2 * row$bark_radius_est_m + 0.10)
  es <- rp[abs(rp$Z - 1.3) <= 0.03 & sqrt(rp$X^2 + rp$Y^2) <= shape_r, ]
  ea <- tryCatch(ellipse_axes(es$X, es$Y), error = function(e) c(NA_real_, NA_real_))
  row$shape_crop_radius_m <- shape_r; row$shape_points <- nrow(es)
  row$ellipse_minor_m <- ea[1]; row$ellipse_major_m <- ea[2]; row$area_equivalent_d_m <- sqrt(ea[1] * ea[2])
  row$outline_filter <- isTRUE(as.logical(sel$dbh_outline_filter))
  if (row$outline_filter) {
    n0 <- nrow(rc); rc <- outline_filter(rc); row$outline_filter_removed_points <- n0 - nrow(rc)
  }
''')
old = '  row$accepted_slices <- length(acc)\n'
assert cell20.source.count(old) == 1
cell20.source = cell20.source.replace(old, old + '  row$dbh13_passes_screen <- !is.null(d13) && accept(d13$arc_coverage, d13$R2, d13$dbh)\n')

cell22 = next(c for c in nb.cells if c.cell_type == 'code' and 'summary <- data.frame(' in c.source)
old = '  human_review_decision=selected$human_review_decision,'
assert cell22.source.count(old) == 1
cell22.source = cell22.source.replace(old, '''  dbh_circle_raw_cm=100 * scalar(lean_result, "dbh13_m"),
  dbh_circle_raw_arc=scalar(lean_result, "dbh13_arc"),
  dbh_circle_raw_rmse_mm=1000 * sqrt(scalar(lean_result, "dbh13_R2")),
  dbh_circle_raw_passes_screen=isTRUE(lean_result$dbh13_passes_screen),
  dbh_area_equivalent_cm=100 * scalar(lean_result, "area_equivalent_d_m"),
  ellipse_minor_cm=100 * scalar(lean_result, "ellipse_minor_m"),
  ellipse_major_cm=100 * scalar(lean_result, "ellipse_major_m"),
  dbh_outline_filter=isTRUE(lean_result$outline_filter),
  outline_filter_removed_points=scalar(lean_result, "outline_filter_removed_points"),
  dbh_report_mode=selected$dbh_report_mode,
  base_shift_xyz_m=selected$base_shift_xyz_m,
''' + old)
nbformat.write(nb, dst)
print(dst)
