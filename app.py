from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    abort,
)

from flask_socketio import (
    SocketIO,
    emit,
    join_room,
    leave_room
)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

import json
import os
import secrets
import time
import unicodedata
import re
import random
import string
import threading
import uuid
from itertools import combinations

from criterion_engine import CriterionEngine
from tiki_taka_engine import TikiTakaEngine
from profile_store import AVATARS, ProfileStore
from friend_store import FriendStore
from ads import mark_match_outcome, public_ad_break, register_ads
from league_clubs import LEAGUE_CLUB_ALIASES as HISTORICAL_LEAGUE_CLUB_ALIASES

from datetime import date, datetime, timedelta


# ==================================================
# APP
# ==================================================

app = Flask(__name__)
register_ads(app)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
IS_PRODUCTION = os.environ.get("FLASK_ENV") == "production"
MOBILE_ORIGINS = {
    "capacitor://localhost",
    "http://localhost",
    "https://localhost",
}

app.config["SECRET_KEY"] = os.environ.get("FOOTBALL_MATCH_SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None" if IS_PRODUCTION else "Lax",
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
    PERMANENT_SESSION_LIFETIME=timedelta(
        days=int(os.environ.get("FOOTBALL_SESSION_DAYS", "30"))
    ),
)
MOBILE_SOCKET_TOKEN_MAX_AGE = int(os.environ.get("FOOTBALL_SOCKET_TOKEN_SECONDS", "900"))
mobile_socket_tokens = URLSafeTimedSerializer(
    app.config["SECRET_KEY"], salt="football-mobile-socket-v1",
)

SUPPORT_EMAIL = os.environ.get("FOOTBALL_SUPPORT_EMAIL", "").strip()

PROFILE_DB = os.environ.get(
    "FOOTBALL_MATCH_PROFILE_DB",
    os.path.join(app.instance_path, "football_match.sqlite3"),
)
profile_store = ProfileStore(PROFILE_DB)
friend_store = FriendStore(profile_store)


def current_user():
    return profile_store.get_user(session.get("user_id"))


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def valid_csrf():
    supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    return bool(supplied and secrets.compare_digest(supplied, session.get("csrf_token", "")))


app.jinja_env.globals.update(current_user=current_user, csrf_token=csrf_token)


@app.after_request
def allow_mobile_app_origin(response):
    origin = request.headers.get("Origin", "")
    if origin in MOBILE_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, X-CSRF-Token, X-Football-Mobile-Shell"
        )
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response


socketio = SocketIO(
    app,
    cors_allowed_origins=[
        "https://edyn-football.onrender.com",
        *sorted(MOBILE_ORIGINS),
    ],
)


PLAYERS_FILE = os.path.join(PROJECT_ROOT, "data", "players.json")
MISSING_XI_MATCHES_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "missing_xi_matches.json",
)
HEATMAP_BOARDS_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "heatmap_boards.json",
)
LOCAL_GAME_TTL_SECONDS = int(os.environ.get("FOOTBALL_LOCAL_GAME_TTL_SECONDS", "3600"))
FINISHED_GAME_TTL_SECONDS = int(os.environ.get("FOOTBALL_FINISHED_GAME_TTL_SECONDS", "900"))
MAX_LOCAL_GAME_STATES = int(os.environ.get("FOOTBALL_MAX_LOCAL_GAME_STATES", "300"))


# ==================================================
# VERİTABANI
# ==================================================

def load_players():

    for attempt in range(10):

        try:

            with open(
                PLAYERS_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

        except json.JSONDecodeError:

            print(
                "players.json şu anda yazılıyor. "
                "Tekrar deneniyor..."
            )

            time.sleep(1)

    raise RuntimeError(
        "players.json okunamadı."
    )


players = load_players()


def load_missing_xi_matches():
    with open(MISSING_XI_MATCHES_FILE, "r", encoding="utf-8") as file:
        matches = json.load(file)
    player_ids = {str(player.get("id", "")).strip() for player in players}
    valid_matches = []
    for match in matches:
        lineup = match.get("lineup", [])
        missing_ids = [str(item.get("player_id", "")).strip() for item in lineup
                       if str(item.get("player_id", "")).strip() not in player_ids]
        slots = [item.get("slot") for item in lineup]
        if len(lineup) != 11 or sorted(slots) != list(range(11)):
            print(f"Kayip 11 maci atlandi (gecersiz slotlar): {match.get('id')}")
            continue
        if any(not str(item.get("answer", "")).strip() for item in lineup):
            print(f"Kayip 11 maci atlandi (Wordle cevabi eksik): {match.get('id')}")
            continue
        if any(not isinstance(item.get("shirt_number"), int) or item["shirt_number"] < 1
               for item in lineup):
            print(f"Kayip 11 maci atlandi (forma numarasi eksik): {match.get('id')}")
            continue
        if missing_ids:
            print(f"Kayip 11 maci atlandi (oyuncu bulunamadi): {match.get('id')} {missing_ids}")
            continue
        valid_matches.append(match)
    if not valid_matches:
        raise RuntimeError("Gecerli Kayip 11 test maci bulunamadi.")
    return valid_matches


missing_xi_matches = load_missing_xi_matches()
missing_xi_games = {}
missing_xi_games_lock = threading.Lock()


def missing_xi_wordle_name(value):
    """Return uppercase letters only, with accents removed, for Wordle."""
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(
        char.upper()
        for char in decomposed
        if not unicodedata.combining(char) and char.isalpha()
    )


def missing_xi_wordle_feedback(target, guess):
    """Standard two-pass Wordle scoring with duplicate-letter limits."""
    feedback = ["gray"] * len(guess)
    remaining = {}
    for index, letter in enumerate(target):
        if index < len(guess) and guess[index] == letter:
            feedback[index] = "green"
        else:
            remaining[letter] = remaining.get(letter, 0) + 1
    for index, letter in enumerate(guess):
        if feedback[index] == "green":
            continue
        if remaining.get(letter, 0) > 0:
            feedback[index] = "yellow"
            remaining[letter] -= 1
    return feedback


print(
    f"Oyuncu veritabanı yüklendi: "
    f"{len(players)} oyuncu"
)


def prune_local_game_store(store, now=None, reserve=0):
    """Bound transient local-game memory without affecting active games."""
    now = time.time() if now is None else now
    stale = []
    for token, game in store.items():
        created_at = game.get("created_at", now)
        ttl = FINISHED_GAME_TTL_SECONDS if game.get("finished") else LOCAL_GAME_TTL_SECONDS
        if now - created_at > ttl:
            stale.append(token)
    for token in stale:
        store.pop(token, None)

    allowed = max(1, MAX_LOCAL_GAME_STATES - max(0, reserve))
    overflow = len(store) - allowed
    if overflow > 0:
        oldest = sorted(
            store,
            key=lambda token: store[token].get("created_at", now),
        )[:overflow]
        for token in oldest:
            store.pop(token, None)
    return len(stale) + max(0, overflow)


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

    "Ζ": "Z",
    "ζ": "z",

    "Η": "H",

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

    "Υ": "Y",
    "υ": "y",

    "Χ": "X",
    "χ": "x",


    # KİRİL

    "А": "A",
    "а": "a",

    "В": "B",
    "в": "b",

    "Е": "E",
    "е": "e",

    "К": "K",
    "к": "k",

    "М": "M",
    "м": "m",

    "Н": "H",
    "н": "h",

    "О": "O",
    "о": "o",

    "Р": "P",
    "р": "p",

    "С": "C",
    "с": "c",

    "Т": "T",
    "т": "t",

    "Х": "X",
    "х": "x",

    "У": "Y",
    "у": "y"

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
# DOĞUM TARİHİ
# ==================================================

def get_birth_date(player):

    possible_values = [

        player.get("birth_date"),
        player.get("date_of_birth"),
        player.get("dob"),
        player.get("birthday")

    ]


    for value in possible_values:

        if not value:

            continue


        if isinstance(
            value,
            str
        ):

            return value.strip()


    return ""


def parse_birth_date(value):

    if not value:

        return None


    formats = [

        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m",
        "%Y"

    ]


    for fmt in formats:

        try:

            return datetime.strptime(
                value[:10],
                fmt
            ).date()

        except Exception:

            continue


    return None


def calculate_age(player):

    born = parse_birth_date(
        get_birth_date(
            player
        )
    )


    if not born:

        return None


    today = date.today()


    return (
        today.year
        -
        born.year
        -
        (
            (today.month, today.day)
            <
            (born.month, born.day)
        )
    )


# ==================================================
# OYUNCU BUL
# ==================================================

def find_player_by_id(
    player_id
):

    target = str(
        player_id
    ).strip()


    if not target:

        return None


    for player in players:

        if str(
            player.get(
                "id",
                ""
            )
        ).strip() == target:

            return player


    return None


def find_players_by_name(
    name
):

    target = normalize(
        name
    )


    matches = []


    for player in players:

        if normalize(
            player.get(
                "name",
                ""
            )
        ) == target:

            matches.append(
                player
            )


    return matches


# ==================================================
# KULÜP ALIASLARI
# ==================================================

CLUB_ALIASES = {

    "arsenal": [
        "Arsenal",
        "Arsenal FC",
        "Arsenal F.C."
    ],

    "liverpool": [
        "Liverpool",
        "Liverpool FC",
        "Liverpool F.C."
    ],

    "manchester united": [
        "Manchester United",
        "Manchester United FC",
        "Manchester United F.C."
    ],

    "manchester city": [
        "Manchester City",
        "Manchester City FC",
        "Manchester City F.C."
    ],

    "tottenham hotspur": [
        "Tottenham Hotspur",
        "Tottenham Hotspur FC",
        "Tottenham Hotspur F.C.",
        "Tottenham"
    ],

    "newcastle united": [
        "Newcastle United",
        "Newcastle United FC",
        "Newcastle United F.C."
    ],

    "chelsea": [
        "Chelsea",
        "Chelsea FC",
        "Chelsea F.C."
    ],

    "sevilla": [
        "Sevilla",
        "Sevilla FC",
        "Sevilla F.C."
    ],

    "atletico madrid": [
        "Atlético Madrid",
        "Atletico Madrid",
        "Atlético de Madrid",
        "Club Atlético de Madrid",
        "Club Atletico de Madrid"
    ],

    "barcelona": [
        "Barcelona",
        "FC Barcelona"
    ],

    "real madrid": [
        "Real Madrid",
        "Real Madrid CF",
        "Real Madrid C.F.",
        "Real Madrid Club de Fútbol",
        "Real Madrid Club de Futbol"
    ],

    "ac milan": [
        "AC Milan",
        "A.C. Milan",
        "Milan",
        "Milan AC"
    ],

    "inter milan": [
        "Inter",
        "Inter Milan",
        "Internazionale",
        "Internazionale Milano",
        "FC Internazionale Milano",
        "F.C. Internazionale Milano"
    ],

    "as roma": [
        "AS Roma",
        "A.S. Roma",
        "Roma"
    ],

    "napoli": [
        "Napoli",
        "SSC Napoli",
        "S.S.C. Napoli"
    ],

    "juventus": [
        "Juventus",
        "Juventus FC",
        "Juventus F.C."
    ],

    "paris saint-germain": [
        "Paris Saint-Germain",
        "Paris Saint-Germain FC",
        "Paris Saint-Germain F.C.",
        "Paris Saint-Germain Football Club",
        "PSG"
    ],

    "as monaco": [
        "AS Monaco",
        "A.S. Monaco",
        "AS Monaco FC",
        "A.S. Monaco FC",
        "Monaco"
    ],

    "bayern munich": [
        "Bayern Munich",
        "Bayern München",
        "FC Bayern Munich",
        "FC Bayern München",
        "FC Bayern München e.V."
    ],

    "borussia dortmund": [
        "Borussia Dortmund",
        "BVB",
        "BV Borussia 09 Dortmund",
        "Ballspielverein Borussia 09 e.V. Dortmund"
    ],

    "benfica": [
        "Benfica",
        "SL Benfica",
        "S.L. Benfica",
        "Sport Lisboa e Benfica"
    ],

    "sporting cp": [
        "Sporting",
        "Sporting CP",
        "Sporting Clube de Portugal",
        "Sporting Lisbon",
        "Sporting Lisboa"
    ],

    "ajax": [
        "Ajax",
        "AFC Ajax",
        "A.F.C. Ajax",
        "Amsterdamsche Football Club Ajax"
    ],

    "galatasaray": [
        "Galatasaray",
        "Galatasaray SK",
        "Galatasaray S.K.",
        "Galatasaray Spor Kulübü"
    ],

    "fenerbahce": [
        "Fenerbahçe",
        "Fenerbahce",
        "Fenerbahçe SK",
        "Fenerbahçe S.K.",
        "Fenerbahçe Istanbul",
        "Fenerbahce Istanbul",
        "Fenerbahçe Spor Kulübü"
    ],

    "besiktas": [
        "Beşiktaş",
        "Besiktas",
        "Beşiktaş JK",
        "Beşiktaş J.K.",
        "Besiktas JK",
        "Beşiktaş J.K. (Football)",
        "Beşiktaş Jimnastik Kulübü"
    ],

    "trabzonspor": [
        "Trabzonspor",
        "Trabzonspor Kulübü",
        "Trabzonspor A.Ş.",
        "Trabzonspor AS"
    ]

}


# ==================================================
# KULÜP KONTROL
# ==================================================

def get_club_names(player):

    names = []


    for club in player.get(
        "clubs",
        []
    ):

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

            names.append(
                name
            )


    return names


def matches_club(
    player,
    club_name
):

    target = normalize(
        club_name
    )


    accepted_names = {
        target
    }


    for canonical_name, aliases in CLUB_ALIASES.items():

        canonical = normalize(
            canonical_name
        )


        alias_set = {
            normalize(alias)
            for alias in aliases
        }


        if (
            target == canonical
            or
            target in alias_set
        ):

            accepted_names.add(
                canonical
            )

            accepted_names.update(
                alias_set
            )

            break


    for club in get_club_names(
        player
    ):

        if normalize(
            club
        ) in accepted_names:

            return True


    return False


# ==================================================
# ÜLKE ALIAS
# ==================================================

COUNTRY_ALIASES = {

    "england": [
        "England"
    ],

    "spain": [
        "Spain"
    ],

    "portugal": [
        "Portugal"
    ],

    "netherlands": [
        "Netherlands",
        "Holland"
    ],

    "italy": [
        "Italy"
    ],

    "france": [
        "France"
    ],

    "germany": [
        "Germany"
    ],

    "turkey": [
        "Turkey",
        "Türkiye",
        "Turkiye"
    ],

    "brazil": [
        "Brazil"
    ],

    "argentina": [
        "Argentina"
    ]

}


def matches_nationality(
    player,
    nationality
):

    target = normalize(
        nationality
    )


    accepted_names = {
        target
    }


    for canonical_name, aliases in COUNTRY_ALIASES.items():

        canonical = normalize(
            canonical_name
        )


        alias_set = {
            normalize(alias)
            for alias in aliases
        }


        if (
            target == canonical
            or
            target in alias_set
        ):

            accepted_names.add(
                canonical
            )

            accepted_names.update(
                alias_set
            )

            break


    current = normalize(
        player.get(
            "nationality",
            ""
        )
    )


    return (
        current
        in
        accepted_names
    )


# ==================================================
# KUPA ALIASLARI
# ==================================================

TROPHY_ALIASES = {

    "english champion": [
        "English Champion"
    ],

    "turkish champion": [
        "Turkish champion"
    ],

    "spanish champion": [
        "Spanish champion"
    ],

    "italian champion": [
        "Italian champion"
    ],

    "german champion": [
        "German Champion"
    ],

    "french champion": [
        "French champion"
    ],

    "champions league": [
        "UEFA Champions League winner",
        "European Champion Clubs' Cup winner"
    ],

    "europa league": [
        "Europa League winner",
        "Uefa Cup winner",
        "UEFA Cup winner"
    ],

    "world cup": [
        "World Cup winner"
    ],

    "european championship": [
        "European champion"
    ],

    "copa america": [
        "Copa América winner",
        "Copa America winner",
        "Copa América champion",
        "Copa America champion"
    ],

    "ballon dor": [
        "Winner Ballon d'Or",
        "Winner Ballon d’Or"
    ],

    "fa cup": [
        "English FA Cup winner"
    ],

    "coppa italia": [
        "Italian cup winner"
    ],

    "copa del rey": [
        "Spanish cup winner"
    ]

}


def clean_trophy_name(
    trophy_name
):

    trophy_name = str(
        trophy_name
    ).strip()


    trophy_name = re.sub(
        r"^\d+x\s+",
        "",
        trophy_name,
        flags=re.IGNORECASE
    )


    return normalize(
        trophy_name
    )


def get_trophy_names(player):

    names = []


    for trophy in player.get(
        "trophies",
        []
    ):

        if isinstance(
            trophy,
            dict
        ):

            name = (
                trophy.get("name")
                or
                trophy.get("title")
                or
                trophy.get("trophy")
                or
                ""
            )

        else:

            name = str(
                trophy
            )


        if name:

            names.append(
                name
            )


    return names


def matches_trophy(
    player,
    trophy_name
):

    target = normalize(
        trophy_name
    )


    accepted_names = {
        target
    }


    for canonical_name, aliases in TROPHY_ALIASES.items():

        canonical = normalize(
            canonical_name
        )


        alias_set = {
            normalize(alias)
            for alias in aliases
        }


        if (
            target == canonical
            or
            target in alias_set
        ):

            accepted_names.add(
                canonical
            )

            accepted_names.update(
                alias_set
            )

            break


    for trophy in get_trophy_names(
        player
    ):

        if clean_trophy_name(
            trophy
        ) in accepted_names:

            return True


    return False


POSITION_GROUPS = {
    "Goalkeeper": {"goalkeeper", "keeper"},
    "Defender": {
        "defender", "centre back", "center back", "left back",
        "right back", "sweeper", "wing back", "left wing back",
        "right wing back", "full back", "back", "stopper",
    },
    "Midfielder": {
        "midfielder", "defensive midfield", "central midfield",
        "attacking midfield", "left midfield", "right midfield",
        "holding midfield", "centre midfield", "center midfield",
        "defensive midfielder", "central midfielder", "centre midfielder",
        "attacking midfielder", "left midfielder", "right midfielder",
        "wide midfielder", "wing half", "playmaker",
    },
    "Forward": {
        "forward", "left winger", "right winger", "winger",
        "centre forward", "center forward", "second striker", "striker",
        "inside forward", "attacker",
    },
}


# Possession continent criteria follow the represented senior national team,
# stored in player["nationality"]. Unknown values intentionally do not match.
COUNTRY_TO_CONTINENT = {
    # Europe
    "Albania": "Europe", "Andorra": "Europe", "Armenia": "Europe",
    "Austria": "Europe", "Azerbaijan": "Europe", "Belarus": "Europe",
    "Belgium": "Europe", "Bosnia and Herzegovina": "Europe",
    "Bulgaria": "Europe", "Croatia": "Europe", "Cyprus": "Europe",
    "Czech Republic": "Europe", "Czechia": "Europe", "Denmark": "Europe",
    "England": "Europe", "Estonia": "Europe", "Faroe Islands": "Europe",
    "Finland": "Europe", "France": "Europe", "Georgia": "Europe",
    "Germany": "Europe", "Gibraltar": "Europe", "Greece": "Europe",
    "Hungary": "Europe", "Iceland": "Europe", "Ireland": "Europe",
    "Italy": "Europe", "Kosovo": "Europe", "Latvia": "Europe",
    "Liechtenstein": "Europe", "Lithuania": "Europe",
    "Luxembourg": "Europe", "Malta": "Europe", "Moldova": "Europe",
    "Monaco": "Europe", "Montenegro": "Europe", "Netherlands": "Europe",
    "North Macedonia": "Europe", "Northern Ireland": "Europe",
    "Norway": "Europe", "Poland": "Europe", "Portugal": "Europe",
    "Republic of Ireland": "Europe", "Romania": "Europe",
    "Russia": "Europe", "San Marino": "Europe", "Scotland": "Europe",
    "Serbia": "Europe", "Slovakia": "Europe", "Slovenia": "Europe",
    "Spain": "Europe", "Sweden": "Europe", "Switzerland": "Europe",
    "Turkey": "Europe", "Ukraine": "Europe", "United Kingdom": "Europe",
    "Wales": "Europe",
    # South America
    "Argentina": "South America", "Bolivia": "South America",
    "Brazil": "South America", "Chile": "South America",
    "Colombia": "South America", "Ecuador": "South America",
    "Guyana": "South America", "Paraguay": "South America",
    "Peru": "South America", "Suriname": "South America",
    "Uruguay": "South America", "Venezuela": "South America",
    # Africa
    "Algeria": "Africa", "Angola": "Africa", "Benin": "Africa",
    "Botswana": "Africa", "Burkina Faso": "Africa", "Burundi": "Africa",
    "Cameroon": "Africa", "Cape Verde": "Africa",
    "Central African Republic": "Africa", "Comoros": "Africa",
    "Democratic Republic of the Congo": "Africa",
    "Republic of the Congo": "Africa", "Egypt": "Africa",
    "Equatorial Guinea": "Africa", "Ethiopia": "Africa", "Gabon": "Africa",
    "The Gambia": "Africa", "Ghana": "Africa", "Guinea": "Africa",
    "Guinea-Bissau": "Africa", "Ivory Coast": "Africa", "Kenya": "Africa",
    "Liberia": "Africa", "Libya": "Africa", "Madagascar": "Africa",
    "Malawi": "Africa", "Mali": "Africa", "Mauritania": "Africa",
    "Mauritius": "Africa", "Morocco": "Africa", "Mozambique": "Africa",
    "Namibia": "Africa", "Niger": "Africa", "Nigeria": "Africa",
    "Rwanda": "Africa", "Senegal": "Africa", "Seychelles": "Africa",
    "Sierra Leone": "Africa", "Somalia": "Africa", "South Africa": "Africa",
    "Sudan": "Africa", "Tanzania": "Africa", "Togo": "Africa",
    "Tunisia": "Africa", "Uganda": "Africa", "Zambia": "Africa",
    "Zimbabwe": "Africa",
    # Asia pool (Australia is intentionally assigned here per game rules).
    "Afghanistan": "Asia", "Australia": "Asia", "Bahrain": "Asia",
    "Bangladesh": "Asia", "Brunei": "Asia", "China": "Asia",
    "Chinese Taipei": "Asia", "Hong Kong": "Asia", "India": "Asia",
    "Indonesia": "Asia", "Iran": "Asia", "Iraq": "Asia", "Israel": "Asia",
    "Japan": "Asia", "Jordan": "Asia", "Kazakhstan": "Asia",
    "Kuwait": "Asia", "Kyrgyzstan": "Asia", "Lebanon": "Asia",
    "Malaysia": "Asia", "Nepal": "Asia", "North Korea": "Asia",
    "Oman": "Asia", "Pakistan": "Asia", "Palestine": "Asia",
    "Philippines": "Asia", "Qatar": "Asia", "Saudi Arabia": "Asia",
    "Singapore": "Asia", "South Korea": "Asia", "Sri Lanka": "Asia",
    "Syria": "Asia", "Tajikistan": "Asia", "Thailand": "Asia",
    "Turkmenistan": "Asia", "United Arab Emirates": "Asia",
    "Uzbekistan": "Asia", "Vietnam": "Asia",
}

CONTINENT_COUNTRY_ALIASES = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Côte d'Ivoire": "Ivory Coast",
    "DR Congo": "Democratic Republic of the Congo",
    "Holland": "Netherlands",
    "Kingdom of Denmark": "Denmark",
    "Kingdom of the Netherlands": "Netherlands",
    "People's Republic of China": "China",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
}

