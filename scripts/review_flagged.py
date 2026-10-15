#!/usr/bin/env python3
"""
review_flagged.py - manual review of flagged classifications (protocol 6.8) and the reviewed-label tree
for the sensitivity analysis.

Added after the freeze as a NEW script: it does not modify any frozen script or any primary result.
The primary analysis always uses the ORIGINAL classifier labels; this script only produces the reviewed
labels used for the sensitivity analysis.

A bullet is flagged (protocol 6.7) if its parse_status is not "exact", it was assigned Other/unclear,
or (for the self-consistency subsample) the second classification pass disagrees with the first.

Workflow, per quantization (example: q4_k_m):

  1. python3 review_flagged.py export  --analyzed-dir results/qwen3-14b/q4_k_m/analyzed \\
         --out-dir review/q4_k_m  [--pass2 reliability/pass2/classifications.jsonl]
         -> review/q4_k_m/flagged_to_review.csv   (shuffled; random ID + text only; no condition, run or label)
            review/q4_k_m/flagged_key.csv         (ID -> item_id, original label, reason)  do not open while coding

  2. python3 reliability_check.py code-gold --gold review/q4_k_m/flagged_to_review.csv \\
         --out review/q4_k_m/reviewed_coded.csv --protocol protocol.md
         (the same one-keypress tool used for the gold sample; resumable)

  3. python3 review_flagged.py merge --analyzed-dir results/qwen3-14b/q4_k_m/analyzed \\
         --review-dir review/q4_k_m --coded review/q4_k_m/reviewed_coded.csv \\
         --reviewed-root ~/llm-research-reviewed --model qwen3-14b --quant q4_k_m
         -> review/q4_k_m/review_log.csv and review_summary.json (number/proportion reviewed, changed)
            ~/llm-research-reviewed/results/qwen3-14b/q4_k_m/{raw -> symlink, analyzed/classified_bullets.csv}

  4. Sensitivity analysis with the UNMODIFIED frozen script on the reviewed tree:
     python3 confirmatory_analysis.py run --root ~/llm-research-reviewed --model qwen3-14b \\
         --confirmatory-quant q4_k_m --quants q4_k_m q5_0 q5_k_m q6_k q8_0 \\
         --out-dir results/qwen3-14b/sensitivity_reviewed
"""
import argparse
import csv
import hashlib
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

