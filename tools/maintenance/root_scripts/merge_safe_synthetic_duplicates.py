import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import argparse
import copy
import json
import os
import re
import shutil
import tempfile
import unicodedata
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path


PLAYERS_FILE = Path("data/players.json")
REPORT_DIR = Path("data")


# ============================================================
# TEMEL YARDIMCILAR
# ============================================================

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


def is_q_id(player_id):
    if not player_id:
        return False

    return bool(
        re.fullmatch(
            r"Q\d+",
            str(player_id).strip()
        )
    )


def is_synthetic_id(player_id):
    if not player_id:
        return False

    value = str(player_id).strip().lower()

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

    # Örn:
    # Nemanja Vidić / Nemanja Vidic
    # Marcos Alonso Mendoza / Marcos Alonso
    # Alisson Becker / Alisson
    if a in b or b in a:
        shorter = min(len(a), len(b))
        longer = max(len(a), len(b))

        if longer:
            containment_ratio = shorter / longer

            if containment_ratio >= 0.40:
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


# ============================================================
# KULÜP NORMALİZASYONU
# ============================================================

def normalize_club(value):
    value = normalize_text(value)

    if not value:
        return ""

    # Sadece isim eşleştirmesi için
    # yaygın kulüp son eklerini temizliyoruz.
    patterns = [
        r"\bf\s*c\b",
        r"\bfc\b",
        r"\bcf\b",
        r"\ba\s*f\s*c\b",
        r"\bafc\b",
        r"\bfootball club\b",
        r"\bfutbol club\b",
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

    return value


def is_reserve_or_youth_club(value):
    raw = normalize_text(value)

    if not raw:
        return False

    keywords = [
        "reserve",
        "reserves",
        "academy",
        "youth",
        "juvenil",
        "primavera",
        "formation",
        "formacao",
        "under 23",
        "under 21",
        "under 20",
        "under 19",
        "under 18",
        "under 17",
        "u23",
        "u21",
        "u20",
        "u19",
        "u18",
        "u17",
        "sub 23",
        "sub 21",
        "sub 20",
        "sub 19",
        "sub 18",
        "sub 17",
    ]

    for keyword in keywords:
        if keyword in raw:
            return True

    # Önce F.C. / FC gibi normal kulüp son eklerini kaldır.
    suffix_check = raw

    suffix_check = re.sub(
        r"\s+f\s+c$",
        "",
        suffix_check
    ).strip()

    suffix_check = re.sub(
        r"\s+fc$",
        "",
        suffix_check
    ).strip()

    suffix_check = re.sub(
        r"\s+cf$",
        "",
        suffix_check
    ).strip()

    # B/C takımlarını kontrol et.
    if re.search(
        r"\s+[bc]$",
        suffix_check
    ):
        return True

    if re.search(
        r"\s+(ii|iii)$",
        suffix_check
    ):
        return True

    known_reserve_names = {
        "fc barcelona atletic",
        "barcelona atletic",
        "sevilla atletico",
        "atletico malagueno",
    }

    if suffix_check in known_reserve_names:
        return True

    return False


def club_overlap(player1, player2):
    clubs1 = {
        normalize_club(club)
        for club in player1.get("clubs", [])
        if normalize_club(club)
    }

    clubs2 = {
        normalize_club(club)
        for club in player2.get("clubs", [])
        if normalize_club(club)
    }

    if not clubs1 or not clubs2:
        return {
            "count": 0,
            "ratio": 0.0,
            "common": [],
        }

    common = clubs1 & clubs2

    smaller = min(
        len(clubs1),
        len(clubs2)
    )

    ratio = (
        len(common) / smaller
        if smaller
        else 0.0
    )

    return {
        "count": len(common),
        "ratio": round(ratio, 3),
        "common": sorted(common),
    }


# ============================================================
# LİSTE BİRLEŞTİRME
# ============================================================

def merge_clubs_preview(canonical, duplicate):
    existing = canonical.get(
        "clubs",
        []
    )

    incoming = duplicate.get(
        "clubs",
        []
    )

    existing_normalized = {
        normalize_club(club)
        for club in existing
        if normalize_club(club)
    }

    additions = []
    aliases_skipped = []
    reserve_filtered = []

    for club in incoming:
        if not club:
            continue

        if is_reserve_or_youth_club(club):
            reserve_filtered.append(club)
            continue

        normalized = normalize_club(club)

        if not normalized:
            continue

        if normalized in existing_normalized:
            aliases_skipped.append(club)
            continue

        additions.append(club)
        existing_normalized.add(normalized)

    return (
        additions,
        aliases_skipped,
        reserve_filtered
    )


def merge_simple_list_preview(
    canonical,
    duplicate,
    field
):
    existing = canonical.get(
        field,
        []
    )

    incoming = duplicate.get(
        field,
        []
    )

    normalized_existing = {
        normalize_text(value)
        for value in existing
        if normalize_text(value)
    }

    additions = []

    for value in incoming:
        if not value:
            continue

        normalized = normalize_text(value)

        if (
            normalized
            and normalized
            not in normalized_existing
        ):
            additions.append(value)
            normalized_existing.add(
                normalized
            )

    return additions


# ============================================================
# GÜVEN SINIFLANDIRMASI
# ============================================================

def evaluate_pair(canonical, duplicate):
    name_score = name_similarity(
        canonical.get("name"),
        duplicate.get("name")
    )

    clubs = club_overlap(
        canonical,
        duplicate
    )

    birth1 = str(
        canonical.get("birthDate")
        or ""
    ).strip()

    birth2 = str(
        duplicate.get("birthDate")
        or ""
    ).strip()

    same_birth = bool(
        birth1
        and birth2
        and birth1 == birth2
    )

    birth_conflict = bool(
        birth1
        and birth2
        and birth1 != birth2
    )

    # Doğum tarihi açıkça çelişiyorsa
    # asla otomatik merge yapma.
    if birth_conflict:
        return {
            "safe": False,
            "reason": "BIRTH_DATE_CONFLICT",
            "name_similarity": round(
                name_score,
                3
            ),
            "common_clubs": clubs[
                "count"
            ],
            "club_overlap_ratio": clubs[
                "ratio"
            ],
            "same_birth": False,
            "birth_conflict": True,
        }

    safe = False
    reason = "NOT_ENOUGH_EVIDENCE"

    # ----------------------------------------------------
    # KURAL 1
    # Çok güçlü isim + en az 1 ortak kulüp
    # ----------------------------------------------------
    if (
        name_score >= 0.88
        and clubs["count"] >= 1
    ):
        safe = True
        reason = (
            "STRONG_NAME_AND_CLUB"
        )

    # ----------------------------------------------------
    # KURAL 2
    # Orta-güçlü isim + en az 2 ortak kulüp
    # ----------------------------------------------------
    elif (
        name_score >= 0.70
        and clubs["count"] >= 2
    ):
        safe = True
        reason = (
            "GOOD_NAME_MULTIPLE_CLUBS"
        )

    # ----------------------------------------------------
    # KURAL 3
    # Daha zayıf isim ama en az 3 ortak kulüp
    # ----------------------------------------------------
    elif (
        name_score >= 0.55
        and clubs["count"] >= 3
    ):
        safe = True
        reason = (
            "MULTIPLE_CLUBS_SUPPORT_NAME"
        )

    # ----------------------------------------------------
    # KURAL 4
    # Aynı doğum tarihi + makul isim + ortak kulüp
    # ----------------------------------------------------
    elif (
        same_birth
        and name_score >= 0.55
        and clubs["count"] >= 1
    ):
        safe = True
        reason = (
            "SAME_BIRTH_NAME_AND_CLUB"
        )

    return {
        "safe": safe,
        "reason": reason,
        "name_similarity": round(
            name_score,
            3
        ),
        "common_clubs": clubs[
            "count"
        ],
        "club_overlap_ratio": clubs[
            "ratio"
        ],
        "common_club_names": clubs[
            "common"
        ],
        "same_birth": same_birth,
        "birth_conflict":
            birth_conflict,
    }


# ============================================================
# DOSYA İŞLEMLERİ
# ============================================================

def create_backup():
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup = Path(
        f"data/"
        f"players_before_safe_synthetic_merge_"
        f"{timestamp}.json"
    )

    shutil.copy2(
        PLAYERS_FILE,
        backup
    )

    return backup


def atomic_save(data):
    PLAYERS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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
            os.remove(temp_path)
        except OSError:
            pass

        raise


# ============================================================
# ANA
# ============================================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Gerçek değişiklikleri uygular. "
            "Varsayılan DRY RUN."
        )
    )

    args = parser.parse_args()

    mode = (
        "APPLY"
        if args.apply
        else "DRY RUN"
    )

    print()
    print("=" * 70)
    print(
        "SAFE SYNTHETIC DUPLICATE MERGE"
    )
    print("Mod:", mode)
    print("=" * 70)

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
            groups[tm_id].append(
                player
            )

    duplicate_groups = {
        tm_id: group
        for tm_id, group
        in groups.items()
        if len(group) > 1
    }

    plans = []
    manual_groups = []
    q_q_groups = []
    other_groups = []

    for tm_id, group in (
        duplicate_groups.items()
    ):
        # Bu script sadece tam 2 kayıtlı
        # gruplarla otomatik işlem yapar.
        if len(group) != 2:
            other_groups.append({
                "transfermarkt_id":
                    tm_id,
                "reason":
                    "GROUP_HAS_MORE_THAN_2",
                "players": [
                    {
                        "id": p.get("id"),
                        "name":
                            p.get("name"),
                    }
                    for p in group
                ],
            })
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

        # Q + Q => asla otomatik dokunma.
        if len(q_players) == 2:
            q_q_groups.append({
                "transfermarkt_id":
                    tm_id,
                "players": [
                    {
                        "id":
                            p.get("id"),
                        "name":
                            p.get("name"),
                        "birthDate":
                            p.get(
                                "birthDate"
                            ),
                    }
                    for p in group
                ],
            })
            continue

        # Sadece 1 Q + 1 synthetic
        if not (
            len(q_players) == 1
            and
            len(synthetic_players)
            == 1
        ):
            other_groups.append({
                "transfermarkt_id":
                    tm_id,
                "reason":
                    "NOT_Q_PLUS_SYNTHETIC",
                "players": [
                    {
                        "id": p.get("id"),
                        "name":
                            p.get("name"),
                    }
                    for p in group
                ],
            })
            continue

        canonical = q_players[0]
        duplicate = (
            synthetic_players[0]
        )

        evaluation = evaluate_pair(
            canonical,
            duplicate
        )

        club_additions, (
            club_alias_skipped
        ), reserve_filtered = (
            merge_clubs_preview(
                canonical,
                duplicate
            )
        )

        position_additions = (
            merge_simple_list_preview(
                canonical,
                duplicate,
                "positions"
            )
        )

        trophy_additions = (
            merge_simple_list_preview(
                canonical,
                duplicate,
                "trophies"
            )
        )

        scalar_fill = {}

        # Sadece canonical boşsa doldur.
        for field in [
            "birthDate",
            "nationality",
            "transfermarkt_id",
        ]:
            canonical_value = (
                canonical.get(field)
            )

            duplicate_value = (
                duplicate.get(field)
            )

            if (
                (
                    canonical_value
                    is None
                    or str(
                        canonical_value
                    ).strip() == ""
                )
                and duplicate_value
                is not None
                and str(
                    duplicate_value
                ).strip() != ""
            ):
                scalar_fill[field] = (
                    duplicate_value
                )

        item = {
            "transfermarkt_id":
                tm_id,

            "canonical_id":
                canonical.get("id"),

            "canonical_name":
                canonical.get("name"),

            "duplicate_id":
                duplicate.get("id"),

            "duplicate_name":
                duplicate.get("name"),

            "canonical_birthDate":
                canonical.get(
                    "birthDate"
                ),

            "duplicate_birthDate":
                duplicate.get(
                    "birthDate"
                ),

            "evaluation":
                evaluation,

            "clubs_to_add":
                club_additions,

            "club_alias_skipped":
                club_alias_skipped,

            "reserve_filtered":
                reserve_filtered,

            "positions_to_add":
                position_additions,

            "trophies_to_add":
                trophy_additions,

            "scalar_fill":
                scalar_fill,
        }

        if evaluation["safe"]:
            plans.append(item)
        else:
            manual_groups.append(item)

    # ========================================================
    # ÖNİZLEME
    # ========================================================

    print()
    print(
        "Toplam duplicate TM grup:",
        len(duplicate_groups)
    )

    print(
        "SAFE Q + synthetic:",
        len(plans)
    )

    print(
        "Manuel Q + synthetic:",
        len(manual_groups)
    )

    print(
        "Q + Q dokunulmayacak:",
        len(q_q_groups)
    )

    print(
        "Diğer/3+ kayıtlı grup:",
        len(other_groups)
    )

    print()
    print("=" * 70)
    print(
        "SAFE MERGE ADAYLARI"
    )
    print("=" * 70)

    for index, plan in enumerate(
        plans,
        start=1
    ):
        ev = plan["evaluation"]

        print()
        print(
            f"{index}/{len(plans)} "
            f"| TM "
            f"{plan['transfermarkt_id']}"
        )

        print(
            "  KALACAK:",
            plan["canonical_name"],
            f"({plan['canonical_id']})"
        )

        print(
            "  SİLİNECEK:",
            plan["duplicate_name"],
            f"({plan['duplicate_id']})"
        )

        print(
            "  Güven sebebi:",
            ev["reason"]
        )

        print(
            "  İsim benzerliği:",
            ev["name_similarity"]
        )

        print(
            "  Ortak kulüp:",
            ev["common_clubs"]
        )

        print(
            "  Aynı doğum tarihi:",
            ev["same_birth"]
        )

        print(
            "  Doğum tarihi çelişkisi:",
            ev["birth_conflict"]
        )

        if plan["clubs_to_add"]:
            print(
                "  Eklenecek kulüpler:",
                plan[
                    "clubs_to_add"
                ]
            )

        if plan[
            "positions_to_add"
        ]:
            print(
                "  Eklenecek positions:",
                plan[
                    "positions_to_add"
                ]
            )

        if plan[
            "trophies_to_add"
        ]:
            print(
                "  Eklenecek trophies:",
                plan[
                    "trophies_to_add"
                ]
            )

        if plan["scalar_fill"]:
            print(
                "  Doldurulacak alan:",
                plan["scalar_fill"]
            )

    # ========================================================
    # RAPOR
    # ========================================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_file = REPORT_DIR / (
        "safe_synthetic_duplicate_"
        f"merge_report_{timestamp}.json"
    )

    report = {
        "mode": mode,

        "players_before":
            len(players),

        "duplicate_group_count":
            len(duplicate_groups),

        "safe_merge_count":
            len(plans),

        "manual_q_synthetic_count":
            len(manual_groups),

        "q_q_count":
            len(q_q_groups),

        "other_group_count":
            len(other_groups),

        "safe_plans":
            plans,

        "manual_q_synthetic":
            manual_groups,

        "q_q_groups":
            q_q_groups,

        "other_groups":
            other_groups,
    }

    # ========================================================
    # APPLY
    # ========================================================

    backup_file = None

    if args.apply:
        if not plans:
            print(
                "\nUygulanacak SAFE merge yok."
            )

        else:
            backup_file = (
                create_backup()
            )

            print()
            print(
                "Backup:",
                backup_file
            )

            by_id = {
                str(
                    p.get("id")
                ): p
                for p in players
            }

            ids_to_remove = set()

            for plan in plans:
                canonical = by_id.get(
                    str(
                        plan[
                            "canonical_id"
                        ]
                    )
                )

                duplicate = by_id.get(
                    str(
                        plan[
                            "duplicate_id"
                        ]
                    )
                )

                if (
                    canonical is None
                    or duplicate is None
                ):
                    raise RuntimeError(
                        "APPLY sırasında "
                        "oyuncu bulunamadı: "
                        f"{plan}"
                    )

                # Kulüpler
                canonical.setdefault(
                    "clubs",
                    []
                )

                canonical["clubs"].extend(
                    plan[
                        "clubs_to_add"
                    ]
                )

                # Positions
                canonical.setdefault(
                    "positions",
                    []
                )

                canonical[
                    "positions"
                ].extend(
                    plan[
                        "positions_to_add"
                    ]
                )

                # Trophies
                canonical.setdefault(
                    "trophies",
                    []
                )

                canonical[
                    "trophies"
                ].extend(
                    plan[
                        "trophies_to_add"
                    ]
                )

                # Scalar alanlar:
                # SADECE boş canonical alanlar.
                for (
                    field,
                    value
                ) in plan[
                    "scalar_fill"
                ].items():
                    canonical[
                        field
                    ] = value

                # ÇOK ÖNEMLİ:
                # trophies_checked,
                # nationality_checked,
                # position_checked,
                # clubs_verified...
                # gibi doğrulama flagleri
                # duplicate kayıttan
                # ASLA kopyalanmaz.

                ids_to_remove.add(
                    str(
                        plan[
                            "duplicate_id"
                        ]
                    )
                )

            players = [
                player
                for player in players
                if str(
                    player.get("id")
                )
                not in ids_to_remove
            ]

            atomic_save(players)

            report[
                "removed_duplicate_ids"
            ] = sorted(
                ids_to_remove
            )

            report[
                "players_after"
            ] = len(players)

            report["backup"] = str(
                backup_file
            )

            print()
            print(
                "players.json kaydedildi."
            )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

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
    print("=" * 70)
    print("TAMAMLANDI")
    print("=" * 70)

    print(
        "Mod:",
        mode
    )

    print(
        "SAFE merge:",
        len(plans)
    )

    print(
        "Manuel Q + synthetic:",
        len(manual_groups)
    )

    print(
        "Q + Q dokunulmadı:",
        len(q_q_groups)
    )

    print(
        "Diğer/3+ grup:",
        len(other_groups)
    )

    if args.apply:
        print(
            "Silinen synthetic kayıt:",
            len(plans)
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