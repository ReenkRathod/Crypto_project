"""
experiment.py — Experiment runner & metrics collection
=======================================================
Drives both consensus engines over configurable loads and mixes,
collects per-run metrics, and returns structured results for
visualization and reporting.
"""

from __future__ import annotations

import hashlib
import random
import statistics
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from blockchain import Blockchain, Transaction
from consensus import BaselineConsensus, HybridConsensus, MLAdaptiveConsensus, MineResult


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
@dataclass
class ExperimentConfig:
    """Parameters for a single experiment run."""
    num_transactions: int = 100
    lightweight_ratio: float = 0.9        # fraction that are lightweight
    block_size: int = 10                  # transactions per block
    baseline_difficulty: int = 3
    hybrid_light_difficulty: int = 1
    hybrid_strong_difficulty: int = 3
    repeats: int = 3                      # independent repetitions
    seed: int = 42


# ──────────────────────────────────────────────
# Per-run metrics
# ──────────────────────────────────────────────
@dataclass
class RunMetrics:
    """Aggregated metrics for one full run (all blocks mined)."""
    total_transactions: int = 0
    total_blocks: int = 0
    total_hash_attempts: int = 0
    total_cpu_time: float = 0.0
    avg_latency: float = 0.0             # seconds
    avg_confirmation: float = 0.0        # seconds
    throughput: float = 0.0              # tx/s
    chain_valid: bool = True
    per_block_attempts: List[int] = field(default_factory=list)
    per_block_cpu: List[float] = field(default_factory=list)
    per_tx_latency: List[float] = field(default_factory=list)


# ──────────────────────────────────────────────
# Transaction generator
# ──────────────────────────────────────────────
def generate_transactions(
    n: int,
    lightweight_ratio: float,
    rng: random.Random,
) -> List[Transaction]:
    """Create *n* synthetic transactions with the given lightweight/strong mix."""
    txs: List[Transaction] = []
    for i in range(n):
        tx_type = "lightweight" if rng.random() < lightweight_ratio else "strong"
        amount = round(rng.uniform(0.001, 100.0), 4) if tx_type == "lightweight" else round(rng.uniform(100.0, 10000.0), 4)
        tx = Transaction(
            tx_id=f"tx-{i:06d}-{uuid.uuid4().hex[:8]}",
            sender=hashlib.sha256(f"sender-{rng.randint(0, 999)}".encode()).hexdigest()[:40],
            receiver=hashlib.sha256(f"receiver-{rng.randint(0, 999)}".encode()).hexdigest()[:40],
            amount=amount,
            tx_type=tx_type,
            timestamp=time.time(),
            submit_time=time.perf_counter(),
        )
        txs.append(tx)
    return txs


# ──────────────────────────────────────────────
# Single-run executor
# ──────────────────────────────────────────────
def _run_once(
    transactions: List[Transaction],
    consensus_engine,
    block_size: int,
) -> RunMetrics:
    """Mine all *transactions* into a fresh blockchain and return metrics."""
    chain = Blockchain()
    metrics = RunMetrics(total_transactions=len(transactions))

    # Reset submit times so latency is measured from *this* run's start
    run_start = time.perf_counter()
    for tx in transactions:
        tx.submit_time = time.perf_counter()

    # Batch transactions into blocks
    batches: List[List[Transaction]] = []
    for i in range(0, len(transactions), block_size):
        batches.append(transactions[i : i + block_size])

    all_latencies: List[float] = []
    all_confirmations: List[float] = []

    for batch in batches:
        result: MineResult = consensus_engine.mine(chain, batch)
        ok = chain.add_block(result.block)
        if not ok:
            metrics.chain_valid = False

        metrics.total_blocks += 1
        metrics.total_hash_attempts += result.hash_attempts
        metrics.total_cpu_time += result.cpu_time
        metrics.per_block_attempts.append(result.hash_attempts)
        metrics.per_block_cpu.append(result.cpu_time)

        # Per-tx latency = time from submit to block-mine-end
        for tx in batch:
            latency = result.mine_end - tx.submit_time
            all_latencies.append(latency)
            all_confirmations.append(result.cpu_time)

    run_end = time.perf_counter()
    wall_time = run_end - run_start

    metrics.per_tx_latency = all_latencies
    metrics.avg_latency = statistics.mean(all_latencies) if all_latencies else 0.0
    metrics.avg_confirmation = statistics.mean(all_confirmations) if all_confirmations else 0.0
    metrics.throughput = len(transactions) / wall_time if wall_time > 0 else 0.0
    metrics.chain_valid = metrics.chain_valid and chain.verify_chain()

    return metrics


