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


trophy_names = set()

players_with_trophies = 0
players_without_trophies = 0


for player in players:

    trophies = player.get(
        "trophies",
        []
    )

    if not trophies:

        players_without_trophies += 1
        continue

    players_with_trophies += 1

    for trophy in trophies:

        if isinstance(
            trophy,
            dict
        ):

            name = (
                trophy.get("name")
                or trophy.get("title")
                or trophy.get("trophy")
                or ""
            )

        else:

            name = str(
                trophy
            )

        name = name.strip()

        if name:

            trophy_names.add(
                name
            )


print(
    "TOPLAM OYUNCU:",
    len(players)
)

print(
    "KUPA BİLGİSİ OLAN:",
    players_with_trophies
)

print(
    "KUPA BİLGİSİ OLMAYAN:",
    players_without_trophies
)

print(
    "\nBENZERSİZ KUPA İSMİ:",
    len(trophy_names)
)


print(
    "\n"
    + "=" * 60
)

print(
    "TÜM TROPHY İSİMLERİ"
)

print(
    "=" * 60
)


for trophy_name in sorted(
    trophy_names,
    key=str.lower
):

    print(
        "-",
        trophy_name
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

    "champion",
    "champions",
    "championship",

    "premier",
    "laliga",
    "la liga",
    "serie",
    "bundesliga",
    "ligue",
    "super lig",
    "süper lig",

    "uefa",
    "europa",

    "world cup",

    "european",

    "ballon"

]


for trophy_name in sorted(
    trophy_names,
    key=str.lower
):

    lowered = (
        trophy_name
        .lower()
    )

    if any(
        keyword in lowered
        for keyword in keywords
    ):

        print(
            "-",
            trophy_name
        )