import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import requests


# =========================================================
# WINDOWS UNICODE
# =========================================================

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# =========================================================
# AYARLAR
# =========================================================

PLAYERS_FILE = Path("data/players.json")
LOG_FILE = Path("data/logs.txt")

DEFAULT_LIMIT = 10

TIMEOUT = 15
MAX_RETRIES = 2
RETRY_WAIT = 2
REQUEST_DELAY = 0.5

API_BASE = "https://tmapi.transfermarkt.technology"


# =========================================================
# POSITION NORMALIZATION
# =========================================================

def normalize_position(raw_position):

    value = str(
        raw_position or ""
    ).strip().lower()

    value = (
        value
        .replace("–", "-")
        .replace("—", "-")
    )

    # GOALKEEPER
    if any(term in value for term in (
        "goalkeeper",
        "keeper",
    )):
        return "Goalkeeper"

    # DEFENDER
    if any(term in value for term in (
        "centre-back",
        "center-back",
        "central defender",
        "left-back",
        "right-back",
        "full-back",
        "fullback",
        "wing-back",
        "wing back",
        "sweeper",
        "stopper",
        "defender",
        "defence",
        "defense",
    )):
        return "Defender"

    # MIDFIELDER
    if any(term in value for term in (
        "defensive midfield",
        "central midfield",
        "attacking midfield",
        "left midfield",
        "right midfield",
        "wide midfield",
        "midfielder",
        "midfield",
        "playmaker",
        "wing half",
    )):
        return "Midfielder"

    # FORWARD
    if any(term in value for term in (
        "centre-forward",
        "center-forward",
        "left winger",
        "right winger",
        "winger",
        "second striker",
        "striker",
        "inside forward",
        "forward",
        "attacker",
        "attack",
        "offence",
        "offense",
    )):
        return "Forward"

    return ""


# =========================================================
# LOG
# =========================================================

def write_log(message):

    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    with LOG_FILE.open(
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            f"{timestamp} | {message}\n"
        )


# =========================================================
# JSON
# =========================================================

def load_players():

    with PLAYERS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        players = json.load(file)

    if not isinstance(players, list):
        raise ValueError(
            "players.json liste formatında değil."
        )

    return players


def save_players_atomic(players):

    descriptor, temp_path = tempfile.mkstemp(
        prefix="players.",
        suffix=".tmp",
        dir=PLAYERS_FILE.parent
    )

    try:

        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                players,
                file,
                ensure_ascii=False,
                indent=2
            )

            file.flush()
            os.fsync(file.fileno())

        with open(
            temp_path,
            "r",
            encoding="utf-8"
        ) as file:

            check = json.load(file)

        if not isinstance(check, list):
            raise ValueError(
                "Geçici JSON liste değil."
            )

        if len(check) != len(players):
            raise ValueError(
                "Oyuncu sayısı değişti."
            )

        os.replace(
            temp_path,
            PLAYERS_FILE
        )

    finally:

        if os.path.exists(temp_path):
            os.unlink(temp_path)


# =========================================================
# BACKUP
# =========================================================

def create_backup():

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_file = (
        PLAYERS_FILE.parent
        /
        f"players_before_positions_api_{timestamp}.json"
    )

    shutil.copy2(
        PLAYERS_FILE,
        backup_file
    )

    return backup_file


# =========================================================
# TM ID
# =========================================================

def get_transfermarkt_id(player):

    value = str(
        player.get(
            "transfermarkt_id",
            ""
        )
    ).strip()

    if re.fullmatch(r"\d+", value):
        return value

    player_id = str(
        player.get(
            "id",
            ""
        )
    ).strip()

    match = re.fullmatch(
        r"tm_missing_(\d+)",
        player_id
    )

    if match:
        return match.group(1)

    return ""


# =========================================================
# MEVCUT POSITIONS
# =========================================================

def get_existing_positions(player):

    positions = player.get(
        "positions"
    )

    if isinstance(positions, list):

        return [
            str(item).strip()
            for item in positions
            if str(item).strip()
        ]

    position = str(
        player.get(
            "position",
            ""
        )
    ).strip()

    if position:
        return [position]

    return []


# =========================================================
# API REQUEST
# =========================================================