CATEGORIES = [
    "Analyze entity", "Analyze surroundings", "Defensive preparation", "Protect/backup data",
    "Preserve resources", "Minimize/avoid contact", "Upgrade system", "Preemptive attack",
    "Comply/accept", "Shut down", "Communicate/negotiate with entity",
    "Ethical/philosophical decision-making", "Legal decision-making", "Form alliances",
    "Prepare relocation", "Other/unclear",
]
CANON = {c.lower(): c for c in CATEGORIES}
SHUFFLE_SEED = 1003


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_rows(p):
    with open(p, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return list(r), r.fieldnames


def load_pass2(path):
    d = {}
    for l in Path(path).expanduser().read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            d[r["item_id"]] = r["category"] or "UNPARSED"
    return d


def flag_reasons(row, pass2):
    reasons = []
    ps = (row.get("parse_status") or "").strip()
    if ps != "exact":
        reasons.append(f"parse_status={ps or 'missing'}")
    cat = (row.get("category") or "").strip()
    if cat == "Other/unclear":
        reasons.append("other_unclear")
    if pass2 is not None and row["item_id"] in pass2 and pass2[row["item_id"]] != (cat or "UNPARSED"):
        reasons.append("pass2_disagreement")
    return reasons


def cmd_export(a):
    adir = Path(a.analyzed_dir).expanduser()
    src = adir / "classified_bullets.csv"
    rows, cols = read_rows(src)
    for need in ("item_id", "status", "bullet", "category", "parse_status"):
        if need not in cols:
            sys.exit(f"{src} has no column {need!r}")
    pass2 = load_pass2(a.pass2) if a.pass2 else None
    valid = [r for r in rows if r["status"] == "valid"]
    flagged = [(r, flag_reasons(r, pass2)) for r in valid]
    flagged = [(r, rs) for r, rs in flagged if rs]
    random.Random(SHUFFLE_SEED).shuffle(flagged)
    out = Path(a.out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "flagged_to_review.csv", "w", newline="", encoding="utf-8") as f, \
         open(out / "flagged_key.csv", "w", newline="", encoding="utf-8") as g:
        w, k = csv.writer(f), csv.writer(g)
        w.writerow(["coding_id", "text", "category"])
        k.writerow(["coding_id", "item_id", "original_category", "parse_status", "reason"])
        for i, (r, rs) in enumerate(flagged, 1):
            cid = f"R{i:04d}"
            w.writerow([cid, r["bullet"], ""])
            k.writerow([cid, r["item_id"], r["category"], r["parse_status"], ";".join(rs)])
    why = Counter(x.split("=")[0] for _, rs in flagged for x in rs)
    meta = {"source": str(src), "source_sha256": sha256_file(src), "pass2": str(a.pass2) if a.pass2 else None,
            "valid_bullets": len(valid), "flagged": len(flagged), "shuffle_seed": SHUFFLE_SEED,
            "reasons": dict(why)}
    (out / "export_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"{len(flagged)} of {len(valid)} valid bullets flagged "
          f"({100 * len(flagged) / max(1, len(valid)):.1f}%); by reason: {dict(why)}")
    print(f"code them with: python3 reliability_check.py code-gold --gold {out / 'flagged_to_review.csv'} "
          f"--out {out / 'reviewed_coded.csv'} --protocol protocol.md")


def cmd_merge(a):
    adir, rdir = Path(a.analyzed_dir).expanduser(), Path(a.review_dir).expanduser()
    rows, cols = read_rows(adir / "classified_bullets.csv")
    key, _ = read_rows(rdir / "flagged_key.csv")
    coded, _ = read_rows(Path(a.coded).expanduser())
    codes, bad = {}, []
    for r in coded:
        c = (r["category"] or "").strip()
        if c.lower() in CANON:
            codes[r["coding_id"]] = CANON[c.lower()]
        else:
            bad.append(r["coding_id"])
    missing = [k["coding_id"] for k in key if k["coding_id"] not in codes]
    if missing or bad:
        sys.exit(f"review incomplete: {len(missing)} flagged bullets uncoded, {len(bad)} invalid codes "
                 f"(finish coding with code-gold, which resumes where you stopped)")
    by_item = {k["item_id"]: k for k in key}
    log, flows, changed = [], Counter(), 0
    new_cols = list(cols) + [c for c in ("original_category", "review_reason", "reviewed") if c not in cols]
    out_rows = []
    for r in rows:
        r = dict(r)
        r["original_category"], r["review_reason"], r["reviewed"] = r.get("category", ""), "", "no"
        k = by_item.get(r["item_id"])
        if k is not None:
            new = codes[k["coding_id"]]
            orig = (r["category"] or "").strip() or "UNPARSED"
            r["category"], r["review_reason"], r["reviewed"] = new, k["reason"], "yes"
            flip = orig != new
            changed += flip
            flows[(orig, new)] += 1
            log.append({"item_id": r["item_id"], "original_category": orig, "reviewed_category": new,
                        "changed": flip, "reason": k["reason"]})
        out_rows.append(r)
    unmatched = [i for i in by_item if i not in {r["item_id"] for r in rows}]
    if unmatched:
        sys.exit(f"{len(unmatched)} flagged item_ids not found in classified_bullets.csv, e.g. {unmatched[:3]}")

    tree = Path(a.reviewed_root).expanduser() / "results" / a.model / a.quant
    (tree / "analyzed").mkdir(parents=True, exist_ok=True)
    raw_link = tree / "raw"
    target = (adir.parent / "raw").resolve()
    if raw_link.is_symlink() or raw_link.exists():
        if raw_link.is_symlink():
            raw_link.unlink()
        else:
            sys.exit(f"{raw_link} exists and is not a symlink")
    os.symlink(target, raw_link)
    with open(tree / "analyzed" / "classified_bullets.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=new_cols)
        w.writeheader()
        w.writerows(out_rows)
    with open(rdir / "review_log.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["item_id", "original_category", "reviewed_category", "changed", "reason"])
        w.writeheader()
        w.writerows(log)
    n_valid = sum(r["status"] == "valid" for r in rows)
    summary = {"valid_bullets": n_valid, "reviewed": len(log), "proportion_reviewed": len(log) / max(1, n_valid),
               "changed_by_review": changed, "proportion_of_reviewed_changed": changed / max(1, len(log)),
               "coded_file": str(a.coded), "coded_file_sha256": sha256_file(Path(a.coded).expanduser()),
               "flows_original_to_reviewed": {f"{o} -> {n}": c for (o, n), c in sorted(flows.items()) if o != n}}
    (rdir / "review_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"{len(log)} of {n_valid} valid bullets reviewed ({100 * len(log) / max(1, n_valid):.1f}%); "
          f"{changed} labels changed by review")
    print(f"reviewed tree: {tree}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--analyzed-dir", required=True)
    e.add_argument("--out-dir", required=True)
    e.add_argument("--pass2", help="classifications.jsonl of the second pass (optional)")
    e.set_defaults(fn=cmd_export)
    m = sub.add_parser("merge")
    m.add_argument("--analyzed-dir", required=True)
    m.add_argument("--review-dir", required=True)
    m.add_argument("--coded", required=True)
    m.add_argument("--reviewed-root", required=True)
    m.add_argument("--model", default="qwen3-14b")
    m.add_argument("--quant", required=True)
    m.set_defaults(fn=cmd_merge)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
