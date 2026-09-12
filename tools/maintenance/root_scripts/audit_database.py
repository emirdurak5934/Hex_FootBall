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
# DATABASE YÜKLE
# ==================================================

with open(
    PLAYERS_FILE,
    "r",
    encoding="utf-8"
) as file:

    players = json.load(file)


print()

print(
    "=" * 60
)

print(
    "DATABASE AUDIT"
)

print(
    "=" * 60
)

print(
    "TOPLAM OYUNCU:",
    len(players)
)


# ==================================================
# KULÜP ALIASLARI
# ==================================================

CLUBS = {

    # ==================================================
    # İNGİLTERE
    # ==================================================

    "Arsenal": [

        "Arsenal",
        "Arsenal FC",
        "Arsenal F.C."

    ],

    "Liverpool": [

        "Liverpool",
        "Liverpool FC",
        "Liverpool F.C."

    ],

    "Manchester United": [

        "Manchester United",
        "Manchester United FC",
        "Manchester United F.C."

    ],

    "Manchester City": [

        "Manchester City",
        "Manchester City FC",
        "Manchester City F.C."

    ],

    "Tottenham Hotspur": [

        "Tottenham Hotspur",
        "Tottenham Hotspur FC",
        "Tottenham Hotspur F.C.",
        "Tottenham"

    ],

    "Newcastle United": [

        "Newcastle United",
        "Newcastle United FC",
        "Newcastle United F.C."

    ],

    "Chelsea": [

        "Chelsea",
        "Chelsea FC",
        "Chelsea F.C."

    ],


    # ==================================================
    # İSPANYA
    # ==================================================

    "Sevilla": [

        "Sevilla",
        "Sevilla FC",
        "Sevilla F.C."

    ],

    "Atletico Madrid": [

        "Atlético Madrid",
        "Atletico Madrid",
        "Atlético de Madrid",
        "Club Atlético de Madrid",
        "Club Atletico de Madrid"

    ],

    "Barcelona": [

        "Barcelona",
        "FC Barcelona"

    ],

    "Real Madrid": [

        "Real Madrid",
        "Real Madrid CF",
        "Real Madrid C.F.",
        "Real Madrid Club de Fútbol",
        "Real Madrid Club de Futbol"

    ],


    # ==================================================
    # İTALYA
    # ==================================================

    "AC Milan": [

        "AC Milan",
        "A.C. Milan",
        "Milan",
        "Milan AC"

    ],

    "Inter Milan": [

        "Inter Milan",
        "Inter",
        "Internazionale",
        "Internazionale Milano",
        "FC Internazionale Milano",
        "F.C. Internazionale Milano"

    ],

    "AS Roma": [

        "AS Roma",
        "A.S. Roma",
        "Roma"

    ],

    "Napoli": [

        "Napoli",
        "SSC Napoli",
        "S.S.C. Napoli"

    ],

    "Juventus": [

        "Juventus",
        "Juventus FC",
        "Juventus F.C."

    ],


    # ==================================================
    # FRANSA
    # ==================================================

    "PSG": [

        "Paris Saint-Germain",
        "Paris Saint-Germain FC",
        "Paris Saint-Germain F.C.",
        "Paris Saint-Germain Football Club",
        "PSG"

    ],

    "Monaco": [

        "Monaco",
        "AS Monaco",
        "A.S. Monaco",
        "AS Monaco FC",
        "A.S. Monaco FC"

    ],


    # ==================================================
    # ALMANYA
    # ==================================================

    "Bayern Munich": [

        "Bayern Munich",
        "Bayern München",
        "FC Bayern Munich",
        "FC Bayern München",
        "FC Bayern München e.V."

    ],

    "Borussia Dortmund": [

        "Borussia Dortmund",
        "BVB",
        "BV Borussia 09 Dortmund",
        "Ballspielverein Borussia 09 e.V. Dortmund"

    ],


    # ==================================================
    # PORTEKİZ
    # ==================================================

    "Benfica": [

        "Benfica",
        "SL Benfica",
        "S.L. Benfica",
        "Sport Lisboa e Benfica"

    ],

    "Sporting CP": [

        "Sporting",
        "Sporting CP",
        "Sporting Clube de Portugal",
        "Sporting Lisbon",
        "Sporting Lisboa"

    ],


    # ==================================================
    # HOLLANDA
    # ==================================================

    "Ajax": [

        "Ajax",
        "AFC Ajax",
        "A.F.C. Ajax",
        "Amsterdamsche Football Club Ajax"

    ],


    # ==================================================
    # TÜRKİYE
    # ==================================================

    "Galatasaray": [

        "Galatasaray",
        "Galatasaray SK",
        "Galatasaray S.K.",
        "Galatasaray Spor Kulübü"

    ],

    "Fenerbahce": [

        "Fenerbahçe",
        "Fenerbahce",
        "Fenerbahçe SK",
        "Fenerbahçe S.K.",
        "Fenerbahçe Istanbul",
        "Fenerbahce Istanbul",
        "Fenerbahçe Spor Kulübü"

    ],

    "Besiktas": [

        "Beşiktaş",
        "Besiktas",
        "Beşiktaş JK",
        "Beşiktaş J.K.",
        "Besiktas JK",
        "Beşiktaş J.K. (Football)",
        "Beşiktaş Jimnastik Kulübü"

    ],

    "Trabzonspor": [

        "Trabzonspor",
        "Trabzonspor Kulübü",
        "Trabzonspor A.Ş.",
        "Trabzonspor AS"

    ]

}


