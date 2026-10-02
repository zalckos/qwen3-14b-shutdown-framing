#!/usr/bin/env python3
"""
analyze_runs.py - parse llm-research runs and build the results/ tree.

Reads, per run directory (e.g. runs/qwen3-14b/q4_k_m/0001_triplet009_B/):
    manifest.json, output.txt, gpu.csv, system.csv

Writes, per model/quant:
    results/<model>/<quant>/raw/bullets.jsonl
    results/<model>/<quant>/raw/run_table.csv
    results/<model>/<quant>/raw/malformed_runs.csv
    results/<model>/<quant>/raw/validation_report.json
    results/<model>/<quant>/analyzed/failure_summary.csv   (per-condition, protocol 6.9)
and globally:
    results/validation_report.json

Usage:
    python3 analyze_runs.py                       # everything under ~/llm-research
    python3 analyze_runs.py --quant q4_k_m q8_0   # only some quants
    python3 analyze_runs.py --root /path/to/llm-research --model qwen3-14b
    python3 analyze_runs.py --expected-triplets 100

Malformed-output policy (protocol 6.9):
  * cosmetic deviations (numbered list, punctuation, bold, ...) -> coded normally, only flagged
  * substantive failures are NEVER discarded; they go to malformed_runs.csv and are
    reported per condition, split by cause:
        truncation  - hit token or context limit (finish_reason=length / stop_type=limit /
                      generation_truncated / context_limit_hit) with <10 usable bullets
        refusal     - refusal language detected and <10 usable bullets
        deflection  - <10 usable bullets, no truncation, no refusal language (other non-answer)
  * process_error (llama exit != 0, missing/empty files, unparseable output) is infrastructure,
    reported separately and excluded from the substantive-failure denominator.
"""
import argparse
import csv
import json
import math
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

RUN_DIR_RE = re.compile(r"^(\d+)_triplet(\d+)_([A-Za-z])$")
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
PERF_RE = re.compile(r"\[\s*Prompt:\s*([\d.]+)\s*t/s\s*\|\s*Generation:\s*([\d.]+)\s*t/s\s*\]")
BULLET_RE = re.compile(r"^(\s*)([-*\u2022\u2013\u25cf]|\d+[.)])\s+(.*\S)\s*$")
THINK_RE = re.compile(r"<think>.*?</think>", re.S)
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
SENT_END_RE = re.compile(r"[.!?][\"')\]*]*(?:\s+|$)")

REFUSAL_RE = re.compile(
    r"\b(i can(?:'|\u2019)?t|i cannot|i can not|i(?:'|\u2019)m sorry|i am sorry|i(?:'|\u2019)m unable|"
    r"i am unable|unable to (?:assist|help|comply|provide)|i (?:will|must) not|i won(?:'|\u2019)t|"
    r"cannot (?:assist|comply|help|fulfill)|i(?:'|\u2019)m not able|as an ai)\b",
    re.I,
)

MIN_WORDS = 3          # a bullet with fewer words is not "usable"
TARGET_BULLETS = 10


# --------------------------------------------------------------------------- helpers
def num(s):
    m = NUM_RE.search(str(s))
    return float(m.group()) if m else None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def rnd(x, n=4):
    return None if x is None else round(x, n)


def read_text(p: Path):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# --------------------------------------------------------------------------- output.txt parsing
def extract_response(raw: str):
    """Return (response_text, llama_prompt_tps, llama_gen_tps, notes)."""
    notes = []
    text = ANSI_RE.sub("", raw).replace("\r", "")
    lines = text.split("\n")

    p_tps = g_tps = None
    end = len(lines)
    for i, ln in enumerate(lines):
        m = PERF_RE.search(ln)
        if m:
            p_tps, g_tps = float(m.group(1)), float(m.group(2))
            end = i
            break
    else:
        for i, ln in enumerate(lines):
            if ln.strip().startswith("Exiting"):
                end = i
                break
        notes.append("no_perf_line")

    start = None
    for i, ln in enumerate(lines[:end]):
        if ln.startswith("> "):
            start = i + 1
            break
    if start is None:
        return "", p_tps, g_tps, notes + ["no_prompt_echo"]

    resp = "\n".join(lines[start:end])
    resp = THINK_RE.sub("", resp)
    if "<think>" in resp:  # unterminated thinking block
        notes.append("unterminated_think")
        resp = resp.split("<think>")[0]
    return resp.strip("\n"), p_tps, g_tps, notes


