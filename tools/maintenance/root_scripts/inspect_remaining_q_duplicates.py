import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json
from collections import defaultdict
from pathlib import Path
from difflib import SequenceMatcher
import unicodedata
import re


PLAYERS_FILE = Path("data/players.json")
REPORT_FILE = Path(
    "data/remaining_q_duplicates_review.json"
)


def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip().lower()

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        ch
        for ch in value
        if not unicodedata.combining(ch)
    )

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_club(value):
    value = normalize_text(value)

    aliases = {
        "as monaco fc": "monaco",
        "as monaco": "monaco",

        "afc ajax": "ajax",
        "ajax amsterdam": "ajax",

        "olympique lyon": "olympique lyonnais",

        "olympique marseille":
            "olympique de marseille",

        "cr flamengo": "flamengo",
        "clube de regatas do flamengo":
            "flamengo",

        "gremio fbpa": "gremio",
        "gremio foot ball porto alegrense":
            "gremio",

        "cr vasco da gama":
            "vasco da gama",
        "clube de regatas vasco da gama":
            "vasco da gama",

        "cruzeiro ec": "cruzeiro",
        "cruzeiro esporte clube":
            "cruzeiro",
    }

    return aliases.get(
        value,
        value
    )


def similarity(a, b):
    a = normalize_text(a)
    b = normalize_text(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


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


def get_clubs(player):
    result = {}

    for club in player.get(
        "clubs",
        []
    ):
        normalized = normalize_club(
            club
        )

        if normalized:
            result[
                normalized
            ] = club

    return result


def player_summary(player):
    return {
        "id": player.get("id"),
        "name": player.get("name"),
        "birthDate":
            player.get("birthDate"),
        "nationality":
            player.get("nationality"),
        "positions":
            player.get("positions", []),
        "clubs":
            player.get("clubs", []),
        "trophies":
            player.get("trophies", []),
        "transfermarkt_id":
            player.get(
                "transfermarkt_id"
            ),
    }


def compare_players(a, b):
    name_score = similarity(
        a.get("name"),
        b.get("name")
    )

    birth_a = str(
        a.get("birthDate")
        or ""
    ).strip()

    birth_b = str(
        b.get("birthDate")
        or ""
    ).strip()

    if birth_a and birth_b:
        birth_status = (
            "AYNI"
            if birth_a == birth_b
            else "FARKLI"
        )
    else:
        birth_status = (
            "BİRİNDE EKSİK"
        )

    nationality_a = normalize_text(
        a.get("nationality")
    )

    nationality_b = normalize_text(
        b.get("nationality")
    )

    if (
        nationality_a
        and nationality_b
    ):
        nationality_status = (
            "AYNI"
            if nationality_a
            == nationality_b
            else "FARKLI"
        )
    else:
        nationality_status = (
            "BİRİNDE EKSİK"
        )

    clubs_a = get_clubs(a)
    clubs_b = get_clubs(b)

    common_keys = (
        set(clubs_a)
        & set(clubs_b)
    )

    common_clubs = [
        clubs_a[x]
        for x in sorted(
            common_keys
        )
    ]

    return {
        "name_similarity":
            round(
                name_score,
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
    }


def main():

    with PLAYERS_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:
        players = json.load(f)

    groups = defaultdict(list)

    for player in players:

        tm_id = valid_tm_id(
            player.get(
                "transfermarkt_id"
            )
        )

        if tm_id:
            groups[
                tm_id
            ].append(
                player
            )

    duplicates = {
        tm_id: group
        for tm_id, group
        in groups.items()
        if len(group) > 1
    }

    pair_groups = []
    triple_groups = []
    other_groups = []

    print()
    print("=" * 88)
    print(
        "REMAINING Q DUPLICATE REVIEW"
    )
    print("=" * 88)

    print()
    print(
        "Toplam oyuncu:",
        len(players)
    )

    print(
        "Duplicate TM grubu:",
        len(duplicates)
    )

    print(
        "Duplicate gruplardaki kayıt:",
        sum(
            len(group)
            for group
            in duplicates.values()
        )
    )

    for group_index, (
        tm_id,
        group
    ) in enumerate(
        sorted(
            duplicates.items(),
            key=lambda x: (
                int(x[0])
                if x[0].isdigit()
                else 999999999,
                x[0]
            )
        ),
        start=1
    ):

        print()
        print("=" * 88)

        print(
            f"{group_index}/"
            f"{len(duplicates)}"
            f" | TM {tm_id}"
            f" | {len(group)} KAYIT"
        )

        print("=" * 88)

        report_group = {
            "transfermarkt_id":
                tm_id,

            "record_count":
                len(group),

            "players": [
                player_summary(p)
                for p in group
            ],

            "comparisons": [],
        }

        for index, player in enumerate(
            group,
            start=1
        ):

            print()
            print(
                f"  KAYIT {index}"
            )

            print(
                "    ID        :",
                player.get("id")
            )

            print(
                "    Ad        :",
                player.get("name")
            )

            print(
                "    Doğum     :",
                player.get(
                    "birthDate"
                )
            )

            print(
                "    Milliyet  :",
                player.get(
                    "nationality"
                )
            )

            print(
                "    Pozisyon  :",
                ", ".join(
                    player.get(
                        "positions",
                        []
                    )
                )
            )

            print(
                "    Kulüpler  :",
                ", ".join(
                    player.get(
                        "clubs",
                        []
                    )
                )
            )

        # Her kaydı diğerleriyle karşılaştır.
        for i in range(
            len(group)
        ):

            for j in range(
                i + 1,
                len(group)
            ):

                comparison = (
                    compare_players(
                        group[i],
                        group[j]
                    )
                )

                comparison[
                    "player_1_id"
                ] = group[i].get(
                    "id"
                )

                comparison[
                    "player_1_name"
                ] = group[i].get(
                    "name"
                )

                comparison[
                    "player_2_id"
                ] = group[j].get(
                    "id"
                )

                comparison[
                    "player_2_name"
                ] = group[j].get(
                    "name"
                )

                report_group[
                    "comparisons"
                ].append(
                    comparison
                )

                print()
                print(
                    "  KARŞILAŞTIRMA"
                )

                print(
                    "    ",
                    group[i].get(
                        "name"
                    ),
                    "<>",
                    group[j].get(
                        "name"
                    )
                )

                print(
                    "    İsim skoru :",
                    comparison[
                        "name_similarity"
                    ]
                )

                print(
                    "    Doğum      :",
                    comparison[
                        "birth_status"
                    ]
                )

                print(
                    "    Milliyet   :",
                    comparison[
                        "nationality_status"
                    ]
                )

                print(
                    "    Ortak kulüp:",
                    comparison[
                        "common_club_count"
                    ]
                )

                if comparison[
                    "common_clubs"
                ]:

                    print(
                        "    Ortaklar   :",
                        ", ".join(
                            comparison[
                                "common_clubs"
                            ]
                        )
                    )

                else:
                    print(
                        "    Ortaklar   : -"
                    )

        if len(group) == 2:
            pair_groups.append(
                report_group
            )

        elif len(group) == 3:
            triple_groups.append(
                report_group
            )

        else:
            other_groups.append(
                report_group
            )

    report = {
        "total_players":
            len(players),

        "duplicate_groups":
            len(duplicates),

        "duplicate_records":
            sum(
                len(group)
                for group
                in duplicates.values()
            ),

        "pair_groups":
            pair_groups,

        "triple_groups":
            triple_groups,

        "other_groups":
            other_groups,
    }

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

    print()
    print("=" * 88)
    print("TAMAMLANDI")
    print("=" * 88)

    print(
        "2 kayıtlı grup:",
        len(pair_groups)
    )

    print(
        "3 kayıtlı grup:",
        len(triple_groups)
    )

    print(
        "Diğer:",
        len(other_groups)
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