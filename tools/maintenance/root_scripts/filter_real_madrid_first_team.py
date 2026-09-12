import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json
import re
import time
import shutil
import unicodedata

from datetime import datetime

import requests
from bs4 import BeautifulSoup


# ==================================================
# AYARLAR
# ==================================================

PLAYERS_FILE = "data/players.json"

START_SEASON = 2005
END_SEASON = 2026

WAIT_SECONDS = 2
TIMEOUT = 20
MAX_RETRIES = 5


# ==================================================
# 24 ANA TAKIM
#
# Arsenal
# Liverpool
# Manchester United
#
# ÇIKARILDI.
# ==================================================

CLUBS = [

    # ==================================================
    # İNGİLTERE
    # ==================================================

    {
        "name": "Manchester City",
        "slug": "manchester-city",
        "tm_id": "281",
        "database_club": "Manchester City F.C."
    },

    {
        "name": "Tottenham Hotspur",
        "slug": "tottenham-hotspur",
        "tm_id": "148",
        "database_club": "Tottenham Hotspur F.C."
    },

    {
        "name": "Newcastle United",
        "slug": "newcastle-united",
        "tm_id": "762",
        "database_club": "Newcastle United F.C."
    },

    {
        "name": "Chelsea",
        "slug": "fc-chelsea",
        "tm_id": "631",
        "database_club": "Chelsea F.C."
    },


    # ==================================================
    # İSPANYA
    # ==================================================

    {
        "name": "Sevilla",
        "slug": "fc-sevilla",
        "tm_id": "368",
        "database_club": "Sevilla FC"
    },

    {
        "name": "Atletico Madrid",
        "slug": "atletico-madrid",
        "tm_id": "13",
        "database_club": "Atlético Madrid"
    },

    {
        "name": "Barcelona",
        "slug": "fc-barcelona",
        "tm_id": "131",
        "database_club": "FC Barcelona"
    },

    {
        "name": "Real Madrid",
        "slug": "real-madrid",
        "tm_id": "418",
        "database_club": "Real Madrid Club de Fútbol"
    },


    # ==================================================
    # İTALYA
    # ==================================================

    {
        "name": "AC Milan",
        "slug": "ac-mailand",
        "tm_id": "5",
        "database_club": "AC Milan"
    },

    {
        "name": "Inter Milan",
        "slug": "inter-mailand",
        "tm_id": "46",
        "database_club": "Inter Milan"
    },

    {
        "name": "AS Roma",
        "slug": "as-rom",
        "tm_id": "12",
        "database_club": "AS Roma"
    },

    {
        "name": "Napoli",
        "slug": "ssc-neapel",
        "tm_id": "6195",
        "database_club": "SSC Napoli"
    },

    {
        "name": "Juventus",
        "slug": "juventus-turin",
        "tm_id": "506",
        "database_club": "Juventus FC"
    },


    # ==================================================
    # FRANSA
    # ==================================================

    {
        "name": "Paris Saint-Germain",
        "slug": "paris-saint-germain",
        "tm_id": "583",
        "database_club": "Paris Saint-Germain FC"
    },

    {
        "name": "AS Monaco",
        "slug": "as-monaco",
        "tm_id": "162",
        "database_club": "AS Monaco"
    },


    # ==================================================
    # ALMANYA
    # ==================================================

    {
        "name": "Bayern Munich",
        "slug": "fc-bayern-munchen",
        "tm_id": "27",
        "database_club": "FC Bayern Munich"
    },

    {
        "name": "Borussia Dortmund",
        "slug": "borussia-dortmund",
        "tm_id": "16",
        "database_club": "Borussia Dortmund"
    },


    # ==================================================
    # PORTEKİZ
    # ==================================================

    {
        "name": "Benfica",
        "slug": "benfica-lissabon",
        "tm_id": "294",
        "database_club": "S.L. Benfica"
    },

    {
        "name": "Sporting CP",
        "slug": "sporting-lissabon",
        "tm_id": "336",
        "database_club": "Sporting CP"
    },


    # ==================================================
    # HOLLANDA
    # ==================================================

    {
        "name": "Ajax",
        "slug": "ajax-amsterdam",
        "tm_id": "610",
        "database_club": "AFC Ajax"
    },


    # ==================================================
    # TÜRKİYE
    # ==================================================

    {
        "name": "Galatasaray",
        "slug": "galatasaray-istanbul",
        "tm_id": "141",
        "database_club": "Galatasaray S.K."
    },

    {
        "name": "Fenerbahce",
        "slug": "fenerbahce-istanbul",
        "tm_id": "36",
        "database_club": "Fenerbahçe Istanbul"
    },

    {
        "name": "Besiktas",
        "slug": "besiktas-istanbul",
        "tm_id": "114",
        "database_club": "Beşiktaş J.K. (Football)"
    },

    {
        "name": "Trabzonspor",
        "slug": "trabzonspor",
        "tm_id": "449",
        "database_club": "Trabzonspor"
    }

]


