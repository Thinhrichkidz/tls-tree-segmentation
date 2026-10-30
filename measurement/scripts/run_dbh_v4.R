# Run the DBH v4 method on the saved v3 per-tree inputs and compare with v3. Read-only on v3; writes into OUT.
# Usage: Rscript run_dbh_v4.R <v3 output folder> <out folder> [workers]
args <- commandArgs(TRUE)
V3 <- args[1]; OUT <- args[2]; WORKERS <- if (length(args) >= 3) as.integer(args[3]) else 16L
library(data.table)
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
here <- dirname(normalizePath(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE)), winslash = "/"))
trees <- list.files(file.path(V3, "per_tree"))

work <- function(t) {
  suppressPackageStartupMessages({ library(jsonlite); library(data.table) })
  src <- readLines(file.path(here, "all163_tree_worker.R")); src <- src[!grepl("^suppressPackageStartupMessages", src)]
  eval(parse(text = src), envir = globalenv()); source(file.path(here, "dbh_v4.R"), local = globalenv())
  d <- file.path(V3, "per_tree", t); prep <- fromJSON(file.path(d, "prep.json")); r3 <- fromJSON(file.path(d, "result.json"))
  g <- function(x) if (is.null(x) || !length(x) || is.na(suppressWarnings(as.numeric(x[1])))) NA_real_ else as.numeric(x[1])
  xyz <- as.data.frame(fread(file.path(d, paste0(t, "_local_xyz.txt")), header = TRUE))[, 1:3]; names(xyz) <- c("X", "Y", "Z")
  has_axis <- !is.null(prep$axis_o)
  if (has_axis) {
    o <- c(prep$axis_o[1], prep$axis_o[2], 0); v <- c(prep$axis_s[1], prep$axis_s[2], 1); v <- v / sqrt(sum(v^2))
    P <- sweep(as.matrix(xyz), 2, o) %*% t(rotation_to_vertical(v)); rp <- data.frame(X = P[, 1], Y = P[, 2], Z = P[, 3]); lean <- acos(v[3]) * 180 / pi
  } else { rp <- xyz; lean <- NA_real_ }   # no axis: assume vertical through the stem foot (local origin)
  f <- joint_fit(rp)
  list(tree = t, has_axis = has_axis, lean = lean, v3_dbh_cm = g(r3$dbh_m) * 100, v3_method = if (is.null(r3$dbh_method)) NA else r3$dbh_method,
       v4_d_cm = if (is.null(f)) NA else f$d * 100, v4_arc = if (is.null(f)) NA else f$arc, v4_rmse_cm = if (is.null(f)) NA else f$rmse * 100,
       v4_n = if (is.null(f)) NA else f$n, v4_spread = if (is.null(f)) NA else f$spread, v4_gate = v4_gate(f),
       cx = if (is.null(f)) NA else f$cx, cy = if (is.null(f)) NA else f$cy)
}
cl <- parallel::makeCluster(WORKERS)
parallel::clusterExport(cl, c("V3", "here", "work"))
res <- parallel::parLapplyLB(cl, trees, function(t) tryCatch(work(t), error = function(e) list(tree = t, v4_gate = paste("error:", conditionMessage(e)))), chunk.size = 1)
parallel::stopCluster(cl)
df <- rbindlist(res, fill = TRUE)
fwrite(df, file.path(OUT, "dbh_v4_vs_v3.csv"))
cat("v3 has DBH:", sum(!is.na(df$v3_dbh_cm)), "| v4 gate ok:", sum(df$v4_gate == "ok", na.rm = TRUE), "\n")
print(table(df$v4_gate, has_v3 = !is.na(df$v3_dbh_cm)))
