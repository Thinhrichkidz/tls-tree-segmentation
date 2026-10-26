"""Create a separate R notebook. Existing notebooks and scientific inputs are read-only."""
from copy import deepcopy
from pathlib import Path
import nbformat as nbf

mp = Path(__file__).resolve().parents[1]
target = mp / 'notebooks' / 'ITSMe_HEIGHT_DBH_CROWN_VOLUME.ipynb'
if target.exists():
    raise FileExistsError(f'Refusing to overwrite {target}')
nb = deepcopy(nbf.read(mp / 'notebooks' / 'ITSMe_HOME_PORTABLE.ipynb', as_version=4))
lean = nbf.read(mp / 'notebooks' / 'ITSMe_DBH_lean_correction.ipynb', as_version=4)

def replace(cell, old, new):
    assert old in cell.source, f'Missing source anchor: {old}'
    cell.source = cell.source.replace(old, new)

nb.cells[0].source = '''# Tree height, DBH and crown-envelope volume
New working notebook, 23 October 2026. Original course and previous working notebooks remain unchanged.

Run with an **R kernel containing ITSMe, geometry, digest, jsonlite, ggplot2 and data.table**.
The default is **one tree: tree_146**. Change `TREE_ID` to a tree in the CURRENT manifest.
Run all cells from the top. Each run creates a new results folder.

The last cell writes and displays `tree_metrics.csv`: height (m), accepted lean-corrected DBH (cm),
crown area (m²), and **3D convex crown-envelope volume (m³)**. Failed measurements stay missing with a reason;
do not interpret a missing DBH as zero.
'''
nb.cells[1].source = '''## What crown volume means here
This extension takes the **same ITSMe-classified crown points** used for projected crown area and encloses
them with a 3D convex hull. `geometry::convhulln` computes the enclosed volume using Qhull.
All crown observations are used; there is no random sampling, automatic outlier removal, gap filling,
or reassignment of points to trees. Exact duplicate positions are redundant to a hull and are collapsed in memory only.

**This is the outer crown envelope, including internal air spaces and gaps between branches.** It is not
wood volume, leaf-material volume, biomass, or CO₂. A convex envelope bridges concavities. Missing crown pieces,
incorrect neighbouring branches and an incorrect automatic crown base can change this estimate substantially.
Inspect the crown-classification plot, envelope projections and derived surface mesh before reporting it.
All measurements remain provisional; this notebook never changes the human approval record.

Height remains vertical height above estimated foot ground. DBH is calculated separately: an optional horizontal
fit is diagnostic, and an accepted lean-corrected fit is the reported DBH. A fallback median from nearby
1.1–1.5 m slices is explicitly labelled and is not a direct measurement at exactly 1.3 m.
No QSM is run. `CloudCompare_review_v2` and all original input files are read only.

References: [geometry/Qhull function documentation](https://search.r-project.org/CRAN/refmans/geometry/html/convhulln.html);
[published comparison of convex and concave crown volumes](https://doi.org/10.1016/j.ecolind.2024.112219).
'''
replace(nb.cells[2], 'if (!requireNamespace("IRkernel",quietly=TRUE))', 'if (!requireNamespace("IRkernel",quietly=TRUE))')
replace(nb.cells[3], 'RUN_DBH <- FALSE', 'RUN_DBH <- TRUE  # horizontal diagnostic, skipped for lean >= 15 degrees')
replace(nb.cells[3], 'RUN_CROWN <- FALSE', 'RUN_CROWN <- TRUE')
replace(nb.cells[3], '"home_selection_manifest.csv"', '"home_selection_manifest_CURRENT_20261023.csv"')
replace(nb.cells[3], '"human_review_template.csv"', '"human_review_template_CURRENT_20261023.csv"')
replace(nb.cells[3], 'paste0("ITSMe_", TREE_ID', 'paste0("ITSMe_metrics_", TREE_ID')
replace(nb.cells[3], 'set.seed(6003)', 'dbh1 <- NULL; ca1 <- NULL; crown1 <- NULL; crown_volume <- NULL; lean_result <- NULL\nset.seed(6003)')
nb.cells[3].source = nb.cells[3].source.replace('# change to any stable ID in the ten-tree selection manifest', '# choose a stable ID from the CURRENT selection manifest')
nb.cells[4].source = '## Check dependencies and record the actual R environment\nNo packages are installed automatically. Missing dependencies stop execution.'
replace(nb.cells[5], 'c("ITSMe", "ggplot2", "data.table")', 'c("ITSMe", "ggplot2", "data.table", "geometry", "digest", "jsonlite")')
nb.cells[8].source = '''## Ground-referenced height
Height is the full-cloud maximum above the fixed stem-foot ground. The diagnostic also shows the earlier
supported-top estimate from the manifest; that earlier comparison can be stale for edited trees.
This is vertical height, not the length of a curved or leaning stem.'''
nb.cells[10].source = '''## Horizontal DBH diagnostic
Uses the earlier ITSMe circle-fit parameters and a 6 cm horizontal slice. A fit error is recorded so that
height and crown processing can continue. For stems leaning at least 15 degrees this diagnostic is skipped
unless explicitly enabled. The accepted perpendicular fit calculated below supplies the reported DBH.'''
nb.cells[11].source = '''dbh_failure <- "NOT_REQUESTED"
if (RUN_DBH) {
  if (selected$estimated_low_stem_lean_degrees >= 15 && !ALLOW_LEAN_HORIZONTAL_DIAMETER) {
    dbh_failure <- "HORIZONTAL_DIAGNOSTIC_SKIPPED_FOR_LEAN"
  } else {
    dbh1 <- tryCatch(run_stage("DBH", function() ITSMe::dbh_pc(pc=tree1, dtm=ground_ref,
      r=ground_lookup_radius, thresholdR2=0.001, slice_thickness=0.06,
      functional=TRUE, concavity=4, plot=TRUE)), error=function(e) {
        dbh_failure <<- conditionMessage(e); NULL
      })
    if (!is.null(dbh1)) {
      dbh_failure <- "DIAGNOSTIC_ONLY"
      saveRDS(dbh1, file.path(RUN_DIR, paste0(TREE_ID, "_dbh_provisional.rds")))
      ggplot2::ggsave(file.path(RUN_DIR, paste0(TREE_ID, "_dbh_horizontal_diagnostic.png")),
                     plot=dbh1$plot, width=7, height=7)
    }
  }
}
'''
nb.cells[12].source = '''## Automatic crown classification and projected crown area
Keeps ITSMe's original width-expansion classification (`thresholdbranch=1.5`) and projected concave-hull
area (`concavity=3`). Classification is a geometric proposal, not a leaf/wood separation or ownership approval.
If classification fails, crown area and volume remain missing; there is no silent alternative crown split.'''
nb.cells[13].source = '''crown_failure <- "NOT_REQUESTED"
if (RUN_CROWN) {
  crown1 <- tryCatch({
    classified <- run_stage("crown_classification", function() ITSMe::classify_crown_pc(pc=tree1,
      dtm=ground_ref, r=ground_lookup_radius, thresholdbranch=1.5, plot=TRUE))
    crown <- classified$crownpoints
    if (is.null(crown) || nrow(crown) == 0) stop("No usable crown points returned.")
    saveRDS(classified, file.path(RUN_DIR, paste0(TREE_ID, "_crown_classification.rds")))
    ggplot2::ggsave(file.path(RUN_DIR, paste0(TREE_ID, "_crown_classification.png")),
                   plot=classified$plot, width=7, height=8)
    crown
  }, error=function(e) { crown_failure <<- conditionMessage(e); NULL })
  if (!is.null(crown1)) {
    crown_failure <- "CLASSIFICATION_AVAILABLE_REQUIRES_VISUAL_REVIEW"
    ca1 <- tryCatch({
      area <- run_stage("projected_crown_area", function() ITSMe::projected_area_pc(pc=crown1,
        concavity=3, plot=TRUE))
      ggplot2::ggsave(file.path(RUN_DIR, paste0(TREE_ID, "_crown_area.png")),
                     plot=area$plot, width=7, height=7)
      saveRDS(area, file.path(RUN_DIR, paste0(TREE_ID, "_crown_area.rds")))
      area
    }, error=function(e) NULL)
  }
}
'''
preflight = nbf.v4.new_code_cell('''# Refuse stale review inputs. Review approval remains a separate human decision.
review_ply <- selected$source_ply_path
stopifnot(file.exists(review_ply))
actual_review_sha256 <- digest::digest(file=review_ply, algo="sha256")
if (!identical(tolower(actual_review_sha256), tolower(selected$review_sha256))) {
  stop("Review PLY changed since the CURRENT manifest. Prepare new versioned inputs before measuring it.")
}
transform_path <- file.path(dirname(selected$local_xyz_path), "coordinate_transform.json")
helper_path <- file.path(WORK, "scripts", "crown_volume_metrics.R")
inputs <- c(review_ply, selected$local_xyz_path, selected$local_ground_reference_path,
            transform_path, helper_path,
            file.path(WORK, "environment", "home_selection_manifest_CURRENT_20261023.csv"), review_path)
stopifnot(all(file.exists(inputs)))
input_hashes <- data.frame(path=inputs,
  sha256=vapply(inputs, function(p) digest::digest(file=p, algo="sha256"), character(1)))
write.csv(input_hashes, file.path(RUN_DIR, "input_hashes.csv"), row.names=FALSE)
source(helper_path, local=TRUE)
''')
nb.cells.insert(6, preflight)

