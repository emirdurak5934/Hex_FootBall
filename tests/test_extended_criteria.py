import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Audit the extended Possession criterion pool without mutating player data."""

from collections import Counter, defaultdict
from itertools import combinations
import json
import statistics
import time

import app


SAMPLE_SIZE = 100
NEW_TYPES = {"position", "league", "birth_decade"}
TURKISH_CLUBS = {"Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor"}


def edges():
    return {
        tuple(sorted((first, second)))
        for first, adjacent in app.neighbors.items()
        for second in adjacent
        if first != second
    }


def connected_groups(size):
    groups = {frozenset((index,)) for index in app.neighbors}
    for _ in range(1, size):
        groups = {
            group | {neighbor}
            for group in groups
            for cell in group
            for neighbor in app.neighbors[cell]
            if neighbor not in group
        }
    return groups


def average_summary(values):
    return {
        "average": round(statistics.mean(values), 3),
        "min": min(values),
        "max": max(values),
    }


def main():
    board_edges = edges()
    groups = {size: connected_groups(size) for size in (2, 3, 4)}
    failures = 0
    times = []
    scores = []
    dead_edges = []
    counts = defaultdict(list)
    violations = Counter()
    opportunity_regions = Counter()
    criterion_answers = defaultdict(lambda: {"total": [], "recognizable": []})
    new_edge_buckets = Counter()
    new_edge_total = 0

    for seed in range(SAMPLE_SIZE):
        started = time.perf_counter()
        try:
            board, analysis = app.criterion_engine.generate_board(seed=seed)
        except RuntimeError:
            failures += 1
            times.append(time.perf_counter() - started)
            continue
        times.append(time.perf_counter() - started)
        scores.append(analysis["score"])
        dead_edges.append(analysis["dead_edges"])
        keys = [(item["type"], item["value"]) for item in board]
        type_counts = Counter(key[0] for key in keys)
        for criterion_type in (
            "club", "trophy", "nationality", "position", "league",
            "birth_decade",
        ):
            counts[criterion_type].append(type_counts[criterion_type])

        expected = {"position": 2, "league": 2, "birth_decade": 1}
        for criterion_type, amount in expected.items():
            violations[f"{criterion_type}_count"] += type_counts[criterion_type] != amount
        violations["club_range"] += not 15 <= type_counts["club"] <= 17
        violations["nationality_range"] += not 3 <= type_counts["nationality"] <= 5
        violations["trophy_range"] += not 6 <= type_counts["trophy"] <= 8
        violations["duplicate_criterion"] += len(set(keys)) != 31
        violations["five_plus_move"] += analysis["has_five_plus"]
        violations["three_plus_turkish_clubs"] += sum(
            item["type"] == "club" and item["value"] in TURKISH_CLUBS
            for item in board
        ) >= 3

        for first, second in board_edges:
            first_type, second_type = keys[first][0], keys[second][0]
            for forbidden in ("nationality", "position", "league"):
                violations[f"{forbidden}_{forbidden}_edge"] += (
                    first_type == second_type == forbidden
                )
            if first_type in NEW_TYPES or second_type in NEW_TYPES:
                new_edge_total += 1
                total, popular, medium, _ = app.criterion_engine._pair_stats(
                    keys[first], keys[second]
                )
                recognizable = popular + medium
                if total == 0:
                    new_edge_buckets["dead"] += 1
                elif recognizable == 0:
                    new_edge_buckets["obscure_only"] += 1
                elif recognizable <= 5:
                    new_edge_buckets["recognizable_1_5"] += 1
                elif recognizable <= 20:
                    new_edge_buckets["recognizable_6_20"] += 1
                else:
                    new_edge_buckets["recognizable_21_plus"] += 1

        for size, candidates in groups.items():
            for group in candidates:
                common = set.intersection(*(
                    app.criterion_engine.answer_sets[keys[index]]
                    for index in group
                ))
                opportunity_regions[size] += bool(common)

        for key in keys:
            if key[0] not in NEW_TYPES:
                continue
            stats = app.criterion_engine.criterion_stats[key]
            criterion_answers[key]["total"].append(stats["total"])
            criterion_answers[key]["recognizable"].append(
                stats["popular"] + stats["medium"]
            )

    produced = SAMPLE_SIZE - failures
    result = {
        "production": {
            "requested": SAMPLE_SIZE,
            "produced": produced,
            "failed_seeds": failures,
            "seconds": average_summary(times),
        },
        "distribution": {
            key: average_summary(value) for key, value in counts.items()
        },
        "violations": dict(sorted(violations.items())),
        "quality": {
            "average_dead_edges": round(statistics.mean(dead_edges), 3),
            "average_playability_score": round(statistics.mean(scores), 3),
            "average_unique_2_regions": round(opportunity_regions[2] / produced, 3),
            "average_unique_3_regions": round(opportunity_regions[3] / produced, 3),
            "average_unique_4_regions": round(opportunity_regions[4] / produced, 3),
        },
        "new_criterion_answers": {
            f"{key[0]}:{key[1]}": {
                "average_total": round(statistics.mean(values["total"]), 3),
                "average_recognizable": round(
                    statistics.mean(values["recognizable"]), 3
                ),
                "appearances": len(values["total"]),
            }
            for key, values in sorted(criterion_answers.items())
        },
        "new_type_edges": {
            "total": new_edge_total,
            **{
                key: {
                    "count": new_edge_buckets[key],
                    "percent": round(
                        new_edge_buckets[key] / max(1, new_edge_total) * 100, 3
                    ),
                }
                for key in (
                    "dead", "obscure_only", "recognizable_1_5",
                    "recognizable_6_20", "recognizable_21_plus",
                )
            },
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
