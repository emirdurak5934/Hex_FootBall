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


NEW_PLAYERS = [

    {
        "id": "Q63676",
        "name": "Arne Friedrich",
        "birthDate": "1979-05-29",
        "nationality": "Germany",
        "positions": [
            "Defender"
        ],
        "clubs": [
            "SC Verl",
            "Arminia Bielefeld",
            "Hertha BSC",
            "VfL Wolfsburg",
            "Chicago Fire FC"
        ],
        "trophies": [
            "German League Cup winner"
        ],
        "trophies_checked": True,
        "team_trophies_checked_v2": True,
        "transfermarkt_id": "698",
        "nationality_checked": True,
        "position_checked": True
    },

    {
        "id": "Q152458",
        "name": "Bernd Schneider",
        "birthDate": "1973-11-17",
        "nationality": "Germany",
        "positions": [
            "Midfielder"
        ],
        "clubs": [
            "FC Carl Zeiss Jena",
            "Eintracht Frankfurt",
            "Bayer 04 Leverkusen"
        ],
        "trophies": [
            "Thuringia Cup winner"
        ],
        "trophies_checked": True,
        "team_trophies_checked_v2": True,
        "transfermarkt_id": "90",
        "nationality_checked": True,
        "position_checked": True
    },

    {
        "id": "Q285111",
        "name": "Mauricio Victorino",
        "birthDate": "1982-10-11",
        "nationality": "Uruguay",
        "positions": [
            "Defender"
        ],
        "clubs": [
            "Club Nacional",
            "Plaza Colonia",
            "CD Veracruz",
            "Universidad de Chile",
            "Cruzeiro E.C.",
            "Sociedade Esportiva Palmeiras",
            "Club Atlético Independiente",
            "Cerro Porteño",
            "Danubio FC"
        ],
        "trophies": [
            "Copa América winner",
            "Chilean champion",
            "Uruguayan champion"
        ],
        "trophies_checked": True,
        "team_trophies_checked_v2": True,
        "transfermarkt_id": "44935",
        "nationality_checked": True,
        "position_checked": True
    },

    {
        "id": "Q178599",
        "name": "Jorge Fucile",
        "birthDate": "1984-11-19",
        "nationality": "Uruguay",
        "positions": [
            "Defender"
        ],
        "clubs": [
            "Liverpool FC Montevideo",
            "FC Porto",
            "Santos FC",
            "FC Porto B",
            "Club Nacional",
            "FC Cartagena",
            "Juventud de Las Piedras"
        ],
        "trophies": [
            "Europa League winner",
            "Portuguese champion",
            "Portuguese cup winner",
            "Portuguese Super Cup winner",
            "Uruguayan champion",
            "Campeão Paulista"
        ],
        "trophies_checked": True,
        "team_trophies_checked_v2": True,
        "transfermarkt_id": "44057",
        "nationality_checked": True,
        "position_checked": True
    },

    {
        "id": "Q315674",
        "name": "Egidio Arévalo Ríos",
        "birthDate": "1982-01-01",
        "nationality": "Uruguay",
        "positions": [
            "Midfielder"
        ],
        "clubs": [
            "Paysandú Bella Vista",
            "CA Bella Vista",
            "CA Peñarol",
            "Monterrey",
            "Danubio FC",
            "San Luis FC",
            "Botafogo F.R.",
            "Palermo FC",
            "Chicago Fire FC",
            "Monarcas Morelia",
            "Tigres UANL",
            "Atlas Guadalajara",
            "Chiapas FC",
            "CD Veracruz",
            "Racing Club",
            "Club Libertad",
            "Deportivo Municipal",
            "Correcaminos UAT",
            "Institución Atlética Sud América",
            "Sacachispas FC"
        ],
        "trophies": [
            "Copa América winner",
            "Mexican Champion Apertura",
            "Uruguayan champion"
        ],
        "trophies_checked": True,
        "team_trophies_checked_v2": True,
        "transfermarkt_id": "54818",
        "nationality_checked": True,
        "position_checked": True
    },

    {
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
            "US Open Cup winner",
            "MLS Cup winner"
        ],
        "trophies_checked": True,
        "team_trophies_checked_v2": True,
        "transfermarkt_id": "76213",
        "nationality_checked": True,
        "position_checked": True
    },

    {
        "id": "Q126461",
        "name": "Joris Mathijsen",
        "birthDate": "1980-04-05",
        "nationality": "Netherlands",
        "positions": [
            "Defender"
        ],
        "clubs": [
            "Willem II Tilburg",
            "AZ Alkmaar",
            "Hamburger SV",
            "Málaga CF",
            "Feyenoord Rotterdam"
        ],
        "trophies": [
            "UI Cup winner"
        ],
        "trophies_checked": True,
        "team_trophies_checked_v2": True,
        "transfermarkt_id": "4563",
        "nationality_checked": True,
        "position_checked": True
    },

    {
        "id": "Q1085348",
        "name": "Christoph Kramer",
        "birthDate": "1991-02-19",
        "nationality": "Germany",
        "positions": [
            "Midfielder"
        ],
        "clubs": [
            "Bayer 04 Leverkusen",
            "VfL Bochum",
            "Borussia Mönchengladbach"
        ],
        "trophies": [
            "World Cup winner"
        ],
        "trophies_checked": True,
        "team_trophies_checked_v2": True,
        "transfermarkt_id": "82097",
        "nationality_checked": True,
        "position_checked": True
    },

    {
        "id": "Q212617",
        "name": "Ron Vlaar",
        "birthDate": "1985-02-16",
        "nationality": "Netherlands",
        "positions": [
            "Defender"
        ],
        "clubs": [
            "AZ Alkmaar",
            "Feyenoord Rotterdam",
            "Aston Villa"
        ],
        "trophies": [
            "Dutch cup winner"
        ],
        "trophies_checked": True,
        "team_trophies_checked_v2": True,
        "transfermarkt_id": "30697",
        "nationality_checked": True,
        "position_checked": True
    },

    {
        "id": "Q198064",
        "name": "Bruno Martins Indi",
        "birthDate": "1992-02-08",
        "nationality": "Netherlands",
        "positions": [
            "Defender"
        ],
        "clubs": [
            "Feyenoord Rotterdam",
            "FC Porto",
            "Stoke City",
            "AZ Alkmaar",
            "Sparta Rotterdam"
        ],
        "trophies": [],
        "trophies_checked": True,
        "team_trophies_checked_v2": True,
        "transfermarkt_id": "112052",
        "nationality_checked": True,
        "position_checked": True
    },

    {
        "id": "Q62786",
        "name": "Hulk",
        "birthDate": "1986-07-25",
        "nationality": "Brazil",
        "positions": [
            "Forward"
        ],
        "clubs": [
            "EC Vitória",
            "Kawasaki Frontale",
            "Hokkaido Consadole Sapporo",
            "Tokyo Verdy",
            "FC Porto",
            "Zenit St. Petersburg",
            "Shanghai Port FC",
            "Clube Atlético Mineiro"
        ],
        "trophies": [
            "Europa League winner",
            "Portuguese champion",
            "Portuguese cup winner",
            "Portuguese Super Cup winner",
            "Russian champion",
            "Russian cup winner",
            "Russian Super Cup winner",
            "Chinese champion",
            "Chinese Super Cup winner",
            "Brazilian champion",
            "Brazilian cup winner",
            "Winner Supercopa do Brasil",
            "Campeão Mineiro",
            "Confederations Cup winner"
        ],
        "trophies_checked": True,
        "team_trophies_checked_v2": True,
        "transfermarkt_id": "80562",
        "nationality_checked": True,
        "position_checked": True
    },

    {
        "id": "Q2736254",
        "name": "José Fonte",
        "birthDate": "1983-12-22",
        "nationality": "Portugal",
        "positions": [
            "Defender"
        ],
        "clubs": [
            "Sporting CP B",
            "FC Felgueiras",
            "Vitória Setúbal FC",
            "SL Benfica",
            "FC Paços de Ferreira",
            "Estrela Amadora",
            "Crystal Palace",
            "Southampton FC",
            "West Ham United",
            "Dalian Professional",
            "LOSC Lille",
            "SC Braga",
            "Casa Pia AC"
        ],
        "trophies": [
            "European champion",
            "Winner UEFA Nations League",
            "French champion",
            "French Super Cup winner",
            "Portuguese league cup winner",
            "Football League Trophy Winner"
        ],
        "trophies_checked": True,
        "team_trophies_checked_v2": True,
        "transfermarkt_id": "33829",
        "nationality_checked": True,
        "position_checked": True
    }
]


