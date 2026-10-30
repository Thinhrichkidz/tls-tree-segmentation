# v4e (28 Oct 2026): changes against v4d

All 15 validation checks pass; only tree_035 changed (user cleaned it a second time at 1.1-1.5 m).
Baseline: `session4_claude_20261028/state/` (v4d baseline kept as CloudCompare_review_v2_v4d_baseline.csv).

## tree_035
- Points 73,251 -> 65,770. Height unchanged (12.372 m, REVIEW).
- DBH still N/A. Slice diameters 1.1-1.5 m: 17.0, 16.3, 19.8, 24.3, 18.5 cm. The 1.4 m slice is about 5 cm wider than the
  rest (branch stub or bump), so slice consistency fails narrowly: spread 16 % (v4) / 17 % (RANSAC) against a 15 % limit.
  The fits (v4 19.3 cm, RANSAC 18.8 cm) suggest about 18-19 cm, but no value is released. The rule was not relaxed for one tree.
- Crown: area 15.42 -> 15.04 m2, envelope volume 100.2 -> 79.6 m3 (crown base 3.0 m, so points above 3 m were removed).

## Totals (unchanged from v4d)
DBH column: 43 VALID, 43 REVIEW, 77 N/A. Estimated: 40. Any DBH: 126 of 163 (v3: 80).
DBH work stopped here (user, 28 Oct 2026). 055 and 137 cannot be fixed by cleaning; 023 and 147 unlikely.
