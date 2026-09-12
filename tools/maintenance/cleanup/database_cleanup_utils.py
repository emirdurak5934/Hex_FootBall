"""Shared, dependency-free helpers for safe players.json maintenance."""

from __future__ import annotations
import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)

import json
import os
import re
import shutil
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(PROJECT_ROOT)
DATA_DIR = PROJECT_ROOT / "data"
PLAYERS_FILE = DATA_DIR / "players.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_players() -> list[dict[str, Any]]:
    players = load_json(PLAYERS_FILE)
    if not isinstance(players, list):
        raise ValueError("data/players.json must contain a JSON array")
    if not all(isinstance(player, dict) for player in players):
        raise ValueError("Every players.json entry must be a JSON object")
    return players


def write_json(path: Path, value: Any) -> None:
    """Atomically write UTF-8 JSON and parse the result before replacing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        load_json(temporary_path)
        os.replace(temporary_path, path)
        load_json(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_backup(label: str) -> Path:
    backup = DATA_DIR / f"players_before_{label}_{timestamp()}.json"
    shutil.copy2(PLAYERS_FILE, backup)
    load_json(backup)
    return backup


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value).strip().casefold())
    return "".join(char for char in text if not unicodedata.combining(char))


def normalize_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_text(value))


def player_summary(player: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id", "name", "birthDate", "nationality", "positions", "clubs",
        "trophies",
    )
    return {key: player.get(key) for key in keys}


def comparison_for_group(players: Iterable[dict[str, Any]]) -> dict[str, str]:
    group = list(players)
    fields = ("name", "birthDate", "nationality", "positions", "clubs", "trophies")
    result: dict[str, str] = {}
    for field in fields:
        serialized = {
            json.dumps(player.get(field), ensure_ascii=False, sort_keys=True)
            for player in group
        }
        result[field] = "same" if len(serialized) == 1 else "different"
    return result


POSITION_MAP = {
    "goalkeeper": "Goalkeeper",
    "keeper": "Goalkeeper",
    "defender": "Defender",
    "full-back": "Defender",
    "full back": "Defender",
    "centre-back": "Defender",
    "centre back": "Defender",
    "center-back": "Defender",
    "center back": "Defender",
    "left-back": "Defender",
    "left back": "Defender",
    "right-back": "Defender",
    "right back": "Defender",
    "sweeper": "Defender",
    "back": "Defender",
    "midfielder": "Midfielder",
    "central midfield": "Midfielder",
    "central midfielder": "Midfielder",
    "defensive midfield": "Midfielder",
    "defensive midfielder": "Midfielder",
    "attacking midfield": "Midfielder",
    "attacking midfielder": "Midfielder",
    "left midfield": "Midfielder",
    "right midfield": "Midfielder",
    "wing half": "Midfielder",
    "forward": "Forward",
    "attacker": "Forward",
    "inside forward": "Forward",
    "centre-forward": "Forward",
    "centre forward": "Forward",
    "center-forward": "Forward",
    "center forward": "Forward",
    "striker": "Forward",
    "left winger": "Forward",
    "right winger": "Forward",
    "winger": "Forward",
    "second striker": "Forward",
}
VALID_POSITIONS = {"Goalkeeper", "Defender", "Midfielder", "Forward"}


def canonical_position(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if stripped in VALID_POSITIONS:
        return stripped
    return POSITION_MAP.get(normalize_text(stripped))


NATIONAL_TEAM_PATTERNS = (
    re.compile(r"\bnational\b.*\bteam\b", re.IGNORECASE),
    re.compile(r"\bolympic\s+(?:association\s+)?football\s+team\b", re.IGNORECASE),
)


def is_high_confidence_national_team(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return any(pattern.search(text) for pattern in NATIONAL_TEAM_PATTERNS)


TROPHY_COUNT_PREFIX = re.compile(r"^\s*\d{1,2}x\s+", re.IGNORECASE)


def trophy_name(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("name") or item.get("title") or item.get("trophy") or "")
    return ""


def canonical_trophy_name(value: Any) -> str:
    return TROPHY_COUNT_PREFIX.sub("", str(value).strip())


def trophy_key(value: Any) -> str:
    return normalize_text(canonical_trophy_name(value))
