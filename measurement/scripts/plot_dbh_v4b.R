# Top-view plots of the 1.1-1.5 m band for the user-reviewed NORMAL trees: all band points (grey), v4 fit (red dashed),
# v4b fit (blue: FLOOR = v4 fit accepted with the small-stem floor, RANSAC = trunk circle). For visual checking only.
# Usage: Rscript plot_dbh_v4b.R <all-163 output folder with per_tree> <user_dbh_review.csv> <out png>
args <- commandArgs(TRUE)
SRC <- args[1]; REVIEW <- args[2]; PNG <- args[3]
suppressPackageStartupMessages({ library(jsonlite); library(data.table) })
here <- dirname(normalizePath(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE)), winslash = "/"))
src <- readLines(file.path(here, "all163_tree_worker.R")); src <- src[!grepl("^suppressPackageStartupMessages", src)]
eval(parse(text = src), envir = globalenv()); source(file.path(here, "dbh_v4.R"), local = globalenv())
trees <- fread(REVIEW)[group == "NORMAL", tree]
png(PNG, width = 2800, height = 1700, res = 110); par(mfrow = c(4, 7), mar = c(2, 2, 3, 1))
circ <- function(cx, cy, r, ...) { a <- seq(0, 2 * pi, length.out = 200); lines(cx + r * cos(a), cy + r * sin(a), ...) }
for (t in trees) {
  d <- file.path(SRC, "per_tree", t); prep <- fromJSON(file.path(d, "prep.json"))
  xyz <- as.data.frame(fread(file.path(d, paste0(t, "_local_xyz.txt")), header = TRUE))[, 1:3]; names(xyz) <- c("X", "Y", "Z")
  if (!is.null(prep$axis_o)) {
    o <- c(prep$axis_o[1], prep$axis_o[2], 0); v <- c(prep$axis_s[1], prep$axis_s[2], 1); v <- v / sqrt(sum(v^2))
    P <- sweep(as.matrix(xyz), 2, o) %*% t(rotation_to_vertical(v)); rp <- data.frame(X = P[, 1], Y = P[, 2], Z = P[, 3])
  } else rp <- xyz
  f <- joint_fit(rp); fr <- ransac_fit(rp)
  pick <- if (v4b_floor_gate(f) == "ok") "FLOOR" else if (ransac_gate(fr) == "ok") "RANSAC" else "none"
  b <- rp[rp$Z >= 1.1 & rp$Z <= 1.5 & sqrt(rp$X^2 + rp$Y^2) <= 1.1, ]
  ctr <- if (pick == "RANSAC") c(fr$cx, fr$cy) else if (!is.null(f)) c(f$cx, f$cy) else c(0, 0)
  lim <- 0.7
  plot(b$X, b$Y, pch = 16, cex = 0.35, col = "grey45", asp = 1, xlim = ctr[1] + c(-lim, lim), ylim = ctr[2] + c(-lim, lim), xlab = "", ylab = "",
       main = sprintf("%s %s\nv4b: %s", t, if (is.null(prep$axis_o)) "(no axis)" else "",
                      if (pick == "FLOOR") sprintf("FLOOR %.1f cm", f$d * 100) else if (pick == "RANSAC") sprintf("RANSAC %.1f cm", fr$d * 100) else "none"),
       cex.main = 1.0, col.main = if (pick == "none") "grey30" else "navy")
  if (!is.null(f)) circ(f$cx, f$cy, f$r, col = "red", lty = 2, lwd = 1.5)
  if (pick == "RANSAC") circ(fr$cx, fr$cy, fr$r, col = "blue", lwd = 2.5) else if (pick == "FLOOR") circ(f$cx, f$cy, f$r, col = "blue", lwd = 2.5)
}
dev.off(); cat("wrote", PNG, "\n")
