args <- commandArgs(trailingOnly=TRUE)
work <- normalizePath(args[1],winslash="/",mustWork=TRUE)
lib <- file.path(work,"environment","R-library")
dir.create(lib,recursive=TRUE,showWarnings=FALSE)
dir.create(file.path(work,"environment","logs"),recursive=TRUE,showWarnings=FALSE)
.libPaths(c(lib,.Library))
Sys.setenv(R_LIBS_USER=lib,LANGUAGE="",LC_ALL="C",RGL_USE_NULL="TRUE")
options(repos=c(CRAN="https://cloud.r-project.org"),timeout=900,Ncpus=4,install.packages.check.source="no")
wanted <- c("IRkernel","remotes","alphashape3d","concaveman","data.table","ggforce","ggplot2","lidR","nabor","R.matlab","rgl","Rvcg","sf","patchwork","ggtext")
missing <- wanted[!vapply(wanted,requireNamespace,logical(1),quietly=TRUE)]
cat("Project-only R library:",lib,"\nPackages required:",paste(missing,collapse=", "),"\n")
if(length(missing)) install.packages(missing,lib=lib,type="binary",dependencies=c("Depends","Imports","LinkingTo"))
missing <- wanted[!vapply(wanted,requireNamespace,logical(1),quietly=TRUE)]
if(length(missing)) stop(paste("Required packages still unavailable:",paste(missing,collapse=", ")))
if(!requireNamespace("ITSMe",quietly=TRUE)) {
  remotes::install_github("lmterryn/ITSMe",lib=lib,dependencies=FALSE,upgrade="never",build_vignettes=FALSE)
}
stopifnot(requireNamespace("ITSMe",quietly=TRUE),requireNamespace("IRkernel",quietly=TRUE))
ip <- installed.packages(lib.loc=lib)
write.csv(as.data.frame(ip[,intersect(c("Package","Version","Built","RemoteSha","RemoteRepo"),colnames(ip)),drop=FALSE]),file.path(work,"environment","R_package_versions.csv"),row.names=FALSE)
writeLines(capture.output(sessionInfo()),file.path(work,"environment","R_install_session_info.txt"))
desc <- packageDescription("ITSMe")
writeLines(capture.output(dput(desc)),file.path(work,"environment","ITSMe_description.txt"))
cat("ITSME_ENVIRONMENT_READY",as.character(packageVersion("ITSMe")),"\n")
