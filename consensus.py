"""
consensus.py — Baseline and Hybrid Consensus Engines
======================================================
Both engines produce valid PoW blocks on the same Blockchain.
The *only* difference is difficulty selection:

  • Baseline:  fixed difficulty for every transaction batch.
  • Hybrid:    difficulty adapts per-block based on the highest-priority
               transaction type in the batch.

This design keeps blockchain integrity identical while letting us
measure whether adaptive difficulty reduces latency / cost.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List

from blockchain import Block, Blockchain, Transaction


# ──────────────────────────────────────────────
# Mining metrics returned by every mine() call
# ──────────────────────────────────────────────
@dataclass
class MineResult:
    block: Block
    hash_attempts: int
    cpu_time: float          # seconds
    mine_start: float        # perf_counter
    mine_end: float          # perf_counter


def _mine_block(block: Block) -> MineResult:
    """Generic PoW miner — works for any difficulty already set on *block*."""
    start = time.perf_counter()
    attempts = 0
    while True:
        h = block.compute_hash()
        attempts += 1
        if block.meets_difficulty(h):
            break
        block.nonce += 1
    end = time.perf_counter()

    block.hash_attempts = attempts
    block.cpu_time = end - start
    block.mine_start = start
    block.mine_end = end
    return MineResult(
        block=block,
        hash_attempts=attempts,
        cpu_time=end - start,
        mine_start=start,
        mine_end=end,
    )


# ──────────────────────────────────────────────
# Baseline consensus — uniform difficulty
# ──────────────────────────────────────────────
class BaselineConsensus:
    """Every block is mined at the *same* fixed difficulty regardless of
    what transactions it contains.

    Parameters:
        difficulty: Number of leading hex-zero characters required.
    """

    def __init__(self, difficulty: int = 4) -> None:
        self.difficulty = difficulty

    def mine(
        self,
        chain: Blockchain,
        transactions: List[Transaction],
    ) -> MineResult:
        block = Block(
            index=len(chain),
            transactions=transactions,
            previous_hash=chain.last_block.compute_hash(),
            difficulty=self.difficulty,
        )
        return _mine_block(block)


# ──────────────────────────────────────────────
# Hybrid consensus — adaptive difficulty
# ──────────────────────────────────────────────
class HybridConsensus:
    """Selects difficulty per-block based on the transaction types it contains.

    If *any* transaction in the batch is ``"strong"`` the block uses
    ``strong_difficulty``; otherwise it uses ``light_difficulty``.

    This mirrors a real-world scenario where high-value / smart-contract
    transactions warrant more security while micro-payments can tolerate
    lighter consensus.

    Parameters:
        light_difficulty:  Difficulty for lightweight-only blocks.
        strong_difficulty: Difficulty for blocks containing ≥1 strong tx.
    """

    def __init__(
        self,
        light_difficulty: int = 2,
        strong_difficulty: int = 4,
    ) -> None:
        self.light_difficulty = light_difficulty
        self.strong_difficulty = strong_difficulty

    def _select_difficulty(self, transactions: List[Transaction]) -> int:
        for tx in transactions:
            if tx.tx_type == "strong":
                return self.strong_difficulty
        return self.light_difficulty

    def mine(
        self,
        chain: Blockchain,
        transactions: List[Transaction],
    ) -> MineResult:
        difficulty = self._select_difficulty(transactions)
        block = Block(
            index=len(chain),
            transactions=transactions,
            previous_hash=chain.last_block.compute_hash(),
            difficulty=difficulty,
        )
        return _mine_block(block)


# ──────────────────────────────────────────────
# Machine Learning Adaptive Consensus
# ──────────────────────────────────────────────
class MLAdaptiveConsensus:
    """Intelligent consensus engine powered by ConsensusMLEngine.

    Replaces static thresholds with multi-feature telemetry evaluation,
    dynamically scaling difficulty (1 to 3) while actively preventing
    structuring and smurfing attacks.
    """

    def __init__(self) -> None:
        from ml_engine import ml_engine
        self.ml_engine = ml_engine

    def mine(
        self,
        chain: Blockchain,
        transactions: List[Transaction],
    ) -> MineResult:
        difficulty, reason, _ = self.ml_engine.evaluate_batch(transactions)
        block = Block(
            index=len(chain),
            transactions=transactions,
            previous_hash=chain.last_block.compute_hash(),
            difficulty=difficulty,
        )
        block.ml_reason = reason
        return _mine_block(block)

