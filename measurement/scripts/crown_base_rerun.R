# Crown area and convex crown envelope above the user-agreed crown base, for the 20 test trees.
# Reads each tree's saved ITSMe crown classification (unchanged run, current source version), keeps crown points with
# Z >= agreed base (local frame: Z = height above stem-foot ground), then repeats the notebook's crown stages:
# projected_area_pc(concavity = 3), crown_convex_hull, 0.5/1/2 m slab sensitivity. Writes only into the batch folder.
args <- commandArgs(trailingOnly = TRUE)
BATCH <- normalizePath(args[1], winslash = "/", mustWork = TRUE)
ROOT <- "G:/22083142/outputs/WSL_ML2A/55x55/3cm/Codex_help"
suppressPackageStartupMessages({ library(ITSMe); library(ggplot2) })
source(file.path(ROOT, "measurement_pipeline/scripts/crown_volume_metrics.R"))
set.seed(6003); options(warn = 1)
bases <- read.csv(file.path(BATCH, "agreed_crown_bases.csv"), stringsAsFactors = FALSE)
out <- list(); slabs <- list()
for (i in seq_len(nrow(bases))) {
  b <- bases[i, ]; tid <- b$tree; dir <- file.path(BATCH, tid); dir.create(dir)
  rds <- file.path(ROOT, b$crown_rds)
  stopifnot(identical(digest::digest(file = rds, algo = "sha256"), b$crown_rds_sha256))
  q <- read.csv(file.path(ROOT, b$run_dir, "batch_quality_diagnostics.csv"))
  cp_all <- readRDS(rds)$crownpoints
  # The saved crown points must be in the frame the run reported (same lowest crown point).
  stopifnot(abs(min(cp_all$Z) - q$crown_min_z_m) < 1e-6)
  cp <- cp_all[cp_all$Z >= b$crown_base_m, c("X", "Y", "Z")]
  row <- list(tree = tid, crown_base_m = b$crown_base_m, base_source = b$base_source,
              crown_points_before = nrow(cp_all), crown_points_kept = nrow(cp))
  area <- tryCatch(ITSMe::projected_area_pc(pc = cp, concavity = 3, plot = TRUE), error = function(e) e)
  if (inherits(area, "error")) row$area_error <- conditionMessage(area) else {
    row$crown_area_m2 <- area$pa
    ggsave(file.path(dir, paste0(tid, "_crown_area.png")), plot = area$plot, width = 7, height = 7)
  }
  hull <- tryCatch(crown_convex_hull(cp), error = function(e) e)
  if (inherits(hull, "error")) row$volume_error <- conditionMessage(hull) else {
    row$crown_volume_m3 <- hull$volume_m3; row$crown_surface_area_m2 <- hull$surface_area_m2
    write_crown_hull_ply(hull, file.path(dir, paste0(tid, "_crown_convex_hull_local.ply")))
    plot_crown_envelope(cp, hull, file.path(dir, paste0(tid, "_crown_envelope_projections.png")), tid)
    for (thickness in c(0.5, 1, 2)) {
      bins <- floor(cp$Z / thickness); vol <- 0; sparse <- 0L; fail <- 0L
      for (k in seq(min(bins), max(bins))) {
        p <- cp[bins == k, ]
        if (nrow(p) < 4) { sparse <- sparse + 1L; next }
        h <- tryCatch(crown_convex_hull(p), error = function(e) NULL)
        if (is.null(h)) fail <- fail + 1L else vol <- vol + h$volume_m3
      }
      slabs[[length(slabs) + 1]] <- data.frame(tree = tid, thickness_m = thickness, sum_separate_slab_hulls_m3 = vol,
        sparse_or_empty_slabs = sparse, degenerate_slabs = fail, full_envelope_to_slab_ratio = if (vol > 0) hull$volume_m3 / vol else NA)
      if (thickness == 1) row$full_envelope_to_1m_slab_ratio <- if (vol > 0) hull$volume_m3 / vol else NA
    }
  }
  # Side view: all ITSMe crown points, grey below the agreed base (dropped), green kept.
  cp_all$kept <- cp_all$Z >= b$crown_base_m
  g <- ggplot(cp_all, aes(X, Z, colour = kept)) + geom_point(size = 0.05, shape = ".") + coord_fixed() +
    scale_colour_manual(values = c(`FALSE` = "grey70", `TRUE` = "darkgreen"), labels = c("dropped (below base)", "crown")) +
    geom_hline(yintercept = b$crown_base_m, colour = "blue") +
    labs(title = sprintf("%s: crown base %.2f m (%s)", tid, b$crown_base_m, b$base_source), colour = NULL)
  ggsave(file.path(dir, paste0(tid, "_crown_base_side_view.png")), plot = g, width = 6, height = 8)
  out[[tid]] <- row
  cat(sprintf("%s base %.2f m: %d of %d crown points kept, area %s m2, envelope %s m3\n", tid, b$crown_base_m, nrow(cp),
              nrow(cp_all), format(row$crown_area_m2, digits = 5), format(row$crown_volume_m3, digits = 6)))
}
res <- data.table::rbindlist(lapply(out, as.list), fill = TRUE)
data.table::fwrite(res, file.path(BATCH, "crown_results.csv"))
data.table::fwrite(do.call(rbind, slabs), file.path(BATCH, "crown_slab_sensitivity.csv"))
writeLines(capture.output(sessionInfo()), file.path(BATCH, "session_info.txt"))
