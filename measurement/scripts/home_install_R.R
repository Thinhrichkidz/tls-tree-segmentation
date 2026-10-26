# Home PC only: run explicitly AFTER installing R. Not executed during handover.
args <- commandArgs(trailingOnly=TRUE)
work <- normalizePath(args[1],winslash="/",mustWork=TRUE)
lib <- file.path(work,"environment","home-R-library")
dir.create(lib,recursive=TRUE,showWarnings=FALSE)
.libPaths(c(lib,.Library))
Sys.setenv(R_LIBS_USER=lib,LC_ALL="C",RGL_USE_NULL="TRUE")
options(repos=c(CRAN="https://cloud.r-project.org"),timeout=900,Ncpus=4,install.packages.check.source="no")
baseline <- read.csv(file.path(work,"environment","R_package_versions.csv"),stringsAsFactors=FALSE)
wanted <- setdiff(unique(c(baseline$Package,"IRkernel","remotes")),"ITSMe")
missing <- wanted[!vapply(wanted,requireNamespace,logical(1),quietly=TRUE)]
if(length(missing))install.packages(missing,lib=lib,type="binary",dependencies=c("Depends","Imports","LinkingTo"))
missing <- wanted[!vapply(wanted,requireNamespace,logical(1),quietly=TRUE)]
if(length(missing))stop(paste("Unavailable home dependencies:",paste(missing,collapse=", ")))
sha <- "6cfb11c18efb3b12a4e12d38ea1cbf426b777e7b"
installed_sha <- if(requireNamespace("ITSMe",quietly=TRUE))packageDescription("ITSMe")$RemoteSha else NULL
if(is.null(installed_sha)||installed_sha!=sha)remotes::install_github(paste0("lmterryn/ITSMe@",sha),lib=lib,dependencies=FALSE,upgrade="never",build_vignettes=FALSE)
stopifnot(requireNamespace("ITSMe",quietly=TRUE),requireNamespace("IRkernel",quietly=TRUE))
ip <- installed.packages(lib.loc=lib)
home <- data.frame(Package=ip[,"Package"],Version=ip[,"Version"],Built=ip[,"Built"],row.names=NULL)
write.csv(home,file.path(work,"environment","home_R_package_versions.csv"),row.names=FALSE)
diff <- merge(baseline[,c("Package","Version")],home[,c("Package","Version")],by="Package",all=TRUE,suffixes=c("_previous","_home"))
diff <- diff[is.na(diff$Version_previous)|is.na(diff$Version_home)|diff$Version_previous!=diff$Version_home,]
write.csv(diff,file.path(work,"environment","home_R_version_differences.csv"),row.names=FALSE)
writeLines(capture.output(sessionInfo()),file.path(work,"environment","home_R_session_info.txt"))
if(nrow(diff))warning("Home dependency versions differ: inspect home_R_version_differences.csv before interpreting reproducibility differences.")
cat("HOME_R_READY; ITSMe",as.character(packageVersion("ITSMe")),"; no notebook executed\n")
