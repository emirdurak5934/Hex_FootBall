import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Regression tests for career-club based league matching."""

import app


def one(name):
    matches = app.find_players_by_name(name)
    assert matches, f"Oyuncu bulunamadı: {name}"
    return matches[0]


def league(value):
    return {"type": "league", "value": value, "label": value, "image": ""}


def main():
    ozan = one("Ozan Kabak")
    assert app.matches_condition(ozan, league("Bundesliga"))
    assert app.matches_condition(ozan, league("Premier League"))
    assert not app.matches_condition(ozan, league("La Liga"))

    other_bundesliga_player = one("Wout Weghorst")
    assert app.matches_condition(other_bundesliga_player, league("Bundesliga"))
    never_bundesliga = one("Lionel Messi")
    assert not app.matches_condition(never_bundesliga, league("Bundesliga"))

    assert one("ozan kabak")["id"] == ozan["id"]
    assert one("  Ozan Kabak  ")["id"] == ozan["id"]

    client = app.app.test_client()
    token, game = app.create_heatmap_game()
    game["cells"][0] = league("Bundesliga")
    response = client.post("/heatmap/check", json={
        "game_token": token, "index": 0, "player_id": ozan["id"],
    })
    assert response.status_code == 200 and response.get_json()["correct"]

    print({
        "ozan_bundesliga": True, "ozan_premier_league": True,
        "ozan_la_liga_false": True, "other_bundesliga_player": True,
        "non_bundesliga_player_false": True, "name_normalization": True,
        "heatmap_endpoint": True,
    })


if __name__ == "__main__":
    main()