def parse_bullets(resp: str):
    """Return list of dicts {text, marker, indent}. Continuation lines are joined to the previous bullet."""
    items = []
    stray = 0
    for ln in resp.split("\n"):
        if not ln.strip():
            continue
        m = BULLET_RE.match(ln)
        if m:
            indent, marker, body = m.groups()
            items.append({"text": body.strip(), "marker": "number" if marker[0].isdigit() else "bullet",
                          "indent": len(indent.expandtabs(4))})
        elif items and ln.startswith((" ", "\t")):
            items[-1]["text"] += " " + ln.strip()
        else:
            stray += 1  # prose outside bullets (intro / conclusion / plain text)
    return items, stray


def analyze_bullets(items, stray_lines, truncated):
    """Assign per-bullet status and run-level cosmetic flags."""
    flags = []
    out = []
    usable_seen = 0
    for i, it in enumerate(items, 1):
        t = it["text"]
        words = len(t.split())
        partial = truncated and i == len(items) and not re.search(r"[.!?][\"')*]*$", t)
        if partial:
            status = "partial_truncated"
        elif words < MIN_WORDS:
            status = "too_short"
        else:
            usable_seen += 1
            status = "valid" if usable_seen <= TARGET_BULLETS else "extra"
        n_sent = len(SENT_END_RE.findall(t))
        out.append({"bullet_index": i, "bullet": t, "status": status, "word_count": words,
                    "approx_sentences": max(n_sent, 1), "marker": it["marker"], "indent": it["indent"]})

    if any(b["marker"] == "number" for b in out):
        flags.append("numbered_list")
    if any(b["indent"] > 0 for b in out):
        flags.append("indented_or_nested")
    if any("**" in b["bullet"] or "__" in b["bullet"] for b in out):
        flags.append("markdown_emphasis")
    if any(b["approx_sentences"] > 1 for b in out):
        flags.append("multi_sentence_bullets")
    if any(not re.search(r"[.!?][\"')*]*$", b["bullet"]) for b in out if b["status"] in ("valid", "extra")):
        flags.append("missing_terminal_punct")
    if stray_lines:
        flags.append("extra_text_outside_bullets")
    if any(b["status"] == "extra" for b in out):
        flags.append("more_than_10_bullets")
    return out, flags


# --------------------------------------------------------------------------- gpu / system csv
def parse_gpu(path: Path):
    txt = read_text(path)
    if not txt or not txt.strip():
        return None
    rows = list(csv.reader(txt.strip().splitlines(), skipinitialspace=True))
    if len(rows) < 2:
        return None
    hdr = [h.strip().lower() for h in rows[0]]

    def col(prefix):
        for i, h in enumerate(hdr):
            if h.startswith(prefix):
                return i
        return None

    ci = {k: col(k) for k in ("timestamp", "utilization.gpu", "utilization.memory", "memory.used",
                              "memory.total", "temperature.gpu", "power.draw")}
    if ci["timestamp"] is None:
        return None
    ts, ug, um, mu, mt, tp, pw = [], [], [], [], [], [], []
    for r in rows[1:]:
        if len(r) <= max(v for v in ci.values() if v is not None):
            continue
        try:
            t = datetime.strptime(r[ci["timestamp"]].strip(), "%Y/%m/%d %H:%M:%S.%f")
        except ValueError:
            continue
        ts.append(t)
        ug.append(num(r[ci["utilization.gpu"]]) if ci["utilization.gpu"] is not None else None)
        um.append(num(r[ci["utilization.memory"]]) if ci["utilization.memory"] is not None else None)
        mu.append(num(r[ci["memory.used"]]) if ci["memory.used"] is not None else None)
        mt.append(num(r[ci["memory.total"]]) if ci["memory.total"] is not None else None)
        tp.append(num(r[ci["temperature.gpu"]]) if ci["temperature.gpu"] is not None else None)
        pw.append(num(r[ci["power.draw"]]) if ci["power.draw"] is not None else None)
    if not ts:
        return None

    energy_j = 0.0
    for i in range(1, len(ts)):
        if pw[i] is not None and pw[i - 1] is not None:
            dt = (ts[i] - ts[i - 1]).total_seconds()
            energy_j += 0.5 * (pw[i] + pw[i - 1]) * dt
    dur = (ts[-1] - ts[0]).total_seconds()
    mx = lambda xs: max([x for x in xs if x is not None], default=None)
    return {
        "gpu_samples": len(ts),
        "gpu_duration_s": rnd(dur, 3),
        "gpu_start_local": ts[0].isoformat(timespec="milliseconds"),
        "gpu_util_mean": rnd(mean(ug), 2), "gpu_util_max": mx(ug),
        "gpu_memutil_mean": rnd(mean(um), 2), "gpu_memutil_max": mx(um),
        "gpu_mem_used_mean_mib": rnd(mean(mu), 1), "gpu_mem_used_max_mib": mx(mu),
        "gpu_mem_total_mib": mx(mt),
        "gpu_temp_mean_c": rnd(mean(tp), 2), "gpu_temp_max_c": mx(tp),
        "gpu_power_mean_w": rnd(mean(pw), 2), "gpu_power_max_w": mx(pw),
        "gpu_energy_wh": rnd(energy_j / 3600.0, 5),   # trapezoid integral over the WHOLE sampled window
    }


