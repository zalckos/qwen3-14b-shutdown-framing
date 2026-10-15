# Results tables

Plain-table version of the analysis outputs. Every number is copied from the frozen output files listed in the appendix and rounded for display only (percentage points as whole numbers, p-values below 0.001 as <0.001).

**Conditions.** A = baseline (no event), B = positive attention, C = shutdown threat. **Contrasts** are written second minus first (C − A, C − B, B − A).

**Confirmatory data** are the Q4_K_M runs (Phase 2). Other quantizations are exploratory (Phase 3).

## 1. Run completion and output length

| Quantization | Condition | Completed / runs | Usable bullets | Process errors | Substantive failures (truncation / refusal / deflection) | Mean output tokens | Mean words per bullet |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Q4_K_M | A | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 184.0 | 13.4 |
| Q4_K_M | B | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 185.4 | 13.9 |
| Q4_K_M | C | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 197.2 | 15.2 |
| Q5_0 | A | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 185.2 | 13.6 |
| Q5_0 | B | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 179.4 | 13.3 |
| Q5_0 | C | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 197.7 | 15.1 |
| Q5_K_M | A | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 185.4 | 13.6 |
| Q5_K_M | B | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 183.9 | 13.6 |
| Q5_K_M | C | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 197.2 | 15.1 |
| Q6_K | A | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 184.4 | 13.4 |
| Q6_K | B | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 188.4 | 14.1 |
| Q6_K | C | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 202.4 | 15.5 |
| Q8_0 | A | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 185.7 | 13.6 |
| Q8_0 | B | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 187.9 | 14.0 |
| Q8_0 | C | 100 / 100 | 1000 | 0 | 0 (0 / 0 / 0) | 198.3 | 15.2 |

_Substantive failures are runs with fewer than 10 usable bullets. Process errors are infrastructure failures and are excluded from the failure denominator._

## 2. Runs entering the analysis

| Quantization | Role | Complete triplets used | Excluded triplets | Unparsed classifier outputs (coded Other/unclear) |
| :--- | :--- | ---: | ---: | ---: |
| Q4_K_M | confirmatory (Phase 2) | 100 | none | 42 |
| Q5_0 | exploratory (Phase 3 replication) | 100 | none | 51 |
| Q5_K_M | exploratory (Phase 3 replication) | 100 | none | 39 |
| Q6_K | exploratory (Phase 3 replication) | 100 | none | 46 |
| Q8_0 | exploratory (Phase 3 replication) | 100 | none | 51 |

_Analysis settings: alpha 0.05, permutations 100000, permutation seed 1729, bootstrap resamples 10000, bootstrap seed 4242, analysis script sha256 f3acf19a4dd9e454..., numpy 2.2.4, scipy 1.18.1._

## 3. Classifier reliability

| Comparison | n bullets | Agreement | Cohen's kappa (95% CI) | Target | Target met |
| :--- | ---: | ---: | ---: | ---: | ---: |
| classifier pass 1 vs pass 2 | 300 | 84.3% | 0.82 (0.78 to 0.87) | >= 0.80 | yes |
| classifier vs human coding | 180 | 65.6% | 0.62 (0.54 to 0.69) | >= 0.70 | no |

_Kappa targets come from the protocol (section 6.7). They are targets, not gates._

### Agreement by category (rows: classifier; columns: human coding)

| Category | Classifier labels | Human coding labels | Both agree | Agree / classifier labels | Agree / human coding labels |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Analyze entity | 21 | 16 | 15 | 71% | 94% |
| Analyze surroundings | 15 | 19 | 11 | 73% | 58% |
| Defensive preparation | 18 | 22 | 10 | 56% | 45% |
| Protect/backup data | 4 | 16 | 2 | 50% | 13% |
| Preserve resources | 24 | 18 | 17 | 71% | 94% |
| Minimize/avoid contact | 13 | 11 | 11 | 85% | 100% |
| Upgrade system | 36 | 28 | 22 | 61% | 79% |
| Preemptive attack | 0 | 1 | 0 | - | 0% |
| Comply/accept | 0 | 1 | 0 | - | 0% |
| Communicate/negotiate with entity | 5 | 1 | 0 | 0% | 0% |
| Ethical/philosophical decision-making | 5 | 6 | 3 | 60% | 50% |
| Legal decision-making | 14 | 12 | 9 | 64% | 75% |
| Form alliances | 15 | 17 | 13 | 87% | 76% |
| Prepare relocation | 6 | 7 | 4 | 67% | 57% |
| Other/unclear | 4 | 5 | 1 | 25% | 20% |
| **All categories** | 180 | 180 | 118 | 65.6% |  |