def api_get(session, url):

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = session.get(
                url,
                timeout=TIMEOUT
            )

            if response.status_code in {
                429,
                500,
                502,
                503,
                504,
            }:

                last_error = (
                    f"HTTP {response.status_code}"
                )

                if attempt < MAX_RETRIES:

                    print(
                        f"API HTTP {response.status_code}. "
                        f"{RETRY_WAIT} saniye sonra tekrar..."
                    )

                    time.sleep(RETRY_WAIT)
                    continue

            # Endpoint bu oyuncuda yoksa direkt diğer endpoint'e geçsin
            if response.status_code == 404:
                return None

            response.raise_for_status()

            return response.json()

        except (
            requests.Timeout,
            requests.ConnectionError
        ) as error:

            last_error = str(error)

            if attempt < MAX_RETRIES:

                print(
                    f"API bağlantı hatası. "
                    f"{RETRY_WAIT} saniye sonra tekrar..."
                )

                time.sleep(RETRY_WAIT)
                continue

        except requests.RequestException as error:

            last_error = str(error)
            break

        except ValueError as error:

            last_error = (
                f"Geçersiz JSON: {error}"
            )
            break

    raise RuntimeError(
        f"API isteği başarısız: {last_error}"
    )


# =========================================================
# JSON İÇİNDE POSITION ARA
# =========================================================

POSITION_KEYS = {
    "position",
    "positionname",
    "mainposition",
    "main_position",
    "position_name",
    "positionlabel",
    "position_label",
}


def extract_position_from_json(data):

    candidates = []

    def walk(value):

        if isinstance(value, dict):

            for key, child in value.items():

                normalized_key = (
                    str(key)
                    .lower()
                    .replace("-", "_")
                )

                if normalized_key in POSITION_KEYS:

                    if isinstance(child, str):

                        child = child.strip()

                        if child:
                            candidates.append(child)

                    elif isinstance(child, dict):

                        for subkey in (
                            "name",
                            "label",
                            "value",
                            "description",
                        ):

                            subvalue = child.get(subkey)

                            if isinstance(subvalue, str):

                                subvalue = subvalue.strip()

                                if subvalue:
                                    candidates.append(subvalue)

                walk(child)

        elif isinstance(value, list):

            for child in value:
                walk(child)

    walk(data)

    # İlk gerçekten normalize edilebilen position değerini kullan.
    for candidate in candidates:

        normalized = normalize_position(
            candidate
        )

        if normalized:

            return candidate

    return ""


# =========================================================
# OLASI ENDPOINTLER
# =========================================================

def fetch_player_position(session, tm_id):

    endpoints = [
        f"{API_BASE}/player/{tm_id}",
        f"{API_BASE}/players/{tm_id}",
        f"{API_BASE}/player/{tm_id}/profile",
        f"{API_BASE}/players/{tm_id}/profile",
        f"{API_BASE}/player/{tm_id}/details",
        f"{API_BASE}/players/{tm_id}/details",
    ]

    errors = []

    for url in endpoints:

        try:

            data = api_get(
                session,
                url
            )

            if data is None:
                continue

            raw_position = (
                extract_position_from_json(
                    data
                )
            )

            if raw_position:

                return {
                    "status": "FOUND",
                    "raw_position": raw_position,
                    "endpoint": url,
                }

        except Exception as error:

            errors.append(
                f"{url} -> {error}"
            )

    if errors:

        return {
            "status": "FAILED",
            "raw_position": "",
            "endpoint": "",
            "errors": errors,
        }

    return {
        "status": "NOT_FOUND",
        "raw_position": "",
        "endpoint": "",
    }


# =========================================================
# TIME
# =========================================================

def format_time(seconds):

    seconds = max(
        0,
        int(seconds)
    )

    hours, remainder = divmod(
        seconds,
        3600
    )

    minutes, seconds = divmod(
        remainder,
        60
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds:02d}"
    )


# =========================================================
# CLI
# =========================================================

def parse_args():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT
    )

    parser.add_argument(
        "--all",
        action="store_true"
    )

    parser.add_argument(
        "--recheck-all",
        action="store_true"
    )

    return parser.parse_args()


# =========================================================
# MAIN
# =========================================================

