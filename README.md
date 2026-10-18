# A Lightweight Hybrid Consensus Mechanism for Efficient Blockchain Transactions

> **Course**: Cryptocurrency and Technology  
> **Type**: University Course Project

## Overview

This project experimentally evaluates whether **adapting the consensus process to each transaction's requirements** reduces transaction latency and computational cost compared with applying one **uniform consensus process** to every transaction.

### Key Insight

Not every blockchain transaction needs the same level of computational security. A micropayment of ₹10 doesn't warrant the same mining effort as a ₹10,00,000 smart-contract settlement. The **Hybrid Consensus** engine classifies transactions as *lightweight* or *strong* and selects proof-of-work difficulty accordingly, while preserving full blockchain integrity.

## Architecture

```
┌─────────────────────────────────────────────┐
│                  main.py                     │
│         CLI entry point & orchestrator       │
├─────────────────────────────────────────────┤
│               experiment.py                  │
│   Generates txs, drives engines, collects    │
│   metrics (latency, cost, throughput)        │
├──────────────────┬──────────────────────────┤
│  consensus.py    │     blockchain.py         │
│  ┌────────────┐  │  ┌───────────────────┐   │
│  │ Baseline   │  │  │ Transaction       │   │
│  │ (uniform   │  │  │ Block             │   │
│  │  PoW diff) │  │  │ Blockchain        │   │
│  ├────────────┤  │  │  · verify_chain() │   │
│  │ Hybrid     │  │  └───────────────────┘   │
│  │ (adaptive  │  │                           │
│  │  PoW diff) │  │                           │
│  └────────────┘  │                           │
├──────────────────┴──────────────────────────┤
│              visualize.py                    │
│   CSV / Markdown tables + Matplotlib charts  │
└─────────────────────────────────────────────┘
```

## How It Works

| Engine | Difficulty Selection | Integrity |
|--------|---------------------|-----------|
| **Baseline** | Fixed difficulty (e.g. 4 leading zeros) for *every* block | Full PoW + hash-chain |
| **Proposed (Hybrid)** | `light_difficulty` (e.g. 2) for lightweight-only blocks; `strong_difficulty` (e.g. 4) for blocks with ≥1 strong tx | Full PoW + hash-chain |

Both engines produce valid proof-of-work blocks on the **same** `Blockchain` class with the **same** `verify_chain()` check. Only the computational effort differs.

## Quick Start

```bash
# 1. Install dependencies (Python 3.10+)
pip install -r requirements.txt

# 2. Quick smoke test (~1-2 minutes)
python main.py --quick

# 3. Full experiment suite (~5-15 minutes depending on hardware)
python main.py

# 4. Custom configuration
python main.py --loads 100 500 1000 5000 --mixes 0.9 0.7 0.5 --repeats 5
```

## Command-Line Options

| Flag | Default | Description |
|------|---------|-------------|
| `--quick` | — | Reduced loads for fast testing |
| `--loads` | 100 500 1000 5000 | Transaction counts to test |
| `--mixes` | 0.9 0.7 0.5 | Lightweight ratios |
| `--repeats` | 3 | Independent repetitions per config |
| `--block-size` | 10 | Transactions per block |
| `--baseline-diff` | 4 | Baseline PoW difficulty |
| `--hybrid-light-diff` | 2 | Hybrid lightweight difficulty |
| `--hybrid-strong-diff` | 4 | Hybrid strong difficulty |
| `--output-dir` | results | Output directory |

## Metrics Collected

For both Baseline and Proposed, each run records:

- **Average Transaction Latency**: Time from submission to block inclusion (seconds)
- **Confirmation Time**: Time spent mining the block that includes the transaction
- **Computational Cost**: Total SHA-256 hash attempts across all blocks
- **CPU Time**: Wall-clock seconds spent in the mining loop
- **Throughput**: Transactions processed per second
- **Chain Validity**: `verify_chain()` result (hash linkage + PoW)

All metrics are reported as **mean ± standard deviation** over multiple repetitions.

## Output Files

After running, the `results/` directory contains:

```
results/
├── results.csv                  # Machine-readable metrics table
├── results.md                   # Markdown-formatted results table
└── charts/
    ├── latency_vs_load.png      # Avg latency vs transaction count
    ├── cost_vs_load.png         # Hash attempts vs transaction count
    ├── throughput_vs_load.png   # Throughput vs transaction count
    ├── cpu_time_vs_load.png     # CPU time vs transaction count
    ├── confirmation_vs_load.png # Confirmation time vs transaction count
    └── mix_effect.png           # Side-by-side comparison across mixes
```

## Expected Results

With default settings (baseline difficulty=4, hybrid light=2/strong=4):

1. **Latency**: Hybrid reduces average latency significantly because ~90% of blocks use difficulty 2 instead of 4
2. **Hash Attempts**: Hybrid uses orders of magnitude fewer total hashes
3. **Throughput**: Hybrid achieves higher throughput (more tx/s)
4. **Chain Integrity**: Both approaches pass `verify_chain()` — the blockchain is equally valid

The improvement scales with the lightweight ratio: at 90% lightweight transactions, the hybrid advantage is largest; at 50/50 the advantage narrows.

## Requirements

- Python 3.10 or later
- `matplotlib` ≥ 3.7.0
- `tabulate` ≥ 0.9.0
- No GPU, no network, no external services — runs entirely on a normal laptop

## Project Structure

| File | Purpose |
|------|---------|
| `blockchain.py` | Core data structures: `Transaction`, `Block`, `Blockchain` with `verify_chain()` |
| `consensus.py` | `BaselineConsensus` (uniform PoW) and `HybridConsensus` (adaptive PoW) engines |
| `experiment.py` | Experiment runner: transaction generation, metrics collection, aggregation |
| `visualize.py` | CSV/Markdown table generation and Matplotlib chart production |
| `main.py` | CLI entry point that orchestrates everything |
| `requirements.txt` | Python dependencies |

## License

University coursework — free to use for educational purposes.