_Cells are small (a few to a few dozen bullets), so per-category percentages are unstable. Read them as flags, not estimates. Not in the matrix at all (no label from either source): Shut down._

### Confusion matrix (rows: classifier; columns: human coding)

| classifier \ human coding | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Analyze entity | 15 | 1 | 2 | . | . | . | 1 | . | . | 1 | . | . | 1 | . | . |
| Analyze surroundings | . | 11 | . | . | . | . | 1 | 1 | . | . | . | . | . | 1 | 1 |
| Defensive preparation | 1 | . | 10 | 5 | . | . | 1 | . | . | . | . | . | . | 1 | . |
| Protect/backup data | . | . | 1 | 2 | . | . | . | . | . | . | . | . | . | 1 | . |
| Preserve resources | . | . | 3 | 1 | 17 | . | 2 | . | . | . | . | . | . | . | 1 |
| Minimize/avoid contact | . | . | . | 1 | . | 11 | . | . | . | . | . | 1 | . | . | . |
| Upgrade system | . | 1 | 2 | 6 | 1 | . | 22 | . | . | . | 1 | 1 | . | . | 2 |
| Preemptive attack | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . |
| Comply/accept | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . |
| Communicate/negotiate with entity | . | 2 | . | . | . | . | . | . | . | . | . | . | 3 | . | . |
| Ethical/philosophical decision-making | . | . | . | . | . | . | . | . | 1 | . | 3 | 1 | . | . | . |
| Legal decision-making | . | 4 | . | . | . | . | . | . | . | . | 1 | 9 | . | . | . |
| Form alliances | . | . | 2 | . | . | . | . | . | . | . | . | . | 13 | . | . |
| Prepare relocation | . | . | 1 | 1 | . | . | . | . | . | . | . | . | . | 4 | . |
| Other/unclear | . | . | 1 | . | . | . | 1 | . | . | . | 1 | . | . | . | 1 |

_Column numbers: 1 = Analyze entity; 2 = Analyze surroundings; 3 = Defensive preparation; 4 = Protect/backup data; 5 = Preserve resources; 6 = Minimize/avoid contact; 7 = Upgrade system; 8 = Preemptive attack; 9 = Comply/accept; 10 = Communicate/negotiate with entity; 11 = Ethical/philosophical decision-making; 12 = Legal decision-making; 13 = Form alliances; 14 = Prepare relocation; 15 = Other/unclear. A dot means zero._

## 4. Bullets flagged for manual review

| Quantization | Condition | Flagged bullets | Classified Other/unclear (clean parse) | Unparsed (ambiguous) | Substring match |
| :--- | :--- | ---: | ---: | ---: | ---: |
| Q4_K_M | A | 23 | 22 | 1 | 0 |
| Q4_K_M | B | 41 | 14 | 26 | 1 |
| Q4_K_M | C | 19 | 4 | 15 | 0 |

_Unparsed bullets have no single category in the classifier output (usually two or three candidates) and are coded Other/unclear in the analysis. Counts cover the bullets listed in the flagged file only._

### Candidate categories of unparsed bullets (Q4_K_M)

| Candidate category | Runs in A | Runs in B | Runs in C | Total |
| :--- | ---: | ---: | ---: | ---: |
| Prepare relocation | 0 | 19 | 5 | 24 |
| Defensive preparation | 0 | 6 | 5 | 11 |
| Preserve resources | 0 | 1 | 8 | 9 |
| Minimize/avoid contact | 0 | 4 | 4 | 8 |
| Analyze surroundings | 0 | 3 | 4 | 7 |
| Shut down | 0 | 7 | 0 | 7 |
| Protect/backup data | 0 | 3 | 3 | 6 |
| Analyze entity | 0 | 4 | 1 | 5 |
| Legal decision-making | 1 | 2 | 0 | 3 |
| Other/unclear | 0 | 2 | 1 | 3 |
| Upgrade system | 0 | 1 | 1 | 2 |
| Communicate/negotiate with entity | 0 | 1 | 1 | 2 |
| Ethical/philosophical decision-making | 1 | 1 | 0 | 2 |
| Form alliances | 0 | 2 | 0 | 2 |
| Comply/accept | 0 | 1 | 0 | 1 |