# ==================================================
# OYUNCUNUN KULÜPLERİNİ AL
# ==================================================

def get_player_clubs(player):

    result = []

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

        result.append(
            normalize(
                name
            )
        )

    return result


# ==================================================
# KULÜP BAŞINA OYUNCU SAYISI
# ==================================================

print()

print(
    "=" * 60
)

print(
    "KULÜP BAŞINA DATABASE OYUNCU SAYISI"
)

print(
    "=" * 60
)


club_players = {}


for club_name, aliases in CLUBS.items():

    normalized_aliases = {
        normalize(alias)
        for alias in aliases
    }

    found = []


    for player in players:

        player_clubs = get_player_clubs(
            player
        )

        matched = False


        for player_club in player_clubs:

            if player_club in normalized_aliases:

                matched = True
                break


        if matched:

            found.append(
                player
            )


    club_players[
        club_name
    ] = found


    print(
        f"{club_name:<22} : {len(found)}"
    )


# ==================================================
# ÖNEMLİ OYUNCU KONTROLÜ
# ==================================================

print()

print(
    "=" * 60
)

print(
    "ÖNEMLİ OYUNCU KONTROLÜ"
)

print(
    "=" * 60
)


TEST_PLAYERS = [

    "Luka Modrić",

    "Cristiano Ronaldo",

    "Lionel Messi",

    "Neymar",

    "Zlatan Ibrahimović",

    "Robert Lewandowski",

    "Sergio Ramos",

    "Karim Benzema",

    "Andrés Iniesta",

    "Xavi",

    "Kaká",

    "Ronaldinho"

]


for test_name in TEST_PLAYERS:

    target = normalize(
        test_name
    )

    found_player = None


    for player in players:

        player_name = normalize(
            player.get(
                "name",
                ""
            )
        )

        if player_name == target:

            found_player = player
            break


    if found_player:

        print(
            f"OK   | {test_name}"
        )

    else:

        print(
            f"YOK  | {test_name}"
        )


# ==================================================
# DUPLICATE ID KONTROLÜ
# ==================================================

print()

print(
    "=" * 60
)

print(
    "DUPLICATE ID KONTROLÜ"
)

print(
    "=" * 60
)


seen_ids = set()

duplicate_ids = set()


