"""
visualize.py — Result tables (CSV / Markdown) and Matplotlib charts
====================================================================
Produces publication-ready output from experiment results.
"""

from __future__ import annotations

import csv
import os
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")                   # headless backend — no GUI needed
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from experiment import ExperimentConfig, ExperimentResult


# ──────────────────────────────────────────────
# Table helpers
# ──────────────────────────────────────────────
_TABLE_HEADERS = [
    "Transactions",
    "Light %",
    "Metric",
    "Baseline (mean ± std)",
    "Heuristic (mean ± std)",
    "ML-Adaptive (mean ± std)",
    "ML vs Baseline %",
]


def _fmt(mean: float, std: float, precision: int = 4) -> str:
    return f"{mean:.{precision}f} ± {std:.{precision}f}"


def _pct(baseline: float, proposed: float, higher_is_better: bool = False) -> str:
    if baseline == 0:
        return "N/A"
    if higher_is_better:
        change = (proposed - baseline) / baseline * 100
    else:
        change = (baseline - proposed) / baseline * 100
    return f"{change:+.1f}%"


def _build_rows(
    results: List[Tuple[ExperimentConfig, ExperimentResult, ExperimentResult, ExperimentResult]],
) -> List[List[str]]:
    rows: List[List[str]] = []
    for cfg, b, h, m in results:
        n = str(cfg.num_transactions)
        light = f"{cfg.lightweight_ratio:.0%}"
        rows.append([n, light, "Avg Latency (s)", _fmt(b.avg_latency_mean, b.avg_latency_std), _fmt(h.avg_latency_mean, h.avg_latency_std), _fmt(m.avg_latency_mean, m.avg_latency_std), _pct(b.avg_latency_mean, m.avg_latency_mean)])
        rows.append([n, light, "Confirmation (s)", _fmt(b.avg_confirmation_mean, b.avg_confirmation_std), _fmt(h.avg_confirmation_mean, h.avg_confirmation_std), _fmt(m.avg_confirmation_mean, m.avg_confirmation_std), _pct(b.avg_confirmation_mean, m.avg_confirmation_mean)])
        rows.append([n, light, "Hash Attempts", _fmt(b.total_hash_attempts_mean, b.total_hash_attempts_std, 0), _fmt(h.total_hash_attempts_mean, h.total_hash_attempts_std, 0), _fmt(m.total_hash_attempts_mean, m.total_hash_attempts_std, 0), _pct(b.total_hash_attempts_mean, m.total_hash_attempts_mean)])
        rows.append([n, light, "CPU Time (s)", _fmt(b.total_cpu_time_mean, b.total_cpu_time_std), _fmt(h.total_cpu_time_mean, h.total_cpu_time_std), _fmt(m.total_cpu_time_mean, m.total_cpu_time_std), _pct(b.total_cpu_time_mean, m.total_cpu_time_mean)])
        rows.append([n, light, "Throughput (tx/s)", _fmt(b.throughput_mean, b.throughput_std, 1), _fmt(h.throughput_mean, h.throughput_std, 1), _fmt(m.throughput_mean, m.throughput_std, 1), _pct(b.throughput_mean, m.throughput_mean, higher_is_better=True)])
        rows.append([n, light, "Chain Valid", str(b.chain_valid), str(h.chain_valid), str(m.chain_valid), "—"])
    return rows


def save_csv(
    results: List[Tuple[ExperimentConfig, ExperimentResult, ExperimentResult, ExperimentResult]],
    path: str = "results.csv",
) -> str:
    rows = _build_rows(results)
    target_path = path
    try:
        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(_TABLE_HEADERS)
            writer.writerows(rows)
    except PermissionError:
        # File is likely open/locked in Excel or another program
        base, ext = os.path.splitext(path)
        target_path = f"{base}_latest{ext}"
        print(f"  [WARN] '{path}' is locked by another program (e.g. Excel). Saving to '{target_path}' instead.")
        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(_TABLE_HEADERS)
            writer.writerows(rows)
    print(f"  [OK] CSV saved to {target_path}")
    return target_path


