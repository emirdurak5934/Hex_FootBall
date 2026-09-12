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
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup


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

TRANSFERMARKT_BASE = "https://www.transfermarkt.com"

DEFAULT_LIMIT = 10

TIMEOUT = 20

MAX_RETRIES = 2
RETRY_WAIT = 3

# Oyuncular arası bekleme
REQUEST_DELAY = 1


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Connection": "keep-alive",
}


# =========================================================
# NORMALIZE
# =========================================================

def normalize(value):

    value = str(
        value or ""
    ).strip().lower()

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return " ".join(
        value.split()
    )


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
# JSON LOAD
# =========================================================

def load_players():

    if not PLAYERS_FILE.exists():

        raise FileNotFoundError(
            f"Dosya bulunamadı: {PLAYERS_FILE}"
        )

    with PLAYERS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        players = json.load(file)

    if not isinstance(
        players,
        list
    ):

        raise ValueError(
            "players.json liste formatında değil."
        )

    return players


# =========================================================
# ATOMİK SAVE
# =========================================================

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

            os.fsync(
                file.fileno()
            )

        # tmp JSON doğrulama
        with open(
            temp_path,
            "r",
            encoding="utf-8"
        ) as file:

            check = json.load(file)

        if not isinstance(
            check,
            list
        ):

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

        if os.path.exists(
            temp_path
        ):

            os.unlink(
                temp_path
            )


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
        f"players_before_transfermarkt_ids_{timestamp}.json"
    )

    shutil.copy2(
        PLAYERS_FILE,
        backup_file
    )

    return backup_file


# =========================================================
# MEVCUT TM ID
# =========================================================

def get_existing_tm_id(player):

    value = str(
        player.get(
            "transfermarkt_id",
            ""
        )
    ).strip()

    if re.fullmatch(
        r"\d+",
        value
    ):

        return value

    return ""


# =========================================================
# HTTP
# =========================================================

def safe_get(
    session,
    url
):

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

            # 403
            if response.status_code == 403:

                last_error = "HTTP 403"

                if attempt < MAX_RETRIES:

                    print(
                        f"Transfermarkt 403. "
                        f"{RETRY_WAIT} saniye sonra tekrar..."
                    )

                    time.sleep(
                        RETRY_WAIT
                    )

                    continue

            # 429
            if response.status_code == 429:

                last_error = "HTTP 429"

                if attempt < MAX_RETRIES:

                    print(
                        f"Transfermarkt 429. "
                        f"{RETRY_WAIT} saniye sonra tekrar..."
                    )

                    time.sleep(
                        RETRY_WAIT
                    )

                    continue

            # 5xx
            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                last_error = (
                    f"HTTP {response.status_code}"
                )

                if attempt < MAX_RETRIES:

                    print(
                        f"Transfermarkt "
                        f"{response.status_code}. "
                        f"{RETRY_WAIT} saniye sonra tekrar..."
                    )

                    time.sleep(
                        RETRY_WAIT
                    )

                    continue

            response.raise_for_status()

            return response

        except (
            requests.Timeout,
            requests.ConnectionError
        ) as error:

            last_error = str(
                error
            )

            if attempt < MAX_RETRIES:

                print(
                    "Bağlantı/timeout hatası. "
                    f"{RETRY_WAIT} saniye sonra tekrar..."
                )

                time.sleep(
                    RETRY_WAIT
                )

                continue

        except requests.RequestException as error:

            last_error = str(
                error
            )

            break

    raise RuntimeError(
        "Transfermarkt isteği başarısız: "
        f"{last_error}"
    )


# =========================================================
# TRANSFERMARKT ARAMA
# =========================================================

def search_transfermarkt(
    session,
    player_name
):

    query = quote_plus(
        player_name
    )

    url = (
        "https://www.transfermarkt.com/"
        "schnellsuche/ergebnis/"
        f"schnellsuche?query={query}"
    )

    response = safe_get(
        session,
        url
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    results = []

    seen_ids = set()

    links = soup.select(
        'a[href*="/profil/spieler/"]'
    )

    for link in links:

        href = str(
            link.get(
                "href",
                ""
            )
        ).strip()

        match = re.search(
            r"/profil/spieler/(\d+)",
            href
        )

        if not match:

            continue

        transfermarkt_id = (
            match.group(1)
        )

        if transfermarkt_id in seen_ids:

            continue

        display_name = (
            str(
                link.get(
                    "title",
                    ""
                )
            ).strip()
            or
            link.get_text(
                " ",
                strip=True
            )
        )

        display_name = str(
            display_name or ""
        ).strip()

        if not display_name:

            continue

        seen_ids.add(
            transfermarkt_id
        )

        results.append(
            {
                "id":
                    transfermarkt_id,

                "name":
                    display_name,

                "url":
                    urljoin(
                        TRANSFERMARKT_BASE,
                        href
                    )
            }
        )

    return results


# =========================================================
# İSİMLE EN UYGUN SONUÇ
# =========================================================

def choose_best_result(
    player_name,
    results
):

    if not results:

        return None

    wanted = normalize(
        player_name
    )

    # 1. Tam isim eşleşmesi
    exact_matches = [
        result
        for result in results
        if normalize(
            result["name"]
        ) == wanted
    ]

    if exact_matches:

        return exact_matches[0]

    # 2. İsim birbirini kapsıyorsa
    partial_matches = []

    for result in results:

        result_name = normalize(
            result["name"]
        )

        if (
            wanted
            and
            result_name
            and
            (
                wanted in result_name
                or
                result_name in wanted
            )
        ):

            partial_matches.append(
                result
            )

    if partial_matches:

        return partial_matches[0]

    # 3. Hiçbiri uymuyorsa ilk sonucu kör yazma
    return None


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
        default=DEFAULT_LIMIT,
        help=(
            "Test modunda işlenecek oyuncu sayısı. "
            "Varsayılan: 10"
        )
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Transfermarkt ID eksik tüm oyuncuları işle."
        )
    )

    return parser.parse_args()


