import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Generate and summarize 500 Heatmap boards without score-cell edge bias."""

from collections import Counter, defaultdict
import json
import statistics
import time

import app


SAMPLE_SIZE = 500


def summary(values):
    return {"min": min(values), "average": round(statistics.mean(values), 4), "max": max(values)}


def main():
    times = []
    analyses = []
    type_counts = defaultdict(list)
    violations = Counter()

    for seed in range(SAMPLE_SIZE):
        started = time.perf_counter()
        try:
            cells = app.generate_heatmap_board(seed=seed)
        except RuntimeError:
            violations["generation_failure"] += 1
            continue
        times.append(time.perf_counter() - started)
        keys = [
            app.criterion_engine._key(cell)
            for cell in cells if cell["type"] != "score"
        ]
        counts = Counter(key[0] for key in keys)
        for criterion_type, amount in counts.items():
            type_counts[criterion_type].append(amount)
        violations["criterion_count"] += len(keys) != 30
        violations["score_count"] += sum(cell["type"] == "score" for cell in cells) != 1
        violations["duplicate"] += len(keys) != len(set(keys))
        violations["zero_answer"] += any(
            app.criterion_engine.criterion_stats[key]["total"] == 0 for key in keys
        )
        analyses.append(app.analyze_heatmap_board(cells))

    produced = len(analyses)
    result = {
        "production": {
            "requested": SAMPLE_SIZE, "successful": produced,
            "failed": SAMPLE_SIZE - produced,
            "seconds": summary(times),
        },
        "violations": dict(violations),
        "type_distribution": {
            key: summary(values) for key, values in sorted(type_counts.items())
        },
        "connections": {
            "average_criterion_edges": round(statistics.mean(a["edge_count"] for a in analyses), 3),
            "average_playable_percent": round(statistics.mean(a["playable_edge_ratio"] for a in analyses) * 100, 2),
            "average_strong_percent": round(statistics.mean(a["strong_edge_ratio"] for a in analyses) * 100, 2),
            "average_dead_edges": round(statistics.mean(a["dead_edges"] for a in analyses), 3),
            "average_isolated_cells": round(statistics.mean(a["isolated_cells"] for a in analyses), 3),
            "average_combo_regions": {
                str(size): round(statistics.mean(a["regions"][size] for a in analyses), 3)
                for size in (2, 3, 4)
            },
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
