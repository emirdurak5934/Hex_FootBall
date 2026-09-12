import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Generate 100 Tiki Taka Toe boards and report playability metrics."""

import json
from statistics import mean

from app import COUNTRY_ALIASES, CLUB_ALIASES, TROPHY_ALIASES
from tiki_taka_engine import TikiTakaEngine


def main():
    with open("data/players.json", encoding="utf-8") as source:
        players = json.load(source)
    engine = TikiTakaEngine(players, CLUB_ALIASES, COUNTRY_ALIASES, TROPHY_ALIASES)
    counts = []
    failed = dead = duplicate = 0
    for _ in range(100):
        try:
            board = engine.generate_board()
        except RuntimeError:
            failed += 1
            continue
        valid, board_counts = engine.validate_board(board["rows"], board["columns"])
        counts.extend(board_counts)
        dead += sum(value == 0 for value in board_counts)
        duplicate += not valid and len(set(
            (item["type"], item["key"])
            for item in board["rows"] + board["columns"]
        )) != 6
    print(f"Boards generated: {100 - failed}")
    print(f"Failed boards: {failed}")
    print(f"Minimum cell answers: {min(counts) if counts else 0}")
    print(f"Average cell answers: {mean(counts):.2f}" if counts else "Average cell answers: 0")
    print(f"Maximum cell answers: {max(counts) if counts else 0}")
    print(f"Dead cells: {dead}")
    print(f"Duplicate criteria: {duplicate}")
    assert failed == dead == duplicate == 0


if __name__ == "__main__":
    main()
