# INFO6003 Report v3: workflow alignment review

v3 revises v2 (12 October) to match the five-stage workflow you described on 15 October.

Your stated status:
- Stages 1–3 have been carried out. Stage 3 is complete for some trees only.
- Stage 4 (attribute extraction) and Stage 5 (field validation) have not started.
- No numerical values are available yet.
- The Excel field inventory is a different file from `TreeData.csv`.

---

## 1. How well v2 represented your actual workflow

| Your stage | How v2 handled it | Problem |
|---|---|---|
| 1. Data acquisition and preparation | Covered only as "Stage 1 filters, crops and downsamples in RiSCAN PRO". It did not mention the >1 km² extent, the PLY export or why ROIs are needed. | Too thin. The narrative did not start from the large dataset. |
| 2. Automated segmentation | Commands, parameter comparison and the benchmark were all present. | Mostly accurate. It presented the automated output as something to be *scored*, not as a preliminary output to be inspected and corrected. |
| 3. Manual refinement | One paragraph listing the edit types. | **Major gap.** v2 did not explain *why* refinement is necessary, *what* automated segmentation gets wrong, or *how* refinement improves the dataset. It also did not show that this is the most time-consuming stage. |
| 4. Attribute extraction | Mentioned only as "DBH estimation requires…", with no Python processing and no height method. | **Missing as a stage.** |
| 5. Field validation | Matching was designed carefully, but against `TreeData.csv` as the reference. | Wrong reference file (the Excel inventory is separate). Validation of height was missing. |
| 6. Contribution and applications | ML was mentioned briefly as an alternative. | Missing: inventory and monitoring, biomass modelling, ML training data and segmentation limits. |
| Overall framing | The narrative was benchmark-evaluation-first (IoU, mF₁, before/after scoring), with the inventory audit as the main result. | It read as an **idealised evaluation study**, not the semi-automated processing study you are actually doing. The audit was the only "result", so the work you have done (Stages 1–3) was barely visible. |

**What v2 got right, and is kept in v3:**
- the research questions' intent;
- the verified inventory audit (all numbers unchanged);
- the Rayextract parameter comparison;
- the matching design (site and quadrant restriction, one-to-one matching, the circularity warning);
- the literature analysis (Table 1);
- reproducibility details;
- all references;
- the clear separation of completed and planned work.

---

## 2. Sections revised and why

| Section | Change | Reason |
|---|---|---|
| Title and abstract | Retitled around "semi-automated … from automated extraction and manual refinement to field validation". The abstract follows the five-stage narrative and states each stage's status. | Reflects what you did; the old title put the evaluation design first. |
| 1. Introduction | RQ1 changed from "how accurately does Rayextract…" to "which errors does automated segmentation make, and what does refinement change". Objectives are now O1–O5, one per stage. Contribution: C1 audit (completed), C2 refined tree dataset (in progress), C3 attributes and validation (planned). | Ties the questions to the real workflow without inventing results. |
| 2. Related Work | New paragraphs: "Automated Segmentation and Its Limits" (Cherlet: errors increase towards the outer crown; similar scores can hide different errors, so qualitative checking stays necessary). "Manual Segmentation as Reference and Bottleneck" (Cherlet, Cushman). Table 1 kept. | Gives literature support for **why** manual refinement is needed. |
| 3. Data | 3.1 now starts from the large (>1 km²) TLS dataset and PLY export. 3.2 separates the Excel validation reference from the audited `TreeData.csv`. 3.3 target definition kept. | Matches your description and avoids treating the CSV as the validation file. |
| 4. Methodology | Rebuilt as Stages 1–5 with a new Fig. 1 (status shown by border style) and a new Table 2 (operations, tools, status). | Clearly separates preparation, automated, manual, attribute and validation stages. |
| 4.4 Stage 3 | New *Why it is necessary / What I correct / How quality is controlled* structure. It covers the four error causes, your six refinement tasks, branch ownership as the hardest step, acceptance criteria (marked as *proposed*), a point-accounting equation, a review log, and the limits of manual work. | This was the core gap. |
| 4.5 Stage 4 (planned) | Height equation, DBH slice and circle-fit approach (with literature caveats), the fork-note issue, optional crown area, and an explicit statement that **tree age is not estimated**. | Adds the missing stage, marked as planned. Follows your rule on age estimation. |
| 4.6 Stage 5 (planned) | Matching design kept; reference changed to the Excel inventory. | Correct reference file. |
| 5. Experimental evaluation | Reorganised by RQ. IoU/F₁ scoring is kept but now framed as measuring *how much refinement changed* the output, not independent accuracy. | More honest given that the reference is derived by editing the automated output. |
| 6. Results | New 6.1 "Processing Progress (Stages 1–3)" with qualitative observations only. Table 3 lists the quantities to report, all pending. Fig. 2 placeholder for a before/after refinement example. The audit is condensed into prose plus Table 4 and Fig. 3; all values are unchanged. | Puts your actual work in the results without inventing numbers. |
| 7. Discussion | New: "How Manual Refinement Contributes to Dataset Quality"; "How Each Stage Can Affect the Final Measurements" (downsampling, automated segmentation, refinement, extraction, field error), written as hypotheses H1–H3; a limitations paragraph; and "Contribution and Potential Applications" (inventory and monitoring, biomass, ML, segmentation limits), all explicitly labelled *potential*. | Covers Stage 6 and the effects-of-each-stage discussion you asked for, without overstating. |
| 8. Conclusion | Retells the actual narrative; makes no accuracy claim. | Matches the evidence. |

