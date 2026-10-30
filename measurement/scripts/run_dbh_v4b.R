# Test the v4b fallbacks (small-stem RMSE floor, RANSAC trunk circle) on saved per-tree inputs; compare with v3 where v3 has a DBH.
# Usage: Rscript run_dbh_v4b.R <all-163 output folder with per_tree> <out folder> [workers]
args <- commandArgs(TRUE)
SRC <- args[1]; OUT <- args[2]; WORKERS <- if (length(args) >= 3) as.integer(args[3]) else 16L
library(data.table)
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
here <- dirname(normalizePath(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE)), winslash = "/"))
trees <- list.files(file.path(SRC, "per_tree"))
work <- function(t) {
  suppressPackageStartupMessages({ library(jsonlite); library(data.table) })
  src <- readLines(file.path(here, "all163_tree_worker.R")); src <- src[!grepl("^suppressPackageStartupMessages", src)]
  eval(parse(text = src), envir = globalenv()); source(file.path(here, "dbh_v4.R"), local = globalenv())
  d <- file.path(SRC, "per_tree", t); prep <- fromJSON(file.path(d, "prep.json")); r3 <- fromJSON(file.path(d, "result.json"))
  g <- function(x) if (is.null(x) || !length(x) || is.na(suppressWarnings(as.numeric(x[1])))) NA_real_ else as.numeric(x[1])
  xyz <- as.data.frame(fread(file.path(d, paste0(t, "_local_xyz.txt")), header = TRUE))[, 1:3]; names(xyz) <- c("X", "Y", "Z")
  if (!is.null(prep$axis_o)) {
    o <- c(prep$axis_o[1], prep$axis_o[2], 0); v <- c(prep$axis_s[1], prep$axis_s[2], 1); v <- v / sqrt(sum(v^2))
    P <- sweep(as.matrix(xyz), 2, o) %*% t(rotation_to_vertical(v)); rp <- data.frame(X = P[, 1], Y = P[, 2], Z = P[, 3])
  } else rp <- xyz
  f <- joint_fit(rp); fr <- ransac_fit(rp)
  data.frame(tree = t, has_axis = !is.null(prep$axis_o), v3_dbh_cm = g(r3$dbh_m) * 100,
             v4_cm = if (is.null(f)) NA else f$d * 100, v4_gate = v4_gate(f), v4_rmse_cm = if (is.null(f)) NA else 100 * f$rmse,
             v4_arc = if (is.null(f)) NA else f$arc, floor_gate = v4b_floor_gate(f),
             ransac_cm = if (is.null(fr)) NA else fr$d * 100, ransac_gate = ransac_gate(fr), ransac_arc = if (is.null(fr)) NA else fr$arc,
             ransac_n = if (is.null(fr)) NA else fr$n, ransac_band = if (is.null(fr)) NA else fr$band_points,
             ransac_spread = if (is.null(fr)) NA else fr$spread, ransac_inside = if (is.null(fr)) NA else fr$inside_ratio)
}
cl <- parallel::makeCluster(WORKERS)
parallel::clusterExport(cl, c("SRC", "here", "work"))
res <- parallel::parLapplyLB(cl, trees, function(t) tryCatch(work(t), error = function(e) data.frame(tree = t, v4_gate = paste("error:", conditionMessage(e)))), chunk.size = 1)
parallel::stopCluster(cl)
df <- rbindlist(res, fill = TRUE)
fwrite(df, file.path(OUT, "dbh_v4b_test.csv"))
cat("done", nrow(df), "\n")