# ==================================================
# HEADER
# ==================================================

HEADERS = {

    "User-Agent":
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36",

    "Accept-Language":
        "en-US,en;q=0.9"

}


# ==================================================
# NORMALIZE
# ==================================================

CONFUSABLE_CHARACTERS = {

    # YUNANCA

    "Α": "A",
    "α": "a",

    "Β": "B",
    "β": "b",

    "Ε": "E",
    "ε": "e",

    "Ι": "I",
    "ι": "i",

    "Κ": "K",
    "κ": "k",

    "Μ": "M",
    "μ": "m",

    "Ν": "N",

    "Ο": "O",
    "ο": "o",

    "Ρ": "P",
    "ρ": "p",

    "Τ": "T",
    "τ": "t",

    "Χ": "X",
    "χ": "x",


    # KİRİL

    "А": "A",
    "а": "a",

    "В": "B",

    "Е": "E",
    "е": "e",

    "К": "K",
    "к": "k",

    "М": "M",
    "м": "m",

    "Н": "H",

    "О": "O",
    "о": "o",

    "Р": "P",
    "р": "p",

    "С": "C",
    "с": "c",

    "Т": "T",
    "т": "t",

    "Х": "X",
    "х": "x"

}


def normalize(text):

    text = str(
        text
    ).strip()

    text = "".join(
        CONFUSABLE_CHARACTERS.get(
            char,
            char
        )
        for char in text
    )

    text = text.lower()

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(
            char
        )
    )

    text = " ".join(
        text.split()
    )

    return text


# ==================================================
# TRANSFERMARKT PLAYER ID
# ==================================================

def extract_tm_player_id(url):

    if not url:

        return None

    match = re.search(
        r"/spieler/(\d+)",
        url
    )

    if not match:

        return None

    return match.group(1)


# ==================================================
# DATABASE LOAD
# ==================================================