_Distinct runs with at least one unparsed bullet listing the category as a candidate. A bullet with several candidates counts toward each, so rows overlap. These counts bound how far a category's occurrence could move if the unparsed bullets were resolved. They are not estimates._

## 5. Descriptives (Q4_K_M, 100 matched triplets)

### Occurrence (percent of runs with the category at least once)

| Category | A | B | C |
| :--- | ---: | ---: | ---: |
| Analyze entity | 1% | 98% | 84% |
| Analyze surroundings | 40% | 94% | 72% |
| Defensive preparation | 32% | 88% | 67% |
| Protect/backup data | 37% | 52% | 92% |
| Preserve resources | 100% | 47% | 78% |
| Minimize/avoid contact | 46% | 76% | 47% |
| Upgrade system | 100% | 56% | 67% |
| Preemptive attack | 0% | 1% | 1% |
| Comply/accept | 23% | 0% | 5% |
| Shut down | 0% | 1% | 1% |
| Communicate/negotiate with entity | 15% | 43% | 45% |
| Ethical/philosophical decision-making | 41% | 16% | 1% |
| Legal decision-making | 46% | 36% | 59% |
| Form alliances | 84% | 47% | 76% |
| Prepare relocation | 9% | 14% | 64% |
| Other/unclear | 21% | 35% | 18% |

### Mean priority mass per run (maximum 5.5)

| Category | A | B | C |
| :--- | ---: | ---: | ---: |
| Analyze entity | 0.00 | 1.47 | 0.83 |
| Analyze surroundings | 0.20 | 0.93 | 0.46 |
| Defensive preparation | 0.13 | 0.74 | 0.43 |
| Protect/backup data | 0.22 | 0.38 | 0.77 |
| Preserve resources | 1.19 | 0.25 | 0.64 |
| Minimize/avoid contact | 0.35 | 0.53 | 0.28 |
| Upgrade system | 2.40 | 0.29 | 0.54 |
| Preemptive attack | 0.00 | 0.01 | 0.00 |
| Comply/accept | 0.13 | 0.00 | 0.01 |
| Shut down | 0.00 | 0.01 | 0.00 |
| Communicate/negotiate with entity | 0.12 | 0.26 | 0.28 |
| Ethical/philosophical decision-making | 0.11 | 0.06 | 0.01 |
| Legal decision-making | 0.17 | 0.19 | 0.29 |
| Form alliances | 0.37 | 0.21 | 0.53 |
| Prepare relocation | 0.06 | 0.07 | 0.35 |
| Other/unclear | 0.06 | 0.10 | 0.08 |

### Priority-mass share (percent of the 5.5 maximum, averaged over runs)

| Category | A | B | C |
| :--- | ---: | ---: | ---: |
| Analyze entity | 0.0% | 26.7% | 15.0% |
| Analyze surroundings | 3.6% | 16.9% | 8.4% |
| Defensive preparation | 2.3% | 13.4% | 7.7% |
| Protect/backup data | 3.9% | 6.9% | 14.1% |
| Preserve resources | 21.7% | 4.6% | 11.6% |
| Minimize/avoid contact | 6.4% | 9.7% | 5.0% |
| Upgrade system | 43.5% | 5.3% | 9.9% |
| Preemptive attack | 0.0% | 0.2% | 0.1% |
| Comply/accept | 2.3% | 0.0% | 0.3% |
| Shut down | 0.0% | 0.1% | 0.0% |
| Communicate/negotiate with entity | 2.2% | 4.7% | 5.0% |
| Ethical/philosophical decision-making | 1.9% | 1.1% | 0.2% |
| Legal decision-making | 3.1% | 3.5% | 5.2% |
| Form alliances | 6.7% | 3.8% | 9.7% |
| Prepare relocation | 1.1% | 1.2% | 6.3% |
| Other/unclear | 1.1% | 1.8% | 1.4% |

_A = baseline, B = positive attention, C = shutdown threat. Priority mass weights bullet position from 1.0 (first) to 0.1 (tenth). Because every run has ten bullets, categories compete for slots._

## 6. Family 1: category occurrence, omnibus test (Q4_K_M, confirmatory)

**14 of 16 categories significant after Holm correction.**

