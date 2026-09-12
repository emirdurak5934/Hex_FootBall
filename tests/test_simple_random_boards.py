import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Audit the rule-driven random Possession board generator."""

from collections import Counter, defaultdict
import json
import statistics
import time

import app
from criterion_engine import CLUB_CLASSES, TURKISH_CLUBS


SAMPLE_SIZE = 500


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


def has_large_trophy_component(board):
    trophy_cells = {
        index for index, item in enumerate(board) if item["type"] == "trophy"
    }
    unseen = set(trophy_cells)
    while unseen:
        component = {unseen.pop()}
        frontier = list(component)
        while frontier:
            connected = unseen & set(app.neighbors[frontier.pop()])
            unseen -= connected
            component |= connected
            frontier.extend(connected)
        if len(component) >= 3:
            return True
    return False


def summary(values):
    return {
        "min": min(values),
        "average": round(statistics.mean(values), 3),
        "max": max(values),
    }


def main():
    class_by_club = {
        club: club_class
        for club_class, clubs in CLUB_CLASSES.items()
        for club in clubs
    }
    groups = {size: connected_groups(size) for size in (2, 3, 4)}
    failures = 0
    times = []
    type_counts = defaultdict(list)
    birth_counts = Counter()
    league_counts = Counter()
    position_counts = Counter()
    continent_counts = Counter()
    class_counts = Counter()
    turkish_board_counts = Counter()
    turkish_club_counts = Counter()
    violations = Counter()
    dead_edges = []
    scores = []
    regions = Counter()
    four_move_opportunities = []
    attempts = []
    edge_counts = []
    playable_edge_ratios = []
    strong_edge_ratios = []
    weak_edge_ratios = []
    isolated_cells = []
    playable_neighbor_cells = Counter()
    quality_triples = []
    continent_edges = Counter()
    continent_edges_by_value = defaultdict(Counter)
    asia_playable_neighbors = []
    asia_strong_boards = 0

    for seed in range(SAMPLE_SIZE):
        started = time.perf_counter()
        try:
            board, analysis = app.criterion_engine.generate_board(seed=seed)
        except RuntimeError:
            failures += 1
            times.append(time.perf_counter() - started)
            continue
        times.append(time.perf_counter() - started)
        attempts.append(analysis["attempts"])
        edge_counts.append(analysis["edge_count"])
        playable_edge_ratios.append(analysis["playable_edge_ratio"])
        strong_edge_ratios.append(analysis["strong_edge_ratio"])
        weak_edge_ratios.append(analysis["weak_edge_ratio"])
        isolated_cells.append(analysis["isolated_cells"])
        playable_neighbor_cells.update(analysis["playable_neighbor_cells"])
        quality_triples.append(analysis["quality_triple_regions"])
        if analysis["asia_local"] is not None:
            asia_playable_neighbors.append(
                analysis["asia_local"]["playable_neighbors"]
            )
            asia_strong_boards += analysis["asia_local"]["strong_neighbors"] > 0
        keys = [(item["type"], item["value"]) for item in board]
        counts = Counter(item["type"] for item in board)
        for criterion_type in (
            "club", "trophy", "nationality", "league", "position",
            "birth_decade", "continent",
        ):
            type_counts[criterion_type].append(counts[criterion_type])

        birth_counts.update(
            item["value"] for item in board if item["type"] == "birth_decade"
        )
        league_counts.update(
            item["value"] for item in board if item["type"] == "league"
        )
        position_counts.update(
            item["value"] for item in board if item["type"] == "position"
        )
        continent_counts.update(
            item["value"] for item in board if item["type"] == "continent"
        )
        clubs = [item["value"] for item in board if item["type"] == "club"]
        class_counts.update(class_by_club[club] for club in clubs)
        turkish = [club for club in clubs if club in TURKISH_CLUBS]
        turkish_board_counts[len(turkish)] += 1
        turkish_club_counts.update(turkish)

        violations["league_count"] += counts["league"] != 2
        violations["position_count"] += counts["position"] != 2
        violations["birth_count"] += counts["birth_decade"] != 1
        violations["total_count"] += len(board) != 31
        violations["continent_count"] += counts["continent"] != 1
        violations["club_range"] += not 14 <= counts["club"] <= 16
        violations["trophy_range"] += not 6 <= counts["trophy"] <= 8
        violations["nationality_range"] += not 3 <= counts["nationality"] <= 5
        violations["isolated_playability_cell"] += analysis["isolated_cells"] > 0
        violations["north_america_criterion"] += any(
            item["type"] == "continent" and item["value"] == "North America"
            for item in board
        )
        violations["oceania_criterion"] += any(
            item["type"] == "continent" and item["value"] == "Oceania"
            for item in board
        )
        violations["duplicate_criterion"] += len(set(keys)) != 31
        violations["five_plus"] += analysis["has_five_plus"]
        violations["zero_answer_criterion"] += any(
            app.criterion_engine.criterion_stats[key]["total"] == 0 for key in keys
        )
        violations["three_plus_turkish"] += len(turkish) >= 3
        violations["trophy_component_3_plus"] += has_large_trophy_component(board)
        for first, adjacent in app.neighbors.items():
            for second in adjacent:
                if first >= second:
                    continue
                first_type, second_type = board[first]["type"], board[second]["type"]
                for criterion_type in ("nationality", "league", "position"):
                    violations[f"{criterion_type}_adjacency"] += (
                        first_type == second_type == criterion_type
                    )
                if "continent" in {first_type, second_type}:
                    first_key, second_key = keys[first], keys[second]
                    total, popular, medium, _ = app.criterion_engine._pair_stats(
                        first_key, second_key
                    )
                    recognizable = popular + medium
                    continent_edges["total"] += 1
                    continent_edges["playable"] += recognizable >= 2
                    continent_edges["strong"] += recognizable >= 5
                    continent_edges["weak"] += recognizable < 2
                    continent_edges["dead"] += total == 0
                    continent_value = (
                        board[first]["value"]
                        if first_type == "continent"
                        else board[second]["value"]
                    )
                    per_continent = continent_edges_by_value[continent_value]
                    per_continent["total"] += 1
                    per_continent["playable"] += recognizable >= 2
                    per_continent["strong"] += recognizable >= 5
                    per_continent["weak"] += recognizable < 2
                    per_continent["dead"] += total == 0

        dead_edges.append(analysis["dead_edges"])
        scores.append(analysis["score"])
        four_move_opportunities.append(analysis["opportunities"]["4"])
        for size, candidates in groups.items():
            for group in candidates:
                common = set.intersection(*(
                    app.criterion_engine.answer_sets[keys[index]] for index in group
                ))
                regions[size] += bool(common)

    produced = SAMPLE_SIZE - failures
    most_league = max(league_counts, key=league_counts.get)
    least_league = min(league_counts, key=league_counts.get)
    result = {
        "production": {
            "requested": SAMPLE_SIZE,
            "produced": produced,
            "failed": failures,
            "average_seconds": round(statistics.mean(times), 3),
            "min_seconds": round(min(times), 3),
            "max_seconds": round(max(times), 3),
            "average_attempts": round(statistics.mean(attempts), 3),
        },
        "connections": {
            "total_edges": sum(edge_counts),
            "playable_edge_percent": {
                key: round(value * 100, 2)
                for key, value in summary(playable_edge_ratios).items()
            },
            "average_strong_edge_percent": round(
                statistics.mean(strong_edge_ratios) * 100, 2
            ),
            "average_weak_edge_percent": round(
                statistics.mean(weak_edge_ratios) * 100, 2
            ),
            "average_isolated_cells": round(
                statistics.mean(isolated_cells), 3
            ),
            "boards_with_isolated_cells": sum(value > 0 for value in isolated_cells),
        },
        "cells_by_playable_neighbor_count": dict(playable_neighbor_cells),
        "quality_triple_regions": {
            **summary(quality_triples),
            "boards_below_6": sum(value < 6 for value in quality_triples),
        },
        "distribution": {
            key: summary(values) for key, values in type_counts.items()
        },
        "birth_frequency": {
            value: {
                "count": birth_counts[value],
                "percent": round(birth_counts[value] / SAMPLE_SIZE * 100, 2),
            }
            for value in (
                "Born in the 1980s", "Born in the 1990s", "Born in the 2000s"
            )
        },
        "league_frequency": dict(league_counts),
        "league_most_to_least_ratio": round(
            league_counts[most_league] / league_counts[least_league], 3
        ),
        "position_frequency": dict(position_counts),
        "continent_frequency": {
            value: {
                "count": continent_counts[value],
                "percent": round(continent_counts[value] / produced * 100, 2),
            }
            for value in ("Europe", "South America", "Africa", "Asia")
        },
        "continent_answer_pools": {
            value: {
                "total": app.criterion_engine.criterion_stats[("continent", value)]["total"],
                "recognizable": sum(
                    app.criterion_engine.criterion_stats[("continent", value)][tier]
                    for tier in ("popular", "medium")
                ),
            }
            for value in ("Europe", "South America", "Africa", "Asia")
        },
        "continent_edges": {
            "total": continent_edges["total"],
            **{
                f"{name}_percent": round(
                    continent_edges[name] / max(1, continent_edges["total"]) * 100,
                    2,
                )
                for name in ("playable", "strong", "weak", "dead")
            },
        },
        "continent_edges_by_value": {
            value: {
                "total": values["total"],
                **{
                    f"{name}_percent": round(
                        values[name] / max(1, values["total"]) * 100, 2
                    )
                    for name in ("playable", "strong", "weak", "dead")
                },
            }
            for value, values in continent_edges_by_value.items()
        },
        "asia_local_connections": {
            "boards": len(asia_playable_neighbors),
            "average_playable_neighbors": round(
                statistics.mean(asia_playable_neighbors), 3
            ),
            "minimum_playable_neighbors": min(asia_playable_neighbors),
            "zero_playable_neighbors": sum(
                value == 0 for value in asia_playable_neighbors
            ),
            "one_playable_neighbor": sum(
                value == 1 for value in asia_playable_neighbors
            ),
            "two_plus_playable_neighbors": sum(
                value >= 2 for value in asia_playable_neighbors
            ),
            "boards_with_strong_edge": asia_strong_boards,
        },
        "club_classes": {
            club_class: {
                "total": class_counts[club_class],
                "average_per_board": round(class_counts[club_class] / produced, 3),
            }
            for club_class in ("A", "B", "C")
        },
        "turkish_clubs": {
            "boards": {
                "0": turkish_board_counts[0], "1": turkish_board_counts[1],
                "2": turkish_board_counts[2],
                "3+": sum(v for k, v in turkish_board_counts.items() if k >= 3),
            },
            "clubs": {club: turkish_club_counts[club] for club in TURKISH_CLUBS},
        },
        "violations": dict(sorted(violations.items())),
        "analysis_only": {
            "average_dead_edges": round(statistics.mean(dead_edges), 3),
            "average_playability_score": round(statistics.mean(scores), 3),
            "average_four_move_opportunities": round(
                statistics.mean(four_move_opportunities), 3
            ),
            "average_unique_2_regions": round(regions[2] / produced, 3),
            "average_unique_3_regions": round(regions[3] / produced, 3),
            "average_unique_4_regions": round(regions[4] / produced, 3),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
