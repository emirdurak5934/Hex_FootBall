import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json


PLAYERS_FILE = "data/players.json"


with open(
    PLAYERS_FILE,
    "r",
    encoding="utf-8"
) as file:

    players = json.load(file)


league_names = set()

players_with_leagues = 0
players_without_leagues = 0


for player in players:

    leagues = player.get(
        "leagues",
        []
    )

    if not leagues:

        players_without_leagues += 1
        continue

    players_with_leagues += 1


    for league in leagues:

        if isinstance(
            league,
            dict
        ):

            name = (
                league.get("name")
                or league.get("league")
                or league.get("title")
                or ""
            )

        else:

            name = str(
                league
            )


        name = name.strip()


        if name:

            league_names.add(
                name
            )


print(
    "TOPLAM OYUNCU:",
    len(players)
)

print(
    "LİG BİLGİSİ OLAN:",
    players_with_leagues
)

print(
    "LİG BİLGİSİ OLMAYAN:",
    players_without_leagues
)

print(
    "BENZERSİZ LİG SAYISI:",
    len(league_names)
)


print(
    "\n"
    + "=" * 60
)

print(
    "TÜM LİG İSİMLERİ"
)

print(
    "=" * 60
)


for league_name in sorted(
    league_names,
    key=str.lower
):

    print(
        "-",
        league_name
    )


print(
    "\n"
    + "=" * 60
)

print(
    "BİZİM OYUN İÇİN İLGİLİ OLABİLECEKLER"
)

print(
    "=" * 60
)


keywords = [

    "premier",
    "england",

    "laliga",
    "la liga",
    "spain",

    "serie a",
    "italy",

    "bundesliga",
    "germany",

    "ligue 1",
    "france",

    "super lig",
    "süper lig",
    "turkey",

    "primeira",
    "portugal",

    "eredivisie",
    "netherlands",
    "dutch"

]


for league_name in sorted(
    league_names,
    key=str.lower
):

    lowered = (
        league_name
        .lower()
    )


    if any(
        keyword in lowered
        for keyword in keywords
    ):

        print(
            "-",
            league_name
        )