NORMALIZED_COUNTRY_TO_CONTINENT = {
    normalize(country): continent
    for country, continent in COUNTRY_TO_CONTINENT.items()
}
NORMALIZED_CONTINENT_COUNTRY_ALIASES = {
    normalize(alias): normalize(country)
    for alias, country in CONTINENT_COUNTRY_ALIASES.items()
}


def player_continent(player):
    nationality = normalize(player.get("nationality", ""))
    canonical = NORMALIZED_CONTINENT_COUNTRY_ALIASES.get(
        nationality, nationality
    )
    return NORMALIZED_COUNTRY_TO_CONTINENT.get(canonical)

CLUB_TO_LEAGUE = {
    "Arsenal": "Premier League", "Liverpool": "Premier League",
    "Manchester United": "Premier League", "Manchester City": "Premier League",
    "Tottenham Hotspur": "Premier League", "Newcastle United": "Premier League",
    "Chelsea": "Premier League", "Sevilla": "La Liga",
    "Atletico Madrid": "La Liga", "Barcelona": "La Liga",
    "Real Madrid": "La Liga", "AC Milan": "Serie A",
    "Inter Milan": "Serie A", "AS Roma": "Serie A", "Napoli": "Serie A",
    "Juventus": "Serie A", "Bayern Munich": "Bundesliga",
    "Borussia Dortmund": "Bundesliga", "Paris Saint-Germain": "Ligue 1",
    "AS Monaco": "Ligue 1", "Galatasaray": "Süper Lig",
    "Fenerbahçe": "Süper Lig", "Beşiktaş": "Süper Lig",
    "Trabzonspor": "Süper Lig", "Ajax": "Eredivisie",
    "Benfica": "Primeira Liga", "Sporting CP": "Primeira Liga",
}

# League criteria cover career clubs beyond the smaller club-criterion pool.
# These aliases are league-specific, so existing club criteria remain unchanged.
LEAGUE_CLUB_ALIASES = HISTORICAL_LEAGUE_CLUB_ALIASES
for league_name, league_clubs in LEAGUE_CLUB_ALIASES.items():
    for canonical_club in league_clubs:
        CLUB_TO_LEAGUE.setdefault(canonical_club, league_name)


def player_position_groups(player):
    positions = player.get("positions", [])
    if isinstance(positions, str):
        positions = [positions]
    normalized = {normalize(position) for position in positions if position}
    return {
        group for group, aliases in POSITION_GROUPS.items()
        if normalized & aliases
    }


def player_birth_decade(player):
    value = str(player.get("birthDate", "")).strip()
    match = re.match(r"^(19[7-9]\d|200\d)(?:\D|$)", value)
    if not match:
        return None
    year = int(match.group(1))
    return f"Born in the {(year // 10) * 10}s"


def player_leagues(player):
    club_values = {normalize(name) for name in get_club_names(player)}
    leagues = set()
    for club, league in CLUB_TO_LEAGUE.items():
        canonical = normalize(club)
        accepted = set(CLUB_ACCEPTED_VALUES.get(canonical, {canonical}))
        accepted.update(
            normalize(alias)
            for alias in LEAGUE_CLUB_ALIASES.get(league, {}).get(club, [])
        )
        if club_values & accepted:
            leagues.add(league)
    return leagues


# ==================================================
# KRİTER KONTROL
# ==================================================

def matches_condition(
    player,
    condition
):

    condition_type = condition[
        "type"
    ]

    value = condition[
        "value"
    ]


    if condition_type == "club":

        return matches_club(
            player,
            value
        )


    if condition_type == "nationality":

        return matches_nationality(
            player,
            value
        )


    if condition_type == "trophy":

        return matches_trophy(
            player,
            value
        )

    if condition_type == "position":
        return value in player_position_groups(player)

    if condition_type == "league":
        return value in player_leagues(player)

    if condition_type == "birth_decade":
        return value == player_birth_decade(player)

    if condition_type == "continent":
        return value == player_continent(player)


    return False


# ==================================================
# 52 KRİTER
# ==================================================

