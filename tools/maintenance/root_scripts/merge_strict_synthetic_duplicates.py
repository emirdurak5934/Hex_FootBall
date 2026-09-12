import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import argparse
import json
import os
import re
import shutil
import tempfile
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path


PLAYERS_FILE = Path("data/players.json")
REPORT_DIR = Path("data")


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip().lower()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        ch for ch in value
        if not unicodedata.combining(ch)
    )

    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_club(value):
    value = normalize_text(value)

    if not value:
        return ""

    # Yaygın kulüp eki temizliği
    patterns = [
        r"\bfootball club\b",
        r"\bfutbol club\b",
        r"\bf\s*c\b",
        r"\bfc\b",
        r"\ba\s*f\s*c\b",
        r"\bafc\b",
        r"\bcf\b",
    ]

    for pattern in patterns:
        value = re.sub(
            pattern,
            " ",
            value
        )

    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()

    # Bilinen aliaslar
    aliases = {
        "as monaco": "monaco",
        "as monaco fc": "monaco",
        "monaco": "monaco",

        "olympique lyon": "olympique lyonnais",
        "olympique lyonnais": "olympique lyonnais",

        "ajax amsterdam": "ajax",
        "afc ajax": "ajax",
        "ajax": "ajax",

        "legia warszawa": "legia warsaw",
        "legia warsaw": "legia warsaw",

        "portimonense sad": "portimonense",
        "portimonense sc": "portimonense",

        "mika ashtarak": "mika",
        "fc mika": "mika",

        "cr flamengo": "flamengo",
        "clube de regatas do flamengo": "flamengo",

        "cruzeiro esporte clube": "cruzeiro",
        "cruzeiro ec": "cruzeiro",

        "esporte clube vitoria": "vitoria",
        "ec vitoria": "vitoria",

        "gremio foot ball porto alegrense": "gremio",
        "gremio fbpa": "gremio",

        "cr vasco da gama": "vasco da gama",
        "clube de regatas vasco da gama": "vasco da gama",
    }

    return aliases.get(
        value,
        value
    )


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


# ============================================================
# COMPARISON
# ============================================================

def get_club_map(player):
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


def evaluate_pair(
    canonical,
    synthetic
):
    canonical_clubs = (
        get_club_map(
            canonical
        )
    )

    synthetic_clubs = (
        get_club_map(
            synthetic
        )
    )

    canonical_set = set(
        canonical_clubs
    )

    synthetic_set = set(
        synthetic_clubs
    )

    common = (
        canonical_set
        & synthetic_set
    )

    synthetic_extra = (
        synthetic_set
        - canonical_set
    )

    # En az 1 kulüp ortak olmak zorunda
    has_common_club = (
        len(common) >= 1
    )

    # Synthetic taraftaki TÜM kulüpler
    # canonical içinde bulunmalı.
    all_synthetic_clubs_match = (
        bool(synthetic_set)
        and not synthetic_extra
    )

    # Pozisyon kontrolü
    canonical_positions = {
        normalize_text(x)
        for x in canonical.get(
            "positions",
            []
        )
        if normalize_text(x)
    }

    synthetic_positions = {
        normalize_text(x)
        for x in synthetic.get(
            "positions",
            []
        )
        if normalize_text(x)
    }

    position_conflict = bool(
        canonical_positions
        and synthetic_positions
        and canonical_positions.isdisjoint(
            synthetic_positions
        )
    )

    # Milliyet kontrolü
    canonical_nat = (
        normalize_text(
            canonical.get(
                "nationality"
            )
        )
    )

    synthetic_nat = (
        normalize_text(
            synthetic.get(
                "nationality"
            )
        )
    )

    nationality_conflict = bool(
        canonical_nat
        and synthetic_nat
        and canonical_nat
        != synthetic_nat
    )

    # Doğum tarihi kontrolü
    canonical_birth = str(
        canonical.get(
            "birthDate"
        )
        or ""
    ).strip()

    synthetic_birth = str(
        synthetic.get(
            "birthDate"
        )
        or ""
    ).strip()

    birth_conflict = bool(
        canonical_birth
        and synthetic_birth
        and canonical_birth
        != synthetic_birth
    )

    safe = bool(
        has_common_club
        and all_synthetic_clubs_match
        and not position_conflict
        and not nationality_conflict
        and not birth_conflict
    )

    if birth_conflict:
        reason = (
            "BIRTH_CONFLICT"
        )

    elif nationality_conflict:
        reason = (
            "NATIONALITY_CONFLICT"
        )

    elif position_conflict:
        reason = (
            "POSITION_CONFLICT"
        )

    elif synthetic_extra:
        reason = (
            "SYNTHETIC_HAS_EXTRA_CLUBS"
        )

    elif not has_common_club:
        reason = (
            "NO_COMMON_CLUB"
        )

    elif safe:
        reason = (
            "STRICT_SAFE"
        )

    else:
        reason = (
            "MANUAL"
        )

    return {
        "safe": safe,
        "reason": reason,

        "common_clubs": [
            canonical_clubs[x]
            for x in sorted(
                common
            )
        ],

        "synthetic_extra_clubs": [
            synthetic_clubs[x]
            for x in sorted(
                synthetic_extra
            )
        ],

        "position_conflict":
            position_conflict,

        "nationality_conflict":
            nationality_conflict,

        "birth_conflict":
            birth_conflict,
    }


# ============================================================
# FILE HELPERS
# ============================================================

def create_backup():
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup = Path(
        "data/"
        "players_before_strict_"
        "synthetic_merge_"
        f"{timestamp}.json"
    )

    shutil.copy2(
        PLAYERS_FILE,
        backup
    )

    return backup