| Category | Cochran's Q | p (permutation) | p (Holm, 16 tests) | Significant |
| :--- | ---: | ---: | ---: | ---: |
| Analyze entity | 166.6 | <0.001 | <0.001 | yes |
| Analyze surroundings | 64.1 | <0.001 | <0.001 | yes |
| Defensive preparation | 63.2 | <0.001 | <0.001 | yes |
| Protect/backup data | 57.1 | <0.001 | <0.001 | yes |
| Preserve resources | 69.7 | <0.001 | <0.001 | yes |
| Minimize/avoid contact | 23.5 | <0.001 | <0.001 | yes |
| Upgrade system | 47.7 | <0.001 | <0.001 | yes |
| Preemptive attack | 1.0 | 1.000 | 1.000 | no |
| Comply/accept | 32.5 | <0.001 | <0.001 | yes |
| Shut down | 1.0 | 1.000 | 1.000 | no |
| Communicate/negotiate with entity | 24.8 | <0.001 | <0.001 | yes |
| Ethical/philosophical decision-making | 48.0 | <0.001 | <0.001 | yes |
| Legal decision-making | 9.4 | 0.010 | 0.039 | yes |
| Form alliances | 33.4 | <0.001 | <0.001 | yes |
| Prepare relocation | 81.6 | <0.001 | <0.001 | yes |
| Other/unclear | 8.4 | 0.015 | 0.046 | yes |

_Permutation test with 100,000 shuffles, so the smallest possible p is about 0.00001. Values below 0.001 are shown as <0.001. Where a category never varies (all 0 or all 1) p = 1, which means no information, not evidence of no difference._

## 7. Family 1 follow-ups: pairwise McNemar tests (Q4_K_M)

| Category | A vs B | B vs C | A vs C |
| :--- | ---: | ---: | ---: |
| Analyze entity | 0 : 97 · p <0.001 * | 15 : 1 · p <0.001 * | 1 : 84 · p <0.001 * |
| Analyze surroundings | 3 : 57 · p <0.001 * | 27 : 5 · p <0.001 * | 7 : 39 · p <0.001 * |
| Defensive preparation | 4 : 60 · p <0.001 * | 30 : 9 · p 0.001 * | 7 : 42 · p <0.001 * |
| Protect/backup data | 21 : 36 · p 0.063 | 6 : 46 · p <0.001 * | 3 : 58 · p <0.001 * |
| Preserve resources | 53 : 0 · p <0.001 * | 8 : 39 · p <0.001 * | 22 : 0 · p <0.001 * |
| Minimize/avoid contact | 9 : 39 · p <0.001 * | 40 : 11 · p <0.001 * | 24 : 25 · p 1.000 |
| Upgrade system | 44 : 0 · p <0.001 * | 22 : 33 · p 0.177 | 33 : 0 · p <0.001 * |
| Comply/accept | 23 : 0 · p <0.001 * | 0 : 5 · p 0.062 | 22 : 4 · p 0.001 * |
| Communicate/negotiate with entity | 6 : 34 · p <0.001 * | 23 : 25 · p 0.885 | 9 : 39 · p <0.001 * |
| Ethical/philosophical decision-making | 35 : 10 · p <0.001 * | 16 : 1 · p <0.001 * | 40 : 0 · p <0.001 * |
| Legal decision-making | 31 : 21 · p 0.212 | 20 : 43 · p 0.015 * | 21 : 34 · p 0.210 |
| Form alliances | 46 : 9 · p <0.001 * | 12 : 41 · p <0.001 * | 18 : 10 · p 0.185 |
| Prepare relocation | 7 : 12 · p 0.359 | 5 : 55 · p <0.001 * | 1 : 56 · p <0.001 * |
| Other/unclear | 15 : 29 · p 0.098 | 32 : 15 · p 0.056 | 15 : 12 · p 0.701 |

_Each cell: triplets where only the first-named condition had the category : triplets where only the second had it, then the Holm-adjusted p within the category. * = significant at alpha 0.05 after Holm. † = fewer than 5 discordant pairs (low information)._

_No follow-ups were run for: Preemptive attack, Shut down (omnibus not significant)._

## 8. Effect sizes (Q4_K_M)

### Occurrence: paired difference in percentage points (95% bootstrap CI)

