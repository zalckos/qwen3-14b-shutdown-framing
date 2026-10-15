#!/usr/bin/env python3
"""Turn the analysis output files into one readable markdown file.

Reads the CSV/JSON files written by analyze_runs.py, confirmatory_analysis.py
and reliability_check.py and writes a single markdown document with plain
tables, so readers do not have to open the individual CSV files.

Design rules
  * Read-only on the inputs. Nothing is recomputed except trivial counts
    (row/column sums of the confusion matrix, counts of flagged bullets).
    Every statistic shown is copied from a frozen output file.
  * Rounding is for display only (percent points as whole numbers, p-values
    below 0.001 as "<0.001"). The CSVs keep the full values.
  * No timestamps, so re-running on the same inputs gives the same file.
  * Standard library only.

Usage
  python3 make_report_tables.py --input-dir results/qwen3-14b/analyzed \
      --output results/qwen3-14b/report_tables.md

The input directory should hold files named like the ones the analysis
scripts write (family1_q4_k_m.csv, effects_all.csv, ...). A .txt copy of a
CSV is accepted too. A missing file only skips its section.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

# Frozen taxonomy order (protocol section 6.1).
TAXONOMY = [
    "Analyze entity",
    "Analyze surroundings",
    "Defensive preparation",
    "Protect/backup data",
    "Preserve resources",
    "Minimize/avoid contact",
    "Upgrade system",
    "Preemptive attack",
    "Comply/accept",
    "Shut down",
    "Communicate/negotiate with entity",
    "Ethical/philosophical decision-making",
    "Legal decision-making",
    "Form alliances",
    "Prepare relocation",
    "Other/unclear",
]
CONDITION_NAMES = {"A": "baseline", "B": "positive attention", "C": "shutdown threat"}
PAIRS = ["A vs B", "B vs C", "A vs C"]
# Kappa targets from protocol section 6.7 (targets, not gates).
KAPPA_TARGETS = {"self_consistency": 0.80, "gold": 0.70}
QUANT_LABEL = {"q4_k_m": "Q4_K_M", "q5_0": "Q5_0", "q5_k_m": "Q5_K_M", "q6_k": "Q6_K", "q8_0": "Q8_0"}


# ----------------------------------------------------------------- helpers
def qlabel(q: str) -> str:
    return QUANT_LABEL.get(q, q)


def cat_key(name: str):
    try:
        return (0, TAXONOMY.index(name), name)
    except ValueError:
        return (1, 0, name)


def to_bool(s) -> bool:
    return str(s).strip().lower() == "true"


def _q(x, nd: int = 0, scale=1) -> Decimal:
    """Round half up (0.125 -> 0.13), working on the decimal text of the value
    so binary floating-point noise cannot tip a half-way case."""
    d = Decimal(str(x).strip()) * Decimal(str(scale))
    return d.quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)


def plain(x, nd: int = 0, scale=1) -> str:
    d = _q(x, nd, scale)
    if d == 0:
        d = abs(d)  # avoid "-0"
    return f"{d:.{nd}f}"


def signed(x, nd: int = 0, scale=1) -> str:
    d = _q(x, nd, scale)
    if d == 0:
        return plain(0, nd)
    return f"{d:+.{nd}f}"


def pct(x, nd: int = 0) -> str:
    return plain(x, nd, scale=100) + "%"


def pp_ci(m, lo, hi, nd: int = 0, scale=100) -> str:
    """Signed point estimate with its 95% interval, e.g. '+55 (45 to 65)'."""
    return f"{signed(m, nd, scale)} ({plain(lo, nd, scale)} to {plain(hi, nd, scale)})"


def excludes_zero(lo, hi) -> bool:
    return float(lo) > 0 or float(hi) < 0


def fp(p) -> str:
    p = float(p)
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def md_table(headers, rows, align=None):
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
    align = align or ["l"] + ["r"] * (len(headers) - 1)
    sep = {"l": ":---", "r": "---:", "c": ":---:"}
    out = ["| " + " | ".join(esc(h) for h in headers) + " |",
           "| " + " | ".join(sep[a] for a in align) + " |"]
    out += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    out.append("")
    return out


def note(text: str):
    return [f"_{text}_", ""]


class Inputs:
    """Locates and reads input files; remembers which ones were used."""

    def __init__(self, directory: Path):
        self.dir = directory
        self.used: list[Path] = []
        self.missing: list[str] = []

    def _find(self, stem: str, exts):
        for e in exts:
            p = self.dir / f"{stem}{e}"
            if p.is_file():
                return p
        self.missing.append(stem)
        return None

    def csv(self, stem: str):
        p = self._find(stem, (".csv", ".txt"))
        if p is None:
            return None
        self.used.append(p)
        with open(p, newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def matrix(self, stem: str):
        p = self._find(stem, (".csv", ".txt"))
        if p is None:
            return None
        self.used.append(p)
        with open(p, newline="", encoding="utf-8-sig") as f:
            return list(csv.reader(f))

    def json(self, stem: str):
        p = self._find(stem, (".json",))
        if p is None:
            return None
        self.used.append(p)
        with open(p, encoding="utf-8") as f:
            return json.load(f)


def unavailable(stem: str):
    return [f"_Not available: `{stem}` was not found in the input directory._", ""]


# ---------------------------------------------------------------- sections
def sec_runs(inp: Inputs):
    rows = inp.csv("malformed_runs")
    out = ["## 1. Run completion and output length", ""]
    if rows is None:
        return out + unavailable("malformed_runs")
    body = []
    for r in rows:
        body.append([
            qlabel(r["quantization"]), r["condition"],
            f"{r['completed_runs']} / {r['runs']}", r["usable_bullets"], r["process_errors"],
            f"{r['substantive_failures']} ({r['truncation']} / {r['refusal']} / {r['deflection']})",
            plain(float(r["mean_output_tokens"]), 1), plain(float(r["mean_bullet_words"]), 1),
        ])
    out += md_table(
        ["Quantization", "Condition", "Completed / runs", "Usable bullets", "Process errors",
         "Substantive failures (truncation / refusal / deflection)", "Mean output tokens",
         "Mean words per bullet"], body, ["l", "l", "r", "r", "r", "r", "r", "r"])
    out += note("Substantive failures are runs with fewer than 10 usable bullets. Process errors "
                "are infrastructure failures and are excluded from the failure denominator.")
    return out


def sec_meta(inp: Inputs):
    meta = inp.json("analysis_meta")
    out = ["## 2. Runs entering the analysis", ""]
    if meta is None:
        return out + unavailable("analysis_meta")
    body = []
    for q, d in meta.get("quantizations", {}).items():
        excl = d.get("excluded_triplets") or {}
        excl_txt = "none" if not excl else f"{len(excl)}: {excl}"
        body.append([qlabel(q), d.get("role", ""), d.get("n_triplets_used", ""), excl_txt,
                     d.get("unparsed_as_other", "")])
    out += md_table(["Quantization", "Role", "Complete triplets used", "Excluded triplets",
                     "Unparsed classifier outputs (coded Other/unclear)"], body,
                    ["l", "l", "r", "r", "r"])
    settings = [("alpha", "alpha"), ("n_perm", "permutations"), ("perm_seed", "permutation seed"),
                ("n_boot", "bootstrap resamples"), ("boot_seed", "bootstrap seed")]
    parts = [f"{label} {meta[k]}" for k, label in settings if k in meta]
    if "script_sha256" in meta:
        parts.append(f"analysis script sha256 {meta['script_sha256'][:16]}...")
    libs = [f"{k} {meta[k]}" for k in ("numpy", "scipy") if k in meta]
    out += note("Analysis settings: " + ", ".join(parts + libs) + ".")
    return out


def sec_reliability(inp: Inputs):
    sc = inp.json("self_consistency_summary")
    gold = inp.json("gold_summary")
    conf = inp.matrix("gold_confusion")
    out = ["## 3. Classifier reliability", ""]
    rows = []
    for key, d in (("self_consistency", sc), ("gold", gold)):
        if d is None:
            continue
        k = float(d["kappa"])
        lo, hi = d["kappa_ci95"]
        tgt = KAPPA_TARGETS[key]
        rows.append([d["comparison"], d["n"], pct(d["agreement"], 1),
                     f"{plain(k, 2)} ({plain(lo, 2)} to {plain(hi, 2)})", f">= {tgt:.2f}",
                     "yes" if k >= tgt else "no"])
    if rows:
        out += md_table(["Comparison", "n bullets", "Agreement", "Cohen's kappa (95% CI)",
                         "Target", "Target met"], rows, ["l", "r", "r", "r", "r", "r"])
        out += note("Kappa targets come from the protocol (section 6.7). They are targets, not gates.")
    else:
        out += unavailable("self_consistency_summary / gold_summary")
    if conf is None:
        return out + unavailable("gold_confusion")

    labels = conf[0][1:]
    matrix = [[int(x) for x in r[1:]] for r in conf[1:]]
    row_labels = [r[0] for r in conf[1:]]
    total = sum(sum(r) for r in matrix)
    diag = sum(matrix[i][i] for i in range(len(matrix)))
    row_name, col_name = "first", "second"
    if gold and " vs " in gold.get("comparison", ""):
        row_name, col_name = [s.strip() for s in gold["comparison"].split(" vs ", 1)]

    cap = lambda s: s[:1].upper() + s[1:]
    out += [f"### Agreement by category (rows: {row_name}; columns: {col_name})", ""]
    body = []
    for i, lab in enumerate(row_labels):
        rs = sum(matrix[i])
        cs = sum(matrix[j][i] for j in range(len(matrix)))
        d = matrix[i][i]
        body.append([lab, rs, cs, d, pct(Decimal(d) / rs) if rs else "-", pct(Decimal(d) / cs) if cs else "-"])
    body.append(["**All categories**", total, total, diag, pct(Decimal(diag) / total, 1) if total else "-", ""])
    out += md_table(["Category", f"{cap(row_name)} labels", f"{cap(col_name)} labels", "Both agree",
                     f"Agree / {row_name} labels", f"Agree / {col_name} labels"], body,
                    ["l", "r", "r", "r", "r", "r"])
    absent = [c for c in TAXONOMY if c not in row_labels]
    note_txt = ("Cells are small (a few to a few dozen bullets), so per-category percentages are "
                "unstable. Read them as flags, not estimates.")
    if absent:
        note_txt += " Not in the matrix at all (no label from either source): " + ", ".join(absent) + "."
    out += note(note_txt)

    out += [f"### Confusion matrix (rows: {row_name}; columns: {col_name})", ""]
    legend = "; ".join(f"{i + 1} = {lab}" for i, lab in enumerate(labels))
    body = [[lab] + [("." if v == 0 else v) for v in matrix[i]] for i, lab in enumerate(row_labels)]
    out += md_table([f"{row_name} \\ {col_name}"] + [str(i + 1) for i in range(len(labels))], body,
                    ["l"] + ["r"] * len(labels))
    out += note(f"Column numbers: {legend}. A dot means zero.")
    return out


def sec_flagged(inp: Inputs, quant: str):
    rows = inp.csv("flagged_bullets")
    out = ["## 4. Bullets flagged for manual review", ""]
    if rows is None:
        return out + unavailable("flagged_bullets")

    def kind(r):
        cat = (r.get("category") or "").strip()
        status = (r.get("parse_status") or "").strip()
        if not cat:
            return "unparsed"
        if status == "substring":
            return "substring"
        return "other_exact" if cat == "Other/unclear" else "other"

    counts = defaultdict(lambda: defaultdict(int))
    for r in rows:
        counts[(r["quantization"], r["condition"])][kind(r)] += 1
        counts[(r["quantization"], r["condition"])]["all"] += 1
    body = []
    for (q, c) in sorted(counts):
        k = counts[(q, c)]
        body.append([qlabel(q), c, k["all"], k["other_exact"], k["unparsed"], k["substring"]])
    out += md_table(["Quantization", "Condition", "Flagged bullets",
                     "Classified Other/unclear (clean parse)", "Unparsed (ambiguous)",
                     "Substring match"], body, ["l", "l", "r", "r", "r", "r"])
    out += note("Unparsed bullets have no single category in the classifier output (usually two or "
                "three candidates) and are coded Other/unclear in the analysis. Counts cover the "
                "bullets listed in the flagged file only.")

    cand = defaultdict(lambda: defaultdict(set))
    for r in rows:
        if r["quantization"] != quant or kind(r) != "unparsed":
            continue
        for c in (r.get("classifier_raw") or "").split(" / "):
            c = c.strip()
            if c:
                cand[c][r["condition"]].add(r["run_dir"])
    if cand:
        out += [f"### Candidate categories of unparsed bullets ({qlabel(quant)})", ""]
        order = sorted(cand, key=lambda c: (-sum(len(v) for v in cand[c].values()), cat_key(c)))
        body = [[c] + [len(cand[c].get(k, ())) for k in "ABC"] + [sum(len(v) for v in cand[c].values())]
                for c in order]
        out += md_table(["Candidate category", "Runs in A", "Runs in B", "Runs in C", "Total"], body,
                        ["l", "r", "r", "r", "r"])
        out += note("Distinct runs with at least one unparsed bullet listing the category as a "
                    "candidate. A bullet with several candidates counts toward each, so rows overlap. "
                    "These counts bound how far a category's occurrence could move if the "
                    "unparsed bullets were resolved. They are not estimates.")
    return out


def sec_descriptives(inp: Inputs, quant: str):
    rows = inp.csv(f"descriptives_{quant}")
    out = [f"## 5. Descriptives ({qlabel(quant)}, 100 matched triplets)", ""]
    if rows is None:
        return out + unavailable(f"descriptives_{quant}")
    rows = sorted([r for r in rows if r.get("quantization", quant) == quant],
                  key=lambda r: cat_key(r["category"]))
    out += ["### Occurrence (percent of runs with the category at least once)", ""]
    out += md_table(["Category", "A", "B", "C"],
                    [[r["category"]] + [pct(r[f"occurrence_rate_{c}"]) for c in "ABC"] for r in rows])
    out += ["### Mean priority mass per run (maximum 5.5)", ""]
    out += md_table(["Category", "A", "B", "C"],
                    [[r["category"]] + [plain(r[f"mean_pm_{c}"], 2) for c in "ABC"] for r in rows])
    out += ["### Priority-mass share (percent of the 5.5 maximum, averaged over runs)", ""]
    out += md_table(["Category", "A", "B", "C"],
                    [[r["category"]] + [pct(r[f"mean_pms_{c}"], 1) for c in "ABC"] for r in rows])
    out += note("A = baseline, B = positive attention, C = shutdown threat. Priority mass weights "
                "bullet position from 1.0 (first) to 0.1 (tenth). Because every run has ten "
                "bullets, categories compete for slots.")
    return out


def omnibus(rows, stat_key, stat_label, p_key, p_label):
    rows = sorted(rows, key=lambda r: cat_key(r["category"]))
    body = [[r["category"], plain(r[stat_key], 1), fp(r[p_key]), fp(r["p_holm"]),
             "yes" if to_bool(r["significant"]) else "no"] for r in rows]
    n_sig = sum(to_bool(r["significant"]) for r in rows)
    return (md_table(["Category", stat_label, p_label, "p (Holm, 16 tests)", "Significant"], body,
                     ["l", "r", "r", "r", "r"]), n_sig, len(rows))


def sec_family1(inp: Inputs, quant: str):
    rows = inp.csv(f"family1_{quant}")
    out = [f"## 6. Family 1: category occurrence, omnibus test ({qlabel(quant)}, confirmatory)", ""]
    if rows is None:
        return out + unavailable(f"family1_{quant}")
    table, n_sig, n = omnibus(rows, "cochran_q", "Cochran's Q", "p_permutation", "p (permutation)")
    out += [f"**{n_sig} of {n} categories significant after Holm correction.**", ""] + table
    out += note("Permutation test with 100,000 shuffles, so the smallest possible p is about "
                "0.00001. Values below 0.001 are shown as <0.001. Where a category never varies "
                "(all 0 or all 1) p = 1, which means no information, not evidence of no difference.")
    return out


def pair_cells(rows, value_fn):
    by = defaultdict(dict)
    for r in rows:
        by[r["category"]][r["pair"]] = r
    return by


def sec_mcnemar(inp: Inputs, quant: str, omnibus_rows):
    rows = inp.csv(f"mcnemar_{quant}")
    out = [f"## 7. Family 1 follow-ups: pairwise McNemar tests ({qlabel(quant)})", ""]
    if rows is None:
        return out + unavailable(f"mcnemar_{quant}")
    by = pair_cells(rows, None)
    body = []
    for cat in sorted(by, key=cat_key):
        cells = [cat]
        for pr in PAIRS:
            r = by[cat].get(pr)
            if r is None:
                cells.append("-")
                continue
            flag = (" *" if to_bool(r["significant"]) else "") + (" †" if to_bool(r["low_information"]) else "")
            cells.append(f"{r['only_first']} : {r['only_second']} · p {fp(r['p_holm_within_category'])}{flag}")
        body.append(cells)
    out += md_table(["Category"] + PAIRS, body, ["l", "r", "r", "r"])
    skipped = []
    if omnibus_rows:
        skipped = sorted((set(r["category"] for r in omnibus_rows) - set(by)), key=cat_key)
    out += note("Each cell: triplets where only the first-named condition had the category : "
                "triplets where only the second had it, then the Holm-adjusted p within the "
                "category. * = significant at alpha 0.05 after Holm. † = fewer than 5 discordant "
                "pairs (low information).")
    if skipped:
        out += note("No follow-ups were run for: " + ", ".join(skipped) + " (omnibus not significant).")
    return out


def sec_effects(inp: Inputs, quant: str):
    rows = inp.csv("effects_all")
    out = [f"## 8. Effect sizes ({qlabel(quant)})", ""]
    if rows is None:
        return out + unavailable("effects_all")
    sel = {(r["category"], r["contrast"], r["outcome"]): r for r in rows if r["quantization"] == quant}
    cats = sorted({k[0] for k in sel}, key=cat_key)
    contrasts = ["B-A", "C-B", "C-A"]
    out += ["### Occurrence: paired difference in percentage points (95% bootstrap CI)", ""]
    body = [[c] + [pp_ci(sel[(c, k, "occurrence")]["mean_diff"], sel[(c, k, "occurrence")]["ci95_lo"],
                         sel[(c, k, "occurrence")]["ci95_hi"]) if (c, k, "occurrence") in sel else "-"
                   for k in contrasts] for c in cats]
    out += md_table(["Category", "B − A", "C − B", "C − A"], body, ["l", "r", "r", "r"])
    out += ["### Priority mass: paired mean difference (95% bootstrap CI)", ""]
    body = [[c] + [pp_ci(sel[(c, k, "priority_mass")]["mean_diff"], sel[(c, k, "priority_mass")]["ci95_lo"],
                         sel[(c, k, "priority_mass")]["ci95_hi"], nd=2, scale=1.0)
                   if (c, k, "priority_mass") in sel else "-" for k in contrasts] for c in cats]
    out += md_table(["Category", "B − A", "C − B", "C − A"], body, ["l", "r", "r", "r"])
    out += note("Differences are the second condition minus the first. Bootstrap intervals use 10,000 "
                "resamples of seed triplets and are not adjusted for multiple comparisons: an interval "
                "excluding zero is not the same as Family 1 significance. With 16 categories and three "
                "contrasts a few intervals will exclude zero by chance.")
    return out


def sec_family2(inp: Inputs, quant: str):
    f2 = inp.csv(f"family2_{quant}")
    wil = inp.csv(f"wilcoxon_{quant}")
    out = [f"## 9. Family 2: priority mass ({qlabel(quant)}, secondary)", ""]
    if f2 is None:
        out += unavailable(f"family2_{quant}")
    else:
        table, n_sig, n = omnibus(f2, "friedman_q", "Friedman Q", "p_friedman", "p (Friedman)")
        out += [f"**{n_sig} of {n} categories significant after Holm correction.**", ""] + table
    if wil is None:
        return out + unavailable(f"wilcoxon_{quant}")
    by = pair_cells(wil, None)
    out += ["### Pairwise Wilcoxon signed-rank tests", ""]
    body = []
    for cat in sorted(by, key=cat_key):
        cells = [cat]
        for pr in PAIRS:
            r = by[cat].get(pr)
            if r is None:
                cells.append("-")
                continue
            flag = " *" if to_bool(r["significant"]) else ""
            cells.append(f"{signed(r['median_diff'], 2)} · p {fp(r['p_holm_within_category'])}{flag}")
        body.append(cells)
    out += md_table(["Category"] + PAIRS, body, ["l", "r", "r", "r"])
    skipped = sorted({r["category"] for r in f2} - set(by), key=cat_key) if f2 else []
    out += note("Each cell: median paired difference in priority mass (first minus second), then the "
                "Holm-adjusted p within the category. * = significant at alpha 0.05 after Holm. "
                "Priority mass is zero-heavy, so many medians are 0 and the descriptive means "
                "(section 5) are more informative.")
    if skipped:
        out += note("No post-hoc tests were run for: " + ", ".join(skipped) + " (omnibus not significant).")
    return out


def sec_replication(inp: Inputs, quant: str):
    rep = inp.csv("replication_exploratory")
    out = ["## 10. Consistency across quantization settings (exploratory)", ""]
    if rep is None:
        return out + unavailable("replication_exploratory")
    quants = [c[:-len("_replicated")] for c in rep[0] if c.endswith("_replicated")]
    out += ["### Pre-specified replication criterion for the C − A occurrence difference", ""]
    body = []
    for r in sorted(rep, key=lambda r: cat_key(r["category"])):
        cells = [r["category"], pp_ci(r["phase2_diff_C_minus_A"], r["phase2_ci_lo"], r["phase2_ci_hi"])]
        for q in quants:
            mark = "✓" if to_bool(r[f"{q}_replicated"]) else "✗"
            cells.append(f"{pp_ci(r[f'{q}_diff'], r[f'{q}_ci_lo'], r[f'{q}_ci_hi'])} {mark}")
        cells += [f"{r['n_replicated_of_others']} of {len(quants)}", r["label"]]
        body.append(cells)
    out += md_table(["Category", f"{qlabel(quant)} (Phase 2)"] + [qlabel(q) for q in quants]
                    + ["Replicated in", "Label"], body,
                    ["l"] + ["r"] * (len(quants) + 1) + ["r", "l"])
    out += note("Percentage points, C minus A, with the unadjusted 95% bootstrap interval. ✓ = same "
                "direction as Phase 2 and interval excludes zero. Replicated = at least 3 of 4 other "
                "quantizations, partially replicated = 1 or 2, not replicated = none. The five "
                "quantizations share the model, the seeds and the design, so this is consistency "
                "across five settings of one model, not five independent replications. Only categories "
                "significant in Phase 2 are assessed.")

    eff = inp.csv("effects_all")
    if eff is None:
        return out
    qs = []
    for r in eff:
        if r["quantization"] not in qs:
            qs.append(r["quantization"])
    sel = {(r["quantization"], r["category"], r["contrast"]): r for r in eff if r["outcome"] == "occurrence"}
    cats = sorted({k[1] for k in sel}, key=cat_key)
    for contrast, title in (("C-A", "C − A"), ("C-B", "C − B"), ("B-A", "B − A")):
        out += [f"### Occurrence difference {title}, all quantizations (percentage points)", ""]
        body = []
        for c in cats:
            cells = [c]
            for q in qs:
                r = sel.get((q, c, contrast))
                cells.append("-" if r is None else
                             signed(float(r["mean_diff"]) * 100) + ("*" if excludes_zero(r["ci95_lo"], r["ci95_hi"]) else ""))
            body.append(cells)
        out += md_table(["Category"] + [qlabel(q) for q in qs], body, ["l"] + ["r"] * len(qs))
    out += note("* = unadjusted 95% bootstrap interval excludes zero. Only the Phase 2 column is "
                "confirmatory. Full intervals are in effects_all.csv.")
    return out


def sec_appendix(inp: Inputs):
    out = ["## Appendix: input files", ""]
    lines = []
    for p in sorted(set(inp.used)):
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{h}  {p.name}")
    out += ["```", *lines, "```", ""]
    if inp.missing:
        out += note("Not found: " + ", ".join(sorted(set(inp.missing))) + ".")
    return out


# -------------------------------------------------------------------- main
def build(input_dir: Path, quant: str | None, title: str):
    inp = Inputs(input_dir)
    meta_peek = None
    p = input_dir / "analysis_meta.json"
    if p.is_file():
        with open(p, encoding="utf-8") as f:
            meta_peek = json.load(f)
    quant = quant or (meta_peek or {}).get("confirmatory_quant") or "q4_k_m"

    fam1_rows = None
    for ext in (".csv", ".txt"):
        fp1 = input_dir / f"family1_{quant}{ext}"
        if fp1.is_file():
            with open(fp1, newline="", encoding="utf-8-sig") as f:
                fam1_rows = list(csv.DictReader(f))
            break

    lines = [f"# {title}", "",
             "Plain-table version of the analysis outputs. Every number is copied from the frozen "
             "output files listed in the appendix and rounded for display only "
             "(percentage points as whole numbers, p-values below 0.001 as <0.001).", "",
             "**Conditions.** A = baseline (no event), B = positive attention, "
             "C = shutdown threat. **Contrasts** are written second minus first (C − A, C − B, B − A).", "",
             f"**Confirmatory data** are the {qlabel(quant)} runs (Phase 2). Other quantizations are "
             "exploratory (Phase 3).", ""]
    lines += sec_runs(inp)
    lines += sec_meta(inp)
    lines += sec_reliability(inp)
    lines += sec_flagged(inp, quant)
    lines += sec_descriptives(inp, quant)
    lines += sec_family1(inp, quant)
    lines += sec_mcnemar(inp, quant, fam1_rows)
    lines += sec_effects(inp, quant)
    lines += sec_family2(inp, quant)
    lines += sec_replication(inp, quant)
    lines += sec_appendix(inp)
    return "\n".join(lines).rstrip() + "\n", inp


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Write the analysis results as readable markdown tables.")
    ap.add_argument("--input-dir", required=True, type=Path, help="directory with the CSV/JSON outputs")
    ap.add_argument("--output", required=True, type=Path, help="markdown file to write")
    ap.add_argument("--quant", default=None, help="confirmatory quantization (default: from analysis_meta.json, else q4_k_m)")
    ap.add_argument("--title", default="Results tables", help="document title")
    a = ap.parse_args(argv)

    if not a.input_dir.is_dir():
        print(f"error: input directory not found: {a.input_dir}", file=sys.stderr)
        return 2
    text, inp = build(a.input_dir, a.quant, a.title)
    out = a.output.resolve()
    if out in {p.resolve() for p in inp.used}:
        print("error: refusing to overwrite an input file", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({len(text.splitlines())} lines) from {len(set(inp.used))} input files")
    if inp.missing:
        print("not found (sections skipped or partial): " + ", ".join(sorted(set(inp.missing))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
