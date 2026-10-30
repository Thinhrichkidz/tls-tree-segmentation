# Hold-out test of DBH v4: take trees whose v3 DBH came from a clean full-arc 1.3 m fit, hide part of the stem (keep only an angular
# window), refit, and compare with the full-arc v3 value. Also reports the plain Kasa circle on the same window as a baseline.
# Usage: Rscript holdout_dbh_v4.R <v3 output folder> <out folder> [workers]
args <- commandArgs(TRUE)
V3 <- args[1]; OUT <- args[2]; WORKERS <- if (length(args) >= 3) as.integer(args[3]) else 16L
library(data.table)
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
here <- dirname(normalizePath(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE)), winslash = "/"))
trees <- list.files(file.path(V3, "per_tree"))
WINDOWS_DEG <- c(270, 180, 120)   # visible arc in degrees, three start angles each

work <- function(t) {
  suppressPackageStartupMessages({ library(jsonlite); library(data.table) })
  src <- readLines(file.path(here, "all163_tree_worker.R")); src <- src[!grepl("^suppressPackageStartupMessages", src)]
  eval(parse(text = src), envir = globalenv()); source(file.path(here, "dbh_v4.R"), local = globalenv())
  d <- file.path(V3, "per_tree", t); prep <- fromJSON(file.path(d, "prep.json")); r3 <- fromJSON(file.path(d, "result.json"))
  if (!identical(r3$dbh_method, "1.3 m along stem") || is.null(prep$axis_o)) return(NULL)
  ref <- as.numeric(r3$dbh_m[1]) * 100
  xyz <- as.data.frame(fread(file.path(d, paste0(t, "_local_xyz.txt")), header = TRUE))[, 1:3]; names(xyz) <- c("X", "Y", "Z")
  o <- c(prep$axis_o[1], prep$axis_o[2], 0); v <- c(prep$axis_s[1], prep$axis_s[2], 1); v <- v / sqrt(sum(v^2))
  P <- sweep(as.matrix(xyz), 2, o) %*% t(rotation_to_vertical(v)); rp <- data.frame(X = P[, 1], Y = P[, 2], Z = P[, 3])
  cx <- as.numeric(r3$bark_radius_est_m[1])   # only used to centre the angular window on the stem
  ang <- (atan2(rp$Y, rp$X) * 180 / pi + 360) %% 360
  out <- list()
  for (w in WINDOWS_DEG) for (start in c(0, 120, 240)) {
    keep <- ((ang - start) %% 360) <= w
    rw <- rp[keep, ]
    f <- joint_fit(rw)
    band <- rw[rw$Z >= 1.2 & rw$Z <= 1.4 & sqrt(rw$X^2 + rw$Y^2) <= max(0.15, cx + 0.1), ]
    kd <- if (nrow(band) >= 5) 200 * tryCatch(kasa(band$X, band$Y)[3], error = function(e) NA) else NA
    out[[length(out) + 1]] <- data.frame(tree = t, ref_cm = ref, window_deg = w, start = start,
      v4_cm = if (is.null(f)) NA else f$d * 100, v4_gate = v4_gate(f), kasa_cm = kd)
  }
  rbindlist(out)
}
cl <- parallel::makeCluster(WORKERS)
parallel::clusterExport(cl, c("V3", "here", "work", "WINDOWS_DEG"))
res <- parallel::parLapplyLB(cl, trees, function(t) tryCatch(work(t), error = function(e) NULL), chunk.size = 1)
parallel::stopCluster(cl)
df <- rbindlist(res, fill = TRUE)
df[, v4_err_pct := 100 * (v4_cm - ref_cm) / ref_cm][, kasa_err_pct := 100 * (kasa_cm - ref_cm) / ref_cm]
fwrite(df, file.path(OUT, "dbh_v4_holdout.csv"))
s <- df[, .(trees = uniqueN(tree), runs = .N, gate_pass_pct = round(100 * mean(v4_gate == "ok"), 1),
            v4_median_abs_err_pct_all = round(median(abs(v4_err_pct), na.rm = TRUE), 2),
            v4_median_abs_err_pct_passed = round(median(abs(v4_err_pct[v4_gate == "ok"]), na.rm = TRUE), 2),
            v4_p90_abs_err_pct_passed = round(quantile(abs(v4_err_pct[v4_gate == "ok"]), 0.9, na.rm = TRUE), 2),
            kasa_median_abs_err_pct = round(median(abs(kasa_err_pct), na.rm = TRUE), 2),
            kasa_p90_abs_err_pct = round(quantile(abs(kasa_err_pct), 0.9, na.rm = TRUE), 2)), by = window_deg]
print(s)
fwrite(s, file.path(OUT, "dbh_v4_holdout_summary.csv"))
