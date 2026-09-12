import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json
from pathlib import Path

INPUT_FILE = Path("data/duplicate_transfermarkt_ids_classified.json")
OUTPUT_FILE = Path("data/probable_duplicate_players_review.json")


IMPORTANT_FIELDS = [
    "name",
    "birthDate",
    "nationality",
    "positions",
    "clubs",
    "trophies",
    "transfermarkt_id",
]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def value_score(value):
    if value is None:
        return 0

    if isinstance(value, str):
        return 1 if value.strip() else 0

    if isinstance(value, list):
        return len(value)

    if isinstance(value, dict):
        return len(value)

    if isinstance(value, bool):
        return 1 if value else 0

    return 1


def player_score(player):
    score = 0
    breakdown = {}

    for field in IMPORTANT_FIELDS:
        field_score = value_score(
            player.get(field)
        )

        breakdown[field] = field_score
        score += field_score

    # Ek faydalı alanlar varsa küçük katkı
    extra_fields = [
        "trophies_checked",
        "team_trophies_checked_v2",
        "position_checked",
        "needs_enrichment",
        "clubs_verified_safe_v2",
    ]

    for field in extra_fields:
        if player.get(field) is True:
            score += 1
            breakdown[field] = 1
        else:
            breakdown[field] = 0

    return score, breakdown


def compare_lists(list1, list2):
    set1 = {
        str(x).strip()
        for x in (list1 or [])
        if str(x).strip()
    }

    set2 = {
        str(x).strip()
        for x in (list2 or [])
        if str(x).strip()
    }

    return {
        "common": sorted(set1 & set2),
        "only_player_1": sorted(set1 - set2),
        "only_player_2": sorted(set2 - set1),
    }


def compare_players(player1, player2):
    score1, breakdown1 = player_score(
        player1
    )

    score2, breakdown2 = player_score(
        player2
    )

    if score1 > score2:
        preferred = "PLAYER_1"
    elif score2 > score1:
        preferred = "PLAYER_2"
    else:
        preferred = "TIE"

    return {
        "player_1_score": score1,
        "player_2_score": score2,
        "preferred_record": preferred,
        "player_1_score_breakdown": breakdown1,
        "player_2_score_breakdown": breakdown2,
        "clubs_comparison": compare_lists(
            player1.get("clubs"),
            player2.get("clubs"),
        ),
        "positions_comparison": compare_lists(
            player1.get("positions"),
            player2.get("positions"),
        ),
        "trophies_comparison": compare_lists(
            player1.get("trophies"),
            player2.get("trophies"),
        ),
        "same_name": (
            str(player1.get("name") or "").strip().lower()
            ==
            str(player2.get("name") or "").strip().lower()
        ),
        "same_birthDate": (
            str(player1.get("birthDate") or "").strip()
            ==
            str(player2.get("birthDate") or "").strip()
        ),
        "same_nationality": (
            str(player1.get("nationality") or "").strip().lower()
            ==
            str(player2.get("nationality") or "").strip().lower()
        ),
    }


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dosya bulunamadı: {INPUT_FILE}"
        )

    report = load_json(INPUT_FILE)

    groups = report.get("groups", [])

    probable_groups = [
        group
        for group in groups
        if group.get("new_classification")
        == "PROBABLY_DUPLICATE_PLAYER"
    ]

    output_groups = []

    print(
        "Muhtemel duplicate grup sayısı:",
        len(probable_groups)
    )

    for index, group in enumerate(
        probable_groups,
        start=1
    ):
        players = group.get(
            "players",
            []
        )

        print("\n" + "=" * 90)
        print(
            f"{index} / {len(probable_groups)}"
        )
        print(
            "Transfermarkt ID:",
            group.get("transfermarkt_id")
        )

        if len(players) != 2:
            print(
                "ATLANDI: Bu grupta 2 kayıt yok."
            )

            output_groups.append({
                "transfermarkt_id":
                    group.get("transfermarkt_id"),
                "status":
                    "MANUAL_REVIEW_GROUP_SIZE",
                "players":
                    players,
            })

            continue

        player1 = players[0]
        player2 = players[1]

        comparison = compare_players(
            player1,
            player2
        )

        print(
            "PLAYER 1:",
            player1.get("name"),
            "|",
            player1.get("id")
        )

        print(
            "Doğum:",
            player1.get("birthDate")
        )

        print(
            "Skor:",
            comparison["player_1_score"]
        )

        print(
            "Kulüpler:"
        )

        for club in player1.get(
            "clubs",
            []
        ):
            print(
                "  -",
                club
            )

        print()

        print(
            "PLAYER 2:",
            player2.get("name"),
            "|",
            player2.get("id")
        )

        print(
            "Doğum:",
            player2.get("birthDate")
        )

        print(
            "Skor:",
            comparison["player_2_score"]
        )

        print(
            "Kulüpler:"
        )

        for club in player2.get(
            "clubs",
            []
        ):
            print(
                "  -",
                club
            )

        print()

        print(
            "ÖNERİLEN DAHA DOLU KAYIT:",
            comparison[
                "preferred_record"
            ]
        )

        print(
            "Ortak kulüpler:",
            comparison[
                "clubs_comparison"
            ]["common"]
        )

        print(
            "Sadece PLAYER 1:",
            comparison[
                "clubs_comparison"
            ]["only_player_1"]
        )

        print(
            "Sadece PLAYER 2:",
            comparison[
                "clubs_comparison"
            ]["only_player_2"]
        )

        output_groups.append({
            "transfermarkt_id":
                group.get("transfermarkt_id"),
            "classification":
                group.get(
                    "new_classification"
                ),
            "analysis":
                group.get("analysis"),
            "player_1":
                player1,
            "player_2":
                player2,
            "comparison":
                comparison,
        })

    output = {
        "source_file":
            str(INPUT_FILE),
        "probable_duplicate_groups":
            len(probable_groups),
        "groups":
            output_groups,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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

    print(
        "\n" + "=" * 90
    )

    print("TAMAMLANDI")

    print(
        "Muhtemel duplicate grup:",
        len(probable_groups)
    )

    print(
        "Rapor:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()