def save_markdown(
    results: List[Tuple[ExperimentConfig, ExperimentResult, ExperimentResult, ExperimentResult]],
    path: str = "results.md",
) -> str:
    rows = _build_rows(results)
    col_widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(_TABLE_HEADERS)]

    lines: List[str] = []
    lines.append("# Experiment Results\n")
    lines.append("## Comparison: Baseline vs Static Heuristic vs ML-Adaptive Consensus\n")

    # Header
    header = "| " + " | ".join(h.ljust(w) for h, w in zip(_TABLE_HEADERS, col_widths)) + " |"
    sep = "| " + " | ".join("-" * w for w in col_widths) + " |"
    lines.append(header)
    lines.append(sep)

    for row in rows:
        line = "| " + " | ".join(cell.ljust(w) for cell, w in zip(row, col_widths)) + " |"
        lines.append(line)

    lines.append("")

    target_path = path
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except PermissionError:
        base, ext = os.path.splitext(path)
        target_path = f"{base}_latest{ext}"
        print(f"  [WARN] '{path}' is locked by another program. Saving to '{target_path}' instead.")
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    print(f"  [OK] Markdown saved to {target_path}")
    return target_path


# ──────────────────────────────────────────────
# Chart helpers
# ──────────────────────────────────────────────
# Beautiful color palette
_C_BASELINE  = "#E74C3C"       # warm red (standard PoW)
_C_HEURISTIC = "#F39C12"       # amber / orange (static threshold)
_C_ML        = "#00D2D3"       # cyan / teal (ML-Adaptive)
_BG_COLOR    = "#1A1A2E"       # dark navy
_GRID_COLOR  = "#2D2D44"
_TEXT_COLOR  = "#E8E8E8"


