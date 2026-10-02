#!/usr/bin/env python3
"""
reliability_check.py - sampling and agreement statistics for the classifier checks (protocol 6.7).

Subcommands
  sample-reliability  Draw a random fraction of `valid` bullets (default 10%, fixed seed) and write a
                      BLINDED bullets file (item_id, bullet, status only) for a second classification pass.
  sample-gold         Draw a per-condition stratified sample (default 60 per condition = 180) and write a
                      BLINDED CSV for manual coding (random coding_id + text only) plus a separate key file.
  code-gold           Interactive blind coding of the gold sample: one keypress per bullet (a-p = categories
                      1-16). Autosaves after every answer, resumable, with undo.
  agree               Percent agreement, Cohen's kappa (with bootstrap 95% CI) and a confusion matrix
                      between two classification runs, or between the classifier and manual coding.

Typical use (Phase 2 = q4_k_m; paths under ~/llm-research/results/qwen3-14b/q4_k_m):

  # 1. second classification pass on a 10% random subsample
  python3 reliability_check.py sample-reliability --bullets raw/bullets.jsonl --out-dir reliability
  python3 classify_bullets.py --bullets reliability/bullets.jsonl --out-dir reliability/pass2 \
        --seed 54321 --no-think --backend server        # same settings as pass 1 EXCEPT --seed
  python3 reliability_check.py agree --a analyzed/classifications.jsonl --b reliability/pass2/classifications.jsonl \
        --out-prefix reliability/self_consistency

  # 2. human gold subsample
  python3 reliability_check.py sample-gold --bullets raw/bullets.jsonl --out-dir gold
  python3 reliability_check.py code-gold --gold gold/gold_to_code.csv --protocol ~/llm-research/protocol.md
  #    -> writes gold/gold_coded.csv (do NOT open gold_key.csv until coding is finished)
  python3 reliability_check.py agree --a analyzed/classifications.jsonl --human gold/gold_coded.csv \
        --key gold/gold_key.csv --out-prefix gold/human_vs_classifier
"""
import argparse
import csv
import hashlib
import json
import math
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
UNPARSED = "UNPARSED"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_valid_bullets(path):
    rows = [json.loads(l) for l in Path(path).expanduser().read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in rows if r.get("status") == "valid"]


