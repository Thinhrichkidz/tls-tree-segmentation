# Terrestrial laser scanning tree segmentation project

Reorganised on 2 October 2026. All 925 original files were retained with their original filenames. The original files total 67,275,399,801 bytes.

## Layout

```text
data/
  raw/{WSF_ML1C,WSL_ML2A}/
  cropped/WSL_ML2A/{35x35,55x55}/{full,2cm,3cm}/
outputs/WSL_ML2A/{35x35,55x55}/{2cm,3cm}/
  raycloud/       RayCloudTools raycloud PLY
  terrain/        Terrain mesh PLY
  segmentation/   Combined segmented PLY
  metadata/       Combined tree TXT
  unassigned/     Segment -1 PLY
  trees/
    clouds/       Individual numbered tree PLY
    metadata/     Individual numbered tree TXT
    meshes/       Combined tree mesh PLY
scripts/          Reorganisation and undo helper
logs/             Complete original-to-current file mapping, sizes and timestamps
misc/             Docker test TXT
```

Output roles are inferred from the established filenames. Matching tree PLY and TXT files retain their tree IDs within each processing run. IDs from different runs should not be assumed to identify the same physical tree.

No duplicates or intermediate files were discarded. The two raw datasets are kept separately. No propagated outputs or original processing scripts were present.

## Trace or undo the moves

`logs/reorganization-2026-10-02.json` records every original and current relative path, exact file size, and original UTC modification timestamp.

Preview restoration from PowerShell:

```powershell
& 'D:\22083142\scripts\reorganize-project.ps1' -Direction Undo
```

Apply restoration:

```powershell
& 'D:\22083142\scripts\reorganize-project.ps1' -Direction Undo -Apply
```

The helper checks all files before moving and refuses destination collisions or changed file metadata. Undo recreates the original empty folders. It retains these new documentation, manifest, and helper files, and may leave empty folders from the new structure.
