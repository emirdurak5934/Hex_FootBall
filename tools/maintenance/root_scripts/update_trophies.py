import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json
import time
import requests
from bs4 import BeautifulSoup


PLAYERS_FILE = "data/players.json"
LOG_FILE = "data/logs.txt"

WAIT_SECONDS = 2


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}


def load_players():

    with open(
        PLAYERS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def save_players(players):

    with open(
        PLAYERS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            players,
            file,
            ensure_ascii=False,
            indent=4
        )


def write_log(message):

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            message + "\n"
        )


def get_transfermarkt_id(player_id):

    url = (
        f"https://www.wikidata.org/wiki/"
        f"Special:EntityData/{player_id}.json"
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    entity = data["entities"][player_id]

    claims = entity.get(
        "claims",
        {}
    )

    transfermarkt_claims = claims.get(
        "P2446",
        []
    )

    if not transfermarkt_claims:
        return None

    try:

        transfermarkt_id = (
            transfermarkt_claims[0]
            ["mainsnak"]
            ["datavalue"]
            ["value"]
        )

        return str(
            transfermarkt_id
        )

    except Exception:

        return None


def get_trophies(transfermarkt_id):

    url = (
        "https://www.transfermarkt.com/"
        "spieler/erfolge/spieler/"
        f"{transfermarkt_id}"
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    trophies = []

    boxes = soup.select(
        ".box"
    )

    for box in boxes:

        header = box.select_one(
            ".content-box-headline"
        )

        if not header:
            continue

        title = header.get_text(
            " ",
            strip=True
        )

        if not title:
            continue

        title_lower = title.lower()

        ignored_titles = [
            "player data",
            "transfer history",
            "market value",
            "stats",
            "career",
            "social media",
            "rumours",
            "news"
        ]

        if any(
            ignored in title_lower
            for ignored in ignored_titles
        ):
            continue

        if (
            "winner" in title_lower
            or "champion" in title_lower
            or "cup" in title_lower
            or "title" in title_lower
            or "victories" in title_lower
            or "champions league" in title_lower
            or "league" in title_lower
        ):

            trophies.append(
                title
            )

    trophies = list(
        dict.fromkeys(
            trophies
        )
    )

    return trophies


players = load_players()

print(
    f"Kontrol edilecek oyuncu: "
    f"{len(players)}"
)


updated = 0
no_transfermarkt = 0
no_trophies = 0
failed = 0
skipped = 0


for index, player in enumerate(
    players,
    start=1
):

    player_id = player["id"]
    player_name = player["name"]

    print(
        "\n------------------------------"
    )

    print(
        f"{index}/{len(players)} "
        f"- {player_name}"
    )


    # Daha önce gerçekten kontrol edilmişse atla
    if player.get("trophies_checked") is True:

        print(
            "Daha önce kontrol edilmiş. "
            "Atlandı."
        )

        skipped += 1

        continue


    # Kupası zaten doluysa tekrar Transfermarkt'a gitme
    existing_trophies = player.get(
        "trophies",
        []
    )

    if existing_trophies:

        player["trophies_checked"] = True

        save_players(
            players
        )

        print(
            "Kupalar zaten mevcut. "
            "Kontrol edilmiş olarak işaretlendi."
        )

        skipped += 1

        continue


    try:

        transfermarkt_id = (
            get_transfermarkt_id(
                player_id
            )
        )


        if not transfermarkt_id:

            print(
                "Transfermarkt ID bulunamadı."
            )

            player["trophies"] = []
            player["trophies_checked"] = True

            save_players(
                players
            )

            no_transfermarkt += 1

            write_log(
                f"TRANSFERMARKT ID YOK | "
                f"{player_name} | "
                f"{player_id}"
            )

            time.sleep(
                WAIT_SECONDS
            )

            continue


        print(
            "Transfermarkt ID:",
            transfermarkt_id
        )


        trophies = get_trophies(
            transfermarkt_id
        )


        if not trophies:

            print(
                "Kupa bulunamadı."
            )

            player["trophies"] = []
            player["trophies_checked"] = True

            save_players(
                players
            )

            no_trophies += 1

            write_log(
                f"TROPHIES YOK | "
                f"{player_name} | "
                f"{player_id} | "
                f"TM:{transfermarkt_id}"
            )

            time.sleep(
                WAIT_SECONDS
            )

            continue


        player["trophies"] = trophies
        player["trophies_checked"] = True

        save_players(
            players
        )

        updated += 1


        print(
            "Kupalar:"
        )

        for trophy in trophies:

            print(
                "-",
                trophy
            )


        print(
            "KAYDEDİLDİ"
        )


        write_log(
            f"TROPHIES UPDATE | "
            f"{player_name} | "
            f"{len(trophies)} kupa"
        )


    except Exception as error:

        failed += 1

        print(
            "Hata:",
            error
        )

        write_log(
            f"TROPHIES ERROR | "
            f"{player_name} | "
            f"{player_id} | "
            f"{error}"
        )


    time.sleep(
        WAIT_SECONDS
    )


print(
    "\n=============================="
)

print(
    "TAMAMLANDI"
)

print(
    "Güncellenen:",
    updated
)

print(
    "Transfermarkt ID olmayan:",
    no_transfermarkt
)

print(
    "Kupa bulunamayan:",
    no_trophies
)

print(
    "Atlanan:",
    skipped
)

print(
    "Hata:",
    failed
)