ALL_CONDITIONS = [

    # ==================================================
    # İNGİLTERE
    # ==================================================

    {
        "label": "ARSENAL",
        "type": "club",
        "value": "Arsenal",
        "image": "/static/clubs/arsenal.png"
    },

    {
        "label": "LIVERPOOL",
        "type": "club",
        "value": "Liverpool",
        "image": "/static/clubs/liverpool.png"
    },

    {
        "label": "MAN UNITED",
        "type": "club",
        "value": "Manchester United",
        "image": "/static/clubs/man_united.png"
    },

    {
        "label": "MAN CITY",
        "type": "club",
        "value": "Manchester City",
        "image": "/static/clubs/man_city.png"
    },

    {
        "label": "TOTTENHAM",
        "type": "club",
        "value": "Tottenham Hotspur",
        "image": "/static/clubs/tottenham.png"
    },

    {
        "label": "NEWCASTLE",
        "type": "club",
        "value": "Newcastle United",
        "image": "/static/clubs/newcastle.png"
    },

    {
        "label": "CHELSEA",
        "type": "club",
        "value": "Chelsea",
        "image": "/static/clubs/chelsea.png"
    },


    # ==================================================
    # İSPANYA
    # ==================================================

    {
        "label": "SEVILLA",
        "type": "club",
        "value": "Sevilla",
        "image": "/static/clubs/sevilla.png"
    },

    {
        "label": "ATLETICO MADRID",
        "type": "club",
        "value": "Atletico Madrid",
        "image": "/static/clubs/atletico_madrid.png"
    },

    {
        "label": "BARCELONA",
        "type": "club",
        "value": "Barcelona",
        "image": "/static/clubs/barcelona.png"
    },

    {
        "label": "REAL MADRID",
        "type": "club",
        "value": "Real Madrid",
        "image": "/static/clubs/real_madrid.png"
    },


    # ==================================================
    # İTALYA
    # ==================================================

    {
        "label": "AC MILAN",
        "type": "club",
        "value": "AC Milan",
        "image": "/static/clubs/ac_milan.png"
    },

    {
        "label": "INTER",
        "type": "club",
        "value": "Inter Milan",
        "image": "/static/clubs/inter.png"
    },

    {
        "label": "ROMA",
        "type": "club",
        "value": "AS Roma",
        "image": "/static/clubs/roma.png"
    },

    {
        "label": "NAPOLI",
        "type": "club",
        "value": "Napoli",
        "image": "/static/clubs/napoli.png"
    },

    {
        "label": "JUVENTUS",
        "type": "club",
        "value": "Juventus",
        "image": "/static/clubs/juventus.png"
    },


    # ==================================================
    # FRANSA
    # ==================================================

    {
        "label": "PSG",
        "type": "club",
        "value": "Paris Saint-Germain",
        "image": "/static/clubs/paris.png"
    },

    {
        "label": "MONACO",
        "type": "club",
        "value": "AS Monaco",
        "image": "/static/clubs/monaco.png"
    },


    # ==================================================
    # ALMANYA
    # ==================================================

    {
        "label": "BAYERN",
        "type": "club",
        "value": "Bayern Munich",
        "image": "/static/clubs/bayern.png"
    },

    {
        "label": "DORTMUND",
        "type": "club",
        "value": "Borussia Dortmund",
        "image": "/static/clubs/dortmund.png"
    },


    # ==================================================
    # PORTEKİZ
    # ==================================================

    {
        "label": "BENFICA",
        "type": "club",
        "value": "Benfica",
        "image": "/static/clubs/benfica.png"
    },

    {
        "label": "SPORTING",
        "type": "club",
        "value": "Sporting CP",
        "image": "/static/clubs/sporting.png"
    },


    # ==================================================
    # HOLLANDA
    # ==================================================

    {
        "label": "AJAX",
        "type": "club",
        "value": "Ajax",
        "image": "/static/clubs/ajax.png"
    },


    # ==================================================
    # TÜRKİYE
    # ==================================================

    {
        "label": "GALATASARAY",
        "type": "club",
        "value": "Galatasaray",
        "image": "/static/clubs/galatasaray.png"
    },

    {
        "label": "FENERBAHCE",
        "type": "club",
        "value": "Fenerbahçe",
        "image": "/static/clubs/fenerbahce.png"
    },

    {
        "label": "BESIKTAS",
        "type": "club",
        "value": "Beşiktaş",
        "image": "/static/clubs/besiktas.png"
    },

    {
        "label": "TRABZONSPOR",
        "type": "club",
        "value": "Trabzonspor",
        "image": "/static/clubs/trabzonspor.png"
    },


    # ==================================================
    # ÜLKELER
    # ==================================================

    {
        "label": "ENGLAND",
        "type": "nationality",
        "value": "England",
        "image": "/static/flags/england.png"
    },

    {
        "label": "SPAIN",
        "type": "nationality",
        "value": "Spain",
        "image": "/static/flags/spain.png"
    },

    {
        "label": "PORTUGAL",
        "type": "nationality",
        "value": "Portugal",
        "image": "/static/flags/portugal.png"
    },

    {
        "label": "NETHERLANDS",
        "type": "nationality",
        "value": "Netherlands",
        "image": "/static/flags/netherlands.png"
    },

    {
        "label": "ITALY",
        "type": "nationality",
        "value": "Italy",
        "image": "/static/flags/italy.png"
    },

    {
        "label": "FRANCE",
        "type": "nationality",
        "value": "France",
        "image": "/static/flags/france.png"
    },

    {
        "label": "GERMANY",
        "type": "nationality",
        "value": "Germany",
        "image": "/static/flags/germany.png"
    },

    {
        "label": "TURKEY",
        "type": "nationality",
        "value": "Turkey",
        "image": "/static/flags/turkey.png"
    },

    {
        "label": "BRAZIL",
        "type": "nationality",
        "value": "Brazil",
        "image": "/static/flags/brazil.png"
    },

    {
        "label": "ARGENTINA",
        "type": "nationality",
        "value": "Argentina",
        "image": "/static/flags/argentina.png"
    },


    # ==================================================
    # LİGLER
    # ==================================================

    {
        "label": "PREMIER LEAGUE ŞAMPİYONU",
        "type": "trophy",
        "value": "english champion",
        "image": "/static/trophies/premier_league.png"
    },

    {
        "label": "SÜPER LİG ŞAMPİYONU",
        "type": "trophy",
        "value": "turkish champion",
        "image": "/static/trophies/super_lig.png"
    },

    {
        "label": "LA LIGA ŞAMPİYONU",
        "type": "trophy",
        "value": "spanish champion",
        "image": "/static/trophies/la_liga.png"
    },

    {
        "label": "SERIE A ŞAMPİYONU",
        "type": "trophy",
        "value": "italian champion",
        "image": "/static/trophies/serie_a.png"
    },

    {
        "label": "BUNDESLIGA ŞAMPİYONU",
        "type": "trophy",
        "value": "german champion",
        "image": "/static/trophies/bundesliga.png"
    },

    {
        "label": "LIGUE 1 ŞAMPİYONU",
        "type": "trophy",
        "value": "french champion",
        "image": "/static/trophies/ligue_1.png"
    },


    # ==================================================
    # AVRUPA KUPALARI
    # ==================================================

    {
        "label": "CHAMPIONS LEAGUE ŞAMPİYONU",
        "type": "trophy",
        "value": "champions league",
        "image": "/static/trophies/champions_league.png"
    },

    {
        "label": "EUROPA LEAGUE ŞAMPİYONU",
        "type": "trophy",
        "value": "europa league",
        "image": "/static/trophies/europa_league.png"
    },


    # ==================================================
    # MİLLİ TAKIM KUPALARI
    # ==================================================

    {
        "label": "DÜNYA KUPASI ŞAMPİYONU",
        "type": "trophy",
        "value": "world cup",
        "image": "/static/trophies/world_cup.png"
    },

    {
        "label": "AVRUPA ŞAMPİYONU",
        "type": "trophy",
        "value": "european championship",
        "image": "/static/trophies/euro.png"
    },

    {
        "label": "COPA AMERICA ŞAMPİYONU",
        "type": "trophy",
        "value": "copa america",
        "image": "/static/trophies/copa_america.png"
    },


    # ==================================================
    # BİREYSEL
    # ==================================================

    {
        "label": "BALLON D'OR SAHİBİ",
        "type": "trophy",
        "value": "ballon dor",
        "image": "/static/trophies/ballon_dor.png"
    },


    # ==================================================
    # YEREL KUPALAR
    # ==================================================

    {
        "label": "FA CUP ŞAMPİYONU",
        "type": "trophy",
        "value": "fa cup",
        "image": "/static/trophies/fa_cup.png"
    },

    {
        "label": "COPPA ITALIA ŞAMPİYONU",
        "type": "trophy",
        "value": "coppa italia",
        "image": "/static/trophies/coppa_italia.png"
    },

    {
        "label": "COPA DEL REY ŞAMPİYONU",
        "type": "trophy",
        "value": "copa del rey",
        "image": "/static/trophies/copa_del_rey.png"
    }

]

ALL_CONDITIONS.extend([
    {"label": "GOALKEEPER", "type": "position", "value": "Goalkeeper", "image": ""},
    {"label": "DEFENDER", "type": "position", "value": "Defender", "image": ""},
    {"label": "MIDFIELDER", "type": "position", "value": "Midfielder", "image": ""},
    {"label": "FORWARD", "type": "position", "value": "Forward", "image": ""},
    {"label": "PREMIER LEAGUE", "type": "league", "value": "Premier League", "image": ""},
    {"label": "LA LIGA", "type": "league", "value": "La Liga", "image": ""},
    {"label": "SERIE A", "type": "league", "value": "Serie A", "image": ""},
    {"label": "BUNDESLIGA", "type": "league", "value": "Bundesliga", "image": ""},
    {"label": "SÜPER LİG", "type": "league", "value": "Süper Lig", "image": ""},
    {"label": "BORN IN THE 1980s", "type": "birth_decade", "value": "Born in the 1980s", "image": ""},
    {"label": "BORN IN THE 1990s", "type": "birth_decade", "value": "Born in the 1990s", "image": ""},
    {"label": "BORN IN THE 2000s", "type": "birth_decade", "value": "Born in the 2000s", "image": ""},
    {"label": "EUROPE", "type": "continent", "value": "Europe", "image": ""},
    {"label": "SOUTH AMERICA", "type": "continent", "value": "South America", "image": ""},
    {"label": "AFRICA", "type": "continent", "value": "Africa", "image": ""},
    {"label": "ASIA", "type": "continent", "value": "Asia", "image": ""},
])


def build_accepted_value_map(aliases):

    accepted = {}

    for canonical_name, alias_names in aliases.items():

        values = {
            normalize(canonical_name),
            *(normalize(name) for name in alias_names)
        }

        for value in values:
            accepted[value] = values

    return accepted


CLUB_ACCEPTED_VALUES = build_accepted_value_map(
    CLUB_ALIASES
)

COUNTRY_ACCEPTED_VALUES = build_accepted_value_map(
    COUNTRY_ALIASES
)

TROPHY_ACCEPTED_VALUES = build_accepted_value_map(
    TROPHY_ALIASES
)


def index_player_condition_keys(player):

    club_values = {
        normalize(name)
        for name in get_club_names(player)
    }

    nationality_value = normalize(
        player.get("nationality", "")
    )

    trophy_values = {
        clean_trophy_name(name)
        for name in get_trophy_names(player)
    }
    position_values = player_position_groups(player)
    league_values = player_leagues(player)
    birth_decade = player_birth_decade(player)
    continent = player_continent(player)

    matched = set()

    for condition in ALL_CONDITIONS:

        condition_type = condition["type"]
        target = normalize(condition["value"])

        if condition_type == "club":
            accepted = CLUB_ACCEPTED_VALUES.get(
                target,
                {target}
            )
            is_match = bool(club_values & accepted)
        elif condition_type == "nationality":
            accepted = COUNTRY_ACCEPTED_VALUES.get(
                target,
                {target}
            )
            is_match = nationality_value in accepted
        elif condition_type == "trophy":
            accepted = TROPHY_ACCEPTED_VALUES.get(
                target,
                {target}
            )
            is_match = bool(trophy_values & accepted)
        elif condition_type == "position":
            is_match = condition["value"] in position_values
        elif condition_type == "league":
            is_match = condition["value"] in league_values
        elif condition_type == "birth_decade":
            is_match = condition["value"] == birth_decade
        elif condition_type == "continent":
            is_match = condition["value"] == continent
        else:
            is_match = False

        if is_match:
            matched.add((condition_type, condition["value"]))

    return matched


print(
    "Toplam kriter:",
    len(ALL_CONDITIONS)
)


# ==================================================
# 31 PETEK
# ==================================================

conditions = [None] * 31


# ==================================================
# BOARD
# ==================================================

rows = [

    [0, 1, 2, 3],

    [4, 5, 6, 7, 8],

    [9, 10, 11, 12],

    [13, 14, 15, 16, 17],

    [18, 19, 20, 21],

    [22, 23, 24, 25, 26],

    [27, 28, 29, 30]

]


row_x_positions = [

    [-3, -1, 1, 3],

    [-4, -2, 0, 2, 4],

    [-3, -1, 1, 3],

    [-4, -2, 0, 2, 4],

    [-3, -1, 1, 3],

    [-4, -2, 0, 2, 4],

    [-3, -1, 1, 3]

]


# ==================================================
# KOMŞULAR
# ==================================================

def build_neighbors():

    positions = {}


    for row_index, row in enumerate(
        rows
    ):

        for item, x in zip(
            row,
            row_x_positions[
                row_index
            ]
        ):

            positions[
                item
            ] = (
                row_index,
                x
            )


    result = {

        index: []

        for index in range(
            len(conditions)
        )

    }


    for first, first_position in positions.items():

        row_a, x_a = (
            first_position
        )


        for second, second_position in positions.items():

            if first == second:

                continue


            row_b, x_b = (
                second_position
            )


            row_diff = abs(
                row_a - row_b
            )


            x_diff = abs(
                x_a - x_b
            )


            same_row = (
                row_diff == 0
                and
                x_diff == 2
            )


            diagonal = (
                row_diff == 1
                and
                x_diff == 1
            )


            if (
                same_row
                or
                diagonal
            ):

                result[
                    first
                ].append(
                    second
                )


    return result


neighbors = build_neighbors()


criterion_engine = CriterionEngine(
    players,
    ALL_CONDITIONS,
    neighbors,
    matches_condition,
    player_key_resolver=index_player_condition_keys
)

# Tiki Taka Toe uses its own immutable indexes and never mutates Possession's
# criterion engine or player database.
tiki_engine = TikiTakaEngine(
    players,
    CLUB_ALIASES,
    COUNTRY_ALIASES,
    TROPHY_ALIASES,
)
TIKI_CRITERION_IMAGES = {
    (condition["type"], tiki_engine._canonical(condition["type"], condition["value"])):
        condition["image"]
    for condition in ALL_CONDITIONS
    if condition["type"] in {"club", "nationality", "trophy"} and condition["image"]
}
tiki_local_games = {}
tiki_local_games_lock = threading.Lock()
tiki_rooms = {}
tiki_rooms_lock = threading.Lock()
matchmaking_queues = {"possession": [], "tiki_taka_toe": []}
matchmaking_lock = threading.Lock()

TIKI_WIN_LINES = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
)
TIKI_TURN_SECONDS = 30


def create_tiki_state(board, starting_player=1, started=True, player_names=None):
    now = time.time()
    return {
        "rows": board["rows"], "columns": board["columns"],
        "board": [None] * 9, "used_players": set(),
        "active_player": starting_player, "started": started,
        "turn_deadline": now + TIKI_TURN_SECONDS if started else None,
        "finished": False, "winner": None, "end_reason": "",
        "created_at": now, "stats_recorded": False,
        "player_names": dict(player_names or {"1": "Oyuncu 1", "2": "Oyuncu 2"}),
    }


