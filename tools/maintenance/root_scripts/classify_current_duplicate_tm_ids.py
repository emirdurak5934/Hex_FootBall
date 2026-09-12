import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path


PLAYERS_FILE = Path("data/players.json")
REPORT_FILE = Path("data/current_duplicate_tm_ids_classified.json")


def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip().lower()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )

    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def valid_tm_id(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if value.lower() in {
        "none",
        "null",
        "nan",
    }:
        return None

    return value


def name_similarity(name1, name2):
    a = normalize_text(name1)
    b = normalize_text(name2)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    # Örn:
    # "Bright Osayi-Samuel"
    # "Osayi-Samuel"
    if a in b or b in a:
        shorter = min(len(a), len(b))
        longer = max(len(a), len(b))

        if longer > 0:
            ratio = shorter / longer

            if ratio >= 0.45:
                return max(
                    0.90,
                    SequenceMatcher(
                        None,
                        a,
                        b
                    ).ratio()
                )

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


def normalize_club(club):
    club = normalize_text(club)

    replacements = {
        "f c": "",
        "fc": "",
        "cf": "",
        "afc": "",
        "a f c": "",
        "calcio": "",
        "football club": "",
        "futbol club": "",
    }

    for old, new in replacements.items():
        club = re.sub(
            rf"\b{re.escape(old)}\b",
            new,
            club
        )

    club = re.sub(r"\s+", " ", club)

    return club.strip()


def club_overlap(player1, player2):
    clubs1 = {
        normalize_club(x)
        for x in player1.get("clubs", [])
        if normalize_club(x)
    }

    clubs2 = {
        normalize_club(x)
        for x in player2.get("clubs", [])
        if normalize_club(x)
    }

    if not clubs1 or not clubs2:
        return {
            "common_count": 0,
            "common": [],
            "ratio": 0.0,
        }

    common = clubs1 & clubs2

    smaller = min(
        len(clubs1),
        len(clubs2)
    )

    ratio = (
        len(common) / smaller
        if smaller > 0
        else 0.0
    )

    return {
        "common_count": len(common),
        "common": sorted(common),
        "ratio": round(ratio, 3),
    }


def compare_players(player1, player2):
    name_score = name_similarity(
        player1.get("name"),
        player2.get("name")
    )

    birth1 = str(
        player1.get("birthDate") or ""
    ).strip()

    birth2 = str(
        player2.get("birthDate") or ""
    ).strip()

    if birth1 and birth2:
        same_birth = birth1 == birth2
        birth_conflict = birth1 != birth2
    else:
        same_birth = False
        birth_conflict = False

    nationality1 = normalize_text(
        player1.get("nationality")
    )

    nationality2 = normalize_text(
        player2.get("nationality")
    )

    same_nationality = bool(
        nationality1
        and nationality2
        and nationality1 == nationality2
    )

    clubs = club_overlap(
        player1,
        player2
    )

    score = 0

    # Doğum tarihi en güçlü sinyal
    if same_birth:
        score += 5

    if birth_conflict:
        score -= 6

    # İsim
    if name_score >= 0.95:
        score += 5

    elif name_score >= 0.85:
        score += 4

    elif name_score >= 0.70:
        score += 2

    elif name_score >= 0.55:
        score += 1

    else:
        score -= 2

    # Kulüpler
    if clubs["common_count"] >= 3:
        score += 4

    elif clubs["common_count"] == 2:
        score += 3

    elif clubs["common_count"] == 1:
        score += 2

    if clubs["ratio"] >= 0.75:
        score += 2

    elif clubs["ratio"] >= 0.50:
        score += 1

    # Milliyet sadece yardımcı sinyal
    if same_nationality:
        score += 1

    return {
        "player1_id": player1.get("id"),
        "player1_name": player1.get("name"),
        "player2_id": player2.get("id"),
        "player2_name": player2.get("name"),

        "name_similarity": round(
            name_score,
            3
        ),

        "birth1": birth1,
        "birth2": birth2,

        "same_birth": same_birth,
        "birth_conflict": birth_conflict,

        "same_nationality": same_nationality,

        "common_clubs": clubs["common"],
        "common_club_count": clubs[
            "common_count"
        ],
        "club_overlap_ratio": clubs[
            "ratio"
        ],

        "score": score,
    }


def classify_group(players):
    comparisons = []

    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            comparisons.append(
                compare_players(
                    players[i],
                    players[j]
                )
            )

    # En güçlü eşleşme
    best = max(
        comparisons,
        key=lambda x: x["score"]
    )

    # Herhangi iki oyuncunun doğum tarihleri
    # farklıysa dikkatli davran.
    birth_dates = {
        str(p.get("birthDate")).strip()
        for p in players
        if p.get("birthDate")
    }

    birth_conflict_group = (
        len(birth_dates) > 1
    )

    # ------------------------------------------------
    # HIGH CONFIDENCE DUPLICATE
    # ------------------------------------------------

    # Aynı doğum tarihi +
    # güçlü isim eşleşmesi
    if (
        best["same_birth"]
        and best["name_similarity"] >= 0.80
        and best["score"] >= 8
    ):
        classification = (
            "HIGH_CONFIDENCE_DUPLICATE"
        )

    # Aynı doğum tarihi +
    # ciddi kulüp örtüşmesi
    elif (
        best["same_birth"]
        and best["common_club_count"] >= 2
        and best["score"] >= 7
    ):
        classification = (
            "HIGH_CONFIDENCE_DUPLICATE"
        )

    # ------------------------------------------------
    # CONFLICT
    # ------------------------------------------------

    elif (
        birth_conflict_group
        and best["name_similarity"] < 0.65
        and best["common_club_count"] == 0
    ):
        classification = (
            "LIKELY_WRONG_TM_ID"
        )

    # ------------------------------------------------
    # MANUAL
    # ------------------------------------------------

    else:
        classification = (
            "MANUAL_REVIEW"
        )

    return (
        classification,
        comparisons,
        best
    )


def main():

    print(
        "\nGüncel players.json okunuyor..."
    )

    with PLAYERS_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:
        players = json.load(f)

    groups = defaultdict(list)

    for player in players:

        tm_id = valid_tm_id(
            player.get("transfermarkt_id")
        )

        if not tm_id:
            continue

        groups[tm_id].append(player)

    duplicate_groups = {
        tm_id: group
        for tm_id, group in groups.items()
        if len(group) > 1
    }

    report = {
        "players_total": len(players),
        "duplicate_group_count": len(
            duplicate_groups
        ),
        "duplicate_record_count": sum(
            len(group)
            for group in duplicate_groups.values()
        ),
        "summary": {
            "HIGH_CONFIDENCE_DUPLICATE": 0,
            "LIKELY_WRONG_TM_ID": 0,
            "MANUAL_REVIEW": 0,
        },
        "groups": [],
    }

    print(
        f"Duplicate TM ID grubu: "
        f"{len(duplicate_groups)}"
    )

    print(
        "Duplicate gruplardaki kayıt:",
        sum(
            len(group)
            for group in duplicate_groups.values()
        )
    )

    for index, (
        tm_id,
        group
    ) in enumerate(
        sorted(
            duplicate_groups.items(),
            key=lambda x: int(x[0])
            if x[0].isdigit()
            else 999999999
        ),
        start=1
    ):

        classification, comparisons, best = (
            classify_group(group)
        )

        report["summary"][
            classification
        ] += 1

        group_report = {
            "transfermarkt_id": tm_id,
            "record_count": len(group),
            "classification": classification,
            "players": [],
            "comparisons": comparisons,
            "best_match": best,
        }

        for player in group:

            group_report[
                "players"
            ].append({
                "id": player.get("id"),
                "name": player.get("name"),
                "birthDate": player.get(
                    "birthDate"
                ),
                "nationality": player.get(
                    "nationality"
                ),
                "positions": player.get(
                    "positions",
                    []
                ),
                "clubs": player.get(
                    "clubs",
                    []
                ),
                "trophies": player.get(
                    "trophies",
                    []
                ),
                "transfermarkt_id":
                    player.get(
                        "transfermarkt_id"
                    ),
            })

        report["groups"].append(
            group_report
        )

        names = " | ".join(
            f"{p.get('name')} "
            f"({p.get('id')})"
            for p in group
        )

        print(
            f"{index:3}/{len(duplicate_groups)} "
            f"| TM {tm_id} "
            f"| {classification}"
        )

        print(
            "    ",
            names
        )

        print(
            "     En iyi eşleşme skoru:",
            best["score"],
            "| isim:",
            best["name_similarity"],
            "| aynı DOB:",
            best["same_birth"],
            "| ortak kulüp:",
            best["common_club_count"],
        )

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with REPORT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("\n" + "=" * 60)
    print("TAMAMLANDI")
    print("=" * 60)

    print(
        "Duplicate grup:",
        report[
            "duplicate_group_count"
        ]
    )

    print(
        "Duplicate kayıt:",
        report[
            "duplicate_record_count"
        ]
    )

    print(
        "\nYüksek güven aynı oyuncu:",
        report["summary"][
            "HIGH_CONFIDENCE_DUPLICATE"
        ]
    )

    print(
        "Muhtemelen yanlış TM ID:",
        report["summary"][
            "LIKELY_WRONG_TM_ID"
        ]
    )

    print(
        "Manuel inceleme:",
        report["summary"][
            "MANUAL_REVIEW"
        ]
    )

    print(
        "\nRapor:",
        REPORT_FILE
    )

    print(
        "\nBU SCRIPT PLAYERS.JSON DOSYASINI "
        "DEĞİŞTİRMEZ."
    )


if __name__ == "__main__":
    main()