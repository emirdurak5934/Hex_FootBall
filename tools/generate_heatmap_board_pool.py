"""Generate validated Heatmap boards for the production-ready board pool."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402


OUTPUT = ROOT / "data" / "heatmap_boards.json"
BOARD_COUNT = 24


def signature(board):
    return tuple((cell.get("type"), cell.get("value")) for cell in board)


def main():
    boards = []
    signatures = set()
    seed = 2026100401
    while len(boards) < BOARD_COUNT:
        board = app.generate_heatmap_board(seed=seed)
        seed += 1
        board_signature = signature(board)
        if board_signature in signatures:
            continue
        signatures.add(board_signature)
        boards.append(board)
        print(f"Hazır Isı Haritası tahtası: {len(boards)}/{BOARD_COUNT}")
    OUTPUT.write_text(
        json.dumps(boards, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Tahta havuzu yazıldı: {OUTPUT}")


if __name__ == "__main__":
    main()