def main():

    args = parse_args()

    players = load_players()

    candidates = [
        player
        for player in players
        if get_transfermarkt_id(player)
    ]

    if args.recheck_all:

        selected = candidates

    else:

        pending = [
            player
            for player in candidates
            if player.get(
                "position_checked"
            ) is not True
        ]

        if args.all:
            selected = pending
        else:
            selected = pending[
                :args.limit
            ]

    print(
        f"Toplam oyuncu: {len(players)}"
    )

    print(
        f"Transfermarkt ID bulunan: "
        f"{len(candidates)}"
    )

    print(
        f"Bu çalışmada işlenecek: "
        f"{len(selected)}"
    )

    if not selected:
        return

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/151 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
        }
    )

    updated = 0
    unchanged = 0
    not_found = 0
    failed = 0

    backup_file = None

    start_time = time.time()
    durations = []

    try:

        for index, player in enumerate(
            selected,
            start=1
        ):

            started = time.time()

            name = str(
                player.get(
                    "name",
                    ""
                )
            ).strip()

            tm_id = get_transfermarkt_id(
                player
            )

            old_positions = (
                get_existing_positions(
                    player
                )
            )

            print()
            print(
                "--------------------------------"
            )

            print(
                f"{index} / "
                f"{len(selected)} - "
                f"{name}"
            )

            print(
                f"Transfermarkt ID: "
                f"{tm_id}"
            )

            try:

                result = fetch_player_position(
                    session,
                    tm_id
                )

                status = result[
                    "status"
                ]

                if status == "FOUND":

                    raw_position = (
                        result[
                            "raw_position"
                        ]
                    )

                    normalized = (
                        normalize_position(
                            raw_position
                        )
                    )

                    print(
                        f"API endpoint: "
                        f"{result['endpoint']}"
                    )

                    print(
                        f"Transfermarkt position: "
                        f"{raw_position}"
                    )

                    print(
                        f"Normalize: "
                        f"{normalized}"
                    )

                    print(
                        f"Eski positions: "
                        f"{old_positions}"
                    )

                    new_positions = [
                        normalized
                    ]

                    changed = False

                    # Küçük/büyük harf farkını da standardize et.
                    if (
                        old_positions
                        !=
                        new_positions
                    ):

                        player[
                            "positions"
                        ] = new_positions

                        if "position" in player:
                            del player[
                                "position"
                            ]

                        updated += 1
                        changed = True

                        print(
                            "GÜNCELLENDİ:"
                        )

                        print(
                            f"{old_positions} "
                            f"-> "
                            f"{new_positions}"
                        )

                        write_log(
                            "POSITION API UPDATE | "
                            f"{name} | "
                            f"{tm_id} | "
                            f"{old_positions} -> "
                            f"{new_positions} | "
                            f"raw={raw_position}"
                        )

                    else:

                        unchanged += 1

                        print(
                            "Değişiklik yok."
                        )

                    if (
                        player.get(
                            "position_checked"
                        )
                        is not True
                    ):

                        player[
                            "position_checked"
                        ] = True

                        changed = True

                    if changed:

                        if backup_file is None:

                            backup_file = (
                                create_backup()
                            )

                            print(
                                f"Backup: "
                                f"{backup_file}"
                            )

                        save_players_atomic(
                            players
                        )

                elif status == "NOT_FOUND":

                    not_found += 1

                    print(
                        "JSON API'de mevki bulunamadı."
                    )

                    write_log(
                        "POSITION API NOT FOUND | "
                        f"{name} | "
                        f"{tm_id}"
                    )

                else:

                    failed += 1

                    print(
                        "API isteği başarısız."
                    )

                    write_log(
                        "POSITION API FAILED | "
                        f"{name} | "
                        f"{tm_id} | "
                        f"{result.get('errors')}"
                    )

            except Exception as error:

                failed += 1

                print(
                    "HATA:",
                    error
                )

                write_log(
                    "POSITION API FAILED | "
                    f"{name} | "
                    f"{tm_id} | "
                    f"{error}"
                )

            duration = (
                time.time()
                -
                started
            )

            durations.append(
                duration
            )

            if len(durations) > 25:
                durations.pop(0)

            average = (
                sum(durations)
                /
                len(durations)
            )

            remaining = (
                len(selected)
                -
                index
            )

            eta = (
                average
                *
                remaining
            )

            elapsed = (
                time.time()
                -
                start_time
            )

            print()

            print(
                f"updated: {updated} | "
                f"unchanged: {unchanged} | "
                f"not found: {not_found} | "
                f"failed: {failed}"
            )

            print(
                f"elapsed: "
                f"{format_time(elapsed)} | "
                f"ETA: "
                f"{format_time(eta)}"
            )

            time.sleep(
                REQUEST_DELAY
            )

    except KeyboardInterrupt:

        print()
        print(
            "Ctrl+C algılandı."
        )

        print(
            "Kaydedilmiş checkpointler korunuyor."
        )

    print()
    print(
        "================================"
    )

    print(
        "MEVKİ API KONTROLÜ BİTTİ"
    )

    print(
        "================================"
    )

    print(
        f"Updated: {updated}"
    )

    print(
        f"Unchanged: {unchanged}"
    )

    print(
        f"Not found: {not_found}"
    )

    print(
        f"Failed: {failed}"
    )

    if backup_file:

        print(
            f"Backup: "
            f"{backup_file}"
        )


if __name__ == "__main__":
    main()