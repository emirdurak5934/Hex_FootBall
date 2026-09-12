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


def normalize(text):

    text = str(text).strip().lower()

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    return "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )


with open(
    PLAYERS_FILE,
    "r",
    encoding="utf-8"
) as file:

    players = json.load(file)


print("TOPLAM OYUNCU:", len(players))


print("\n==============================")
print("LUKA MODRIC ARAMA")
print("==============================")


modric_found = False


for player in players:

    name = player.get(
        "name",
        ""
    )

    if "modric" in normalize(name):

        modric_found = True

        print("\nBULUNDU:")
        print("ID:", player.get("id"))
        print("İsim:", name)
        print("Kulüpler:", player.get("clubs"))
        print("Milliyet:", player.get("nationality"))


if not modric_found:

    print(
        "\nLuka Modric players.json içinde bulunamadı."
    )


print("\n==============================")
print("INTER KULÜP İSİMLERİ")
print("==============================")


club_names = set()


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

            club_name = club.get(
                "name",
                ""
            )

        else:

            club_name = str(club)


        normalized = normalize(
                club_name
            )


        if (
            "inter" in normalized
            or
            "internazionale" in normalized
        ):

            club_names.add(
                club_name
            )


if club_names:

    print(
        "\nDatabase içindeki Inter isimleri:"
    )

    for club_name in sorted(
        club_names
    ):

        print("-", club_name)

else:

    print(
        "\nInter ile ilişkili hiçbir kulüp adı bulunamadı."
    )


print("\n==============================")
print("INTER OYUNCULARINDAN ÖRNEKLER")
print("==============================")


count = 0


for player in players:

    clubs = player.get(
        "clubs",
        []
    )

    player_clubs = []


    for club in clubs:

        if isinstance(
            club,
            dict
        ):

            club_name = club.get(
                "name",
                ""
            )

        else:

            club_name = str(club)


        player_clubs.append(
            club_name
        )


    if any(
        (
            "inter" in normalize(club)
            or
            "internazionale" in normalize(club)
        )
        for club in player_clubs
    ):

        print(
            player.get(
                "name"
            ),
            "->",
            player_clubs
        )

        count += 1


        if count >= 20:

            break


print(
    "\nBulunan örnek Inter oyuncusu:",
    count
)