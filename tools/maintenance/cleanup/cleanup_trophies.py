import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Canonicalize trophy names without changing string/dict representation."""

from datetime import datetime

from database_cleanup_utils import (
    DATA_DIR,
    PLAYERS_FILE,
    canonical_trophy_name,
    create_backup,
    load_players,
    normalize_text,
    trophy_key,
    trophy_name,
    write_json,
)


def updated_item(item, cleaned_name):
    if isinstance(item, str):
        return cleaned_name
    if isinstance(item, dict):
        result = dict(item)
        for key in ("name", "title", "trophy"):
            if key in result:
                result[key] = cleaned_name
                break
        return result
    return item


def main() -> None:
    players = load_players()
    changed_players = 0
    all_titles_removed = 0
    duplicate_trophies_removed = 0
    count_prefixes_removed = 0
    invalid_items_untouched = 0
    for player in players:
        trophies = player.get("trophies")
        if not isinstance(trophies, list):
            continue
        cleaned = []
        seen = set()
        changed = False
        for item in trophies:
            name = trophy_name(item)
            if not name:
                cleaned.append(item)
                invalid_items_untouched += 1
                continue
            if normalize_text(name) == "all titles":
                all_titles_removed += 1
                changed = True
                continue
            canonical = canonical_trophy_name(name)
            if canonical != name:
                count_prefixes_removed += 1
                changed = True
            key = trophy_key(canonical)
            if key in seen:
                duplicate_trophies_removed += 1
                changed = True
                continue
            seen.add(key)
            cleaned.append(updated_item(item, canonical))
        if changed:
            player["trophies"] = cleaned
            changed_players += 1

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "players_changed": changed_players,
        "all_titles_removed": all_titles_removed,
        "duplicate_trophies_removed": duplicate_trophies_removed,
        "count_prefixes_removed": count_prefixes_removed,
        "invalid_items_untouched": invalid_items_untouched,
    }
    if changed_players:
        backup = create_backup("trophy_cleanup")
        write_json(PLAYERS_FILE, players)
        report["backup"] = str(backup)
    write_json(DATA_DIR / "trophy_cleanup_report.json", report)
    print(f"Players changed: {changed_players}")
    print(f"All titles removed: {all_titles_removed}")
    print(f"Duplicate trophies removed: {duplicate_trophies_removed}")
    print(f"Count prefixes removed: {count_prefixes_removed}")
    if changed_players:
        print(f"Backup: {report['backup']}")


if __name__ == "__main__":
    main()
