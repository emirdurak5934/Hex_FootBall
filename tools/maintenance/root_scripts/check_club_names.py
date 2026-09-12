import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json
import unicodedata


PLAYERS_FILE = "data/players.json"


# ==================================================
# NORMALIZE
# ==================================================

def normalize(text):

    text = str(
        text
    ).strip().lower()

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    return text


# ==================================================
# DATABASE
# ==================================================

with open(
    PLAYERS_FILE,
    "r",
    encoding="utf-8"
) as file:

    players = json.load(file)


# ==================================================
# ARANACAK KELİMELER
# ==================================================

keywords = [

    "bayern",
    "munchen",
    "munich",

    "benfica",
    "lisboa",

    "besiktas",
    "beşiktaş"

]


# ==================================================
# BULUNAN KULÜP İSİMLERİ
# ==================================================

found_names = set()


for player in players:

    clubs = player.get(
        "clubs",
        []
    )

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


        if not name:

            continue


        normalized_name = normalize(
            name
        )


        for keyword in keywords:

            normalized_keyword = normalize(
                keyword
            )


            if normalized_keyword in normalized_name:

                found_names.add(
                    name
                )

                break


# ==================================================
# SONUÇ
# ==================================================

print()

print(
    "=" * 60
)

print(
    "DATABASE'DE BULUNAN İLGİLİ KULÜP İSİMLERİ"
)

print(
    "=" * 60
)


for name in sorted(
    found_names,
    key=str.lower
):

    print(
        "-",
        name
    )


print()

print(
    "Toplam bulunan farklı isim:",
    len(found_names)
)

print()