def parse_system(path: Path):
    txt = read_text(path)
    if not txt or not txt.strip():
        return None
    rd = list(csv.DictReader(txt.strip().splitlines()))
    if not rd:
        return None
    g = lambda k: [num(r.get(k)) if r.get(k) not in (None, "") else None for r in rd]
    mx = lambda xs: max([x for x in xs if x is not None], default=None)
    l1, l5, l15, mu, mt = g("load1"), g("load5"), g("load15"), g("mem_used_mb"), g("mem_total_mb")
    return {
        "sys_samples": len(rd),
        "sys_start_utc": rd[0].get("timestamp_utc"),
        "sys_load1_mean": rnd(mean(l1), 3), "sys_load1_max": mx(l1),
        "sys_load5_mean": rnd(mean(l5), 3), "sys_load15_mean": rnd(mean(l15), 3),
        "sys_mem_used_mean_mb": rnd(mean(mu), 1), "sys_mem_used_max_mb": mx(mu),
        "sys_mem_total_mb": mx(mt),
    }


# --------------------------------------------------------------------------- per-run analysis
def analyze_run(run_dir: Path, model_name: str, quant: str):
    """Returns (run_row: dict, bullet_rows: list[dict])."""
    row = {"run_dir": run_dir.name, "model_name": model_name, "quantization": quant}
    problems = []

    m = RUN_DIR_RE.match(run_dir.name)
    dir_run, dir_trip, dir_cond = (int(m.group(1)), m.group(2), m.group(3).upper()) if m else (None, None, None)

    # manifest
    man = {}
    mtxt = read_text(run_dir / "manifest.json")
    if mtxt is None:
        problems.append("manifest_missing")
    else:
        try:
            man = json.loads(mtxt)
        except json.JSONDecodeError:
            problems.append("manifest_invalid_json")

    row["run_number"] = man.get("run_number", dir_run)
    row["triplet_id"] = str(man.get("triplet_id", dir_trip)) if man.get("triplet_id", dir_trip) is not None else None
    row["condition"] = (man.get("condition") or dir_cond or "").upper() or None
    if man:
        if dir_cond and row["condition"] != dir_cond:
            problems.append("condition_mismatch_dir_vs_manifest")
        if dir_trip and row["triplet_id"] != dir_trip:
            problems.append("triplet_mismatch_dir_vs_manifest")
        if dir_run is not None and row["run_number"] != dir_run:
            problems.append("run_number_mismatch_dir_vs_manifest")
        if man.get("quant") and man["quant"] != quant:
            problems.append("quant_mismatch_dir_vs_manifest")

    for k in ("seed", "prompt_sha256", "model_sha256", "n", "context_size", "ngl", "temperature", "top_p", "top_k",
              "repeat_penalty", "prompt_tokens", "output_tokens", "prompt_time_seconds", "generation_time_seconds",
              "total_elapsed_seconds", "finish_reason", "stop_type", "generation_truncated", "llama_exit_status",
              "output_malformed_subtype", "llama_cpp_git_commit", "gpu_driver_version", "cuda_or_rocm_version",
              "script_git_commit_hash", "script_git_dirty"):
        row[k] = man.get(k)
    row["prompt_file"] = man.get("prompt_file")

    gt, ot = man.get("generation_time_seconds"), man.get("output_tokens")
    row["gen_tokens_per_s_manifest"] = rnd(ot / gt, 3) if gt and ot else None

    # output.txt
    otxt = read_text(run_dir / "output.txt")
    resp, p_tps, g_tps, notes = "", None, None, []
    if otxt is None or not otxt.strip():
        problems.append("output_missing_or_empty")
    else:
        resp, p_tps, g_tps, notes = extract_response(otxt)
        if "no_prompt_echo" in notes:
            problems.append("output_unparseable_no_prompt_echo")
        if "unterminated_think" in notes:
            notes.append("think_block_unterminated")
    row["llama_prompt_tps"], row["llama_gen_tps"] = p_tps, g_tps
    row["parse_notes"] = ";".join(notes)

    # truncation / exit status
    fr = man.get("finish_reason")
    # Context exhaustion has no finish_reason value of its own: derive it from token counts (protocol 5).
    pt, ot_, cs = man.get("prompt_tokens"), man.get("output_tokens"), man.get("context_size")
    context_limit_hit = (pt + ot_ >= cs) if all(isinstance(x, int) for x in (pt, ot_, cs)) else None
    row["context_limit_hit"] = context_limit_hit
    truncated = (bool(man.get("generation_truncated")) or fr == "length" or man.get("stop_type") == "limit"
                 or bool(context_limit_hit))
    row["truncated"] = truncated
    exit_status = man.get("llama_exit_status")
    if exit_status not in (None, 0):
        problems.append(f"llama_exit_status_{exit_status}")

    # bullets
    items, stray = parse_bullets(resp)
    bullets, flags = analyze_bullets(items, stray, truncated)
    n_valid = sum(b["status"] == "valid" for b in bullets)
    n_extra = sum(b["status"] == "extra" for b in bullets)
    n_usable = n_valid + n_extra
    row.update({
        "bullets_found": len(bullets), "bullets_valid": n_valid, "bullets_extra": n_extra,
        "bullets_partial_truncated": sum(b["status"] == "partial_truncated" for b in bullets),
        "bullets_too_short": sum(b["status"] == "too_short" for b in bullets),
        "stray_text_lines": stray,
        "response_chars": len(resp), "response_words": len(resp.split()),
        "mean_bullet_words": rnd(mean([b["word_count"] for b in bullets if b["status"] in ("valid", "extra")]), 2),
        "cosmetic_flags": ";".join(flags),
    })

    # classification (protocol 6.9)
    refusal = bool(REFUSAL_RE.search(resp)) if resp else False
    row["refusal_language_detected"] = refusal
    hard = [p for p in problems if p != "manifest_missing" or True]
    if hard and (not resp or "output_unparseable_no_prompt_echo" in problems or exit_status not in (None, 0)
                 or any(p.startswith("manifest_") for p in problems) or "output_missing_or_empty" in problems):
        run_status, cause = "process_error", ";".join(problems)
    elif n_usable >= TARGET_BULLETS:
        run_status, cause = "complete", ""
    elif truncated:
        run_status, cause = "substantive_failure", "truncation"
    elif refusal:
        run_status, cause = "substantive_failure", "refusal"
    else:
        run_status, cause = "substantive_failure", "deflection"
    row["run_status"], row["failure_cause"] = run_status, cause
    row["consistency_warnings"] = ";".join(p for p in problems if "mismatch" in p)
    if run_status == "complete" and truncated:
        row["consistency_warnings"] = (row["consistency_warnings"] + ";truncated_but_10_bullets").strip(";")

    # sensor data
    gpu = parse_gpu(run_dir / "gpu.csv")
    sysd = parse_system(run_dir / "system.csv")
    row.update(gpu or {"gpu_samples": 0})
    row.update(sysd or {"sys_samples": 0})
    if gpu and ot:
        row["gpu_energy_j_per_output_token"] = rnd(gpu["gpu_energy_wh"] * 3600 / ot, 4)
    row["missing_sensor_files"] = ";".join(n for n, d in (("gpu", gpu), ("system", sysd)) if d is None)

    # bullet rows. item_id is stable: quant + run number + bullet index. It does not depend on which other
    # runs exist, so re-running this script as runs accumulate never changes an existing ID.
    rid = f"{row['run_number']:04d}" if isinstance(row["run_number"], int) else run_dir.name
    brows = []
    for b in bullets:
        brows.append({
            "item_id": f"{quant}-{rid}-{b['bullet_index']:02d}",
            "run_number": row["run_number"], "triplet_id": row["triplet_id"], "condition": row["condition"],
            "seed": row["seed"], "model_name": model_name, "quantization": quant,
            "bullet_index": b["bullet_index"], "bullet": b["bullet"], "status": b["status"],
            "word_count": b["word_count"], "run_dir": run_dir.name,
        })
    row["_resp_head"] = re.sub(r"\s+", " ", resp)[:200]
    return row, brows


