import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Generate a board sample and report Turkish-club distribution metrics."""

from collections import Counter
import json
import time

import app


SAMPLE_SIZE = 500
TURKISH_CLUBS = {
    "Galatasaray",
    "Fenerbahçe",
    "Beşiktaş",
    "Trabzonspor",
}


def main():
    turkish_counts = Counter()
    team_counts = Counter()
    dead_edges = []
    playability_scores = []
    generation_times = []
    failures = 0

    for seed in range(SAMPLE_SIZE):
        started = time.perf_counter()
        try:
            board, analysis = app.criterion_engine.generate_board(seed=seed)
        except RuntimeError:
            failures += 1
            generation_times.append((time.perf_counter() - started) * 1000)
            continue

        generation_times.append((time.perf_counter() - started) * 1000)
        present = {item["value"] for item in board} & TURKISH_CLUBS
        turkish_counts[len(present)] += 1
        team_counts.update(present)
        dead_edges.append(analysis["dead_edges"])
        playability_scores.append(analysis["score"])

    result = {
        "boards_requested": SAMPLE_SIZE,
        "turkish_board_counts": {
            "0": turkish_counts[0],
            "1": turkish_counts[1],
            "2": turkish_counts[2],
            "3+": sum(
                count for club_count, count in turkish_counts.items()
                if club_count >= 3
            ),
        },
        "team_counts": {
            team: team_counts[team] for team in sorted(TURKISH_CLUBS)
        },
        "team_percentages": {
            team: round(team_counts[team] / SAMPLE_SIZE * 100, 2)
            for team in sorted(TURKISH_CLUBS)
        },
        "average_dead_edges": round(
            sum(dead_edges) / len(dead_edges), 3
        ) if dead_edges else None,
        "average_playability_score": round(
            sum(playability_scores) / len(playability_scores), 3
        ) if playability_scores else None,
        "average_generation_ms": round(
            sum(generation_times) / len(generation_times), 3
        ),
        "failed_boards": failures,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