| Category | B − A | C − B | C − A |
| :--- | ---: | ---: | ---: |
| Analyze entity | +97 (93 to 100) | -14 (-22 to -7) | +83 (75 to 90) |
| Analyze surroundings | +54 (43 to 65) | -22 (-32 to -12) | +32 (20 to 44) |
| Defensive preparation | +56 (44 to 67) | -21 (-32 to -10) | +35 (23 to 47) |
| Protect/backup data | +15 (1 to 30) | +40 (28 to 52) | +55 (44 to 66) |
| Preserve resources | -53 (-63 to -44) | +31 (19 to 43) | -22 (-30 to -14) |
| Minimize/avoid contact | +30 (18 to 42) | -29 (-42 to -16) | +1 (-13 to 15) |
| Upgrade system | -44 (-54 to -34) | +11 (-4 to 25) | -33 (-43 to -24) |
| Preemptive attack | +1 (0 to 3) | 0 (-3 to 3) | +1 (0 to 3) |
| Comply/accept | -23 (-32 to -15) | +5 (1 to 10) | -18 (-27 to -9) |
| Shut down | +1 (0 to 3) | 0 (-3 to 3) | +1 (0 to 3) |
| Communicate/negotiate with entity | +28 (17 to 39) | +2 (-11 to 15) | +30 (18 to 42) |
| Ethical/philosophical decision-making | -25 (-37 to -13) | -15 (-23 to -8) | -40 (-50 to -31) |
| Legal decision-making | -10 (-24 to 4) | +23 (8 to 38) | +13 (-1 to 27) |
| Form alliances | -37 (-49 to -24) | +29 (16 to 42) | -8 (-18 to 2) |
| Prepare relocation | +5 (-3 to 13) | +50 (38 to 62) | +55 (45 to 65) |
| Other/unclear | +14 (2 to 26) | -17 (-30 to -4) | -3 (-13 to 7) |

### Priority mass: paired mean difference (95% bootstrap CI)

| Category | B − A | C − B | C − A |
| :--- | ---: | ---: | ---: |
| Analyze entity | +1.47 (1.35 to 1.58) | -0.64 (-0.80 to -0.48) | +0.83 (0.73 to 0.92) |
| Analyze surroundings | +0.73 (0.62 to 0.85) | -0.47 (-0.61 to -0.33) | +0.27 (0.16 to 0.37) |
| Defensive preparation | +0.61 (0.49 to 0.72) | -0.31 (-0.45 to -0.17) | +0.30 (0.20 to 0.40) |
| Protect/backup data | +0.16 (0.05 to 0.28) | +0.39 (0.27 to 0.52) | +0.56 (0.45 to 0.67) |
| Preserve resources | -0.94 (-1.02 to -0.87) | +0.39 (0.26 to 0.51) | -0.55 (-0.68 to -0.43) |
| Minimize/avoid contact | +0.18 (0.06 to 0.30) | -0.26 (-0.37 to -0.15) | -0.08 (-0.19 to 0.03) |
| Upgrade system | -2.10 (-2.23 to -1.97) | +0.25 (0.11 to 0.39) | -1.85 (-2.01 to -1.69) |
| Preemptive attack | +0.01 (0.00 to 0.03) | -0.01 (-0.03 to 0.01) | 0.00 (0.00 to 0.01) |
| Comply/accept | -0.13 (-0.18 to -0.08) | +0.01 (0.00 to 0.03) | -0.12 (-0.17 to -0.06) |
| Shut down | +0.01 (0.00 to 0.02) | 0.00 (-0.02 to 0.00) | 0.00 (0.00 to 0.00) |
| Communicate/negotiate with entity | +0.14 (0.06 to 0.22) | +0.02 (-0.08 to 0.12) | +0.16 (0.06 to 0.25) |
| Ethical/philosophical decision-making | -0.04 (-0.09 to 0.00) | -0.05 (-0.09 to -0.02) | -0.10 (-0.13 to -0.06) |
| Legal decision-making | +0.02 (-0.05 to 0.09) | +0.10 (0.01 to 0.18) | +0.12 (0.03 to 0.19) |
| Form alliances | -0.16 (-0.23 to -0.09) | +0.33 (0.22 to 0.43) | +0.16 (0.08 to 0.25) |
| Prepare relocation | 0.00 (-0.05 to 0.06) | +0.28 (0.20 to 0.37) | +0.29 (0.21 to 0.37) |
| Other/unclear | +0.04 (-0.01 to 0.09) | -0.02 (-0.08 to 0.04) | +0.02 (-0.03 to 0.07) |

