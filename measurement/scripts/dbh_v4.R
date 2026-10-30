# DBH v4: joint multi-slice robust circle fit for stems whose single 1.3 m slice fails the v3 rules (arc < 60 %, no axis, bad RMSE).
# Does not replace the v3 DBH. A v3 value that passed stays as reported; v4 only supplies a labelled ESTIMATED value where v3 has none.
# Input: points already rotated so the stem axis is vertical through (0, 0) (same frame as all163_tree_worker.R, rp / rc).

V4_BAND <- c(1.1, 1.5)         # pooled height band (m); lean correction makes slices overlay
V4_MIN_ARC <- 0.40             # pooled angular coverage (10-degree bins); v3 required 0.60 on one 6 cm slice
V4_MIN_INLIERS <- 25
V4_MAX_SLICE_SPREAD <- 0.15    # (max - min) / median of per-slice radii at fixed centre
V4_CENTRE_SD_M <- 0.05         # weak prior: centre stays near the fitted stem axis

huber_rho <- function(r, k) ifelse(abs(r) <= k, 0.5 * r^2, k * (abs(r) - 0.5 * k))

fit_circle_robust <- function(x, y, centre0 = c(0, 0), centre_sd = V4_CENTRE_SD_M, k = 0.01) {
  p0 <- tryCatch(kasa(x, y), error = function(e) c(mean(x), mean(y), sd(x) + sd(y)))
  if (!all(is.finite(p0))) p0 <- c(mean(x), mean(y), sd(x) + sd(y))
  obj <- function(p) sum(huber_rho(sqrt((x - p[1])^2 + (y - p[2])^2) - p[3], k)) +
    0.5 * sum((p[1:2] - centre0)^2) / centre_sd^2 * k^2 * 4
  best <- NULL
  for (s in list(p0, c(centre0, max(0.05, p0[3])))) {
    o <- tryCatch(optim(s, obj, method = "Nelder-Mead", control = list(reltol = 1e-10, maxit = 600)), error = function(e) NULL)
    if (!is.null(o) && (is.null(best) || o$value < best$value)) best <- o
  }
  if (is.null(best)) return(NULL)
  best$par
}

arc_fraction <- function(x, y, cx, cy, bin_deg = 10) {
  a <- (atan2(y - cy, x - cx) * 180 / pi + 360) %% 360
  length(unique(floor(a / bin_deg))) / (360 / bin_deg)
}

# Radial-histogram stem-radius estimate in the band (same rule as the v3 worker); used to crop away neighbours and understorey.
bark_radius_est <- function(rp, band = V4_BAND) {
  b <- rp[rp$Z >= 1.0 & rp$Z <= 1.6, ]; rho <- sqrt(b$X^2 + b$Y^2); rho <- rho[rho <= 0.8]
  if (length(rho) < 10) return(NA_real_)
  hs <- stats::filter(tabulate(pmax(1, ceiling(rho / 0.01)), nbins = 80), rep(1 / 3, 3), sides = 2); hs[is.na(hs)] <- 0
  (which.max(hs) - 0.5) * 0.01
}

