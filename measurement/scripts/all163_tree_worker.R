# One-tree measurement for the all-163 batch. Sourced by each parallel worker; writes only into its tree folder.
# Height, lean-corrected DBH, crown classification and crown envelope reuse the code and parameters of
# ITSMe_HEIGHT_DBH_CROWN_VOLUME_TOP20_20261023.ipynb (cells 10, 14, 16, 18-20, 24) with plotting switched off, plus the
# user-agreed crown base (crown points below it are dropped) and, where the manifest says so, the 067 outline filter
# and the 103 ellipse / area-equivalent diameter. Every stage is attempted independently; failures are recorded.
suppressPackageStartupMessages({ library(ITSMe); library(jsonlite); library(digest) })

WORKER_VERSION <- "all163-worker-v2"  # v2: records peak R memory per tree
AXIS_SEARCH <- NULL
MIN_ARC <- 0.6; MAX_RMSE_M <- 0.04; SLICE_HEIGHTS <- c(1.1, 1.2, 1.3, 1.4, 1.5)

kasa <- function(x, y) {
  p <- unname(qr.solve(cbind(x, y, 1), x^2 + y^2)); cx <- p[1] / 2; cy <- p[2] / 2
  c(cx, cy, sqrt(p[3] + cx^2 + cy^2))
}
rotation_to_vertical <- function(v) {
  v <- v / sqrt(sum(v^2)); z <- c(0, 0, 1)
  k <- c(v[2] * z[3] - v[3] * z[2], v[3] * z[1] - v[1] * z[3], v[1] * z[2] - v[2] * z[1])
  s <- sqrt(sum(k^2)); c0 <- sum(v * z)
  if (s < 1e-12) return(diag(3))
  K <- matrix(c(0, -k[3], k[2], k[3], 0, -k[1], -k[2], k[1], 0), 3, byrow = TRUE)
  diag(3) + K + K %*% K * ((1 - c0) / s^2)
}
accept <- function(arc, R2, d) is.finite(d) && d > 0.03 && d < 2 && arc >= MIN_ARC &&
  sqrt(R2) <= min(MAX_RMSE_M, max(0.01, 0.1 * d))
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
ellipse_axes <- function(x, y) {
  if (length(x) < 8) return(c(NA_real_, NA_real_))
  a <- qr.solve(cbind(x * x, x * y, y * y, x, y), rep(1, length(x)))
  M <- matrix(c(a[1], a[2] / 2, a[2] / 2, a[3]), 2); w <- eigen(M, symmetric = TRUE)$values
  if (any(w <= 0)) return(c(NA_real_, NA_real_))
  c0 <- solve(2 * M, -a[4:5]); F <- 1 + drop(t(c0) %*% M %*% c0)
  sort(2 * sqrt(F / w))
}
num <- function(x) if (is.null(x) || !length(x)) NA_real_ else as.numeric(x[1])

envelope <- function(cp) {
  out <- list(points = nrow(cp))
  area <- tryCatch(ITSMe::projected_area_pc(pc = cp, concavity = 3, plot = FALSE), error = function(e) e)
  if (inherits(area, "error")) out$area_error <- conditionMessage(area) else out$area_m2 <- area$pa
  hull <- tryCatch(crown_convex_hull(cp), error = function(e) e)
  if (inherits(hull, "error")) { out$volume_error <- conditionMessage(hull); return(out) }
  out$volume_m3 <- hull$volume_m3; out$surface_m2 <- hull$surface_area_m2
  for (thickness in c(0.5, 1, 2)) {
    bins <- floor(cp$Z / thickness); vol <- 0
    for (k in seq(min(bins), max(bins))) {
      p <- cp[bins == k, ]; if (nrow(p) < 4) next
      h <- tryCatch(crown_convex_hull(p), error = function(e) NULL); if (!is.null(h)) vol <- vol + h$volume_m3
    }
    out[[paste0("slab_ratio_", thickness, "m")]] <- if (vol > 0) hull$volume_m3 / vol else NA_real_
  }
  out
}

