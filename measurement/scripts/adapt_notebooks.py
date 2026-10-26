"""Build auditable working copies without executing notebook measurement cells."""
from pathlib import Path
import json,csv,hashlib,ast,subprocess,sys,importlib.util,shutil,os
W=Path(__file__).resolve().parents[1];ROOT=W.parent

def cell(kind,s):
    c=dict(cell_type=kind,id=hashlib.sha256((kind+s).encode()).hexdigest()[:12],metadata={},source=s.strip().splitlines(True))
    if kind=='code':c.update(execution_count=None,outputs=[])
    return c
def md(s):return cell('markdown',s)
def code(s):return cell('code',s)
def notebook(cells,language):
    metadata=dict(kernelspec=dict(display_name='R' if language=='R' else 'Python 3 (ipykernel)',language=language.lower(),name='ir' if language=='R' else 'python3'),language_info=dict(name=language.lower()))
    return dict(cells=cells,metadata=metadata,nbformat=4,nbformat_minor=5)
def write(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def main():
    audit=[]
    for name in ['04_ARS_TLS_practical_ITSME.ipynb','03_ARS_TLS_practical_QSM.ipynb']:
        p=W/'notebooks'/name;n=json.loads(p.read_text(encoding='utf-8'))
        audit.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),cell_count=len(n['cells']),metadata=n['metadata'],cells=[dict(index=i,cell_type=c['cell_type'],source=''.join(c['source'])) for i,c in enumerate(n['cells'])]))
    write(W/'validation/original_notebook_static_audit.json',audit)
    r=[md('''# ITSMe: one selected V2 tree at a time
Working adaptation of `04_ARS_TLS_practical_ITSME.ipynb`; original remains untouched. Select the **R / ir** kernel. Do not run this in a Python kernel.

All ten files are provisional: **human approval PENDING**, biological completeness not certified. Start with `tree_146` for a height-only smoke test, after checking it in CloudCompare. No automatic installation or batch execution is included.

The unchanged absolute-coordinate PLY remains the authoritative input copy. The loader uses a separately prepared, explicitly translated XYZ text copy (all observations retained) to avoid global-coordinate precision and PLY-cleaning ambiguity. A constant foot-ground translation preserves slope; this is not per-point terrain flattening. See each tree's `coordinate_transform.json`.

Changes from the source: replace Colab mount/install cells with local paths and checks; pass an explicit foot-ground XYZ data.frame to relevant functions; timestamp outputs; retain warnings; make optional diameter/crown stages opt-in. The original ITSMe functions and their algorithms remain in use. No measurements have been executed in this notebook.'''),code(r'''
ROOT <- "G:/22083142/outputs/WSL_ML2A/55x55/3cm/Codex_help"
WORK <- file.path(ROOT, "measurement_pipeline")
TREE_ID <- "tree_146"  # change to any stable ID in the ten-tree selection manifest
RUN_DBH <- FALSE
RUN_SENSITIVITY <- FALSE
RUN_OTHER_DIAMETERS <- FALSE
RUN_CROWN <- FALSE
ALLOW_LEAN_HORIZONTAL_DIAMETER <- FALSE
set.seed(6003)
options(warn = 1)  # retain warnings; the source notebook suppressed them
manifest <- read.csv(file.path(WORK, "results", "top10_selection_manifest.csv"), check.names = FALSE, stringsAsFactors = FALSE, fileEncoding = "UTF-8-BOM")
manifest$qc_screen_eligible <- tolower(as.character(manifest$qc_screen_eligible)) == "true"
selected <- manifest[manifest$stable_tree_id == TREE_ID, , drop = FALSE]
stopifnot(nrow(selected) == 1L, selected$qc_screen_eligible)
selected$human_review_decision <- "PENDING"
review_path <- file.path(WORK, "results", "human_review_template.csv")
if (file.exists(review_path)) {
  decisions <- read.csv(review_path, stringsAsFactors=FALSE, fileEncoding="UTF-8-BOM")
  decision <- decisions[decisions$stable_tree_id == TREE_ID & decisions$review_sha256 == selected$review_sha256, , drop=FALSE]
  if (nrow(decision) != 1L) stop("Human review record missing, duplicated or stale for this exact input hash.")
  selected$human_review_decision <- decision$human_decision
}
RUN_DIR <- file.path(WORK, "results", paste0("ITSMe_", TREE_ID, "_", format(Sys.time(), "%Y%m%d_%H%M%OS6"), "_", Sys.getpid()))
if (dir.exists(RUN_DIR)) stop("Run directory already exists; choose a new run.")
dir.create(RUN_DIR, recursive = TRUE)
write.csv(selected, file.path(RUN_DIR, paste0(TREE_ID, "_input_and_qc.csv")), row.names = FALSE)
print(selected[, c("stable_tree_id", "original_v2_filename", "review_ply_filename", "preliminary_height_m", "estimated_low_stem_lean_degrees", "human_approval")])
warning("Provisional input: this run does not approve segmentation or biological completeness.")
'''),md('''## Check the existing R environment
Missing packages stop here without installing anything. Installation and kernel-registration instructions are in `measurement_pipeline_readme.md`. The detected R executable is R 4.5.2; ITSMe and IRkernel were absent during preparation. Record the actual installed version and function signatures because package defaults can change.'''),code(r'''
required <- c("ITSMe", "ggplot2", "data.table")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) {
  msg <- paste("Missing R packages:", paste(missing, collapse = ", "), "-- no installation attempted.")
  writeLines(msg, file.path(RUN_DIR, "dependency_blocker.txt")); stop(msg)
}
library(ITSMe)
writeLines(c(capture.output(sessionInfo()), paste("ITSMe", packageVersion("ITSMe"))), file.path(RUN_DIR, "session_info.txt"))
functions <- c("read_tree_pc", "tree_height_pc", "dbh_pc", "diameter_slice_pc", "classify_crown_pc", "projected_area_pc")
writeLines(unlist(lapply(functions, function(n) c(n, capture.output(formals(get(n, asNamespace("ITSMe"))))))), file.path(RUN_DIR, "function_signatures.txt"))
for (name in c("tree_height_pc", "dbh_pc", "diameter_slice_pc", "classify_crown_pc")) {
  if (!"dtm" %in% names(formals(get(name, asNamespace("ITSMe"))))) stop(paste(name, "in this installed version lacks an explicit dtm argument. Stop and review compatibility."))
}
parameters <- list(TREE_ID=TREE_ID, RUN_DBH=RUN_DBH, RUN_SENSITIVITY=RUN_SENSITIVITY,
  RUN_OTHER_DIAMETERS=RUN_OTHER_DIAMETERS, RUN_CROWN=RUN_CROWN,
  thresholdR2=0.001, slice_thickness_m=0.06, functional=TRUE, concavity=4,
  thresholdbranch=1.5, crown_area_concavity=3, random_seed=6003,
  height_top="ITSMe unchanged full-cloud maximum; compare separately with supported-top screening height",
  ground="one explicit XYZ foot-ground reference, not a median over sloping plot terrain")
saveRDS(parameters, file.path(RUN_DIR, "parameters.rds"))
writeLines(capture.output(dput(parameters)), file.path(RUN_DIR, "parameters.txt"))
'''),md('''## Load the selected observations and foot-ground reference
ITSMe supports PLY through Rvcg, but its PLY reader requests cleaning and its precision depends on the installed stack. This working copy uses ITSMe's supported TXT reader with `samplefactor=1`. Every XYZ observation is retained. The shared translation is `(absolute stem-foot X, absolute stem-foot Y, absolute mesh-ground Z)`.

The one-point DTM is a deliberate fixed ground reference `(0,0,0)`, not a claim to represent a flat forest. The original sloping terrain triangle subset is also supplied separately for QSM and inspection. The lookup radius below only ensures ITSMe can find that fixed reference despite lean; it does not average nearby terrain or alter the cloud.'''),code(r'''
stopifnot(file.exists(selected$input_ply_path), file.exists(selected$local_xyz_path), file.exists(selected$local_ground_reference_path))
tree1 <- ITSMe::read_tree_pc(path = selected$local_xyz_path, samplefactor = 1)
ground_ref <- as.data.frame(read.table(selected$local_ground_reference_path, header = TRUE))
stopifnot(nrow(tree1) == selected$point_count, all(c("X", "Y", "Z") %in% names(tree1)), all(is.finite(as.matrix(tree1[, c("X", "Y", "Z")]))))
stopifnot(nrow(ground_ref) == 1L, all(as.numeric(unlist(ground_ref[1, ])) == 0))
low10 <- tree1[order(tree1$Z)[seq_len(min(10L, nrow(tree1)))], ]
ground_lookup_radius <- max(1, max(abs(c(low10$X, low10$Y))) + 0.05)
writeLines(paste("ground_lookup_radius_m", ground_lookup_radius), file.path(RUN_DIR, "ground_lookup.txt"))
run_stage <- function(label, fun) {
  tryCatch(withCallingHandlers(fun(), warning = function(w) {
    cat(label, conditionMessage(w), "\n", file=file.path(RUN_DIR, "warnings.log"), append=TRUE)
  }), error = function(e) {
    cat(label, conditionMessage(e), "\n", file=file.path(RUN_DIR, "errors.log"), append=TRUE)
    stop(e)
  })
}
'''),md('''## Height-only smoke test
Retain the source notebook's `tree_height_pc` algorithm, now using the fixed ground reference. ITSMe uses the full-cloud maximum; the preliminary ranking instead uses a locally supported observed top. Report both explicitly. For `tree_102`, for example, the unsupported-maximum difference is about 0.018 m. No points are removed.

ITSMe's own diagnostic plots can use cloud-minimum zero even when a DTM is passed. The extra plot below uses the explicit foot-ground zero and is the preferred height-axis diagnostic. This is vertical tree height, not curved stem length.'''),code(r'''
h1 <- run_stage("height", function() ITSMe::tree_height_pc(pc=tree1, dtm=ground_ref, r=ground_lookup_radius, plot=TRUE))
stopifnot(is.finite(h1$h), abs(h1$lp) < 1e-8)
height_result <- cbind(selected, itsme_full_cloud_height_m=h1$h,
  itsme_minus_supported_top_height_m=h1$h-selected$preliminary_height_m,
  itsme_ground_local_z_m=h1$lp, validation_status="PROVISIONAL_NOT_HUMAN_APPROVED")
write.csv(height_result, file.path(RUN_DIR, paste0(TREE_ID, "_height.csv")), row.names=FALSE)
saveRDS(h1, file.path(RUN_DIR, paste0(TREE_ID, "_height_diagnostics.rds")))
ggplot2::ggsave(file.path(RUN_DIR, paste0(TREE_ID, "_ITSMe_height_XZ.png")), plot=h1$plotXZ, width=6, height=8)
foot_plot <- ggplot2::ggplot(tree1, ggplot2::aes(X, Z)) + ggplot2::geom_point(size=0.1, shape=".") +
  ggplot2::geom_hline(yintercept=0, colour="brown") + ggplot2::geom_hline(yintercept=selected$preliminary_height_m, colour="blue") +
  ggplot2::coord_fixed() + ggplot2::labs(y="Vertical Z above estimated stem-foot ground (m)", title=paste(TREE_ID, "provisional ground-referenced height"))
ggplot2::ggsave(file.path(RUN_DIR, paste0(TREE_ID, "_foot_ground_height_XZ.png")), plot=foot_plot, width=6, height=8)
print(height_result[, c("stable_tree_id", "preliminary_height_m", "itsme_full_cloud_height_m", "human_approval")])
'''),md('''## Optional DBH and source-notebook sensitivity tests
Keep disabled for the first smoke test. DBH is a horizontal circle/functional-hull fit in a 0.06 m band centred **1.3 m vertically above the fixed foot ground**. A leaning circular trunk cuts an ellipse horizontally: a thinner band reduces axial smear but does not correct this geometric bias. `tree_108` has an estimated low-stem lean near 26 degrees, and `tree_103` near 17 degrees. The 15-degree safeguard is a review trigger, not a validated forestry threshold. A stem-normal DBH method would require a separate approved methodological change.

At approximately 3 cm sampling a thin slice can be sparse; inspect angular coverage, circle fit, functional hull, neighbouring vegetation and warnings. Original sensitivity alternatives (R2 0.002, thickness 0.2 m, concavity 3) remain optional and must not be chosen just because they produce a preferred answer.'''),code(r'''
diameter_requested <- RUN_DBH || RUN_SENSITIVITY || RUN_OTHER_DIAMETERS || RUN_CROWN
if (diameter_requested && selected$estimated_low_stem_lean_degrees >= 15 && !ALLOW_LEAN_HORIZONTAL_DIAMETER) {
  stop("Leaning-stem diameter review required. Inspect geometry before explicitly allowing a provisional horizontal-slice diameter.")
}
if (RUN_DBH) {
  dbh1 <- run_stage("DBH", function() ITSMe::dbh_pc(pc=tree1, dtm=ground_ref, r=ground_lookup_radius,
    thresholdR2=0.001, slice_thickness=0.06, functional=TRUE, concavity=4, plot=TRUE))
  saveRDS(dbh1, file.path(RUN_DIR, paste0(TREE_ID, "_dbh_provisional.rds")))
  writeLines(capture.output(str(dbh1)), file.path(RUN_DIR, paste0(TREE_ID, "_dbh_fields.txt")))
  ggplot2::ggsave(file.path(RUN_DIR, paste0(TREE_ID, "_dbh.png")), plot=dbh1$plot, width=7, height=7)
}
if (RUN_SENSITIVITY) {
  dbh1a <- run_stage("DBH_R2_0.002", function() ITSMe::dbh_pc(pc=tree1, dtm=ground_ref, r=ground_lookup_radius, thresholdR2=0.002, functional=TRUE, plot=TRUE))
  dbh1b <- run_stage("DBH_band_0.2m", function() ITSMe::dbh_pc(pc=tree1, dtm=ground_ref, r=ground_lookup_radius, slice_thickness=0.2, functional=TRUE, plot=TRUE))
  dbh1c <- run_stage("DBH_concavity_3", function() ITSMe::dbh_pc(pc=tree1, dtm=ground_ref, r=ground_lookup_radius, concavity=3, functional=TRUE, plot=TRUE))
  saveRDS(list(R2=dbh1a, band=dbh1b, concavity=dbh1c), file.path(RUN_DIR, paste0(TREE_ID, "_dbh_sensitivity.rds")))
}
'''),md('''## Optional diameters and crown metrics
These preserve the source notebook's ITSMe functions and chosen heights. The crown boundary uses the original width-expansion classification (`thresholdbranch=1.5`), then concave-hull projected crown area (`concavity=3`). This is not independent validation of crown ownership. Crown dimensions and volume are not automatically added to the original algorithm; approve an extension after inspection.'''),code(r'''
if (RUN_OTHER_DIAMETERS) {
  diameters <- lapply(c(1, 1.5, 1.9), function(h) run_stage(paste0("diameter_",h), function()
    ITSMe::diameter_slice_pc(pc=tree1, slice_height=h, dtm=ground_ref, r=ground_lookup_radius, functional=TRUE, plot=TRUE)))
  names(diameters) <- c("1.0m", "1.5m", "1.9m")
  saveRDS(diameters, file.path(RUN_DIR, paste0(TREE_ID, "_diameter_slices.rds")))
}
if (RUN_CROWN) {
  tree1_classified <- run_stage("crown_classification", function() ITSMe::classify_crown_pc(pc=tree1,
    dtm=ground_ref, r=ground_lookup_radius, thresholdbranch=1.5, plot=TRUE))
  crown1 <- tree1_classified$crownpoints
  if (is.null(crown1) || nrow(crown1) == 0) stop("No usable crown points returned; inspect classification.")
  ca1 <- run_stage("projected_crown_area", function() ITSMe::projected_area_pc(pc=crown1, concavity=3, plot=TRUE))
  saveRDS(list(classification=tree1_classified, area=ca1), file.path(RUN_DIR, paste0(TREE_ID, "_crown_provisional.rds")))
  ggplot2::ggsave(file.path(RUN_DIR, paste0(TREE_ID, "_crown_classification.png")), plot=tree1_classified$plot, width=7, height=8)
  ggplot2::ggsave(file.path(RUN_DIR, paste0(TREE_ID, "_crown_area.png")), plot=ca1$plot, width=7, height=7)
}
cat("Outputs:", RUN_DIR, "\nAll results remain provisional; no segmentation approval was recorded.\n")
''')]
    # Python notebook has no non-standard Python dependency.
    q=[md('''# QSM / RayExtract: selected V2 tree preparation
Working adaptation of `03_ARS_TLS_practical_QSM.ipynb`, Python 3 kernel. The original notebook builds RayCloudTools and TreeTools in Colab, imports one tree with a synthetic ray, derives terrain from that tree, then runs `rayextract trees`. It does not run TreeQSM or export biomass.

This copy uses the prepared tree and original plot-terrain triangle subset in a shared, explicit local frame. It passes `--segmented` with one uniform non-black tree colour, preserving the single input label instead of repeating tree segmentation. It does not derive ground from a tree-only cloud. The source notebook's RayExtract model is retained. Model construction and ray conversion are **disabled by default**; no 10-tree loop is included.

Dependencies were not installed during preparation. Docker CLI exists but its Linux engine was unavailable. Native ray tools were not found on PATH. Start with configuration/preflight after the environment is approved and available.'''),code(r'''
from pathlib import Path
import csv, json, hashlib, shutil, subprocess, sys, platform, datetime, uuid
ROOT = Path(r"G:\22083142\outputs\WSL_ML2A\55x55\3cm\Codex_help")
WORK = ROOT / "measurement_pipeline"
TREE_ID = "tree_146"
MODE = "docker"  # alternatively: native
IMAGE = "ghcr.io/csiro-robotics/raycloudtools:latest"  # installed local image only; record immutable image ID
NATIVE_TOOLS = {"rayimport": "rayimport", "rayextract": "rayextract", "treeinfo": "treeinfo"}
RUN_CONVERSION = False
RUN_QSM = False
RUN_TREEINFO = False
PARAMETERS = {"max_diameter_m": 0.9, "height_min_m": 2.0, "synthetic_ray": "0,0,-0.1", "max_intensity": 0}
manifest = list(csv.DictReader((WORK/"results/top10_selection_manifest.csv").open(encoding="utf-8-sig")))
matches = [r for r in manifest if r["stable_tree_id"] == TREE_ID]
assert len(matches) == 1
selected = matches[0]
review_file = WORK/"results/human_review_template.csv"
if review_file.is_file():
    decisions = list(csv.DictReader(review_file.open(encoding="utf-8-sig")))
    match = [r for r in decisions if r["stable_tree_id"] == TREE_ID and r["review_sha256"] == selected["review_sha256"]]
    if len(match) != 1: raise RuntimeError("Human review entry is stale, missing or duplicated for this source hash")
    selected["human_review_decision"] = match[0]["human_decision"]
source = Path(selected["local_xyzrgb_ply_path"])
terrain = Path(selected["local_terrain_mesh_path"])
assert all(p.is_file() for p in [source, terrain, Path(selected["input_ply_path"])])
print(TREE_ID, selected["original_v2_filename"], selected["preliminary_height_m"], "m; human approval PENDING")
print("Shared explicit translation:", [selected[f"translation_{a}_m"] for a in "xyz"])
'''),md('''## Environment and version preflight
No installation, image pull or system configuration is performed. Docker mode uses `--pull=never` and disables networking. If an image or executable is missing, stop and follow the README. Record the image ID/digest or executable hash plus command help; do not assume a particular `--version` syntax. The official current container builds both RayCloudTools and TreeTools, but the actual locally installed image must be checked.

Ordinary CloudCompare normals are **not acquisition rays**. The conversion input therefore intentionally contains only XYZ and a uniform tree label colour. The original attributes remain intact in the copied primary PLY. Synthetic rays are format scaffolding, not recovered scanner trajectories; never add `--use_rays` for these files.'''),code(r'''
def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8*1024*1024), b""): h.update(block)
    return h.hexdigest()

environment = {"python": sys.version, "platform": platform.platform(), "mode": MODE}
if MODE == "docker":
    docker = shutil.which("docker")
    if not docker: raise RuntimeError("Docker CLI missing; no installation attempted.")
    server = subprocess.run([docker, "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True)
    if server.returncode: raise RuntimeError("Docker engine unavailable: " + server.stderr)
    result = subprocess.run([docker, "image", "inspect", IMAGE], capture_output=True, text=True)
    if result.returncode: raise RuntimeError("Required local image missing; no image pull attempted.")
    environment["docker_image"] = json.loads(result.stdout)[0]
elif MODE == "native":
    for tool in ["rayimport", "rayextract"]:
        executable = shutil.which(NATIVE_TOOLS[tool])
        if not executable: raise RuntimeError(f"Missing {tool}; configure an existing executable path.")
        environment[tool] = {"path": executable, "sha256": digest(executable)}
else:
    raise ValueError("MODE must be native or docker")

RUN_DIR = WORK / "results" / ("QSM_" + TREE_ID + "_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_" + uuid.uuid4().hex[:8])
RUN_DIR.mkdir(parents=True, exist_ok=False)
(RUN_DIR/"environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
(RUN_DIR/"parameters_and_input.json").write_text(json.dumps({"parameters": PARAMETERS, "selected": selected,
    "original_ply_sha256": digest(selected["input_ply_path"]), "validation": "PROVISIONAL_NOT_HUMAN_APPROVED"}, indent=2), encoding="utf-8")

def map_path(path):
    path = Path(path).resolve()
    return str(path) if MODE == "native" else "/work/" + path.relative_to(ROOT.resolve()).as_posix()

def command(tool, arguments):
    if MODE == "native": return [NATIVE_TOOLS[tool], *map(str, arguments)]
    return [docker, "run", "--rm", "--pull=never", "--network", "none",
            "--mount", f"type=bind,source={ROOT},target=/work", "--workdir", map_path(RUN_DIR),
            IMAGE, tool, *map(str, arguments)]

def run_logged(label, cmd, check=True):
    (RUN_DIR/(label+"_command.json")).write_text(json.dumps(cmd, indent=2), encoding="utf-8")
    result = subprocess.run(cmd, cwd=RUN_DIR, text=True, capture_output=True)
    (RUN_DIR/(label+"_stdout.txt")).write_text(result.stdout, encoding="utf-8")
    (RUN_DIR/(label+"_stderr.txt")).write_text(result.stderr, encoding="utf-8")
    if check and result.returncode: raise RuntimeError(f"{label} failed ({result.returncode}); see logs in {RUN_DIR}")
    return result

# Usage-only probe; a nonzero usage return code is acceptable. No modelling occurs.
help_result = run_logged("rayextract_help", command("rayextract", []), check=False)
if "--segmented" not in help_result.stdout + help_result.stderr:
    raise RuntimeError("This RayExtract executable does not advertise --segmented; review compatibility before proceeding.")
'''),md('''## Prepare an intermediate ray-cloud format (one tree only)
Enable `RUN_CONVERSION` only after preflight. A fresh timestamped run gets its own local XYZRGB input, so `rayimport` cannot overwrite the prepared input or previous results. The importer receives the source notebook's synthetic ray vector and `--max_intensity 0`. It does not use `--remove_start_pos` or apply a hidden translation. The prepared terrain already uses the same local frame.

The `.ply` suffix alone does not establish ray-cloud compatibility. This conversion has **not** been run because the tools are unavailable. Before model construction, validate its point count and XYZ against the prepared input; normals/time may be synthetic. The validation below reads scalar-vertex binary/ASCII PLY without extra Python packages and enforces a 0.1 mm coordinate tolerance (allows float output in this small local frame).'''),code(r'''
import struct, itertools
scalar_types = {"char":"b", "int8":"b", "uchar":"B", "uint8":"B", "short":"h", "int16":"h", "ushort":"H", "uint16":"H",
                "int":"i", "int32":"i", "uint":"I", "uint32":"I", "float":"f", "float32":"f", "double":"d", "float64":"d"}
def iter_scalar_vertex_xyz(path):
    with Path(path).open("rb") as f:
        if f.readline().strip() != b"ply": raise ValueError("Not a PLY")
        properties=[]; count=None; format_name=None; in_vertex=False; first_element=None
        while True:
            line=f.readline()
            if not line: raise ValueError("Truncated PLY header")
            t=line.decode("ascii").strip().split()
            if not t: continue
            if t[0]=="format": format_name=t[1]
            if t[0]=="element":
                if first_element is None: first_element=t[1]
                in_vertex=t[1]=="vertex"
                if in_vertex: count=int(t[2])
            if t[0]=="property" and in_vertex:
                if t[1]=="list": raise ValueError("List-valued vertex property is unsupported by this validator")
                properties.append((t[2],t[1]))
            if t[0]=="end_header": break
        if first_element!="vertex" or count is None: raise ValueError("Expected vertex as first PLY element")
        names=[v[0] for v in properties]; indices=[names.index(a) for a in ("x","y","z")]
        if format_name=="ascii":
            for _ in range(count):
                values=f.readline().split()
                if len(values)!=len(properties): raise ValueError("Truncated/malformed vertex")
                yield tuple(float(values[i]) for i in indices)
        else:
            endian={"binary_little_endian":"<","binary_big_endian":">"}[format_name]
            layout=struct.Struct(endian+"".join(scalar_types[v[1]] for v in properties))
            for _ in range(count):
                values=layout.unpack(f.read(layout.size));yield tuple(float(values[i]) for i in indices)

local_input = RUN_DIR / source.name
ray_file = local_input.with_name(local_input.stem+"_raycloud.ply")
if RUN_CONVERSION:
    if local_input.exists() or ray_file.exists(): raise FileExistsError("Use a fresh run directory for conversion")
    shutil.copy2(source, local_input)
    run_logged("rayimport", command("rayimport", [map_path(local_input), "ray", PARAMETERS["synthetic_ray"], "--max_intensity", PARAMETERS["max_intensity"]]))
    if not ray_file.is_file(): raise RuntimeError("Expected converted ray cloud was not generated")
    max_error=0.0; count=0
    for before,after in itertools.zip_longest(iter_scalar_vertex_xyz(local_input),iter_scalar_vertex_xyz(ray_file)):
        if before is None or after is None: raise RuntimeError("Conversion changed point count")
        error=max(abs(a-b) for a,b in zip(before,after))
        if not all(__import__("math").isfinite(v) for v in after) or error>0.0001:
            raise RuntimeError("Converted XYZ changed beyond 0.1 mm; stop before modelling")
        max_error=max(max_error,error);count+=1
    assert count==int(selected["point_count"])
    (RUN_DIR/"conversion_validation.json").write_text(json.dumps({"point_count":count,"max_xyz_difference_m":max_error,
        "synthetic_rays":True,"use_rays_allowed":False,"uniform_nonblack_single_tree_label":True},indent=2),encoding="utf-8")
else:
    print("Ray conversion skipped. Prepared XYZRGB PLY and terrain are available; no ray-cloud result claimed.")
'''),md('''## Optional later model construction — deliberately disabled
This stage is computational modelling and has not been run. Enable it for one reviewed tree only after inspecting the conversion. `--segmented` uses the single known input label; black/unlabelled and mixed crown colours are avoided in the derivative. The source notebook's `--height_min 10` is changed to an explicit configurable 2 m so short trees near 10 m are not dropped; `max_diameter=0.9` is retained as a starting parameter, not a measured diameter. Inspect its suitability rather than forcing agreement. No leaf/wood separation is implemented by the source notebook. Leaf-bearing crowns and mistaken ownership can bias model structure.

Expected outputs are a RayExtract tree-structure text file, a model mesh and an auxiliary coloured cloud. Confirm exactly one plausible biological-tree model and check base, branch connections, taper, crown coverage and cylinder overlap. The auxiliary cloud is a modelling by-product and must never replace the authoritative segmentation. Branch radii use structural priors. Never use synthetic rays as real free-space evidence.'''),code(r'''
if RUN_QSM:
    if not RUN_CONVERSION or not (RUN_DIR/"conversion_validation.json").is_file():
        raise RuntimeError("Run and validate conversion in this same fresh session first")
    run_logged("rayextract_trees", command("rayextract", ["trees", map_path(ray_file), map_path(terrain), "--segmented",
        "--max_diameter", PARAMETERS["max_diameter_m"], "--height_min", PARAMETERS["height_min_m"]]))
    expected=[ray_file.with_name(ray_file.stem+suffix) for suffix in ["_trees.txt","_trees_mesh.ply","_segmented.ply"]]
    missing=[str(p) for p in expected if not p.is_file()]
    if missing: raise RuntimeError("Missing expected model outputs: "+repr(missing))
    (RUN_DIR/"model_outputs_pending_review.json").write_text(json.dumps({"files":[str(p) for p in expected],
        "status":"PENDING_GEOMETRIC_MODEL_VALIDATION","tree_id":TREE_ID,"source_filename":selected["original_v2_filename"]},indent=2),encoding="utf-8")
else:
    print("QSM model construction skipped; no volume or biomass calculated.")
'''),md('''## Optional TreeTools summary after inspecting a model
The source notebook installs TreeTools but does not call it. This optional extension logs `treeinfo` without inventing a volume parser. Verify the installed output schema and exactly one tree before transferring any volume to a result table. A modelled wood volume is not biomass: biomass additionally needs justified wood density, uncertainty and appropriate biological assumptions. RayExtract TXT is not TreeQSM `.mat`, so do not pass it directly to ITSMe's TreeQSM reader.'''),code(r'''
if RUN_TREEINFO:
    if not RUN_QSM: raise RuntimeError("TreeTools needs a reviewed model from the enabled one-tree QSM stage")
    tree_txt=ray_file.with_name(ray_file.stem+"_trees.txt")
    run_logged("treeinfo_help", command("treeinfo", []), check=False)
    run_logged("treeinfo", command("treeinfo", [map_path(tree_txt)]))
    print("Inspect the logged tree/model count and volume schema; no biomass or automatic summary acceptance.")
''')]
    rn=notebook(r,'R');qn=notebook(q,'python')
    write(W/'notebooks/ITSMe_V2_10_selected_trees.ipynb',rn);write(W/'notebooks/QSM_V2_10_selected_trees.ipynb',qn)
    rfile=W/'validation/ITSMe_working_copy_cells_for_parse_only.R';rfile.write_text('\n\n'.join(''.join(c['source']) for c in r if c['cell_type']=='code'),encoding='utf-8')
    for c in q:
        if c['cell_type']=='code':ast.parse(''.join(c['source']))
    rscript=Path('C:/Program Files/R/R-4.5.2/bin/Rscript.exe');env=os.environ.copy();env.update(LC_ALL='C',LANG='C',LANGUAGE='')
    result=subprocess.run([str(rscript),'--vanilla','-e',f'invisible(parse(file="{rfile.as_posix()}")); cat("R_PARSE_OK\\n")'],capture_output=True,text=True,env=env)
    write(W/'validation/adapted_notebook_static_validation.json',dict(python_code_cells_parse=True,R_parse_returncode=result.returncode,R_parse_stdout=result.stdout,R_parse_stderr=result.stderr,notebook_cells_executed=False,original_notebooks_unchanged=all(hashlib.sha256(Path(a['path']).read_bytes()).hexdigest()==a['sha256'] for a in audit),R_cell_count=len(r),python_cell_count=len(q)))
    assert result.returncode==0,result.stderr
    csv_check=f'w <- "{W.as_posix()}"; x <- read.csv(file.path(w,"results/top10_selection_manifest.csv"),check.names=FALSE,stringsAsFactors=FALSE); x$qc_screen_eligible <- tolower(as.character(x$qc_screen_eligible)) == "true"; stopifnot(nrow(x)==10L,all(x$qc_screen_eligible)); g <- read.table(x$local_ground_reference_path[x$stable_tree_id=="tree_146"],header=TRUE); stopifnot(all(as.numeric(unlist(g[1,]))==0)); cat("R_MANIFEST_AND_GROUND_READ_OK\\n")'
    csv_result=subprocess.run([str(rscript),'--vanilla','-e',csv_check],capture_output=True,text=True,env=env)
    write(W/'validation/R_manifest_and_ground_read_check.json',dict(passed=csv_result.returncode==0,stdout=csv_result.stdout,stderr=csv_result.stderr,scope='Base-R CSV and fixed-ground-reference loading only; no ITSMe package or notebook measurement cells executed',boolean_conversion='Explicit case-insensitive True/False conversion for Python-generated CSV'))
    assert csv_result.returncode==0,csv_result.stderr
    wanted=['ITSMe','IRkernel','ggplot2','data.table','Rvcg','lidR','nabor','alphashape3d','concaveman','sf','R.matlab','rgl','patchwork','ggforce','ggtext','remotes']
    expression='p <- c('+','.join('"'+p+'"' for p in wanted)+'); ip <- installed.packages(); cat(R.version.string,"\\n"); for (x in p) cat(x, if(x %in% rownames(ip)) ip[x,"Version"] else "MISSING", "\\n"); cat("LIBRARIES\\n"); cat(.libPaths(),sep="\\n")'
    rr=subprocess.run([str(rscript),'--vanilla','-e',expression],capture_output=True,text=True,env=env)
    environment=dict(python_executable=sys.executable,python_version=sys.version,python_packages={p:importlib.util.find_spec(p) is not None for p in ['jupyter','jupyterlab','notebook','ipykernel','nbformat','numpy','scipy','plyfile']},Rscript=str(rscript),R_package_check=rr.stdout,R_package_check_stderr=rr.stderr,executables={p:shutil.which(p) for p in ['rayimport','rayextract','treeinfo','docker']},R_kernel_found_in_standard_jupyter_locations=False,earlier_WSL_check='Only docker-desktop distro reported by wsl --list --quiet',earlier_Docker_check='CLI exists; dockerDesktopLinuxEngine named pipe absent; local images and tool versions could not be inspected',ITSMe_smoke_test='NOT_RUN: ITSMe and IRkernel/Jupyter missing',QSM_model_run=False,packages_installed=False)
    write(W/'validation/environment_readiness.json',environment)
    print(json.dumps(dict(R_parse=result.returncode,python_parse=True,originals_unchanged=True,environment=environment),indent=2))

if __name__=='__main__':main()