# Fit one circle to pooled band points, trim outliers, refit. Returns NULL when not enough points.
joint_fit <- function(rp, band = V4_BAND, centre0 = c(0, 0), max_r = NULL) {
  bark <- bark_radius_est(rp)
  if (is.null(max_r)) max_r <- if (is.finite(bark)) max(0.15, bark + 0.10) else 0.9
  b <- rp[rp$Z >= band[1] & rp$Z <= band[2] & sqrt(rp$X^2 + rp$Y^2) <= max_r, ]
  if (nrow(b) < 12) return(NULL)
  p <- fit_circle_robust(b$X, b$Y, centre0); if (is.null(p)) return(NULL)
  for (it in 1:2) {  # trim to the stem surface: drop branch stubs / neighbours / understorey
    res <- sqrt((b$X - p[1])^2 + (b$Y - p[2])^2) - p[3]
    keep <- abs(res) <= max(0.015, 2.5 * 1.4826 * median(abs(res - median(res))))
    if (sum(keep) < 12) break
    p2 <- fit_circle_robust(b$X[keep], b$Y[keep], centre0); if (is.null(p2)) break
    p <- p2; b <- b[keep, ]
  }
  res <- sqrt((b$X - p[1])^2 + (b$Y - p[2])^2) - p[3]
  rc0 <- rp[rp$Z >= 1.0 & rp$Z <= 1.6, ]   # radial-histogram radius around the fitted centre (v4b check; v4 uses the axis-centred one)
  rho <- sqrt((rc0$X - p[1])^2 + (rc0$Y - p[2])^2); rho <- rho[rho <= 0.8]
  bark_c <- if (length(rho) >= 10) { hs <- stats::filter(tabulate(pmax(1, ceiling(rho / 0.01)), nbins = 80), rep(1 / 3, 3), sides = 2)
                                     hs[is.na(hs)] <- 0; (which.max(hs) - 0.5) * 0.01 } else NA_real_
  slices <- NULL
  for (h in seq(band[1] + 0.03, band[2] - 0.03, by = 0.1)) {   # radius per 6 cm slice at the joint centre
    s <- b[abs(b$Z - h) <= 0.03, ]
    if (nrow(s) >= 8) slices <- c(slices, median(sqrt((s$X - p[1])^2 + (s$Y - p[2])^2)))
  }
  list(cx = p[1], cy = p[2], r = p[3], d = 2 * p[3], n = nrow(b), rmse = sqrt(mean(res^2)), bark = bark, bark_c = bark_c,
       arc = arc_fraction(b$X, b$Y, p[1], p[2]), slice_r = slices,
       spread = if (length(slices) >= 2) (max(slices) - min(slices)) / median(slices) else NA_real_)
}

v4_gate <- function(f) {
  if (is.null(f)) return("no fit")
  if (f$n < V4_MIN_INLIERS) return("too few inlier points")
  if (!is.finite(f$d) || f$d < 0.05 || f$d > 1.6) return("diameter outside 5-160 cm")
  if (f$arc < V4_MIN_ARC) return("pooled arc below limit")
  if (f$rmse > min(MAX_RMSE_M, max(0.01, 0.1 * f$d))) return("RMSE above limit")
  if (!is.na(f$spread) && f$spread > V4_MAX_SLICE_SPREAD) return("slice radii inconsistent")
  if (is.finite(f$bark) && abs(f$r - f$bark) > max(0.03, 0.25 * f$r)) return("radius disagrees with radial histogram")
  "ok"
}

# ---------------- v4b fallbacks (28 Oct 2026; used only where v4_gate fails, released only for user-reviewed NORMAL trees) -------------
# (a) Small-stem RMSE floor: with ~3 cm point spacing, ~1.5 cm surface noise is normal, so 10 % of a 10 cm stem (1 cm) is stricter
#     than the data allow. With a well-covered stem (pooled arc >= 0.70) the RMSE limit becomes at least V4B_RMSE_FLOOR_M.
# (b) RANSAC trunk circle: for cluttered bands (branches, understorey, neighbour stems inside the crop) find the circle that most
#     band points lie on, refit it on those points only, and accept it only with good arc cover and consistent slices.
V4B_RMSE_FLOOR_M <- 0.02; V4B_FLOOR_MIN_ARC <- 0.70
V4B_RANSAC_TOL_M <- 0.015; V4B_RANSAC_ITERS <- 3000; V4B_RANSAC_MAX_R <- 0.6; V4B_RANSAC_MAX_OFFSET_M <- 0.5
V4B_RANSAC_MIN_ARC <- 0.60; V4B_RANSAC_MIN_INLIERS <- 30
V4B_RANSAC_MAX_INSIDE <- 0.10   # band points clearly inside the circle / inliers: a real trunk section is hollow to the scanner;
                                # applied to every RANSAC candidate (most points on a hollow circle wins) and again after refitting

v4b_floor_gate <- function(f) {
  if (is.null(f)) return("no fit")
  if (f$arc < V4B_FLOOR_MIN_ARC) return("pooled arc below 0.70 (floor not applicable)")
  if (f$n < V4_MIN_INLIERS) return("too few inlier points")
  if (!is.finite(f$d) || f$d < 0.05 || f$d > 1.6) return("diameter outside 5-160 cm")
  if (f$rmse > max(V4B_RMSE_FLOOR_M, min(MAX_RMSE_M, max(0.01, 0.1 * f$d)))) return("RMSE above floor limit")
  if (!is.na(f$spread) && f$spread > V4_MAX_SLICE_SPREAD) return("slice radii inconsistent")
  if (is.finite(f$bark_c) && abs(f$r - f$bark_c) > max(0.03, 0.25 * f$r)) return("radius disagrees with radial histogram")
  "ok"
}

