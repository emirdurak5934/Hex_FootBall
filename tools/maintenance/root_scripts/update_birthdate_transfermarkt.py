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

WIKIDATA_API = "https://www.wikidata.org/w/api.php"

DEFAULT_LIMIT = 10
BATCH_SIZE = 25

TIMEOUT = 30
MAX_RETRIES = 2
RETRY_WAIT = 3
REQUEST_DELAY = 1


HEADERS = {
    "User-Agent": (
        "FootballDatabase/1.0 "
        "(birthdate enrichment via Wikidata)"
    ),
    "Accept": "application/json",
}


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
# LOAD
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
        f"players_before_birthdates_wikidata_{timestamp}.json"
    )

    shutil.copy2(
        PLAYERS_FILE,
        backup_file
    )

    return backup_file


# =========================================================
# QID
# =========================================================

def get_qid(player):

    player_id = str(
        player.get(
            "id",
            ""
        )
    ).strip()

    if re.fullmatch(
        r"Q\d+",
        player_id
    ):

        return player_id

    return ""


# =========================================================
# ESKİ BIRTHDATE
# =========================================================

def get_existing_birthdate(player):

    value = str(
        player.get(
            "birthDate",
            ""
        )
    ).strip()

    if re.fullmatch(
        r"\d{4}-\d{2}-\d{2}",
        value
    ):

        return value

    return ""


# =========================================================
# WIKIDATA REQUEST
# =========================================================

def wikidata_request(
    session,
    qids
):

    params = {
        "action": "wbgetentities",
        "ids": "|".join(qids),
        "props": "claims",
        "format": "json",
        "formatversion": "2",
    }

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = session.get(
                WIKIDATA_API,
                params=params,
                timeout=TIMEOUT
            )

            if response.status_code == 429:

                last_error = "HTTP 429"

                if attempt < MAX_RETRIES:

                    print(
                        f"Wikidata 429. "
                        f"{RETRY_WAIT} saniye sonra tekrar..."
                    )

                    time.sleep(
                        RETRY_WAIT
                    )

                    continue

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
                        f"Wikidata HTTP "
                        f"{response.status_code}. "
                        f"{RETRY_WAIT} saniye sonra tekrar..."
                    )

                    time.sleep(
                        RETRY_WAIT
                    )

                    continue

            response.raise_for_status()

            return response.json()

        except (
            requests.Timeout,
            requests.ConnectionError
        ) as error:

            last_error = str(error)

            if attempt < MAX_RETRIES:

                print(
                    "Wikidata bağlantı/timeout hatası. "
                    f"{RETRY_WAIT} saniye sonra tekrar..."
                )

                time.sleep(
                    RETRY_WAIT
                )

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
        f"Wikidata request failed: {last_error}"
    )


# =========================================================
# WIKIDATA TIME -> YYYY-MM-DD
# =========================================================

def parse_wikidata_time(value):

    if not isinstance(value, dict):

        return ""

    raw_time = str(
        value.get(
            "time",
            ""
        )
    ).strip()

    precision = value.get(
        "precision"
    )

    if not raw_time:

        return ""

    # Tam gün kesinliği istiyoruz.
    # Wikidata:
    # 11 = day
    # 10 = month
    # 9  = year
    #
    # Month/year precision ise sahte gün üretmeyelim.
    if precision is not None and precision < 11:

        return ""

    match = re.match(
        r"^[+-](\d{4,})-(\d{2})-(\d{2})T",
        raw_time
    )

    if not match:

        return ""

    year = int(
        match.group(1)
    )

    month = int(
        match.group(2)
    )

    day = int(
        match.group(3)
    )

    # Futbol veri tabanı için makul doğrulama.
    if year < 1850 or year > 2020:

        return ""

    try:

        parsed = datetime(
            year,
            month,
            day
        )

    except ValueError:

        return ""

    return parsed.strftime(
        "%Y-%m-%d"
    )


