"""
blockchain.py — Core blockchain primitives
============================================
Implements Transaction, Block, and Blockchain classes.
Both the baseline and proposed consensus engines operate on the same
blockchain data-structures so the *integrity guarantees are identical*;
only the computational effort (difficulty) applied during mining differs.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import List, Optional


# ──────────────────────────────────────────────
# Transaction
# ──────────────────────────────────────────────
@dataclass
class Transaction:
    """A single transaction on the blockchain.

    Attributes:
        tx_id:       Unique identifier.
        sender:      Sender address (hex string).
        receiver:    Receiver address (hex string).
        amount:      Transfer amount.
        tx_type:     'lightweight' or 'strong' — used by the hybrid engine
                     to select consensus difficulty.
        timestamp:   Unix epoch when the transaction was created.
        submit_time: High-resolution timestamp for latency measurement.
    """
    tx_id: str
    sender: str
    receiver: str
    amount: float
    tx_type: str = "lightweight"          # "lightweight" | "strong"
    timestamp: float = field(default_factory=time.time)
    submit_time: float = field(default_factory=time.perf_counter)

    def to_dict(self) -> dict:
        return {
            "tx_id": self.tx_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "tx_type": self.tx_type,
            "timestamp": self.timestamp,
        }

    def hash(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode()
        ).hexdigest()


# ──────────────────────────────────────────────
# Block
# ──────────────────────────────────────────────
@dataclass
class Block:
    """A single block in the chain.

    Attributes:
        index:         Position in the chain (genesis = 0).
        transactions:  List of Transaction objects included in this block.
        previous_hash: SHA-256 hash of the preceding block.
        nonce:         Proof-of-Work nonce discovered during mining.
        timestamp:     Unix epoch when block was mined.
        difficulty:    Number of leading hex-zero characters required.
        hash_attempts: Number of hashes tried to find the nonce.
        cpu_time:      Wall-clock CPU seconds spent mining this block.
        mine_start:    perf_counter timestamp when mining began.
        mine_end:      perf_counter timestamp when mining ended.
    """
    index: int
    transactions: List[Transaction]
    previous_hash: str
    nonce: int = 0
    timestamp: float = field(default_factory=time.time)
    difficulty: int = 4                   # default; overridden by engine
    hash_attempts: int = 0
    cpu_time: float = 0.0
    mine_start: float = 0.0
    mine_end: float = 0.0

    # ── serialization helpers ────────────────
    def _header_string(self) -> str:
        """Deterministic string of the block header (excludes the hash)."""
        return json.dumps(
            {
                "index": self.index,
                "transactions": [tx.to_dict() for tx in self.transactions],
                "previous_hash": self.previous_hash,
                "nonce": self.nonce,
                "timestamp": self.timestamp,
                "difficulty": self.difficulty,
            },
            sort_keys=True,
        )

    def compute_hash(self) -> str:
        return hashlib.sha256(self._header_string().encode()).hexdigest()

    def meets_difficulty(self, hash_val: Optional[str] = None) -> bool:
        """Check whether *hash_val* (or the block's own hash) satisfies the
        difficulty target (leading zeros)."""
        h = hash_val or self.compute_hash()
        return h[: self.difficulty] == "0" * self.difficulty


# ──────────────────────────────────────────────
# Blockchain
# ──────────────────────────────────────────────
class Blockchain:
    """Append-only chain of blocks with full integrity verification."""

    def __init__(self) -> None:
        self.chain: List[Block] = []
        self._create_genesis()

    # ── genesis ──────────────────────────────
    def _create_genesis(self) -> None:
        genesis = Block(
            index=0,
            transactions=[],
            previous_hash="0" * 64,
            difficulty=1,               # trivial difficulty for genesis
        )
        genesis.nonce = 0
        genesis.timestamp = time.time()
        # Mine genesis (effectively instant with difficulty=1)
        while not genesis.meets_difficulty():
            genesis.nonce += 1
        self.chain.append(genesis)

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def add_block(self, block: Block) -> bool:
        """Append *block* if it links correctly and meets its own difficulty."""
        if block.previous_hash != self.last_block.compute_hash():
            return False
        if not block.meets_difficulty():
            return False
        self.chain.append(block)
        return True

    # ── integrity verification ───────────────
    def verify_chain(self) -> bool:
        """Walk the entire chain and verify hash linkage + PoW."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            # 1. Hash linkage
            if current.previous_hash != previous.compute_hash():
                return False
            # 2. PoW validity
            if not current.meets_difficulty():
                return False
        return True

    def __len__(self) -> int:
        return len(self.chain)
