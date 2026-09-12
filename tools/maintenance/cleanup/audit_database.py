"""Read-only audit for data/players.json; writes reports, never players.json."""

from __future__ import annotations
import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)

import re
from collections import Counter, defaultdict
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any

from database_cleanup_utils import (
    DATA_DIR,
    VALID_POSITIONS,
    canonical_position,
    canonical_trophy_name,
    comparison_for_group,
    is_high_confidence_national_team,
    load_players,
    normalize_name,
    normalize_text,
    player_summary,
    trophy_key,
    trophy_name,
    write_json,
)


REQUIRED_FIELDS = ("id", "name", "birthDate", "nationality", "positions", "clubs", "trophies")
QID_PATTERN = re.compile(r"^Q\d+$", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://|www\.", re.IGNORECASE)
STAT_PATTERN = re.compile(r"caps\s*/\s*goals|^\s*[\d\s/.:+-]+\s*$", re.IGNORECASE)
TEAM_NATIONALITY_PATTERN = re.compile(
    r"(?:\bF\.?C\.?\b|\bteam\b|football club|association football)", re.IGNORECASE
)


def nationality_reasons(value: Any) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return ["missing"]
    reasons = []
    if URL_PATTERN.search(value):
        reasons.append("contains_url")
    if "caps/goals" in value.casefold():
        reasons.append("contains_caps_goals")
    if STAT_PATTERN.fullmatch(value):
        reasons.append("statistics_like")
    if TEAM_NATIONALITY_PATTERN.search(value):
        reasons.append("club_or_team_like")
    return reasons


def birthdate_issue(value: Any) -> tuple[str, str] | None:
    if value is None or not isinstance(value, str) or not value.strip():
        return "missing", "Birth date is empty or absent"
    if URL_PATTERN.search(value):
        return "invalid", "Birth date contains a URL"
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return "invalid", "Birth date is not a valid YYYY-MM-DD date"
    if parsed > date.today():
        return "invalid", "Birth date is in the future"
    if parsed.year <= 1801 or value.endswith("-01-01") and parsed.year < 1900:
        return "suspicious", "Possible historical placeholder date"
    return None


def duplicate_group(kind: str, key: str, group: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "match_type": kind,
        "match_value": key,
        "players": [player_summary(player) for player in group],
        "field_comparison": comparison_for_group(group),
    }


def build_duplicate_report(players: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, int]:
    groups: list[dict[str, Any]] = []
    seen_signatures: set[tuple[str, ...]] = set()

    def add_groups(kind: str, grouped: dict[str, list[dict[str, Any]]]) -> None:
        for key, group in sorted(grouped.items()):
            if not key or len(group) < 2:
                continue
            signature = tuple(sorted(str(player.get("id", "")) for player in group))
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            groups.append(duplicate_group(kind, key, group))

    by_tm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_birth: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for player in players:
        transfermarkt_id = str(player.get("transfermarkt_id", "")).strip()
        if transfermarkt_id:
            by_tm[transfermarkt_id].append(player)
        name_key = normalize_name(player.get("name", ""))
        if name_key:
            by_name[name_key].append(player)
        birthdate = str(player.get("birthDate", "")).strip()
        if birthdate:
            by_birth[birthdate].append(player)

    duplicate_tm_count = sum(len(group) > 1 for group in by_tm.values())
    duplicate_name_count = sum(len(group) > 1 for group in by_name.values())
    add_groups("transfermarkt_id", by_tm)
    add_groups("normalized_name", by_name)

    # Compare only players sharing a birth date; this avoids unsafe global fuzzy matching.
    for birthdate, candidates in by_birth.items():
        if len(candidates) < 2 or len(candidates) > 100:
            continue
        parent = list(range(len(candidates)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for left in range(len(candidates)):
            left_name = normalize_name(candidates[left].get("name", ""))
            for right in range(left + 1, len(candidates)):
                right_name = normalize_name(candidates[right].get("name", ""))
                if not left_name or not right_name:
                    continue
                similarity = SequenceMatcher(None, left_name, right_name).ratio()
                if similarity >= 0.84:
                    union(left, right)
        fuzzy: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for index, player in enumerate(candidates):
            fuzzy[find(index)].append(player)
        for group in fuzzy.values():
            if len(group) < 2:
                continue
            signature = tuple(sorted(str(player.get("id", "")) for player in group))
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                groups.append(duplicate_group("birthdate_and_similar_name", birthdate, group))
    return groups, duplicate_tm_count, duplicate_name_count


def main() -> None:
    players = load_players()
    duplicates, duplicate_tm_count, duplicate_name_count = build_duplicate_report(players)
    invalid_nationalities = []
    invalid_birthdates = []
    invalid_names = []
    national_teams = []
    all_positions: Counter[str] = Counter()
    unmapped_positions: dict[str, list[dict[str, str]]] = defaultdict(list)
    missing = Counter()
    non_normalized_player_ids: set[str] = set()
    national_team_player_ids: set[str] = set()
    players_with_all_titles = 0
    players_with_duplicate_trophies = 0

    duplicate_tm_names: dict[str, set[str]] = defaultdict(set)
    for player in players:
        tm_id = str(player.get("transfermarkt_id", "")).strip()
        if tm_id:
            duplicate_tm_names[tm_id].add(str(player.get("name", "")))

    for player in players:
        player_id = str(player.get("id", ""))
        for field in REQUIRED_FIELDS:
            value = player.get(field)
            if field not in player or value is None or value == "" or value == []:
                missing[field] += 1

        reasons = nationality_reasons(player.get("nationality"))
        if reasons:
            invalid_nationalities.append({
                "id": player.get("id"), "name": player.get("name"),
                "nationality": player.get("nationality"), "reasons": reasons,
            })

        date_problem = birthdate_issue(player.get("birthDate"))
        if date_problem:
            status, reason = date_problem
            invalid_birthdates.append({
                "id": player.get("id"), "name": player.get("name"),
                "birthDate": player.get("birthDate"), "status": status,
                "reason": reason,
            })

        name = player.get("name")
        name_reasons = []
        if not isinstance(name, str) or not name.strip():
            name_reasons.append("missing")
        elif QID_PATTERN.fullmatch(name.strip()) or name.strip() == player_id:
            name_reasons.append("qid_or_id_placeholder")
        elif URL_PATTERN.search(name):
            name_reasons.append("contains_url")
        tm_id = str(player.get("transfermarkt_id", "")).strip()
        if tm_id and len(duplicate_tm_names[tm_id]) > 1:
            aliases = sorted(duplicate_tm_names[tm_id])
            if any(
                SequenceMatcher(None, normalize_name(name), normalize_name(alias)).ratio() >= 0.65
                for alias in aliases if alias != name
            ):
                name_reasons.append("possible_typo_or_alias_in_duplicate_transfermarkt_group")
        if name_reasons:
            invalid_names.append({
                "id": player.get("id"), "name": name,
                "transfermarkt_id": player.get("transfermarkt_id"),
                "reasons": name_reasons,
            })

        positions = player.get("positions")
        if isinstance(positions, list):
            for position in positions:
                all_positions[str(position)] += 1
                canonical = canonical_position(position)
                if canonical is None:
                    unmapped_positions[str(position)].append({"id": player_id, "name": str(name)})
                    non_normalized_player_ids.add(player_id)
                elif position not in VALID_POSITIONS:
                    non_normalized_player_ids.add(player_id)
        elif positions is not None:
            unmapped_positions[f"<invalid type: {type(positions).__name__}>"].append(
                {"id": player_id, "name": str(name)}
            )
            non_normalized_player_ids.add(player_id)

        clubs = player.get("clubs")
        if isinstance(clubs, list):
            for club in clubs:
                if is_high_confidence_national_team(club):
                    national_team_player_ids.add(player_id)
                    national_teams.append({
                        "id": player.get("id"), "name": name,
                        "suggested_removal": club,
                    })

        trophies = player.get("trophies")
        if isinstance(trophies, list):
            keys = []
            has_all_titles = False
            for trophy in trophies:
                current_name = trophy_name(trophy)
                if normalize_text(current_name) == "all titles":
                    has_all_titles = True
                    continue
                if current_name:
                    keys.append(trophy_key(current_name))
            players_with_all_titles += int(has_all_titles)
            players_with_duplicate_trophies += int(len(keys) != len(set(keys)))

    write_json(DATA_DIR / "database_issues.json", {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "note": "Potential duplicates only; no records were merged or deleted.",
        "duplicate_groups": duplicates,
    })
    write_json(DATA_DIR / "invalid_nationalities.json", invalid_nationalities)
    write_json(DATA_DIR / "invalid_birthdates.json", invalid_birthdates)
    write_json(DATA_DIR / "invalid_names.json", invalid_names)
    national_team_report = DATA_DIR / "national_teams_inside_clubs.json"
    # Preserve the cleanup dry-run evidence after a successful cleanup. A fresh
    # database (or one still containing matches) always gets a current report.
    if national_teams or not national_team_report.exists():
        write_json(national_team_report, national_teams)
    write_json(DATA_DIR / "unmapped_positions.json", {
        "all_position_values": dict(sorted(all_positions.items())),
        "unmapped": [
            {"value": value, "count": len(records), "players": records}
            for value, records in sorted(unmapped_positions.items())
        ],
    })

    invalid_birth_count = sum(item["status"] == "invalid" for item in invalid_birthdates)
    health = {
        "total_players": len(players),
        "missing_id": missing["id"],
        "missing_name": missing["name"],
        "missing_birthdate": missing["birthDate"],
        "missing_nationality": missing["nationality"],
        "missing_positions": missing["positions"],
        "missing_clubs": missing["clubs"],
        "missing_trophies": missing["trophies"],
        "invalid_birthdates": invalid_birth_count,
        "suspicious_birthdates": sum(item["status"] == "suspicious" for item in invalid_birthdates),
        "invalid_nationalities": sum("missing" not in item["reasons"] for item in invalid_nationalities),
        "duplicate_transfermarkt_ids": duplicate_tm_count,
        "duplicate_names": duplicate_name_count,
        "potential_duplicate_groups_total": len(duplicates),
        "players_with_national_teams_in_clubs": len(national_team_player_ids),
        "national_team_entries_inside_clubs": len(national_teams),
        "players_with_non_normalized_positions": len(non_normalized_player_ids),
        "players_with_all_titles": players_with_all_titles,
        "players_with_duplicate_trophies": players_with_duplicate_trophies,
    }
    write_json(DATA_DIR / "database_health_report.json", health)

    print("================================")
    print("DATABASE AUDIT")
    print("================================")
    print(f"Total players: {len(players)}")
    print(f"Duplicate Transfermarkt IDs: {duplicate_tm_count}")
    print(f"Duplicate names: {duplicate_name_count}")
    print(f"Invalid nationalities: {health['invalid_nationalities']}")
    print(f"Missing nationalities: {missing['nationality']}")
    print(f"Invalid birthdates: {invalid_birth_count}")
    print(f"Missing birthdates: {missing['birthDate']}")
    print(f"Missing positions: {missing['positions']}")
    print(f"Non-normalized positions: {len(non_normalized_player_ids)}")
    print(f"National-team entries inside clubs: {len(national_teams)}")
    print(f"All titles entries (players): {players_with_all_titles}")
    print(f"Duplicate trophy entries (players): {players_with_duplicate_trophies}")
    print("================================")


if __name__ == "__main__":
    main()