# =========================================================
# P569 ÇIKAR
# =========================================================

def extract_birthdate(entity):

    if not isinstance(entity, dict):

        return ""

    claims = entity.get(
        "claims",
        {}
    )

    if not isinstance(claims, dict):

        return ""

    p569 = claims.get(
        "P569",
        []
    )

    if not isinstance(
        p569,
        list
    ):

        return ""

    candidates = []

    for claim in p569:

        if not isinstance(
            claim,
            dict
        ):

            continue

        mainsnak = claim.get(
            "mainsnak",
            {}
        )

        if mainsnak.get(
            "snaktype"
        ) != "value":

            continue

        datavalue = mainsnak.get(
            "datavalue",
            {}
        )

        value = datavalue.get(
            "value"
        )

        birthdate = (
            parse_wikidata_time(
                value
            )
        )

        if not birthdate:

            continue

        candidates.append(
            {
                "rank":
                    claim.get(
                        "rank",
                        "normal"
                    ),

                "birthDate":
                    birthdate
            }
        )

    if not candidates:

        return ""

    preferred = [
        item
        for item in candidates
        if item["rank"] == "preferred"
    ]

    if preferred:

        return preferred[0][
            "birthDate"
        ]

    return candidates[0][
        "birthDate"
    ]


# =========================================================
# ENTITY MAP
# =========================================================

def parse_entities(data):

    entities = data.get(
        "entities",
        {}
    )

    result = {}

    if isinstance(
        entities,
        dict
    ):

        iterable = (
            entities.items()
        )

    elif isinstance(
        entities,
        list
    ):

        iterable = []

        for entity in entities:

            if not isinstance(
                entity,
                dict
            ):

                continue

            qid = str(
                entity.get(
                    "id",
                    ""
                )
            ).strip()

            if qid:

                iterable.append(
                    (
                        qid,
                        entity
                    )
                )

    else:

        return result

    for qid, entity in iterable:

        result[qid] = (
            extract_birthdate(
                entity
            )
        )

    return result


