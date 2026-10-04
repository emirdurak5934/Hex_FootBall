"""Regression tests for prepared Heatmap boards and transient-state cleanup."""

from __future__ import annotations

import os as _path_os
import sys as _path_sys
import time


SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)

import app


def main():
    assert len(app.heatmap_board_pool) >= 20
    assert all(
        len(board) == 31
        and board[app.HEATMAP_SCORE_INDEX]["type"] == "score"
        and app.analyze_heatmap_board(board)["isolated_cells"] == 0
        for board in app.heatmap_board_pool
    )

    original_generator = app.generate_heatmap_board
    app.generate_heatmap_board = lambda seed=None: (_ for _ in ()).throw(
        AssertionError("Route sırasında ağır tahta üretimi çağrıldı.")
    )
    try:
        token, game = app.create_heatmap_game()
        assert token in app.heatmap_games and len(game["cells"]) == 31
    finally:
        app.generate_heatmap_board = original_generator
        app.heatmap_games.pop(token, None)

    now = time.time()
    store = {
        "active": {"created_at": now, "finished": False},
        "abandoned": {
            "created_at": now - app.LOCAL_GAME_TTL_SECONDS - 1,
            "finished": False,
        },
        "finished": {
            "created_at": now - app.FINISHED_GAME_TTL_SECONDS - 1,
            "finished": True,
        },
    }
    removed = app.prune_local_game_store(store, now=now)
    assert removed == 2 and set(store) == {"active"}

    original_limit = app.MAX_LOCAL_GAME_STATES
    app.MAX_LOCAL_GAME_STATES = 3
    try:
        bounded = {
            f"game-{index}": {"created_at": now + index, "finished": False}
            for index in range(6)
        }
        app.prune_local_game_store(bounded, now=now, reserve=1)
        assert set(bounded) == {"game-4", "game-5"}
    finally:
        app.MAX_LOCAL_GAME_STATES = original_limit

    print({
        "prepared_heatmap_boards": len(app.heatmap_board_pool),
        "request_time_generation_removed": True,
        "abandoned_games_expire": True,
        "finished_games_expire_early": True,
        "state_count_is_bounded": True,
    })


if __name__ == "__main__":
    main()
