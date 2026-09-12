import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Measure soft league-frequency balancing over sequential board generation."""

import argparse
from collections import Counter
import json
import statistics
import time

import app


LEAGUES = (
    "Premier League", "La Liga", "Serie A", "Bundesliga", "Süper Lig"
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=500)
    return parser.parse_args()


def main():
    sample_size = parse_args().sample_size
    counts = Counter()
    failures = exact_two_violations = adjacency_violations = 0
    five_plus = repeated_pairs = 0
    dead_edges, scores, times = [], [], []
    previous_pair = None

    for seed in range(sample_size):
        started = time.perf_counter()
        try:
            board, analysis = app.criterion_engine.generate_board(seed=seed)
        except RuntimeError:
            failures += 1
            times.append(time.perf_counter() - started)
            continue
        times.append(time.perf_counter() - started)
        league_cells = [
            index for index, item in enumerate(board) if item["type"] == "league"
        ]
        pair = frozenset(board[index]["value"] for index in league_cells)
        counts.update(pair)
        exact_two_violations += len(league_cells) != 2 or len(pair) != 2
        adjacency_violations += any(
            second in app.neighbors[first]
            for first in league_cells for second in league_cells if first < second
        )
        repeated_pairs += previous_pair is not None and pair == previous_pair
        previous_pair = pair
        five_plus += analysis["has_five_plus"]
        dead_edges.append(analysis["dead_edges"])
        scores.append(analysis["score"])

    most = max(LEAGUES, key=counts.get)
    least = min(LEAGUES, key=counts.get)
    produced = sample_size - failures
    result = {
        "requested": sample_size,
        "produced": produced,
        "failed": failures,
        "league_counts": {
            league: {
                "count": counts[league],
                "board_percent": round(counts[league] / sample_size * 100, 2),
                "slot_percent": round(counts[league] / max(1, produced * 2) * 100, 2),
            }
            for league in LEAGUES
        },
        "most_frequent": most,
        "least_frequent": least,
        "most_to_least_ratio": round(counts[most] / max(1, counts[least]), 3),
        "consecutive_exact_pair_repeats": repeated_pairs,
        "exact_two_league_violations": exact_two_violations,
        "league_adjacency_violations": adjacency_violations,
        "average_dead_edges": round(statistics.mean(dead_edges), 3),
        "average_playability_score": round(statistics.mean(scores), 3),
        "five_plus_boards": five_plus,
        "average_generation_seconds": round(statistics.mean(times), 3),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