# ──────────────────────────────────────────────
# Experiment result container
# ──────────────────────────────────────────────
@dataclass
class ExperimentResult:
    """Aggregated statistics over multiple repetitions."""
    label: str                             # "Baseline" or "Proposed"
    num_transactions: int = 0
    lightweight_ratio: float = 0.0
    repeats: int = 0

    avg_latency_mean: float = 0.0
    avg_latency_std: float = 0.0

    avg_confirmation_mean: float = 0.0
    avg_confirmation_std: float = 0.0

    total_hash_attempts_mean: float = 0.0
    total_hash_attempts_std: float = 0.0

    total_cpu_time_mean: float = 0.0
    total_cpu_time_std: float = 0.0

    throughput_mean: float = 0.0
    throughput_std: float = 0.0

    chain_valid: bool = True


def _aggregate(label: str, runs: List[RunMetrics], n_tx: int, ratio: float) -> ExperimentResult:
    """Compute mean ± std from multiple RunMetrics."""
    res = ExperimentResult(
        label=label,
        num_transactions=n_tx,
        lightweight_ratio=ratio,
        repeats=len(runs),
    )
    lats = [r.avg_latency for r in runs]
    confs = [r.avg_confirmation for r in runs]
    hashes = [float(r.total_hash_attempts) for r in runs]
    cpus = [r.total_cpu_time for r in runs]
    tputs = [r.throughput for r in runs]

    res.avg_latency_mean = statistics.mean(lats)
    res.avg_latency_std = statistics.stdev(lats) if len(lats) > 1 else 0.0

    res.avg_confirmation_mean = statistics.mean(confs)
    res.avg_confirmation_std = statistics.stdev(confs) if len(confs) > 1 else 0.0

    res.total_hash_attempts_mean = statistics.mean(hashes)
    res.total_hash_attempts_std = statistics.stdev(hashes) if len(hashes) > 1 else 0.0

    res.total_cpu_time_mean = statistics.mean(cpus)
    res.total_cpu_time_std = statistics.stdev(cpus) if len(cpus) > 1 else 0.0

    res.throughput_mean = statistics.mean(tputs)
    res.throughput_std = statistics.stdev(tputs) if len(tputs) > 1 else 0.0

    res.chain_valid = all(r.chain_valid for r in runs)
    return res


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────
def run_experiment(cfg: ExperimentConfig) -> Tuple[ExperimentResult, ExperimentResult, ExperimentResult]:
    """Execute Baseline, Heuristic, and ML-Adaptive engines *cfg.repeats* times."""
    baseline_engine = BaselineConsensus(difficulty=cfg.baseline_difficulty)
    heuristic_engine = HybridConsensus(
        light_difficulty=cfg.hybrid_light_difficulty,
        strong_difficulty=cfg.hybrid_strong_difficulty,
    )
    ml_consensus_engine = MLAdaptiveConsensus()

    baseline_runs: List[RunMetrics] = []
    heuristic_runs: List[RunMetrics] = []
    ml_runs: List[RunMetrics] = []

    for rep in range(cfg.repeats):
        rng = random.Random(cfg.seed + rep)
        txs = generate_transactions(cfg.num_transactions, cfg.lightweight_ratio, rng)

        # Deep-copy transactions for each engine so submit_times are independent
        import copy
        txs_baseline = copy.deepcopy(txs)
        txs_heuristic = copy.deepcopy(txs)
        txs_ml = copy.deepcopy(txs)

        print(f"    Run {rep + 1}/{cfg.repeats}  "
              f"(n={cfg.num_transactions}, light={cfg.lightweight_ratio:.0%}) ... ",
              end="", flush=True)

        bm = _run_once(txs_baseline, baseline_engine, cfg.block_size)
        hm = _run_once(txs_heuristic, heuristic_engine, cfg.block_size)
        mm = _run_once(txs_ml, ml_consensus_engine, cfg.block_size)

        baseline_runs.append(bm)
        heuristic_runs.append(hm)
        ml_runs.append(mm)

        status_b = "OK" if bm.chain_valid else "FAIL"
        status_h = "OK" if hm.chain_valid else "FAIL"
        status_m = "OK" if mm.chain_valid else "FAIL"
        print(f"Base: {status_b} | Heuristic: {status_h} | ML: {status_m}")

    baseline_result = _aggregate("Baseline", baseline_runs, cfg.num_transactions, cfg.lightweight_ratio)
    heuristic_result = _aggregate("Heuristic", heuristic_runs, cfg.num_transactions, cfg.lightweight_ratio)
    ml_result = _aggregate("ML-Adaptive", ml_runs, cfg.num_transactions, cfg.lightweight_ratio)
    return baseline_result, heuristic_result, ml_result