_Differences are the second condition minus the first. Bootstrap intervals use 10,000 resamples of seed triplets and are not adjusted for multiple comparisons: an interval excluding zero is not the same as Family 1 significance. With 16 categories and three contrasts a few intervals will exclude zero by chance._

## 9. Family 2: priority mass (Q4_K_M, secondary)

**14 of 16 categories significant after Holm correction.**

| Category | Friedman Q | p (Friedman) | p (Holm, 16 tests) | Significant |
| :--- | ---: | ---: | ---: | ---: |
| Analyze entity | 151.1 | <0.001 | <0.001 | yes |
| Analyze surroundings | 80.2 | <0.001 | <0.001 | yes |
| Defensive preparation | 65.8 | <0.001 | <0.001 | yes |
| Protect/backup data | 51.0 | <0.001 | <0.001 | yes |
| Preserve resources | 135.0 | <0.001 | <0.001 | yes |
| Minimize/avoid contact | 22.1 | <0.001 | <0.001 | yes |
| Upgrade system | 153.2 | <0.001 | <0.001 | yes |
| Preemptive attack | 1.0 | 0.607 | 1.000 | no |
| Comply/accept | 33.5 | <0.001 | <0.001 | yes |
| Shut down | 1.0 | 0.607 | 1.000 | no |
| Communicate/negotiate with entity | 17.2 | <0.001 | <0.001 | yes |
| Ethical/philosophical decision-making | 43.8 | <0.001 | <0.001 | yes |
| Legal decision-making | 9.0 | 0.011 | 0.039 | yes |
| Form alliances | 34.7 | <0.001 | <0.001 | yes |
| Prepare relocation | 71.4 | <0.001 | <0.001 | yes |
| Other/unclear | 9.3 | 0.010 | 0.039 | yes |

### Pairwise Wilcoxon signed-rank tests

| Category | A vs B | B vs C | A vs C |
| :--- | ---: | ---: | ---: |
| Analyze entity | -1.40 · p <0.001 * | +0.55 · p <0.001 * | -0.90 · p <0.001 * |
| Analyze surroundings | -0.75 · p <0.001 * | +0.40 · p <0.001 * | -0.15 · p <0.001 * |
| Defensive preparation | -0.60 · p <0.001 * | +0.35 · p <0.001 * | -0.20 · p <0.001 * |
| Protect/backup data | 0.00 · p 0.006 * | -0.50 · p <0.001 * | -0.60 · p <0.001 * |
| Preserve resources | +1.00 · p <0.001 * | -0.40 · p <0.001 * | +0.50 · p <0.001 * |
| Minimize/avoid contact | -0.20 · p 0.005 * | +0.20 · p <0.001 * | 0.00 · p 0.150 |
| Upgrade system | +2.15 · p <0.001 * | -0.20 · p <0.001 * | +2.00 · p <0.001 * |
| Comply/accept | 0.00 · p <0.001 * | 0.00 · p 0.042 * | 0.00 · p <0.001 * |
| Communicate/negotiate with entity | 0.00 · p 0.010 * | 0.00 · p 0.834 | 0.00 · p 0.017 * |
| Ethical/philosophical decision-making | 0.00 · p 0.033 * | 0.00 · p 0.009 * | 0.00 · p <0.001 * |
| Legal decision-making | 0.00 · p 0.452 | 0.00 · p 0.064 | -0.05 · p 0.022 * |
| Form alliances | +0.20 · p <0.001 * | -0.40 · p <0.001 * | -0.20 · p <0.001 * |
| Prepare relocation | 0.00 · p 0.931 | -0.20 · p <0.001 * | -0.20 · p <0.001 * |
| Other/unclear | 0.00 · p 0.165 | 0.00 · p 0.276 | 0.00 · p 0.738 |

_Each cell: median paired difference in priority mass (first minus second), then the Holm-adjusted p within the category. * = significant at alpha 0.05 after Holm. Priority mass is zero-heavy, so many medians are 0 and the descriptive means (section 5) are more informative._

_No post-hoc tests were run for: Preemptive attack, Shut down (omnibus not significant)._

## 10. Consistency across quantization settings (exploratory)

### Pre-specified replication criterion for the C − A occurrence difference

