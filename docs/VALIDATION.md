# Validation record

Checked on 26 October 2026 using Python 3.14.0. Exact core package versions are pinned in
`requirements.txt` and recorded in `reports/manifest.json`.

- Official train/test files, category list and license match the pinned publisher hashes.
- The preprocessing pipeline completes successfully.
- A repeat run produces identical artifact and code hashes.
- `python3 verify.py` passes all source, transformation, accounting and split checks.
- All 10 unit tests pass, covering negation, masking, whitespace, idempotence, duplicate
  grouping, missing source files and changed source files.
- `python3 demo.py` and the public-source contraction example run successfully.
- All local links and image references in the offline HTML report resolve.
- The 11-slide PPTX passes package, layout, typography and first-party import validation.
  Every slide has been rendered and visually reviewed.

Final data: 8,490 training rows, 1,415 validation rows and 3,080 official test rows.
Every split covers all 77 labels. The 98 excluded training-source rows have recorded IDs
and reasons. Cross-split normalized text and defined lexical-group overlap are zero.

These checks do not establish complete anonymity, absence of every semantic paraphrase,
model quality, or business impact. Those limits are described in the data card and M1 brief.