nb.cells += [nbf.v4.new_markdown_cell('''## Crown-envelope volume (m³)
The hull is fitted in the original, unrotated local frame to exactly the classified crown used above.
The exported mesh uses that same local frame; do not overlay it on global-coordinate files without the
recorded coordinate transform. Invalid or coplanar geometry produces a missing value with a reason.
Orange outlines in the diagnostic are projections of the 3D envelope, not the earlier concave crown-area boundary.'''),
nbf.v4.new_code_cell('''volume_failure <- "CROWN_UNAVAILABLE"
if (!is.null(crown1)) {
  crown_volume <- tryCatch({
    hull <- crown_convex_hull(crown1)
    saveRDS(hull, file.path(RUN_DIR, paste0(TREE_ID, "_crown_convex_hull.rds")))
    write_crown_hull_ply(hull, file.path(RUN_DIR, paste0(TREE_ID, "_crown_convex_hull_local.ply")))
    plot_crown_envelope(crown1, hull,
      file.path(RUN_DIR, paste0(TREE_ID, "_crown_envelope_projections.png")), TREE_ID)
    volume_failure <- "PROVISIONAL_ENVELOPE_REQUIRES_VISUAL_REVIEW"
    hull
  }, error=function(e) { volume_failure <<- conditionMessage(e); NULL })
}
'''),
nbf.v4.new_markdown_cell('''## Lean-corrected DBH
Uses the helpers and measurement loop from `ITSMe_DBH_lean_correction.ipynb`: rotate the lower-stem axis
to vertical, crop near the estimated bark radius, and apply the same ITSMe slice fits and acceptance rules.
Acceptable coverage is at least 60%; RMSE must satisfy the documented diameter-dependent limit.

**Additional input check:** this notebook requires the saved axis checkpoint to match the current review PLY
hash. If the tree has been edited since that axis was fitted, DBH is left unavailable pending an updated
axis. It does not silently reuse an old axis or run the earlier unreliable fallback tracker.
The crown-volume calculation is independent of this rotation and is retained even if DBH is unavailable.''')]

