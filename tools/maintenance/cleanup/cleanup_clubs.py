import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Remove only high-confidence national-team values from clubs arrays."""

from database_cleanup_utils import (
    DATA_DIR,
    PLAYERS_FILE,
    create_backup,
    is_high_confidence_national_team,
    load_players,
    write_json,
)


def main() -> None:
    players = load_players()
    changed_players = 0
    removed_entries = 0
    proposed_removals = []
    for player in players:
        clubs = player.get("clubs")
        if not isinstance(clubs, list):
            continue
        removals = [club for club in clubs if is_high_confidence_national_team(club)]
        retained = [club for club in clubs if not is_high_confidence_national_team(club)]
        proposed_removals.extend(
            {
                "id": player.get("id"),
                "name": player.get("name"),
                "suggested_removal": club,
            }
            for club in removals
        )
        removed = len(clubs) - len(retained)
        if removed:
            player["clubs"] = retained
            changed_players += 1
            removed_entries += removed
    if not changed_players:
        print("No high-confidence national-team club entries found; no write was made.")
        return
    # Persist the dry-run detail before mutating players.json.
    write_json(DATA_DIR / "national_teams_inside_clubs.json", proposed_removals)
    backup = create_backup("club_cleanup")
    write_json(PLAYERS_FILE, players)
    print(f"Backup: {backup}")
    print(f"Players changed: {changed_players}")
    print(f"National-team entries removed: {removed_entries}")


if __name__ == "__main__":
    main()