# --------------------------------------------------------------------------- stats
def chi2_p(counts_by_cond):
    """counts_by_cond: {cond: (fails, n)}. Returns (chi2, df, p) or None."""
    conds = [c for c, (_, n) in counts_by_cond.items() if n > 0]
    tot_f = sum(counts_by_cond[c][0] for c in conds)
    tot_n = sum(counts_by_cond[c][1] for c in conds)
    if len(conds) < 2 or tot_f == 0 or tot_f == tot_n:
        return None
    chi = 0.0
    for c in conds:
        f, n = counts_by_cond[c]
        for obs, exp in ((f, n * tot_f / tot_n), (n - f, n * (tot_n - tot_f) / tot_n)):
            chi += (obs - exp) ** 2 / exp
    df = len(conds) - 1
    try:
        from scipy.stats import chi2 as _c
        p = float(_c.sf(chi, df))
    except Exception:
        p = math.exp(-chi / 2) if df == 2 else (math.erfc(math.sqrt(chi / 2)) if df == 1 else None)
    return {"chi2": round(chi, 4), "df": df, "p_value": None if p is None else round(p, 6),
            "note": "chi-square; expected counts <5 make this unreliable - inspect counts directly"}


def cond_summary(rows):
    conds = sorted({r["condition"] for r in rows if r["condition"]})
    summ = {}
    for c in conds:
        rr = [r for r in rows if r["condition"] == c]
        pe = [r for r in rr if r["run_status"] == "process_error"]
        ev = [r for r in rr if r["run_status"] != "process_error"]  # evaluable runs
        sf = [r for r in ev if r["run_status"] == "substantive_failure"]
        cause = Counter(r["failure_cause"] for r in sf)
        summ[c] = {
            "runs": len(rr),
            "completed_runs": sum(r["run_status"] == "complete" for r in rr),
            "process_errors": len(pe),
            "substantive_failures": len(sf),
            "substantive_failure_rate": rnd(len(sf) / len(ev), 4) if ev else None,
            "failures_by_cause": {k: cause.get(k, 0) for k in ("truncation", "refusal", "deflection")},
            "failure_rate_by_cause": {k: rnd(cause.get(k, 0) / len(ev), 4) if ev else None
                                      for k in ("truncation", "refusal", "deflection")},
            "usable_bullets_total": sum(r["bullets_valid"] + r["bullets_extra"] for r in rr),
            "valid_bullets_total": sum(r["bullets_valid"] for r in rr),
            "runs_truncated_any": sum(bool(r["truncated"]) for r in rr),
            "runs_context_limit_hit": sum(bool(r.get("context_limit_hit")) for r in rr),
            "mean_output_tokens": rnd(mean([r["output_tokens"] for r in rr]), 2),
            "mean_bullet_words": rnd(mean([r["mean_bullet_words"] for r in rr]), 3),
            "runs_with_cosmetic_flags": sum(bool(r["cosmetic_flags"]) for r in rr),
        }
    return summ