lean_settings = lean.cells[1].source.replace('TREES <- NULL', 'TREES <- c(TREE_ID)')
lean_settings = lean_settings.replace('# NULL = all ten selected trees; or e.g. c("tree_103", "tree_108")', '# one selected tree')
nb.cells.append(nbf.v4.new_code_cell(lean_settings + '''
suppressPackageStartupMessages(library(ggplot2))
OUT <- file.path(RUN_DIR, "lean_dbh")
dir.create(OUT)
ground0 <- ground_ref
'''))
nb.cells.append(nbf.v4.new_code_cell(lean.cells[3].source))
loop = lean.cells[4].source
replace_anchor = 'if (file.exists(ck)) {\n    sa <- jsonlite::fromJSON(ck)$stem_axis'
assert replace_anchor in loop
loop = loop.replace(replace_anchor, '''checkpoint <- if (file.exists(ck)) jsonlite::fromJSON(ck) else NULL
  checkpoint_hash <- if (!is.null(checkpoint)) checkpoint$row$review_sha256 else NULL
  if (is.null(checkpoint_hash) || !identical(tolower(checkpoint_hash), tolower(sel$review_sha256))) {
    row$status <- "STALE_OR_MISSING_STEM_AXIS_CHECKPOINT"
    row$method <- "unavailable: update and inspect stem axis for current review PLY"
    results[[tid]] <- row
    next
  }
  if (file.exists(ck)) {
    sa <- checkpoint$stem_axis''')