# =========================================================
# MAIN
# =========================================================

def main():

    args = parse_args()

    if args.limit < 1:

        raise SystemExit(
            "--limit en az 1 olmalı."
        )

    players = load_players()

    missing = [
        player
        for player in players
        if not get_existing_tm_id(
            player
        )
    ]

    if args.all:

        selected = missing

    else:

        selected = missing[
            :args.limit
        ]

    print(
        f"Toplam oyuncu: "
        f"{len(players)}"
    )

    print(
        f"Transfermarkt ID eksik: "
        f"{len(missing)}"
    )

    print(
        f"Bu çalışmada işlenecek: "
        f"{len(selected)}"
    )

    if not selected:

        print(
            "Eksik oyuncu yok."
        )

        return

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    backup_file = None

    added = 0

    not_found = 0

    failed = 0

    start_time = (
        time.time()
    )

    durations = []

    try:

        for index, player in enumerate(
            selected,
            start=1
        ):

            player_start = (
                time.time()
            )

            name = str(
                player.get(
                    "name",
                    ""
                )
            ).strip()

            player_id = str(
                player.get(
                    "id",
                    ""
                )
            ).strip()

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
                f"Player ID: "
                f"{player_id}"
            )

            try:

                print(
                    "Transfermarkt'ta isimle aranıyor..."
                )

                results = search_transfermarkt(
                    session,
                    name
                )

                print(
                    f"Bulunan profil adayı: "
                    f"{len(results)}"
                )

                result = choose_best_result(
                    name,
                    results
                )

                if not result:

                    not_found += 1

                    print(
                        "İsme uygun Transfermarkt profili bulunamadı."
                    )

                    write_log(
                        "TRANSFERMARKT ID NOT FOUND | "
                        f"{name} | "
                        f"{player_id}"
                    )

                else:

                    transfermarkt_id = (
                        result["id"]
                    )

                    transfermarkt_name = (
                        result["name"]
                    )

                    print(
                        f"Eşleşen isim: "
                        f"{transfermarkt_name}"
                    )

                    print(
                        f"Transfermarkt ID: "
                        f"{transfermarkt_id}"
                    )

                    if backup_file is None:

                        backup_file = (
                            create_backup()
                        )

                        print(
                            f"Backup oluşturuldu: "
                            f"{backup_file}"
                        )

                    player[
                        "transfermarkt_id"
                    ] = str(
                        transfermarkt_id
                    )

                    save_players_atomic(
                        players
                    )

                    added += 1

                    print(
                        "KAYDEDİLDİ."
                    )

                    write_log(
                        "TRANSFERMARKT ID ADDED BY NAME | "
                        f"{name} | "
                        f"{player_id} -> "
                        f"{transfermarkt_id} | "
                        f"tm_name={transfermarkt_name}"
                    )

            except Exception as error:

                failed += 1

                print(
                    "HATA:",
                    error
                )

                write_log(
                    "TRANSFERMARKT ID FAILED | "
                    f"{name} | "
                    f"{player_id} | "
                    f"{error}"
                )

            # =============================================
            # ETA
            # =============================================

            duration = (
                time.time()
                -
                player_start
            )

            durations.append(
                duration
            )

            if len(
                durations
            ) > 20:

                durations.pop(
                    0
                )

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
                f"added: {added} | "
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
            "Daha önce kaydedilen ID'ler korunuyor."
        )

        write_log(
            "TRANSFERMARKT ID SCRIPT INTERRUPTED"
        )

    # =====================================================
    # FINAL
    # =====================================================

    current_missing = sum(
        1
        for player in players
        if not get_existing_tm_id(
            player
        )
    )

    print()
    print(
        "================================"
    )

    print(
        "TRANSFERMARKT ID TARAMASI BİTTİ"
    )

    print(
        "================================"
    )

    print(
        f"Added: "
        f"{added}"
    )

    print(
        f"Not found: "
        f"{not_found}"
    )

    print(
        f"Failed: "
        f"{failed}"
    )

    print(
        f"Kalan Transfermarkt ID eksik: "
        f"{current_missing}"
    )

    if backup_file:

        print(
            f"Backup: "
            f"{backup_file}"
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()