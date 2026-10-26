# Crown-envelope geometry only. Does not read, modify, or reassign tree inputs.
crown_convex_hull <- function(xyz) {
  if (!requireNamespace("geometry", quietly = TRUE)) stop("Install geometry in the project R library first.")
  if (is.data.frame(xyz)) xyz <- as.matrix(xyz[, c("X", "Y", "Z"), drop = FALSE])
  if (!is.matrix(xyz) || ncol(xyz) != 3L || !is.numeric(xyz)) stop("Expected numeric XYZ coordinates in metres.")
  if (any(!is.finite(xyz))) stop("Non-finite crown coordinates; review the input rather than silently dropping points.")
  original_count <- nrow(xyz)
  xyz <- unique(xyz)
  if (nrow(xyz) < 4L) stop("At least four distinct crown points are required.")
  origin <- colMeans(xyz)
  centred <- sweep(xyz, 2, origin)
  if (qr(centred)$rank < 3L) stop("Crown points are coplanar or collinear; a 3D volume is unavailable.")
  # No random jitter, point sampling, gap filling, or outlier removal.
  hull <- geometry::convhulln(centred, options = "Qt Tv", output.options = "FA")
  bbox_volume <- prod(apply(xyz, 2, function(x) diff(range(x))))
  if (!is.finite(hull$vol) || hull$vol <= 0 || hull$vol > bbox_volume * (1 + 1e-8)) {
    stop("Invalid hull volume; inspect geometry and numeric precision.")
  }
  used <- sort(unique(as.vector(hull$hull)))
  faces <- matrix(match(as.vector(hull$hull), used), ncol = 3)
  list(volume_m3 = hull$vol, surface_area_m2 = hull$area,
       input_points = original_count, unique_points = nrow(xyz),
       bbox_volume_m3 = bbox_volume, vertices = xyz[used, , drop = FALSE],
       faces = faces, centre_used_for_numerics = origin,
       method = "3D_CONVEX_HULL_CROWN_ENVELOPE_INCLUDING_INTERNAL_GAPS")
}

write_crown_hull_ply <- function(hull, path) {
  if (file.exists(path)) stop("Refusing to overwrite an existing hull export.")
  con <- file(path, open = "wt")
  on.exit(close(con))
  writeLines(c("ply", "format ascii 1.0",
    "comment Derived convex crown envelope; local XYZ metres, same frame as the prepared tree text input",
    "comment Includes internal gaps; not wood volume, foliage material volume, or a validated biological crown",
    paste("element vertex", nrow(hull$vertices)), "property double x", "property double y", "property double z",
    paste("element face", nrow(hull$faces)), "property list uchar int vertex_indices", "end_header"), con)
  writeLines(apply(hull$vertices, 1, function(p) paste(sprintf("%.12f", p), collapse = " ")), con)
  writeLines(apply(hull$faces - 1L, 1, function(f) paste(c(3L, f), collapse = " ")), con)
  invisible(path)
}

plot_crown_envelope <- function(crown, hull, path, tree_id) {
  png(path, width = 1800, height = 850, res = 150)
  on.exit(dev.off())
  par(mfrow = c(1, 3), mar = c(4, 4, 4, 1))
  xyz <- as.matrix(crown[, c("X", "Y", "Z")])
  # Plot all observations. Geometry also uses all observations.
  for (axes in list(c(1, 3), c(2, 3), c(1, 2))) {
    p <- xyz[, axes, drop = FALSE]
    boundary <- hull$vertices[, axes, drop = FALSE]
    ix <- chull(boundary)
    plot(p, pch = ".", col = "darkgreen", asp = 1,
         xlab = paste(colnames(xyz)[axes[1]], "(local m)"),
         ylab = paste(colnames(xyz)[axes[2]], "(local m)"),
         main = paste(tree_id, paste(colnames(xyz)[axes], collapse = "-"), "projection"))
    polygon(boundary[ix, , drop = FALSE], border = "darkorange", lwd = 2)
  }
  invisible(path)
}