def expire_tiki_turn(state, now=None):
    """Advance elapsed turns without allowing a late answer to claim a cell."""
    if not state["started"] or state["finished"] or state.get("turn_deadline") is None:
        return False
    now = time.time() if now is None else now
    deadline = state["turn_deadline"]
    if now < deadline:
        return False
    elapsed_turns = int((now - deadline) // TIKI_TURN_SECONDS) + 1
    if elapsed_turns % 2:
        state["active_player"] = 2 if state["active_player"] == 1 else 1
    state["turn_deadline"] = deadline + elapsed_turns * TIKI_TURN_SECONDS
    return True


def serialize_tiki_state(state):
    def public_criterion(item):
        result = tiki_engine.public_criterion(item)
        result["image"] = TIKI_CRITERION_IMAGES.get((item["type"], item["key"]), "")
        return result

    public_state = {
        "rows": [public_criterion(item) for item in state["rows"]],
        "columns": [public_criterion(item) for item in state["columns"]],
        "board": list(state["board"]),
        "active_player": state["active_player"], "started": state["started"],
        "turn_deadline": state.get("turn_deadline"),
        "turn_remaining_ms": max(0, int((state["turn_deadline"] - time.time()) * 1000))
        if state.get("turn_deadline") is not None and state["started"] and not state["finished"]
        else 0,
        "finished": state["finished"], "winner": state["winner"],
        "end_reason": state["end_reason"],
        "player_names": dict(state.get("player_names", {"1": "Oyuncu 1", "2": "Oyuncu 2"})),
    }
    ad_break = public_ad_break(state)
    if ad_break:
        public_state["ad_break"] = ad_break
    return public_state


def tiki_winner(board):
    for first, second, third in TIKI_WIN_LINES:
        owners = [board[index]["owner"] if board[index] else None
                  for index in (first, second, third)]
        if owners[0] and owners.count(owners[0]) == 3:
            return owners[0]
    return None


def apply_tiki_move(state, cell_index, player_id, player_number):
    if not state["started"]:
        return {"accepted": False, "message": "Maç henüz başlamadı."}
    if state["finished"]:
        return {"accepted": False, "message": "Maç sona erdi."}
    if expire_tiki_turn(state):
        return {"accepted": False, "message": "Süre doldu. Sıra diğer oyuncuya geçti."}
    if state["active_player"] != player_number:
        return {"accepted": False, "message": "Sıra sende değil."}
    if not 0 <= cell_index < 9:
        return {"accepted": False, "message": "Geçersiz hücre."}
    if state["board"][cell_index] is not None:
        return {"accepted": False, "message": "Bu hücre zaten alındı."}
    player_id = str(player_id).strip()
    player = tiki_engine.players_by_id.get(player_id)
    if not player:
        return {"accepted": False, "message": "Futbolcuyu listeden seç."}
    if player_id in state["used_players"]:
        return {"accepted": False, "message": "Bu futbolcu bu maçta kullanıldı."}

    row, column = divmod(cell_index, 3)
    correct = tiki_engine.player_matches(
        player_id, state["rows"][row], state["columns"][column]
    )
    if correct:
        state["board"][cell_index] = {
            "owner": player_number, "player_id": player_id,
            "player_name": player["name"],
        }
        state["used_players"].add(player_id)
        winner = tiki_winner(state["board"])
        if winner:
            state.update(finished=True, winner=winner,
                         end_reason=f"Oyuncu {winner} üçlü çizgiyi tamamladı.")
            mark_match_outcome(state, "tiki_taka_toe", "completed_win")
        elif all(state["board"]):
            state.update(finished=True, winner=0, end_reason="BERABERE")
            mark_match_outcome(state, "tiki_taka_toe", "completed_draw")
    if not state["finished"]:
        state["active_player"] = 2 if player_number == 1 else 1
        state["turn_deadline"] = time.time() + TIKI_TURN_SECONDS
    return {
        "accepted": True, "correct": correct,
        "message": "Doğru cevap!" if correct else "Bu futbolcu iki kriteri birlikte karşılamıyor.",
        "player": player["name"] if correct else None,
    }


def record_tiki_results(match_id, state, user_ids):
    if state.get("stats_recorded"):
        return
    duration = max(0, int(time.time() - state.get("created_at", time.time())))
    for number, user_id in user_ids.items():
        if state["winner"] == 0:
            result = "draw"
        else:
            result = "win" if state["winner"] == number else "loss"
        correct = sum(1 for cell in state["board"] if cell and cell["owner"] == number)
        profile_store.record_result(
            match_id, user_id, "tiki_taka_toe", result,
            correct_answers=correct, play_seconds=duration,
            fastest_win_seconds=duration if result == "win" else None,
        )
    state["stats_recorded"] = True


def record_possession_results(room_code, room):
    state = room["state"]
    if state.get("stats_recorded"):
        return
    duration = max(0, int(time.time() - state.get("created_at", time.time())))
    for number, user_id in room.get("user_ids", {}).items():
        if not user_id:
            continue
        if state["winner"] in (None, 0):
            result = "draw"
        else:
            result = "win" if state["winner"] == number else "loss"
        profile_store.record_result(
            room.get("match_id", room_code), user_id, "possession", result,
            captures=state["owners"].count(number),
            steals=state.get("steals", {}).get(str(number), 0),
            play_seconds=duration,
        )
    state["stats_recorded"] = True


conditions, initial_board_analysis = (
    criterion_engine.generate_board()
)


# ==================================================
# HEATMAP BOARD
# ==================================================

HEATMAP_SCORE_INDEX = 15
heatmap_games = {}
heatmap_games_lock = threading.Lock()
heatmap_board_pool = []


def generate_heatmap_board(seed=None):
    """Create 30 unique criterion cells plus one non-playable center cell."""
    for attempt in range(20):
        attempt_seed = (
            None if seed is None else seed + attempt * 1000003
        )
        board, _ = criterion_engine.generate_board(seed=attempt_seed)
        cells = [dict(condition) for condition in board]
        cells[HEATMAP_SCORE_INDEX] = {
            "type": "score",
            "value": None,
            "label": "PUAN",
            "image": ""
        }
        if analyze_heatmap_board(cells)["isolated_cells"] == 0:
            return cells
    raise RuntimeError("No connected Heatmap board could be generated")


def create_heatmap_game(seed=None, user_id=None):
    token = uuid.uuid4().hex
    if seed is None and heatmap_board_pool:
        cells = [dict(cell) for cell in random.choice(heatmap_board_pool)]
    else:
        cells = generate_heatmap_board(seed=seed)
    prune_local_game_store(heatmap_games, reserve=1)
    heatmap_games[token] = {
        "cells": cells,
        "heated": {},
        "score": 0,
        "moves": 0,
        "correct_answers": 0,
        "wrong_answers": 0,
        "user_id": user_id,
        "created_at": time.time(),
        "stats_recorded": False,
        "finished": False,
    }
    return token, heatmap_games[token]


def analyze_heatmap_board(cells):
    criterion_indexes = {
        index for index, cell in enumerate(cells)
        if cell["type"] != "score"
    }
    keys = {
        index: criterion_engine._key(cells[index])
        for index in criterion_indexes
    }
    edges = {
        tuple(sorted((index, neighbor)))
        for index in criterion_indexes
        for neighbor in neighbors[index]
        if neighbor in criterion_indexes
    }
    playable = strong = dead = 0
    playable_neighbors = {index: 0 for index in criterion_indexes}
    for first, second in edges:
        total, popular, medium, _ = criterion_engine._pair_stats(
            keys[first], keys[second]
        )
        recognizable = popular + medium
        is_playable = recognizable >= 2
        playable += is_playable
        strong += recognizable >= 5
        dead += total == 0
        if is_playable:
            playable_neighbors[first] += 1
            playable_neighbors[second] += 1

    regions = {2: 0, 3: 0, 4: 0}
    for center in criterion_indexes:
        direct = [
            item for item in neighbors[center]
            if item in criterion_indexes
        ]
        center_answers = criterion_engine.answer_sets[keys[center]]
        for size in regions:
            for adjacent in combinations(direct, size - 1):
                common = set(center_answers)
                for item in adjacent:
                    common &= criterion_engine.answer_sets[keys[item]]
                regions[size] += bool(common)

    return {
        "edge_count": len(edges),
        "playable_edge_ratio": playable / max(1, len(edges)),
        "strong_edge_ratio": strong / max(1, len(edges)),
        "dead_edges": dead,
        "isolated_cells": sum(value == 0 for value in playable_neighbors.values()),
        "regions": regions,
    }


def load_heatmap_board_pool():
    """Load prevalidated boards so page requests never run the heavy generator."""
    try:
        with open(HEATMAP_BOARDS_FILE, "r", encoding="utf-8") as source:
            candidates = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Hazır Isı Haritası havuzu okunamadı: {exc}")
        return [generate_heatmap_board(seed=2026100401)]

    valid = []
    for board in candidates:
        if not isinstance(board, list) or len(board) != 31:
            continue
        if board[HEATMAP_SCORE_INDEX].get("type") != "score":
            continue
        try:
            analysis = analyze_heatmap_board(board)
        except (KeyError, TypeError):
            continue
        if analysis["isolated_cells"] == 0:
            valid.append(tuple(dict(cell) for cell in board))
    if not valid:
        raise RuntimeError("Geçerli hazır Isı Haritası tahtası bulunamadı.")
    print(f"Hazır Isı Haritası havuzu yüklendi: {len(valid)} tahta")
    return valid


heatmap_board_pool.extend(load_heatmap_board_pool())


# ==================================================
# ONLINE ODALAR
# ==================================================

online_rooms = {}

online_rooms_lock = threading.Lock()

# Presence is deliberately transient: a user may have several open tabs.
online_user_sids = {}
socket_identities = {}
presence_lock = threading.Lock()
game_invites = {}
game_invites_lock = threading.Lock()
INVITE_TTL_SECONDS = 120


def socket_current_user():
    socket_id = getattr(request, "sid", None)
    with presence_lock:
        authenticated = socket_identities.get(socket_id)
    return authenticated or current_user()


def socket_user_id():
    user = socket_current_user()
    return user["id"] if user else None


def account_identity():
    user = socket_current_user()
    if not user:
        return None
    return {"user_id": user["id"], "username": user["username"]}


def remove_from_matchmaking(socket_id):
    removed_modes = []
    with matchmaking_lock:
        for mode, queue in matchmaking_queues.items():
            original_size = len(queue)
            queue[:] = [entry for entry in queue if entry["sid"] != socket_id]
            if len(queue) != original_size:
                removed_modes.append(mode)
    return removed_modes


def user_room(user_id):
    return f"user:{user_id}"


def is_user_online(user_id):
    with presence_lock:
        return bool(online_user_sids.get(user_id))


def notify_friend_presence(user_id, status):
    for friend in friend_store.get_friends(user_id):
        socketio.emit("friend_presence", {"user_id": user_id, "status": status}, to=user_room(friend["id"]))


def create_invite_possession_room(sender_id, receiver_id):
    """Create the existing Possession room shape; clients still join via join_game_room."""
    with online_rooms_lock:
        room_code = generate_room_code()
        room_conditions, _ = criterion_engine.generate_board()
        online_rooms[room_code] = {
            "players": {}, "state": create_match_state(), "conditions": room_conditions,
            "rematch_ready": {1: False, 2: False}, "match_number": 1,
            "starting_player": 1, "timer_generation": 0,
            "user_ids": {1: None, 2: None}, "match_id": uuid.uuid4().hex,
            "reserved_user_ids": {sender_id, receiver_id},
        }
    return room_code

ONLINE_START_TIME = 4 * 60


def create_match_state(
    starting_player=1
):

    return {

        "owners": [0] * len(conditions),

        "active_player": starting_player,

        "scores": {
            "1": 0,
            "2": 0
        },

        "times": {
            "1": ONLINE_START_TIME,
            "2": ONLINE_START_TIME
        },

        "started": False,

        "finished": False,

        "winner": None,

        "end_reason": "",

        "created_at": time.time(),

        "stats_recorded": False,

        "steals": {"1": 0, "2": 0}

    }


def serialize_room_state(
    room,
    include_conditions=False
):

    state = room[
        "state"
    ]


    public_state = {

        "owners": list(
            state["owners"]
        ),

        "active_player":
            state["active_player"],

        "scores": dict(
            state["scores"]
        ),

        "times": dict(
            state["times"]
        ),

        "remaining_times": dict(
            state["times"]
        ),

        "started":
            state["started"],

        "finished":
            state["finished"],

        "winner":
            state["winner"],

        "end_reason":
            state["end_reason"],

        "player_names": dict(
            room.get("player_names", {1: "Oyuncu 1", 2: "Oyuncu 2"})
        )

    }

    latest_answer = room.get("latest_answer")
    if latest_answer and latest_answer.get("expires_at_ms", 0) > int(time.time() * 1000):
        public_state["latest_answer"] = dict(latest_answer)

    ad_break = public_ad_break(state)
    if ad_break:
        public_state["ad_break"] = ad_break


    if include_conditions:

        public_state["conditions"] = room[
            "conditions"
        ]


    return public_state


def calculate_room_scores(
    state
):

    state["scores"] = {

        "1": state["owners"].count(1),

        "2": state["owners"].count(2)

    }


def finish_room_game(
    state,
    winner,
    reason,
    outcome="completed_board"
):

    state["finished"] = True

    state["winner"] = winner

    state["end_reason"] = reason
    mark_match_outcome(state, "possession", outcome)


def run_room_timer(
    room_code,
    timer_generation
):

    while True:

        socketio.sleep(1)


        with online_rooms_lock:

            room = online_rooms.get(
                room_code
            )


            if not room:

                return


            if room["timer_generation"] != timer_generation:

                return


            state = room[
                "state"
            ]


            if (
                not state["started"]
                or
                state["finished"]
            ):

                return


            active_key = str(
                state["active_player"]
            )


            state["times"][
                active_key
            ] = max(
                0,
                state["times"][active_key] - 1
            )


            if state["times"][active_key] == 0:

                winner = (
                    2
                    if state["active_player"] == 1
                    else 1
                )


                finish_room_game(
                    state,
                    winner,
                    "Rakibin süresi bitti.",
                    "completed_timeout"
                )

                record_possession_results(room_code, room)


            public_state = serialize_room_state(
                room
            )


        socketio.emit(
            "game_state",
            public_state,
            to=room_code
        )


        if public_state["finished"]:

            return


def generate_room_code():

    while True:

        code = "".join(
            random.choices(
                string.ascii_uppercase
                +
                string.digits,
                k=6
            )
        )


        if code not in online_rooms:

            return code


def find_socket_room(
    socket_id
):

    for room_code, room in online_rooms.items():

        if socket_id in room[
            "players"
        ]:

            return room_code


    return None


def get_socket_player_number(
    room_code,
    socket_id
):

    room = online_rooms.get(
        room_code
    )


    if not room:

        return None


    return room[
        "players"
    ].get(
        socket_id
    )


def remove_socket_from_room(
    socket_id
):

    with online_rooms_lock:

        room_code = find_socket_room(
            socket_id
        )


        if not room_code:

            return None


        room = online_rooms[
            room_code
        ]


        player_number = room[
            "players"
        ].pop(
            socket_id,
            None
        )


        if not room[
            "players"
        ]:

            del online_rooms[
                room_code
            ]

            return {
                "room_code": room_code,
                "player_number": player_number,
                "match_finished": False,
                "state": None
            }


        state = room[
            "state"
        ]

        match_was_already_finished = bool(state.get("finished"))


        room["rematch_ready"] = {
            1: False,
            2: False
        }


        match_finished = (
            state["started"]
            and
            not state["finished"]
        )


        if match_finished:

            remaining_player = next(
                iter(room["players"].values())
            )


            finish_room_game(
                state,
                remaining_player,
                (
                    "Rakibin bağlantısı kesildi. "
                    "Maçı hükmen kazandın."
                ),
                "abandoned_disconnect"
            )

            record_possession_results(room_code, room)


        public_state = serialize_room_state(
            room
        )


        return {
            "room_code": room_code,
            "player_number": player_number,
            "match_finished": match_finished,
            "match_was_already_finished": match_was_already_finished,
            "winner": public_state["winner"],
            "state": public_state
        }


def notify_remaining_player(
    result,
    message
):

    room_code = result[
        "room_code"
    ]


    if result.get("state"):

        socketio.emit(
            "game_state",
            result["state"],
            to=room_code
        )


    socketio.emit(
        "opponent_left",
        {
            "message": message,
            "reason": "disconnect",
            "match_finished": result.get(
                "match_finished",
                False
            ),
            "match_was_already_finished": result.get(
                "match_was_already_finished",
                False
            ),
            "winner": result.get("winner")
        },
        to=room_code
    )


# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():
    if not current_user():
        return redirect(url_for("login"))
    return render_template(
        "home.html"
    )


@app.get("/healthz")
def healthz():
    """Lightweight health check used by the production host."""
    return jsonify({"status": "ok"})


@app.get("/privacy")
def privacy_policy():
    return render_template(
        "legal.html", page="privacy", support_email=SUPPORT_EMAIL,
    )


@app.get("/terms")
def terms_of_use():
    return render_template(
        "legal.html", page="terms", support_email=SUPPORT_EMAIL,
    )


@app.get("/support")
def support_page():
    return render_template(
        "legal.html", page="support", support_email=SUPPORT_EMAIL,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("home"))
    error = ""
    if request.method == "POST":
        if not valid_csrf():
            abort(400, "Geçersiz güvenlik anahtarı.")
        try:
            user = profile_store.create_user(
                request.form.get("username", ""), request.form.get("password", ""),
                request.form.get("avatar", "captain"),
            )
            session.clear(); session.permanent = True
            session["user_id"] = user["id"]; csrf_token()
            return redirect(url_for("home"))
        except ValueError as exc:
            error = str(exc)
    return render_template("auth.html", mode="register", error=error, avatars=AVATARS)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("home"))
    error = ""
    if request.method == "POST":
        if not valid_csrf():
            abort(400, "Geçersiz güvenlik anahtarı.")
        user = profile_store.authenticate(
            request.form.get("identity", ""), request.form.get("password", "")
        )
        if user:
            session.clear(); session.permanent = True
            session["user_id"] = user["id"]; csrf_token()
            return redirect(url_for("home"))
        error = "Kullanıcı bilgileri hatalı."
    return render_template("auth.html", mode="login", error=error, avatars=AVATARS)


