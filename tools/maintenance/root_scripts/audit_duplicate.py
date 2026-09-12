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
from difflib import SequenceMatcher
from pathlib import Path

INPUT_FILE = Path("data/duplicate_transfermarkt_ids_report.json")
OUTPUT_FILE = Path("data/duplicate_transfermarkt_ids_classified.json")


def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip().lower()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def normalize_name(value):
    value = normalize_text(value)

    removable_parts = {
        "jr",
        "junior",
        "filho",
        "neto",
    }

    parts = [
        part
        for part in value.split()
        if part not in removable_parts
    ]

    return " ".join(parts)


def normalize_club(value):
    value = normalize_text(value)

    replacements = {
        "football club": "",
        "futbol club": "",
        "futebol clube": "",
        "club de futbol": "",
        "club de football": "",
        "fc": "",
        "f c": "",
        "cf": "",
        "afc": "",
        "sc": "",
        "ac": "",
    }

    for old, new in replacements.items():
        value = re.sub(
            rf"\b{re.escape(old)}\b",
            new,
            value
        )

    value = re.sub(r"\s+", " ", value).strip()

    aliases = {
        "ajax amsterdam": "ajax",
        "afc ajax": "ajax",
        "inter milan": "inter",
        "internazionale": "inter",
        "internazionale milano": "inter",
        "atletico madrid": "atletico de madrid",
        "manchester united": "manchester united",
        "manchester city": "manchester city",
        "paris saint germain": "paris saint germain",
        "psg": "paris saint germain",
        "bayern munich": "bayern munchen",
        "bayern munchen": "bayern munchen",
    }

    return aliases.get(value, value)


def name_similarity(name1, name2):
    a = normalize_name(name1)
    b = normalize_name(name2)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    a_parts = set(a.split())
    b_parts = set(b.split())

    if a_parts and b_parts:
        intersection = a_parts & b_parts

        if intersection:
            shorter = min(len(a_parts), len(b_parts))

            if shorter > 0:
                token_score = len(intersection) / shorter
            else:
                token_score = 0
        else:
            token_score = 0
    else:
        token_score = 0

    sequence_score = SequenceMatcher(
        None,
        a,
        b
    ).ratio()

    return max(
        sequence_score,
        token_score
    )


def club_sets(player):
    clubs = player.get("clubs", [])

    normalized = {
        normalize_club(club)
        for club in clubs
        if normalize_club(club)
    }

    return normalized


def club_overlap(player1, player2):
    clubs1 = club_sets(player1)
    clubs2 = club_sets(player2)

    if not clubs1 or not clubs2:
        return {
            "common_count": 0,
            "overlap_ratio": 0.0,
            "common_clubs": [],
        }

    common = clubs1 & clubs2

    smaller_size = min(
        len(clubs1),
        len(clubs2)
    )

    ratio = (
        len(common) / smaller_size
        if smaller_size
        else 0.0
    )

    return {
        "common_count": len(common),
        "overlap_ratio": round(ratio, 3),
        "common_clubs": sorted(common),
    }


def same_birthdate(player1, player2):
    birth1 = str(
        player1.get("birthDate") or ""
    ).strip()

    birth2 = str(
        player2.get("birthDate") or ""
    ).strip()

    return (
        bool(birth1)
        and bool(birth2)
        and birth1 == birth2
    )


