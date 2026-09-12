import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import argparse
import json
import re
import time
import unicodedata

from collections import Counter, deque
from datetime import datetime
from pathlib import Path

import requests

from enrich_missing_players import (
    PLAYERS_FILE,
    HEADERS,
    REQUEST_DELAY,
    atomic_save,
    create_backup,
    fetch_transfer_clubs,
)


CHECK_FIELD = "clubs_verified_safe_v2"

REPORT_DIR = Path("data")
LOG_FILE = REPORT_DIR / "logs.txt"

ETA_WINDOW_SIZE = 20


# ============================================================
# ARGUMENTS
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Safely verify player club histories "
            "using Transfermarkt club-history API."
        )
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Tüm uygun oyuncuları kontrol et.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Test modunda kontrol edilecek oyuncu sayısı. Varsayılan: 10",
    )

    parser.add_argument(
        "--player",
        type=str,
        default="",
        help="Belirli isimdeki oyuncuları kontrol et.",
    )

    parser.add_argument(
        "--replace",
        action="store_true",
        help=(
            "Güvenli eşleşmede JSON clubs alanını "
            "Transfermarkt kulüp listesiyle değiştir."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Daha önce doğrulanan oyuncuları tekrar kontrol et.",
    )

    parser.add_argument(
        "--start-from",
        type=int,
        default=1,
        help="Seçilen oyuncu listesinin kaçıncı kaydından başlanacağı.",
    )

    return parser.parse_args()


# ============================================================
# BASIC HELPERS
# ============================================================

def load_players():

    with PLAYERS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        players = json.load(file)

    if not isinstance(players, list):

        raise ValueError(
            "players.json liste formatında değil."
        )

    return players


def write_log(message):

    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with LOG_FILE.open(
        "a",
        encoding="utf-8",
    ) as file:

        file.write(
            f"{datetime.now().isoformat(timespec='seconds')} | "
            f"{message}\n"
        )


def save_report(report, report_file):

    report_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = report_file.with_suffix(
        ".json.tmp"
    )

    with temp_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temp_file.replace(
        report_file
    )


def format_seconds(seconds):

    seconds = max(
        0,
        int(seconds),
    )

    hours, remainder = divmod(
        seconds,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds:02d}"
    )


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(value):

    value = str(
        value or ""
    ).strip()

    if not value:
        return ""

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.casefold()

    value = value.replace(
        "&",
        " and ",
    )

    value = re.sub(
        r"[^\w\s]",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


def safe_club_key(value):

    key = normalize_text(
        value
    )

    if not key:
        return ""

    # --------------------------------------------------------
    # Çok yaygın kulüp son eklerini normalize et.
    # --------------------------------------------------------

    replacements = (
        r"\bf c\b",
        r"\bfc\b",
        r"\bc f\b",
        r"\bcf\b",
        r"\bfootball club\b",
        r"\bclub de futbol\b",
        r"\bclub de football\b",
    )

    for pattern in replacements:

        key = re.sub(
            pattern,
            " ",
            key,
        )

    key = re.sub(
        r"\s+",
        " ",
        key,
    ).strip()

    # --------------------------------------------------------
    # Bilinen isim varyasyonları
    # --------------------------------------------------------

    aliases = {
        "atletico madrid":
            "atletico de madrid",

        "manchester city":
            "manchester city",

        "manchester united":
            "manchester united",

        "internazionale":
            "inter",

        "internazionale milano":
            "inter",

        "inter milan":
            "inter",

        "paris saint germain":
            "paris saint germain",
    }

    return aliases.get(
        key,
        key,
    )


# ============================================================
# RESERVE / YOUTH FILTER
# ============================================================

def is_reserve_or_youth_club(name):

    key = normalize_text(
        name
    )

    if not key:
        return True

    markers = (
        " u23",
        " u22",
        " u21",
        " u20",
        " u19",
        " u18",
        " u17",
        " u16",
        " u15",

        " under 23",
        " under 21",
        " under 19",
        " under 18",
        " under 17",

        " reserve",
        " reserves",

        " youth",
        " academy",

        " primavera",

        " junior",
        " juniors",

        " amateure",

        " second team",
        " second squad",
    )

    padded = (
        f" {key} "
    )

    for marker in markers:

        if marker in padded:
            return True

    # --------------------------------------------------------
    # Takım sonundaki B / II / 2 gibi reserve ifadeleri
    # --------------------------------------------------------

    if re.search(
        r"\s+b$",
        key,
    ):
        return True

    if re.search(
        r"\s+ii$",
        key,
    ):
        return True

    if re.search(
        r"\s+iii$",
        key,
    ):
        return True

    return False


def clean_transfermarkt_clubs(clubs):

    cleaned = []

    seen = set()

    for club in clubs:

        club = str(
            club or ""
        ).strip()

        if not club:
            continue

        if is_reserve_or_youth_club(
            club
        ):
            continue

        key = safe_club_key(
            club
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        cleaned.append(
            club
        )

    return cleaned


# ============================================================
# CLUB COMPARISON
# ============================================================

def club_map(clubs):

    result = {}

    if not isinstance(
        clubs,
        list,
    ):
        return result

    for club in clubs:

        club = str(
            club or ""
        ).strip()

        if not club:
            continue

        key = safe_club_key(
            club
        )

        if not key:
            continue

        if key not in result:

            result[
                key
            ] = club

    return result


def compare_clubs(
    existing_clubs,
    tm_clubs,
):

    existing_map = club_map(
        existing_clubs
    )

    tm_map = club_map(
        tm_clubs
    )

    common_keys = (
        set(
            existing_map.keys()
        )
        &
        set(
            tm_map.keys()
        )
    )

    missing_keys = (
        set(
            tm_map.keys()
        )
        -
        set(
            existing_map.keys()
        )
    )

    extra_keys = (
        set(
            existing_map.keys()
        )
        -
        set(
            tm_map.keys()
        )
    )

    common = [
        existing_map[key]
        for key in sorted(
            common_keys
        )
    ]

    missing = [
        tm_map[key]
        for key in sorted(
            missing_keys
        )
    ]

    extra = [
        existing_map[key]
        for key in sorted(
            extra_keys
        )
    ]

    return (
        common,
        missing,
        extra,
    )


# ============================================================
# IDENTITY CONFIDENCE
# ============================================================

def identity_is_safe(
    existing_clubs,
    tm_clubs,
):

    existing_map = club_map(
        existing_clubs
    )

    tm_map = club_map(
        tm_clubs
    )

    existing_keys = set(
        existing_map.keys()
    )

    tm_keys = set(
        tm_map.keys()
    )

    common = (
        existing_keys
        &
        tm_keys
    )

    old_count = len(
        existing_keys
    )

    tm_count = len(
        tm_keys
    )

    common_count = len(
        common
    )

    # --------------------------------------------------------
    # JSON'da hiç kulüp yoksa kimliği kulüpler üzerinden
    # doğrulayamıyoruz.
    # --------------------------------------------------------

    if old_count == 0:

        return (
            False,
            "NO_EXISTING_CLUBS",
            common_count,
        )

    # --------------------------------------------------------
    # Transfermarkt boşsa kesinlikle kullanma.
    # --------------------------------------------------------

    if tm_count == 0:

        return (
            False,
            "EMPTY_TM_CLUBS",
            common_count,
        )

    # --------------------------------------------------------
    # Hiç ortak kulüp yoksa şüpheli Transfermarkt ID.
    # --------------------------------------------------------

    if common_count == 0:

        return (
            False,
            "NO_COMMON_CLUB",
            common_count,
        )

    # --------------------------------------------------------
    # JSON'da yalnızca 1 kulüp varsa,
    # o kulübün TM listesinde bulunması yeterli.
    # --------------------------------------------------------

    if old_count == 1:

        return (
            True,
            "ONE_CLUB_MATCH",
            common_count,
        )

    # --------------------------------------------------------
    # JSON'da 2+ kulüp varsa en az 2 ortak kulüp tercih ediyoruz.
    # --------------------------------------------------------

    if common_count >= 2:

        return (
            True,
            "MULTIPLE_CLUB_MATCH",
            common_count,
        )

    # --------------------------------------------------------
    # Tek ortak kulüp var ama JSON'da çok kulüp varsa
    # yanlış ID ihtimali nedeniyle değiştirmiyoruz.
    # --------------------------------------------------------

    return (
        False,
        "WEAK_CLUB_OVERLAP",
        common_count,
    )


# ============================================================
# MERGE
# ============================================================

def merge_clubs(
    existing_clubs,
    tm_clubs,
):

    result = list(
        existing_clubs
        if isinstance(
            existing_clubs,
            list,
        )
        else []
    )

    seen = set(
        club_map(
            result
        ).keys()
    )

    for club in tm_clubs:

        key = safe_club_key(
            club
        )

        if not key:
            continue

        if key in seen:
            continue

        result.append(
            club
        )

        seen.add(
            key
        )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_args()

    if args.limit < 1:

        raise SystemExit(
            "--limit 1 veya daha büyük olmalı."
        )

    players = load_players()

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_file = (
        REPORT_DIR
        /
        f"club_verification_report_{timestamp}.json"
    )

    print()
    print(
        "=" * 70
    )

    print(
        "SAFE CLUB HISTORY VERIFICATION V2"
    )

    print(
        "=" * 70
    )

    print(
        f"Toplam oyuncu: {len(players)}"
    )

    print(
        "Kaynak: Transfermarkt club-history API"
    )

    print(
        "Transfermarkt profil sayfası kullanılmıyor."
    )

    # ========================================================
    # DUPLICATE TM IDS
    # ========================================================

    tm_ids = []

    for player in players:

        tm_id = str(
            player.get(
                "transfermarkt_id",
                "",
            )
            or ""
        ).strip()

        if tm_id:

            tm_ids.append(
                tm_id
            )

    id_counts = Counter(
        tm_ids
    )

    duplicate_ids = {
        tm_id
        for tm_id, count
        in id_counts.items()
        if count > 1
    }

    print(
        f"Duplicate Transfermarkt ID: "
        f"{len(duplicate_ids)}"
    )

    # ========================================================
    # SELECT PLAYERS
    # ========================================================

    player_query = str(
        args.player
        or ""
    ).strip().casefold()

    if player_query:

        selected = [
            player
            for player in players
            if str(
                player.get(
                    "name",
                    "",
                )
            ).strip().casefold()
            == player_query
        ]

    else:

        eligible = []

        for player in players:

            tm_id = str(
                player.get(
                    "transfermarkt_id",
                    "",
                )
                or ""
            ).strip()

            if not tm_id:
                continue

            if (
                not args.force
                and player.get(
                    CHECK_FIELD
                ) is True
            ):
                continue

            eligible.append(
                player
            )

        start_index = max(
            0,
            args.start_from - 1,
        )

        eligible = eligible[
            start_index:
        ]

        if args.all:

            selected = eligible

        else:

            selected = eligible[
                :args.limit
            ]

    print(
        f"Bu çalışmada kontrol edilecek: "
        f"{len(selected)}"
    )

    print()

    if args.replace:

        print(
            "MOD: SAFE REPLACE"
        )

        print(
            "Yalnızca güçlü kulüp eşleşmesi olan "
            "oyuncular değiştirilecek."
        )

    else:

        print(
            "MOD: SAFE MERGE"
        )

        print(
            "Yalnızca güvenli eşleşmede eksik kulüpler eklenecek."
        )

    print()

    # ========================================================
    # SESSION
    # ========================================================

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    backup = None

    recent_durations = deque(
        maxlen=ETA_WINDOW_SIZE
    )

    run_started = time.perf_counter()

    counters = {
        "processed": 0,
        "updated": 0,
        "same": 0,

        "duplicate_id": 0,

        "no_existing_clubs": 0,
        "no_common_club": 0,
        "weak_overlap": 0,
        "empty_tm_clubs": 0,

        "404": 0,
        "403": 0,
        "errors": 0,

        "missing_added": 0,
        "extra_removed": 0,

        "reserve_filtered": 0,
    }

    report = {
        "started_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "mode":
            "replace"
            if args.replace
            else "merge",

        "check_field":
            CHECK_FIELD,

        "duplicate_transfermarkt_ids":
            sorted(
                duplicate_ids
            ),

        "players": [],
    }

    # ========================================================
    # LOOP
    # ========================================================

    try:

        for index, player in enumerate(
            selected,
            start=1,
        ):

            player_started = time.perf_counter()

            counters[
                "processed"
            ] += 1

            name = str(
                player.get(
                    "name",
                    "",
                )
            ).strip()

            wikidata_id = str(
                player.get(
                    "id",
                    "",
                )
                or ""
            ).strip()

            tm_id = str(
                player.get(
                    "transfermarkt_id",
                    "",
                )
                or ""
            ).strip()

            old_clubs = list(
                player.get(
                    "clubs",
                    [],
                )
                or []
            )

            print(
                "-" * 70
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

            detail = {
                "name":
                    name,

                "id":
                    wikidata_id,

                "transfermarkt_id":
                    tm_id,

                "old_clubs":
                    old_clubs,
            }

            # ==================================================
            # DUPLICATE ID
            # ==================================================

            if tm_id in duplicate_ids:

                counters[
                    "duplicate_id"
                ] += 1

                duplicates = []

                for other in players:

                    other_tm_id = str(
                        other.get(
                            "transfermarkt_id",
                            "",
                        )
                        or ""
                    ).strip()

                    if other_tm_id != tm_id:
                        continue

                    duplicates.append(
                        {
                            "id":
                                other.get(
                                    "id",
                                    "",
                                ),

                            "name":
                                other.get(
                                    "name",
                                    "",
                                ),

                            "birthDate":
                                other.get(
                                    "birthDate",
                                    "",
                                ),

                            "clubs":
                                other.get(
                                    "clubs",
                                    [],
                                ),
                        }
                    )

                print()

                print(
                    "ATLANDI: DUPLICATE TRANSFERMARKT ID"
                )

                for duplicate in duplicates:

                    print(
                        "  - "
                        f"{duplicate['name']} | "
                        f"{duplicate['birthDate']} | "
                        f"{duplicate['id']}"
                    )

                detail[
                    "status"
                ] = "DUPLICATE_TRANSFERMARKT_ID"

                detail[
                    "duplicates"
                ] = duplicates

                report[
                    "players"
                ].append(
                    detail
                )

                save_report(
                    report,
                    report_file,
                )

                write_log(
                    "CLUB V2 DUPLICATE TM ID | "
                    f"{name} | {tm_id}"
                )

                continue

            # ==================================================
            # FETCH CLUBS
            # ==================================================

            try:

                raw_tm_clubs = (
                    fetch_transfer_clubs(
                        session,
                        tm_id,
                    )
                )

            except Exception as error:

                error_text = str(
                    error
                )

                if "404" in error_text:

                    counters[
                        "404"
                    ] += 1

                    status = (
                        "TRANSFERMARKT_404"
                    )

                elif "403" in error_text:

                    counters[
                        "403"
                    ] += 1

                    status = (
                        "TRANSFERMARKT_403"
                    )

                else:

                    counters[
                        "errors"
                    ] += 1

                    status = (
                        "FETCH_ERROR"
                    )

                print()

                print(
                    f"ATLANDI: {error_text}"
                )

                detail[
                    "status"
                ] = status

                detail[
                    "error"
                ] = error_text

                report[
                    "players"
                ].append(
                    detail
                )

                save_report(
                    report,
                    report_file,
                )

                write_log(
                    "CLUB V2 FETCH ERROR | "
                    f"{name} | "
                    f"{tm_id} | "
                    f"{error_text}"
                )

                time.sleep(
                    REQUEST_DELAY
                )

                continue

            # ==================================================
            # FILTER RESERVE / YOUTH
            # ==================================================

            tm_clubs = clean_transfermarkt_clubs(
                raw_tm_clubs
            )

            filtered_count = (
                len(raw_tm_clubs)
                -
                len(tm_clubs)
            )

            counters[
                "reserve_filtered"
            ] += max(
                0,
                filtered_count,
            )

            detail[
                "raw_transfermarkt_clubs"
            ] = raw_tm_clubs

            detail[
                "transfermarkt_clubs"
            ] = tm_clubs

            if filtered_count > 0:

                print(
                    f"Reserve/youth filtrelendi: "
                    f"{filtered_count}"
                )

            # ==================================================
            # IDENTITY SAFETY
            # ==================================================

            (
                identity_safe,
                identity_reason,
                common_count,
            ) = identity_is_safe(
                old_clubs,
                tm_clubs,
            )

            detail[
                "identity_reason"
            ] = identity_reason

            detail[
                "common_club_count"
            ] = common_count

            if not identity_safe:

                if (
                    identity_reason
                    == "NO_EXISTING_CLUBS"
                ):

                    counters[
                        "no_existing_clubs"
                    ] += 1

                elif (
                    identity_reason
                    == "NO_COMMON_CLUB"
                ):

                    counters[
                        "no_common_club"
                    ] += 1

                elif (
                    identity_reason
                    == "WEAK_CLUB_OVERLAP"
                ):

                    counters[
                        "weak_overlap"
                    ] += 1

                elif (
                    identity_reason
                    == "EMPTY_TM_CLUBS"
                ):

                    counters[
                        "empty_tm_clubs"
                    ] += 1

                print()

                print(
                    "ATLANDI: KİMLİK / KULÜP "
                    "EŞLEŞMESİ YETERİNCE GÜVENLİ DEĞİL"
                )

                print(
                    f"Neden: {identity_reason}"
                )

                print()

                print(
                    "JSON clubs:"
                )

                for club in old_clubs:

                    print(
                        f"  - {club}"
                    )

                print()

                print(
                    "Transfermarkt clubs:"
                )

                for club in tm_clubs:

                    print(
                        f"  - {club}"
                    )

                detail[
                    "status"
                ] = identity_reason

                report[
                    "players"
                ].append(
                    detail
                )

                save_report(
                    report,
                    report_file,
                )

                write_log(
                    "CLUB V2 UNSAFE ID | "
                    f"{name} | "
                    f"{tm_id} | "
                    f"{identity_reason}"
                )

                time.sleep(
                    REQUEST_DELAY
                )

                continue

            # ==================================================
            # COMPARE
            # ==================================================

            (
                common,
                missing,
                extra,
            ) = compare_clubs(
                old_clubs,
                tm_clubs,
            )

            print()

            print(
                "JSON clubs:"
            )

            for club in old_clubs:

                print(
                    f"  - {club}"
                )

            print()

            print(
                "Transfermarkt clubs:"
            )

            for club in tm_clubs:

                print(
                    f"  - {club}"
                )

            print()

            print(
                f"ORTAK ({len(common)}):"
            )

            for club in common:

                print(
                    f"  = {club}"
                )

            if missing:

                print()

                print(
                    f"EKSİK ({len(missing)}):"
                )

                for club in missing:

                    print(
                        f"  + {club}"
                    )

            if extra:

                print()

                print(
                    "JSON'DA FAZLA / "
                    f"ŞÜPHELİ ({len(extra)}):"
                )

                for club in extra:

                    print(
                        f"  - {club}"
                    )

            # ==================================================
            # NEW CLUB LIST
            # ==================================================

            if args.replace:

                new_clubs = list(
                    tm_clubs
                )

            else:

                new_clubs = merge_clubs(
                    old_clubs,
                    tm_clubs,
                )

            old_keys = set(
                club_map(
                    old_clubs
                ).keys()
            )

            new_keys = set(
                club_map(
                    new_clubs
                ).keys()
            )

            changed = (
                old_keys
                !=
                new_keys
            )

            # ==================================================
            # CHANGE
            # ==================================================

            if changed:

                if backup is None:

                    backup = create_backup()

                    print()

                    print(
                        f"Backup oluşturuldu: "
                        f"{backup}"
                    )

                player[
                    "clubs"
                ] = new_clubs

                counters[
                    "updated"
                ] += 1

                counters[
                    "missing_added"
                ] += len(
                    missing
                )

                if args.replace:

                    counters[
                        "extra_removed"
                    ] += len(
                        extra
                    )

                print()

                print(
                    "GÜNCELLENDİ:"
                )

                print(
                    old_clubs
                )

                print(
                    "->"
                )

                print(
                    new_clubs
                )

            else:

                counters[
                    "same"
                ] += 1

                print()

                print(
                    "Değişiklik yok."
                )

            # ==================================================
            # MARK VERIFIED
            # ==================================================

            player[
                CHECK_FIELD
            ] = True

            player[
                "clubs_verified_at"
            ] = datetime.now().isoformat(
                timespec="seconds"
            )

            player[
                "clubs_verification_source"
            ] = (
                "transfermarkt_club_history_api"
            )

            player[
                "clubs_verification_mode"
            ] = (
                "replace"
                if args.replace
                else "merge"
            )

            detail[
                "status"
            ] = "VERIFIED"

            detail[
                "common"
            ] = common

            detail[
                "missing"
            ] = missing

            detail[
                "extra"
            ] = extra

            detail[
                "new_clubs"
            ] = new_clubs

            detail[
                "changed"
            ] = changed

            report[
                "players"
            ].append(
                detail
            )

            # ==================================================
            # SAVE AFTER EVERY SUCCESS
            # ==================================================

            atomic_save(
                players
            )

            save_report(
                report,
                report_file,
            )

            write_log(
                "CLUB V2 VERIFIED | "
                f"{name} | "
                f"{tm_id} | "
                f"changed={changed}"
            )

            # ==================================================
            # ETA
            # ==================================================

            player_duration = (
                time.perf_counter()
                -
                player_started
            )

            recent_durations.append(
                player_duration
            )

            average = (
                sum(
                    recent_durations
                )
                /
                len(
                    recent_durations
                )
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
                time.perf_counter()
                -
                run_started
            )

            print()

            print(
                f"updated: "
                f"{counters['updated']} | "
                f"same: "
                f"{counters['same']} | "
                f"duplicate: "
                f"{counters['duplicate_id']} | "
                f"404: "
                f"{counters['404']} | "
                f"errors: "
                f"{counters['errors']}"
            )

            print(
                f"elapsed: "
                f"{format_seconds(elapsed)} | "
                f"ETA: "
                f"{format_seconds(eta)}"
            )

            time.sleep(
                REQUEST_DELAY
            )

    except KeyboardInterrupt:

        print()

        print(
            "CTRL+C algılandı."
        )

        print(
            "Daha önce kaydedilmiş oyuncular korunuyor."
        )

    finally:

        report[
            "finished_at"
        ] = datetime.now().isoformat(
            timespec="seconds"
        )

        report[
            "counters"
        ] = counters

        save_report(
            report,
            report_file,
        )

    # ========================================================
    # FINAL
    # ========================================================

    print()

    print(
        "=" * 70
    )

    print(
        "TAMAMLANDI"
    )

    print(
        "=" * 70
    )

    print(
        f"İşlenen: "
        f"{counters['processed']}"
    )

    print(
        f"Güncellenen: "
        f"{counters['updated']}"
    )

    print(
        f"Değişmeyen: "
        f"{counters['same']}"
    )

    print(
        f"Duplicate ID nedeniyle atlanan: "
        f"{counters['duplicate_id']}"
    )

    print(
        f"Mevcut kulüp olmadığı için atlanan: "
        f"{counters['no_existing_clubs']}"
    )

    print(
        f"Hiç ortak kulüp olmadığı için atlanan: "
        f"{counters['no_common_club']}"
    )

    print(
        f"Zayıf kulüp eşleşmesi nedeniyle atlanan: "
        f"{counters['weak_overlap']}"
    )

    print(
        f"TM kulüp listesi boş: "
        f"{counters['empty_tm_clubs']}"
    )

    print(
        f"404: "
        f"{counters['404']}"
    )

    print(
        f"403: "
        f"{counters['403']}"
    )

    print(
        f"Diğer hata: "
        f"{counters['errors']}"
    )

    print(
        f"Eklenen eksik kulüp: "
        f"{counters['missing_added']}"
    )

    print(
        f"Kaldırılan fazla kulüp: "
        f"{counters['extra_removed']}"
    )

    print(
        f"Filtrelenen reserve/youth takım: "
        f"{counters['reserve_filtered']}"
    )

    if backup:

        print(
            f"Backup: {backup}"
        )

    print(
        f"Rapor: {report_file}"
    )


if __name__ == "__main__":
    main()