**Removed or condensed to make room within 12 pages:**
- The v2 status table, replaced by the stage table.
- The two-panel diameter/slot statistics table. Its key values are now in the prose and none were lost: mean, SD, median, quartiles, range, pooled mean, slot counts.
- The mF₁ equation.
- The detailed TLS-results table, replaced by the stage quantities table.

---

## 3. Status vocabulary used in v3

| Term | Means | Applied to |
|---|---|---|
| **Completed** | Done, with evidence in the report | Inventory audit |
| **Carried out** | Done by you; evidence (settings, logs) still to be added | Stage 1, Stage 2 |
| **In progress** | Started, not finished | Stage 3 manual refinement |
| **Planned** | Method designed, not started | Stage 4, Stage 5, effort and IoU analysis |
| **Potential** | Possible future use, not demonstrated | Inventory and monitoring, biomass, ML, second forest type |

---

## 4. Missing evidence, conflicts and limitations to resolve

### Things the report now depends on
1. **ROI evidence:** number, size and location of the ROIs, and why each was chosen. Needed for Fig. 2a.
2. **Downsampling:** method and resolution, plus point counts before and after.
3. **Stage 2 settings:** the `rayextract` parameters you actually used (gradient, `height_min`, `max_diameter`) and why.
4. **Stage 3 progress:** trees refined, accepted and flagged uncertain out of the total, and time spent.
5. **Unedited automated output:** was it kept? If not, the before/after comparison (RQ1, IoU/F₁) cannot be done. RQ1 would then have to rely on the review log alone, and Sect. 5 should be cut accordingly.
6. **Leftover cloud:** do you use it during refinement (Stage 3 of the pipeline)?
7. **Acceptance criteria:** v3 *proposes* four checks (continuous stem; no neighbour branches; no unexplained crown truncation; non-tree material removed). Confirm or replace them, and say whether you record them per tree.
8. **Review log:** v3 assumes one will record error type, edit, uncertainty and time. If you have not been logging, start now. RQ2 (effort) cannot be answered otherwise. Do not reconstruct times from memory.
9. **Before/after example figure (Fig. 2b):** a screenshot pair from CloudCompare showing a reassigned overlapping branch.
10. **Excel field inventory:**
    - file name and custodian;
    - fields available (does it include **height**?);
    - its relationship to `TreeData.csv` (same plots and records? a newer version?).
    If it has no heights, remove height validation from RQ3.
11. **Stage 4 method:** slice thickness, fitting method, quality rule and Python libraries.
12. **TLS acquisition metadata:** scanner, dates, registration and coordinate system.

### Source conflicts
- **Study extent.** You describe the TLS dataset as covering >1 km². The meeting notes describe ~34–36 monitoring plots, and the benchmark notes that TLS plots are typically ≤1 ha. Confirm whether the >1 km² dataset is one contiguous scan or the combined area of many plots. v3 states it as you described it, with a "to be completed" on extent.
- **"RayTerrain".** No tool by this name appears in the pipeline document. Terrain extraction is `rayextract terrain`. v3 uses the documented command names. If you used a different terrain tool, tell me.
- **Plot count.** 36 (meeting notes), ~34 scanned, 35 (topic description), 37 site IDs (`TreeData.csv`). Unchanged from v2 and still unresolved.
- **Assessment split.** Still unresolved: "50% report / 50% GitHub" vs the 50/30/20 marking criteria. See the v2 notes.

### Limitations stated in the report
- Stages 4–5 have no results yet.
- Effort and error frequencies are not quantified.
- Single operator, so decisions are subjective.
- The refined trees are not independent of the automated output.
- Only selected ROIs are covered, not the full dataset.
- The Excel–CSV relationship is unconfirmed.
- No age estimation, because there is no validated method or data.

---

## 5. Length and compilation

- **Pages:** 12, compiled with the official `llncs.cls` v2.24 at default font, margins and spacing.
- **Compiler output:** no errors and no overfull or underfull boxes. All citations and cross-references resolve.
- **Word count:** about 4,900 by pdftotext, including tables, captions and references.
  - This is slightly below the brief's 5,000 minimum.
  - About 400 of those words are "To be completed" marker text.
  - The page limit is the binding constraint. It will tighten further once Fig. 2 becomes a real image and Table 3 gains values.
- **Recommendations:**
  - Ask the coordinator which limit governs (12 pages or at least 5,000 words).
  - When adding results, replace marker text rather than adding to it.
  - If space runs out, cut Fig. 3 (the diameter ECDF) first. Its key numbers are already in the text.
