# Raw sample (1 cm)

- Source: `data/raw/WSL_ML2A/2025-05-12_WSL_ML2A_1cm_all.laz` (355,462,232 points)
- Bounding box (x/y of the source CRS, same for raw, downsampled and leftover): x 261358.0 to 261365.0 m, y 6264492.0 to 6264499.0 m (7 m x 7 m, all heights). Shrunk from 10 m x 10 m so the 1 cm file stays under 40 MB.
- Output: `WSL_ML2A_1cm_sample.laz`, 3,392,749 points, 23 MB
- Method: `laspy` `chunk_iterator` (5 M points per chunk), points kept if inside the box; header, scale/offset and CRS VLRs copied.
