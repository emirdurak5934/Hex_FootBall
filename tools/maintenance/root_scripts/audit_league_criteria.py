import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Development-only audit for league criterion coverage.

Usage: .venv/Scripts/python.exe audit_league_criteria.py
"""

import json
from collections import Counter, defaultdict

import app
from league_clubs import LEGACY_LEAGUE_CLUBS, LEAGUE_CLUB_ALIASES


def accepted_values(clubs):
    values = set()
    for club in clubs:
        canonical = app.normalize(club)
        values.update(app.CLUB_ACCEPTED_VALUES.get(canonical, {canonical}))
    return values


def main():
    actual_leagues = sorted({
        condition["value"] for condition in app.ALL_CONDITIONS
        if condition["type"] == "league"
    })
    alias_owners = defaultdict(set)
    league_values = {}
    for league in actual_leagues:
        values = set()
        for canonical, aliases in LEAGUE_CLUB_ALIASES[league].items():
            canonical_normalized = app.normalize(canonical)
            values.update(app.CLUB_ACCEPTED_VALUES.get(canonical_normalized, {canonical_normalized}))
            for name in aliases:
                normalized = app.normalize(name)
                values.add(normalized)
                alias_owners[normalized].add(league)
            for normalized in values:
                alias_owners[normalized].add(league)
        league_values[league] = values

    report = {"leagues": {}, "conflicting_aliases": {}, "unmapped_clubs": []}
    all_mapped = set().union(*league_values.values())
    unmapped = Counter()
    for player in app.players:
        for club in app.get_club_names(player):
            normalized = app.normalize(club)
            if normalized not in all_mapped:
                unmapped[club] += 1

    for league in actual_leagues:
        old_values = accepted_values(LEGACY_LEAGUE_CLUBS[league])
        new_values = league_values[league]
        old_players = set()
        new_players = set()
        for player in app.players:
            player_id = str(player.get("id", ""))
            clubs = {app.normalize(club) for club in app.get_club_names(player)}
            if clubs & old_values:
                old_players.add(player_id)
            if clubs & new_values:
                new_players.add(player_id)
        report["leagues"][league] = {
            "canonical_clubs": len(LEAGUE_CLUB_ALIASES[league]),
            "unique_names_and_aliases": len(new_values),
            "old_players": len(old_players),
            "new_players": len(new_players),
            "added_players": len(new_players - old_players),
        }
    report["conflicting_aliases"] = {
        alias: sorted(owners) for alias, owners in alias_owners.items() if len(owners) > 1
    }
    report["unmapped_clubs"] = unmapped.most_common(30)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
