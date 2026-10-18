"""
ml_engine.py — Machine Learning Risk Engine for Adaptive Blockchain Consensus
==============================================================================
Replaces hardcoded if/else heuristics with a trained Scikit-Learn ensemble model.
Evaluates multi-dimensional transaction telemetry:
  1. amount: Transaction value in INR
  2. velocity: Transaction burst rate / frequency from sender
  3. fee_ratio: Gas fee relative to transaction value
  4. structuring_risk: Statistical detection of split micro-transactions (smurfing attacks)

Outputs:
  • risk_level: "low" (Diff 1), "medium" (Diff 2), "high" (Diff 3)
  • risk_score: Float [0.0 - 1.0]
  • confidence: Model prediction probability [0.0 - 1.0]
  • suggested_difficulty: 1, 2, or 3
  • reasoning: Explainable AI insight for the consensus decision
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
from sklearn.ensemble import RandomForestClassifier


@dataclass
class MLRiskResult:
    risk_level: str               # "low" | "medium" | "high"
    risk_score: float             # 0.0 to 1.0
    confidence: float             # probability (e.g. 0.94)
    suggested_difficulty: int     # 1, 2, or 3
    reasoning: str                # Human-readable explanation


class ConsensusMLEngine:
    """Trained Random Forest Classifier for intelligent difficulty scaling."""

    def __init__(self, random_seed: int = 42):
        self.random_seed = random_seed
        self.model = RandomForestClassifier(
            n_estimators=50,
            max_depth=6,
            random_state=random_seed
        )
        self.is_trained = False
        self._sender_history: Dict[str, List[float]] = {}
        self._train_initial_model()

    def _generate_synthetic_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate realistic blockchain telemetry training data:
        - Class 0 (Low Risk / Micropayment): Small amounts, low velocity, normal fee.
        - Class 1 (Medium Risk / Standard): Moderate amounts, normal velocity.
        - Class 2 (High Risk / Settlement or Smurfing Attack): High amounts OR split micro-bursts.
        """
        rng = np.random.default_rng(self.random_seed)
        n_samples = 1200

        X = []
        y = []

        # 1. Low Risk (400 samples): Legitimate micropayments (Chai, bus ticket, etc.)
        for _ in range(400):
            amt = rng.uniform(1.0, 150.0)
            vel = rng.uniform(0.1, 1.5)           # tx/min
            fee_r = rng.uniform(0.01, 0.05)       # normal fee ratio
            structuring = rng.uniform(0.0, 0.15)  # low structuring flag
            X.append([amt, vel, fee_r, structuring])
            y.append(0)  # Low -> Diff 1

        # 2. Medium Risk (400 samples): Everyday retail & peer-to-peer transfers
        for _ in range(400):
            amt = rng.uniform(150.0, 3000.0)
            vel = rng.uniform(0.5, 3.0)
            fee_r = rng.uniform(0.005, 0.03)
            structuring = rng.uniform(0.0, 0.3)
            X.append([amt, vel, fee_r, structuring])
            y.append(1)  # Medium -> Diff 2

        # 3. High Risk (400 samples):
        # 3A. Genuine High-Value Settlements (200 samples)
        for _ in range(200):
            amt = rng.uniform(10000.0, 1000000.0)
            vel = rng.uniform(0.1, 2.0)
            fee_r = rng.uniform(0.001, 0.02)
            structuring = rng.uniform(0.0, 0.2)
            X.append([amt, vel, fee_r, structuring])
            y.append(2)  # High -> Diff 3

        # 3B. Smurfing / Split Micro-Transaction Attacks (200 samples)
        # Attacker tries to disguise $1M as ₹95 transactions, but velocity and structuring flags spike!
        for _ in range(200):
            amt = rng.uniform(85.0, 99.9)        # deceptive micro amounts
            vel = rng.uniform(8.0, 30.0)         # ABNORMAL burst velocity
            fee_r = rng.uniform(0.03, 0.12)      # higher gas to crowd out
            structuring = rng.uniform(0.75, 1.0) # HIGH structuring pattern detected
            X.append([amt, vel, fee_r, structuring])
            y.append(2)  # High -> Diff 3 (Attacker caught!)

        return np.array(X), np.array(y)

    def _train_initial_model(self):
        X, y = self._generate_synthetic_training_data()
        self.model.fit(X, y)
        self.is_trained = True

    def extract_features(
        self,
        amount: float,
        sender: str,
        timestamp: float
    ) -> List[float]:
        """Extract multi-dimensional telemetry features for a given transaction."""
        # Track velocity (transactions in last 60 seconds)
        now = timestamp
        if sender not in self._sender_history:
            self._sender_history[sender] = []
        history = self._sender_history[sender]
        # Keep timestamps from the last 60 seconds
        history = [t for t in history if now - t <= 60.0]
        history.append(now)
        self._sender_history[sender] = history

        velocity = float(len(history))

        # Fee ratio estimate
        fee_ratio = 0.02 if amount < 500 else 0.005

        # Structuring risk: high velocity combined with amounts hovering just below the 100 threshold
        if velocity > 4.0 and (80.0 <= amount <= 99.99):
            structuring_risk = 0.95
        elif velocity > 3.0:
            structuring_risk = 0.45
        else:
            structuring_risk = 0.05

        return [float(amount), velocity, fee_ratio, structuring_risk]

    def evaluate_transaction(
        self,
        amount: float,
        sender: str,
        timestamp: float
    ) -> MLRiskResult:
        """Run ML inference on a single transaction."""
        features = self.extract_features(amount, sender, timestamp)
        features_arr = np.array([features])

        probs = self.model.predict_proba(features_arr)[0]
        pred_class = int(np.argmax(probs))
        confidence = float(probs[pred_class])

        class_map = {0: "low", 1: "medium", 2: "high"}
        diff_map = {0: 1, 1: 2, 2: 3}

        level = class_map[pred_class]
        diff = diff_map[pred_class]

        # Calculate continuous risk score (0.0 to 1.0)
        risk_score = float(probs[1] * 0.5 + probs[2] * 1.0)

        # Generate explainable AI reasoning
        amount_val, vel, _, struct_flag = features
        if struct_flag > 0.8:
            reasoning = f"Anomaly: High-velocity micro-burst detected ({vel:.0f} tx/min). Prevented smurfing attack."
        elif level == "high":
            reasoning = f"High-value financial settlement (INR {amount_val:,.2f}). Imposing maximum PoW security."
        elif level == "medium":
            reasoning = f"Standard retail transfer (INR {amount_val:,.2f}). Balanced difficulty applied."
        else:
            reasoning = f"Verified low-risk micropayment (INR {amount_val:,.2f}). Low-latency fast path approved."

        return MLRiskResult(
            risk_level=level,
            risk_score=round(risk_score, 3),
            confidence=round(confidence, 3),
            suggested_difficulty=diff,
            reasoning=reasoning
        )

    def evaluate_batch(self, transactions) -> Tuple[int, str, List[MLRiskResult]]:
        """Evaluate an entire batch of transactions for block mining.
        The block difficulty adapts to the HIGHEST risk transaction in the batch.
        """
        if not transactions:
            return 1, "Empty batch -> Default low difficulty", []

        results = []
        max_diff = 1
        dominant_reason = "All transactions verified low-risk micropayments."

        for tx in transactions:
            amt = getattr(tx, "amount", 0.0)
            sender = getattr(tx, "sender", "0xAnonymous")
            ts = getattr(tx, "timestamp", 0.0)
            res = self.evaluate_transaction(amt, sender, ts)
            results.append(res)

            if res.suggested_difficulty > max_diff:
                max_diff = res.suggested_difficulty
                dominant_reason = res.reasoning

        return max_diff, dominant_reason, results


# Global singleton instance for high-speed cached inference
ml_engine = ConsensusMLEngine()
