import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Transfermarkt-only enrichment for needs_enrichment players.

This script intentionally does NOT use Wikidata.
It enriches:
- senior club history
- birth date
- positions
- senior national team (from Transfermarkt profile when available)

Safe behavior:
- test mode by default (--limit 10)
- --all is required for bulk processing
- atomic saves
- one backup per run
- completed players are skipped on later runs
"""

import argparse
from collections import deque
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import unicodedata
from difflib import SequenceMatcher

import requests
from bs4 import BeautifulSoup


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


PLAYERS_FILE = Path("data/players.json")
LOG_FILE = Path("data/logs.txt")

DEFAULT_LIMIT = 10

# Transfermarkt request policy
TIMEOUT = 25
MAX_RETRIES = 2
RETRY_BACKOFF = 7
REQUEST_DELAY = 2
ETA_WINDOW_SIZE = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

POSITION_MAP = {
    "goalkeeper": "Goalkeeper",
    "keeper": "Goalkeeper",
    "centre-back": "Centre-Back",
    "center-back": "Centre-Back",
    "central defender": "Centre-Back",
    "left-back": "Left-Back",
    "left back": "Left-Back",
    "right-back": "Right-Back",
    "right back": "Right-Back",
    "defensive midfield": "Defensive Midfield",
    "defensive midfielder": "Defensive Midfield",
    "central midfield": "Central Midfield",
    "central midfielder": "Central Midfield",
    "attacking midfield": "Attacking Midfield",
    "attacking midfielder": "Attacking Midfield",
    "left midfield": "Left Midfield",
    "right midfield": "Right Midfield",
    "left winger": "Left Winger",
    "right winger": "Right Winger",
    "second striker": "Second Striker",
    "centre-forward": "Centre-Forward",
    "center-forward": "Centre-Forward",
    "centre forward": "Centre-Forward",
    "center forward": "Centre-Forward",
}

YOUTH_CLUB_MARKERS = (
    " u15", " u16", " u17", " u18", " u19", " u20", " u21", " u23",
    " under 15", " under 16", " under 17", " under 18", " under 19",
    " under 20", " under 21", " under 23",
    " youth", " academy", " reserve", " reserves", " junior", " juniors",
    " ii", " b team", " b-team", " amateur", " amateurs",
)

NON_CLUB_MARKERS = (
    "without club", "retired", "career break", "unknown",
)

NATIONAL_FOUND = "FOUND"
NO_SENIOR_NATIONAL_TEAM = "NO_SENIOR_NATIONAL_TEAM"
TRANSFERMARKT_FAILED = "TRANSFERMARKT_FAILED"


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def club_key(value):
    key = normalize(value)
    tokens = key.split()

    if len(tokens) >= 2 and tokens[-2:] == ["f", "c"]:
        tokens = tokens[:-2]

    while tokens and tokens[-1] in {
        "fc", "cf", "afc", "sc", "fk", "sk", "jk"
    }:
        tokens.pop()

    return " ".join(tokens)


def names_match(existing, fetched):
    first = normalize(existing)
    second = normalize(fetched)

    if not first or not second:
        return False

    if first == second:
        return True

    return SequenceMatcher(
        None,
        first,
        second,
    ).ratio() >= 0.82


def is_senior_national_team_name(name):
    lowered = normalize(name)

    if not lowered:
        return False

    blocked = (
        "women",
        "youth",
        "olympic",
        "b team",
        "b-team",
    )

    if any(item in lowered for item in blocked):
        return False

    if re.search(
        r"\b(?:u|under)\s*(?:15|16|17|18|19|20|21|22|23)\b",
        lowered,
    ):
        return False

    return True


def clean_national_team_name(name):
    value = str(name or "").strip()

    suffixes = (
        " men's national association football team",
        " men's national football team",
        " national association football team",
        " national football team",
    )

    lowered = value.lower()

    for suffix in suffixes:
        if lowered.endswith(suffix):
            value = value[: -len(suffix)].strip()
            break

    return value



def is_valid_national_team_label(name):
    """Return True only for plausible senior national-team/country labels."""
    value = str(name or "").strip()

    if not value:
        return False

    normalized = normalize(value)

    if not normalized:
        return False

    blocked_phrases = (
        "caps goals",
        "caps goal",
        "appearances",
        "appearance",
        "squad",
        "matches",
        "match",
        "market value",
        "contract",
        "joined",
        "height",
        "foot",
        "player agent",
        "date of birth",
        "place of birth",
        "citizenship",
        "position",
    )

    if any(phrase in normalized for phrase in blocked_phrases):
        return False

    if ":" in value or "/" in value:
        return False

    if re.search(r"\b\d+\b", value):
        return False

    return is_senior_national_team_name(value)


def write_log(message):
    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with LOG_FILE.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            f"{datetime.now().isoformat(timespec='seconds')} | "
            f"{message}\n"
        )


def load_players():
    with PLAYERS_FILE.open(
        "r",
        encoding="utf-8",
    ) as handle:
        players = json.load(handle)

    if not isinstance(players, list):
        raise ValueError(
            "players.json root must be a list"
        )

    return players


def atomic_save(players):
    PLAYERS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temp_name = tempfile.mkstemp(
        prefix=f"{PLAYERS_FILE.name}.",
        suffix=".tmp",
        dir=PLAYERS_FILE.parent,
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                players,
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        with open(
            temp_name,
            "r",
            encoding="utf-8",
        ) as handle:
            validated = json.load(
                handle
            )

        if (
            not isinstance(validated, list)
            or len(validated) != len(players)
        ):
            raise ValueError(
                "temporary players JSON validation failed"
            )

        os.replace(
            temp_name,
            PLAYERS_FILE,
        )

    finally:
        if os.path.exists(
            temp_name
        ):
            os.unlink(
                temp_name
            )


def create_backup():
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup = PLAYERS_FILE.with_name(
        "players_before_tm_only_enrichment_"
        f"{timestamp}.json"
    )

    shutil.copy2(
        PLAYERS_FILE,
        backup,
    )

    return backup


def retry_after_seconds(response):
    value = response.headers.get(
        "Retry-After",
        "",
    ).strip()

    if not value:
        return None

    try:
        return max(
            0,
            int(value),
        )
    except ValueError:
        return None


def safe_get(session, url, params=None):
    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        try:
            response = session.get(
                url,
                params=params,
                timeout=TIMEOUT,
            )

            if response.status_code == 429:
                last_error = RuntimeError(
                    "HTTP 429"
                )

                if attempt < MAX_RETRIES:
                    wait_seconds = (
                        retry_after_seconds(response)
                        or RETRY_BACKOFF
                    )

                    print(
                        "Transfermarkt 429. "
                        f"{wait_seconds} saniye bekleniyor..."
                    )

                    time.sleep(
                        wait_seconds
                    )
                    continue

            if response.status_code in {
                500,
                502,
                503,
                504,
            }:
                last_error = RuntimeError(
                    f"HTTP {response.status_code}"
                )

                if attempt < MAX_RETRIES:
                    print(
                        f"Transfermarkt HTTP {response.status_code}. "
                        f"{RETRY_BACKOFF} saniye sonra tekrar..."
                    )

                    time.sleep(
                        RETRY_BACKOFF
                    )
                    continue

            response.raise_for_status()
            return response

        except (
            requests.Timeout,
            requests.ConnectionError,
        ) as error:
            last_error = error

            if attempt < MAX_RETRIES:
                print(
                    "Transfermarkt bağlantı hatası. "
                    f"{RETRY_BACKOFF} saniye sonra tekrar..."
                )

                time.sleep(
                    RETRY_BACKOFF
                )
                continue

        except requests.RequestException as error:
            last_error = error
            break

    raise RuntimeError(
        f"Transfermarkt request failed: {last_error}"
    )


def value_after_label(soup, label):
    label_pattern = re.compile(
        rf"^\s*{re.escape(label)}\s*:?\s*$",
        re.I,
    )

    node = soup.find(
        string=label_pattern
    )

    if not node:
        return ""

    parent = node.parent

    sibling = (
        parent.find_next_sibling()
        if parent
        else None
    )

    if sibling:
        return sibling.get_text(
            " ",
            strip=True,
        )

    text = (
        parent.parent.get_text(
            " ",
            strip=True,
        )
        if parent and parent.parent
        else ""
    )

    return re.sub(
        rf"^\s*{re.escape(label)}\s*:?\s*",
        "",
        text,
        flags=re.I,
    )


def parse_birth_date(soup):
    node = soup.select_one(
        '[itemprop="birthDate"]'
    )

    raw = (
        node.get("content", "")
        if node
        else ""
    )

    if not raw and node:
        raw = node.get_text(
            " ",
            strip=True,
        )

    if not raw:
        raw = value_after_label(
            soup,
            "Date of birth/Age",
        )

    iso_match = re.search(
        r"\b(\d{4})-(\d{2})-(\d{2})\b",
        raw,
    )

    if iso_match:
        return iso_match.group(0)

    cleaned = re.sub(
        r"\s*\([^)]*\)\s*$",
        "",
        raw,
    ).strip()

    for pattern in (
        "%b %d, %Y",
        "%B %d, %Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ):
        try:
            return datetime.strptime(
                cleaned,
                pattern,
            ).strftime(
                "%Y-%m-%d"
            )
        except ValueError:
            pass

    return ""


def parse_positions(soup):
    raw = value_after_label(
        soup,
        "Position",
    )

    if not raw:
        for label in soup.select(
            ".info-table__content--regular"
        ):
            if normalize(
                label.get_text(
                    " ",
                    strip=True,
                )
            ).startswith(
                "position"
            ):
                value = label.find_next(
                    class_="info-table__content--bold"
                )

                if value:
                    raw = value.get_text(
                        " ",
                        strip=True,
                    )

                break

    if not raw:
        page_text = soup.get_text(
            " ",
            strip=True,
        )

        match = re.search(
            r"Position\s*:\s*(.{1,100}?)"
            r"(?:\s+Foot\s*:|\s+Player agent\s*:|$)",
            page_text,
            flags=re.I,
        )

        if match:
            raw = match.group(1)

    def recognized_positions(value):
        normalized_value = normalize(
            value
        )

        found = []

        for source, canonical in POSITION_MAP.items():
            if normalize(
                source
            ) in normalized_value:
                found.append(
                    canonical
                )

        return found

    positions = recognized_positions(
        raw
    )

    if not positions:
        page_text = soup.get_text(
            " ",
            strip=True,
        )

        for match in re.finditer(
            r"Position\s*:\s*([^:]{1,100})",
            page_text,
            re.I,
        ):
            positions = recognized_positions(
                match.group(1)
            )

            if positions:
                break

    return list(
        dict.fromkeys(
            positions
        )
    )


def extract_tm_national_team(soup):
    """
    Transfermarkt profilinden A milli takım bilgisini bulmaya çalışır.

    Returns:
        (team_name, caps, evidence_found)
    """

    candidates = []

    for link in soup.select(
        'a[href*="/nationalmannschaft/spieler/"]'
    ):
        text = link.get_text(
            " ",
            strip=True,
        )

        href = link.get(
            "href",
            "",
        )

        team_name = (
            link.get(
                "title",
                "",
            ).strip()
        )

        caps_match = re.search(
            r"\b(\d+)\b",
            text,
        )

        caps = (
            int(caps_match.group(1))
            if caps_match
            else 0
        )

        if not team_name:
            team_id_match = re.search(
                r"verein_id/(\d+)",
                href,
            )

            if team_id_match:
                team_link = soup.select_one(
                    f'a[href*="/startseite/verein/'
                    f'{team_id_match.group(1)}"]'
                )

                if team_link:
                    team_name = (
                        team_link.get(
                            "title",
                            "",
                        ).strip()
                        or team_link.get_text(
                            " ",
                            strip=True,
                        )
                    )

        if team_name:
            candidates.append(
                (
                    team_name,
                    caps,
                    True,
                )
            )

    label_names = (
        "Current international",
        "National player",
        "Former International",
        "International",
    )

    for label_name in label_names:
        value = value_after_label(
            soup,
            label_name,
        )

        if not value:
            continue

        cleaned = re.sub(
            r"\s+\(.*?\)\s*$",
            "",
            value,
        ).strip()

        cleaned = re.sub(
            r"\s+\d+\s+(?:caps?|appearances?).*$",
            "",
            cleaned,
            flags=re.I,
        ).strip()

        caps_match = re.search(
            r"\b(\d+)\s+(?:caps?|appearances?)\b",
            value,
            flags=re.I,
        )

        caps = (
            int(caps_match.group(1))
            if caps_match
            else 0
        )

        if cleaned:
            candidates.append(
                (
                    cleaned,
                    caps,
                    True,
                )
            )

    for team_name, caps, evidence in candidates:
        cleaned_team = clean_national_team_name(
            team_name
        )

        if is_valid_national_team_label(
            cleaned_team
        ):
            return (
                cleaned_team,
                caps,
                evidence,
            )

    return "", 0, bool(candidates)


def parse_profile(response):
    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    heading = (
        soup.select_one(
            "h1.data-header__headline-wrapper"
        )
        or soup.select_one("h1")
    )

    name = (
        heading.get_text(
            " ",
            strip=True,
        )
        if heading
        else ""
    )

    name = re.sub(
        r"^#\d+\s*",
        "",
        name,
    ).strip()

    national_team, national_caps, national_evidence = (
        extract_tm_national_team(
            soup
        )
    )

    return {
        "name": name,
        "birthDate": parse_birth_date(
            soup
        ),
        "positions": parse_positions(
            soup
        ),
        "tm_national_team": national_team,
        "tm_national_caps": national_caps,
        "tm_national_evidence": national_evidence,
    }


def is_senior_club(
    name,
    is_national_team=False,
):
    key = f" {normalize(name)}"

    if (
        is_national_team
        or not normalize(name)
        or "national team" in key
    ):
        return False

    return not any(
        marker in key
        for marker in (
            *YOUTH_CLUB_MARKERS,
            *NON_CLUB_MARKERS,
        )
    )


def fetch_transfer_clubs(session, transfermarkt_id):

    history_url = (
        "https://tmapi.transfermarkt.technology/"
        "transfer/history/player/"
        f"{transfermarkt_id}"
    )

    history_response = safe_get(
        session,
        history_url,
    )

    payload = history_response.json()

    if not payload.get("success"):
        raise ValueError(
            "Transfermarkt transfer history response invalid"
        )

    history_data = payload.get("data")

    if not history_data:
        return []

    club_ids_raw = history_data.get(
        "clubIds",
        []
    )

    club_ids = []

    for value in club_ids_raw:

        value = str(value).strip()

        if not value:
            continue

        if value == "0":
            continue

        if value not in club_ids:
            club_ids.append(value)

    if not club_ids:
        return []

    params = []

    for club_id in club_ids:

        params.append(
            (
                "ids[]",
                club_id
            )
        )

    clubs_response = safe_get(
        session,
        "https://tmapi.transfermarkt.technology/clubs",
        params=params,
    )

    clubs_payload = clubs_response.json()

    if not clubs_payload.get("success"):
        raise ValueError(
            "Transfermarkt club entity response invalid"
        )

    club_entities = clubs_payload.get(
        "data",
        []
    )

    if not isinstance(
        club_entities,
        list
    ):
        raise ValueError(
            "Transfermarkt clubs response data is not a list"
        )

    clubs = []

    seen_clubs = set()

    for entity in club_entities:

        if not isinstance(
            entity,
            dict
        ):
            continue

        name = str(
            entity.get(
                "name",
                ""
            )
        ).strip()

        if not name:
            continue

        base_details = (
            entity.get(
                "baseDetails"
            )
            or {}
        )

        is_national_team = bool(
            base_details.get(
                "isNationalTeam"
            )
        )

        if not is_senior_club(
            name,
            is_national_team,
        ):
            continue

        key = club_key(name)

        if not key:
            continue

        if key in seen_clubs:
            continue

        seen_clubs.add(key)

        clubs.append(name)

    return clubs


def fetch_transfermarkt_player(session, transfermarkt_id):
    """Fetch and combine Transfermarkt profile details and senior club history."""

    profile_url = (
        "https://www.transfermarkt.com/-/profil/spieler/"
        f"{transfermarkt_id}"
    )

    profile_response = safe_get(
        session,
        profile_url,
    )

    fetched = parse_profile(
        profile_response
    )

    if not fetched.get("name"):
        raise ValueError(
            "Transfermarkt profile response invalid: player name missing"
        )

    fetched["clubs"] = fetch_transfer_clubs(
        session,
        transfermarkt_id,
    )

    return fetched


def merge_clubs(
    existing,
    incoming,
):
    merged = (
        list(existing)
        if isinstance(
            existing,
            list,
        )
        else []
    )

    known = {
        club_key(value)
        for value in merged
    }

    added = []

    for club in incoming:
        key = club_key(
            club
        )

        if (
            key
            and key not in known
        ):
            merged.append(
                club
            )
            added.append(
                club
            )
            known.add(
                key
            )

    return merged, added


def determine_national_team_status(
    fetched,
):
    team = str(
        fetched.get(
            "tm_national_team",
            "",
        )
    ).strip()

    cleaned_team = clean_national_team_name(
        team
    )

    if (
        cleaned_team
        and is_valid_national_team_label(
            cleaned_team
        )
    ):
        return (
            cleaned_team,
            NATIONAL_FOUND,
        )

    return (
        "",
        NO_SENIOR_NATIONAL_TEAM,
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Enrich needs_enrichment players "
            "using Transfermarkt only."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=(
            "Safe test mode player count "
            "(default: 10)"
        ),
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Process every "
            "needs_enrichment=true player"
        ),
    )

    parser.add_argument(
        "--transfermarkt-ids",
        help=(
            "Comma-separated Transfermarkt IDs "
            "for manual test"
        ),
    )

    return parser.parse_args()


def format_duration(seconds):
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

    if hours:
        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )

    return (
        f"{minutes:02d}:"
        f"{seconds:02d}"
    )


def print_progress(
    index,
    total,
    player_name,
    completed,
    failed,
    started,
    recent_durations,
):
    elapsed = (
        time.perf_counter()
        - started
    )

    if recent_durations:
        average = (
            sum(recent_durations)
            / len(recent_durations)
        )
    else:
        average = (
            elapsed
            / max(
                1,
                index,
            )
        )

    remaining = max(
        0,
        total - index,
    )

    eta = (
        average
        * remaining
    )

    print()

    print(
        f"{index} / {total} - "
        f"{player_name}"
    )

    print(
        f"completed: {completed} | "
        f"still pending: "
        f"{max(0, total - index)} | "
        f"failed: {failed} | "
        f"elapsed: {format_duration(elapsed)} | "
        f"ETA: {format_duration(eta)}"
    )


def main():
    args = parse_args()

    if args.limit < 1:
        raise SystemExit(
            "--limit must be positive"
        )

    players = load_players()

    explicit_id_list = [
        value.strip()
        for value in (
            args.transfermarkt_ids
            or ""
        ).split(",")
        if value.strip()
    ]

    explicit_ids = set(
        explicit_id_list
    )

    if explicit_ids:
        selected = [
            player
            for player in players
            if str(
                player.get(
                    "transfermarkt_id",
                    "",
                )
            ) in explicit_ids
        ]

        selected.sort(
            key=lambda player: (
                explicit_id_list.index(
                    str(
                        player.get(
                            "transfermarkt_id",
                            "",
                        )
                    )
                )
            )
        )

    else:
        eligible = [
            player
            for player in players
            if player.get(
                "needs_enrichment"
            ) is True
        ]

        selected = (
            eligible
            if args.all
            else eligible[
                :args.limit
            ]
        )

    mode = (
        "BULK MODE"
        if args.all
        else "SAFE TEST MODE"
    )

    print(
        f"{mode} | "
        f"selected players: "
        f"{len(selected)}"
    )

    print(
        "SOURCE: Transfermarkt only | "
        f"timeout={TIMEOUT}s | "
        f"attempts={MAX_RETRIES}"
    )

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    backup = None

    counters = {
        "processed": 0,
        "transfermarkt_success": 0,
        "clubs_expanded": 0,
        "birthdates_found": 0,
        "positions_found": 0,
        "national_team_found": 0,
        "no_senior_national_team": 0,
        "completed": 0,
        "failed": 0,
        "errors": 0,
    }

    details = []

    run_started = (
        time.perf_counter()
    )

    recent_durations = deque(
        maxlen=ETA_WINDOW_SIZE
    )

    try:
        for (
            player_index,
            player,
        ) in enumerate(
            selected,
            start=1,
        ):

            name = str(
                player.get(
                    "name",
                    "",
                )
            ).strip()

            transfermarkt_id = str(
                player.get(
                    "transfermarkt_id",
                    "",
                )
            ).strip()

            old_clubs = list(
                player.get(
                    "clubs",
                    [],
                )
            )

            print()

            print(
                f"{player_index} / "
                f"{len(selected)} - "
                f"{name}"
            )

            write_log(
                "TM_ONLY ENRICH START | "
                f"{name} | "
                f"{transfermarkt_id}"
            )

            counters[
                "processed"
            ] += 1

            player_started = (
                time.perf_counter()
            )

            detail = {
                "player": name,
                "transfermarkt_id":
                    transfermarkt_id,
                "old_clubs":
                    old_clubs,
                "added_clubs": [],
            }

            try:
                if not transfermarkt_id:
                    raise ValueError(
                        "transfermarkt_id missing"
                    )

                fetched = (
                    fetch_transfermarkt_player(
                        session,
                        transfermarkt_id,
                    )
                )

                fetched_name = str(
                    fetched.get(
                        "name",
                        "",
                    )
                ).strip()

                if not names_match(
                    name,
                    fetched_name,
                ):
                    raise ValueError(
                        "name mismatch: "
                        f"{fetched_name}"
                    )

                counters[
                    "transfermarkt_success"
                ] += 1

                detail[
                    "transfermarkt_match"
                ] = "FOUND"

                changed = False

                # ==========================
                # CLUBS
                # ==========================

                (
                    merged_clubs,
                    added,
                ) = merge_clubs(
                    old_clubs,
                    fetched.get(
                        "clubs",
                        [],
                    ),
                )

                if added:
                    player[
                        "clubs"
                    ] = merged_clubs

                    detail[
                        "added_clubs"
                    ] = added

                    counters[
                        "clubs_expanded"
                    ] += 1

                    changed = True

                    write_log(
                        "TM_ONLY CLUBS "
                        f"+{len(added)} | "
                        f"{name}"
                    )

                # ==========================
                # BIRTH DATE
                # ==========================

                fetched_birth = str(
                    fetched.get(
                        "birthDate",
                        "",
                    )
                ).strip()

                if (
                    fetched_birth
                    and not player.get(
                        "birthDate"
                    )
                ):
                    player[
                        "birthDate"
                    ] = fetched_birth

                    changed = True

                    write_log(
                        "TM_ONLY BIRTHDATE OK | "
                        f"{name} | "
                        f"{fetched_birth}"
                    )

                if player.get(
                    "birthDate"
                ):
                    counters[
                        "birthdates_found"
                    ] += 1

                # ==========================
                # POSITIONS
                # ==========================

                fetched_positions = (
                    fetched.get(
                        "positions",
                        [],
                    )
                )

                if (
                    fetched_positions
                    and not player.get(
                        "positions"
                    )
                ):
                    player[
                        "positions"
                    ] = (
                        fetched_positions
                    )

                    changed = True

                    write_log(
                        "TM_ONLY POSITION OK | "
                        f"{name} | "
                        f"{', '.join(fetched_positions)}"
                    )

                positions_ok = (
                    isinstance(
                        player.get(
                            "positions"
                        ),
                        list,
                    )
                    and bool(
                        player.get(
                            "positions"
                        )
                    )
                )

                if positions_ok:
                    counters[
                        "positions_found"
                    ] += 1

                # ==========================
                # NATIONAL TEAM
                # ==========================

                (
                    nationality,
                    national_team_status,
                ) = (
                    determine_national_team_status(
                        fetched
                    )
                )

                if (
                    national_team_status
                    == NATIONAL_FOUND
                ):

                    counters[
                        "national_team_found"
                    ] += 1

                    existing_nationality = str(
                        player.get(
                            "nationality",
                            "",
                        )
                    ).strip()

                    if (
                        existing_nationality
                        and not is_valid_national_team_label(
                            existing_nationality
                        )
                    ):
                        write_log(
                            "TM_ONLY INVALID NATIONALITY CLEARED | "
                            f"{name} | "
                            f"{existing_nationality}"
                        )

                        player[
                            "nationality"
                        ] = ""

                        existing_nationality = ""
                        changed = True

                    if (
                        nationality
                        and normalize(
                            existing_nationality
                        ) != normalize(
                            nationality
                        )
                    ):
                        player[
                            "nationality"
                        ] = nationality

                        changed = True

                        write_log(
                            "TM_ONLY NATIONAL TEAM OK | "
                            f"{name} | "
                            f"{existing_nationality or '(empty)'}"
                            f" -> {nationality}"
                        )

                else:
                    counters[
                        "no_senior_national_team"
                    ] += 1

                    write_log(
                        "TM_ONLY NO SENIOR "
                        "NATIONAL TEAM | "
                        f"{name}"
                    )

                # ==========================
                # COMPLETE CHECK
                # ==========================

                clubs_ok = bool(
                    player.get(
                        "clubs"
                    )
                )

                birth_ok = bool(
                    player.get(
                        "birthDate"
                    )
                )

                nationality_ok = (
                    national_team_status
                    != NATIONAL_FOUND
                    or bool(
                        player.get(
                            "nationality"
                        )
                    )
                )

                national_team_complete = (
                    national_team_status
                    in {
                        NATIONAL_FOUND,
                        NO_SENIOR_NATIONAL_TEAM,
                    }
                )

                complete = bool(
                    clubs_ok
                    and birth_ok
                    and positions_ok
                    and nationality_ok
                    and national_team_complete
                )

                if complete:
                    if (
                        player.get(
                            "needs_enrichment"
                        )
                        is not False
                    ):
                        player[
                            "needs_enrichment"
                        ] = False

                        changed = True

                    counters[
                        "completed"
                    ] += 1

                    write_log(
                        "TM_ONLY ENRICH COMPLETE | "
                        f"{name}"
                    )

                else:
                    counters[
                        "failed"
                    ] += 1

                    missing = []

                    if not clubs_ok:
                        missing.append(
                            "clubs"
                        )

                    if not birth_ok:
                        missing.append(
                            "birthDate"
                        )

                        write_log(
                            "BIRTHDATE_MISSING | "
                            f"{name} | "
                            f"{transfermarkt_id}"
                        )

                    if not positions_ok:
                        missing.append(
                            "positions"
                        )

                        write_log(
                            "POSITION_MISSING | "
                            f"{name} | "
                            f"{transfermarkt_id}"
                        )

                    if not nationality_ok:
                        missing.append(
                            "nationality"
                        )

                    write_log(
                        "TM_ONLY ENRICH "
                        "INCOMPLETE | "
                        f"{name} | "
                        f"{', '.join(missing)}"
                    )

                # ==========================
                # ATOMIC SAVE
                # ==========================

                if changed:
                    if backup is None:
                        backup = (
                            create_backup()
                        )

                        print(
                            f"Backup: {backup}"
                        )

                    atomic_save(
                        players
                    )

                detail.update(
                    {
                        "senior_clubs":
                            fetched.get(
                                "clubs",
                                [],
                            ),

                        "birthDate":
                            player.get(
                                "birthDate",
                                "",
                            ),

                        "positions":
                            player.get(
                                "positions",
                                [],
                            ),

                        "transfermarkt_national_team":
                            fetched.get(
                                "tm_national_team",
                                "",
                            ),

                        "transfermarkt_national_caps":
                            fetched.get(
                                "tm_national_caps",
                                0,
                            ),

                        "national_team_status":
                            national_team_status,

                        "nationality":
                            player.get(
                                "nationality",
                                "",
                            ),

                        "flag":
                            player.get(
                                "needs_enrichment"
                            )
                            is True,
                    }
                )

            except Exception as error:
                counters[
                    "errors"
                ] += 1

                counters[
                    "failed"
                ] += 1

                detail[
                    "error"
                ] = str(
                    error
                )

                write_log(
                    "TRANSFERMARKT_FAILED | "
                    f"{name} | "
                    f"{transfermarkt_id} | "
                    f"{error}"
                )

                write_log(
                    "TM_ONLY ENRICH ERROR | "
                    f"{name} | "
                    f"{error}"
                )

            duration = (
                time.perf_counter()
                - player_started
            )

            detail[
                "processing_seconds"
            ] = round(
                duration,
                3,
            )

            details.append(
                detail
            )

            recent_durations.append(
                duration
            )

            print_progress(
                player_index,
                len(selected),
                name,
                counters[
                    "completed"
                ],
                counters[
                    "failed"
                ],
                run_started,
                recent_durations,
            )

            time.sleep(
                REQUEST_DELAY
            )

    except KeyboardInterrupt:
        print()

        print(
            "Ctrl+C algılandı. "
            "Tamamlanan checkpointler "
            "kaydedildi."
        )

        write_log(
            "TM_ONLY BULK INTERRUPTED BY USER"
        )

    elapsed = (
        time.perf_counter()
        - run_started
    )

    report = {
        **counters,

        "selected":
            len(selected),

        "average_seconds_per_player":
            round(
                elapsed
                / max(
                    1,
                    counters[
                        "processed"
                    ],
                ),
                3,
            ),

        "backup":
            str(
                backup
            )
            if backup
            else None,

        "details":
            details,
    }

    print()

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()