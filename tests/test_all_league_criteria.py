import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Focused league matching tests using first-team and safe alias variants."""

import app


CASES = {
    "Premier League": {
        "major": "Liverpool F.C.", "other": "Brentford", "historic": "Oldham Athletic",
        "official": "Manchester United F.C.", "short": "Wolves",
    },
    "La Liga": {
        "major": "Real Madrid CF", "other": "Getafe", "historic": "Compostela",
        "official": "RCD Espanyol de Barcelona", "short": "FC Barcelona",
    },
    "Serie A": {
        "major": "Juventus FC", "other": "Sassuolo", "historic": "Chievo Verona",
        "official": "FC Internazionale Milano", "short": "Milan",
    },
    "Bundesliga": {
        "major": "FC Bayern München", "other": "TSG 1899 Hoffenheim", "historic": "KFC Uerdingen 05",
        "official": "FC Schalke 04", "short": "Stuttgart",
    },
    "Süper Lig": {
        "major": "Galatasaray S.K.", "other": "Sivasspor", "historic": "Zeytinburnuspor",
        "official": "Beşiktaş J.K. (Football)", "short": "Fenerbahce",
    },
}


def condition(league):
    return {"type": "league", "value": league}


def synthetic(club):
    return {"clubs": [club]}


def main():
    actual = {item["value"] for item in app.ALL_CONDITIONS if item["type"] == "league"}
    assert actual == set(CASES)
    for league, cases in CASES.items():
        for key in ("major", "other", "historic", "official", "short"):
            assert app.matches_condition(synthetic(cases[key]), condition(league)), (league, key)
        assert not app.matches_condition(synthetic("Arsenal de Sarandí"), condition(league))
        assert not app.matches_condition(synthetic("Paris Saint-Germain"), condition(league))
        assert not app.matches_condition(synthetic(f"{cases['major']} U21"), condition(league))
        assert not app.matches_condition(synthetic(f"{cases['major']} Women"), condition(league))
    ozan = app.find_players_by_name("Ozan Kabak")[0]
    assert app.matches_condition(ozan, condition("Bundesliga"))
    assert app.matches_condition(ozan, condition("Premier League"))
    assert not app.matches_condition(ozan, condition("La Liga"))
    print({league: "PASS" for league in CASES} | {"ozan_regression": "PASS"})


if __name__ == "__main__":
    main()
