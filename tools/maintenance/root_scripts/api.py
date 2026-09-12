import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import requests


WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

HEADERS = {
    "User-Agent": "FootballDatabase/1.0"
}

def run_query(query, max_retries=3):
    import time

    for attempt in range(1, max_retries + 1):

        try:
            response = requests.get(
                WIKIDATA_ENDPOINT,
                params={
                    "query": query,
                    "format": "json"
                },
                headers=HEADERS,
                timeout=60
            )

            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as error:

            print(f"API hatası: {error}")

            if attempt < max_retries:
                print(
                    f"20 saniye bekleniyor... "
                    f"Tekrar deneme {attempt}/{max_retries}"
                )

                time.sleep(20)

            else:
                print("3 deneme başarısız. Bu oyuncu atlanıyor.")
                return None
def get_player_by_name(player_name):
    query = f"""
    SELECT ?player ?playerLabel ?birthDate
           ?nationalityLabel ?positionLabel ?clubLabel
    WHERE {{

      ?player wdt:P31 wd:Q5;
              wdt:P106 wd:Q937857.

      ?player rdfs:label "{player_name}"@en.

      OPTIONAL {{
        ?player wdt:P569 ?birthDate.
      }}

      OPTIONAL {{
        ?player wdt:P27 ?nationality.
      }}

      OPTIONAL {{
        ?player wdt:P413 ?position.
      }}

      OPTIONAL {{
        ?player wdt:P54 ?club.
      }}

      SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "en".
      }}
    }}
    """

    data = run_query(query)

    rows = data["results"]["bindings"]

    if not rows:
        return None

    first = rows[0]

    player = {
        "id": first["player"]["value"].split("/")[-1],
        "name": first.get(
            "playerLabel",
            {}
        ).get("value", player_name),

        "birthDate": "",
        "nationality": "",
        "positions": [],
        "clubs": [],
        "trophies": []
    }

    for row in rows:

        if "birthDate" in row:
            player["birthDate"] = (
                row["birthDate"]["value"][:10]
            )

        if "nationalityLabel" in row:
            nationality = row[
                "nationalityLabel"
            ]["value"]

            player["nationality"] = nationality

        if "positionLabel" in row:
            position = row[
                "positionLabel"
            ]["value"]

            if position not in player["positions"]:
                player["positions"].append(position)

        if "clubLabel" in row:
            club = row["clubLabel"]["value"]

            if club not in player["clubs"]:
                player["clubs"].append(club)

    return player
def get_team_players(team_id, start_year=1990):
    query = f"""
    SELECT DISTINCT
        ?player
        ?playerLabel
        ?birthDate
        ?nationalityLabel
        ?positionLabel
        ?start
        ?end
        ?matches
    WHERE {{

        ?player p:P54 ?teamStatement.
        ?teamStatement ps:P54 wd:{team_id}.

        OPTIONAL {{
            ?teamStatement pq:P580 ?start.
        }}

        OPTIONAL {{
            ?teamStatement pq:P582 ?end.
        }}

        OPTIONAL {{
            ?teamStatement pq:P1350 ?matches.
        }}

        OPTIONAL {{
            ?player wdt:P569 ?birthDate.
        }}

        OPTIONAL {{
            ?player wdt:P27 ?nationality.
        }}

        OPTIONAL {{
            ?player wdt:P413 ?position.
        }}

        FILTER(
            !BOUND(?matches)
            || ?matches > 0
        )

        FILTER(
            !BOUND(?end)
            || YEAR(?end) >= {start_year}
        )

        SERVICE wikibase:label {{
            bd:serviceParam wikibase:language "en".
        }}
    }}
    ORDER BY ?playerLabel
    """

    data = run_query(query)

    if data is None:
        return []

    rows = data["results"]["bindings"]

    players = {}

    for row in rows:
        player_id = row["player"]["value"].split("/")[-1]

        if player_id not in players:
            players[player_id] = {
                "id": player_id,
                "name": row.get(
                    "playerLabel",
                    {}
                ).get("value", ""),
                "birthDate": "",
                "nationality": "",
                "positions": [],
                "clubs": [],
                "trophies": []
            }

        player = players[player_id]

        if "birthDate" in row:
            player["birthDate"] = row["birthDate"]["value"][:10]

        if "nationalityLabel" in row:
            player["nationality"] = row[
                "nationalityLabel"
            ]["value"]

        if "positionLabel" in row:
            position = row[
                "positionLabel"
            ]["value"]

            if position not in player["positions"]:
                player["positions"].append(position)

    return list(players.values())
