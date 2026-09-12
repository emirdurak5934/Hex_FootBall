import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import unicodedata

import requests
from bs4 import BeautifulSoup

PLAYERS_FILE = Path("data/players.json")
LOG_FILE = Path("data/logs.txt")
CHECK_FIELD = "team_trophies_checked_v2"

DEFAULT_LIMIT = 10
WAIT_SECONDS = 2
TIMEOUT = 25
MAX_RETRIES = 2
RETRY_BACKOFF = 7

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def load_players():
    with PLAYERS_FILE.open("r", encoding="utf-8") as f:
        players = json.load(f)
    if not isinstance(players, list):
        raise ValueError("players.json root must be a list")
    return players


def atomic_save(players):
    PLAYERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=f"{PLAYERS_FILE.name}.",
        suffix=".tmp",
        dir=PLAYERS_FILE.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(players, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        with open(tmp, "r", encoding="utf-8") as f:
            check = json.load(f)

        if not isinstance(check, list) or len(check) != len(players):
            raise ValueError("temporary JSON validation failed")

        os.replace(tmp, PLAYERS_FILE)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def create_backup():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = PLAYERS_FILE.with_name(
        f"players_before_team_trophies_{stamp}.json"
    )
    shutil.copy2(PLAYERS_FILE, backup)
    return backup


def write_log(message):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(
            f"{datetime.now().isoformat(timespec='seconds')} | "
            f"{message}\n"
        )


def safe_get(session, url):
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(
                url,
                timeout=TIMEOUT,
                allow_redirects=True,
            )

            if response.status_code == 429 and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF
                try:
                    wait = int(response.headers.get("Retry-After", wait))
                except ValueError:
                    pass
                print(f"Transfermarkt 429. {wait} saniye bekleniyor...")
                time.sleep(wait)
                continue

            if response.status_code in {500, 502, 503, 504} and attempt < MAX_RETRIES:
                print(
                    f"Transfermarkt HTTP {response.status_code}. "
                    f"{RETRY_BACKOFF} saniye sonra tekrar..."
                )
                time.sleep(RETRY_BACKOFF)
                continue

            response.raise_for_status()
            return response

        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
            if attempt < MAX_RETRIES:
                print(
                    "Transfermarkt bağlantı hatası. "
                    f"{RETRY_BACKOFF} saniye sonra tekrar..."
                )
                time.sleep(RETRY_BACKOFF)
                continue

        except requests.RequestException as error:
            last_error = error
            break

    raise RuntimeError(f"Transfermarkt request failed: {last_error}")


def strip_count(title):
    return re.sub(
        r"^\s*\d+\s*x\s+",
        "",
        str(title or "").strip(),
        flags=re.I,
    ).strip()


def is_team_trophy(title):
    key = normalize(strip_count(title))

    if not key:
        return False

    blocked = (
        "participant",
        "runner up",
        "second place",
        "third place",
        "finalist",
        "semi finalist",
        "footballer of the year",
        "player of the year",
        "player of the season",
        "goalkeeper",
        "golden boot",
        "golden shoe",
        "golden glove",
        "top goal scorer",
        "top goalscorer",
        "best assist",
        "best foreign player",
        "best young player",
        "ballon d or",
        "best fifa",
        "uefa best player",
        "fritz walter",
        "medalist",
        "medallist",
        " u17",
        " u18",
        " u19",
        " u20",
        " u21",
        " u23",
        "under 17",
        "under 18",
        "under 19",
        "under 20",
        "under 21",
        "under 23",
        "youth",
        "junior",
        "reserve",
    )

    if any(item in f" {key}" for item in blocked):
        return False

    positive = (
        "champion",
        "champions",
        "cup winner",
        "super cup winner",
        "supercup winner",
        "league winner",
        "europa league winner",
        "uefa cup winner",
        "world cup winner",
        "club world cup winner",
        "nations league winner",
        "copa america winner",
        "africa cup winner",
        "asian cup winner",
        "european champion",
        "conference league winner",
        "libertadores winner",
        "sudamericana winner",
        "recopa winner",
        "intercontinental cup winner",
    )

    return any(item in key for item in positive)


def get_team_trophies(session, transfermarkt_id):
    urls = (
        f"https://www.transfermarkt.com/jumplist/erfolge/spieler/{transfermarkt_id}",
        f"https://www.transfermarkt.com/spieler/erfolge/spieler/{transfermarkt_id}",
    )

    last_error = None

    for url in urls:
        try:
            response = safe_get(session, url)
            soup = BeautifulSoup(response.text, "html.parser")

            candidates = []

            for selector in (
                ".content-box-headline",
                "h2",
                "h3",
            ):
                for node in soup.select(selector):
                    text = " ".join(
                        node.get_text(" ", strip=True).split()
                    )
                    if text and len(text) <= 140:
                        candidates.append(text)

            trophies = []

            for candidate in candidates:
                trophy = strip_count(candidate)
                if (
                    is_team_trophy(trophy)
                    and trophy not in trophies
                ):
                    trophies.append(trophy)

            page_text = soup.get_text(" ", strip=True).lower()
            title = (
                soup.title.get_text(" ", strip=True).lower()
                if soup.title
                else ""
            )

            if (
                "transfermarkt" in title
                or "titles and season" in page_text
                or "erfolge" in response.url.lower()
            ):
                return trophies

            last_error = ValueError(
                "achievements page not recognized"
            )

        except Exception as error:
            last_error = error

    raise RuntimeError(
        f"Could not parse Transfermarkt achievements: {last_error}"
    )


def trophy_name(item):
    if isinstance(item, dict):
        return str(
            item.get("name")
            or item.get("title")
            or item.get("trophy")
            or ""
        ).strip()
    return str(item or "").strip()


def merge_trophies(existing, incoming):
    merged = list(existing) if isinstance(existing, list) else []
    known = {
        normalize(trophy_name(item))
        for item in merged
        if trophy_name(item)
    }
    added = []

    for trophy in incoming:
        key = normalize(trophy)
        if key and key not in known:
            merged.append(trophy)
            added.append(trophy)
            known.add(key)

    return merged, added


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--transfermarkt-ids")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be positive")

    players = load_players()

    manual_list = [
        x.strip()
        for x in (args.transfermarkt_ids or "").split(",")
        if x.strip()
    ]
    manual_ids = set(manual_list)

    if manual_ids:
        selected = [
            p for p in players
            if str(p.get("transfermarkt_id", "")).strip() in manual_ids
        ]
        selected.sort(
            key=lambda p: manual_list.index(
                str(p.get("transfermarkt_id", "")).strip()
            )
        )
    else:
        eligible = [
            p for p in players
            if p.get(CHECK_FIELD) is not True
        ]
        selected = eligible if args.all else eligible[:args.limit]

    print(
        ("BULK MODE" if args.all else "SAFE TEST MODE")
        + f" | selected players: {len(selected)}"
    )
    print("SOURCE: Transfermarkt | TEAM TROPHIES ONLY")

    session = requests.Session()
    session.headers.update(HEADERS)

    backup = None
    counters = {
        "processed": 0,
        "updated": 0,
        "no_trophies": 0,
        "no_transfermarkt_id": 0,
        "failed": 0,
    }

    try:
        for index, player in enumerate(selected, start=1):
            name = str(player.get("name", "")).strip()
            tm_id = str(player.get("transfermarkt_id", "")).strip()

            print(f"\n{index} / {len(selected)} - {name}")
            counters["processed"] += 1
            changed = False

            try:
                if not tm_id:
                    counters["no_transfermarkt_id"] += 1
                    player[CHECK_FIELD] = True
                    changed = True
                    print("Transfermarkt ID yok.")
                    write_log(f"TEAM_TROPHIES NO TM ID | {name}")

                else:
                    trophies = get_team_trophies(session, tm_id)

                    merged, added = merge_trophies(
                        player.get("trophies", []),
                        trophies,
                    )

                    if added:
                        player["trophies"] = merged
                        counters["updated"] += 1
                        changed = True
                        print(f"{len(added)} yeni takım kupası:")
                        for trophy in added:
                            print(" -", trophy)
                    else:
                        counters["no_trophies"] += 1
                        print(
                            "Yeni takım kupası yok."
                            if trophies
                            else "Takım kupası bulunamadı."
                        )

                    player[CHECK_FIELD] = True
                    changed = True

                    write_log(
                        f"TEAM_TROPHIES CHECKED | {name} | "
                        f"TM:{tm_id} | found:{len(trophies)} | "
                        f"added:{len(added)}"
                    )

            except Exception as error:
                counters["failed"] += 1
                print("Hata:", error)
                write_log(
                    f"TEAM_TROPHIES ERROR | {name} | "
                    f"TM:{tm_id} | {error}"
                )

            if changed:
                if backup is None:
                    backup = create_backup()
                    print("Backup:", backup)
                atomic_save(players)

            time.sleep(WAIT_SECONDS)

    except KeyboardInterrupt:
        print(
            "\nCtrl+C algılandı. Kaydedilmiş "
            "checkpointler korunuyor."
        )
        write_log("TEAM_TROPHIES INTERRUPTED BY USER")

    print(
        "\n" + json.dumps(
            {
                **counters,
                "selected": len(selected),
                "backup": str(backup) if backup else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()