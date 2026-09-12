import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Normalize only explicitly mapped football positions."""

from database_cleanup_utils import (
    PLAYERS_FILE,
    canonical_position,
    create_backup,
    load_players,
    write_json,
)


def main() -> None:
    players = load_players()
    changed_players = 0
    changed_values = 0
    for player in players:
        positions = player.get("positions")
        if not isinstance(positions, list):
            continue
        normalized = []
        changed = False
        for position in positions:
            canonical = canonical_position(position)
            replacement = canonical if canonical is not None else position
            if replacement != position:
                changed = True
                changed_values += 1
            if replacement not in normalized:
                normalized.append(replacement)
            elif replacement in normalized and replacement != position:
                changed = True
        if changed:
            player["positions"] = normalized
            changed_players += 1
    if not changed_players:
        print("No position changes were needed; no backup or write was made.")
        return
    backup = create_backup("position_cleanup")
    write_json(PLAYERS_FILE, players)
    print(f"Backup: {backup}")
    print(f"Players changed: {changed_players}")
    print(f"Position values normalized: {changed_values}")


if __name__ == "__main__":
    main()
