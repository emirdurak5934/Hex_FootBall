import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json
import os
import shutil
from pathlib import Path
from datetime import datetime


PLAYERS_FILE = Path("data/players.json")

WRONG_IDS = {
    "Q110001765",
    "Q27899245"
}

NEW_PLAYER = {
    "id": "Q250973",
    "name": "Álvaro Fernández",
    "birthDate": "1985-10-11",
    "nationality": "Uruguay",
    "positions": [
        "Midfielder"
    ],
    "clubs": [
        "Uruguay Montevideo FC",
        "Atenas de San Carlos",
        "Montevideo Wanderers",
        "Puebla FC",
        "Club Nacional",
        "Vitória Setúbal FC",
        "Universidad de Chile",
        "Seattle Sounders FC",
        "Chicago Fire FC",
        "Al-Rayyan SC",
        "Gimnasia y Esgrima La Plata",
        "San Martín de San Juan",
        "Rampla Juniors",
        "Plaza Colonia"
    ],
    "trophies": [
        "Uruguayan champion",
        "US Open Cup winner"
    ],
    "trophies_checked": True,
    "team_trophies_checked_v2": True,
    "transfermarkt_id": "76213",
    "nationality_checked": True,
    "position_checked": True
}


def load_players():
    with PLAYERS_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def atomic_save(players):
    temp_file = PLAYERS_FILE.with_suffix(".tmp")

    with temp_file.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            players,
            f,
            ensure_ascii=False,
            indent=2
        )

        f.flush()
        os.fsync(f.fileno())

    # doğrula
    with temp_file.open(
        "r",
        encoding="utf-8"
    ) as f:
        json.load(f)

    os.replace(
        temp_file,
        PLAYERS_FILE
    )


print("players.json yükleniyor...")

players = load_players()

print(
    f"Mevcut oyuncu sayısı: {len(players)}"
)


# --------------------------------------------------
# BACKUP
# --------------------------------------------------

timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

backup = (
    PLAYERS_FILE.parent
    / f"players_before_fix_alvaro_{timestamp}.json"
)

shutil.copy2(
    PLAYERS_FILE,
    backup
)

print(
    f"Backup oluşturuldu: {backup}"
)


# --------------------------------------------------
# YANLIŞ TM ID'LERİ TEMİZLE
# --------------------------------------------------

cleaned = []

for player in players:

    player_id = str(
        player.get("id", "")
    )

    if player_id not in WRONG_IDS:
        continue

    if str(
        player.get("transfermarkt_id")
    ) == "76213":

        print()
        print(
            f"YANLIŞ TM ID TEMİZLENDİ:"
        )

        print(
            f"{player.get('name')} | "
            f"{player_id} | "
            f"76213 -> null"
        )

        player["transfermarkt_id"] = None

        cleaned.append(
            player_id
        )


# --------------------------------------------------
# GERÇEK ÁLVARO VAR MI?
# --------------------------------------------------

existing_ids = {
    str(player.get("id"))
    for player in players
    if player.get("id")
}


if "Q250973" in existing_ids:

    print()
    print(
        "Q250973 zaten mevcut. "
        "Yeni kayıt eklenmedi."
    )

else:

    players.append(
        NEW_PLAYER
    )

    print()
    print(
        "GERÇEK ÁLVARO FERNÁNDEZ EKLENDİ:"
    )

    print(
        "Q250973 | Álvaro Fernández | "
        "TM:76213"
    )


# --------------------------------------------------
# DUPLICATE TM ID KONTROL
# --------------------------------------------------

tm_76213_players = [
    player
    for player in players
    if str(
        player.get("transfermarkt_id")
    ) == "76213"
]


print()
print(
    f"76213 kullanan kayıt sayısı: "
    f"{len(tm_76213_players)}"
)

for player in tm_76213_players:

    print(
        f" - {player.get('id')} | "
        f"{player.get('name')}"
    )


if len(tm_76213_players) != 1:

    print()
    print(
        "HATA: 76213 hâlâ birden fazla "
        "kayıtta bulunuyor."
    )

    print(
        "players.json değiştirilmedi."
    )

    raise SystemExit(1)


if (
    tm_76213_players[0].get("id")
    != "Q250973"
):

    print()
    print(
        "HATA: 76213 yanlış oyuncuda."
    )

    print(
        "players.json değiştirilmedi."
    )

    raise SystemExit(1)


# --------------------------------------------------
# KAYDET
# --------------------------------------------------

atomic_save(
    players
)


# --------------------------------------------------
# SON KONTROL
# --------------------------------------------------

test_players = load_players()

print()
print("=" * 60)
print("İŞLEM TAMAMLANDI")
print("=" * 60)

print(
    f"Temizlenen yanlış kayıt: "
    f"{len(cleaned)}"
)

print(
    f"Yeni oyuncu sayısı: "
    f"{len(test_players)}"
)

print()
print(
    "76213 artık yalnızca "
    "Q250973 Álvaro Fernández'e ait."
)