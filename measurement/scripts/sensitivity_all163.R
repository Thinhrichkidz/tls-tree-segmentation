# REPORT_DATA_REQUEST.md item 5 (sensitivity.csv) for 8 representative trees with accepted DBH.
# Uses the same rotated, cropped stem points as the all-163 worker (prep.json axis; bark-radius crop) and ITSMe
# diameter_slice_pc at 1.3 m along the stem with slice thickness 3, 5, 6 (baseline) and 10 cm. Reports the circle
# diameter and ITSMe's functional (hull-based) fdiameter. Height (max vs 99th percentile) and crown volume (single
# convex envelope vs sums of 1 m and 0.5 m slab envelopes) are read from the batch outputs. Read-only.
# Usage: Rscript sensitivity_all163.R <all-163 output folder>
args <- commandArgs(trailingOnly = TRUE); OUT <- normalizePath(args[1], winslash = "/")
# Project root = two levels above this script (portable; edited 23 Oct 2026 after the final run, logic unchanged)
self <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))
ROOT <- normalizePath(file.path(dirname(self), "..", ".."), winslash = "/")
source(file.path(ROOT, "measurement_pipeline/scripts/all163_tree_worker.R"))
TREES <- c("tree_146", "tree_151", "tree_063", "tree_093", "tree_069", "tree_118", "tree_084", "tree_103")
rows <- list()
for (tid in TREES) {
  prep <- jsonlite::fromJSON(file.path(OUT, "per_tree", tid, "prep.json"))
  res <- jsonlite::fromJSON(file.path(OUT, "per_tree", tid, "result.json"))
  pc <- ITSMe::read_tree_pc(path = file.path(OUT, "per_tree", tid, basename(prep$local_xyz_path)), samplefactor = 1)   # relative: works if the drive letter changes
  o <- c(prep$axis_o, 0); v <- c(prep$axis_s, 1); v <- v / sqrt(sum(v^2))
  P <- sweep(as.matrix(pc[, c("X", "Y", "Z")]), 2, o) %*% t(rotation_to_vertical(v))
  rp <- data.frame(X = P[, 1], Y = P[, 2], Z = P[, 3])
  rc <- rp[sqrt(rp$X^2 + rp$Y^2) <= res$crop_radius_m, ]
  if (isTRUE(prep$dbh_outline_filter)) rc <- outline_filter(rc)
  base <- list(tree = tid, height_max_m = prep$full_cloud_height_m, height_p99_m = prep$height_p99_m,
               crown_envelope_m3 = res$crown$volume_m3,
               crown_sum_1m_slab_hulls_m3 = res$crown$volume_m3 / res$crown$slab_ratio_1m,
               crown_sum_0p5m_slab_hulls_m3 = res$crown$volume_m3 / res$crown$slab_ratio_0.5m,
               neighbour_contact = "see workbook", reported_dbh_cm = 100 * res$dbh_m)
  for (w in c(0.03, 0.05, 0.06, 0.10)) {
    s <- tryCatch(ITSMe::diameter_slice_pc(pc = rc, slice_height = 1.3, slice_thickness = w, dtm = data.frame(X = 0, Y = 0, Z = 0),
                                           r = 1.5, functional = TRUE, plot = FALSE), error = function(e) NULL)
    tag <- paste0(round(100 * w), "cm")
    base[[paste0("dbh_circle_", tag, "_cm")]] <- if (is.null(s)) NA else 100 * s$diameter
    base[[paste0("dbh_hull_", tag, "_cm")]] <- if (is.null(s)) NA else 100 * s$fdiameter
    base[[paste0("passes_", tag)]] <- !is.null(s) && accept(s$arc_coverage, s$R2, s$diameter)
  }
  rows[[tid]] <- base
}
tab <- data.table::rbindlist(rows, fill = TRUE)
dir.create(file.path(OUT, "results"), showWarnings = FALSE)
data.table::fwrite(tab, file.path(OUT, "results", "sensitivity.csv"))
print(tab[, c("tree", "reported_dbh_cm", "dbh_circle_3cm_cm", "dbh_circle_5cm_cm", "dbh_circle_6cm_cm", "dbh_circle_10cm_cm", "dbh_hull_6cm_cm",
              "height_max_m", "height_p99_m", "crown_envelope_m3", "crown_sum_1m_slab_hulls_m3")], digits = 4)
