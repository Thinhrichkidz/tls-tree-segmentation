# v5d (28 Oct 2026): changes against v5c

All 15 validation checks pass. Height VALID 79 -> **81** (100, 124), REVIEW 84 -> 82. No tree got worse. Only 100, 124, 137, 083 changed.

## Source edit by Claude, at the user's request
Isolated floating points above the crown top deleted directly in `CloudCompare_review_v2`.
- Only the vertices above the stated Z were deleted. Every other vertex, its colour, normals and the binary format were verified identical.
- Originals backed up byte-for-byte; edit log written. Both are in `session4_claude_20261028/backup_before_floating_point_removal_20261028/`.
- To undo, copy a backup back.

| Tree | Points removed (Z) | Height | Status | Crown volume (envelope) |
|---|---|---|---|---|
| 100 | 3 (720.19, 713.99, 713.93) | 26.803 -> **17.280** (-9.52 m) | REVIEW -> **VALID** | 95.2 -> 36.4 m3 (REVIEW -> VALID) |
| 124 | 1 (713.08) | 21.118 -> **13.407** (-7.71 m) | REVIEW -> **VALID** | 77.0 -> 56.3 m3 (REVIEW -> VALID) |
| 137 | 4 (713.56-713.69) | 25.545 -> **16.720** (-8.83 m) | REVIEW | 120.2 -> 59.4 m3 (REVIEW -> VALID) |
| 083 | 1 (716.44) | 20.765 -> **16.775** (-3.99 m) | REVIEW | 269.3 -> 231.8 m3 |

The floating points were also inflating the convex crown envelope, so crown volumes fell sharply.

Remaining reasons:
- **137:** the stem axis refitted on the edited cloud meets the ground 1.09 m from the foot used for the ground height.
- **083:** the sparse real top is 0.21 m above the dense crown top, just over the 0.2 m rule. Kept on purpose: it is connected crown, not floating.

## Detached fragments (not edited; user will review at home, 28 Oct 2026)
- **078:** one piece of 7,421 points, 18.6-24.4 m above ground, 0.38 m from the main crown (tree top ~24.8 m).
  Most likely this tree's own upper crown separated by a small scan gap.
- **082:** one piece of 2,631 points, -0.4 to 3.1 m above ground, 0.29 m from the trunk.
  Most likely understorey or ground, not this tree. Does not affect height.
