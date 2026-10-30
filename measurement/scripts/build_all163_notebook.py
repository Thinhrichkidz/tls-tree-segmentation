"""Write the all-163 batch notebook (R kernel). Existing notebooks are not touched; refuses to overwrite."""
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

MP = Path(__file__).resolve().parents[1]
import sys
dst = MP / 'notebooks' / (sys.argv[1] if len(sys.argv) > 1 else 'ITSMe_ALL163_HEIGHT_DBH_CROWN_VOLUME.ipynb')
assert not dst.exists(), 'notebook exists; write a new version instead'

cells = [
    new_markdown_cell("""# ITSMe all-163 batch: height, DBH, crown area and crown-envelope volume
Prepared 23 October 2026; v5 (28 Oct 2026) adds step 2b, height refinements (`scripts/height_refine_all163.py`): the top rule re-checked on the current points and, for fallback-foot trees, the foot moved under the trunk; v4 (28 Oct 2026) adds the DBH v4 stage (`scripts/dbh_v4.R`: pooled 1.1-1.5 m robust circle fit) whose result appears only as ESTIMATED in the "Estimated DBH (cm)" column and never changes the DBH column; v3 (audit) adds stricter QC rules, stronger validation and an independent recalculation step; v2 added the user's crown-base choices for 55 more trees (`CROWN_BASE_REVIEW_ALL163_20261023_194703/user_crown_choices.csv`). Extends `ITSMe_HEIGHT_DBH_CROWN_VOLUME_TOP20_20261023.ipynb` (unchanged) from 20 trees to all 163
trees in `CloudCompare_review_v2`. Run all cells with the **R (INFO6003 ITSMe)** kernel (`info6003-ir`).

**What it does**
1. Checks every source cloud against the Session 3 hash snapshot (stops if any changed), then writes hash-checked local XYZ inputs
   and per-tree geometry with `scripts/prepare_all163.py` (Python, parallel).
2. Measures every tree in parallel R worker processes with `scripts/all163_tree_worker.R`: ITSMe height, lean-corrected DBH,
   ITSMe crown classification, and crown area / convex crown envelope above the user-agreed crown base. Same code and
   parameters as the 20-tree notebook; plotting is off (figures are a separate task).
3. Saves a checkpoint (`result.json`) per tree. Rerunning with the same `OUT` folder skips trees whose input, preparation and
   worker code are unchanged, and retries the rest.
4. Builds `ITSMe_all163_results.xlsx`, `results/tree_attributes.csv`, `methods.json`, `summary.json`, `outliers.csv` and
   `processing_summary.md` with `scripts/all163_postprocess.py`, then validates them.

**Rules kept from the project**: source clouds are read only; no thresholds were relaxed; a value that fails its quality rule is
`N/A` in the measurement column (raw fit kept in a separate column); no estimates are made (`REPORT_DATA_REQUEST.md` rule 1);
all human approvals stay PENDING; nothing is field-validated."""),
    new_code_cell("""# Settings
find_root <- function() {
  configured <- Sys.getenv("INFO6003_PROJECT_ROOT", "")
  p <- normalizePath(if (nzchar(configured)) configured else getwd(), winslash = "/", mustWork = TRUE)
  repeat {
    if (dir.exists(file.path(p, "CloudCompare_review_v2")) && dir.exists(file.path(p, "measurement_pipeline"))) return(p)
    parent <- dirname(p); if (identical(parent, p)) stop("Open Jupyter inside Codex_help or set INFO6003_PROJECT_ROOT."); p <- parent
  }
}
ROOT <- find_root(); WORK <- file.path(ROOT, "measurement_pipeline")
TREE_IDS <- NULL           # NULL = all 163 trees; e.g. c("tree_146", "tree_103") for a small test run
WORKERS <- NA              # NA = automatic: physical cores, limited by free RAM
RAM_PER_WORKER_GB <- 4     # conservative peak for the largest clouds (~1.3 M points)
OUT <- Sys.getenv("ALL163_OUT", "")   # set to an existing output folder to resume it
PREVIOUS_OUT <- Sys.getenv("ALL163_PREVIOUS", "")   # optional earlier all-163 output to compare against
if (!nzchar(OUT)) OUT <- file.path(WORK, "results", paste0("ITSMe_all163_output_", format(Sys.time(), "%Y%m%d_%H%M%S")))
for (d in c("", "logs", "checkpoints", "manifests", "results")) dir.create(file.path(OUT, d), showWarnings = FALSE, recursive = TRUE)
PY <- file.path(WORK, ".venv", "Scripts", "python.exe")
cat("Output folder:", OUT, "\\n")"""),
    new_code_cell("""# Dependencies and environment record (nothing is installed automatically)
need <- c("ITSMe", "jsonlite", "digest", "geometry", "data.table", "parallel")
missing <- need[!vapply(need, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) stop("Missing R packages: ", paste(missing, collapse = ", "))
stopifnot(file.exists(PY))
py_env <- jsonlite::fromJSON(system2(PY, c("-I", file.path(WORK, "scripts", "all163_env.py")), stdout = TRUE))
env <- list(R = R.version.string, ITSMe = as.character(packageVersion("ITSMe")), geometry = as.character(packageVersion("geometry")),
            data.table = as.character(packageVersion("data.table")), python = py_env,
            physical_cores = parallel::detectCores(logical = FALSE), logical_cores = parallel::detectCores(logical = TRUE),
            started = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"))
jsonlite::write_json(env, file.path(OUT, "logs", "environment.json"), auto_unbox = TRUE, pretty = TRUE)
str(env)"""),
    new_code_cell("""# 1. Prepare hash-checked local inputs and per-tree geometry (Python, parallel; reuses matching earlier preparation)
t_prep <- Sys.time()
args <- c("-I", file.path(WORK, "scripts", "prepare_all163.py"), "--out", OUT)
if (!is.null(TREE_IDS)) args <- c(args, "--trees", paste(TREE_IDS, collapse = ","))
status <- system2(PY, args, stdout = file.path(OUT, "logs", "prepare_stdout.txt"), stderr = file.path(OUT, "logs", "prepare_stderr.txt"))
if (status != 0) stop("Preparation failed; see logs/prepare_stderr.txt")
man <- read.csv(file.path(OUT, "manifests", "all163_manifest.csv"), stringsAsFactors = FALSE)
prep_seconds <- as.numeric(difftime(Sys.time(), t_prep, units = "secs"))
cat(nrow(man), "trees prepared in", round(prep_seconds), "s;", sum(man$reused == "True"), "reused\\n")
print(table(axis = ifelse(is.na(man$axis_source) | man$axis_source == "", "NO STEM AXIS", "stem axis available")))"""),
    new_code_cell("""# 2. Parallel measurement, one R worker process per core, largest clouds first
free_gb <- as.numeric(system2("powershell", c("-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"), stdout = TRUE)) / 1024^2
if (is.na(WORKERS)) WORKERS <- max(1, min(parallel::detectCores(logical = FALSE), floor(0.7 * free_gb / RAM_PER_WORKER_GB), nrow(man)))
preps <- file.path(OUT, "per_tree", man$tree, "prep.json")[order(-man$point_count)]
Sys.setenv(OMP_NUM_THREADS = "1", OPENBLAS_NUM_THREADS = "1", MKL_NUM_THREADS = "1", RGL_USE_NULL = "TRUE")
progress <- file.path(OUT, "checkpoints", "progress.csv")
if (!file.exists(progress)) writeLines("time,tree,status,seconds,pid", progress)
run_batch <- function(paths, workers) {
  cl <- parallel::makePSOCKcluster(workers, outfile = file.path(OUT, "logs", "workers.log"))
  on.exit(parallel::stopCluster(cl))
  parallel::clusterExport(cl, c("ROOT", "WORK", "progress"), envir = globalenv())
  parallel::clusterEvalQ(cl, {
    Sys.setenv(OMP_NUM_THREADS = "1", OPENBLAS_NUM_THREADS = "1", RGL_USE_NULL = "TRUE")
    .libPaths(c(file.path(WORK, "environment", "R-library"), .libPaths()))
    source(file.path(ROOT, "measurement_pipeline", "scripts", "all163_tree_worker.R")); TRUE })
  parallel::parLapplyLB(cl, paths, function(p) {
    r <- tryCatch(measure_tree(p, ROOT), error = function(e) list(tree = basename(dirname(p)), status = "failed", error = conditionMessage(e)))
    cat(sprintf("%s,%s,%s,%s,%d\\n", format(Sys.time(), "%Y-%m-%dT%H:%M:%S"), r$tree, r$status,
                if (is.null(r$seconds)) "" else round(r$seconds, 1), Sys.getpid()), file = progress, append = TRUE)
    r
  }, chunk.size = 1)
}
t_run <- Sys.time()
cat("Workers:", WORKERS, "| free RAM (GB):", round(free_gb), "| trees:", length(preps), "\\n")
res <- run_batch(preps, WORKERS)
failed <- vapply(res, function(r) identical(r$status, "failed"), logical(1))
retry <- NULL
if (any(failed)) {   # one retry of failed trees only; successful trees are not rerun
  cat("Retrying", sum(failed), "failed trees\\n")
  retry <- run_batch(preps[failed], min(WORKERS, sum(failed)))
  res[failed] <- retry
}
run_seconds <- as.numeric(difftime(Sys.time(), t_run, units = "secs"))
st <- vapply(res, function(r) r$status, character(1))
print(table(st))
jsonlite::write_json(list(workers = WORKERS, free_ram_gb = free_gb, ram_per_worker_gb = RAM_PER_WORKER_GB,
  physical_cores = parallel::detectCores(logical = FALSE), trees = length(preps), prep_seconds = prep_seconds,
  measure_seconds = run_seconds, retried = if (is.null(retry)) 0 else length(retry),
  statuses = as.list(table(st)), failures = Filter(function(r) identical(r$status, "failed"), res)),
  file.path(OUT, "logs", "run_timing.json"), auto_unbox = TRUE, pretty = TRUE)"""),
    new_code_cell("""# 2b. Height refinements (Python): top-edge check on the current points, trunk-centre foot candidates for fallback-foot trees
status <- system2(PY, c("-I", file.path(WORK, "scripts", "height_refine_all163.py"), "--out", OUT),
                  stdout = file.path(OUT, "logs", "height_refine_stdout.txt"), stderr = file.path(OUT, "logs", "height_refine_stderr.txt"))
cat(readLines(file.path(OUT, "logs", "height_refine_stdout.txt")), sep = "\n")
if (status != 0) stop("Height refinement failed; see logs/height_refine_stderr.txt")"""),
    new_code_cell("""# 3. Results tables, Excel workbook, QC and validation (Python)
status <- system2(PY, c("-I", file.path(WORK, "scripts", "all163_postprocess.py"), "--out", OUT, if (nzchar(PREVIOUS_OUT)) c("--previous", PREVIOUS_OUT)),
                  stdout = file.path(OUT, "logs", "postprocess_stdout.txt"), stderr = file.path(OUT, "logs", "postprocess_stderr.txt"))
cat(readLines(file.path(OUT, "logs", "postprocess_stdout.txt")), sep = "\\n")
if (status != 0) stop("Post-processing failed; see logs/postprocess_stderr.txt")"""),
    new_code_cell("""# 3b. Independent recalculation of 24 sample trees (own height, circle-fit DBH and convex crown hulls, no ITSMe)
status <- system2(PY, c("-I", file.path(WORK, "scripts", "verify_all163_independent.py"), "--out", OUT),
                  stdout = file.path(OUT, "logs", "independent_stdout.txt"), stderr = file.path(OUT, "logs", "independent_stderr.txt"))
if (status != 0) stop("Independent verification failed; see logs/independent_stderr.txt")
str(jsonlite::fromJSON(file.path(OUT, "logs", "independent_verification.json"))$summary)"""),
    new_code_cell("""# 3c. REPORT_DATA_REQUEST.md item 5: sensitivity.csv for 8 representative trees (DBH slice 3/5/6/10 cm, circle vs hull,
# height max vs 99th percentile, crown envelope vs slab-hull sums)
status <- system2(file.path(R.home("bin"), "Rscript"), c(file.path(WORK, "scripts", "sensitivity_all163.R"), OUT),
                  stdout = file.path(OUT, "logs", "sensitivity_stdout.txt"), stderr = file.path(OUT, "logs", "sensitivity_stderr.txt"))
if (status != 0) stop("Sensitivity step failed; see logs/sensitivity_stderr.txt")
print(read.csv(file.path(OUT, "results", "sensitivity.csv"))[, c("tree", "reported_dbh_cm", "dbh_circle_3cm_cm", "dbh_circle_10cm_cm", "height_max_m", "height_p99_m")])"""),
    new_code_cell("""# 4. Validation summary (written by the post-processing step)
v <- jsonlite::fromJSON(file.path(OUT, "logs", "validation.json"))
str(v, max.level = 1)
if (!isTRUE(v$all_checks_passed)) warning("Some validation checks failed; see logs/validation.json")"""),
]
nb = new_notebook(cells=cells, metadata={'kernelspec': {'name': 'info6003-ir', 'display_name': 'R (INFO6003 ITSMe)', 'language': 'R'},
                                         'language_info': {'name': 'R'}})
nbformat.write(nb, dst)
print(dst)
