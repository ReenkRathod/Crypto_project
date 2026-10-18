"""
app.py — Interactive Web Dashboard Server for Hybrid Consensus Blockchain
==========================================================================
Zero-dependency local web server built with Python standard library.
Serves REST APIs and the interactive dashboard at http://localhost:5000.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from blockchain import Block, Blockchain, Transaction
from consensus import BaselineConsensus, HybridConsensus

PORT = 5000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

# Active global state
chain = Blockchain()
mempool = []
baseline_engine = BaselineConsensus(difficulty=3)
hybrid_engine = HybridConsensus(light_difficulty=1, strong_difficulty=3)

def seed_initial_mempool():
    global mempool
    mempool = [
        Transaction(
            tx_id=f"tx-{uuid.uuid4().hex[:6]}",
            sender="0xAlice_4A",
            receiver="0xBob_9F",
            amount=25.0,
            tx_type="lightweight",
            timestamp=time.time(),
        ),
        Transaction(
            tx_id=f"tx-{uuid.uuid4().hex[:6]}",
            sender="0xCharlie_11",
            receiver="0xCafe_88",
            amount=40.0,
            tx_type="lightweight",
            timestamp=time.time(),
        ),
    ]

seed_initial_mempool()


def serialize_block(b: Block) -> dict:
    return {
        "index": b.index,
        "transactions": [tx.to_dict() for tx in b.transactions],
        "previous_hash": b.previous_hash,
        "hash": b.compute_hash(),
        "nonce": b.nonce,
        "difficulty": b.difficulty,
        "timestamp": b.timestamp,
        "hash_attempts": getattr(b, "hash_attempts", 0),
        "cpu_time": getattr(b, "cpu_time", 0.0),
    }


def get_system_state() -> dict:
    is_valid = chain.verify_chain()
    serialized_blocks = [serialize_block(b) for b in chain.chain]
    serialized_mempool = [tx.to_dict() for tx in mempool]

    total_hashes = sum(getattr(b, "hash_attempts", 0) for b in chain.chain)
    total_cpu = sum(getattr(b, "cpu_time", 0.0) for b in chain.chain)

    return {
        "chain": serialized_blocks,
        "mempool": serialized_mempool,
        "chain_valid": is_valid,
        "total_blocks": len(chain.chain),
        "total_transactions": sum(len(b.transactions) for b in chain.chain) + len(mempool),
        "total_hashes": total_hashes,
        "total_cpu_time": round(total_cpu, 4),
    }


class BlockchainRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status: int = HTTPStatus.OK):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, filepath: str):
        if not os.path.isfile(filepath):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        mime_type, _ = mimetypes.guess_type(filepath)
        mime_type = mime_type or "application/octet-stream"
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            index_path = os.path.join(WEB_DIR, "index.html")
            self._serve_file(index_path)
            return

        if path.startswith("/results/charts/"):
            rel_file = path.replace("/results/charts/", "")
            chart_file = os.path.join(RESULTS_DIR, "charts", rel_file)
            self._serve_file(chart_file)
            return

        if path == "/api/state":
            self._send_json(get_system_state())
            return

        rel_path = path.lstrip("/")
        potential_file = os.path.join(WEB_DIR, rel_path)
        if os.path.isfile(potential_file):
            self._serve_file(potential_file)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self):
        global chain, mempool
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        # 1. Add Single Transaction
        if path == "/api/transaction":
            sender = payload.get("sender", "0xUserA").strip() or "0xUserA"
            receiver = payload.get("receiver", "0xUserB").strip() or "0xUserB"
            amount = float(payload.get("amount", 10.0))
            tx_type = payload.get("tx_type")
            if not tx_type:
                tx_type = "strong" if amount >= 1000.0 else "lightweight"

            tx = Transaction(
                tx_id=f"tx-{uuid.uuid4().hex[:6]}",
                sender=sender,
                receiver=receiver,
                amount=amount,
                tx_type=tx_type,
                timestamp=time.time(),
            )
            mempool.append(tx)
            self._send_json({
                "success": True,
                "message": f"Added {tx_type} transaction for ₹{amount:,.2f}",
                "transaction": tx.to_dict(),
                "mempool_size": len(mempool)
            })
            return

        # 2. Add Sample Presets (Chai, Metro, Contract)
        if path == "/api/quick-batch":
            preset = payload.get("preset", "lightweight")
            added = []
            if preset == "lightweight":
                items = [
                    ("0xRohan_22", "0xChaiPoint", 25.0, "lightweight"),
                    ("0xPriya_77", "0xMetroRail", 60.0, "lightweight"),
                    ("0xAmit_99", "0xGroceryStore", 180.0, "lightweight"),
                ]
            else: # strong / high-value settlement
                items = [
                    ("0xRohan_22", "0xCafeDay", 140.0, "lightweight"),
                    ("0xFinCorp_Treasury", "0xEscrowVault", 500000.0, "strong"),
                    ("0xTechVenture", "0xVendorService", 125000.0, "strong"),
                ]
            for s, r, a, t in items:
                tx = Transaction(
                    tx_id=f"tx-{uuid.uuid4().hex[:6]}",
                    sender=s, receiver=r, amount=a, tx_type=t, timestamp=time.time()
                )
                mempool.append(tx)
                added.append(tx.to_dict())

            self._send_json({
                "success": True,
                "message": f"Added {len(added)} transactions to mempool",
                "added": added,
                "mempool_size": len(mempool)
            })
            return

        # 3. Mine Block with chosen consensus mode
        if path == "/api/mine":
            mode = payload.get("mode", "hybrid")
            if not mempool:
                self._send_json({"success": False, "message": "Mempool is empty! Add transactions first."}, status=400)
                return

            batch_to_mine = list(mempool)
            mempool.clear()

            engine = hybrid_engine if mode == "hybrid" else baseline_engine
            t_start = time.perf_counter()
            result = engine.mine(chain, batch_to_mine)
            t_end = time.perf_counter()

            ok = chain.add_block(result.block)

            self._send_json({
                "success": ok,
                "mode": mode,
                "block_index": result.block.index,
                "difficulty_applied": result.block.difficulty,
                "hash_attempts": result.hash_attempts,
                "mining_time_ms": round((t_end - t_start) * 1000, 2),
                "block_hash": result.block.compute_hash(),
                "chain_valid": chain.verify_chain(),
                "transactions_mined": len(batch_to_mine),
            })
            return

        # 4. Tamper with a Block to demonstrate tamper-evidence
        if path == "/api/tamper":
            block_idx = int(payload.get("block_index", 1))
            if block_idx <= 0 or block_idx >= len(chain.chain):
                self._send_json({"success": False, "message": "Cannot tamper genesis or non-existent block"}, status=400)
                return

            target_block = chain.chain[block_idx]
            if not target_block.transactions:
                self._send_json({"success": False, "message": "Target block has no transactions to tamper"}, status=400)
                return

            orig_amount = target_block.transactions[0].amount
            tampered_amount = orig_amount + 5000000.0
            target_block.transactions[0].amount = tampered_amount

            valid_after = chain.verify_chain()
            self._send_json({
                "success": True,
                "tampered_block": block_idx,
                "original_amount": orig_amount,
                "tampered_amount": tampered_amount,
                "chain_valid": valid_after,
                "message": f"Block #{block_idx} tampered! Chain validation now returns: {valid_after}"
            })
            return

        # 5. Reset Blockchain to Genesis
        if path == "/api/reset":
            chain = Blockchain()
            seed_initial_mempool()
            self._send_json({
                "success": True,
                "message": "Blockchain reset to Genesis. Fresh demo transactions loaded in mempool."
            })
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")


def start_server():
    server_address = ("127.0.0.1", PORT)
    httpd = ThreadingHTTPServer(server_address, BlockchainRequestHandler)
    print("\n" + "=" * 65)
    print(f"  BLOCKCHAIN INTERACTIVE DASHBOARD RUNNING")
    print(f"  URL: http://localhost:{PORT}")
    print("=" * 65 + "\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    start_server()
