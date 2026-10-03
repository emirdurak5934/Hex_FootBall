import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Heatmap V1 route, validation, capture, scoring, and completion tests."""

import re

import app


def player_id(index):
    return str(app.players[index]["id"])


def condition(key):
    return dict(app.criterion_engine.by_key[key])


def make_controlled_game(combo_size):
    source = max(
        (index for index in app.neighbors if index != app.HEATMAP_SCORE_INDEX),
        key=lambda index: len([
            item for item in app.neighbors[index]
            if item != app.HEATMAP_SCORE_INDEX
        ]),
    )
    playable_neighbors = [
        item for item in app.neighbors[source]
        if item != app.HEATMAP_SCORE_INDEX
    ]
    for index, matched in enumerate(app.criterion_engine.player_keys):
        matched = [key for key in matched if key in app.criterion_engine.by_key]
        nonmatched = next(
            (key for key in app.criterion_engine.keys if key not in matched),
            None,
        )
        if len(matched) >= combo_size and nonmatched:
            break
    else:
        raise AssertionError("No controlled Heatmap player found")

    cells = [condition(nonmatched) for _ in range(31)]
    cells[app.HEATMAP_SCORE_INDEX] = {
        "type": "score", "value": None, "label": "PUAN", "image": ""
    }
    cells[source] = condition(matched[0])
    for neighbor, key in zip(playable_neighbors, matched[1:combo_size]):
        cells[neighbor] = condition(key)

    token = f"controlled-{combo_size}"
    app.heatmap_games[token] = {
        "cells": cells, "heated": {}, "score": 0, "moves": 0,
        "finished": False,
    }
    return token, source, index


def make_reheat_game(new_capture_count=1, reheat_count=1, heat_level=1):
    source = max(
        (index for index in app.neighbors if index != app.HEATMAP_SCORE_INDEX),
        key=lambda index: len([
            item for item in app.neighbors[index]
            if item != app.HEATMAP_SCORE_INDEX
        ]),
    )
    playable_neighbors = [
        item for item in app.neighbors[source]
        if item != app.HEATMAP_SCORE_INDEX
    ]
    required_matches = new_capture_count + reheat_count
    for player_index, player_keys in enumerate(app.criterion_engine.player_keys):
        matched = [key for key in player_keys if key in app.criterion_engine.by_key]
        nonmatched = next(
            (key for key in app.criterion_engine.keys if key not in matched), None
        )
        if len(matched) >= required_matches and nonmatched:
            break
    else:
        raise AssertionError("No controlled Reheat player found")

    cells = [condition(nonmatched) for _ in range(31)]
    cells[app.HEATMAP_SCORE_INDEX] = {
        "type": "score", "value": None, "label": "PUAN", "image": ""
    }
    cells[source] = condition(matched[0])
    new_neighbors = playable_neighbors[:new_capture_count - 1]
    reheat_neighbors = playable_neighbors[
        new_capture_count - 1:new_capture_count - 1 + reheat_count
    ]
    mismatched_heated_neighbor = playable_neighbors[
        new_capture_count - 1 + reheat_count
    ]
    for neighbor, key in zip(new_neighbors + reheat_neighbors, matched[1:]):
        cells[neighbor] = condition(key)

    non_direct = next(
        index for index in range(31)
        if index != app.HEATMAP_SCORE_INDEX
        and index != source
        and index not in app.neighbors[source]
    )
    cells[non_direct] = condition(matched[-1])
    heated = {neighbor: heat_level for neighbor in reheat_neighbors}
    heated[mismatched_heated_neighbor] = heat_level
    heated[non_direct] = heat_level
    token = f"reheat-{new_capture_count}-{reheat_count}-{heat_level}"
    app.heatmap_games[token] = {
        "cells": cells, "heated": heated, "score": 0, "moves": 0,
        "finished": False,
    }
    return (
        token, source, player_index, reheat_neighbors,
        mismatched_heated_neighbor, non_direct,
    )


def main():
    client = app.app.test_client()
    home = client.get("/")
    page = client.get("/heatmap")
    html = page.data.decode("utf-8")

    assert page.status_code == 200
    assert 'href="/heatmap"' in home.data.decode("utf-8")
    assert html.count('data-cell-type="criterion"') == 30
    assert html.count('data-cell-type="score"') == 1
    assert f'data-index="{app.HEATMAP_SCORE_INDEX}" data-cell-type="score"' in html
    assert re.search(r'data-cell-type="score"[^>]*>\s*<div', html)

    cells = app.generate_heatmap_board(seed=7001)
    keys = [
        app.criterion_engine._key(cell)
        for cell in cells if cell["type"] != "score"
    ]
    assert len(keys) == len(set(keys)) == 30
    assert all(app.criterion_engine.criterion_stats[key]["total"] > 0 for key in keys)

    search_name = app.players[0]["name"][:3]
    assert client.get(f"/search_players?q={search_name}").status_code == 200

    for combo_size, expected in ((1, 1), (2, 3), (3, 6), (4, 10)):
        token, source, controlled_player = make_controlled_game(combo_size)
        response = client.post("/heatmap/check", json={
            "game_token": token,
            "index": source,
            "player_id": player_id(controlled_player),
        })
        result = response.get_json()
        assert result["correct"]
        assert len(result["heated"]) == combo_size
        assert result["combo_level"] == combo_size
        assert result["gained_score"] == expected
        assert result["score"] == expected
        assert result["moves"] == 1
        assert set(result["heated"]) <= {source, *app.neighbors[source]}
        assert app.HEATMAP_SCORE_INDEX not in result["heated"]

        repeated = client.post("/heatmap/check", json={
            "game_token": token, "index": source,
            "player_id": player_id(controlled_player),
        })
        assert repeated.status_code == 409

    token, source, controlled_player = make_controlled_game(1)
    source_condition = app.heatmap_games[token]["cells"][source]
    wrong_player = next(
        index for index, candidate in enumerate(app.players)
        if not app.matches_condition(candidate, source_condition)
    )
    wrong = client.post("/heatmap/check", json={
        "game_token": token, "index": source,
        "player_id": player_id(wrong_player),
    }).get_json()
    assert wrong["accepted"] and not wrong["correct"]
    assert wrong["score"] == 0 and wrong["moves"] == 1
    assert wrong["scorePenalty"] == 1 and wrong["moveScore"] == -1
    assert wrong["totalScore"] == 0
    assert wrong["newlyHeated"] == [] and wrong["reheated"] == []
    assert not app.heatmap_games[token]["heated"]

    for starting_score, expected_score in ((10, 9), (5, 4), (1, 0), (0, 0)):
        token, source, controlled_player = make_controlled_game(1)
        game = app.heatmap_games[token]
        game["score"] = starting_score
        source_condition = game["cells"][source]
        wrong_player = next(
            index for index, candidate in enumerate(app.players)
            if not app.matches_condition(candidate, source_condition)
        )
        before_heated = dict(game["heated"])
        penalty_result = client.post("/heatmap/check", json={
            "game_token": token, "index": source,
            "player_id": player_id(wrong_player),
        }).get_json()
        assert penalty_result["totalScore"] == expected_score
        assert penalty_result["score"] == expected_score
        assert penalty_result["moves"] == 1
        assert penalty_result["moveScore"] == -1
        assert penalty_result["newlyHeated"] == []
        assert penalty_result["reheated"] == []
        assert game["heated"] == before_heated

    token, source, controlled_player = make_controlled_game(1)
    repeated_game = app.heatmap_games[token]
    repeated_game["score"] = 10
    source_condition = repeated_game["cells"][source]
    wrong_player = next(
        index for index, candidate in enumerate(app.players)
        if not app.matches_condition(candidate, source_condition)
    )
    repeated_scores = []
    for expected_score in (9, 8):
        repeated_result = client.post("/heatmap/check", json={
            "game_token": token, "index": source,
            "player_id": player_id(wrong_player),
        }).get_json()
        repeated_scores.append(repeated_result["totalScore"])
        assert repeated_result["totalScore"] == expected_score
        assert repeated_result["moves"] == 10 - expected_score
        assert repeated_game["heated"] == {}
    assert repeated_scores == [9, 8]

    score_attempt = client.post("/heatmap/check", json={
        "game_token": token, "index": app.HEATMAP_SCORE_INDEX,
        "player_id": player_id(controlled_player),
    })
    assert score_attempt.status_code == 400

    token, source, controlled_player, reheated, mismatched_neighbor, non_direct = make_reheat_game(
        new_capture_count=2, reheat_count=3, heat_level=1
    )
    reheat_result = client.post("/heatmap/check", json={
        "game_token": token, "index": source,
        "player_id": player_id(controlled_player),
    }).get_json()
    assert reheat_result["newlyHeated"] == reheat_result["heated"]
    assert len(reheat_result["newlyHeated"]) == 2
    assert set(reheat_result["reheated"]) == set(reheated)
    assert reheat_result["comboCount"] == 2
    assert reheat_result["comboScore"] == 3
    assert reheat_result["reheatScore"] == 3
    assert reheat_result["moveScore"] == reheat_result["totalScore"] == 6
    assert all(app.heatmap_games[token]["heated"][index] == 2 for index in reheated)
    assert mismatched_neighbor not in reheat_result["reheated"]
    assert app.heatmap_games[token]["heated"][mismatched_neighbor] == 1
    assert app.heatmap_games[token]["heated"][non_direct] == 1
    assert app.HEATMAP_SCORE_INDEX not in reheat_result["reheated"]

    token, source, controlled_player, reheated, _, _ = make_reheat_game(
        new_capture_count=1, reheat_count=1, heat_level=5
    )
    capped = client.post("/heatmap/check", json={
        "game_token": token, "index": source,
        "player_id": player_id(controlled_player),
    }).get_json()
    assert capped["reheatScore"] == 1 and capped["moveScore"] == 2
    assert app.heatmap_games[token]["heated"][reheated[0]] == 5

    game = app.heatmap_games[token]
    game["heated"] = {
        index: 1 for index in range(31)
        if index not in {source, app.HEATMAP_SCORE_INDEX}
    }
    completion = client.post("/heatmap/check", json={
        "game_token": token, "index": source,
        "player_id": player_id(controlled_player),
    }).get_json()
    assert completion["finished"]
    assert completion["heated_count"] == 30
    assert completion["ad_break"]["eligible"] is True
    assert completion["ad_break"]["game_mode"] == "heatmap"

    css = client.get("/static/heatmap.css").data.decode("utf-8")
    js = client.get("/static/heatmap.js").data.decode("utf-8")
    assert all(f"combo-level-{level}" in css for level in range(1, 6))
    assert "heated.has(index)" in js
    assert "reheat-pulse" in css and "data.reheated" in js
    assert "showWrongFeedback" in js and "score-penalty-feedback" in css
    assert "data.totalScore ?? data.score" in js
    assert "heat-ads-1" in html
    assert "scorePenaltyFeedback" in html
    assert "modal.getAnimations({subtree: true})" in js
    assert "afterClose" in js and "showWrongFeedback(penalty)" in js
    wrong_branch = js.index("if (data.accepted && data.correct === false)")
    close_call = js.index("closeModal({", wrong_branch)
    score_update = js.index('document.getElementById("scoreValue").textContent = newScore', close_call)
    assert close_call < score_update
    assert "animateHeatFlowBetweenHexes" in js
    assert "getBoundingClientRect()" in js and "Math.atan2" in js
    assert 'document.querySelectorAll(".heat-flow-line")' in js
    assert "index !== heatmapData.scoreIndex" in js
    assert "heat-source-pulse" in css and "heat-target-impact" in css
    assert "heat-reheat-impact" in css and "heat-flow-line" in css
    assert "animateHeatmapMove" not in client.get("/static/game.js").data.decode("utf-8")
    assert 'class="combo-legend"' not in html
    assert 'id="helpButton"' in html and '>?</button>' in html
    assert 'id="helpModal"' in html and "NASIL OYNANIR?" in html
    assert 'id="closeHelpModal"' in html and 'id="helpModalBackdrop"' in html
    assert 'class="help-color-scale"' in html
    assert all(rule in html for rule in (
        "BOŞ PETEĞİ SEÇ", "FUTBOLCUYU BUL", "BAĞLANTILARI YAKALA",
        "KOMBO YAP", "REHEAT", "YANLIŞ CEVAP", "AMAÇ",
    ))
    assert 'addEventListener("click", openHelpModal)' in js
    assert js.count('addEventListener("click", closeHelpModal)') == 2
    help_open = js[js.index("function openHelpModal"):js.index("function closeHelpModal")]
    assert "fetch(" not in help_open and "selectedIndex" not in help_open
    assert "window.location.reload()" in js
    assert 'href="/"' in html

    print({
        "route": True, "cells_30_plus_1": True, "center_score": True,
        "unique_and_answered": True, "player_search": True,
        "combos_1_to_4": True, "heated_replay_blocked": True,
        "wrong_answer_penalty": True, "wrong_answer_state_unchanged": True,
        "direct_neighbors_only": True,
        "score_cell_blocked": True, "completion_at_30": True,
        "combo_classes": True, "reheat_scoring": True,
        "reheat_direct_only": True, "heat_level_cap": True,
        "restart_and_home": True,
    })


if __name__ == "__main__":
    main()