def _style_ax(ax: plt.Axes, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_facecolor(_BG_COLOR)
    ax.set_title(title, fontsize=13, fontweight="bold", color=_TEXT_COLOR, pad=12)
    ax.set_xlabel(xlabel, fontsize=11, color=_TEXT_COLOR)
    ax.set_ylabel(ylabel, fontsize=11, color=_TEXT_COLOR)
    ax.tick_params(colors=_TEXT_COLOR, labelsize=9)
    ax.grid(True, color=_GRID_COLOR, linestyle="--", alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(fontsize=9, facecolor="#16213E", edgecolor=_GRID_COLOR, labelcolor=_TEXT_COLOR)


def _filter_by_mix(
    results: List[Tuple[ExperimentConfig, ExperimentResult, ExperimentResult, ExperimentResult]],
    ratio: float,
) -> List[Tuple[ExperimentConfig, ExperimentResult, ExperimentResult, ExperimentResult]]:
    return [r for r in results if abs(r[0].lightweight_ratio - ratio) < 0.01]


def _filter_by_load(
    results: List[Tuple[ExperimentConfig, ExperimentResult, ExperimentResult, ExperimentResult]],
    load: int,
) -> List[Tuple[ExperimentConfig, ExperimentResult, ExperimentResult, ExperimentResult]]:
    return [r for r in results if r[0].num_transactions == load]


def generate_charts(
    results: List[Tuple[ExperimentConfig, ExperimentResult, ExperimentResult, ExperimentResult]],
    output_dir: str = "charts",
) -> List[str]:
    """Generate publication-ready 3-engine comparison charts and feature importance chart."""
    os.makedirs(output_dir, exist_ok=True)
    saved: List[str] = []

    # Determine unique loads and mixes
    loads = sorted({r[0].num_transactions for r in results})
    mixes = sorted({r[0].lightweight_ratio for r in results}, reverse=True)

    default_mix = mixes[0] if mixes else 0.9
    default_load = loads[-1] if loads else 1000

    subset = _filter_by_mix(results, default_mix)
    xs = [r[0].num_transactions for r in subset]

    # ── 1. Latency vs Load ────────────────────
    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.set_facecolor(_BG_COLOR)
    b_lat = [r[1].avg_latency_mean for r in subset]
    b_lat_err = [r[1].avg_latency_std for r in subset]
    h_lat = [r[2].avg_latency_mean for r in subset]
    h_lat_err = [r[2].avg_latency_std for r in subset]
    m_lat = [r[3].avg_latency_mean for r in subset]
    m_lat_err = [r[3].avg_latency_std for r in subset]
    ax.errorbar(xs, b_lat, yerr=b_lat_err, marker="o", color=_C_BASELINE, linewidth=2, capsize=4, label="Baseline (Diff 3)")
    ax.errorbar(xs, h_lat, yerr=h_lat_err, marker="^", color=_C_HEURISTIC, linewidth=2, linestyle="--", capsize=4, label="Static Heuristic")
    ax.errorbar(xs, m_lat, yerr=m_lat_err, marker="s", color=_C_ML, linewidth=2, capsize=4, label="ML-Adaptive (Proposed)")
    _style_ax(ax, f"Average Transaction Latency vs Load  (mix={default_mix:.0%} light)", "Number of Transactions", "Avg Latency (s)")
    path = os.path.join(output_dir, "latency_vs_load.png")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    saved.append(path)
    print(f"  [OK] Chart: {path}")

    # ── 2. Computational Cost vs Load ─────────
    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.set_facecolor(_BG_COLOR)
    b_hash = [r[1].total_hash_attempts_mean for r in subset]
    b_hash_err = [r[1].total_hash_attempts_std for r in subset]
    h_hash = [r[2].total_hash_attempts_mean for r in subset]
    h_hash_err = [r[2].total_hash_attempts_std for r in subset]
    m_hash = [r[3].total_hash_attempts_mean for r in subset]
    m_hash_err = [r[3].total_hash_attempts_std for r in subset]
    ax.errorbar(xs, b_hash, yerr=b_hash_err, marker="o", color=_C_BASELINE, linewidth=2, capsize=4, label="Baseline (Diff 3)")
    ax.errorbar(xs, h_hash, yerr=h_hash_err, marker="^", color=_C_HEURISTIC, linewidth=2, linestyle="--", capsize=4, label="Static Heuristic")
    ax.errorbar(xs, m_hash, yerr=m_hash_err, marker="s", color=_C_ML, linewidth=2, capsize=4, label="ML-Adaptive (Proposed)")
    _style_ax(ax, f"Computational Cost vs Load  (mix={default_mix:.0%} light)", "Number of Transactions", "Total Hash Attempts")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    path = os.path.join(output_dir, "cost_vs_load.png")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    saved.append(path)
    print(f"  [OK] Chart: {path}")

    # ── 3. Throughput vs Load ─────────────────
    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.set_facecolor(_BG_COLOR)
    b_tp = [r[1].throughput_mean for r in subset]
    b_tp_err = [r[1].throughput_std for r in subset]
    h_tp = [r[2].throughput_mean for r in subset]
    h_tp_err = [r[2].throughput_std for r in subset]
    m_tp = [r[3].throughput_mean for r in subset]
    m_tp_err = [r[3].throughput_std for r in subset]
    ax.errorbar(xs, b_tp, yerr=b_tp_err, marker="o", color=_C_BASELINE, linewidth=2, capsize=4, label="Baseline (Diff 3)")
    ax.errorbar(xs, h_tp, yerr=h_tp_err, marker="^", color=_C_HEURISTIC, linewidth=2, linestyle="--", capsize=4, label="Static Heuristic")
    ax.errorbar(xs, m_tp, yerr=m_tp_err, marker="s", color=_C_ML, linewidth=2, capsize=4, label="ML-Adaptive (Proposed)")
    _style_ax(ax, f"Throughput vs Load  (mix={default_mix:.0%} light)", "Number of Transactions", "Throughput (tx/s)")
    path = os.path.join(output_dir, "throughput_vs_load.png")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    saved.append(path)
    print(f"  [OK] Chart: {path}")

    # ── 4. Effect of Transaction Mix ──────────
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    fig.set_facecolor(_BG_COLOR)
    fig.suptitle(f"Effect of Transaction Mix  (load={default_load} txs)", fontsize=15, fontweight="bold", color=_TEXT_COLOR, y=1.02)

    mix_subset = _filter_by_load(results, default_load)
    mix_labels = [f"{r[0].lightweight_ratio:.0%}" for r in mix_subset]
    x_pos = range(len(mix_labels))
    w = 0.25

    # 4a — Latency
    ax = axes[0]
    b_vals = [r[1].avg_latency_mean for r in mix_subset]
    h_vals = [r[2].avg_latency_mean for r in mix_subset]
    m_vals = [r[3].avg_latency_mean for r in mix_subset]
    b_errs = [r[1].avg_latency_std for r in mix_subset]
    h_errs = [r[2].avg_latency_std for r in mix_subset]
    m_errs = [r[3].avg_latency_std for r in mix_subset]
    ax.bar([p - w for p in x_pos], b_vals, w, yerr=b_errs, color=_C_BASELINE, capsize=3, label="Baseline", alpha=0.9)
    ax.bar([p for p in x_pos], h_vals, w, yerr=h_errs, color=_C_HEURISTIC, capsize=3, label="Heuristic", alpha=0.9)
    ax.bar([p + w for p in x_pos], m_vals, w, yerr=m_errs, color=_C_ML, capsize=3, label="ML-Adaptive", alpha=0.9)
    ax.set_xticks(list(x_pos))
    ax.set_xticklabels(mix_labels)
    _style_ax(ax, "Avg Latency", "Lightweight Ratio", "Seconds")

    # 4b — Hash Attempts
    ax = axes[1]
    b_vals = [r[1].total_hash_attempts_mean for r in mix_subset]
    h_vals = [r[2].total_hash_attempts_mean for r in mix_subset]
    m_vals = [r[3].total_hash_attempts_mean for r in mix_subset]
    b_errs = [r[1].total_hash_attempts_std for r in mix_subset]
    h_errs = [r[2].total_hash_attempts_std for r in mix_subset]
    m_errs = [r[3].total_hash_attempts_std for r in mix_subset]
    ax.bar([p - w for p in x_pos], b_vals, w, yerr=b_errs, color=_C_BASELINE, capsize=3, label="Baseline", alpha=0.9)
    ax.bar([p for p in x_pos], h_vals, w, yerr=h_errs, color=_C_HEURISTIC, capsize=3, label="Heuristic", alpha=0.9)
    ax.bar([p + w for p in x_pos], m_vals, w, yerr=m_errs, color=_C_ML, capsize=3, label="ML-Adaptive", alpha=0.9)
    ax.set_xticks(list(x_pos))
    ax.set_xticklabels(mix_labels)
    _style_ax(ax, "Hash Attempts", "Lightweight Ratio", "Count")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # 4c — Throughput
    ax = axes[2]
    b_vals = [r[1].throughput_mean for r in mix_subset]
    h_vals = [r[2].throughput_mean for r in mix_subset]
    m_vals = [r[3].throughput_mean for r in mix_subset]
    b_errs = [r[1].throughput_std for r in mix_subset]
    h_errs = [r[2].throughput_std for r in mix_subset]
    m_errs = [r[3].throughput_std for r in mix_subset]
    ax.bar([p - w for p in x_pos], b_vals, w, yerr=b_errs, color=_C_BASELINE, capsize=3, label="Baseline", alpha=0.9)
    ax.bar([p for p in x_pos], h_vals, w, yerr=h_errs, color=_C_HEURISTIC, capsize=3, label="Heuristic", alpha=0.9)
    ax.bar([p + w for p in x_pos], m_vals, w, yerr=m_errs, color=_C_ML, capsize=3, label="ML-Adaptive", alpha=0.9)
    ax.set_xticks(list(x_pos))
    ax.set_xticklabels(mix_labels)
    _style_ax(ax, "Throughput", "Lightweight Ratio", "tx/s")

    path = os.path.join(output_dir, "mix_effect.png")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    saved.append(path)
    print(f"  [OK] Chart: {path}")

    # ── 5. CPU Time vs Load ───────────────────
    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.set_facecolor(_BG_COLOR)
    b_cpu = [r[1].total_cpu_time_mean for r in subset]
    b_cpu_err = [r[1].total_cpu_time_std for r in subset]
    h_cpu = [r[2].total_cpu_time_mean for r in subset]
    h_cpu_err = [r[2].total_cpu_time_std for r in subset]
    m_cpu = [r[3].total_cpu_time_mean for r in subset]
    m_cpu_err = [r[3].total_cpu_time_std for r in subset]
    ax.errorbar(xs, b_cpu, yerr=b_cpu_err, marker="o", color=_C_BASELINE, linewidth=2, capsize=4, label="Baseline (Diff 3)")
    ax.errorbar(xs, h_cpu, yerr=h_cpu_err, marker="^", color=_C_HEURISTIC, linewidth=2, linestyle="--", capsize=4, label="Static Heuristic")
    ax.errorbar(xs, m_cpu, yerr=m_cpu_err, marker="s", color=_C_ML, linewidth=2, capsize=4, label="ML-Adaptive (Proposed)")
    _style_ax(ax, f"CPU Time vs Load  (mix={default_mix:.0%} light)", "Number of Transactions", "Total CPU Time (s)")
    path = os.path.join(output_dir, "cpu_time_vs_load.png")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    saved.append(path)
    print(f"  [OK] Chart: {path}")

    # ── 6. Confirmation Time vs Load ──────────
    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.set_facecolor(_BG_COLOR)
    b_conf = [r[1].avg_confirmation_mean for r in subset]
    b_conf_err = [r[1].avg_confirmation_std for r in subset]
    h_conf = [r[2].avg_confirmation_mean for r in subset]
    h_conf_err = [r[2].avg_confirmation_std for r in subset]
    m_conf = [r[3].avg_confirmation_mean for r in subset]
    m_conf_err = [r[3].avg_confirmation_std for r in subset]
    ax.errorbar(xs, b_conf, yerr=b_conf_err, marker="o", color=_C_BASELINE, linewidth=2, capsize=4, label="Baseline (Diff 3)")
    ax.errorbar(xs, h_conf, yerr=h_conf_err, marker="^", color=_C_HEURISTIC, linewidth=2, linestyle="--", capsize=4, label="Static Heuristic")
    ax.errorbar(xs, m_conf, yerr=m_conf_err, marker="s", color=_C_ML, linewidth=2, capsize=4, label="ML-Adaptive (Proposed)")
    _style_ax(ax, f"Confirmation Time vs Load  (mix={default_mix:.0%} light)", "Number of Transactions", "Avg Confirmation Time (s)")
    path = os.path.join(output_dir, "confirmation_vs_load.png")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    saved.append(path)
    print(f"  [OK] Chart: {path}")

    # ── 7. ML Feature Importance ──────────────
    try:
        from ml_engine import ml_engine
        fig, ax = plt.subplots(figsize=(8, 4.5))
        fig.set_facecolor(_BG_COLOR)
        feature_names = ["Amount", "Velocity (Burst)", "Fee Ratio", "Structuring Flag"]
        importances = ml_engine.model.feature_importances_
        colors = ["#4A90E2", "#FF6B6B", "#F39C12", "#00D2D3"]
        bars = ax.barh(feature_names, importances, color=colors, height=0.55)
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 0.01, bar.get_y() + bar.get_height()/2, f"{width:.1%}",
                    va='center', ha='left', color=_TEXT_COLOR, fontsize=10, fontweight="bold")
        _style_ax(ax, "Random Forest Feature Importance in Adaptive Consensus", "Relative Importance", "Telemetry Feature")
        ax.set_xlim(0, max(importances) * 1.25)
        path = os.path.join(output_dir, "ml_feature_importance.png")
        fig.tight_layout()
        fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
        saved.append(path)
        print(f"  [OK] Chart: {path}")
    except Exception as e:
        print(f"  [WARN] Could not generate feature importance chart: {e}")

    return saved