def get_player_by_id(player_id):
    query = f"""
    SELECT
        ?player
        ?playerLabel
        ?birthDate
        ?nationalityLabel
        ?positionLabel
        ?clubLabel
    WHERE {{

        VALUES ?player {{ wd:{player_id} }}

        OPTIONAL {{
            ?player wdt:P569 ?birthDate.
        }}

        OPTIONAL {{
            ?player wdt:P27 ?nationality.
        }}

        OPTIONAL {{
            ?player wdt:P413 ?position.
        }}

        OPTIONAL {{
            ?player wdt:P54 ?club.
        }}

        SERVICE wikibase:label {{
            bd:serviceParam wikibase:language "en".
        }}
    }}
    """

    data = run_query(query)

    if data is None:
        return None

    rows = data["results"]["bindings"]

    if not rows:
        return None

    first = rows[0]

    player = {
        "id": player_id,
        "name": first.get(
            "playerLabel",
            {}
        ).get("value", player_id),
        "birthDate": "",
        "nationality": "",
        "positions": [],
        "clubs": [],
        "trophies": []
    }

    for row in rows:

        if "birthDate" in row:
            player["birthDate"] = row["birthDate"]["value"][:10]

        if "nationalityLabel" in row:
            player["nationality"] = row[
                "nationalityLabel"
            ]["value"]

        if "positionLabel" in row:
            position = row[
                "positionLabel"
            ]["value"]

            if position not in player["positions"]:
                player["positions"].append(position)

        if "clubLabel" in row:
            club = row["clubLabel"]["value"]

            if club not in player["clubs"]:
                player["clubs"].append(club)

    return player
def get_player_full_history(player_id, fallback_name=""):
    query = f"""
    SELECT DISTINCT
        ?player
        ?playerLabel
        ?birthDate
        ?nationalityLabel
        ?positionLabel
        ?clubLabel
    WHERE {{

        VALUES ?player {{ wd:{player_id} }}

        OPTIONAL {{
            ?player wdt:P569 ?birthDate.
        }}

        OPTIONAL {{
            ?player wdt:P27 ?nationality.
        }}

        OPTIONAL {{
            ?player p:P413 ?positionStatement.
            ?positionStatement ps:P413 ?position.
        }}

        OPTIONAL {{
            ?player p:P54 ?clubStatement.
            ?clubStatement ps:P54 ?club.
        }}

        SERVICE wikibase:label {{
            bd:serviceParam wikibase:language "en".
        }}
    }}
    """

    data = run_query(query)

    if data is None:
        return None

    rows = data["results"]["bindings"]

    if not rows:
        return None

    first = rows[0]

    name = first.get(
        "playerLabel",
        {}
    ).get("value", fallback_name)

    if name.startswith("Q") and fallback_name:
        name = fallback_name

    player = {
        "id": player_id,
        "name": name,
        "birthDate": "",
        "nationality": "",
        "positions": [],
        "clubs": [],
        "trophies": []
    }

    for row in rows:

        if "birthDate" in row:
            player["birthDate"] = (
                row["birthDate"]["value"][:10]
            )

        if "nationalityLabel" in row:
            nationality = row[
                "nationalityLabel"
            ]["value"]

            player["nationality"] = nationality

        if "positionLabel" in row:
            position = row[
                "positionLabel"
            ]["value"]

            if position not in player["positions"]:
                player["positions"].append(position)

        if "clubLabel" in row:
            club = row[
                "clubLabel"
            ]["value"]

            if club not in player["clubs"]:
                player["clubs"].append(club)

    return player
def get_player_national_team(player_id):
    query = f"""
    SELECT DISTINCT ?team ?teamLabel
    WHERE {{
        VALUES ?player {{ wd:{player_id} }}

        ?player p:P54 ?statement.
        ?statement ps:P54 ?team.

        SERVICE wikibase:label {{
            bd:serviceParam wikibase:language "en".
        }}
    }}
    """

    data = run_query(query)

    if data is None:
        return []

    rows = data["results"]["bindings"]

    senior_teams = []

    youth_keywords = [
        "under-15",
        "under-16",
        "under-17",
        "under-18",
        "under-19",
        "under-20",
        "under-21",
        "under-23",
        "u15",
        "u16",
        "u17",
        "u18",
        "u19",
        "u20",
        "u21",
        "u23"
    ]

    for row in rows:
        name = row["teamLabel"]["value"]
        lower_name = name.lower()

        # Milli takım değilse geç
        if "national" not in lower_name:
            continue

        # Genç milli takımsa geç
        if any(keyword in lower_name for keyword in youth_keywords):
            continue

        # Kadın takımıysa geç
        if "women" in lower_name:
            continue

        if name not in senior_teams:
            senior_teams.append(name)

    return senior_teams
    query = f"""
    SELECT DISTINCT ?team ?teamLabel
    WHERE {{
        VALUES ?player {{ wd:{player_id} }}

        ?player p:P54 ?statement.
        ?statement ps:P54 ?team.

        ?team wdt:P31 wd:Q6979593.

        FILTER NOT EXISTS {{
            ?team wdt:P31 ?type.
            FILTER(
                CONTAINS(LCASE(STR(?type)), "under")
            )
        }}

        SERVICE wikibase:label {{
            bd:serviceParam wikibase:language "en".
        }}
    }}
    """

    data = run_query(query)

    if data is None:
        return []

    rows = data["results"]["bindings"]

    teams = []

    for row in rows:
        name = row["teamLabel"]["value"]

        if "under-" in name.lower():
            continue

        if "u17" in name.lower():
            continue

        if "u18" in name.lower():
            continue

        if "u19" in name.lower():
            continue

        if "u20" in name.lower():
            continue

        if "u21" in name.lower():
            continue

        if "u23" in name.lower():
            continue

        if name not in teams:
            teams.append(name)

    return teams