@app.post("/logout")
def logout():
    if not valid_csrf():
        abort(400, "Geçersiz güvenlik anahtarı.")
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    return render_template("profile.html", profile=profile_store.profile(user["id"]), avatars=AVATARS)


@app.route("/leaderboard")
def leaderboard():
    mode = str(request.args.get("mode", "overall"))
    try:
        board = profile_store.leaderboard(mode, request.args.get("page", 1))
    except ValueError:
        abort(400, "Geçersiz liderlik modu.")
    return render_template(
        "leaderboard.html", board=board,
        current_user_id=session.get("user_id"),
    )


@app.route("/player/<user_id>")
def public_player_profile(user_id):
    public = profile_store.public_profile(user_id)
    if not public:
        return render_template("public_profile.html", profile=None), 404
    viewer = current_user()
    return render_template(
        "public_profile.html", profile=public,
        is_self=session.get("user_id") == user_id,
        friendship_status=friend_store.get_friendship_status(viewer["id"], user_id) if viewer and viewer["id"] != user_id else "none",
        is_online=is_user_online(user_id),
    )


@app.get("/api/leaderboard")
def leaderboard_api():
    mode = str(request.args.get("mode", "overall"))
    try:
        board = profile_store.leaderboard(mode, request.args.get("page", 1))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    board["entries"] = [
        {key: value for key, value in entry.items()
         if key not in {"password_hash", "last_login_at"}}
        for entry in board["entries"]
    ]
    return jsonify(board)


@app.get("/api/profile")
def profile_api():
    user = current_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    return jsonify(profile_store.profile(user["id"]))


@app.get("/api/mobile/socket-token")
def mobile_socket_token_api():
    """Issue a short-lived signed identity for native Socket.IO handshakes."""
    user = current_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    return jsonify({
        "token": mobile_socket_tokens.dumps({"user_id": user["id"]}),
        "expires_in": MOBILE_SOCKET_TOKEN_MAX_AGE,
    })


@app.post("/api/profile")
def update_profile_api():
    user = current_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    if not valid_csrf():
        return jsonify({"error": "Geçersiz güvenlik anahtarı."}), 400
    data = request.get_json(silent=True) or request.form
    try:
        updated = profile_store.update_profile(
            user["id"], data.get("username", ""), data.get("avatar", user["avatar"]),
        )
        return jsonify({"success": True, "user": updated})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/profile/password")
def change_password_api():
    user = current_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    if not valid_csrf():
        return jsonify({"error": "Geçersiz güvenlik anahtarı."}), 400
    data = request.get_json(silent=True) or request.form
    try:
        profile_store.change_password(
            user["id"], data.get("current_password", ""), data.get("new_password", "")
        )
        return jsonify({"success": True})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/profile/delete")
def delete_profile_api():
    user = current_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    if not valid_csrf():
        return jsonify({"error": "Geçersiz güvenlik anahtarı."}), 400
    data = request.get_json(silent=True) or request.form
    try:
        profile_store.delete_account(user["id"], data.get("current_password", ""))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    session.clear()
    return jsonify({"success": True, "redirect": url_for("login")})


def social_user_or_401():
    user = current_user()
    return user, (jsonify({"error": "Giriş gerekli."}), 401) if not user else None


@app.route("/friends")
def friends():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    return render_template("friends.html")


@app.get("/api/friends")
def friends_api():
    user, error = social_user_or_401()
    if error: return error
    friends = friend_store.get_friends(user["id"])
    for friend in friends:
        friend["presence"] = "online" if is_user_online(friend["id"]) else "offline"
    return jsonify({"friends": friends})


@app.get("/api/friends/requests")
def friend_requests_api():
    user, error = social_user_or_401()
    if error: return error
    return jsonify({"requests": friend_store.get_incoming_friend_requests(user["id"])})


@app.get("/api/users/search")
def users_search_api():
    user, error = social_user_or_401()
    if error: return error
    query = str(request.args.get("q", "")).strip()
    if len(query) < 2: return jsonify({"error": "Arama en az 2 karakter olmalı."}), 400
    return jsonify({"users": friend_store.search_users(user["id"], query)})