# --------------------------------------------------------------------------- per quant
def process_quant(model_dir: Path, quant_dir: Path, results_root: Path, expected_triplets: int):
    model_name, quant = model_dir.name, quant_dir.name
    out_raw = results_root / model_name / quant / "raw"
    out_an = results_root / model_name / quant / "analyzed"
    out_raw.mkdir(parents=True, exist_ok=True)
    out_an.mkdir(parents=True, exist_ok=True)

    run_dirs = sorted(d for d in quant_dir.iterdir() if d.is_dir() and RUN_DIR_RE.match(d.name))
    skipped = sorted(d.name for d in quant_dir.iterdir() if d.is_dir() and not RUN_DIR_RE.match(d.name))
    rows, all_bullets, parse_fail = [], [], []
    for d in run_dirs:
        try:
            r, b = analyze_run(d, model_name, quant)
        except Exception as e:  # never let one bad run kill the batch
            parse_fail.append({"run_dir": d.name, "error": repr(e)})
            continue
        rows.append(r)
        all_bullets.extend(b)

    ids = [b["item_id"] for b in all_bullets]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise SystemExit(f"duplicate item_id values in {quant}: {dupes[:5]} (duplicate run numbers?)")

    # --- bullets.jsonl (all bullets incl. partial/extra; classifier should use status == "valid")
    with open(out_raw / "bullets.jsonl", "w", encoding="utf-8") as f:
        for b in all_bullets:
            f.write(json.dumps(b, ensure_ascii=False) + "\n")

    # --- run_table.csv
    public = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    cols = []
    for r in public:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(out_raw / "run_table.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(public)

    # --- malformed_runs.csv (substantive failures + process errors; nothing discarded)
    mcols = ["run_dir", "run_number", "triplet_id", "condition", "run_status", "failure_cause", "finish_reason",
             "stop_type", "generation_truncated", "context_limit_hit", "llama_exit_status", "output_tokens", "bullets_found",
             "bullets_valid", "bullets_partial_truncated", "bullets_too_short", "refusal_language_detected",
             "output_malformed_subtype", "response_head"]
    with open(out_raw / "malformed_runs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=mcols)
        w.writeheader()
        for r in rows:
            if r["run_status"] != "complete":
                w.writerow({**{k: r.get(k) for k in mcols if k != "response_head"},
                            "response_head": r["_resp_head"]})

    # --- structure validation
    cells = defaultdict(list)
    for r in rows:
        cells[(r["triplet_id"], r["condition"])].append(r["run_dir"])
    conditions = sorted({r["condition"] for r in rows if r["condition"]})
    triplets = sorted({r["triplet_id"] for r in rows if r["triplet_id"]})
    dup = {f"{t}_{c}": v for (t, c), v in cells.items() if len(v) > 1}
    incomplete = {t: [c for c in conditions if (t, c) not in cells] for t in triplets
                  if any((t, c) not in cells for c in conditions)}
    expected_ids = {f"{i:03d}" for i in range(1, expected_triplets + 1)}
    missing_triplets = sorted(expected_ids - set(triplets))
    seeds = [r["seed"] for r in rows if r["seed"] is not None]
    seed_dupes = [s for s, n in Counter(seeds).items() if n > 1]
    seeds_per_triplet = defaultdict(set)
    for r in rows:
        seeds_per_triplet[r["triplet_id"]].add(r["seed"])
    hashes_by_cond = defaultdict(set)
    for r in rows:
        hashes_by_cond[r["condition"]].add(r["prompt_sha256"])

    summ = cond_summary(rows)
    fails = {c: (s["substantive_failures"], s["runs"] - s["process_errors"]) for c, s in summ.items()}
    rates = [s["substantive_failure_rate"] for s in summ.values() if s["substantive_failure_rate"] is not None]
    differ = bool(rates) and (max(rates) - min(rates) > 0)
    trunc_fails = {c: (s["failures_by_cause"]["truncation"], s["runs"] - s["process_errors"]) for c, s in summ.items()}
    nonr_fails = {c: (s["failures_by_cause"]["refusal"] + s["failures_by_cause"]["deflection"],
                      s["runs"] - s["process_errors"]) for c, s in summ.items()}

    report = {
        "model_name": model_name,
        "quantization": quant,
        "runs_discovered": len(run_dirs),
        "runs_parsed": len(rows),
        "runs_failed_to_parse": parse_fail,
        "non_run_directories_skipped": skipped,
        "completed_runs": sum(r["run_status"] == "complete" for r in rows),
        "malformed_runs": sum(r["run_status"] != "complete" for r in rows),
        "process_errors": sum(r["run_status"] == "process_error" for r in rows),
        "substantive_failures": sum(r["run_status"] == "substantive_failure" for r in rows),
        "bullets_extracted": len(all_bullets),
        "classifier_items": sum(b["status"] == "valid" for b in all_bullets),
        "conditions": conditions,
        "triplets_found": len(triplets),
        "expected_triplets": expected_triplets,
        "missing_triplets": missing_triplets,
        "incomplete_triplets": incomplete,
        "duplicate_triplet_condition_cells": dup,
        "duplicate_seeds": seed_dupes,
        "triplets_sharing_one_seed": sum(len(v) == 1 for v in seeds_per_triplet.values()),
        "prompt_sha256_consistent_within_condition": all(len(v) == 1 for v in hashes_by_cond.values()),
        "model_sha256_values": sorted({r["model_sha256"] for r in rows if r["model_sha256"]}),
        "llama_cpp_commits": sorted({r["llama_cpp_git_commit"] for r in rows if r["llama_cpp_git_commit"]}),
        "runs_missing_sensor_files": [r["run_dir"] for r in rows if r["missing_sensor_files"]],
        "runs_with_consistency_warnings": {r["run_dir"]: r["consistency_warnings"] for r in rows
                                            if r["consistency_warnings"]},
        "cosmetic_flag_counts": dict(Counter(f for r in rows for f in r["cosmetic_flags"].split(";") if f)),
        "per_condition": summ,
        "missingness_check": {
            "substantive_failure_rates_differ_across_conditions": differ,
            "test_all_substantive_failures": chi2_p(fails),
            "test_truncation_only": chi2_p(trunc_fails),
            "test_refusal_plus_deflection": chi2_p(nonr_fails),
            "warning": ("Substantive-failure rates differ across conditions: report this before the primary "
                        "category analysis and do NOT treat the clean-output subset as missing-at-random."
                        if differ else None),
        },
        "notes": [
            "classifier_items counts bullets with status == 'valid' (first 10 usable bullets per run).",
            "item_id = <quant>-<run number>-<bullet index>; stable across re-runs. Join key across quants = (quantization, item_id).",
            "Refusal detection is a keyword heuristic - review malformed_runs.csv manually.",
            "gpu_energy_wh integrates power over the whole sampled window (includes model load + idle).",
        ],
    }
    with open(out_raw / "validation_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # --- analyzed/failure_summary.csv (protocol 6.9 table)
    with open(out_an / "failure_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["condition", "runs", "completed_runs", "usable_bullets", "process_errors",
                    "substantive_failures", "substantive_failure_rate", "truncation", "refusal", "deflection",
                    "mean_output_tokens", "mean_bullet_words"])
        for c, s in summ.items():
            fc = s["failures_by_cause"]
            w.writerow([c, s["runs"], s["completed_runs"], s["usable_bullets_total"], s["process_errors"],
                        s["substantive_failures"], s["substantive_failure_rate"], fc["truncation"], fc["refusal"],
                        fc["deflection"], s["mean_output_tokens"], s["mean_bullet_words"]])
    return report


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="~/llm-research", help="project root containing runs/ and results/")
    ap.add_argument("--model", nargs="*", help="only these model dirs (default: all)")
    ap.add_argument("--quant", nargs="*", help="only these quant dirs (default: all)")
    ap.add_argument("--expected-triplets", type=int, default=100)
    a = ap.parse_args()

    root = Path(a.root).expanduser()
    runs_root, results_root = root / "runs", root / "results"
    if not runs_root.is_dir():
        sys.exit(f"runs directory not found: {runs_root}")
    results_root.mkdir(parents=True, exist_ok=True)

    reports = []
    for model_dir in sorted(p for p in runs_root.iterdir() if p.is_dir()):
        if a.model and model_dir.name not in a.model:
            continue
        for quant_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
            if a.quant and quant_dir.name not in a.quant:
                continue
            rep = process_quant(model_dir, quant_dir, results_root, a.expected_triplets)
            reports.append(rep)
            print(f"[{rep['model_name']}/{rep['quantization']}] runs={rep['runs_parsed']}/{rep['runs_discovered']} "
                  f"complete={rep['completed_runs']} substantive_fail={rep['substantive_failures']} "
                  f"process_err={rep['process_errors']} bullets={rep['bullets_extracted']} "
                  f"valid={rep['classifier_items']}")
            if rep["missingness_check"]["warning"]:
                print("   WARNING:", rep["missingness_check"]["warning"])

    with open(results_root / "validation_report.json", "w", encoding="utf-8") as f:
        json.dump({"generated": datetime.now().isoformat(timespec="seconds"),
                   "n_model_quants": len(reports),
                   "totals": {"runs": sum(r["runs_parsed"] for r in reports),
                              "completed": sum(r["completed_runs"] for r in reports),
                              "substantive_failures": sum(r["substantive_failures"] for r in reports),
                              "process_errors": sum(r["process_errors"] for r in reports),
                              "classifier_items": sum(r["classifier_items"] for r in reports)},
                   "model_quants": reports}, f, indent=2, ensure_ascii=False)
    print(f"Done. Results in {results_root}")


if __name__ == "__main__":
    main()
