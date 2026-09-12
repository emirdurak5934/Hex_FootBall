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

import requests
from bs4 import BeautifulSoup


# =========================================================
# WINDOWS TERMINAL UNICODE
# =========================================================

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# =========================================================
# AYARLAR
# =========================================================

PLAYERS_FILE = Path("data/players.json")
LOG_FILE = Path("data/logs.txt")

DEFAULT_LIMIT = 10

TIMEOUT = 25
MAX_RETRIES = 2

RETRY_WAIT = 7

# 403 sonrası biraz daha uzun bekleme
FORBIDDEN_WAIT = 20

# Oyuncular arasında bekleme
REQUEST_DELAY = 2


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
# ÜLKE ALIAS'LARI
# =========================================================

COUNTRY_ALIASES = {

    # DR CONGO
    "dr congo":
        "Democratic Republic of the Congo",

    "d r congo":
        "Democratic Republic of the Congo",

    "democratic republic congo":
        "Democratic Republic of the Congo",

    "democratic republic of congo":
        "Democratic Republic of the Congo",

    "congo dr":
        "Democratic Republic of the Congo",

    # SOUTH KOREA
    "south korea":
        "South Korea",

    "korea republic":
        "South Korea",

    "republic of korea":
        "South Korea",

    # NORTH KOREA
    "north korea":
        "North Korea",

    "korea dpr":
        "North Korea",

    "dpr korea":
        "North Korea",

    # IVORY COAST
    "ivory coast":
        "Ivory Coast",

    "cote d ivoire":
        "Ivory Coast",

    # USA
    "usa":
        "United States",

    "united states of america":
        "United States",

    "united states":
        "United States",

    # UK HOME NATIONS
    "england":
        "England",

    "scotland":
        "Scotland",

    "wales":
        "Wales",

    "northern ireland":
        "Northern Ireland",

    # CZECHIA
    "czech republic":
        "Czech Republic",

    "czechia":
        "Czech Republic",

    # CAPE VERDE
    "cape verde":
        "Cape Verde",

    "cabo verde":
        "Cape Verde",
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
# JSON LOAD
# =========================================================

def load_players():

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

    PLAYERS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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

        # Geçici JSON tekrar okunarak doğrulanıyor
        with open(
            temp_path,
            "r",
            encoding="utf-8"
        ) as file:

            test_data = json.load(
                file
            )

        if (
            not isinstance(
                test_data,
                list
            )
            or
            len(test_data)
            !=
            len(players)
        ):

            raise ValueError(
                "Geçici players JSON doğrulanamadı."
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
        f"players_before_nationalities_{timestamp}.json"
    )

    shutil.copy2(
        PLAYERS_FILE,
        backup_file
    )

    return backup_file


# =========================================================
# TRANSFERMARKT ID
# =========================================================

def get_transfermarkt_id(player):

    # Öncelik açık Transfermarkt ID
    transfermarkt_id = str(
        player.get(
            "transfermarkt_id",
            ""
        )
    ).strip()

    if transfermarkt_id:

        return transfermarkt_id

    # Sonradan eklenen kayıtlar:
    # tm_missing_12345

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

            # =============================================
            # 403
            # =============================================

            if response.status_code == 403:

                last_error = "HTTP 403"

                # 403'te agresif retry yapmıyoruz.
                # Bir kez kısa bekleyip tekrar deneyebiliriz.

                if attempt < MAX_RETRIES:

                    print(
                        "Transfermarkt HTTP 403. "
                        f"{FORBIDDEN_WAIT} saniye bekleniyor..."
                    )

                    time.sleep(
                        FORBIDDEN_WAIT
                    )

                    continue

            # =============================================
            # 429
            # =============================================

            if response.status_code == 429:

                last_error = "HTTP 429"

                if attempt < MAX_RETRIES:

                    retry_after = (
                        response.headers.get(
                            "Retry-After"
                        )
                    )

                    try:

                        wait = int(
                            retry_after
                        )

                    except Exception:

                        wait = RETRY_WAIT

                    print(
                        f"HTTP 429. "
                        f"{wait} saniye bekleniyor..."
                    )

                    time.sleep(
                        wait
                    )

                    continue

            # =============================================
            # SERVER ERROR
            # =============================================

            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                last_error = (
                    f"HTTP "
                    f"{response.status_code}"
                )

                if attempt < MAX_RETRIES:

                    print(
                        f"Transfermarkt HTTP "
                        f"{response.status_code}. "
                        f"{RETRY_WAIT} saniye sonra "
                        "tekrar deneniyor..."
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
                    f"{RETRY_WAIT} saniye sonra "
                    "tekrar deneniyor..."
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
# SENIOR NATIONAL TEAM KONTROL
# =========================================================

def is_senior_national_team(
    team_name
):

    value = normalize(
        team_name
    )

    if not value:

        return False

    blocked_words = (
        "women",
        "woman",
        "youth",
        "olympic",
        "reserve",
        "academy",
        "b team",
        "caps goals",
        "appearances",
        "international matches",
    )

    for word in blocked_words:

        if word in value:

            return False

    # U15-U23
    if re.search(
        r"\bu\s*(15|16|17|18|19|20|21|22|23)\b",
        value
    ):

        return False

    # Under-15 vb
    if re.search(
        r"\bunder\s*(15|16|17|18|19|20|21|22|23)\b",
        value
    ):

        return False

    return True


# =========================================================
# ÜLKE ADINI TEMİZLE
# =========================================================

def clean_country_name(
    team_name
):

    team_name = str(
        team_name or ""
    ).strip()

    suffixes = (
        " men's national association football team",
        " men's national football team",
        " national association football team",
        " national football team",
        " National Team",
        " national team",
    )

    lowered = team_name.lower()

    for suffix in suffixes:

        if lowered.endswith(
            suffix.lower()
        ):

            team_name = team_name[
                :-len(suffix)
            ].strip()

            break

    return team_name


# =========================================================
# ÜLKE ADINI CANONICAL YAP
# =========================================================

def canonical_country_name(
    value
):

    value = clean_country_name(
        value
    )

    key = normalize(
        value
    )

    return COUNTRY_ALIASES.get(
        key,
        value
    )


# =========================================================
# GEÇERLİ TAKIM ADAYI MI?
# =========================================================

def valid_national_team_candidate(
    value
):

    value = str(
        value or ""
    ).strip()

    if not value:

        return False

    normalized = normalize(
        value
    )

    blocked_prefixes = (
        "caps goals",
        "caps goal",
        "caps",
        "goals",
        "appearances",
        "international matches",
        "debut",
    )

    for blocked in blocked_prefixes:

        if normalized.startswith(
            blocked
        ):

            return False

    # Caps/Goals gibi text
    if (
        "caps goals"
        in normalized
    ):

        return False

    # Sadece istatistik
    if re.fullmatch(
        r"[\d\s:/\-]+",
        value
    ):

        return False

    # Takım/ülke adında rakam istemiyoruz
    if re.search(
        r"\d",
        value
    ):

        return False

    if not is_senior_national_team(
        value
    ):

        return False

    return True


# =========================================================
# LABEL SONRASI VALUE
# =========================================================

def get_value_after_label(
    soup,
    label_text
):

    pattern = re.compile(
        rf"^\s*"
        rf"{re.escape(label_text)}"
        rf"\s*:?\s*$",
        re.I
    )

    label = soup.find(
        string=pattern
    )

    if not label:

        return ""

    parent = label.parent

    if not parent:

        return ""

    sibling = (
        parent.find_next_sibling()
    )

    if sibling:

        value = sibling.get_text(
            " ",
            strip=True
        )

        if value:

            return value

    if parent.parent:

        whole_text = (
            parent.parent.get_text(
                " ",
                strip=True
            )
        )

        whole_text = re.sub(
            rf"^\s*"
            rf"{re.escape(label_text)}"
            rf"\s*:?\s*",
            "",
            whole_text,
            flags=re.I
        )

        return whole_text.strip()

    return ""


# =========================================================
# CAPS/GOALS TEMİZLE
# =========================================================

def clean_profile_team_value(
    value
):

    value = str(
        value or ""
    ).strip()

    if not value:

        return ""

    # Portugal Caps/Goals: 233 / 146
    value = re.split(
        r"\bCaps\s*/\s*Goals\s*:",
        value,
        maxsplit=1,
        flags=re.I
    )[0]

    # Caps:
    value = re.split(
        r"\bCaps\s*:",
        value,
        maxsplit=1,
        flags=re.I
    )[0]

    # Appearances:
    value = re.split(
        r"\bAppearances\s*:",
        value,
        maxsplit=1,
        flags=re.I
    )[0]

    value = re.sub(
        r"\s+\d+\s*/\s*\d+\s*$",
        "",
        value
    )

    value = re.sub(
        r"\s+\([^)]*\)\s*$",
        "",
        value
    )

    return value.strip()


# =========================================================
# TRANSFERMARKT PROFİLİNİ PARSE ET
# =========================================================

def parse_senior_national_team(
    html
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    candidates = []

    # =====================================================
    # METHOD 1
    # NATIONALMANNSCHAFT LINK
    # =====================================================

    national_links = soup.select(
        'a[href*="/nationalmannschaft/spieler/"]'
    )

    for link in national_links:

        team_name = str(
            link.get(
                "title",
                ""
            )
        ).strip()

        href = str(
            link.get(
                "href",
                ""
            )
        )

        team_name = (
            clean_profile_team_value(
                team_name
            )
        )

        if valid_national_team_candidate(
            team_name
        ):

            candidates.append(
                team_name
            )

            continue

        team_id_match = re.search(
            r"verein_id/(\d+)",
            href
        )

        if not team_id_match:

            continue

        team_id = (
            team_id_match.group(1)
        )

        possible_links = soup.select(
            f'a[href*="/verein/{team_id}"]'
        )

        for possible in possible_links:

            possible_name = (
                str(
                    possible.get(
                        "title",
                        ""
                    )
                ).strip()
                or
                possible.get_text(
                    " ",
                    strip=True
                )
            )

            possible_name = (
                clean_profile_team_value(
                    possible_name
                )
            )

            if valid_national_team_candidate(
                possible_name
            ):

                candidates.append(
                    possible_name
                )

                break

    # =====================================================
    # METHOD 2
    # LABELS
    # =====================================================

    labels = (
        "Current international",
        "Former International",
        "Former international",
        "National player",
        "International",
    )

    for label_text in labels:

        value = get_value_after_label(
            soup,
            label_text
        )

        value = (
            clean_profile_team_value(
                value
            )
        )

        if valid_national_team_candidate(
            value
        ):

            candidates.append(
                value
            )

    # =====================================================
    # METHOD 3
    # PAGE TEXT
    # =====================================================

    page_text = soup.get_text(
        " ",
        strip=True
    )

    patterns = (

        (
            r"Current international\s*:\s*"
            r"(.{2,60}?)"
            r"\s+Caps\s*/\s*Goals\s*:"
        ),

        (
            r"Former International\s*:\s*"
            r"(.{2,60}?)"
            r"\s+Caps\s*/\s*Goals\s*:"
        ),

        (
            r"Former international\s*:\s*"
            r"(.{2,60}?)"
            r"\s+Caps\s*/\s*Goals\s*:"
        ),

        (
            r"National player\s*:\s*"
            r"(.{2,60}?)"
            r"\s+Caps\s*/\s*Goals\s*:"
        ),
    )

    for pattern in patterns:

        match = re.search(
            pattern,
            page_text,
            flags=re.I
        )

        if not match:

            continue

        value = (
            match.group(1)
            .strip()
        )

        value = (
            clean_profile_team_value(
                value
            )
        )

        if valid_national_team_candidate(
            value
        ):

            candidates.append(
                value
            )

    # =====================================================
    # NORMALIZE + ALIAS
    # =====================================================

    countries = {}

    for candidate in candidates:

        candidate = (
            clean_profile_team_value(
                candidate
            )
        )

        if not valid_national_team_candidate(
            candidate
        ):

            continue

        country = (
            canonical_country_name(
                candidate
            )
        )

        # SON GÜVENLİK
        if not valid_national_team_candidate(
            country
        ):

            continue

        key = normalize(
            country
        )

        if not key:

            continue

        countries[
            key
        ] = country

    unique_countries = list(
        countries.values()
    )

    # =====================================================
    # RESULT
    # =====================================================

    if len(
        unique_countries
    ) == 1:

        return {
            "status":
                "FOUND",

            "country":
                unique_countries[0],

            "candidates":
                unique_countries
        }

    if len(
        unique_countries
    ) > 1:

        return {
            "status":
                "AMBIGUOUS",

            "country":
                "",

            "candidates":
                unique_countries
        }

    return {
        "status":
            "NO_SENIOR_NATIONAL_TEAM",

        "country":
            "",

        "candidates":
            []
    }


# =========================================================
# TRANSFERMARKT PROFİLİ
# =========================================================

def get_player_national_team(
    session,
    transfermarkt_id
):

    # İlk URL
    url = (
        "https://www.transfermarkt.com/-/"
        f"profil/spieler/"
        f"{transfermarkt_id}"
    )

    response = safe_get(
        session,
        url
    )

    return parse_senior_national_team(
        response.text
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
            "nationality_checked true olmayan "
            "Transfermarkt ID'li tüm oyuncuları işle."
        )
    )

    parser.add_argument(
        "--recheck-all",
        action="store_true",
        help=(
            "nationality_checked değerine bakmadan "
            "Transfermarkt ID bulunan tüm oyuncuları "
            "baştan kontrol et."
        )
    )

    return parser.parse_args()


# =========================================================
# TIME FORMAT
# =========================================================

def format_time(
    seconds
):

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
# MAIN
# =========================================================

def main():

    args = parse_args()

    if (
        args.all
        and
        args.recheck_all
    ):

        raise SystemExit(
            "--all ve --recheck-all "
            "aynı anda kullanılamaz."
        )

    if args.limit < 1:

        raise SystemExit(
            "--limit 1 veya daha büyük olmalı."
        )

    players = load_players()

    print(
        f"Toplam oyuncu: "
        f"{len(players)}"
    )

    # =====================================================
    # SELECT
    # =====================================================

    if args.recheck_all:

        selected = [
            player
            for player in players
            if get_transfermarkt_id(
                player
            )
        ]

    else:

        pending = [
            player
            for player in players

            if
            get_transfermarkt_id(
                player
            )

            and

            player.get(
                "nationality_checked"
            ) is not True
        ]

        if args.all:

            selected = pending

        else:

            selected = pending[
                :args.limit
            ]

    print(
        f"Kontrol edilecek oyuncu: "
        f"{len(selected)}"
    )

    if not selected:

        print(
            "Kontrol edilecek oyuncu yok."
        )

        return

    # =====================================================
    # SESSION
    # =====================================================

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    backup_file = None

    # =====================================================
    # COUNTERS
    # =====================================================

    updated = 0

    unchanged = 0

    no_senior = 0

    ambiguous = 0

    failed = 0

    start_time = (
        time.time()
    )

    recent_times = []

    # =====================================================
    # LOOP
    # =====================================================

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

            transfermarkt_id = (
                get_transfermarkt_id(
                    player
                )
            )

            old_value = str(
                player.get(
                    "nationality",
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
                f"Transfermarkt ID: "
                f"{transfermarkt_id}"
            )

            try:

                result = (
                    get_player_national_team(
                        session,
                        transfermarkt_id
                    )
                )

                status = str(
                    result.get(
                        "status",
                        ""
                    )
                )

                country = str(
                    result.get(
                        "country",
                        ""
                    )
                ).strip()

                candidates = result.get(
                    "candidates",
                    []
                )

                changed = False

                # =================================================
                # FOUND
                # =================================================

                if status == "FOUND":

                    # SON GÜVENLİK

                    normalized_country = (
                        normalize(
                            country
                        )
                    )

                    if (
                        not country
                        or
                        "caps" in normalized_country
                        or
                        "goals" in normalized_country
                        or
                        "appearances" in normalized_country
                        or
                        re.search(
                            r"\d",
                            country
                        )
                    ):

                        raise ValueError(
                            "Geçersiz milli takım "
                            "değeri yakalandı: "
                            f"{country}"
                        )

                    print(
                        f"A milli takım: "
                        f"{country}"
                    )

                    print(
                        f"Eski nationality: "
                        f"{old_value or 'BOŞ'}"
                    )

                    if (
                        normalize(
                            old_value
                        )
                        !=
                        normalize(
                            country
                        )
                    ):

                        player[
                            "nationality"
                        ] = country

                        updated += 1

                        changed = True

                        print(
                            "GÜNCELLENDİ:"
                        )

                        print(
                            f"{old_value or 'BOŞ'} "
                            f"-> "
                            f"{country}"
                        )

                        write_log(
                            "NATIONALITY UPDATE | "
                            f"{name} | "
                            f"{old_value} -> "
                            f"{country}"
                        )

                    else:

                        unchanged += 1

                        print(
                            "Değişiklik yok."
                        )

                        write_log(
                            "NATIONALITY UNCHANGED | "
                            f"{name} | "
                            f"{country}"
                        )

                    # Güvenilir sorgu tamamlandı
                    if (
                        player.get(
                            "nationality_checked"
                        )
                        is not True
                    ):

                        player[
                            "nationality_checked"
                        ] = True

                        changed = True

                # =================================================
                # NO SENIOR
                # =================================================

                elif (
                    status
                    ==
                    "NO_SENIOR_NATIONAL_TEAM"
                ):

                    no_senior += 1

                    print(
                        "A milli takım bulunamadı."
                    )

                    print(
                        "Mevcut nationality korunuyor:",
                        old_value or "BOŞ"
                    )

                    # Profil başarıyla okundu.
                    # Youth / vatandaşlık yazmıyoruz.

                    if (
                        player.get(
                            "nationality_checked"
                        )
                        is not True
                    ):

                        player[
                            "nationality_checked"
                        ] = True

                        changed = True

                    write_log(
                        "NO SENIOR NATIONAL TEAM | "
                        f"{name} | "
                        f"{transfermarkt_id}"
                    )

                # =================================================
                # AMBIGUOUS
                # =================================================

                elif status == "AMBIGUOUS":

                    ambiguous += 1

                    print(
                        "Birden fazla senior milli takım "
                        "adayı bulundu."
                    )

                    print(
                        "Adaylar:",
                        candidates
                    )

                    print(
                        "Nationality değiştirilmedi."
                    )

                    # Belirsiz olduğu için checked=true YAPMA

                    write_log(
                        "NATIONALITY AMBIGUOUS | "
                        f"{name} | "
                        f"{candidates}"
                    )

                else:

                    raise ValueError(
                        "Bilinmeyen status: "
                        f"{status}"
                    )

                # =================================================
                # SAVE
                # =================================================

                if changed:

                    if backup_file is None:

                        backup_file = (
                            create_backup()
                        )

                        print(
                            "Backup oluşturuldu: "
                            f"{backup_file}"
                        )

                    save_players_atomic(
                        players
                    )

            except Exception as error:

                failed += 1

                print(
                    "HATA:",
                    error
                )

                write_log(
                    "NATIONALITY FAILED | "
                    f"{name} | "
                    f"{transfermarkt_id} | "
                    f"{error}"
                )

                # Hata varsa nationality_checked dokunulmaz.

            # =====================================================
            # ETA
            # =====================================================

            player_duration = (
                time.time()
                -
                player_start
            )

            recent_times.append(
                player_duration
            )

            if len(
                recent_times
            ) > 20:

                recent_times.pop(
                    0
                )

            average = (
                sum(
                    recent_times
                )
                /
                len(
                    recent_times
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
                time.time()
                -
                start_time
            )

            print()

            print(
                f"updated: {updated} | "
                f"unchanged: {unchanged} | "
                f"no senior: {no_senior} | "
                f"ambiguous: {ambiguous} | "
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
            "Script kullanıcı tarafından "
            "durduruldu."
        )

        print(
            "Daha önce kaydedilen "
            "değişiklikler korundu."
        )

        write_log(
            "NATIONALITY SCRIPT INTERRUPTED"
        )

    # =====================================================
    # FINAL
    # =====================================================

    print()

    print(
        "================================"
    )

    print(
        "MİLLİYET KONTROLÜ BİTTİ"
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
        f"No senior national team: "
        f"{no_senior}"
    )

    print(
        f"Ambiguous: {ambiguous}"
    )

    print(
        f"Failed: {failed}"
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