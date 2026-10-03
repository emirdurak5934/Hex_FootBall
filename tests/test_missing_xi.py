import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Kayip 11 full-screen Wordle, free guesses and server state tests."""

import re

import app


def post_guess(client, token, match_id, slot, guess):
    return client.post("/missing-xi/guess", json={
        "game_token": token, "match_id": match_id, "slot": slot, "guess": guess,
    })


def main():
    client = app.app.test_client()
    page = client.get("/missing-xi")
    html = page.data.decode("utf-8")
    script = open("static/missing_xi.js", encoding="utf-8").read()
    css = open("static/missing_xi_wordle.css", encoding="utf-8").read()
    assert page.status_code == 200
    assert len(re.findall(r'class="player-slot(?: is-goalkeeper)?"', html)) == 11
    assert html.count("mini-shirt") == 11
    assert html.count("answer-length") == 11
    assert 'class="player-slot is-goalkeeper"' in html
    assert 'id="fieldView"' in html and 'id="wordleView"' in html
    assert 'id="answerModal"' not in html and "wordle-grid" in html
    assert len(re.findall(r'class="keyboard-row"', html)) == 3
    assert "BACKSPACE" in script and "ENTER" in script and "keydown" in script
    assert "/search_players" not in script and "player_id" not in script
    assert "for (let rowIndex = 0; rowIndex < 6" in script
    assert "overflow:hidden" in css and "sideRank" in script

    token = re.search(r'"gameToken":\s*"([^"]+)"', html).group(1)
    game = app.missing_xi_games[token]
    match = next(item for item in app.missing_xi_matches if item["id"] == game["match_id"])
    assert all(item["name"] not in html for item in match["lineup"])
    assert all(item["answer"] not in html for item in match["lineup"])
    assert all(str(item.get("answer", "")).strip() for item in match["lineup"])
    assert all(isinstance(item.get("shirt_number"), int) for item in match["lineup"])
    for item in match["lineup"]:
        assert f">{item['shirt_number']}</strong>" in html
        assert len(app.missing_xi_wordle_name(item["answer"])) > 0
    positions = {item["position"] for item in match["lineup"]}
    assert "LB" in positions and "RB" in positions

    expected_numbers = {
        "ucl-final-2011-barcelona": [1, 2, 3, 14, 22, 16, 6, 8, 17, 10, 7],
        "ucl-final-2009-barcelona": [1, 5, 3, 24, 16, 28, 6, 8, 10, 9, 14],
        "ucl-final-2018-real-madrid": [1, 2, 5, 4, 12, 14, 10, 8, 22, 9, 7],
    }
    for test_match in app.missing_xi_matches:
        if test_match["id"] not in expected_numbers:
            continue
        ordered = sorted(test_match["lineup"], key=lambda item: item["slot"])
        assert [item["shirt_number"] for item in ordered] == expected_numbers[test_match["id"]]

    assert app.missing_xi_wordle_name("José O'Cearuill-Sr.") == "JOSEOCEARUILLSR"
    assert app.missing_xi_wordle_feedback("APPLE", "ALLEY") == [
        "green", "yellow", "gray", "yellow", "gray",
    ]
    assert app.missing_xi_wordle_feedback("ABACA", "AAAAA") == [
        "green", "gray", "green", "gray", "green",
    ]

    first = match["lineup"][0]
    target = app.missing_xi_wordle_name(first["answer"])
    incomplete = post_guess(client, token, match["id"], 0, target[:-1])
    assert incomplete.status_code == 400
    assert incomplete.get_json()["attempt"] == 0 and game["attempts"] == {}

    wrong = "X" * len(target)
    if wrong == target:
        wrong = "Y" * len(target)
    for attempt in range(1, 7):
        response = post_guess(client, token, match["id"], 0, wrong)
        result = response.get_json()
        assert response.status_code == 200 and not result["correct"]
        assert result["attempt"] == attempt and result["errors"] == attempt
        assert result["guess"] == wrong
    assert result["exhausted"] and game["slot_states"][0] == "missed"
    assert post_guess(client, token, match["id"], 0, target).status_code == 409

    second = match["lineup"][1]
    second_target = app.missing_xi_wordle_name(second["answer"])
    found = post_guess(client, token, match["id"], 1, second_target).get_json()
    assert found["correct"] and found["player_name"] == second["answer"]
    assert found["correct_count"] == 1 and found["errors"] == 6
    assert post_guess(client, token, match["id"], 1, second_target).status_code == 409

    for item in sorted(match["lineup"], key=lambda value: value["slot"])[2:]:
        guess = app.missing_xi_wordle_name(item["answer"])
        result = post_guess(client, token, match["id"], item["slot"], guess).get_json()
        assert result["accepted"] and result["correct"]
    assert result["finished"] and result["correct_count"] == 10
    assert result["missed_count"] == 1 and result["errors"] == 6
    assert result["ad_break"]["eligible"] is True
    assert result["ad_break"]["game_mode"] == "missing_xi"

    new_page = client.get("/missing-xi")
    new_token = re.search(r'"gameToken":\s*"([^"]+)"', new_page.data.decode("utf-8")).group(1)
    assert new_token != token and app.missing_xi_games[new_token]["attempts"] == {}
    print("Kayip 11 full-screen Wordle tests passed")


if __name__ == "__main__":
    main()