def load_players(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def atomic_save(path, data):
    temp_path = path.with_suffix(".tmp")

    with temp_path.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

        f.flush()
        os.fsync(f.fileno())

    # Temp dosyanın gerçekten sağlam JSON olduğunu kontrol et
    with temp_path.open(
        "r",
        encoding="utf-8"
    ) as f:
        json.load(f)

    os.replace(
        temp_path,
        path
    )


# --------------------------------------------------
# PLAYERS.JSON KONTROL
# --------------------------------------------------

if not PLAYERS_FILE.exists():
    raise FileNotFoundError(
        "data/players.json bulunamadı."
    )


print("players.json yükleniyor...")

players = load_players(
    PLAYERS_FILE
)

old_count = len(players)

print(
    f"Mevcut oyuncu sayısı: {old_count}"
)


# --------------------------------------------------
# YEDEK
# --------------------------------------------------

timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

backup_file = (
    PLAYERS_FILE.parent
    / f"players_before_add_missing_xi_{timestamp}.json"
)

shutil.copy2(
    PLAYERS_FILE,
    backup_file
)

print(
    f"Backup oluşturuldu: {backup_file}"
)


# --------------------------------------------------
# MEVCUT ID VE TRANSFERMARKT ID'LERİ
# --------------------------------------------------

existing_ids = {
    str(player.get("id"))
    for player in players
    if player.get("id")
}

existing_tm_ids = {
    str(player.get("transfermarkt_id"))
    for player in players
    if player.get("transfermarkt_id")
}


# --------------------------------------------------
# OYUNCULARI EKLE
# --------------------------------------------------

added = []
skipped = []


print()
print("=" * 70)
print("OYUNCULAR EKLENİYOR")
print("=" * 70)


for new_player in NEW_PLAYERS:

    player_id = new_player["id"]
    player_name = new_player["name"]
    tm_id = new_player.get(
        "transfermarkt_id"
    )

    if player_id in existing_ids:

        print(
            f"ATLANDI | {player_name} | "
            f"{player_id} zaten mevcut"
        )

        skipped.append(
            player_name
        )

        continue

    # Aynı Transfermarkt ID başka oyuncuda varsa
    # yanlış duplicate oluşmasını engelle
    if (
        tm_id
        and str(tm_id) in existing_tm_ids
    ):

        print()
        print(
            f"UYARI | {player_name}"
        )

        print(
            f"Transfermarkt ID {tm_id} "
            f"başka bir kayıtta zaten bulunuyor."
        )

        print(
            "Bu oyuncu eklenmedi."
        )

        skipped.append(
            player_name
        )

        continue

    players.append(
        new_player
    )

    existing_ids.add(
        player_id
    )

    if tm_id:
        existing_tm_ids.add(
            str(tm_id)
        )

    added.append(
        player_name
    )

    print(
        f"EKLENDİ | {player_name} | "
        f"{player_id} | TM:{tm_id}"
    )


# --------------------------------------------------
# DUPLICATE ID KONTROL
# --------------------------------------------------

seen_ids = set()
duplicate_ids = []

for player in players:

    player_id = player.get("id")

    if not player_id:
        continue

    if player_id in seen_ids:
        duplicate_ids.append(
            player_id
        )

    seen_ids.add(
        player_id
    )


if duplicate_ids:

    print()
    print("HATA: Duplicate oyuncu ID bulundu:")

    for player_id in duplicate_ids:
        print(
            f" - {player_id}"
        )

    print()
    print(
        "players.json değiştirilmedi."
    )

    raise SystemExit(1)


# --------------------------------------------------
# KAYDET
# --------------------------------------------------

atomic_save(
    PLAYERS_FILE,
    players
)


# --------------------------------------------------
# SON DOĞRULAMA
# --------------------------------------------------

saved_players = load_players(
    PLAYERS_FILE
)

new_count = len(
    saved_players
)


print()
print("=" * 70)
print("İŞLEM TAMAMLANDI")
print("=" * 70)

print(
    f"Eski oyuncu sayısı : {old_count}"
)

print(
    f"Eklenen oyuncu      : {len(added)}"
)

print(
    f"Atlanan oyuncu      : {len(skipped)}"
)

print(
    f"Yeni oyuncu sayısı  : {new_count}"
)


if added:

    print()
    print("Eklenenler:")

    for name in added:
        print(
            f" + {name}"
        )


if skipped:

    print()
    print("Atlananlar:")

    for name in skipped:
        print(
            f" - {name}"
        )


print()
print(
    "players.json başarıyla güncellendi."
)