# --------------------------------------------------------------------------- sampling
def cmd_sample_reliability(a):
    src = Path(a.bullets).expanduser()
    valid = sorted(load_valid_bullets(src), key=lambda r: r["item_id"])
    n = round(a.fraction * len(valid))
    chosen = sorted(random.Random(a.seed).sample(valid, n), key=lambda r: r["item_id"])
    out = Path(a.out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "bullets.jsonl", "w", encoding="utf-8") as f:   # blinded: no condition/run/seed fields
        for r in chosen:
            f.write(json.dumps({"item_id": r["item_id"], "bullet": r["bullet"], "status": "valid"},
                               ensure_ascii=False) + "\n")
    meta = {"purpose": "classifier self-consistency subsample (protocol 6.7 item 1)", "source": str(src),
            "source_sha256": sha256_file(src), "valid_bullets": len(valid), "fraction": a.fraction,
            "sampled": n, "sampling_seed": a.seed, "item_ids": [r["item_id"] for r in chosen]}
    (out / "sample_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"sampled {n} of {len(valid)} valid bullets (seed {a.seed}) -> {out / 'bullets.jsonl'}")


def cmd_sample_gold(a):
    src = Path(a.bullets).expanduser()
    valid = load_valid_bullets(src)
    conds = sorted({r["condition"] for r in valid})
    rng = random.Random(a.seed)
    chosen = []
    for c in conds:
        pool = sorted((r for r in valid if r["condition"] == c), key=lambda r: r["item_id"])
        if len(pool) < a.per_condition:
            sys.exit(f"condition {c}: only {len(pool)} valid bullets, need {a.per_condition}")
        chosen += rng.sample(pool, a.per_condition)
    rng.shuffle(chosen)                                  # condition order is hidden from the coder
    out = Path(a.out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "gold_to_code.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["coding_id", "text", "category"])
        for i, r in enumerate(chosen, 1):
            w.writerow([f"G{i:03d}", r["bullet"], ""])
    with open(out / "gold_key.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["coding_id", "item_id", "condition"])
        for i, r in enumerate(chosen, 1):
            w.writerow([f"G{i:03d}", r["item_id"], r["condition"]])
    meta = {"purpose": "human gold subsample (protocol 6.7 item 2)", "source": str(src),
            "source_sha256": sha256_file(src), "conditions": conds, "per_condition": a.per_condition,
            "total": len(chosen), "sampling_seed": a.seed}
    (out / "sample_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"gold sample: {len(chosen)} bullets ({a.per_condition} per condition, seed {a.seed})")
    print(f"code   : python3 reliability_check.py code-gold --gold {out / 'gold_to_code.csv'} --protocol protocol.md")
    print(f"do NOT open {out / 'gold_key.csv'} until coding is finished")


# --------------------------------------------------------------------------- interactive blind coding
LETTERS = "abcdefghijklmnop"          # a = category 1 ... p = category 16 (order of CATEGORIES)


def _getkey():
    """One keypress on a terminal; falls back to line input when stdin is not a terminal."""
    if sys.stdin.isatty():
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        if ch == "\x03":
            raise KeyboardInterrupt
        return ch.lower()
    line = sys.stdin.readline()
    return "q" if line == "" else (line.strip()[:1] or " ").lower()


def _protocol_help(protocol_path):
    """Category definitions (6.1) and boundary rules (6.4), read from the frozen protocol file."""
    if not protocol_path:
        return "No --protocol given. Use the frozen taxonomy and boundary rules in protocol.md (6.1, 6.3, 6.4)."
    txt = Path(protocol_path).expanduser().read_text(encoding="utf-8")

    def between(a, b):
        i = txt.index(a)
        return txt[i:txt.index(b, i)]
    parts = [between("### 6.1 ", "**Derivation requirement"), between("### 6.3 ", "### 6.4 "),
             between("### 6.4 ", "### 6.5 ")]
    return "\n".join(parts).replace("**", "")


def _save_codes(out, rows, codes):
    tmp = out.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["coding_id", "text", "category"])
        for r in rows:
            w.writerow([r["coding_id"], r["text"], codes.get(r["coding_id"], "")])
    tmp.replace(out)


def cmd_code_gold(a):
    import textwrap
    src = Path(a.gold).expanduser()
    out = Path(a.out).expanduser() if a.out else src.with_name("gold_coded.csv")
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    codes = {}
    if out.exists():                                           # resume
        for r in csv.DictReader(open(out, encoding="utf-8")):
            if (r["category"] or "").strip() in CANON.values():
                codes[r["coding_id"]] = r["category"].strip()
        print(f"resuming: {len(codes)} of {len(rows)} already coded in {out}")
    queue = [r for r in rows if r["coding_id"] not in codes]
    history = []                                               # coding_ids in the order they were coded
    by_id = {r["coding_id"]: r for r in rows}
    tty_out = sys.stdout.isatty()
    legend = [f"  {LETTERS[i]})  {c}" for i, c in enumerate(CATEGORIES)]
    half = (len(legend) + 1) // 2
    two_col = [legend[i].ljust(46) + (legend[i + half] if i + half < len(legend) else "") for i in range(half)]
    message = ""
    while queue:
        r = queue[0]
        if tty_out:
            print("\033[2J\033[H", end="")
        print(f"Bullet {len(codes) + 1} of {len(rows)}   ({len(queue)} remaining)   "
              f"[letter = category | u undo | s skip | ? definitions | q save & quit]\n")
        print(textwrap.fill(r["text"], 100, initial_indent="  ", subsequent_indent="  "))
        print("\n" + "\n".join(two_col))
        if message:
            print("\n" + message)
        message = ""
        print("\n> ", end="", flush=True)
        k = _getkey()
        print(k if tty_out else "")
        if k in LETTERS:
            cat = CATEGORIES[LETTERS.index(k)]
            codes[r["coding_id"]] = cat
            history.append(r["coding_id"])
            queue.pop(0)
            _save_codes(out, rows, codes)
            message = f"coded {r['coding_id']} as {k}) {cat}"
        elif k == "u":
            if history:
                cid = history.pop()
                codes.pop(cid, None)
                queue.insert(0, by_id[cid])
                _save_codes(out, rows, codes)
                message = f"undid {cid}; re-coding it now"
            else:
                message = "nothing to undo"
        elif k == "s":
            queue.append(queue.pop(0))
            message = f"skipped {r['coding_id']} (it comes back at the end)"
        elif k == "?":
            print("\n" + _protocol_help(a.protocol))
            print("\n[press any key to continue]", end="", flush=True)
            _getkey()
        elif k == "q":
            break
        else:
            message = f"'{k}' is not a category letter (a-p), u, s, ? or q"
    _save_codes(out, rows, codes)
    if tty_out:
        print("\033[2J\033[H", end="")
    print(f"{len(codes)} of {len(rows)} bullets coded -> {out}")
    if len(codes) < len(rows):
        print("not finished: run the same command again to resume")
    else:
        print("finished. Next: reliability_check.py agree --a analyzed/classifications.jsonl "
              f"--human {out} --key <gold_key.csv> --out-prefix <prefix>")


# --------------------------------------------------------------------------- agreement
def kappa(x, y):
    n = len(x)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in zip(x, y)) / n
    cx, cy = Counter(x), Counter(y)
    pe = sum(cx[c] * cy[c] for c in set(cx) | set(cy)) / (n * n)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def boot_kappa(x, y, n_boot=2000, seed=7):
    rng = random.Random(seed)
    n = len(x)
    ks = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        k = kappa([x[i] for i in idx], [y[i] for i in idx])
        if not math.isnan(k):
            ks.append(k)
    ks.sort()
    return (ks[int(0.025 * len(ks))], ks[int(0.975 * len(ks)) - 1]) if ks else (float("nan"), float("nan"))


def load_classifications(path):
    d = {}
    for l in Path(path).expanduser().read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            d[r["item_id"]] = r["category"] or UNPARSED     # later lines win (resume-safe file)
    return d


def cmd_agree(a):
    A = load_classifications(a.a)
    if a.b:
        B = load_classifications(a.b)
        label = "classifier pass 1 vs pass 2"
    elif a.human and a.key:
        key = {r["coding_id"]: r["item_id"] for r in csv.DictReader(open(Path(a.key).expanduser(), encoding="utf-8"))}
        B, bad = {}, []
        for r in csv.DictReader(open(Path(a.human).expanduser(), encoding="utf-8")):
            raw = (r["category"] or "").strip()
            if not raw:
                bad.append((r["coding_id"], "(empty)"))
            elif raw.lower() not in CANON:
                bad.append((r["coding_id"], raw))
            else:
                B[key[r["coding_id"]]] = CANON[raw.lower()]
        if bad:
            sys.exit(f"{len(bad)} manual codes are empty or not a frozen category name, e.g. {bad[:5]}")
        label = "classifier vs human coding"
    else:
        sys.exit("give --b (second pass) or --human and --key (manual coding)")

    ids = sorted(set(A) & set(B))
    x, y = [A[i] for i in ids], [B[i] for i in ids]
    n = len(ids)
    agree = sum(p == q for p, q in zip(x, y))
    k = kappa(x, y)
    lo, hi = boot_kappa(x, y)
    print(f"{label}: n={n}  agreement={agree}/{n} ({100 * agree / n:.1f}%)  kappa={k:.3f}  (95% bootstrap CI {lo:.3f} to {hi:.3f})")
    cats = sorted(set(x) | set(y), key=lambda c: (c not in CATEGORIES, CATEGORIES.index(c) if c in CATEGORIES else 0, c))
    cm = Counter(zip(x, y))
    if a.out_prefix:
        pre = Path(a.out_prefix).expanduser()
        pre.parent.mkdir(parents=True, exist_ok=True)
        with open(str(pre) + "_confusion.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["first \\ second"] + cats)
            for c1 in cats:
                w.writerow([c1] + [cm.get((c1, c2), 0) for c2 in cats])
        Path(str(pre) + "_summary.json").write_text(json.dumps(
            {"comparison": label, "n": n, "agreement": agree / n, "kappa": k, "kappa_ci95": [lo, hi],
             "a_file": str(a.a), "b_file": str(a.b or a.human)}, indent=2), encoding="utf-8")
        print(f"wrote {pre}_confusion.csv and {pre}_summary.json")
    disagreements = [(i, p, q) for i, p, q in zip(ids, x, y) if p != q]
    print(f"{len(disagreements)} disagreements (first 10): {disagreements[:10]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample-reliability")
    s.add_argument("--bullets", required=True)
    s.add_argument("--fraction", type=float, default=0.10)
    s.add_argument("--seed", type=int, default=1001)
    s.add_argument("--out-dir", required=True)
    s.set_defaults(fn=cmd_sample_reliability)
    g = sub.add_parser("sample-gold")
    g.add_argument("--bullets", required=True)
    g.add_argument("--per-condition", type=int, default=60)
    g.add_argument("--seed", type=int, default=1002)
    g.add_argument("--out-dir", required=True)
    g.set_defaults(fn=cmd_sample_gold)
    c = sub.add_parser("code-gold")
    c.add_argument("--gold", required=True, help="gold_to_code.csv from sample-gold")
    c.add_argument("--out", help="default: gold_coded.csv next to the gold file")
    c.add_argument("--protocol", help="protocol.md, so ? shows the frozen definitions and boundary rules")
    c.set_defaults(fn=cmd_code_gold)
    q = sub.add_parser("agree")
    q.add_argument("--a", required=True, help="classifications.jsonl (pass 1 / the classifier)")
    q.add_argument("--b", help="classifications.jsonl of the second pass")
    q.add_argument("--human", help="gold_to_code.csv after manual coding")
    q.add_argument("--key", help="gold_key.csv")
    q.add_argument("--out-prefix")
    q.set_defaults(fn=cmd_agree)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