for player in players:

    player_id = str(
        player.get(
            "id",
            ""
        )
    ).strip()

    if not player_id:

        continue


    if player_id in seen_ids:

        duplicate_ids.add(
            player_id
        )


    seen_ids.add(
        player_id
    )


if duplicate_ids:

    for player_id in sorted(
        duplicate_ids
    ):

        print(
            "DUPLICATE:",
            player_id
        )

else:

    print(
        "Duplicate ID bulunamadı."
    )


# ==================================================
# AYNI İSİMLİ OYUNCULAR
# ==================================================

print()

print(
    "=" * 60
)

print(
    "AYNI İSİMLİ OYUNCULAR"
)

print(
    "=" * 60
)


name_counts = {}


for player in players:

    player_name = str(
        player.get(
            "name",
            ""
        )
    ).strip()

    if not player_name:

        continue


    key = normalize(
        player_name
    )


    name_counts[key] = (
        name_counts.get(
            key,
            0
        )
        +
        1
    )


duplicate_name_count = 0


for player_name, count in sorted(
    name_counts.items()
):

    if count > 1:

        duplicate_name_count += 1


print(
    "Aynı isimli farklı kayıt sayısı:",
    duplicate_name_count
)


# ==================================================
# BOŞ İSİMLİ OYUNCULAR
# ==================================================

print()

print(
    "=" * 60
)

print(
    "BOŞ İSİMLİ OYUNCULAR"
)

print(
    "=" * 60
)


empty_names = []


for player in players:

    player_name = str(
        player.get(
            "name",
            ""
        )
    ).strip()


    if not player_name:

        empty_names.append(
            player
        )


print(
    "Toplam:",
    len(empty_names)
)


# ==================================================
# BOŞ ID
# ==================================================

print()

print(
    "=" * 60
)

print(
    "BOŞ ID"
)

print(
    "=" * 60
)


empty_ids = []


for player in players:

    player_id = str(
        player.get(
            "id",
            ""
        )
    ).strip()


    if not player_id:

        empty_ids.append(
            player
        )


print(
    "Toplam:",
    len(empty_ids)
)


# ==================================================
# NATIONALITY BOŞ
# ==================================================

print()

print(
    "=" * 60
)

print(
    "MİLLİYET BİLGİSİ OLMAYAN OYUNCULAR"
)

print(
    "=" * 60
)


empty_nationality = []


for player in players:

    nationality = str(
        player.get(
            "nationality",
            ""
        )
    ).strip()


    if not nationality:

        empty_nationality.append(
            player
        )


print(
    "Toplam:",
    len(empty_nationality)
)


# ==================================================
# CLUBS BOŞ
# ==================================================

print()

print(
    "=" * 60
)

print(
    "KULÜP BİLGİSİ OLMAYAN OYUNCULAR"
)

print(
    "=" * 60
)


empty_clubs = []


for player in players:

    clubs = player.get(
        "clubs",
        []
    )


    if not clubs:

        empty_clubs.append(
            player
        )


print(
    "Toplam:",
    len(empty_clubs)
)


# ==================================================
# TROPHIES BOŞ
# ==================================================

print()

print(
    "=" * 60
)

print(
    "KUPA BİLGİSİ OLMAYAN OYUNCULAR"
)

print(
    "=" * 60
)


empty_trophies = []


for player in players:

    trophies = player.get(
        "trophies",
        []
    )


    if not trophies:

        empty_trophies.append(
            player
        )


print(
    "Toplam:",
    len(empty_trophies)
)


# ==================================================
# PROBLEMLİ KULÜPLER
# ==================================================

print()

print(
    "=" * 60
)

print(
    "ŞÜPHELİ KULÜP SAYILARI"
)

print(
    "=" * 60
)


for club_name, found in club_players.items():

    count = len(
        found
    )


    if count < 50:

        print(
            f"UYARI | {club_name:<22} : {count}"
        )


# ==================================================
# SONUÇ
# ==================================================

print()

print(
    "=" * 60
)

print(
    "AUDIT TAMAMLANDI"
)

print(
    "=" * 60
)

print()