nb.cells.append(nbf.v4.new_code_cell('''lean_failure <- "NOT_COMPLETED"
tryCatch({
''' + loop + '''
  lean_failure <- "COMPLETED_CHECK_FIT_STATUS"
}, error=function(e) {
  lean_failure <<- conditionMessage(e)
  writeLines(lean_failure, file.path(OUT, "dbh_error.txt"))
})
if (length(results)) {
  lean_table <- data.table::rbindlist(lapply(results, as.list), fill=TRUE)
  data.table::fwrite(lean_table, file.path(OUT, "dbh_lean_corrected.csv"))
  lean_result <- results[[TREE_ID]]
}
if (length(slices)) data.table::fwrite(do.call(rbind, slices), file.path(OUT, "dbh_lean_corrected_slices.csv"))
'''))
nb.cells.append(nbf.v4.new_markdown_cell('''## Final results and interpretation
`tree_metrics.csv` is the single-row result to open or copy. DBH is in centimetres; height is in metres;
crown area is in square metres; crown-envelope volume is in cubic metres. Missing results are `NA`.
The horizontal DBH is retained only as a diagnostic. Review the labelled lean method and fit plots.
The volume is a convex envelope, with no biological accuracy claim or uncertainty interval.
Human approval is carried from the exact-hash review record, not granted by this run.'''))
nb.cells.append(nbf.v4.new_code_cell('''scalar <- function(x, name) {
  value <- x[[name]]
  if (is.null(value) || !length(value)) NA_real_ else as.numeric(value[1])
}
text_value <- function(x, name, fallback) {
  value <- x[[name]]
  if (is.null(value) || !length(value)) fallback else as.character(value[1])
}
summary <- data.frame(
  stable_tree_id=TREE_ID, review_sha256=actual_review_sha256,
  height_m=h1$h,
  dbh_cm=100 * scalar(lean_result, "dbh_corrected_m"),
  dbh_method=text_value(lean_result, "method", lean_failure),
  dbh_status=if (identical(text_value(lean_result, "status", lean_failure), "OK") &&
    !is.finite(scalar(lean_result, "dbh_corrected_m"))) "NO_ACCEPTABLE_SLICE" else
    text_value(lean_result, "status", lean_failure),
  dbh_horizontal_diagnostic_cm=100 * scalar(dbh1, "dbh"),
  horizontal_dbh_status=dbh_failure,
  crown_area_m2=scalar(ca1, "pa"),
  crown_volume_m3=scalar(crown_volume, "volume_m3"),
  crown_volume_method="3D_CONVEX_HULL_CROWN_ENVELOPE_INCLUDING_INTERNAL_GAPS",
  crown_volume_status=volume_failure,
  crown_classification_status=crown_failure,
  crown_points=if (is.null(crown1)) NA_integer_ else nrow(crown1),
  crown_surface_area_m2=scalar(crown_volume, "surface_area_m2"),
  human_review_decision=selected$human_review_decision,
  validation_status="PROVISIONAL_NOT_FIELD_VALIDATED")
write.csv(summary, file.path(RUN_DIR, "tree_metrics.csv"), row.names=FALSE, na="NA")
saveRDS(list(summary=summary, volume=crown_volume, lean_dbh=lean_result), file.path(RUN_DIR, "tree_metrics.rds"))
file.copy(transform_path, file.path(RUN_DIR, "coordinate_transform.json"), overwrite=FALSE)
ck <- file.path(WORK, "checkpoints", paste0(TREE_ID, "_height.json"))
if (file.exists(ck)) {
  writeLines(digest::digest(file=ck, algo="sha256"), file.path(RUN_DIR, "stem_axis_checkpoint_sha256.txt"))
  file.copy(ck, file.path(RUN_DIR, "stem_axis_checkpoint_used_or_rejected.json"), overwrite=FALSE)
}
cat("Results folder:", RUN_DIR, "\\n")
print(summary[, c("stable_tree_id", "height_m", "dbh_cm", "dbh_method", "crown_area_m2", "crown_volume_m3")])
'''))
for c in nb.cells:
    if c.cell_type == 'code':
        c.outputs = []
        c.execution_count = None
nb.metadata.kernelspec = {'display_name': 'R (INFO6003 ITSMe)', 'language': 'R', 'name': 'info6003-ir'}
nbf.validate(nb)
nbf.write(nb, target)
print(target)
