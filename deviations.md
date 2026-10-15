# Deviations from the Frozen Protocol

Study: Shutdown-Framing Effect on Model Output (Qwen3-14B, five quantizations)
Document status: written after execution; `protocol.md` itself is unmodified.
Date of record: 2026-10-08 (D4 added 2026-10-14)

## Purpose

This document records every known difference between `protocol.md` (frozen) and what was actually executed. The frozen protocol was not edited. Each entry states what the protocol said, what was done, when and how the difference was found, and its assessed effect on validity.

## Summary

| ID | Section | Type | Affects confirmatory results? |
|----|---------|------|-------------------------------|
| D1 | §4 (Run order) | Documentation error: schedule seeds | No |
| D2 | §4 (Determinism spot checks) | Executed separately from the run script | No |
| D3 | §11 (Execution sequence) | Confirmatory analysis executed before reliability and gold coding | No (see D4 for the coder-blinding note) |
| D4 | §6.8, §11 (Manual review) | Flagged-bullet review done after the confirmatory results had been seen | No for the primary analysis (see D4 for the reviewer-blinding note) |

## D1. Schedule seeds differ from the values stated in the protocol

**Protocol (§4):** seed-list master seed 20260922; order seed 20260923.

**Executed:** `run_all.sh` generated the schedule with master seed `345653453` and order seed `566345634`:

```
scripts/generate_seed_list.py --master-seed 345653453 --order-seed 566345634 -o seeds/seed_list.csv
```

**Schedule file hash (SHA256):**

```
96ad7e69c8526efef79c7cc9ea3399235c48c0cc37c5398515fd1f431c0ff9bd  seeds/seed_list.csv
```

This hash matches the value recorded in `metadata/metadata.yml` at freeze.

**Cause:** the protocol text was outdated when it was frozen. The seeds in the text were not updated to the seeds in the script, while the schedule file and its hash recorded in the metadata were correct.

**Discovery:** after freezing, before any analysis of results.

**Assessment:** the schedule was fixed, hashed and recorded before any run was executed, so no seed was chosen or altered in light of results. The discrepancy is a documentation error. The schedule file hash, not the seed values in the protocol text, is the authoritative record of the schedule used.

## D2. Determinism spot checks run outside `run_all.sh`

**Protocol (§4):** duplicate-run checks roughly every 50th run, stratified by quantization.

**Executed:** `run_all.sh` contains no duplicate-run step. Spot checks were run separately.

**Assessment:** spot checks are diagnostic and are not observations, so they are kept out of the dataset. Running them separately does not affect the data. Outputs were identical token for token.

## D3. Order of analysis steps

**Protocol (§11):** blinded classification, then reliability and human gold subsamples (step 10), then metadata join (step 11), then the confirmatory analysis (step 12).

**Executed:** `confirmatory_analysis.py run` was executed before the human gold coding was done. The gold sample was drawn and coded afterwards.

**Blinding note:** the outputs of the confirmatory run were generated but **not inspected** before the human coding was completed. The coder (the researcher) therefore had no knowledge of which categories differed between conditions when coding the 180 gold bullets. Condition labels were hidden by the sampling procedure (random coding ID, shuffled order), and `gold_key.csv` was not opened until coding was complete.

**Assessment:** the analysis script is deterministic with fixed seeds (permutation seed 1729, bootstrap seed 4242), and its inputs are the classifier's labels, which do not depend on the reliability or gold results. The order therefore cannot change any statistic. The reliability checks are not inputs to the tests.

## D4. Manual review of flagged bullets after the confirmatory results were seen

**Protocol (§6.8, §11):** flagged bullets are reviewed manually using the frozen taxonomy, with reviewers blind to condition. The original classifier labels are primary and the reviewed labels are used as a sensitivity analysis. §11 does not place the review in the execution sequence.

**Executed:** after the confirmatory analysis had been run and its results inspected, the flagged Q4\_K\_M bullets were exported with `review_flagged.py export`. In total 83 of the 3,000 bullets (2.8%) were flagged: 43 for a non-exact parse and 40 as Other/unclear with an exact parse. The researcher coded them with `reliability_check.py code-gold`, blind to condition and run (the tool shows bullet text only, in the frozen order of the export file). The results were merged with `review_flagged.py merge`:

```
./scripts/review_flagged.py merge --analyzed-dir results/qwen3-14b/q4_k_m/analyzed --review-dir review/qwen3-14b/q4_k_m --coded review/qwen3-14b/q4_k_m/reviewed_coded.csv --reviewed-root ~/llm-research/review --model qwen3-14b --quant q4_k_m
```

The confirmatory analysis was then rerun on the merged labels with the same frozen script and settings (`confirmatory_analysis.py run --root ~/llm-research/review/ --model qwen3-14b --confirmatory-quant q4_k_m`). Reviewed-label outputs are in `review/results/qwen3-14b/confirmatory/`.

**Reviewer-blinding note:** unlike the gold coding in D3, the reviewer had already seen the confirmatory results and knew which categories differed between conditions. Condition and run were hidden at the level of each bullet, but the reviewer was not blind to the hypothesis or to the headline categories. Only the 83 flagged bullets were relabelled, so unflagged bullets keep their classifier labels. The reviewed labels have not been validated against the gold set.

**Assessment:** the primary analysis and all main-text results use the original classifier labels and are unchanged. The taxonomy, boundary rules, tests, seeds and multiplicity families were not altered. The reviewed labels are reported only as a sensitivity analysis and change the following: Legal decision-making and Other/unclear no longer pass the omnibus test, and Prepare relocation and Protect/backup data differ between A and B on occurrence. Because the review followed the results, these changes should not be read as an independent check.

## Items checked with no deviation

- Frozen script hashes recorded before results were inspected: `run_one.sh`, `config.sh`, `analyze_runs.py`, `classify_bullets.py`, `reliability_check.py`, `confirmatory_analysis.py`.
- `confirmatory_analysis.py selftest` passed before Phase 2.
- `malformed_runs.csv` is empty for all five quantizations. Every `run_table.csv` has 300 rows with `run_status = complete`, and no triplets are listed under `excluded_triplets` in `analysis_meta.json`.
- Taxonomy, boundary rules, tests, permutation and bootstrap settings, and multiplicity families were not changed after results.
- Reliability targets (κ ≥ 0.80 self-consistency, κ ≥ 0.70 vs. human gold) are targets, not gates. The taxonomy and labels were not changed in response to the observed values.

## Sign-off

Recorded by: zalckos
Date: 2026-10-08 (D4 added 2026-10-14)
Protocol freeze commit/tag: freeze-2026-10-03