def load_players():

    with open(
        PLAYERS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ==================================================
# DATABASE SAVE
#
# .tmp YOK
# os.replace YOK
# ==================================================

def save_players(players):

    for attempt in range(
        1,
        11
    ):

        try:

            with open(
                PLAYERS_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    players,
                    file,
                    ensure_ascii=False,
                    indent=2
                )

            return True

        except PermissionError:

            print(
                "players.json kullanımda."
            )

            print(
                f"Kaydetme denemesi "
                f"{attempt}/10"
            )

            time.sleep(1)

        except Exception as error:

            print(
                "KAYDETME HATASI:",
                error
            )

            return False

    print(
        "players.json "
        "10 denemeden sonra "
        "kaydedilemedi."
    )

    return False


# ==================================================
# BACKUP
# ==================================================

def create_backup():

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_file = (
        "data/players_backup_squads_"
        +
        timestamp
        +
        ".json"
    )

    shutil.copy2(
        PLAYERS_FILE,
        backup_file
    )

    print()

    print(
        "BACKUP OLUŞTURULDU:"
    )

    print(
        backup_file
    )

    return backup_file


# ==================================================
# REQUEST SESSION
# ==================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# ==================================================
# SAFE GET
# ==================================================

def safe_get(url):

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = session.get(
                url,
                timeout=TIMEOUT
            )

            print(
                "HTTP:",
                response.status_code
            )


            if response.status_code == 429:

                wait_time = min(
                    20 * attempt,
                    120
                )

                print(
                    "429 RATE LIMIT."
                )

                print(
                    wait_time,
                    "saniye bekleniyor..."
                )

                time.sleep(
                    wait_time
                )

                continue


            if response.status_code in [
                500,
                502,
                503,
                504
            ]:

                wait_time = min(
                    10 * attempt,
                    60
                )

                print(
                    "SERVER HATASI:",
                    response.status_code
                )

                print(
                    wait_time,
                    "saniye bekleniyor..."
                )

                time.sleep(
                    wait_time
                )

                continue


            response.raise_for_status()

            return response


        except requests.RequestException as error:

            print(
                "REQUEST HATASI:",
                error
            )

            if attempt == MAX_RETRIES:

                return None

            wait_time = min(
                10 * attempt,
                60
            )

            print(
                wait_time,
                "saniye sonra tekrar..."
            )

            time.sleep(
                wait_time
            )

    return None


# ==================================================
# ANA TAKIM SEZON KADRO URL
# ==================================================

def build_squad_url(
    club,
    season
):

    return (

        "https://www.transfermarkt.com/"
        f"{club['slug']}/kader/"
        f"verein/{club['tm_id']}/"
        f"saison_id/{season}/"
        "plus/1"

    )


# ==================================================
# OYUNCUNUN KULÜPLERİ
# ==================================================

def get_player_clubs(player):

    result = []

    clubs = player.get(
        "clubs",
        []
    )

    if not isinstance(
        clubs,
        list
    ):

        return result

    for club in clubs:

        if isinstance(
            club,
            dict
        ):

            name = club.get(
                "name",
                ""
            )

        else:

            name = str(
                club
            )

        if name:

            result.append(
                name
            )

    return result


# ==================================================
# OYUNCUDA KULÜP VAR MI
# ==================================================

def player_has_club(
    player,
    club_name
):

    target = normalize(
        club_name
    )

    for current_club in get_player_clubs(
        player
    ):

        if normalize(
            current_club
        ) == target:

            return True

    return False


# ==================================================
# KULÜP EKLE
# ==================================================

def add_club_to_player(
    player,
    club_name
):

    if player_has_club(
        player,
        club_name
    ):

        return False

    clubs = player.get(
        "clubs",
        []
    )

    if not isinstance(
        clubs,
        list
    ):

        clubs = []

    clubs.append(
        club_name
    )

    player[
        "clubs"
    ] = clubs

    return True


# ==================================================
# TEK SEZON ANA TAKIM KADROSU
# ==================================================

def scrape_season_squad(
    club,
    season
):

    url = build_squad_url(
        club,
        season
    )

    print()

    print(
        "-" * 70
    )

    print(
        club["name"],
        "|",
        f"{season}/{str(season + 1)[-2:]}"
    )

    print(
        "-" * 70
    )

    response = safe_get(
        url
    )

    if not response:

        print(
            "SAYFA ALINAMADI."
        )

        return None

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    table = soup.select_one(
        "table.items"
    )

    if not table:

        print(
            "KADRO TABLOSU BULUNAMADI."
        )

        return None

    found = {}

    rows = table.select(
        "tbody > tr"
    )

    for row in rows:

        player_links = row.select(
            'a[href*="/profil/spieler/"]'
        )

        if not player_links:

            continue

        player_link = None
        player_name = ""

        for link in player_links:

            candidate_name = link.get_text(
                " ",
                strip=True
            )

            if candidate_name:

                player_link = link
                player_name = candidate_name
                break

        if not player_link:

            continue

        profile_url = player_link.get(
            "href",
            ""
        )

        tm_player_id = extract_tm_player_id(
            profile_url
        )

        if (
            not player_name
            or
            not tm_player_id
        ):

            continue

        found[
            tm_player_id
        ] = {

            "tm_id":
                tm_player_id,

            "name":
                player_name,

            "season":
                season,

            "database_club":
                club[
                    "database_club"
                ]

        }

    print(
        "Ana takım kadrosunda bulunan:",
        len(found)
    )

    return found


# ==================================================
# BAŞLAT
# ==================================================

players = load_players()


print()

print(
    "=" * 80
)

print(
    "24 KULÜP - 2000+ ANA TAKIM KADRO TARAMASI"
)

print(
    "=" * 80
)

print(
    "Mevcut database:",
    len(players)
)

print(
    "Kulüp sayısı:",
    len(CLUBS)
)

print(
    "İlk sezon:",
    START_SEASON
)

print(
    "Son sezon:",
    END_SEASON
)


# ==================================================
# BACKUP
# ==================================================

create_backup()


# ==================================================
# DATABASE INDEXLERİ
# ==================================================

players_by_name = {}

players_by_tm_id = {}


for player in players:

    # ==================================================
    # İSİM INDEX
    # ==================================================

    name = str(
        player.get(
            "name",
            ""
        )
    ).strip()

    if name:

        key = normalize(
            name
        )

        if key not in players_by_name:

            players_by_name[
                key
            ] = player


    # ==================================================
    # TRANSFERMARKT ID INDEX
    # ==================================================

    transfermarkt_id = str(
        player.get(
            "transfermarkt_id",
            ""
        )
    ).strip()

    if transfermarkt_id:

        players_by_tm_id[
            transfermarkt_id
        ] = player


# ==================================================
# GLOBAL SAYAÇLAR
# ==================================================

total_new = 0
total_club_added = 0
total_existing = 0

failed_pages = []


# ==================================================
# TÜM KULÜPLER
# ==================================================

for club_index, club in enumerate(
    CLUBS,
    start=1
):

    print()

    print(
        "=" * 80
    )

    print(
        f"{club_index}/{len(CLUBS)} "
        f"{club['name']}"
    )

    print(
        "=" * 80
    )


    # ==================================================
    # BU KULÜBÜN 2000+ TÜM ANA TAKIM OYUNCULARI
    # ==================================================

    club_players = {}


    for season in range(
        START_SEASON,
        END_SEASON + 1
    ):

        season_players = scrape_season_squad(
            club,
            season
        )


        if season_players is None:

            failed_pages.append(
                {
                    "club":
                        club["name"],

                    "season":
                        season
                }
            )

            time.sleep(
                WAIT_SECONDS
            )

            continue


        for tm_id, info in season_players.items():

            if tm_id not in club_players:

                club_players[
                    tm_id
                ] = {

                    "tm_id":
                        tm_id,

                    "name":
                        info[
                            "name"
                        ],

                    "database_club":
                        club[
                            "database_club"
                        ],

                    "first_season":
                        season,

                    "last_season":
                        season

                }

            else:

                club_players[
                    tm_id
                ][
                    "last_season"
                ] = season


        time.sleep(
            WAIT_SECONDS
        )


    # ==================================================
    # KULÜP HAVUZU
    # ==================================================

    print()

    print(
        club["name"],
        "2000+ benzersiz ana takım oyuncusu:",
        len(club_players)
    )


    club_new = 0
    club_updated = 0
    club_existing = 0


    # ==================================================
    # DATABASE'E İŞLE
    # ==================================================

    for candidate in club_players.values():

        tm_id = candidate[
            "tm_id"
        ]

        name = candidate[
            "name"
        ]

        database_club = candidate[
            "database_club"
        ]

        key = normalize(
            name
        )


        # ==================================================
        # ÖNCE TRANSFERMARKT ID
        # ==================================================

        existing_player = players_by_tm_id.get(
            tm_id
        )


        # ==================================================
        # SONRA İSİM
        # ==================================================

        if not existing_player:

            existing_player = players_by_name.get(
                key
            )


        # ==================================================
        # OYUNCU ZATEN VAR
        # ==================================================

        if existing_player:

            changed = add_club_to_player(
                existing_player,
                database_club
            )


            if changed:

                club_updated += 1
                total_club_added += 1

                print(
                    "KULÜP EKLENDİ |",
                    name,
                    "|",
                    database_club
                )

            else:

                club_existing += 1
                total_existing += 1


            # ==================================================
            # TRANSFERMARKT ID YOKSA EKLE
            # ==================================================

            if not existing_player.get(
                "transfermarkt_id"
            ):

                existing_player[
                    "transfermarkt_id"
                ] = tm_id

                players_by_tm_id[
                    tm_id
                ] = existing_player


            save_players(
                players
            )

            continue


        # ==================================================
        # YENİ OYUNCU
        # ==================================================

        new_player = {

            "id":
                "tm_missing_"
                +
                tm_id,

            "name":
                name,

            "clubs": [
                database_club
            ],

            "nationality":
                "",

            "position":
                "",

            "trophies":
                [],

            "transfermarkt_id":
                tm_id,

            "needs_enrichment":
                True,

            "first_seen_season":
                candidate[
                    "first_season"
                ],

            "last_seen_season":
                candidate[
                    "last_season"
                ]

        }


        players.append(
            new_player
        )


        # ==================================================
        # INDEX GÜNCELLE
        # ==================================================

        players_by_name[
            key
        ] = new_player


        players_by_tm_id[
            tm_id
        ] = new_player


        club_new += 1
        total_new += 1


        print(
            "YENİ |",
            name,
            "|",
            club["name"],
            "|",
            candidate[
                "first_season"
            ],
            "-",
            candidate[
                "last_season"
            ]
        )


        save_players(
            players
        )


    # ==================================================
    # KULÜP ÖZETİ
    # ==================================================

    print()

    print(
        "-" * 80
    )

    print(
        club["name"],
        "TAMAMLANDI"
    )

    print(
        "Yeni oyuncu:",
        club_new
    )

    print(
        "Mevcut oyuncuya kulüp eklendi:",
        club_updated
    )

    print(
        "Zaten doğru:",
        club_existing
    )

    print(
        "-" * 80
    )


# ==================================================
# SON KEZ KAYDET
# ==================================================

save_players(
    players
)


# ==================================================
# FINAL SONUÇ
# ==================================================

print()

print(
    "=" * 80
)

print(
    "TÜM KULÜPLER TAMAMLANDI"
)

print(
    "=" * 80
)


print(
    "Yeni eklenen oyuncu:",
    total_new
)


print(
    "Mevcut oyuncuya eklenen kulüp:",
    total_club_added
)


print(
    "Zaten doğru eşleşme:",
    total_existing
)


print(
    "Yeni database toplamı:",
    len(players)
)


# ==================================================
# BAŞARISIZ SAYFALAR
# ==================================================

print()

print(
    "=" * 80
)

print(
    "BAŞARISIZ SEZON SAYFALARI"
)

print(
    "=" * 80
)


if not failed_pages:

    print(
        "Yok."
    )

else:

    for item in failed_pages:

        print(
            item[
                "club"
            ],
            "|",
            item[
                "season"
            ]
        )


    print()

    print(
        "Toplam başarısız sayfa:",
        len(failed_pages)
    )


# ==================================================
# ENRICH BEKLEYEN
# ==================================================

needs_enrichment_count = 0


for player in players:

    if player.get(
        "needs_enrichment"
    ) is True:

        needs_enrichment_count += 1


print()

print(
    "=" * 80
)

print(
    "ENRICH BEKLEYEN"
)

print(
    "=" * 80
)


print(
    "needs_enrichment=True:",
    needs_enrichment_count
)


print()

print(
    "İŞLEM TAMAMLANDI."
)

print()