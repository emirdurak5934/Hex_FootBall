import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json
import os

from config import PLAYERS_FILE


def load_players():
    """players.json dosyasındaki oyuncuları yükler."""

    if not os.path.exists(PLAYERS_FILE):
        return []

    with open(PLAYERS_FILE, "r", encoding="utf-8") as file:
        try:
            data = json.load(file)

            if isinstance(data, list):
                return data

            return []

        except json.JSONDecodeError:
            return []


def save_players(players):
    """Oyuncuları players.json dosyasına kaydeder."""

    os.makedirs(os.path.dirname(PLAYERS_FILE), exist_ok=True)

    with open(PLAYERS_FILE, "w", encoding="utf-8") as file:
        json.dump(
            players,
            file,
            ensure_ascii=False,
            indent=4
        )


def find_player(player_id):
    """ID ile oyuncu bulur."""

    players = load_players()

    for player in players:
        if player.get("id") == player_id:
            return player

    return None


def player_exists(player_id):
    """Oyuncu daha önce kayıtlı mı kontrol eder."""

    return find_player(player_id) is not None


def add_player(player):
    """Yeni oyuncuyu veritabanına ekler."""

    required_fields = [
        "id",
        "name",
        "birthDate",
        "nationality",
        "positions",
        "clubs",
        "trophies"
    ]

    for field in required_fields:
        if field not in player:
            print(f"Eksik bilgi: {field}")
            return False

    players = load_players()

    for current_player in players:
        if current_player.get("id") == player["id"]:
            print(f"{player['name']} zaten kayıtlı.")
            return False

    players.append(player)
    save_players(players)

    print(f"{player['name']} başarıyla eklendi.")
    return True


def update_player(player_id, updates):
    """Oyuncunun belirli bilgilerini günceller."""

    players = load_players()

    for player in players:
        if player.get("id") == player_id:

            player.update(updates)

            save_players(players)

            print(f"{player['name']} güncellendi.")
            return True

    print("Oyuncu bulunamadı.")
    return False


def delete_player(player_id):
    """Oyuncuyu veritabanından siler."""

    players = load_players()

    new_players = [
        player
        for player in players
        if player.get("id") != player_id
    ]

    if len(new_players) == len(players):
        print("Oyuncu bulunamadı.")
        return False

    save_players(new_players)

    print("Oyuncu silindi.")
    return True


def search_players(
    name=None,
    nationality=None,
    position=None,
    club=None,
    trophy=None
):
    """Oyuncuları verilen kriterlere göre arar."""

    players = load_players()
    results = []

    for player in players:

        if name:
            player_name = player.get("name", "").lower()

            if name.lower() not in player_name:
                continue

        if nationality:
            player_nationality = player.get(
                "nationality",
                ""
            ).lower()

            if nationality.lower() != player_nationality:
                continue

        if position:
            positions = [
                p.lower()
                for p in player.get("positions", [])
            ]

            if position.lower() not in positions:
                continue

        if club:
            clubs = [
                c.lower()
                for c in player.get("clubs", [])
            ]

            if club.lower() not in clubs:
                continue

        if trophy:
            trophies = [
                t.get("name", "").lower()
                for t in player.get("trophies", [])
            ]

            if trophy.lower() not in trophies:
                continue

        results.append(player)

    return results
from config import PROCESSED_TEAMS_FILE, LOG_FILE


def load_processed_teams():
    if not os.path.exists(PROCESSED_TEAMS_FILE):
        return []

    with open(PROCESSED_TEAMS_FILE, "r", encoding="utf-8") as file:
        try:
            data = json.load(file)

            if isinstance(data, list):
                return data

            return []

        except json.JSONDecodeError:
            return []


def save_processed_teams(teams):
    with open(PROCESSED_TEAMS_FILE, "w", encoding="utf-8") as file:
        json.dump(
            teams,
            file,
            ensure_ascii=False,
            indent=4
        )


def mark_team_processed(team_name):
    teams = load_processed_teams()

    if team_name not in teams:
        teams.append(team_name)
        save_processed_teams(teams)


def team_is_processed(team_name):
    teams = load_processed_teams()
    return team_name in teams


def write_log(message):
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(message + "\n")
def merge_player(player_id, new_data):
    players = load_players()

    for player in players:
        if player.get("id") == player_id:

            for field in ["name", "birthDate", "nationality"]:
                if new_data.get(field):
                    player[field] = new_data[field]

            for field in ["positions", "clubs"]:
                old_values = player.get(field, [])
                new_values = new_data.get(field, [])

                merged = []

                for value in old_values + new_values:
                    if value not in merged:
                        merged.append(value)

                player[field] = merged

            if new_data.get("trophies"):
                trophy_map = {
                    trophy["name"]: trophy
                    for trophy in player.get("trophies", [])
                }

                for trophy in new_data["trophies"]:
                    trophy_map[trophy["name"]] = trophy

                player["trophies"] = list(trophy_map.values())

            save_players(players)

            print(f"{player['name']} güncellendi.")
            return True

    print(f"Oyuncu bulunamadı: {player_id}")
    return False