circle3 <- function(x, y) {
  A <- cbind(x, y, 1); if (abs(det(A)) < 1e-10) return(NULL)
  p <- solve(A, x^2 + y^2); cx <- p[1] / 2; cy <- p[2] / 2; c(cx, cy, sqrt(p[3] + cx^2 + cy^2))
}

ransac_fit <- function(rp, band = V4_BAND, centre0 = c(0, 0), seed = 6003) {
  b <- rp[rp$Z >= band[1] & rp$Z <= band[2] & sqrt((rp$X - centre0[1])^2 + (rp$Y - centre0[2])^2) <= V4B_RANSAC_MAX_OFFSET_M + V4B_RANSAC_MAX_R, ]
  if (nrow(b) < 12) return(NULL)
  old <- if (exists(".Random.seed", globalenv())) get(".Random.seed", globalenv()) else NULL
  set.seed(seed); on.exit(if (!is.null(old)) assign(".Random.seed", old, globalenv()))
  x <- b$X; y <- b$Y; best <- NULL; best_n <- 0
  for (i in seq_len(V4B_RANSAC_ITERS)) {
    s <- sample.int(length(x), 3); p <- circle3(x[s], y[s])
    if (is.null(p) || !is.finite(p[3]) || p[3] < 0.025 || p[3] > V4B_RANSAC_MAX_R || sqrt(sum((p[1:2] - centre0)^2)) > V4B_RANSAC_MAX_OFFSET_M) next
    dd <- sqrt((x - p[1])^2 + (y - p[2])^2)
    k <- sum(abs(dd - p[3]) <= V4B_RANSAC_TOL_M)
    if (k > best_n && sum(dd < p[3] - 3 * V4B_RANSAC_TOL_M) <= V4B_RANSAC_MAX_INSIDE * k) { best_n <- k; best <- p }
  }
  if (is.null(best)) return(NULL)
  inl <- abs(sqrt((x - best[1])^2 + (y - best[2])^2) - best[3]) <= 2 * V4B_RANSAC_TOL_M
  bi <- b[inl, ]; p <- fit_circle_robust(bi$X, bi$Y, best[1:2]); if (is.null(p)) p <- best
  res <- sqrt((bi$X - p[1])^2 + (bi$Y - p[2])^2) - p[3]
  slices <- NULL
  for (h in seq(band[1] + 0.03, band[2] - 0.03, by = 0.1)) {
    s <- bi[abs(bi$Z - h) <= 0.03, ]
    if (nrow(s) >= 8) slices <- c(slices, median(sqrt((s$X - p[1])^2 + (s$Y - p[2])^2)))
  }
  inside <- sum(sqrt((b$X - p[1])^2 + (b$Y - p[2])^2) < p[3] - 3 * V4B_RANSAC_TOL_M)
  list(cx = p[1], cy = p[2], r = p[3], d = 2 * p[3], n = nrow(bi), band_points = nrow(b), rmse = sqrt(mean(res^2)),
       inside_ratio = inside / nrow(bi),
       arc = arc_fraction(bi$X, bi$Y, p[1], p[2]), slice_r = slices,
       spread = if (length(slices) >= 2) (max(slices) - min(slices)) / median(slices) else NA_real_)
}

ransac_gate <- function(f) {
  if (is.null(f)) return("no fit")
  if (f$n < V4B_RANSAC_MIN_INLIERS) return("too few inlier points")
  if (!is.finite(f$d) || f$d < 0.05 || f$d > 1.2) return("diameter outside 5-120 cm")
  if (f$arc < V4B_RANSAC_MIN_ARC) return("inlier arc below 0.60")
  if (f$inside_ratio > V4B_RANSAC_MAX_INSIDE) return("points inside the circle (circle encloses the trunk or clutter)")
  if (is.na(f$spread)) return("fewer than 2 slices to check consistency")
  if (f$spread > V4_MAX_SLICE_SPREAD) return("slice radii inconsistent")
  "ok"
}