# =========================================================
# TIME FORMAT
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
# ARGUMENTS
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
            "birthdate_wikidata_checked true olmayan "
            "tüm QID'li oyuncuları işle."
        )
    )

    parser.add_argument(
        "--recheck-all",
        action="store_true",
        help=(
            "Checked durumuna bakmadan tüm QID'li "
            "oyuncuları yeniden kontrol et."
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

    qid_players = [
        player
        for player in players
        if get_qid(
            player
        )
    ]

    if args.recheck_all:

        pending = qid_players

    else:

        pending = [
            player
            for player in qid_players
            if player.get(
                "birthdate_wikidata_checked"
            ) is not True
        ]

    if args.all:

        selected = pending

    else:

        selected = pending[
            :args.limit
        ]

    print(
        f"Toplam oyuncu: "
        f"{len(players)}"
    )

    print(
        f"Wikidata QID bulunan: "
        f"{len(qid_players)}"
    )

    print(
        f"Kontrol bekleyen: "
        f"{len(pending)}"
    )

    print(
        f"Bu çalışmada işlenecek: "
        f"{len(selected)}"
    )

    if not selected:

        print(
            "Kontrol edilecek oyuncu yok."
        )

        return

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    backup_file = None

    updated = 0
    unchanged = 0
    not_found = 0
    failed = 0

    start_time = (
        time.time()
    )

    try:

        for batch_start in range(
            0,
            len(selected),
            BATCH_SIZE
        ):

            batch = selected[
                batch_start:
                batch_start + BATCH_SIZE
            ]

            qids = [
                get_qid(player)
                for player in batch
            ]

            batch_number = (
                batch_start // BATCH_SIZE
                + 1
            )

            total_batches = (
                (
                    len(selected)
                    +
                    BATCH_SIZE
                    -
                    1
                )
                //
                BATCH_SIZE
            )

            print()
            print(
                "================================"
            )

            print(
                f"BATCH "
                f"{batch_number} / "
                f"{total_batches}"
            )

            print(
                "================================"
            )

            try:

                data = wikidata_request(
                    session,
                    qids
                )

                birth_map = (
                    parse_entities(
                        data
                    )
                )

            except Exception as error:

                failed += len(
                    batch
                )

                print(
                    "BATCH HATASI:",
                    error
                )

                for player in batch:

                    write_log(
                        "BIRTHDATE WIKIDATA FAILED | "
                        f"{player.get('name')} | "
                        f"{get_qid(player)} | "
                        f"{error}"
                    )

                time.sleep(
                    REQUEST_DELAY
                )

                continue

            changed_batch = False

            for offset, player in enumerate(
                batch,
                start=1
            ):

                global_index = (
                    batch_start
                    +
                    offset
                )

                name = str(
                    player.get(
                        "name",
                        ""
                    )
                ).strip()

                qid = get_qid(
                    player
                )

                old_birthdate = (
                    get_existing_birthdate(
                        player
                    )
                )

                new_birthdate = (
                    birth_map.get(
                        qid,
                        ""
                    )
                )

                print()
                print(
                    "--------------------------------"
                )

                print(
                    f"{global_index} / "
                    f"{len(selected)} - "
                    f"{name}"
                )

                print(
                    f"Wikidata ID: "
                    f"{qid}"
                )

                if not new_birthdate:

                    not_found += 1

                    print(
                        "Wikidata P569 tam doğum tarihi bulunamadı."
                    )

                    # Sorgu başarılı oldu.
                    # P569 yokluğu tekrar tekrar sorgulanmasın.
                    player[
                        "birthdate_wikidata_checked"
                    ] = True

                    changed_batch = True

                    write_log(
                        "BIRTHDATE WIKIDATA NOT FOUND | "
                        f"{name} | "
                        f"{qid}"
                    )

                    continue

                print(
                    f"Wikidata birthDate: "
                    f"{new_birthdate}"
                )

                print(
                    f"Eski birthDate: "
                    f"{old_birthdate or '-'}"
                )

                if (
                    old_birthdate
                    !=
                    new_birthdate
                ):

                    player[
                        "birthDate"
                    ] = new_birthdate

                    updated += 1

                    changed_batch = True

                    print(
                        "GÜNCELLENDİ:"
                    )

                    print(
                        f"{old_birthdate or '-'} "
                        f"-> "
                        f"{new_birthdate}"
                    )

                    write_log(
                        "BIRTHDATE WIKIDATA UPDATE | "
                        f"{name} | "
                        f"{qid} | "
                        f"{old_birthdate or '-'} -> "
                        f"{new_birthdate}"
                    )

                else:

                    unchanged += 1

                    print(
                        "Değişiklik yok."
                    )

                if player.get(
                    "birthdate_wikidata_checked"
                ) is not True:

                    player[
                        "birthdate_wikidata_checked"
                    ] = True

                    changed_batch = True

            # =============================================
            # BATCH CHECKPOINT
            # =============================================

            if changed_batch:

                if backup_file is None:

                    backup_file = (
                        create_backup()
                    )

                    print()
                    print(
                        f"Backup oluşturuldu: "
                        f"{backup_file}"
                    )

                save_players_atomic(
                    players
                )

            elapsed = (
                time.time()
                -
                start_time
            )

            completed = min(
                batch_start
                +
                BATCH_SIZE,
                len(selected)
            )

            average_per_player = (
                elapsed
                /
                completed
            )

            remaining = (
                len(selected)
                -
                completed
            )

            eta = (
                average_per_player
                *
                remaining
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
            "Tamamlanmış batch checkpointleri korunuyor."
        )

        write_log(
            "BIRTHDATE WIKIDATA SCRIPT INTERRUPTED"
        )

    print()
    print(
        "================================"
    )

    print(
        "WIKIDATA DOĞUM TARİHİ KONTROLÜ BİTTİ"
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