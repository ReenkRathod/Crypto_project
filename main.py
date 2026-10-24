#!/usr/bin/env python3
"""
main.py -- Entry point for the Hybrid Consensus Experiment
============================================================
A Lightweight Hybrid Consensus Mechanism for Efficient Blockchain Transactions

Usage:
    python main.py               # Full experiment suite (default settings)
    python main.py --quick       # Quick smoke test (smaller loads)

Outputs:
    results/results.csv          CSV table with all metrics
    results/results.md           Markdown table
    results/charts/*.png         Matplotlib charts
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import time

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

from experiment import (
    ExperimentConfig,
    run_full_experiment_suite,
    run_adversarial_security_benchmark,
)
from visualize import generate_charts, save_csv, save_markdown


def print_banner() -> None:
    banner = """
    +==================================================================+
    |  Intelligent Adaptive Consensus Mechanism for High-Throughput     |
    |  Blockchain Networks using Explainable AI Telemetry               |
    |                                                                  |
    |  Course Project: BCSE328L Cryptocurrency Technologies (VIT)      |
    +==================================================================+
    """
    print(banner)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hybrid Consensus Blockchain Experiment"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a quick smoke test with smaller loads",
    )
    parser.add_argument(
        "--loads",
        type=int,
        nargs="+",
        default=None,
        help="Transaction loads to test (e.g. 100 500 1000 5000)",
    )
    parser.add_argument(
        "--mixes",
        type=float,
        nargs="+",
        default=None,
        help="Lightweight ratios to test (e.g. 0.9 0.7 0.5)",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Number of repetitions per configuration",
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=10,
        help="Transactions per block",
    )
    parser.add_argument(
        "--baseline-diff",
        type=int,
        default=3,
        help="Baseline PoW difficulty (leading hex zeros)",
    )
    parser.add_argument(
        "--hybrid-light-diff",
        type=int,
        default=1,
        help="Hybrid light PoW difficulty",
    )
    parser.add_argument(
        "--hybrid-strong-diff",
        type=int,
        default=3,
        help="Hybrid strong PoW difficulty",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Output directory for results",
    )
    args = parser.parse_args()

    print_banner()

    # Determine loads and mixes
    if args.quick:
        loads = [50, 100, 200]
        mixes = [0.9, 0.7, 0.5]
        repeats = 2
        print("  [QUICK] Quick mode: reduced loads for fast testing\n")
    else:
        loads = args.loads or [100, 500, 1000, 5000]
        mixes = args.mixes or [0.9, 0.7, 0.5]
        repeats = args.repeats

    print(f"  Configuration:")
    print(f"    Loads:             {loads}")
    print(f"    Mixes (light %):   {mixes}")
    print(f"    Repeats:           {repeats}")
    print(f"    Block size:        {args.block_size} tx/block")
    print(f"    Baseline diff:     {args.baseline_diff}")
    print(f"    Hybrid light diff: {args.hybrid_light_diff}")
    print(f"    Hybrid strong diff:{args.hybrid_strong_diff}")
    print()

    # Run experiments
    t0 = time.time()
    results = run_full_experiment_suite(
        loads=loads,
        mixes=mixes,
        repeats=repeats,
        baseline_difficulty=args.baseline_diff,
        hybrid_light_difficulty=args.hybrid_light_diff,
        hybrid_strong_difficulty=args.hybrid_strong_diff,
        block_size=args.block_size,
    )
    elapsed = time.time() - t0

    # Save outputs
    os.makedirs(args.output_dir, exist_ok=True)
    charts_dir = os.path.join(args.output_dir, "charts")

    print(f"\n{'='*60}")
    print("  Saving results...")
    print(f"{'='*60}")

    csv_path = save_csv(results, os.path.join(args.output_dir, "results.csv"))
    md_path = save_markdown(results, os.path.join(args.output_dir, "results.md"))
    chart_paths = generate_charts(results, charts_dir)

    # Print summary
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    print(f"  Total wall-clock time: {elapsed:.1f}s")
    print(f"  Experiments run:       {len(results)}")
    print(f"  Output files:")
    print(f"    {csv_path}")
    print(f"    {md_path}")
    for cp in chart_paths:
        print(f"    {cp}")

    # Chain verification summary
    print(f"\n  Chain Integrity Verification:")
    all_valid = True
    for cfg, b, h, m in results:
        status_b = "PASS" if b.chain_valid else "FAIL"
        status_h = "PASS" if h.chain_valid else "FAIL"
        status_m = "PASS" if m.chain_valid else "FAIL"
        print(f"    {cfg.num_transactions:>5} txs, {cfg.lightweight_ratio:.0%} light: "
              f"Baseline={status_b}  Heuristic={status_h}  ML-Adaptive={status_m}")
        if not b.chain_valid or not h.chain_valid or not m.chain_valid:
            all_valid = False

    if all_valid:
        print("\n  [OK] All chains verified successfully!")
    else:
        print("\n  [FAIL] Some chains failed verification!")
        sys.exit(1)

    # Quick comparison for the largest load
    largest = max(results, key=lambda r: r[0].num_transactions)
    cfg, b, h, m = largest
    lat_imp = ((b.avg_latency_mean - m.avg_latency_mean) / b.avg_latency_mean * 100) if b.avg_latency_mean > 0 else 0
    hash_imp = ((b.total_hash_attempts_mean - m.total_hash_attempts_mean) / b.total_hash_attempts_mean * 100) if b.total_hash_attempts_mean > 0 else 0
    tp_imp = ((m.throughput_mean - b.throughput_mean) / b.throughput_mean * 100) if b.throughput_mean > 0 else 0

    print(f"\n  Key findings at {cfg.num_transactions} txs, {cfg.lightweight_ratio:.0%} light:")
    print(f"    ML Latency reduction vs Baseline:   {lat_imp:+.1f}%")
    print(f"    ML Hash cost reduction vs Baseline: {hash_imp:+.1f}%")
    print(f"    ML Throughput improvement:          {tp_imp:+.1f}% ({b.throughput_mean:.1f} -> {m.throughput_mean:.1f} tx/s)")
    print()

    # Adversarial Security Benchmark
    print(f"{'='*60}")
    print("  ADVERSARIAL SECURITY & STRUCTURING RESILIENCE BENCHMARK")
    print(f"{'='*60}")
    adv_res = run_adversarial_security_benchmark()
    print(f"  Attack Scenario:             {adv_res['attack_type']}")
    print(f"  Burst Transactions Injected: {adv_res['attack_transactions']} x INR {adv_res['target_amount_per_tx']:.2f}")
    print(f"  Heuristic Defense Assigned:  Difficulty {adv_res['heuristic_difficulty_assigned']} (Vulnerable: {'INTERCEPTED' if adv_res['heuristic_intercepted'] else 'FAILED - Kept Diff 1'})")
    print(f"  ML-Adaptive Defense Assigned:Difficulty {adv_res['ml_difficulty_assigned']} (Secure: {'INTERCEPTED - Scaled to Diff 3' if adv_res['ml_intercepted'] else 'FAILED'})")
    print(f"  ML Explainable AI Reasoning: {adv_res['ml_reasoning']}")
    print()


if __name__ == "__main__":
    main()