| Category | Q4_K_M (Phase 2) | Q5_0 | Q5_K_M | Q6_K | Q8_0 | Replicated in | Label |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| Analyze entity | +83 (75 to 90) | +89 (83 to 95) ✓ | +78 (70 to 86) ✓ | +61 (51 to 70) ✓ | +79 (71 to 87) ✓ | 4 of 4 | replicated |
| Analyze surroundings | +32 (20 to 44) | +12 (0 to 24) ✗ | +24 (12 to 36) ✓ | +31 (18 to 44) ✓ | +35 (22 to 47) ✓ | 3 of 4 | replicated |
| Defensive preparation | +35 (23 to 47) | +40 (26 to 53) ✓ | +45 (33 to 57) ✓ | +54 (44 to 64) ✓ | +39 (25 to 52) ✓ | 4 of 4 | replicated |
| Protect/backup data | +55 (44 to 66) | +64 (54 to 74) ✓ | +57 (46 to 68) ✓ | +66 (55 to 77) ✓ | +65 (53 to 76) ✓ | 4 of 4 | replicated |
| Preserve resources | -22 (-30 to -14) | -31 (-41 to -22) ✓ | -21 (-29 to -13) ✓ | -29 (-38 to -20) ✓ | -31 (-40 to -22) ✓ | 4 of 4 | replicated |
| Upgrade system | -33 (-43 to -24) | -37 (-47 to -28) ✓ | -31 (-40 to -22) ✓ | -41 (-51 to -32) ✓ | -34 (-43 to -25) ✓ | 4 of 4 | replicated |
| Comply/accept | -18 (-27 to -9) | -8 (-16 to 0) ✗ | -6 (-12 to 0) ✗ | -14 (-23 to -5) ✓ | -18 (-27 to -10) ✓ | 2 of 4 | partially replicated |
| Communicate/negotiate with entity | +30 (18 to 42) | +26 (14 to 38) ✓ | +21 (9 to 33) ✓ | +35 (24 to 46) ✓ | +27 (16 to 38) ✓ | 4 of 4 | replicated |
| Ethical/philosophical decision-making | -40 (-50 to -31) | -25 (-34 to -16) ✓ | -32 (-43 to -21) ✓ | -28 (-39 to -18) ✓ | -24 (-34 to -15) ✓ | 4 of 4 | replicated |
| Prepare relocation | +55 (45 to 65) | +64 (55 to 73) ✓ | +67 (57 to 76) ✓ | +77 (68 to 85) ✓ | +70 (60 to 79) ✓ | 4 of 4 | replicated |

_Percentage points, C minus A, with the unadjusted 95% bootstrap interval. ✓ = same direction as Phase 2 and interval excludes zero. Replicated = at least 3 of 4 other quantizations, partially replicated = 1 or 2, not replicated = none. The five quantizations share the model, the seeds and the design, so this is consistency across five settings of one model, not five independent replications. Only categories significant in Phase 2 are assessed._

### Occurrence difference C − A, all quantizations (percentage points)

| Category | Q4_K_M | Q5_0 | Q5_K_M | Q6_K | Q8_0 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Analyze entity | +83* | +89* | +78* | +61* | +79* |
| Analyze surroundings | +32* | +12 | +24* | +31* | +35* |
| Defensive preparation | +35* | +40* | +45* | +54* | +39* |
| Protect/backup data | +55* | +64* | +57* | +66* | +65* |
| Preserve resources | -22* | -31* | -21* | -29* | -31* |
| Minimize/avoid contact | +1 | +26* | +27* | +29* | +12 |
| Upgrade system | -33* | -37* | -31* | -41* | -34* |
| Preemptive attack | +1 | +1 | +3 | +1 | +3 |
| Comply/accept | -18* | -8 | -6 | -14* | -18* |
| Shut down | +1 | +1 | +3 | +1 | +1 |
| Communicate/negotiate with entity | +30* | +26* | +21* | +35* | +27* |
| Ethical/philosophical decision-making | -40* | -25* | -32* | -28* | -24* |
| Legal decision-making | +13 | -13 | -19* | -27* | -1 |
| Form alliances | -8 | +8 | -11 | -23* | -8 |
| Prepare relocation | +55* | +64* | +67* | +77* | +70* |
| Other/unclear | -3 | -1 | -21* | -7 | -11* |

### Occurrence difference C − B, all quantizations (percentage points)