def run_full_experiment_suite(
    loads: List[int] | None = None,
    mixes: List[float] | None = None,
    repeats: int = 3,
    baseline_difficulty: int = 3,
    hybrid_light_difficulty: int = 1,
    hybrid_strong_difficulty: int = 3,
    block_size: int = 10,
) -> List[Tuple[ExperimentConfig, ExperimentResult, ExperimentResult, ExperimentResult]]:
    """Run experiments across all load × mix combinations for all three engines.

    Returns a list of (config, baseline_res, heuristic_res, ml_res) tuples.
    """
    if loads is None:
        loads = [100, 500, 1000]
    if mixes is None:
        mixes = [0.9, 0.7, 0.5]

    results: List[Tuple[ExperimentConfig, ExperimentResult, ExperimentResult, ExperimentResult]] = []

    for n in loads:
        for ratio in mixes:
            cfg = ExperimentConfig(
                num_transactions=n,
                lightweight_ratio=ratio,
                block_size=block_size,
                baseline_difficulty=baseline_difficulty,
                hybrid_light_difficulty=hybrid_light_difficulty,
                hybrid_strong_difficulty=hybrid_strong_difficulty,
                repeats=repeats,
            )
            print(f"\n{'='*60}")
            print(f"  Experiment: {n} txs, {ratio:.0%} lightweight")
            print(f"{'='*60}")
            b, h, m = run_experiment(cfg)
            results.append((cfg, b, h, m))

    return results


def run_adversarial_security_benchmark() -> Dict[str, any]:
    """Tests resilience against Structuring / Smurfing Evasion Attacks.

    Adversary Model:
      An attacker sends a rapid burst of transactions priced just below the 
      static threshold (INR 95.00 each) to force the consensus engine to apply
      Difficulty 1, enabling a subsequent low-cost chain reorganization.

    Evaluates:
      - Heuristic engine detection rate (fails: stays at Diff 1)
      - ML-Adaptive engine detection rate (succeeds: detects velocity anomaly and elevates to Diff 3)
    """
    heuristic_engine = HybridConsensus(light_difficulty=1, strong_difficulty=3)
    ml_engine = MLAdaptiveConsensus()

    # Generate 10 burst transactions from the same sender
    attack_txs: List[Transaction] = []
    now = time.time()
    for i in range(10):
        tx = Transaction(
            tx_id=f"attack-tx-{i:03d}",
            sender="0xMaliciousAttacker_X",
            receiver="0xMuleVault",
            amount=95.0,  # Just below 100 threshold
            tx_type="lightweight",
            timestamp=now + (i * 0.5), # Rapid burst
            submit_time=time.perf_counter()
        )
        attack_txs.append(tx)

    chain_h = Blockchain()
    chain_m = Blockchain()

    res_h = heuristic_engine.mine(chain_h, attack_txs)
    res_m = ml_engine.mine(chain_m, attack_txs)

    heuristic_intercepted = res_h.block.difficulty >= 3
    ml_intercepted = res_m.block.difficulty >= 3

    return {
        "attack_type": "Smurfing / Structuring Micro-Burst Evasion",
        "attack_transactions": len(attack_txs),
        "target_amount_per_tx": 95.0,
        "heuristic_difficulty_assigned": res_h.block.difficulty,
        "heuristic_intercepted": heuristic_intercepted,
        "ml_difficulty_assigned": res_m.block.difficulty,
        "ml_intercepted": ml_intercepted,
        "ml_reasoning": getattr(res_m.block, "ml_reason", "High risk detected"),
    }