def friend_mutation(action, other_id):
    user, error = social_user_or_401()
    if error: return error
    if not valid_csrf(): return jsonify({"error": "Geçersiz güvenlik anahtarı."}), 400
    try:
        getattr(friend_store, action)(user["id"], other_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if action == "send_friend_request":
        socketio.emit("friend_request_received", {"from": {"id": user["id"], "username": user["username"], "avatar": user["avatar"]}}, to=user_room(other_id))
    return jsonify({"success": True})


@app.post("/api/friends/request/<user_id>")
def send_friend_request_api(user_id): return friend_mutation("send_friend_request", user_id)

@app.post("/api/friends/accept/<user_id>")
def accept_friend_request_api(user_id): return friend_mutation("accept_friend_request", user_id)

@app.post("/api/friends/reject/<user_id>")
def reject_friend_request_api(user_id): return friend_mutation("reject_friend_request", user_id)

@app.post("/api/friends/cancel/<user_id>")
def cancel_friend_request_api(user_id): return friend_mutation("cancel_friend_request", user_id)

@app.post("/api/friends/remove/<user_id>")
def remove_friend_api(user_id): return friend_mutation("remove_friend", user_id)


@app.route("/possession")
def possession():

    return render_template(

        "index.html",

        conditions=conditions,

        rows=rows,

        neighbors=neighbors

    )


@app.route("/heatmap")
def heatmap():
    with heatmap_games_lock:
        game_token, game = create_heatmap_game(user_id=session.get("user_id"))

    return render_template(
        "heatmap.html",
        cells=game["cells"],
        rows=rows,
        neighbors=neighbors,
        game_token=game_token,
        score_index=HEATMAP_SCORE_INDEX,
    )


@app.route("/tiki-taka-toe")
def tiki_taka_toe():
    board = tiki_engine.generate_board()
    game_token = uuid.uuid4().hex
    with tiki_local_games_lock:
        prune_local_game_store(tiki_local_games, reserve=1)
        tiki_local_games[game_token] = create_tiki_state(board, started=False)
        tiki_local_games[game_token]["user_id"] = session.get("user_id")
    return render_template(
        "tiki_taka.html", game_token=game_token,
        initial_state=serialize_tiki_state(tiki_local_games[game_token]),
    )


@app.post("/tiki-taka-toe/start")
def tiki_local_start():
    token = str((request.get_json(silent=True) or {}).get("game_token", "")).strip()
    with tiki_local_games_lock:
        state = tiki_local_games.get(token)
        if not state:
            return jsonify({"accepted": False, "message": "Oyun bulunamadı."}), 404
        if not state["started"]:
            state["started"] = True
            state["turn_deadline"] = time.time() + TIKI_TURN_SECONDS
        return jsonify({"accepted": True, "state": serialize_tiki_state(state)})


@app.get("/tiki-taka-toe/state/<token>")
def tiki_local_state(token):
    with tiki_local_games_lock:
        state = tiki_local_games.get(token)
        if not state:
            return jsonify({"accepted": False, "message": "Oyun bulunamadı."}), 404
        expire_tiki_turn(state)
        return jsonify({"accepted": True, "state": serialize_tiki_state(state)})


@app.route("/tiki-taka-toe/move", methods=["POST"])
def tiki_local_move():
    data = request.get_json(silent=True) or {}
    token = str(data.get("game_token", "")).strip()
    try:
        cell_index = int(data.get("index"))
        player_number = int(data.get("player_number"))
    except (TypeError, ValueError):
        return jsonify({"accepted": False, "message": "Geçersiz hamle."}), 400
    if player_number not in (1, 2):
        return jsonify({"accepted": False, "message": "Geçersiz oyuncu."}), 400
    with tiki_local_games_lock:
        state = tiki_local_games.get(token)
        if not state:
            return jsonify({"accepted": False, "message": "Oyun bulunamadı."}), 404
        result = apply_tiki_move(state, cell_index, data.get("player_id"), player_number)
        if state["finished"]:
            record_tiki_results(token, state, {1: state.get("user_id")})
        result["state"] = serialize_tiki_state(state)
    return jsonify(result), (200 if result["accepted"] else 409)


@app.route("/tiki-taka-toe/rematch", methods=["POST"])
def tiki_local_rematch():
    data = request.get_json(silent=True) or {}
    token = str(data.get("game_token", "")).strip()
    with tiki_local_games_lock:
        previous = tiki_local_games.get(token)
        if not previous:
            return jsonify({"accepted": False, "message": "Oyun bulunamadı."}), 404
        if not previous["finished"]:
            return jsonify({"accepted": False, "message": "Maç henüz bitmedi."}), 409
        starting_player = 2 if previous.get("starting_player", 1) == 1 else 1
        board = tiki_engine.generate_board({
            "rows": previous["rows"], "columns": previous["columns"]
        })
        state = create_tiki_state(board, starting_player)
        state["starting_player"] = starting_player
        state["user_id"] = previous.get("user_id")
        tiki_local_games[token] = state
    return jsonify({"accepted": True, "state": serialize_tiki_state(state)})


@app.route("/missing-xi")
def missing_xi():
    match = random.choice(missing_xi_matches)
    game_token = uuid.uuid4().hex
    with missing_xi_games_lock:
        prune_local_game_store(missing_xi_games, reserve=1)
        missing_xi_games[game_token] = {
            "match_id": match["id"], "slot_states": {},
            "attempts": {}, "errors": 0, "finished": False,
            "reward_hints": {},
            "user_id": session.get("user_id"), "created_at": time.time(),
            "stats_recorded": False,
        }
    public_match = {key: match[key] for key in (
        "id", "date", "competition", "home_team", "away_team",
        "score", "target_team", "formation",
    )}
    public_match["lineup"] = [
        {
            "slot": item["slot"], "position": item["position"],
            "shirt_number": item["shirt_number"],
            "letter_count": len(missing_xi_wordle_name(item["answer"])),
        }
        for item in sorted(match["lineup"], key=lambda item: item["slot"])
    ]
    return render_template(
        "missing_xi.html", match=public_match, game_token=game_token
    )


@app.route("/missing-xi/reward-hint", methods=["POST"])
def missing_xi_reward_hint():
    data = request.get_json(silent=True) or {}
    game_token = str(data.get("game_token", "")).strip()
    match_id = str(data.get("match_id", "")).strip()
    if data.get("reward_completed") is not True:
        return jsonify({"accepted": False, "message": "Reklam ödülü doğrulanamadı."}), 400
    try:
        slot = int(data.get("slot"))
    except (TypeError, ValueError):
        return jsonify({"accepted": False, "message": "Geçersiz oyuncu slotu."}), 400
    with missing_xi_games_lock:
        game = missing_xi_games.get(game_token)
        if not game:
            return jsonify({"accepted": False, "message": "Oyun bulunamadı."}), 404
        if game["finished"]:
            return jsonify({"accepted": False, "message": "Oyun tamamlandı."}), 409
        if match_id and match_id != game["match_id"]:
            return jsonify({"accepted": False, "message": "Maç bilgisi geçersiz."}), 400
        if not 0 <= slot < 11:
            return jsonify({"accepted": False, "message": "Geçersiz oyuncu slotu."}), 400
        if slot in game["slot_states"]:
            return jsonify({"accepted": False, "message": "Bu slot tamamlandı."}), 409
        match = next(item for item in missing_xi_matches if item["id"] == game["match_id"])
        answer = next(item for item in match["lineup"] if item["slot"] == slot)
        target_name = missing_xi_wordle_name(answer["answer"])
        hints = game.setdefault("reward_hints", {})
        slot_hints = hints.setdefault(slot, [])
        revealed_positions = {item["index"] for item in slot_hints}
        available_positions = [
            index for index in range(len(target_name))
            if index not in revealed_positions
        ]
        if not available_positions:
            return jsonify({
                "accepted": False,
                "message": "Oyuncu adındaki tüm harfler zaten açıldı.",
            }), 409
        positions = sorted(random.sample(
            available_positions, min(2, len(available_positions))
        ))
        slot_hints.extend(
            {"index": index, "letter": target_name[index]}
            for index in positions
        )
        slot_hints.sort(key=lambda item: item["index"])
        return jsonify({
            "accepted": True,
            "hint": slot_hints,
            "letter_count": len(target_name),
            "remaining_letters": len(target_name) - len(slot_hints),
            "complete": len(slot_hints) == len(target_name),
            "message": (
                "Kalan harfler açıldı."
                if len(positions) < 2 else "İki yeni harf açıldı."
            ),
        })


@app.route("/missing-xi/check", methods=["POST"])
@app.route("/missing-xi/guess", methods=["POST"])
def missing_xi_check():
    data = request.get_json(silent=True) or {}
    game_token = str(data.get("game_token", "")).strip()
    match_id = str(data.get("match_id", "")).strip()
    raw_guess = str(data.get("guess", "")).strip()
    try:
        slot = int(data.get("slot"))
    except (TypeError, ValueError):
        return jsonify({"accepted": False, "message": "Geçersiz oyuncu slotu."}), 400
    with missing_xi_games_lock:
        game = missing_xi_games.get(game_token)
        if not game:
            return jsonify({"accepted": False, "message": "Oyun bulunamadı."}), 404
        if game["finished"]:
            return jsonify({"accepted": False, "message": "Oyun tamamlandı."}), 409
        if match_id and match_id != game["match_id"]:
            return jsonify({"accepted": False, "message": "Maç bilgisi geçersiz."}), 400
        if not 0 <= slot < 11:
            return jsonify({"accepted": False, "message": "Geçersiz oyuncu slotu."}), 400
        if slot in game["slot_states"]:
            return jsonify({"accepted": False, "message": "Bu slot tamamlandı."}), 409
        match = next(item for item in missing_xi_matches if item["id"] == game["match_id"])
        answer = next(item for item in match["lineup"] if item["slot"] == slot)
        target_name = missing_xi_wordle_name(answer["answer"])
        guess_name = missing_xi_wordle_name(raw_guess)
        if len(guess_name) != len(target_name):
            return jsonify({
                "accepted": False, "message": "Tüm harfleri doldur.",
                "attempt": game["attempts"].get(slot, 0),
            }), 400
        attempt = game["attempts"].get(slot, 0) + 1
        game["attempts"][slot] = attempt
        correct = guess_name == target_name
        feedback = missing_xi_wordle_feedback(target_name, guess_name)
        exhausted = not correct and attempt >= 6
        if correct:
            game["slot_states"][slot] = "found"
        elif exhausted:
            game["errors"] += 1
            game["slot_states"][slot] = "missed"
        else:
            game["errors"] += 1
        if correct:
            message = "Doğru tahmin!"
        elif exhausted:
            message = "Hakkın bitti."
        else:
            message = "Yanlış tahmin. Tekrar dene."
        found_count = sum(state == "found" for state in game["slot_states"].values())
        missed_count = sum(state == "missed" for state in game["slot_states"].values())
        game["finished"] = len(game["slot_states"]) == 11
        if game["finished"] and not game.get("ad_break"):
            mark_match_outcome(game, "missing_xi", "completed_board", game_token)
        if game["finished"] and not game.get("stats_recorded", False):
            found_count = sum(state == "found" for state in game["slot_states"].values())
            profile_store.record_result(
                game_token, game.get("user_id"), "missing_xi", "complete",
                correct_answers=found_count, wrong_answers=game["errors"],
                completed=int(found_count == 11), score=found_count,
                play_seconds=int(time.time() - game.get("created_at", time.time())),
                completion_seconds=int(time.time() - game.get("created_at", time.time())) if found_count == 11 else None,
            )
            game["stats_recorded"] = True
        return jsonify({
            "accepted": True, "correct": correct, "exhausted": exhausted,
            "slot": slot, "guess": guess_name, "feedback": feedback,
            "attempt": attempt, "remaining": 6 - attempt,
            "player_name": answer["answer"] if correct else None,
            "answer": answer["answer"] if exhausted else None,
            "correct_count": found_count, "missed_count": missed_count,
            "errors": game["errors"], "finished": game["finished"],
            "ad_break": public_ad_break(game),
            "message": message,
        })


@app.route("/heatmap/check", methods=["POST"])
def heatmap_check():
    data = request.get_json(silent=True) or {}
    game_token = str(data.get("game_token", "")).strip()
    player_id = str(data.get("player_id", "")).strip()

    try:
        selected_index = int(data.get("index"))
    except (TypeError, ValueError):
        return jsonify({"accepted": False, "message": "Geçersiz petek."}), 400

    player = find_player_by_id(player_id)
    if not player:
        return jsonify({"accepted": False, "message": "Futbolcuyu listeden seç."}), 400

    with heatmap_games_lock:
        game = heatmap_games.get(game_token)
        if not game:
            return jsonify({"accepted": False, "message": "Oyun bulunamadı."}), 404
        if game["finished"]:
            return jsonify({"accepted": False, "message": "Oyun tamamlandı."}), 409
        if not (0 <= selected_index < len(game["cells"])):
            return jsonify({"accepted": False, "message": "Geçersiz petek."}), 400
        if selected_index == HEATMAP_SCORE_INDEX:
            return jsonify({"accepted": False, "message": "Skor peteği oynanamaz."}), 400
        if selected_index in game["heated"]:
            return jsonify({"accepted": False, "message": "Bu petek zaten ısındı."}), 409

        game["moves"] += 1
        source_condition = game["cells"][selected_index]
        if not matches_condition(player, source_condition):
            game["wrong_answers"] = game.get("wrong_answers", 0) + 1
            previous_score = game["score"]
            game["score"] = max(0, previous_score - 1)
            applied_penalty = previous_score - game["score"]
            return jsonify({
                "accepted": True, "correct": False,
                "message": f"{player['name']} bu kriteri karşılamıyor.",
                "score": game["score"], "moves": game["moves"],
                "scorePenalty": 1,
                "appliedPenalty": applied_penalty,
                "moveScore": -1,
                "totalScore": game["score"],
                "newlyHeated": [],
                "reheated": [],
            })

        newly_heated = [selected_index]
        game["correct_answers"] = game.get("correct_answers", 0) + 1
        reheated = []
        for neighbor in neighbors[selected_index]:
            if neighbor == HEATMAP_SCORE_INDEX:
                continue
            if not matches_condition(player, game["cells"][neighbor]):
                continue
            if neighbor in game["heated"]:
                reheated.append(neighbor)
            else:
                newly_heated.append(neighbor)

        combo_count = len(newly_heated)
        combo_score = combo_count * (combo_count + 1) // 2
        reheat_score = len(reheated)
        move_score = combo_score + reheat_score
        capture_heat_level = min(combo_count, 5)
        for index in newly_heated:
            game["heated"][index] = capture_heat_level
        for index in reheated:
            previous_level = game["heated"][index]
            if isinstance(previous_level, dict):
                previous_level = previous_level.get("heatLevel", 1)
            game["heated"][index] = min(int(previous_level) + 1, 5)
        game["score"] += move_score
        game["finished"] = len(game["heated"]) == 30
        if game["finished"] and not game.get("ad_break"):
            mark_match_outcome(game, "heatmap", "completed_board", game_token)
        if game["finished"] and not game.get("stats_recorded", False):
            profile_store.record_result(
                game_token, game.get("user_id"), "heatmap", "complete",
                correct_answers=game.get("correct_answers", 0), wrong_answers=game.get("wrong_answers", 0),
                score=game["score"], density=round(game["score"] / 30, 2),
                play_seconds=int(time.time() - game.get("created_at", time.time())), completed=1,
            )
            game["stats_recorded"] = True

        affected_heat_levels = {
            str(index): game["heated"][index]
            for index in newly_heated + reheated
        }

        return jsonify({
            "accepted": True, "correct": True, "player": player["name"],
            "source": selected_index,
            "heated": newly_heated,
            "newlyHeated": newly_heated,
            "reheated": reheated,
            "heatLevels": affected_heat_levels,
            "combo_level": combo_count,
            "comboCount": combo_count,
            "comboScore": combo_score,
            "reheatScore": reheat_score,
            "moveScore": move_score,
            "gained_score": move_score,
            "score": game["score"], "moves": game["moves"],
            "totalScore": game["score"],
            "heated_count": len(game["heated"]),
            "finished": game["finished"],
            "ad_break": public_ad_break(game),
        })


# ==================================================
# FUTBOLCU ARAMA
# ==================================================

@app.route(
    "/search_players"
)
def search_players():

    query = str(
        request.args.get(
            "q",
            ""
        )
    ).strip()


    if len(
        query
    ) < 2:

        return jsonify([])


    target = normalize(
        query
    )


    query_parts = [

        part

        for part in target.split()

        if part

    ]


    starts_with = []

    contains = []


    for player in players:

        name = str(
            player.get(
                "name",
                ""
            )
        ).strip()


        if not name:

            continue


        normalized_name = normalize(
            name
        )


        name_parts = [

            part

            for part in normalized_name.split()

            if part

        ]


        result = {

            "id":
                player.get(
                    "id"
                ),

            "name":
                name,

            "age":
                calculate_age(
                    player
                ),

            "birth_date":
                get_birth_date(
                    player
                )

        }


        if normalized_name.startswith(
            target
        ):

            starts_with.append(
                result
            )

            continue


        all_parts_match = True


        for query_part in query_parts:

            found_part = False


            for name_part in name_parts:

                if name_part.startswith(
                    query_part
                ):

                    found_part = True

                    break


            if not found_part:

                all_parts_match = False

                break


        if all_parts_match:

            contains.append(
                result
            )

            continue


        if target in normalized_name:

            contains.append(
                result
            )


    combined = (
        starts_with
        +
        contains
    )


    unique_results = []

    seen_ids = set()


    for item in combined:

        player_id = str(
            item.get(
                "id",
                ""
            )
        )


        if player_id in seen_ids:

            continue


        seen_ids.add(
            player_id
        )


        unique_results.append(
            item
        )


    combined = (
        unique_results[
            :12
        ]
    )


    name_counts = {}


    for item in combined:

        key = normalize(
            item[
                "name"
            ]
        )


        name_counts[
            key
        ] = (
            name_counts.get(
                key,
                0
            )
            +
            1
        )


    for item in combined:

        key = normalize(
            item[
                "name"
            ]
        )


        item[
            "show_age"
        ] = (
            name_counts.get(
                key,
                0
            )
            >
            1
        )


    return jsonify(
        combined
    )


# ==================================================
# CEVAP KONTROL
# ==================================================

@app.route(
    "/check",
    methods=[
        "POST"
    ]
)
def check():

    data = request.get_json(
        silent=True
    ) or {}


    player_name = str(
        data.get(
            "player",
            ""
        )
    ).strip()


    player_id = str(
        data.get(
            "player_id",
            ""
        )
    ).strip()


    try:

        selected_index = int(
            data.get(
                "index"
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({

            "correct":
                False,

            "message":
                "Geçersiz petek."

        }), 400


    if not (
        0
        <=
        selected_index
        <
        len(
            conditions
        )
    ):

        return jsonify({

            "correct":
                False,

            "message":
                "Geçersiz petek."

        }), 400


    if not player_name:

        return jsonify({

            "correct":
                False,

            "message":
                "Bir futbolcu seç."

        })


    if not player_id:

        return jsonify({

            "correct":
                False,

            "message":
                (
                    "Futbolcuyu "
                    "arama listesinden seç."
                )

        })


    player = find_player_by_id(
        player_id
    )


    if not player:

        return jsonify({

            "correct":
                False,

            "message":
                (
                    "Oyuncu veritabanında "
                    "bulunamadı."
                )

        })


    selected_condition = (
        conditions[
            selected_index
        ]
    )


    if not matches_condition(
        player,
        selected_condition
    ):

        return jsonify({

            "correct":
                False,

            "message":
                (
                    f"{player['name']} "
                    f"{selected_condition['label']} "
                    f"şartını karşılamıyor."
                )

        })


    matched = [
        selected_index
    ]


    for neighbor in neighbors.get(
        selected_index,
        []
    ):

        if matches_condition(
            player,
            conditions[
                neighbor
            ]
        ):

            matched.append(
                neighbor
            )


    return jsonify({

        "correct":
            True,

        "player":
            player[
                "name"
            ],

        "player_id":
            player.get(
                "id"
            ),

        "solved":
            matched

    })


# ==================================================
# SOCKET CONNECT
# ==================================================

@socketio.on(
    "connect"
)
def socket_connect(auth=None):
    user = current_user()
    if not user:
        token = str((auth or {}).get("mobile_token", "")).strip()
        if token:
            try:
                payload = mobile_socket_tokens.loads(
                    token, max_age=MOBILE_SOCKET_TOKEN_MAX_AGE,
                )
                user = profile_store.get_user(payload.get("user_id"))
            except (BadSignature, SignatureExpired, TypeError):
                user = None
    if not user:
        return
    user_id = user["id"]
    with presence_lock:
        socket_identities[request.sid] = user
        sockets = online_user_sids.setdefault(user_id, set())
        became_online = not sockets
        sockets.add(request.sid)
    join_room(user_room(user_id))
    if became_online:
        notify_friend_presence(user_id, "online")


# ==================================================
# ODA OLUŞTUR
# ==================================================

@socketio.on("find_random_match")
def socket_find_random_match():
    identity = account_identity()
    if not identity:
        emit("matchmaking_error", {"message": "Rastgele eşleşme için giriş yapmalısın."})
        return

    socket_id = request.sid
    if find_socket_room(socket_id) or find_tiki_socket_room(socket_id):
        emit("matchmaking_error", {"message": "Zaten bir oyun odasındasın."})
        return

    opponent = None
    with matchmaking_lock:
        queue = matchmaking_queues["possession"]
        queue[:] = [entry for entry in queue if entry["sid"] != socket_id]
        for index, entry in enumerate(queue):
            if entry["user_id"] != identity["user_id"]:
                opponent = queue.pop(index)
                break
        if opponent is None:
            queue.append({"sid": socket_id, **identity})

    if opponent is None:
        emit("matchmaking_waiting", {"game_mode": "possession"})
        return

    room_code = generate_room_code()
    room_conditions, _ = criterion_engine.generate_board()
    with online_rooms_lock:
        online_rooms[room_code] = {
            "players": {opponent["sid"]: 1, socket_id: 2},
            "state": create_match_state(), "conditions": room_conditions,
            "rematch_ready": {1: False, 2: False}, "match_number": 1,
            "starting_player": 1, "timer_generation": 1,
            "user_ids": {1: opponent["user_id"], 2: identity["user_id"]},
            "player_names": {1: opponent["username"], 2: identity["username"]},
            "match_id": uuid.uuid4().hex, "matchmaking": True,
        }
        online_rooms[room_code]["state"]["started"] = True
        public_state = serialize_room_state(online_rooms[room_code], include_conditions=True)

    socketio.server.enter_room(opponent["sid"], room_code, namespace="/")
    join_room(room_code)
    socketio.emit("matchmaking_found", {
        "game_mode": "possession", "room_code": room_code, "player_number": 1,
    }, to=opponent["sid"])
    emit("matchmaking_found", {
        "game_mode": "possession", "room_code": room_code, "player_number": 2,
    })
    socketio.emit("game_ready", {
        "room_code": room_code, "message": "Rastgele rakip bulundu.", "state": public_state,
    }, to=room_code)
    socketio.start_background_task(run_room_timer, room_code, 1)


@socketio.on("cancel_random_match")
def socket_cancel_random_match():
    removed = remove_from_matchmaking(request.sid)
    emit("matchmaking_cancelled", {"cancelled": bool(removed)})


@socketio.on(
    "create_room"
)
def socket_create_room():

    socket_id = (
        request.sid
    )


    existing_room = find_socket_room(
        socket_id
    )


    if existing_room:

        emit(
            "room_created",
            {

                "room_code":
                    existing_room,

                "player_number":
                    get_socket_player_number(
                        existing_room,
                        socket_id
                    )

            }
        )

        return


    room_code = generate_room_code()

    room_conditions, _ = (
        criterion_engine.generate_board()
    )


    creator = socket_current_user()

    online_rooms[
        room_code
    ] = {

        "players": {

            socket_id:
                1

        },

        "state":
            create_match_state(),

        "conditions":
            room_conditions,

        "rematch_ready": {
            1: False,
            2: False
        },

        "match_number": 1,

        "starting_player": 1,

        "timer_generation": 0,

        "user_ids": {1: socket_user_id(), 2: None},

        "player_names": {1: creator["username"] if creator else "Oyuncu 1", 2: "Oyuncu 2"},

        "match_id": uuid.uuid4().hex

    }


    join_room(
        room_code
    )


    print(
        "ODA OLUŞTURULDU:",
        room_code
    )


    emit(
        "room_created",
        {

            "room_code":
                room_code,

            "player_number":
                1

        }
    )


# ==================================================
# ODAYA KATIL
# ==================================================

@socketio.on(
    "join_game_room"
)
def socket_join_game_room(
    data
):

    socket_id = (
        request.sid
    )


    room_code = str(
        (
            data
            or
            {}
        ).get(
            "room_code",
            ""
        )
    ).strip().upper()


    if not room_code:

        emit(
            "room_error",
            {

                "message":
                    "Oda kodunu gir."

            }
        )

        return


    if room_code not in online_rooms:

        emit(
            "room_error",
            {

                "message":
                    "Oda bulunamadı."

            }
        )

        return


    if find_socket_room(
        socket_id
    ):

        emit(
            "room_error",
            {

                "message":
                    "Zaten bir odadasın."

            }
        )

        return


    room = online_rooms[
        room_code
    ]

    reserved = room.get("reserved_user_ids")
    if reserved is not None and socket_user_id() not in reserved:
        emit("room_error", {"message": "Bu davet odasına katılamazsın."})
        return


    if len(
        room[
            "players"
        ]
    ) >= 2:

        emit(
            "room_error",
            {

                "message":
                    "Oda dolu."

            }
        )

        return


    used_numbers = set(
        room["players"].values()
    )


    player_number = (
        1
        if 1 not in used_numbers
        else 2
    )


    room[
        "players"
    ][
        socket_id
    ] = player_number

    room.setdefault("user_ids", {})[player_number] = socket_user_id()
    joining_user = socket_current_user()
    room.setdefault("player_names", {})[player_number] = (
        joining_user["username"] if joining_user else f"Oyuncu {player_number}"
    )


    room[
        "state"
    ] = create_match_state()


    room[
        "state"
    ][
        "started"
    ] = True


    join_room(
        room_code
    )


    emit(
        "room_joined",
        {

            "room_code":
                room_code,

            "player_number":
                player_number

        }
    )


    emit(
        "game_ready",
        {

            "room_code":
                room_code,

            "message":
                "Rakip bulundu.",

            "state":
                serialize_room_state(
                    room,
                    include_conditions=True
                )

        },
        to=room_code
    )


    room["timer_generation"] += 1


    socketio.start_background_task(
        run_room_timer,
        room_code,
        room["timer_generation"]
    )


# ==================================================
# ODADAN ÇIK
# ==================================================

@socketio.on("submit_move")
def socket_submit_move(data):

    socket_id = request.sid
    payload = data or {}

    with online_rooms_lock:
        room_code = find_socket_room(socket_id)

        if not room_code:
            emit("move_result", {
                "accepted": False,
                "message": "Bir oyun odasında değilsin."
            })
            return

        room = online_rooms.get(room_code)
        player_number = get_socket_player_number(
            room_code,
            socket_id
        )
        state = room["state"]

        if len(room["players"]) != 2:
            emit("move_result", {
                "accepted": False,
                "message": "Maç için iki oyuncu gerekli."
            })
            return

        if not state["started"]:
            emit("move_result", {
                "accepted": False,
                "message": "Maç henüz başlamadı."
            })
            return

        if state["finished"]:
            emit("move_result", {
                "accepted": False,
                "message": "Maç sona erdi."
            })
            return

        if player_number != state["active_player"]:
            emit("move_result", {
                "accepted": False,
                "message": "Sıra sende değil."
            })
            return

        try:
            selected_index = int(payload.get("index"))
        except (TypeError, ValueError):
            emit("move_result", {
                "accepted": False,
                "message": "Geçersiz petek."
            })
            return

        if not (0 <= selected_index < len(conditions)):
            emit("move_result", {
                "accepted": False,
                "message": "Geçersiz petek."
            })
            return

        if state["owners"][selected_index] != 0:
            emit("move_result", {
                "accepted": False,
                "message": "Yalnızca boş bir petek seçebilirsin."
            })
            return

        player_id = str(
            payload.get("player_id", "")
        ).strip()
        player = find_player_by_id(player_id)

        if not player:
            emit("move_result", {
                "accepted": False,
                "message": "Oyuncu veritabanında bulunamadı."
            })
            return

        room_conditions = room[
            "conditions"
        ]

        selected_condition = room_conditions[selected_index]

        if not matches_condition(player, selected_condition):
            state["active_player"] = (
                2 if player_number == 1 else 1
            )
            move_result = {
                "accepted": True,
                "correct": False,
                "message": (
                    f"{player['name']} "
                    f"{selected_condition['label']} "
                    "şartını karşılamıyor."
                )
            }
        else:
            matched = [selected_index]

            for neighbor in neighbors.get(selected_index, []):
                if matches_condition(player, room_conditions[neighbor]):
                    matched.append(neighbor)

            claimed = []
            stolen = []

            for index in matched:
                if state["owners"][index] == player_number:
                    continue

                if state["owners"][index] not in (0, player_number):
                    stolen.append(index)

                state["owners"][index] = player_number
                claimed.append(index)

            state["steals"][str(player_number)] += len(stolen)

            calculate_room_scores(state)

            if all(state["owners"]):
                winner = (
                    1
                    if state["scores"]["1"] > state["scores"]["2"]
                    else 2
                )
                finish_room_game(
                    state,
                    winner,
                    "Tüm petekler doldu."
                )
                record_possession_results(room_code, room)
            else:
                state["active_player"] = (
                    2 if player_number == 1 else 1
                )

            move_result = {
                "accepted": True,
                "correct": True,
                "player": player["name"],
                "source": selected_index,
                "solved": matched,
                "claimed": claimed,
                "stolen": stolen
            }

        answer_notice = {
            "notice_id": uuid.uuid4().hex,
            "account_name": room.get("player_names", {}).get(
                player_number, f"Oyuncu {player_number}"
            ),
            "player_name": player["name"],
            "correct": bool(move_result.get("correct")),
            "hex_index": selected_index,
            "duration_ms": 2000,
            "expires_at_ms": int(time.time() * 1000) + 2000,
        }
        room["latest_answer"] = answer_notice
        public_state = serialize_room_state(room)

    emit("move_result", move_result)

    socketio.emit("online_answer", answer_notice, to=room_code)

    if move_result.get("correct"):
        socketio.emit(
            "move_animation",
            {
                "player_number": player_number,
                "owner": player_number,
                "source": move_result["source"],
                "claimed": move_result["claimed"],
                "stolen": move_result["stolen"]
            },
            to=room_code
        )

    socketio.emit(
        "game_state",
        public_state,
        to=room_code
    )


@socketio.on("request_rematch")
def socket_request_rematch():

    socket_id = request.sid

    with online_rooms_lock:

        room_code = find_socket_room(socket_id)

        if not room_code:
            emit("rematch_status", {
                "accepted": False,
                "message": "Bir oyun odasında değilsin."
            })
            return

        room = online_rooms.get(room_code)
        player_number = get_socket_player_number(
            room_code,
            socket_id
        )

        if len(room["players"]) != 2:
            emit("rematch_status", {
                "accepted": False,
                "message": "Rövanş için iki oyuncu gerekli."
            })
            return

        if not room["state"]["finished"]:
            emit("rematch_status", {
                "accepted": False,
                "message": "Rövanş yalnızca maç bittikten sonra istenebilir."
            })
            return

        room["rematch_ready"][player_number] = True
        ready = dict(room["rematch_ready"])
        start_rematch = all(ready.values())

        if start_rematch:
            previous_conditions = room["conditions"]
            new_conditions, _ = criterion_engine.generate_board(
                previous=previous_conditions
            )

            room["conditions"] = new_conditions
            room["match_number"] += 1
            room["starting_player"] = (
                2 if room["starting_player"] == 1 else 1
            )
            room["state"] = create_match_state(
                room["starting_player"]
            )
            room["match_id"] = uuid.uuid4().hex
            room["state"]["started"] = True
            room["rematch_ready"] = {
                1: False,
                2: False
            }
            room["timer_generation"] += 1
            timer_generation = room["timer_generation"]
            public_state = serialize_room_state(
                room,
                include_conditions=True
            )
            match_number = room["match_number"]
        else:
            timer_generation = None
            public_state = None
            match_number = room["match_number"]

    socketio.emit(
        "rematch_status",
        {
            "accepted": True,
            "requested_by": player_number,
            "ready": {
                "1": ready[1],
                "2": ready[2]
            },
            "started": start_rematch
        },
        to=room_code
    )

    if not start_rematch:
        return

    socketio.emit(
        "rematch_started",
        {
            "room_code": room_code,
            "match_number": match_number,
            "state": public_state
        },
        to=room_code
    )

    socketio.start_background_task(
        run_room_timer,
        room_code,
        timer_generation
    )


@socketio.on("forfeit_match")
def socket_forfeit_match():
    """Finish an active Possession match from the authoritative room state."""
    socket_id = request.sid
    user_id = socket_user_id()
    with online_rooms_lock:
        room_code = find_socket_room(socket_id)
        room = online_rooms.get(room_code) if room_code else None
        player_number = get_socket_player_number(room_code, socket_id) if room else None
        app.logger.info(
            "FORFEIT user=%s sid=%s room=%s player=%s started=%s finished=%s",
            user_id, socket_id, room_code, player_number,
            room and room["state"].get("started"),
            room and room["state"].get("finished"),
        )
        if (not user_id or not room or not player_number
                or room.get("user_ids", {}).get(player_number) != user_id
                or len(room["players"]) != 2
                or not room["state"]["started"] or room["state"]["finished"]):
            emit("forfeit_result", {"accepted": False, "message": "Bu maçtan şu anda pes edemezsin."})
            return {"ok": False, "message": "Bu maçtan şu anda pes edemezsin."}

        winner = 2 if player_number == 1 else 1
        finish_room_game(room["state"], winner, "forfeit", "abandoned_forfeit")
        room["timer_generation"] += 1
        record_possession_results(room_code, room)
        public_state = serialize_room_state(room)

    socketio.emit("game_state", public_state, to=room_code)
    emit("forfeit_result", {"accepted": True})
    return {"ok": True, "finished": True, "winner": winner, "end_reason": "forfeit"}


@socketio.on(
    "leave_game_room"
)
def socket_leave_game_room():

    socket_id = (
        request.sid
    )


    result = remove_socket_from_room(
        socket_id
    )


    if not result:

        return


    room_code = (
        result[
            "room_code"
        ]
    )


    leave_room(
        room_code
    )


    notify_remaining_player(
        result,
        (
            "Rakibin odadan ayrıldı. "
            "Maçı hükmen kazandın."
            if result["match_finished"]
            else "Rakip odadan ayrıldı."
        )
    )


    return


# ==================================================
# TIKI TAKA TOE SOCKET.IO (isolated room namespace)
# ==================================================

def run_tiki_turn_timer(room_code, match_id):
    while True:
        socketio.sleep(0.5)
        with tiki_rooms_lock:
            room = tiki_rooms.get(room_code)
            if not room or room["match_id"] != match_id:
                return
            state = room["state"]
            if state["finished"]:
                return
            changed = expire_tiki_turn(state)
            public_state = serialize_tiki_state(state) if changed else None
        if public_state:
            socketio.emit("tiki_game_state", public_state, to=room_code)


def find_tiki_socket_room(socket_id):
    for room_code, room in tiki_rooms.items():
        if socket_id in room["players"]:
            return room_code
    return None


def generate_tiki_room_code():
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if code not in tiki_rooms and code not in online_rooms:
            return code


def remove_socket_from_tiki_room(socket_id):
    with tiki_rooms_lock:
        room_code = find_tiki_socket_room(socket_id)
        if not room_code:
            return None
        room = tiki_rooms[room_code]
        player_number = room["players"].pop(socket_id, None)
        if not room["players"]:
            del tiki_rooms[room_code]
            return {"room_code": room_code, "state": None, "match_finished": False}
        state = room["state"]
        match_was_already_finished = bool(state.get("finished"))
        match_finished = state["started"] and not state["finished"]
        if match_finished:
            winner = next(iter(room["players"].values()))
            state.update(finished=True, winner=winner,
                         end_reason="Rakibin bağlantısı kesildi. Hükmen kazandın.")
            mark_match_outcome(state, "tiki_taka_toe", "abandoned_disconnect")
            record_tiki_results(room["match_id"], state, room.get("user_ids", {}))
        room["rematch_ready"] = {1: False, 2: False}
        return {
            "room_code": room_code, "player_number": player_number,
            "match_finished": match_finished,
            "match_was_already_finished": match_was_already_finished,
            "state": serialize_tiki_state(state),
        }


@socketio.on("tiki_find_random_match")
def tiki_find_random_match():
    identity = account_identity()
    if not identity:
        emit("tiki_matchmaking_error", {"message": "Rastgele eşleşme için giriş yapmalısın."})
        return

    socket_id = request.sid
    if find_tiki_socket_room(socket_id) or find_socket_room(socket_id):
        emit("tiki_matchmaking_error", {"message": "Zaten bir oyun odasındasın."})
        return

    opponent = None
    with matchmaking_lock:
        queue = matchmaking_queues["tiki_taka_toe"]
        queue[:] = [entry for entry in queue if entry["sid"] != socket_id]
        for index, entry in enumerate(queue):
            if entry["user_id"] != identity["user_id"]:
                opponent = queue.pop(index)
                break
        if opponent is None:
            queue.append({"sid": socket_id, **identity})

    if opponent is None:
        emit("tiki_matchmaking_waiting", {"game_mode": "tiki_taka_toe"})
        return

    room_code = generate_tiki_room_code()
    names = {"1": opponent["username"], "2": identity["username"]}
    state = create_tiki_state(tiki_engine.generate_board(), 1, True, names)
    state["starting_player"] = 1
    with tiki_rooms_lock:
        tiki_rooms[room_code] = {
            "players": {opponent["sid"]: 1, socket_id: 2}, "state": state,
            "rematch_ready": {1: False, 2: False},
            "user_ids": {1: opponent["user_id"], 2: identity["user_id"]},
            "player_names": names, "match_id": uuid.uuid4().hex, "matchmaking": True,
        }
        public_state = serialize_tiki_state(state)
        match_id = tiki_rooms[room_code]["match_id"]

    socketio.server.enter_room(opponent["sid"], room_code, namespace="/")
    join_room(room_code)
    socketio.emit("tiki_matchmaking_found", {
        "room_code": room_code, "player_number": 1,
    }, to=opponent["sid"])
    emit("tiki_matchmaking_found", {"room_code": room_code, "player_number": 2})
    socketio.emit("tiki_game_ready", {"room_code": room_code, "state": public_state}, to=room_code)
    socketio.start_background_task(run_tiki_turn_timer, room_code, match_id)


@socketio.on("tiki_cancel_random_match")
def tiki_cancel_random_match():
    removed = remove_from_matchmaking(request.sid)
    emit("tiki_matchmaking_cancelled", {"cancelled": bool(removed)})


@socketio.on("tiki_create_room")
def tiki_create_room():
    socket_id = request.sid
    with tiki_rooms_lock:
        existing = find_tiki_socket_room(socket_id)
        if existing:
            emit("tiki_room_created", {
                "room_code": existing,
                "player_number": tiki_rooms[existing]["players"][socket_id],
            })
            return
        room_code = generate_tiki_room_code()
        creator = socket_current_user()
        names = {"1": creator["username"] if creator else "Oyuncu 1", "2": "Oyuncu 2"}
        state = create_tiki_state(tiki_engine.generate_board(), started=False, player_names=names)
        state["starting_player"] = 1
        tiki_rooms[room_code] = {
            "players": {socket_id: 1}, "state": state,
            "rematch_ready": {1: False, 2: False},
            "user_ids": {1: socket_user_id(), 2: None},
            "player_names": names,
            "match_id": uuid.uuid4().hex,
        }
    join_room(room_code)
    emit("tiki_room_created", {"room_code": room_code, "player_number": 1})


@socketio.on("tiki_join_room")
def tiki_join_room(data):
    socket_id = request.sid
    room_code = str((data or {}).get("room_code", "")).strip().upper()
    with tiki_rooms_lock:
        room = tiki_rooms.get(room_code)
        if not room:
            emit("tiki_room_error", {"message": "Oda bulunamadı."})
            return
        if find_tiki_socket_room(socket_id):
            emit("tiki_room_error", {"message": "Zaten bir Tiki Taka Toe odasındasın."})
            return
        if len(room["players"]) >= 2:
            emit("tiki_room_error", {"message": "Oda dolu."})
            return
        room["players"][socket_id] = 2
        room["user_ids"][2] = socket_user_id()
        joining_user = socket_current_user()
        room.setdefault("player_names", {"1": "Oyuncu 1", "2": "Oyuncu 2"})["2"] = (
            joining_user["username"] if joining_user else "Oyuncu 2"
        )
        room["state"] = create_tiki_state(
            tiki_engine.generate_board(), 1, True, room["player_names"]
        )
        room["state"]["starting_player"] = 1
        public_state = serialize_tiki_state(room["state"])
        match_id = room["match_id"]
    join_room(room_code)
    emit("tiki_room_joined", {"room_code": room_code, "player_number": 2})
    socketio.emit("tiki_game_ready", {"room_code": room_code, "state": public_state}, to=room_code)
    socketio.start_background_task(run_tiki_turn_timer, room_code, match_id)


@socketio.on("tiki_submit_answer")
def tiki_submit_answer(data):
    socket_id = request.sid
    payload = data or {}
    with tiki_rooms_lock:
        room_code = find_tiki_socket_room(socket_id)
        room = tiki_rooms.get(room_code) if room_code else None
        if not room:
            emit("tiki_move_result", {"accepted": False, "message": "Bir Tiki Taka Toe odasında değilsin."})
            return
        player_number = room["players"].get(socket_id)
        try:
            cell_index = int(payload.get("index"))
        except (TypeError, ValueError):
            emit("tiki_move_result", {"accepted": False, "message": "Geçersiz hücre."})
            return
        result = apply_tiki_move(room["state"], cell_index, payload.get("player_id"), player_number)
        submitted_player = tiki_engine.players_by_id.get(str(payload.get("player_id", "")).strip())
        answer_notice = None
        if result.get("accepted") and submitted_player:
            answer_notice = {
                "account_name": room.get("player_names", {}).get(
                    str(player_number), f"Oyuncu {player_number}"
                ),
                "player_name": submitted_player["name"],
                "correct": bool(result.get("correct")),
                "duration_ms": 2000,
            }
        if room["state"]["finished"]:
            record_tiki_results(room["match_id"], room["state"], room.get("user_ids", {}))
        public_state = serialize_tiki_state(room["state"])
    emit("tiki_move_result", result)
    if answer_notice:
        socketio.emit("online_answer", answer_notice, to=room_code)
    socketio.emit("tiki_game_state", public_state, to=room_code)
    if public_state["finished"]:
        socketio.emit("tiki_game_over", public_state, to=room_code)


@socketio.on("tiki_rematch_request")
def tiki_rematch_request():
    socket_id = request.sid
    with tiki_rooms_lock:
        room_code = find_tiki_socket_room(socket_id)
        room = tiki_rooms.get(room_code) if room_code else None
        if not room or len(room["players"]) != 2:
            emit("tiki_rematch_status", {"accepted": False, "message": "Rövanş için iki oyuncu gerekli."})
            return
        if not room["state"]["finished"]:
            emit("tiki_rematch_status", {"accepted": False, "message": "Maç henüz bitmedi."})
            return
        player_number = room["players"][socket_id]
        room["rematch_ready"][player_number] = True
        started = all(room["rematch_ready"].values())
        if started:
            previous = room["state"]
            starter = 2 if previous.get("starting_player", 1) == 1 else 1
            board = tiki_engine.generate_board({"rows": previous["rows"], "columns": previous["columns"]})
            room["state"] = create_tiki_state(
                board, starter, True, room.get("player_names")
            )
            room["state"]["starting_player"] = starter
            room["match_id"] = uuid.uuid4().hex
            room["rematch_ready"] = {1: False, 2: False}
            public_state = serialize_tiki_state(room["state"])
            match_id = room["match_id"]
        else:
            public_state = None
        ready = dict(room["rematch_ready"])
    socketio.emit("tiki_rematch_status", {"accepted": True, "started": started, "ready": ready}, to=room_code)
    if started:
        socketio.emit("tiki_rematch_started", {"state": public_state}, to=room_code)
        socketio.start_background_task(run_tiki_turn_timer, room_code, match_id)


@socketio.on("tiki_leave_room")
def tiki_leave_room():
    result = remove_socket_from_tiki_room(request.sid)
    if not result:
        return
    leave_room(result["room_code"])
    if result["state"]:
        socketio.emit("tiki_game_state", result["state"], to=result["room_code"])
        socketio.emit("tiki_opponent_left", {
            "message": (
                "Rakip odadan ayrıldı. Maçı hükmen kazandın."
                if result["match_finished"]
                else "Rakip tamamlanan maçtan ayrıldı."
            ),
            "match_finished": result["match_finished"],
            "match_was_already_finished": result.get(
                "match_was_already_finished", False
            ),
        }, to=result["room_code"])


def user_is_in_game(user_id):
    for room in online_rooms.values():
        if user_id in room.get("user_ids", {}).values():
            return True
    for room in tiki_rooms.values():
        if user_id in room.get("user_ids", {}).values():
            return True
    return False


@socketio.on("send_game_invite")
def send_game_invite(data):
    sender = socket_current_user()
    receiver_id = str((data or {}).get("target_user_id", "")).strip()
    game_mode = str((data or {}).get("game_mode", ""))
    if not sender or game_mode != "possession" or not receiver_id or receiver_id == sender["id"]:
        emit("game_invite_error", {"message": "Geçersiz oyun daveti."}); return
    if not friend_store.are_friends(sender["id"], receiver_id):
        emit("game_invite_error", {"message": "Yalnızca arkadaşlarını davet edebilirsin."}); return
    if not is_user_online(receiver_id):
        emit("game_invite_error", {"message": "Arkadaşın çevrim dışı."}); return
    if user_is_in_game(sender["id"]) or user_is_in_game(receiver_id):
        emit("game_invite_error", {"message": "Oyunculardan biri şu anda maçta."}); return
    with game_invites_lock:
        now = time.time()
        for stale_id, stale in list(game_invites.items()):
            if stale["status"] != "pending" or now - stale["created_at"] > INVITE_TTL_SECONDS:
                del game_invites[stale_id]
        if any(item["status"] == "pending" and {item["sender_id"], item["receiver_id"]} == {sender["id"], receiver_id} for item in game_invites.values()):
            emit("game_invite_error", {"message": "Bu kullanıcıyla zaten bekleyen bir davet var."}); return
        invite_id = uuid.uuid4().hex
        game_invites[invite_id] = {"sender_id": sender["id"], "sender_sid": request.sid, "receiver_id": receiver_id, "game_mode": game_mode, "created_at": time.time(), "status": "pending"}
    socketio.emit("game_invite_received", {"invite_id": invite_id, "sender": {"id": sender["id"], "username": sender["username"]}, "game_mode": game_mode}, to=user_room(receiver_id))
    emit("game_invite_sent", {"invite_id": invite_id})


@socketio.on("accept_game_invite")
def accept_game_invite(data):
    receiver = socket_current_user()
    invite_id = str((data or {}).get("invite_id", ""))
    with game_invites_lock:
        invite = game_invites.get(invite_id)
        valid = invite and invite["status"] == "pending" and receiver and invite["receiver_id"] == receiver["id"] and time.time() - invite["created_at"] <= INVITE_TTL_SECONDS
        if not valid:
            emit("game_invite_error", {"message": "Bu davet artık geçerli değil."}); return
        if (not friend_store.are_friends(invite["sender_id"], invite["receiver_id"])
                or invite["sender_sid"] not in online_user_sids.get(invite["sender_id"], set())
                or user_is_in_game(invite["sender_id"]) or user_is_in_game(invite["receiver_id"])):
            invite["status"] = "cancelled"; emit("game_invite_error", {"message": "Davet artık başlatılamıyor."}); return
        invite["status"] = "accepted"
    room_code = create_invite_possession_room(invite["sender_id"], invite["receiver_id"])
    payload = {"invite_id": invite_id, "room_code": room_code, "game_mode": "possession"}
    socketio.emit("game_invite_accepted", payload, to=invite["sender_sid"])
    socketio.emit("game_invite_accepted", payload, to=request.sid)


@socketio.on("decline_game_invite")
def decline_game_invite(data):
    receiver = socket_current_user()
    invite_id = str((data or {}).get("invite_id", ""))
    with game_invites_lock:
        invite = game_invites.get(invite_id)
        if not invite or invite["status"] != "pending" or not receiver or invite["receiver_id"] != receiver["id"]:
            emit("game_invite_error", {"message": "Bu davet artık geçerli değil."}); return
        invite["status"] = "declined"
    socketio.emit("game_invite_declined", {"invite_id": invite_id}, to=user_room(invite["sender_id"]))


# ==================================================
# DISCONNECT
# ==================================================

@socketio.on(
    "disconnect"
)
def socket_disconnect():

    socket_id = (
        request.sid
    )

    remove_from_matchmaking(socket_id)


    with presence_lock:
        authenticated = socket_identities.pop(socket_id, None)
    user_id = authenticated["id"] if authenticated else session.get("user_id")
    if user_id:
        with presence_lock:
            sockets = online_user_sids.get(user_id, set())
            sockets.discard(socket_id)
            became_offline = not sockets
            if became_offline:
                online_user_sids.pop(user_id, None)
        if became_offline:
            notify_friend_presence(user_id, "offline")

    tiki_result = remove_socket_from_tiki_room(socket_id)
    if tiki_result and tiki_result["state"]:
        socketio.emit("tiki_game_state", tiki_result["state"], to=tiki_result["room_code"])
        socketio.emit("tiki_opponent_left", {
            "message": (
                "Rakibin bağlantısı kesildi. Maçı hükmen kazandın."
                if tiki_result["match_finished"]
                else "Rakip tamamlanan maçtan ayrıldı."
            ),
            "match_finished": tiki_result["match_finished"],
            "match_was_already_finished": tiki_result.get(
                "match_was_already_finished", False
            ),
        }, to=tiki_result["room_code"])


    result = remove_socket_from_room(
        socket_id
    )


    if not result:

        return


    notify_remaining_player(
        result,
        (
            "Rakibin bağlantısı kesildi. "
            "Maçı hükmen kazandın."
            if result["match_finished"]
            else (
                "Rakip tamamlanan maçtan ayrıldı."
                if result.get("match_was_already_finished")
                else "Rakibin bağlantısı kesildi."
            )
        )
    )


    return


# ==================================================
# HEALTH
# ==================================================

@app.route(
    "/health"
)
def health():

    return jsonify({

        "status":
            "ok",

        "players":
            len(
                players
            ),

        "condition_pool":
            len(
                ALL_CONDITIONS
            ),

        "hexes":
            len(
                conditions
            ),

        "online_rooms":
            len(
                online_rooms
            )

    })


# ==================================================
# BAŞLAT
# ==================================================

if __name__ == "__main__":

    socketio.run(

        app,

        host=
            "127.0.0.1",

        port=
            5000,

        debug=
            True,

        use_reloader=
            False

    )