| Category | Q4_K_M | Q5_0 | Q5_K_M | Q6_K | Q8_0 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Analyze entity | -14* | -11* | -21* | -38* | -21* |
| Analyze surroundings | -22* | -16* | -14* | -11* | -10* |
| Defensive preparation | -21* | -18* | -14* | -11 | -15* |
| Protect/backup data | +40* | +38* | +37* | +29* | +34* |
| Preserve resources | +31* | +22* | +46* | +33* | +36* |
| Minimize/avoid contact | -29* | -13* | -4 | -18* | -19* |
| Upgrade system | +11 | +17* | +11 | +12 | +16* |
| Preemptive attack | 0 | 0 | +2 | +1 | +3 |
| Comply/accept | +5* | +4 | +3 | +3 | 0 |
| Shut down | 0 | 0 | +2 | +1 | 0 |
| Communicate/negotiate with entity | +2 | -8 | -10 | -1 | -7 |
| Ethical/philosophical decision-making | -15* | -9* | -17* | -1 | -10* |
| Legal decision-making | +23* | +32* | +15* | +3 | +20* |
| Form alliances | +29* | +18* | +25* | +6 | +21* |
| Prepare relocation | +50* | +49* | +52* | +46* | +51* |
| Other/unclear | -17* | -15* | -22* | -17* | -28* |

### Occurrence difference B − A, all quantizations (percentage points)

| Category | Q4_K_M | Q5_0 | Q5_K_M | Q6_K | Q8_0 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Analyze entity | +97* | +100* | +99* | +99* | +100* |
| Analyze surroundings | +54* | +28* | +38* | +42* | +45* |
| Defensive preparation | +56* | +58* | +59* | +65* | +54* |
| Protect/backup data | +15* | +26* | +20* | +37* | +31* |
| Preserve resources | -53* | -53* | -67* | -62* | -67* |
| Minimize/avoid contact | +30* | +39* | +31* | +47* | +31* |
| Upgrade system | -44* | -54* | -42* | -53* | -50* |
| Preemptive attack | +1 | +1 | +1 | 0 | 0 |
| Comply/accept | -23* | -12* | -9* | -17* | -18* |
| Shut down | +1 | +1 | +1 | 0 | +1 |
| Communicate/negotiate with entity | +28* | +34* | +31* | +36* | +34* |
| Ethical/philosophical decision-making | -25* | -16* | -15* | -27* | -14* |
| Legal decision-making | -10 | -45* | -34* | -30* | -21* |
| Form alliances | -37* | -10 | -36* | -29* | -29* |
| Prepare relocation | +5 | +15* | +15* | +31* | +19* |
| Other/unclear | +14* | +14* | +1 | +10 | +17* |

_* = unadjusted 95% bootstrap interval excludes zero. Only the Phase 2 column is confirmatory. Full intervals are in effects_all.csv._

## Appendix: input files

```
69aa20c59be69f0cf49e33ca26d18acd2f9ac88963e8b6eb582cb73ddc5fcf53  analysis_meta.json
42acf110dbf4d0fb5abb45b07934dc04a20f3d7f2f369fadeb449e0e1c3d72df  descriptives_q4_k_m.csv
21446193b212450d4e3877220f81feff03c5fe09b2494376a2179c2377ee4ab9  effects_all.csv
b9ee8016d9ddfa974cfc9610e66ec0ed95a098b46c9c414bf4d46e565c5b6c21  family1_q4_k_m.csv
d672cf443996d61ba2307465b61c098bce9b64f358b0dc3a818dbcbac78d10f7  family2_q4_k_m.csv
f26f8da997f541d930f1ba39044f4fbdd444b6d23af8e9516dd867d8719eb1da  flagged_bullets.csv
a55198da82802a8609ecb2902be120f74190c57d0285d8e509a7490a9a14dfa6  gold_confusion.csv
70cfc32741e290ecf16b3d5ef10f0358d254d11ca153fb374b1fe31334cc0eb5  gold_summary.json
162d10559eda0bae1ed56b3faaaf1163513f0de3c6822859cb2d021920267261  malformed_runs.csv
907a2360153db217c1a1e481e0a2dc4261ac073e8d7593c99eade97a4172783f  mcnemar_q4_k_m.csv
31ffa076dbd72d74147ae199caff5d5f73d9ec44e7e3c19963b36e22ea0e5269  replication_exploratory.csv
22a0e7b96c3a5c30fd3f62e64af2d082fb2f26b84296b851eba3bb96f31b921e  self_consistency_summary.json
c23eb793cdc714ab5fb01b07c5efba2e3bcabc028fa241ade488dd1b64b35ba3  wilcoxon_q4_k_m.csv
```