measure_tree <- function(prep_path, root) {
  t_start <- Sys.time()
  invisible(gc(reset = TRUE))
  prep <- fromJSON(prep_path)
  dir <- dirname(prep_path); res_path <- file.path(dir, "result.json")
  stamp <- list(worker = WORKER_VERSION, worker_sha256 = digest(file = file.path(root, "measurement_pipeline/scripts/all163_tree_worker.R"), algo = "sha256"),
                prep_sha256 = digest(file = prep_path, algo = "sha256"))
  if (file.exists(res_path)) {
    old <- fromJSON(res_path)
    if (identical(old$stamp, stamp)) return(list(tree = prep$tree, status = "reused"))
  }
  # Helper functions go into the global environment so envelope() (defined at top level) can see them.
  source(file.path(root, "measurement_pipeline/scripts/crown_volume_metrics.R"), local = globalenv())
  set.seed(6003)
  r <- list(tree = prep$tree, review_sha256 = prep$review_sha256, stamp = stamp, errors = list(), warnings = character())
  wlog <- function(w) { r$warnings <<- c(r$warnings, conditionMessage(w)); invokeRestart("muffleWarning") }
  stage <- function(name, expr) withCallingHandlers(tryCatch(expr, error = function(e) { r$errors[[name]] <<- conditionMessage(e); NULL }), warning = wlog)
  stopifnot(identical(digest(file = prep$local_xyz_path, algo = "sha256"), prep$local_xyz_sha256))
  tree1 <- ITSMe::read_tree_pc(path = prep$local_xyz_path, samplefactor = 1)
  stopifnot(nrow(tree1) == prep$point_count)
  ground_ref <- data.frame(X = 0, Y = 0, Z = 0)
  low10 <- tree1[order(tree1$Z)[seq_len(min(10L, nrow(tree1)))], ]
  ground_lookup_radius <- max(1, max(abs(c(low10$X, low10$Y))) + 0.05)
  r$ground_lookup_radius_m <- ground_lookup_radius
  # Height (notebook cell 10)
  h1 <- stage("height", ITSMe::tree_height_pc(pc = tree1, dtm = ground_ref, r = ground_lookup_radius, plot = FALSE))
  if (!is.null(h1)) { r$itsme_height_m <- h1$h; r$itsme_ground_local_z_m <- h1$lp }
  # Crown classification (cell 14) and agreed crown base
  cl <- stage("crown_classification", ITSMe::classify_crown_pc(pc = tree1, dtm = ground_ref, r = ground_lookup_radius,
                                                             thresholdbranch = 1.5, plot = FALSE))
  if (!is.null(cl) && (is.null(cl$crownpoints) || nrow(cl$crownpoints) == 0)) {
    r$errors$crown_classification <- "ITSMe returned no crown points"; cl <- NULL
  }
  if (!is.null(cl)) {
    cp <- cl$crownpoints[, c("X", "Y", "Z")]
    r$auto_crown_min_z_m <- min(cp$Z); r$auto_crown_points <- nrow(cp)
    auto <- stage("auto_crown_envelope", envelope(cp)); if (!is.null(auto)) r$auto <- auto
  }
  # Crown above the agreed base: ITSMe crown points (standard). Only if ITSMe classification is unavailable, all tree
  # points above the base are used instead, under a distinct method label (reported as REVIEW downstream).
  has_base <- !is.null(prep$crown_base_m) && is.finite(num(prep$crown_base_m))
  if (!has_base) r$errors$crown_envelope <- "no crown base (rule found no continuous crown)"
  if (has_base) {
    if (!is.null(cl)) { src <- cp; r$crown_method <- "ITSME_CROWN_POINTS_ABOVE_AGREED_BASE" }
    else { src <- tree1[, c("X", "Y", "Z")]; r$crown_method <- "ALL_TREE_POINTS_ABOVE_AGREED_BASE (ITSMe crown classification unavailable)" }
    kept <- src[src$Z >= prep$crown_base_m, ]
    if (nrow(kept) >= 4) { base <- stage("crown_envelope", envelope(kept)); if (!is.null(base)) r$crown <- base }
    else r$errors$crown_envelope <- "fewer than 4 crown points above the agreed crown base"
  }
  # Lean-corrected DBH (cells 18-20)
  if (!is.null(prep$axis_o)) {
    stage("dbh", {
      o <- c(prep$axis_o[1], prep$axis_o[2], 0); v <- c(prep$axis_s[1], prep$axis_s[2], 1); v <- v / sqrt(sum(v^2))
      r$axis_lean_deg <- acos(v[3]) * 180 / pi
      P <- sweep(as.matrix(tree1[, c("X", "Y", "Z")]), 2, o) %*% t(rotation_to_vertical(v))
      rp <- data.frame(X = P[, 1], Y = P[, 2], Z = P[, 3])
      b <- rp[rp$Z >= 1.0 & rp$Z <= 1.6, ]; rho <- sqrt(b$X^2 + b$Y^2); rho <- rho[rho <= 0.8]
      if (length(rho) < 10) stop("TOO_FEW_POINTS_NEAR_AXIS")
      hcount <- tabulate(pmax(1, ceiling(rho / 0.01)), nbins = 80)
      hs <- stats::filter(hcount, rep(1 / 3, 3), sides = 2); hs[is.na(hs)] <- 0
      r$bark_radius_est_m <- (which.max(hs) - 0.5) * 0.01
      crop_r <- max(0.15, r$bark_radius_est_m + 0.10); r$crop_radius_m <- crop_r
      rc <- rp[sqrt(rp$X^2 + rp$Y^2) <= crop_r, ]
      shape_r <- max(crop_r, 2 * r$bark_radius_est_m + 0.10)
      es <- rp[abs(rp$Z - 1.3) <= 0.03 & sqrt(rp$X^2 + rp$Y^2) <= shape_r, ]
      ea <- tryCatch(ellipse_axes(es$X, es$Y), error = function(e) c(NA_real_, NA_real_))
      r$ellipse_minor_m <- ea[1]; r$ellipse_major_m <- ea[2]; r$area_equivalent_d_m <- sqrt(ea[1] * ea[2])
      r$outline_filter <- isTRUE(prep$dbh_outline_filter)
      if (r$outline_filter) { n0 <- nrow(rc); rc <- outline_filter(rc); r$outline_filter_removed_points <- n0 - nrow(rc) }
      r$dbh13_points <- sum(abs(rc$Z - 1.3) <= 0.03)
      d13 <- tryCatch(ITSMe::dbh_pc(pc = rc, dtm = ground_ref, r = 1.5, thresholdR2 = 0.001, slice_thickness = 0.06,
                                    functional = TRUE, concavity = 4, plot = FALSE), error = function(e) { r$errors$dbh_pc <<- conditionMessage(e); NULL })
      if (!is.null(d13)) { r$dbh13_m <- d13$dbh; r$fdbh13_m <- d13$fdbh; r$dbh13_arc <- d13$arc_coverage; r$dbh13_R2 <- d13$R2 }
      r$dbh13_passes <- !is.null(d13) && accept(d13$arc_coverage, d13$R2, d13$dbh)
      sl <- list(); acc <- c()
      for (h in SLICE_HEIGHTS) {
        s <- tryCatch(ITSMe::diameter_slice_pc(pc = rc, slice_height = h, slice_thickness = 0.06, dtm = ground_ref, r = 1.5,
                                               functional = TRUE, plot = FALSE), error = function(e) NULL)
        ok <- !is.null(s) && accept(s$arc_coverage, s$R2, s$diameter)
        sl[[length(sl) + 1]] <- list(height_m = h, diameter_m = if (is.null(s)) NA else s$diameter,
          fdiameter_m = if (is.null(s)) NA else s$fdiameter, arc = if (is.null(s)) NA else s$arc_coverage,
          rmse_m = if (is.null(s)) NA else sqrt(s$R2), points = sum(abs(rc$Z - h) <= 0.03), accepted = ok)
        if (ok) acc <- c(acc, s$diameter)
      }
      r$slices <- sl; r$accepted_slices <- length(acc)
      if (r$dbh13_passes) { r$dbh_m <- d13$dbh; r$dbh_method <- "1.3 m along stem" }
      else if (length(acc)) { r$dbh_m <- median(acc); r$dbh_method <- paste0("median of ", length(acc), " accepted slices, 1.1-1.5 m") }
      else r$dbh_method <- "no acceptable slice"
      if (length(acc) > 1) r$slice_range_m <- range(acc)
      TRUE
    })
  } else r$errors$dbh <- paste("no stem axis:", if (is.null(prep$axis_failure)) "unavailable" else prep$axis_failure)
  r$seconds <- as.numeric(difftime(Sys.time(), t_start, units = "secs"))
  g <- gc(); r$r_peak_memory_mb <- sum(g[, ncol(g)])   # R heap peak for this tree (max used, MB)
  r$pid <- Sys.getpid()
  writeLines(toJSON(r, auto_unbox = TRUE, digits = NA, null = "null", na = "null", pretty = TRUE), res_path)
  list(tree = prep$tree, status = if (length(r$errors)) "partial" else "ok", seconds = r$seconds)
}
