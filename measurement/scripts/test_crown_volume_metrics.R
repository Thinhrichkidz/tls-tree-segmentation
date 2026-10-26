args <- commandArgs(trailingOnly = TRUE)
source(args[1])
cube <- as.matrix(expand.grid(X = c(0, 2), Y = c(0, 3), Z = c(0, 4)))
h <- crown_convex_hull(cube)
stopifnot(abs(h$volume_m3 - 24) < 1e-10, abs(h$surface_area_m2 - 52) < 1e-10)
# Interior points and repeated observations must not change an envelope.
expanded <- rbind(cube, cube, c(1, 1.5, 2))
stopifnot(abs(crown_convex_hull(expanded)$volume_m3 - 24) < 1e-10)
# Volume must be independent of the local origin and rigid rotation.
shifted <- sweep(cube, 2, c(261350, 6264474, 698), "+")
stopifnot(abs(crown_convex_hull(shifted)$volume_m3 - 24) < 1e-8)
a <- 0.37
rotation <- matrix(c(cos(a), -sin(a), 0, sin(a), cos(a), 0, 0, 0, 1), 3, byrow = TRUE)
stopifnot(abs(crown_convex_hull(cube %*% rotation)$volume_m3 - 24) < 1e-10)
tetrahedron <- rbind(c(0, 0, 0), c(1, 0, 0), c(0, 1, 0), c(0, 0, 1))
stopifnot(abs(crown_convex_hull(tetrahedron)$volume_m3 - 1 / 6) < 1e-10)
fails <- function(expr) inherits(tryCatch(expr, error = identity), "error")
stopifnot(fails(crown_convex_hull(cube[1:3, ])),
          fails(crown_convex_hull(cbind(cube[, 1:2], 0))),
          fails(crown_convex_hull(rbind(cube, c(NA, 1, 1)))))
# The exported mesh must retain valid triangular indices and the same enclosed volume.
mesh_path <- tempfile(fileext = ".ply")
write_crown_hull_ply(h, mesh_path)
stopifnot(fails(write_crown_hull_ply(h, mesh_path)))
lines <- readLines(mesh_path)
start <- match("end_header", lines)
vertices <- as.matrix(read.table(text = paste(lines[start + seq_len(nrow(h$vertices))], collapse = "\n")))
faces <- as.matrix(read.table(text = paste(tail(lines, nrow(h$faces)), collapse = "\n")))
stopifnot(all(faces[, 1] == 3), all(faces[, -1] >= 0), all(faces[, -1] < nrow(vertices)))
stopifnot(abs(crown_convex_hull(vertices)$volume_m3 - 24) < 1e-10)
# Sum tetrahedra from each surface triangle to an interior point: checks face connectivity.
centre <- colMeans(vertices)
mesh_volume <- sum(apply(faces[, -1, drop = FALSE] + 1L, 1, function(f) {
  abs(det(sweep(vertices[f, , drop = FALSE], 2, centre))) / 6
}))
stopifnot(abs(mesh_volume - 24) < 1e-10)
unlink(mesh_path)
cat("PASS: known cube/tetrahedron volumes, duplicates/interior points, translation/rotation invariance, invalid geometry, mesh round trip.\n")
