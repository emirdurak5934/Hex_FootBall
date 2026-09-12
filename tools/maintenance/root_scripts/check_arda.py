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


print()
print("=" * 60)
print("ARDA ARAMASI")
print("=" * 60)


found = 0


for player in players:

    name = str(
        player.get(
            "name",
            ""
        )
    ).strip()

    normalized_name = normalize(
        name
    )

    if (
        "arda" in normalized_name
        or
        "guler" in normalized_name
        or
        "güler" in name.lower()
    ):

        found += 1

        print()
        print("ID:", player.get("id"))
        print("NAME:", repr(name))
        print("NORMALIZE:", repr(normalized_name))
        print("NATIONALITY:", player.get("nationality"))
        print("CLUBS:", player.get("clubs"))


print()
print("TOPLAM BULUNAN:", found)
print()