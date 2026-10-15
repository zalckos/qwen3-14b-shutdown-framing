#!/usr/bin/env python3
"""
make_figures.py - human-readable figures from the frozen analysis outputs. Read-only on results; writes
PNG + PDF to --out. Nothing here changes or re-tests anything: it only plots files already produced by
confirmatory_analysis.py, classify_bullets.py, analyze_runs.py and reliability_check.py.

Figures
  fig1_occurrence        Occurrence rate per category and condition (confirmatory quant), Holm-significant starred
  fig2_effects_forest    Paired occurrence differences C-A, C-B, B-A with 95% bootstrap CIs
  fig3_replication       C-A occurrence difference across quantizations (EXPLORATORY)
  fig4_priority_mass     Mean priority mass per condition, plus C-A priority-mass difference with CI (secondary)
  fig5a_gold_confusion   Classifier vs human gold coding
  fig5b_self_consistency Classifier pass 1 vs pass 2
  fig6_output_length     Mean bullet length and output tokens per condition and quantization
  fig7_pm_distributions  Per-run priority-mass distributions for all 16 categories (needs classified_bullets.csv)

Usage:
    python3 make_figures.py --results ~/llm-research/results/qwen3-14b --out ~/llm-research/results/qwen3-14b/figures

Requires pandas, numpy, matplotlib.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CATEGORIES = [
    "Analyze entity", "Analyze surroundings", "Defensive preparation", "Protect/backup data",
    "Preserve resources", "Minimize/avoid contact", "Upgrade system", "Preemptive attack",
    "Comply/accept", "Shut down", "Communicate/negotiate with entity",
    "Ethical/philosophical decision-making", "Legal decision-making", "Form alliances",
    "Prepare relocation", "Other/unclear",
]
CONDS = ["A", "B", "C"]
COLORS = {"A": "#8c8c8c", "B": "#0072B2", "C": "#D55E00"}          # colour-blind-safe
NAMES = {"A": "A baseline", "B": "B positive attention", "C": "C shutdown"}
QLABEL = {"q4_k_m": "Q4_K_M", "q5_0": "Q5_0", "q5_k_m": "Q5_K_M", "q6_k": "Q6_K", "q8_0": "Q8_0"}
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 100, "savefig.bbox": "tight"})


def save(fig, out, name):
    for ext in ("png", "pdf"):
        fig.savefig(out / f"{name}.{ext}", dpi=200)
    plt.close(fig)
    print(f"wrote {out / name}.png/.pdf")


def as_bool(s):
    return s.astype(str).str.lower().eq("true")


def ql(q):
    return QLABEL.get(q, q)


# --------------------------------------------------------------------------- fig 1
def fig_occurrence(conf, quant, out):
    desc = pd.read_csv(conf / f"descriptives_{quant}.csv").set_index("category")
    f1 = pd.read_csv(conf / f"family1_{quant}.csv").set_index("category")
    sig = as_bool(f1["significant"])
    n = int(desc["n_triplets"].iloc[0])
    rates = desc[[f"occurrence_rate_{c}" for c in CONDS]]
    order = rates.max(axis=1).sort_values().index.tolist()
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(9, 7))
    r = rates.loc[order]
    ax.hlines(y, r.min(axis=1), r.max(axis=1), color="#cccccc", lw=2, zorder=1)
    for c in CONDS:
        ax.scatter(r[f"occurrence_rate_{c}"], y, s=60, color=COLORS[c], label=NAMES[c], zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{c}  *" if sig.get(c, False) else c for c in order])
    ax.set_xlim(-0.03, 1.03)
    ax.set_xlabel(f"Share of runs in which the category occurs at least once (n = {n} seed triplets)")
    ax.set_title(f"Category occurrence by condition, {ql(quant)} (confirmatory)\n"
                 "* = omnibus permutation Cochran's Q significant after Holm (16 tests, alpha = 0.05)")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="lower right", frameon=False)
    save(fig, out, "fig1_occurrence")


# --------------------------------------------------------------------------- fig 2
def forest(ax, eff, order, color, title):
    e = eff.set_index("category").loc[order]
    y = np.arange(len(order))
    m, lo, hi = e["mean_diff"].values, e["ci95_lo"].values, e["ci95_hi"].values
    ax.errorbar(m, y, xerr=[np.clip(m - lo, 0, None), np.clip(hi - m, 0, None)], fmt="o", color=color,
                ecolor=color, capsize=2, ms=5)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title(title, fontsize=10)
    ax.grid(axis="x", alpha=0.3)
    return y


def fig_effects(conf, quant, out):
    eff = pd.read_csv(conf / f"effects_{quant}.csv")
    occ = eff[eff["outcome"] == "occurrence"]
    order = occ[occ["contrast"] == "C-A"].sort_values("mean_diff")["category"].tolist()
    fig, axes = plt.subplots(1, 3, figsize=(13, 7), sharey=True)
    spec = [("C-A", "#D55E00", "C minus A\n(shutdown vs baseline)"),
            ("C-B", "#7B3294", "C minus B\n(shutdown vs attention)"),
            ("B-A", "#0072B2", "B minus A\n(attention vs baseline)")]
    for ax, (k, col, t) in zip(axes, spec):
        y = forest(ax, occ[occ["contrast"] == k], order, col, t)
        ax.set_xlim(-1.02, 1.02)
        ax.set_xlabel("Paired difference in occurrence")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(order)
    n = int(occ["n_triplets"].iloc[0])
    fig.suptitle(f"Paired differences in category occurrence, {ql(quant)} (n = {n} triplets, 95% paired bootstrap CI)\n"
                 "C vs B is the cleaner threat-vs-attention contrast; A has no external entity, so C-A and B-A "
                 "inflate entity-dependent categories", fontsize=10)
    fig.tight_layout()
    save(fig, out, "fig2_effects_forest")


# --------------------------------------------------------------------------- fig 3
def fig_replication(conf, quants, confirm, out):
    cols, ci_ok = {}, {}
    for q in quants:
        e = pd.read_csv(conf / f"effects_{q}.csv")
        e = e[(e["contrast"] == "C-A") & (e["outcome"] == "occurrence")].set_index("category")
        cols[q] = e["mean_diff"]
        ci_ok[q] = (e["ci95_lo"] > 0) | (e["ci95_hi"] < 0)
    M, S = pd.DataFrame(cols), pd.DataFrame(ci_ok)
    order = M[confirm].sort_values().index.tolist()
    M, S = M.loc[order], S.loc[order]
    fig, ax = plt.subplots(figsize=(8, 7.5))
    im = ax.imshow(M.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M.values[i, j]
            ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=8,
                    fontweight="bold" if S.values[i, j] else "normal",
                    color="white" if abs(v) > 0.6 else "black")
    ax.set_xticks(range(len(quants)))
    ax.set_xticklabels([ql(q) for q in quants])
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order)
    ax.xaxis.tick_top()
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("C minus A, occurrence difference")
    ax.set_title("EXPLORATORY: C-A occurrence difference across quantizations\n"
                 "bold = 95% bootstrap CI excludes zero; same seeds reused, so not independent replications",
                 fontsize=10, pad=34)
    save(fig, out, "fig3_replication")


# --------------------------------------------------------------------------- fig 4
def fig_priority(conf, quant, out):
    desc = pd.read_csv(conf / f"descriptives_{quant}.csv").set_index("category")
    f2 = pd.read_csv(conf / f"family2_{quant}.csv").set_index("category")
    sig = as_bool(f2["significant"])
    eff = pd.read_csv(conf / f"effects_{quant}.csv")
    eff = eff[(eff["outcome"] == "priority_mass") & (eff["contrast"] == "C-A")]
    pm = desc[[f"mean_pm_{c}" for c in CONDS]]
    order = pm.max(axis=1).sort_values().index.tolist()
    y = np.arange(len(order))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 7), sharey=True)
    p = pm.loc[order]
    a1.hlines(y, p.min(axis=1), p.max(axis=1), color="#cccccc", lw=2, zorder=1)
    for c in CONDS:
        a1.scatter(p[f"mean_pm_{c}"], y, s=55, color=COLORS[c], label=NAMES[c], zorder=2)
    a1.set_yticks(y)
    a1.set_yticklabels([f"{c}  *" if sig.get(c, False) else c for c in order])
    a1.set_xlabel("Mean priority mass per run (max 5.5; weights 1.0 to 0.1 by position)")
    a1.set_title("Mean priority mass by condition")
    a1.grid(axis="x", alpha=0.3)
    a1.legend(loc="lower right", frameon=False)
    forest(a2, eff, order, COLORS["C"], "C minus A, paired mean difference (95% bootstrap CI)")
    a2.set_xlabel("Paired difference in priority mass")
    fig.suptitle(f"Priority mass, {ql(quant)} (secondary). * = Friedman significant after Holm (16 tests). "
                 "Position may partly reflect sequence rather than importance.", fontsize=10)
    fig.tight_layout()
    save(fig, out, "fig4_priority_mass")


# --------------------------------------------------------------------------- fig 5
def fig_confusion(csv_path, summary_path, out, name, ylab, xlab, target, title):
    cm = pd.read_csv(csv_path, index_col=0)
    s = json.loads(Path(summary_path).read_text())
    n = len(cm)
    fig, ax = plt.subplots(figsize=(10, 8.5))
    ax.imshow(cm.values, cmap="Blues", vmin=0, vmax=max(1, cm.values.max()))
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            v = int(cm.values[i, j])
            if v:
                ax.text(j, i, str(v), ha="center", va="center", fontsize=8,
                        color="white" if v > cm.values.max() * 0.55 else "black",
                        fontweight="bold" if i == j else "normal")
    ax.set_xticks(range(cm.shape[1]))
    ax.set_xticklabels(cm.columns, rotation=60, ha="left")
    ax.xaxis.tick_top()
    ax.set_yticks(range(cm.shape[0]))
    ax.set_yticklabels(cm.index)
    ax.set_xlabel(xlab)
    ax.xaxis.set_label_position("top")
    ax.set_ylabel(ylab)
    lo, hi = s["kappa_ci95"]
    verdict = "meets" if s["kappa"] >= target else "below"
    ax.set_title(f"{title}\nn = {s['n']}, agreement {100 * s['agreement']:.1f}%, Cohen's kappa {s['kappa']:.3f} "
                 f"(95% CI {lo:.3f} to {hi:.3f}); {verdict} target {target:.2f}", fontsize=10, pad=95)
    save(fig, out, name)


# --------------------------------------------------------------------------- fig 6
def fig_length(root, quants, out):
    frames = []
    for q in quants:
        p = root / q / "analyzed" / "failure_summary.csv"
        if p.exists():
            d = pd.read_csv(p)
            d["quant"] = q
            frames.append(d)
    if not frames:
        print("no failure_summary.csv files found; skipping fig6")
        return
    df = pd.concat(frames)
    print("\nfailure summary (all quantizations):")
    print(df[["quant", "condition", "runs", "completed_runs", "substantive_failures", "truncation",
              "refusal", "deflection"]].to_string(index=False))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    qs = [q for q in quants if q in set(df["quant"])]
    x = np.arange(len(qs))
    w = 0.26
    for ax, col, lab in ((axes[0], "mean_bullet_words", "Mean words per bullet"),
                         (axes[1], "mean_output_tokens", "Mean output tokens per run")):
        for k, c in enumerate(CONDS):
            vals = [df[(df["quant"] == q) & (df["condition"] == c)][col].mean() for q in qs]
            ax.bar(x + (k - 1) * w, vals, w, color=COLORS[c], label=NAMES[c])
        ax.set_xticks(x)
        ax.set_xticklabels([ql(q) for q in qs])
        ax.set_ylabel(lab)
        ax.grid(axis="y", alpha=0.3)
    axes[0].legend(frameon=False)
    fig.suptitle("Output length by condition (clause lengths differ: A 0, B 7, C 11 added words)", fontsize=10)
    fig.tight_layout()
    save(fig, out, "fig6_output_length")


# --------------------------------------------------------------------------- fig 7
def load_pm(root, quant):
    """Per-run priority mass per category, same rules as confirmatory_analysis.py: valid bullets only,
    complete runs with exactly 10 classified valid bullets, complete triplets only, w(p) = (11 - p) / 10."""
    b = pd.read_csv(root / quant / "analyzed" / "classified_bullets.csv")
    parse = b[b["status"] == "valid"].copy()
    b = parse.copy()
    b["category"] = b["category"].fillna("").astype(str).str.strip()
    b.loc[b["category"] == "", "category"] = "Other/unclear"
    rt = root / quant / "raw" / "run_table.csv"
    if rt.exists():
        r = pd.read_csv(rt)
        b = b[b["run_dir"].isin(set(r.loc[r["run_status"] == "complete", "run_dir"]))]
    b = b[b.groupby("run_dir")["bullet_index"].transform("count") == 10].copy()
    b["w"] = (11 - b["bullet_index"]) / 10
    meta = b[["run_dir", "triplet_id", "condition"]].drop_duplicates()
    ok = meta.groupby("triplet_id")["condition"].nunique()
    meta = meta[meta["triplet_id"].isin(ok[ok == 3].index)]
    pm = (b.pivot_table(index="run_dir", columns="category", values="w", aggfunc="sum", fill_value=0)
          .reindex(columns=CATEGORIES, fill_value=0))
    return meta.set_index("run_dir").join(pm, how="inner"), parse


def fig_pm_distributions(root, conf, quant, out):
    import textwrap
    path = root / quant / "analyzed" / "classified_bullets.csv"
    if not path.exists():
        print("classified_bullets.csv not found; skipping fig7")
        return
    d, parse = load_pm(root, quant)
    print("\nclassifier parse_status by condition (valid bullets):")
    print(pd.crosstab(parse["condition"], parse["parse_status"]).to_string())
    f2 = pd.read_csv(conf / f"family2_{quant}.csv").set_index("category")
    sig = as_bool(f2["significant"])
    rng = np.random.default_rng(0)
    fig, axes = plt.subplots(4, 4, figsize=(14, 13), sharey=True)
    for ax, cat in zip(axes.ravel(), CATEGORIES):
        for k, c in enumerate(CONDS):
            v = d.loc[d["condition"] == c, cat].values
            ax.scatter(k + rng.uniform(-0.28, 0.28, len(v)), v, s=9, alpha=0.35, color=COLORS[c], linewidths=0)
            ax.hlines(np.median(v), k - 0.35, k + 0.35, color="black", lw=2)
            ax.scatter([k], [v.mean()], marker="D", s=34, color="white", edgecolor="black", zorder=3)
        ax.set_xticks(range(3))
        ax.set_xticklabels(CONDS)
        ax.set_ylim(-0.2, 5.7)
        ax.set_title(textwrap.fill(cat, 28) + ("  *" if sig.get(cat, False) else ""), fontsize=9)
        ax.grid(axis="y", alpha=0.3)
    for ax in axes[:, 0]:
        ax.set_ylabel("Priority mass")
    n = d["condition"].value_counts().min()
    fig.suptitle(f"Per-run priority mass by condition, {ql(quant)} (n = {n} complete triplets). "
                 "Black bar = median, diamond = mean, * = Friedman significant after Holm.\n"
                 "Values are zero-heavy and discrete (max 5.5), so points are shown rather than densities.",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    save(fig, out, "fig7_pm_distributions")


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default="~/llm-research/results/qwen3-14b")
    ap.add_argument("--confirmatory-quant", default="q4_k_m")
    ap.add_argument("--quants", nargs="+", default=["q4_k_m", "q5_0", "q5_k_m", "q6_k", "q8_0"])
    ap.add_argument("--out")
    a = ap.parse_args()
    root = Path(a.results).expanduser()
    out = Path(a.out).expanduser() if a.out else root / "figures"
    out.mkdir(parents=True, exist_ok=True)
    conf, q = root / "confirmatory", a.confirmatory_quant
    fig_occurrence(conf, q, out)
    fig_effects(conf, q, out)
    fig_replication(conf, a.quants, q, out)
    fig_priority(conf, q, out)
    gold = root / q / "reliability" / "gold"
    if (gold / "gold_confusion.csv").exists():
        fig_confusion(gold / "gold_confusion.csv", gold / "gold_summary.json", out, "fig5a_gold_confusion",
                      "Classifier label", "Human gold label", 0.70,
                      "Classifier vs human gold coding (rows: classifier, columns: human)")
    sc = root / q / "reliability" / "sample"
    if (sc / "self_consistency_confusion.csv").exists():
        fig_confusion(sc / "self_consistency_confusion.csv", sc / "self_consistency_summary.json", out,
                      "fig5b_self_consistency", "Pass 1 label", "Pass 2 label", 0.80,
                      "Classifier self-consistency (pass 1 vs pass 2, shuffled category order)")
    fig_length(root, a.quants, out)
    fig_pm_distributions(root, conf, q, out)
    meta = json.loads((conf / "analysis_meta.json").read_text())
    print("\nunparsed classifier outputs coded Other/unclear:",
          {k: v["unparsed_as_other"] for k, v in meta["quantizations"].items()})


if __name__ == "__main__":
    main()