def atomic_save(data):
    fd, temp_path = tempfile.mkstemp(
        prefix="players_tmp_",
        suffix=".json",
        dir=str(
            PLAYERS_FILE.parent
        ),
        text=True
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temp_path,
            PLAYERS_FILE
        )

    except Exception:
        try:
            os.remove(
                temp_path
            )
        except OSError:
            pass

        raise


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true"
    )

    args = parser.parse_args()

    mode = (
        "APPLY"
        if args.apply
        else "DRY RUN"
    )

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

    safe_plans = []
    manual = []

    for tm_id, group in (
        duplicates.items()
    ):
        if len(group) != 2:
            continue

        q_players = [
            p
            for p in group
            if is_q_id(
                p.get("id")
            )
        ]

        synthetic_players = [
            p
            for p in group
            if is_synthetic_id(
                p.get("id")
            )
        ]

        if not (
            len(q_players) == 1
            and
            len(
                synthetic_players
            ) == 1
        ):
            continue

        canonical = (
            q_players[0]
        )

        synthetic = (
            synthetic_players[0]
        )

        evaluation = (
            evaluate_pair(
                canonical,
                synthetic
            )
        )

        item = {
            "transfermarkt_id":
                tm_id,

            "canonical_id":
                canonical.get(
                    "id"
                ),

            "canonical_name":
                canonical.get(
                    "name"
                ),

            "synthetic_id":
                synthetic.get(
                    "id"
                ),

            "synthetic_name":
                synthetic.get(
                    "name"
                ),

            "evaluation":
                evaluation,
        }

        if evaluation["safe"]:
            safe_plans.append(
                item
            )
        else:
            manual.append(
                item
            )

    print()
    print("=" * 72)
    print(
        "STRICT SYNTHETIC DUPLICATE MERGE"
    )
    print(
        "Mod:",
        mode
    )
    print("=" * 72)

    print()
    print(
        "Toplam duplicate grup:",
        len(duplicates)
    )

    print(
        "STRICT SAFE:",
        len(safe_plans)
    )

    print(
        "Manuel kalan Q + synthetic:",
        len(manual)
    )

    print()
    print("=" * 72)
    print(
        "STRICT SAFE ADAYLAR"
    )
    print("=" * 72)

    for index, plan in enumerate(
        safe_plans,
        start=1
    ):
        ev = plan[
            "evaluation"
        ]

        print()
        print(
            f"{index}/"
            f"{len(safe_plans)}"
            f" | TM "
            f"{plan['transfermarkt_id']}"
        )

        print(
            "  KALACAK:",
            plan[
                "canonical_name"
            ],
            f"({plan['canonical_id']})"
        )

        print(
            "  SİLİNECEK:",
            plan[
                "synthetic_name"
            ],
            f"({plan['synthetic_id']})"
        )

        print(
            "  Ortak kulüpler:",
            ev[
                "common_clubs"
            ]
        )

    print()
    print("=" * 72)
    print(
        "MANUEL / REDDEDİLENLER"
    )
    print("=" * 72)

    for item in manual:
        ev = item[
            "evaluation"
        ]

        print()
        print(
            f"TM "
            f"{item['transfermarkt_id']}"
            f" | "
            f"{item['canonical_name']}"
            f" <> "
            f"{item['synthetic_name']}"
        )

        print(
            "  Sebep:",
            ev["reason"]
        )

        if ev[
            "synthetic_extra_clubs"
        ]:
            print(
                "  Synthetic ekstra kulüp:",
                ev[
                    "synthetic_extra_clubs"
                ]
            )

    # --------------------------------------------------------
    # APPLY
    # --------------------------------------------------------

    backup = None

    if args.apply:
        if safe_plans:
            backup = (
                create_backup()
            )

            print()
            print(
                "Backup:",
                backup
            )

            ids_to_remove = {
                str(
                    plan[
                        "synthetic_id"
                    ]
                )
                for plan
                in safe_plans
            }

            # Bu script synthetic kayıttan
            # hiçbir bilgi taşımıyor.
            #
            # Çünkü STRICT SAFE durumunda
            # synthetic kulüpler zaten
            # canonical kayıtta mevcut.
            #
            # Flag, trophy, nationality,
            # position vs. kopyalanmaz.

            players = [
                player
                for player
                in players
                if str(
                    player.get(
                        "id"
                    )
                )
                not in ids_to_remove
            ]

            atomic_save(
                players
            )

            print(
                "players.json kaydedildi."
            )

    timestamp = (
        datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    report_file = (
        REPORT_DIR
        / (
            "strict_synthetic_"
            "merge_report_"
            f"{timestamp}.json"
        )
    )

    report = {
        "mode":
            mode,

        "players_before":
            (
                len(players)
                + (
                    len(
                        safe_plans
                    )
                    if args.apply
                    else 0
                )
            ),

        "safe_count":
            len(
                safe_plans
            ),

        "manual_count":
            len(
                manual
            ),

        "safe_plans":
            safe_plans,

        "manual":
            manual,

        "backup":
            (
                str(backup)
                if backup
                else None
            ),
    }

    with report_file.open(
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
    print("=" * 72)
    print("TAMAMLANDI")
    print("=" * 72)

    print(
        "Mod:",
        mode
    )

    print(
        "STRICT SAFE:",
        len(
            safe_plans
        )
    )

    print(
        "Manuel kalan:",
        len(
            manual
        )
    )

    if args.apply:
        print(
            "Silinen synthetic:",
            len(
                safe_plans
            )
        )

    print(
        "Rapor:",
        report_file
    )

    if not args.apply:
        print()
        print(
            "BU SADECE DRY RUN."
        )
        print(
            "players.json değiştirilmedi."
        )


if __name__ == "__main__":
    main()