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
REPORT_FILE = Path("data/remaining_synthetic_duplicates_review.json")


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


def is_q_id(value):
    if not value:
        return False

    return bool(
        re.fullmatch(
            r"Q\d+",
            str(value).strip()
        )
    )


def is_synthetic_id(value):
    if not value:
        return False

    value = str(value).strip().lower()

    return (
        value.startswith("tm_missing_")
        or value.startswith("rm_missing_")
    )


def name_similarity(name1, name2):
    a = normalize_text(name1)
    b = normalize_text(name2)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


def normalized_clubs(player):
    result = {}

    for club in player.get("clubs", []):
        normalized = normalize_text(club)

        if normalized:
            result[normalized] = club

    return result


def get_common_clubs(player1, player2):
    clubs1 = normalized_clubs(player1)
    clubs2 = normalized_clubs(player2)

    common_keys = (
        set(clubs1)
        & set(clubs2)
    )

    return [
        clubs1[key]
        for key in sorted(common_keys)
    ]


def print_value(label, value):
    if value is None:
        value = "-"

    if isinstance(value, list):
        if value:
            value = ", ".join(
                str(x) for x in value
            )
        else:
            value = "-"

    print(
        f"    {label:<14}: {value}"
    )


def main():
    print()
    print("=" * 80)
    print("KALAN Q + SYNTHETIC DUPLICATE İNCELEMESİ")
    print("=" * 80)
    print()
    print("SADECE OKUMA MODU")
    print("players.json değiştirilmeyecek.")
    print()

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

        if tm_id:
            groups[tm_id].append(
                player
            )

    duplicate_groups = {
        tm_id: group
        for tm_id, group in groups.items()
        if len(group) > 1
    }

    review_groups = []

    for tm_id, group in duplicate_groups.items():

        # Burada sadece 2 kayıtlı gruplar
        if len(group) != 2:
            continue

        q_players = [
            p for p in group
            if is_q_id(
                p.get("id")
            )
        ]

        synthetic_players = [
            p for p in group
            if is_synthetic_id(
                p.get("id")
            )
        ]

        if not (
            len(q_players) == 1
            and
            len(synthetic_players) == 1
        ):
            continue

        q_player = q_players[0]
        synthetic = synthetic_players[0]

        birth_q = str(
            q_player.get("birthDate")
            or ""
        ).strip()

        birth_s = str(
            synthetic.get("birthDate")
            or ""
        ).strip()

        if birth_q and birth_s:
            birth_status = (
                "AYNI"
                if birth_q == birth_s
                else "FARKLI"
            )
        elif birth_q or birth_s:
            birth_status = (
                "BİRİNDE EKSİK"
            )
        else:
            birth_status = (
                "İKİSİNDE DE EKSİK"
            )

        nat_q = normalize_text(
            q_player.get("nationality")
        )

        nat_s = normalize_text(
            synthetic.get("nationality")
        )

        if nat_q and nat_s:
            nationality_status = (
                "AYNI"
                if nat_q == nat_s
                else "FARKLI"
            )
        elif nat_q or nat_s:
            nationality_status = (
                "BİRİNDE EKSİK"
            )
        else:
            nationality_status = (
                "İKİSİNDE DE EKSİK"
            )

        common_clubs = get_common_clubs(
            q_player,
            synthetic
        )

        similarity = name_similarity(
            q_player.get("name"),
            synthetic.get("name")
        )

        review_groups.append({
            "transfermarkt_id": tm_id,

            "name_similarity": round(
                similarity,
                3
            ),

            "birth_status":
                birth_status,

            "nationality_status":
                nationality_status,

            "common_club_count":
                len(common_clubs),

            "common_clubs":
                common_clubs,

            "q_player": {
                "id":
                    q_player.get("id"),

                "name":
                    q_player.get("name"),

                "birthDate":
                    q_player.get(
                        "birthDate"
                    ),

                "nationality":
                    q_player.get(
                        "nationality"
                    ),

                "positions":
                    q_player.get(
                        "positions",
                        []
                    ),

                "clubs":
                    q_player.get(
                        "clubs",
                        []
                    ),

                "trophies":
                    q_player.get(
                        "trophies",
                        []
                    ),
            },

            "synthetic_player": {
                "id":
                    synthetic.get("id"),

                "name":
                    synthetic.get("name"),

                "birthDate":
                    synthetic.get(
                        "birthDate"
                    ),

                "nationality":
                    synthetic.get(
                        "nationality"
                    ),

                "positions":
                    synthetic.get(
                        "positions",
                        []
                    ),

                "clubs":
                    synthetic.get(
                        "clubs",
                        []
                    ),

                "trophies":
                    synthetic.get(
                        "trophies",
                        []
                    ),
            },
        })

    # En güçlü adayları önce göster.
    review_groups.sort(
        key=lambda x: (
            x["common_club_count"],
            x["name_similarity"]
        ),
        reverse=True
    )

    for index, item in enumerate(
        review_groups,
        start=1
    ):
        q = item["q_player"]
        s = item[
            "synthetic_player"
        ]

        print()
        print("=" * 80)

        print(
            f"{index}/{len(review_groups)}"
            f" | TM {item['transfermarkt_id']}"
        )

        print("=" * 80)

        print()
        print("  Q KAYDI")

        print_value(
            "ID",
            q["id"]
        )

        print_value(
            "Ad",
            q["name"]
        )

        print_value(
            "Doğum",
            q["birthDate"]
        )

        print_value(
            "Milliyet",
            q["nationality"]
        )

        print_value(
            "Pozisyon",
            q["positions"]
        )

        print_value(
            "Kulüpler",
            q["clubs"]
        )

        print()
        print("  SYNTHETIC KAYIT")

        print_value(
            "ID",
            s["id"]
        )

        print_value(
            "Ad",
            s["name"]
        )

        print_value(
            "Doğum",
            s["birthDate"]
        )

        print_value(
            "Milliyet",
            s["nationality"]
        )

        print_value(
            "Pozisyon",
            s["positions"]
        )

        print_value(
            "Kulüpler",
            s["clubs"]
        )

        print()
        print("  KARŞILAŞTIRMA")

        print_value(
            "İsim skoru",
            item[
                "name_similarity"
            ]
        )

        print_value(
            "Doğum",
            item[
                "birth_status"
            ]
        )

        print_value(
            "Milliyet",
            item[
                "nationality_status"
            ]
        )

        print_value(
            "Ortak kulüp",
            item[
                "common_club_count"
            ]
        )

        print_value(
            "Ortaklar",
            item[
                "common_clubs"
            ]
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
            {
                "players_total":
                    len(players),

                "duplicate_groups_total":
                    len(
                        duplicate_groups
                    ),

                "q_synthetic_groups":
                    len(
                        review_groups
                    ),

                "groups":
                    review_groups,
            },
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 80)
    print("TAMAMLANDI")
    print("=" * 80)

    print(
        "Toplam oyuncu:",
        len(players)
    )

    print(
        "Tüm duplicate TM grubu:",
        len(duplicate_groups)
    )

    print(
        "Kalan Q + synthetic:",
        len(review_groups)
    )

    print(
        "Rapor:",
        REPORT_FILE
    )

    print()
    print(
        "players.json DEĞİŞTİRİLMEDİ."
    )


if __name__ == "__main__":
    main()