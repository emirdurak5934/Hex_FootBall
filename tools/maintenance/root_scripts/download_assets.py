import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import os
import requests


API_KEY = "123"

BASE_URL = (
    f"https://www.thesportsdb.com/api/v1/json/"
    f"{API_KEY}/searchteams.php"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}


CLUBS = {
    "barcelona": "Barcelona",
    "real_madrid": "Real Madrid",
    "man_united": "Manchester United",
    "juventus": "Juventus",
    "bayern": "Bayern Munich",
    "man_city": "Manchester City",
    "psg": "Paris Saint-Germain",
    "liverpool": "Liverpool",
    "ajax": "Ajax",
    "chelsea": "Chelsea",
    "arsenal": "Arsenal",
}


FLAGS = {
    "argentina": "https://flagcdn.com/w320/ar.png",
    "portugal": "https://flagcdn.com/w320/pt.png",
    "germany": "https://flagcdn.com/w320/de.png",
    "brazil": "https://flagcdn.com/w320/br.png",
    "france": "https://flagcdn.com/w320/fr.png",
    "netherlands": "https://flagcdn.com/w320/nl.png",
    "spain": "https://flagcdn.com/w320/es.png",
}


def download_image(url, path):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            ""
        )

        if "image" not in content_type.lower():

            print(
                "GÖRSEL DEĞİL:",
                path,
                content_type
            )

            return False

        with open(
            path,
            "wb"
        ) as file:

            file.write(
                response.content
            )

        print(
            "İNDİRİLDİ:",
            path
        )

        return True

    except Exception as error:

        print(
            "İNDİRME HATASI:",
            path,
            error
        )

        return False


def find_team(team_name):

    try:

        response = requests.get(
            BASE_URL,
            params={
                "t": team_name
            },
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        teams = data.get(
            "teams"
        )

        if not teams:

            print(
                "TAKIM BULUNAMADI:",
                team_name
            )

            return None

        # Futbol takımını tercih et
        for team in teams:

            sport = (
                team.get(
                    "strSport",
                    ""
                )
                .lower()
            )

            if sport == "soccer":

                return team

        return teams[0]

    except Exception as error:

        print(
            "API HATASI:",
            team_name,
            error
        )

        return None


def get_team_badge(team):

    possible_fields = [
        "strBadge",
        "strTeamBadge",
        "strLogo"
    ]

    for field in possible_fields:

        value = team.get(
            field
        )

        if value:

            return value

    return None


# ==================================================
# KLASÖRLER
# ==================================================

os.makedirs(
    "assets/clubs",
    exist_ok=True
)

os.makedirs(
    "assets/flags",
    exist_ok=True
)


# ==================================================
# KULÜP LOGOLARI
# ==================================================

print(
    "\n=============================="
)

print(
    "KULÜP LOGOLARI"
)

print(
    "==============================\n"
)


club_success = 0
club_failed = 0


for file_name, team_name in CLUBS.items():

    print(
        "Aranıyor:",
        team_name
    )

    team = find_team(
        team_name
    )

    if not team:

        club_failed += 1
        continue


    print(
        "Bulundu:",
        team.get(
            "strTeam"
        )
    )


    badge_url = get_team_badge(
        team
    )


    if not badge_url:

        print(
            "LOGO BULUNAMADI:",
            team_name
        )

        club_failed += 1

        continue


    print(
        "Logo:",
        badge_url
    )


    path = (
        "assets/clubs/"
        + file_name
        + ".png"
    )


    success = download_image(
        badge_url,
        path
    )


    if success:

        club_success += 1

    else:

        club_failed += 1


# ==================================================
# BAYRAKLAR
# ==================================================

print(
    "\n=============================="
)

print(
    "ÜLKE BAYRAKLARI"
)

print(
    "==============================\n"
)


flag_success = 0
flag_failed = 0


for file_name, url in FLAGS.items():

    path = (
        "assets/flags/"
        + file_name
        + ".png"
    )


    # Zaten varsa yeniden indirme
    if os.path.exists(
        path
    ):

        print(
            "ZATEN VAR:",
            path
        )

        flag_success += 1

        continue


    success = download_image(
        url,
        path
    )


    if success:

        flag_success += 1

    else:

        flag_failed += 1


# ==================================================
# SONUÇ
# ==================================================

print(
    "\n=============================="
)

print(
    "TAMAMLANDI"
)

print(
    "=============================="
)


print(
    "Kulüp logosu indirilen:",
    club_success
)

print(
    "Kulüp logosu başarısız:",
    club_failed
)

print(
    "Bayrak hazır:",
    flag_success
)

print(
    "Bayrak başarısız:",
    flag_failed
)