def classify_pair(player1, player2):
    name_score = name_similarity(
        player1.get("name"),
        player2.get("name"),
    )

    clubs = club_overlap(
        player1,
        player2,
    )

    birth_same = same_birthdate(
        player1,
        player2,
    )

    common_count = clubs["common_count"]
    overlap_ratio = clubs["overlap_ratio"]

    if birth_same:
        if name_score >= 0.80 and common_count >= 1:
            classification = "PROBABLY_DUPLICATE_PLAYER"

        elif name_score >= 0.92:
            classification = "PROBABLY_DUPLICATE_PLAYER"

        elif name_score >= 0.65 and overlap_ratio >= 0.50:
            classification = "PROBABLY_DUPLICATE_PLAYER"

        elif name_score < 0.45 and common_count == 0:
            classification = "PROBABLY_WRONG_TM_ID"

        else:
            classification = "MANUAL_REVIEW"

    else:
        if name_score >= 0.90 and overlap_ratio >= 0.75:
            classification = "MANUAL_REVIEW"

        elif name_score < 0.50 and common_count == 0:
            classification = "PROBABLY_WRONG_TM_ID"

        else:
            classification = "MANUAL_REVIEW"

    return {
        "classification": classification,
        "same_birthdate": birth_same,
        "name_similarity": round(
            name_score,
            3
        ),
        "club_common_count": common_count,
        "club_overlap_ratio": overlap_ratio,
        "common_clubs": clubs["common_clubs"],
    }


def classify_group(group):
    players = group.get("players", [])

    if len(players) != 2:
        return {
            "classification": "MANUAL_REVIEW",
            "reason": "GROUP_HAS_MORE_THAN_2_RECORDS",
            "pairs": [],
        }

    pair_result = classify_pair(
        players[0],
        players[1],
    )

    return {
        "classification": pair_result["classification"],
        "reason": "PAIR_ANALYSIS",
        "pairs": [
            {
                "player1": {
                    "id": players[0].get("id"),
                    "name": players[0].get("name"),
                    "birthDate": players[0].get("birthDate"),
                },
                "player2": {
                    "id": players[1].get("id"),
                    "name": players[1].get("name"),
                    "birthDate": players[1].get("birthDate"),
                },
                **pair_result,
            }
        ],
    }


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dosya bulunamadı: {INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        report = json.load(f)

    groups = report.get("groups", [])

    counters = {
        "PROBABLY_DUPLICATE_PLAYER": 0,
        "PROBABLY_WRONG_TM_ID": 0,
        "MANUAL_REVIEW": 0,
    }

    classified_groups = []

    for index, group in enumerate(
        groups,
        start=1
    ):
        result = classify_group(group)

        classification = result[
            "classification"
        ]

        counters[classification] += 1

        output_group = {
            "transfermarkt_id": group.get(
                "transfermarkt_id"
            ),
            "record_count": group.get(
                "record_count"
            ),
            "old_classification": group.get(
                "classification"
            ),
            "new_classification": classification,
            "analysis": result,
            "players": group.get(
                "players",
                []
            ),
        }

        classified_groups.append(
            output_group
        )

        print("\n" + "=" * 80)
        print(
            f"{index} / {len(groups)}"
        )
        print(
            "Transfermarkt ID:",
            group.get("transfermarkt_id")
        )
        print(
            "SONUÇ:",
            classification
        )

        if result["pairs"]:
            pair = result["pairs"][0]

            print(
                "Oyuncu 1:",
                pair["player1"]["name"]
            )
            print(
                "Oyuncu 2:",
                pair["player2"]["name"]
            )
            print(
                "Aynı doğum tarihi:",
                pair["same_birthdate"]
            )
            print(
                "İsim benzerliği:",
                pair["name_similarity"]
            )
            print(
                "Ortak kulüp:",
                pair["club_common_count"]
            )
            print(
                "Kulüp örtüşmesi:",
                pair["club_overlap_ratio"]
            )

            if pair["common_clubs"]:
                print(
                    "Ortak kulüpler:",
                    ", ".join(
                        pair["common_clubs"]
                    )
                )

    output = {
        "source_file": str(INPUT_FILE),
        "total_groups": len(groups),
        "summary": counters,
        "groups": classified_groups,
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("\n" + "=" * 80)
    print("TAMAMLANDI")
    print(
        "Muhtemelen aynı oyuncu:",
        counters["PROBABLY_DUPLICATE_PLAYER"]
    )
    print(
        "Muhtemelen yanlış TM ID:",
        counters["PROBABLY_WRONG_TM_ID"]
    )
    print(
        "Manuel inceleme:",
        counters["MANUAL_REVIEW"]
    )
    print(
        "Rapor:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()