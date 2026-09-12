"""Indexed criterion and board engine for Tiki Taka Toe."""

from __future__ import annotations

import random
import re
import unicodedata
from collections import defaultdict


DEFAULT_CLUBS = [
    "Arsenal", "Liverpool", "Manchester United", "Manchester City",
    "Tottenham Hotspur", "Newcastle United", "Chelsea", "Sevilla",
    "Atletico Madrid", "Barcelona", "Real Madrid", "AC Milan",
    "Inter Milan", "AS Roma", "Napoli", "Juventus",
    "Paris Saint-Germain", "AS Monaco", "Bayern Munich",
    "Borussia Dortmund", "Benfica", "Sporting CP", "Ajax",
    "Galatasaray", "Fenerbahce", "Besiktas", "Trabzonspor",
]

DEFAULT_NATIONALITIES = [
    "England", "Spain", "Portugal", "Netherlands", "Italy", "France",
    "Germany", "Turkey", "Brazil", "Argentina",
]

DEFAULT_TROPHIES = [
    "English Champion", "Turkish Champion", "Spanish Champion",
    "Italian Champion", "German Champion", "French Champion",
    "Champions League", "Europa League", "World Cup",
    "European Championship", "Copa America", "Ballon d'Or",
    "FA Cup", "Coppa Italia", "Copa del Rey",
]


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


class TikiTakaEngine:
    """Build indexes once and generate fully playable 3x3 boards."""

    def __init__(self, players, club_aliases=None, country_aliases=None,
                 trophy_aliases=None, rng=None):
        self.players = players
        self.rng = rng or random.Random()
        self.players_by_id = {
            str(player.get("id", "")).strip(): player
            for player in players if str(player.get("id", "")).strip()
        }
        self.aliases = {
            "club": self._alias_map(club_aliases or {}),
            "nationality": self._alias_map(country_aliases or {}),
            "trophy": self._alias_map(trophy_aliases or {}),
        }
        self.indexes = {kind: defaultdict(set) for kind in self.aliases}
        self._build_indexes()
        self.pools = {
            "club": self._available("club", DEFAULT_CLUBS),
            "nationality": self._available("nationality", DEFAULT_NATIONALITIES),
            "trophy": self._available("trophy", DEFAULT_TROPHIES),
        }

    @staticmethod
    def _alias_map(groups):
        result = {}
        for canonical, aliases in groups.items():
            canonical_key = normalize(canonical)
            for value in [canonical, *aliases]:
                result[normalize(value)] = canonical_key
        return result

    def _canonical(self, kind, value):
        cleaned = normalize(value)
        if kind == "trophy":
            cleaned = re.sub(r"^\d+x\s+", "", cleaned)
        return self.aliases[kind].get(cleaned, cleaned)

    def _build_indexes(self):
        for player in self.players:
            player_id = str(player.get("id", "")).strip()
            if not player_id:
                continue
            for club in player.get("clubs", []):
                value = club.get("name", "") if isinstance(club, dict) else club
                if value:
                    self.indexes["club"][self._canonical("club", value)].add(player_id)
            nationality = player.get("nationality", "")
            if nationality:
                self.indexes["nationality"][self._canonical("nationality", nationality)].add(player_id)
            for trophy in player.get("trophies", []):
                if isinstance(trophy, dict):
                    value = trophy.get("name") or trophy.get("title") or trophy.get("trophy")
                else:
                    value = trophy
                if value:
                    self.indexes["trophy"][self._canonical("trophy", value)].add(player_id)

    def _available(self, kind, labels):
        return [self.criterion(kind, label) for label in labels
                if self.answers(self.criterion(kind, label))]

    def criterion(self, kind, label):
        return {"type": kind, "label": label, "key": self._canonical(kind, label)}

    def answers(self, criterion):
        return self.indexes.get(criterion["type"], {}).get(criterion["key"], set())

    def cell_answers(self, row, column):
        return self.answers(row) & self.answers(column)

    def player_matches(self, player_id, row, column):
        player_id = str(player_id).strip()
        return player_id in self.cell_answers(row, column)

    @staticmethod
    def public_criterion(criterion):
        return {"type": criterion["type"], "label": criterion["label"]}

    def validate_board(self, rows, columns, minimum_answers=1):
        identities = {(item["type"], item["key"]) for item in rows + columns}
        counts = [len(self.cell_answers(row, column))
                  for row in rows for column in columns]
        return len(identities) == 6 and min(counts, default=0) >= minimum_answers, counts

    def generate_board(self, previous=None, minimum_answers=2, max_attempts=3000):
        previous_signature = None
        if previous:
            previous_signature = tuple(
                (item["type"], item.get("key") or self._canonical(item["type"], item["label"]))
                for item in previous["rows"] + previous["columns"]
            )
        column_patterns = [
            ("club", "nationality", "trophy"),
            ("club", "club", "nationality"),
            ("club", "club", "trophy"),
        ]
        for required in (minimum_answers, 1):
            for _ in range(max_attempts):
                rows = self.rng.sample(self.pools["club"], 3)
                pattern = self.rng.choice(column_patterns)
                columns = []
                for kind in pattern:
                    choices = [item for item in self.pools[kind] if item not in columns]
                    columns.append(self.rng.choice(choices))
                valid, counts = self.validate_board(rows, columns, required)
                signature = tuple((item["type"], item["key"]) for item in rows + columns)
                if valid and signature != previous_signature:
                    return {
                        "rows": rows, "columns": columns,
                        "answer_counts": counts,
                    }
        raise RuntimeError("Oynanabilir Tiki Taka Toe tahtasi uretilemedi.")

