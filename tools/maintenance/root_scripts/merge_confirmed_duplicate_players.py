import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import argparse
import json
import re
import shutil
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path


PLAYERS_FILE = Path("data/players.json")
CLASSIFIED_FILE = Path(
    "data/duplicate_transfermarkt_ids_classified.json"
)

REPORT_DIR = Path("data")
BACKUP_DIR = Path("data")


# =========================================================
# JSON
# =========================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def atomic_save_json(path, data):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=path.parent,
        suffix=".tmp",
    ) as temp_file:

        json.dump(
            data,
            temp_file,
            ensure_ascii=False,
            indent=2,
        )

        temp_path = Path(
            temp_file.name
        )

    temp_path.replace(path)


def create_backup():
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_path = (
        BACKUP_DIR
        / f"players_before_duplicate_merge_{timestamp}.json"
    )

    shutil.copy2(
        PLAYERS_FILE,
        backup_path,
    )

    return backup_path


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip().lower()

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.replace("&", " and ")

    value = re.sub(
        r"[^a-z0-9\s]",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


# =========================================================
# CLUB ALIASES
# =========================================================

CLUB_ALIAS_MAP = {

    # AJAX
    "ajax": "ajax",
    "afc ajax": "ajax",
    "ajax amsterdam": "ajax",

    # ATLETICO MADRID
    "atletico madrid": "atletico madrid",
    "atletico de madrid": "atletico madrid",

    # BENFICA
    "sl benfica": "benfica",
    "s l benfica": "benfica",
    "benfica": "benfica",

    # BESIKTAS
    "besiktas": "besiktas",
    "besiktas jk": "besiktas",
    "besiktas j k": "besiktas",
    "besiktas jk football": "besiktas",
    "besiktas j k football": "besiktas",

    # FENERBAHCE
    "fenerbahce": "fenerbahce",
    "fenerbahce istanbul": "fenerbahce",

    # BAYERN
    "fc bayern munich": "bayern munich",
    "bayern munich": "bayern munich",
    "bayern munchen": "bayern munich",
    "fc bayern munchen": "bayern munich",

    # MANCHESTER
    "manchester united": "manchester united",
    "manchester united fc": "manchester united",

    "manchester city": "manchester city",
    "manchester city fc": "manchester city",

    # INTER
    "inter": "inter",
    "inter milan": "inter",
    "internazionale": "inter",
    "internazionale milano": "inter",

    # PSG
    "paris saint germain": "paris saint germain",
    "paris saint germain fc": "paris saint germain",
    "psg": "paris saint germain",

    # SANTOS
    "santos": "santos",
    "santos fc": "santos",
    "santos f c": "santos",

    # ESPANYOL
    "rcd espanyol barcelona": "espanyol",
    "rcd espanyol de barcelona": "espanyol",
    "espanyol": "espanyol",

    # HUESCA
    "sd huesca": "huesca",
    "sociedad deportiva huesca": "huesca",

    # ALMERIA
    "ud almeria": "almeria",
    "union deportiva almeria": "almeria",

    # DEPORTIVO
    "deportivo a coruna": "deportivo la coruna",
    "deportivo de a coruna": "deportivo la coruna",

    # OSASUNA
    "ca osasuna": "osasuna",
    "club atletico osasuna": "osasuna",
    "osasuna": "osasuna",

    # VALLADOLID
    "real valladolid": "real valladolid",
    "real valladolid cf": "real valladolid",

    # RACING
    "racing santander": "racing santander",
    "racing de santander": "racing santander",

    # TWENTE
    "fc twente": "twente",
    "fc twente enschede": "twente",

    # EUPEN
    "kas eupen": "eupen",
    "k a s eupen": "eupen",

    # FLAMENGO
    "cr flamengo": "flamengo",
    "clube de regatas do flamengo": "flamengo",

    # INTERNACIONAL
    "sport club internacional": "internacional",
    "sc internacional": "internacional",
    "s c internacional": "internacional",

    # CRUZ AZUL
    "cruz azul": "cruz azul",
    "cd cruz azul": "cruz azul",

    # CLUB BRUGGE
    "club brugge kv": "club brugge",
    "club brugge k v": "club brugge",
    "club brugge": "club brugge",

    # AL AHLI
    "al ahli": "al ahli",
    "al ahli fc": "al ahli",
    "al ahli sfc": "al ahli",
    "al ahli saudi fc": "al ahli",

    # AL HILAL
    "al hilal": "al hilal",
    "al hilal sfc": "al hilal",

    # MARITIMO
    "cs maritimo": "maritimo",
    "c s maritimo": "maritimo",

    # WISLA
    "wisla krakow": "wisla krakow",

    # REAL JAEN
    "real jaen": "real jaen",
    "real jaen cf": "real jaen",

    # CEUTA
    "ad ceuta": "ceuta",
    "ad ceuta fc": "ceuta",

    # REUS
    "cf reus deportiu": "reus",

    # LUCENA
    "lucena cf": "lucena",

    # ONTINYENT
    "ontinyent cf": "ontinyent",

    # IRAKLIS
    "iraklis thessaloniki": "iraklis",
    "g s iraklis thessalonikis": "iraklis",
    "g s iraklis thessalonikis mens association football": "iraklis",

    # SAO PAULO
    "sao paulo fc": "sao paulo",
    "sao paulo futebol clube": "sao paulo",

    # JOINVILLE
    "joinville esporte clube": "joinville",
    "joinville esporte clube sc": "joinville",

    # VITORIA
    "e c vitoria": "vitoria",
    "esporte clube vitoria": "vitoria",

    # GREMIO
    "gremio fbpa": "gremio",
    "gremio foot ball porto alegrense": "gremio",

    # CRB
    "clube de regatas brasil": "crb",
    "clube de regatas brasil al": "crb",

    # PORTUGUESA
    "portuguesa": "portuguesa",
    "associacao portuguesa de desportos": "portuguesa",

    # ARAPIRAQUENSE
    "agremiacao sportiva arapiraquense": "arapiraquense",
    "agremiacao sportiva arapiraquense al": "arapiraquense",

    # JEANNE D'ARC
    "asc jeanne d arc": "jeanne d arc",
    "asc jeanne d arc dakar": "jeanne d arc",
}


def strip_year_suffix(value):
    # Örnek:
    # CF Reus Deportiu (-2020)
    # FC Barcelona C (- 2007)

    value = re.sub(
        r"\s*\(\s*-\s*\d{4}\s*\)\s*$",
        "",
        value,
    )

    return value.strip()


def normalize_club(value):
    value = normalize_text(value)

    if not value:
        return ""

    value = strip_year_suffix(
        value
    )

    # Gereksiz Wikidata açıklaması
    value = value.replace(
        "mens association football",
        "",
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    # Önce exact alias kontrolü
    if value in CLUB_ALIAS_MAP:
        return CLUB_ALIAS_MAP[value]

    # FC/F.C. gibi ekleri karşılaştırma
    # amacıyla sadeleştir.
    simplified = value

    endings = [
        " football club",
        " futebol clube",
        " futbol club",
    ]

    for ending in endings:
        if simplified.endswith(ending):
            simplified = simplified[
                :-len(ending)
            ].strip()

    simplified = re.sub(
        r"\bfc\b",
        "",
        simplified,
    )

    simplified = re.sub(
        r"\bcf\b",
        "",
        simplified,
    )

    simplified = re.sub(
        r"\bafc\b",
        "",
        simplified,
    )

    simplified = re.sub(
        r"\s+",
        " ",
        simplified,
    ).strip()

    if simplified in CLUB_ALIAS_MAP:
        return CLUB_ALIAS_MAP[
            simplified
        ]

    return simplified


# =========================================================
# RESERVE / YOUTH FILTER
# =========================================================

KNOWN_RESERVE_CLUBS = {
    "fc barcelona atletic",
    "barcelona atletic",
    "seville atletico",
    "sevilla atletico",
    "atletico malagueno",
}


def is_reserve_or_youth_club(club):
    raw = normalize_text(club)

    if not raw:
        return True

    raw_without_year = strip_year_suffix(
        raw
    )

    # -----------------------------------------------------
    # F.C. / F C / FC son eklerini geçici olarak koru
    # Çünkü "Arsenal F.C." -> "arsenal f c"
    # ve sondaki "c" C takımı sanılmamalı.
    # -----------------------------------------------------

    raw_for_suffix_check = re.sub(
        r"\s+f\s+c$",
        "",
        raw_without_year,
    ).strip()

    raw_for_suffix_check = re.sub(
        r"\s+fc$",
        "",
        raw_for_suffix_check,
    ).strip()

    # -----------------------------------------------------
    # Bilinen özel reserve / alt takım isimleri
    # -----------------------------------------------------

    known_reserve_clubs = {
        "fc barcelona atletic",
        "barcelona atletic",
        "sevilla atletico",
        "atletico malagueno",
    }

    if (
        raw_without_year
        in known_reserve_clubs
    ):
        return True

    # -----------------------------------------------------
    # Yaş grupları
    # -----------------------------------------------------

    age_patterns = [
        r"\bu\s*15\b",
        r"\bu\s*16\b",
        r"\bu\s*17\b",
        r"\bu\s*18\b",
        r"\bu\s*19\b",
        r"\bu\s*20\b",
        r"\bu\s*21\b",
        r"\bu\s*22\b",
        r"\bu\s*23\b",

        r"\bu15\b",
        r"\bu16\b",
        r"\bu17\b",
        r"\bu18\b",
        r"\bu19\b",
        r"\bu20\b",
        r"\bu21\b",
        r"\bu22\b",
        r"\bu23\b",

        r"\bunder\s*15\b",
        r"\bunder\s*16\b",
        r"\bunder\s*17\b",
        r"\bunder\s*18\b",
        r"\bunder\s*19\b",
        r"\bunder\s*20\b",
        r"\bunder\s*21\b",
        r"\bunder\s*22\b",
        r"\bunder\s*23\b",

        r"\bsub\s*15\b",
        r"\bsub\s*16\b",
        r"\bsub\s*17\b",
        r"\bsub\s*18\b",
        r"\bsub\s*19\b",
        r"\bsub\s*20\b",
        r"\bsub\s*21\b",
        r"\bsub\s*22\b",
        r"\bsub\s*23\b",
    ]

    for pattern in age_patterns:
        if re.search(
            pattern,
            raw_without_year,
        ):
            return True

    # -----------------------------------------------------
    # Genel reserve / youth kelimeleri
    # -----------------------------------------------------

    keyword_patterns = [
        r"\byouth\b",
        r"\bacademy\b",
        r"\bjunior\b",
        r"\bjuniors\b",
        r"\bprimavera\b",
        r"\breserve\b",
        r"\breserves\b",
        r"\bamateure\b",
        r"\bformation\b",
        r"\bformacao\b",
        r"\bsecond team\b",
        r"\bsecond squad\b",
    ]

    for pattern in keyword_patterns:
        if re.search(
            pattern,
            raw_without_year,
        ):
            return True

    # -----------------------------------------------------
    # B / C / II / III TAKIMLARI
    #
    # Burada raw_for_suffix_check kullanıyoruz.
    # Böylece:
    #
    # Arsenal F.C. -> arsenal
    # Manchester City F.C. -> manchester city
    #
    # olur ve yanlışlıkla C takım sayılmaz.
    # -----------------------------------------------------

    if re.search(
        r"\s+b$",
        raw_for_suffix_check,
    ):
        return True

    if re.search(
        r"\s+c$",
        raw_for_suffix_check,
    ):
        return True

    if re.search(
        r"\s+ii$",
        raw_for_suffix_check,
    ):
        return True

    if re.search(
        r"\s+iii$",
        raw_for_suffix_check,
    ):
        return True

    # -----------------------------------------------------
    # Özel alt takım isimleri
    # -----------------------------------------------------

    if re.search(
        r"\bbarcelona\s+atletic$",
        raw_without_year,
    ):
        return True

    if re.search(
        r"\bsevilla\s+atletico$",
        raw_without_year,
    ):
        return True

    if re.search(
        r"\batletico\s+malagueno$",
        raw_without_year,
    ):
        return True

    return False

def merge_clubs(
    main_clubs,
    duplicate_clubs,
):
    result = list(
        main_clubs or []
    )

    normalized_existing = set()

    for club in result:
        normalized = normalize_club(
            club
        )

        if normalized:
            normalized_existing.add(
                normalized
            )

    added = []
    skipped_alias = []
    skipped_reserve = []

    for club in duplicate_clubs or []:

        if is_reserve_or_youth_club(
            club
        ):
            skipped_reserve.append(
                club
            )
            continue

        normalized = normalize_club(
            club
        )

        if not normalized:
            continue

        if (
            normalized
            in normalized_existing
        ):
            skipped_alias.append(
                club
            )
            continue

        result.append(
            club
        )

        normalized_existing.add(
            normalized
        )

        added.append(
            club
        )

    return (
        result,
        added,
        skipped_alias,
        skipped_reserve,
    )


# =========================================================
# OTHER LISTS
# =========================================================

def merge_simple_list(
    main_values,
    duplicate_values,
):
    result = list(
        main_values or []
    )

    existing = {
        normalize_text(value)
        for value in result
        if normalize_text(value)
    }

    added = []

    for value in duplicate_values or []:

        normalized = normalize_text(
            value
        )

        if not normalized:
            continue

        if normalized in existing:
            continue

        result.append(
            value
        )

        existing.add(
            normalized
        )

        added.append(
            value
        )

    return (
        result,
        added,
    )


# =========================================================
# PLAYER MERGE
# =========================================================

def merge_player(
    main_player,
    duplicate_player,
):
    changes = {
        "clubs_added": [],
        "clubs_skipped_alias": [],
        "clubs_skipped_reserve": [],
        "positions_added": [],
        "trophies_added": [],
        "scalar_fields_filled": {},
    }

    # CLUBS
    (
        merged_clubs,
        clubs_added,
        alias_skipped,
        reserve_skipped,
    ) = merge_clubs(
        main_player.get(
            "clubs",
            [],
        ),
        duplicate_player.get(
            "clubs",
            [],
        ),
    )

    main_player["clubs"] = (
        merged_clubs
    )

    changes[
        "clubs_added"
    ] = clubs_added

    changes[
        "clubs_skipped_alias"
    ] = alias_skipped

    changes[
        "clubs_skipped_reserve"
    ] = reserve_skipped

    # POSITIONS
    (
        merged_positions,
        positions_added,
    ) = merge_simple_list(
        main_player.get(
            "positions",
            [],
        ),
        duplicate_player.get(
            "positions",
            [],
        ),
    )

    if merged_positions:
        main_player[
            "positions"
        ] = merged_positions

    changes[
        "positions_added"
    ] = positions_added

    # TROPHIES
    (
        merged_trophies,
        trophies_added,
    ) = merge_simple_list(
        main_player.get(
            "trophies",
            [],
        ),
        duplicate_player.get(
            "trophies",
            [],
        ),
    )

    if (
        merged_trophies
        or "trophies"
        in main_player
        or "trophies"
        in duplicate_player
    ):
        main_player[
            "trophies"
        ] = merged_trophies

    changes[
        "trophies_added"
    ] = trophies_added

    # Ana kayıtta boşsa doldur.
    # Var olan değeri EZME.
    scalar_fields = [
        "birthDate",
        "nationality",
        "transfermarkt_id",
    ]

    for field in scalar_fields:

        old_value = main_player.get(
            field
        )

        incoming = (
            duplicate_player.get(
                field
            )
        )

        old_empty = (
            old_value is None
            or (
                isinstance(
                    old_value,
                    str,
                )
                and not old_value.strip()
            )
        )

        incoming_valid = (
            incoming is not None
            and (
                not isinstance(
                    incoming,
                    str,
                )
                or incoming.strip()
            )
        )

        if (
            old_empty
            and incoming_valid
        ):
            main_player[
                field
            ] = incoming

            changes[
                "scalar_fields_filled"
            ][field] = incoming

    # TRUE kontrol alanlarını koru
    boolean_fields = [
        "trophies_checked",
        "team_trophies_checked_v2",
        "position_checked",
    ]

    for field in boolean_fields:

        if (
            duplicate_player.get(
                field
            ) is True
            and main_player.get(
                field
            ) is not True
        ):
            main_player[
                field
            ] = True

            changes[
                "scalar_fields_filled"
            ][field] = True

    return changes


# =========================================================
# MAIN
# =========================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Gerçek değişiklik yapar. "
            "Verilmezse DRY RUN."
        ),
    )

    args = parser.parse_args()

    apply_changes = (
        args.apply
    )

    print("=" * 90)

    if apply_changes:
        print(
            "MOD: APPLY"
        )
        print(
            "players.json DEĞİŞTİRİLECEK"
        )
    else:
        print(
            "MOD: DRY RUN"
        )
        print(
            "players.json DEĞİŞTİRİLMEYECEK"
        )

    print("=" * 90)

    players = load_json(
        PLAYERS_FILE
    )

    classified = load_json(
        CLASSIFIED_FILE
    )

    groups = [
        group
        for group in classified.get(
            "groups",
            [],
        )
        if (
            group.get(
                "new_classification"
            )
            == "PROBABLY_DUPLICATE_PLAYER"
        )
    ]

    print(
        "İncelenecek grup:",
        len(groups),
    )

    player_index = {
        str(
            player.get("id")
        ): player
        for player in players
        if player.get("id")
    }

    ids_to_remove = set()

    report_groups = []

    counters = {
        "groups": len(groups),
        "merged": 0,
        "manual_q_duplicate": 0,
        "manual_group_size": 0,
        "record_not_found": 0,
        "birthdate_mismatch": 0,
        "clubs_added": 0,
        "reserve_filtered": 0,
        "alias_duplicates_skipped": 0,
        "positions_added": 0,
        "trophies_added": 0,
        "records_to_remove": 0,
    }

    for index, group in enumerate(
        groups,
        start=1,
    ):

        group_players = (
            group.get(
                "players",
                [],
            )
        )

        tm_id = group.get(
            "transfermarkt_id"
        )

        print(
            "\n" + "=" * 90
        )

        print(
            f"{index} / {len(groups)}"
        )

        print(
            "Transfermarkt ID:",
            tm_id,
        )

        if len(group_players) != 2:

            print(
                "MANUEL: Grup 2 kayıt değil."
            )

            counters[
                "manual_group_size"
            ] += 1

            report_groups.append({
                "transfermarkt_id":
                    tm_id,
                "status":
                    "MANUAL_GROUP_SIZE",
            })

            continue

        p1_id = str(
            group_players[0].get(
                "id"
            )
        )

        p2_id = str(
            group_players[1].get(
                "id"
            )
        )

        p1 = player_index.get(
            p1_id
        )

        p2 = player_index.get(
            p2_id
        )

        if not p1 or not p2:

            print(
                "ATLANDI: players.json kaydı bulunamadı."
            )

            counters[
                "record_not_found"
            ] += 1

            continue

        p1_tm_missing = (
            p1_id.startswith(
                "tm_missing_"
            )
        )

        p2_tm_missing = (
            p2_id.startswith(
                "tm_missing_"
            )
        )

        # Q + Q
        if (
            not p1_tm_missing
            and not p2_tm_missing
        ):

            print(
                "MANUEL Q DUPLICATE"
            )

            print(
                "PLAYER 1:",
                p1.get("name"),
                "|",
                p1_id,
            )

            print(
                "PLAYER 2:",
                p2.get("name"),
                "|",
                p2_id,
            )

            print(
                "Bu iki kayıt otomatik değiştirilmeyecek."
            )

            counters[
                "manual_q_duplicate"
            ] += 1

            report_groups.append({
                "transfermarkt_id":
                    tm_id,
                "status":
                    "MANUAL_Q_DUPLICATE",
                "player_1_id":
                    p1_id,
                "player_2_id":
                    p2_id,
            })

            continue

        # tm_missing + tm_missing
        if (
            p1_tm_missing
            and p2_tm_missing
        ):

            print(
                "MANUEL: İki kayıt da tm_missing."
            )

            counters[
                "manual_group_size"
            ] += 1

            continue

        if p1_tm_missing:
            duplicate_player = p1
            main_player = p2
        else:
            duplicate_player = p2
            main_player = p1

        main_id = str(
            main_player.get("id")
        )

        duplicate_id = str(
            duplicate_player.get(
                "id"
            )
        )

        print(
            "ANA KAYIT:"
        )

        print(
            " ",
            main_player.get(
                "name"
            ),
            "|",
            main_id,
        )

        print(
            "DUPLICATE:"
        )

        print(
            " ",
            duplicate_player.get(
                "name"
            ),
            "|",
            duplicate_id,
        )

        # Doğum tarihi güvenlik kontrolü
        birth_main = str(
            main_player.get(
                "birthDate"
            )
            or ""
        ).strip()

        birth_duplicate = str(
            duplicate_player.get(
                "birthDate"
            )
            or ""
        ).strip()

        if (
            birth_main
            and birth_duplicate
            and birth_main
            != birth_duplicate
        ):

            print(
                "ATLANDI: DOĞUM TARİHLERİ FARKLI"
            )

            counters[
                "birthdate_mismatch"
            ] += 1

            report_groups.append({
                "transfermarkt_id":
                    tm_id,
                "status":
                    "BIRTHDATE_MISMATCH",
                "main_id":
                    main_id,
                "duplicate_id":
                    duplicate_id,
            })

            continue

        changes = merge_player(
            main_player,
            duplicate_player,
        )

        ids_to_remove.add(
            duplicate_id
        )

        counters[
            "merged"
        ] += 1

        counters[
            "clubs_added"
        ] += len(
            changes[
                "clubs_added"
            ]
        )

        counters[
            "alias_duplicates_skipped"
        ] += len(
            changes[
                "clubs_skipped_alias"
            ]
        )

        counters[
            "reserve_filtered"
        ] += len(
            changes[
                "clubs_skipped_reserve"
            ]
        )

        counters[
            "positions_added"
        ] += len(
            changes[
                "positions_added"
            ]
        )

        counters[
            "trophies_added"
        ] += len(
            changes[
                "trophies_added"
            ]
        )

        print()

        print(
            "EKLENECEK KULÜPLER:"
        )

        if changes[
            "clubs_added"
        ]:
            for club in changes[
                "clubs_added"
            ]:
                print(
                    "  +",
                    club,
                )
        else:
            print(
                "  Yok"
            )

        print(
            "ALIAS / AYNI KULÜP DİYE ATLANAN:"
        )

        if changes[
            "clubs_skipped_alias"
        ]:
            for club in changes[
                "clubs_skipped_alias"
            ]:
                print(
                    "  =",
                    club,
                )
        else:
            print(
                "  Yok"
            )

        print(
            "REZERV / GENÇ TAKIM DİYE ATLANAN:"
        )

        if changes[
            "clubs_skipped_reserve"
        ]:
            for club in changes[
                "clubs_skipped_reserve"
            ]:
                print(
                    "  X",
                    club,
                )
        else:
            print(
                "  Yok"
            )

        print(
            "SİLİNECEK DUPLICATE KAYIT:",
            duplicate_id,
        )

        report_groups.append({
            "transfermarkt_id":
                tm_id,
            "status":
                "READY_TO_MERGE",
            "main_player": {
                "id":
                    main_id,
                "name":
                    main_player.get(
                        "name"
                    ),
            },
            "duplicate_player": {
                "id":
                    duplicate_id,
                "name":
                    duplicate_player.get(
                        "name"
                    ),
            },
            "changes":
                changes,
        })

    counters[
        "records_to_remove"
    ] = len(
        ids_to_remove
    )

    backup_path = None

    # =====================================================
    # APPLY
    # =====================================================

    if apply_changes:

        if ids_to_remove:

            backup_path = (
                create_backup()
            )

            print(
                "\nBackup:",
                backup_path,
            )

            players = [
                player
                for player in players
                if str(
                    player.get(
                        "id"
                    )
                )
                not in ids_to_remove
            ]

            atomic_save_json(
                PLAYERS_FILE,
                players,
            )

            print(
                "players.json kaydedildi."
            )

        else:
            print(
                "Uygulanacak değişiklik yok."
            )

    # =====================================================
    # REPORT
    # =====================================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_file = (
        REPORT_DIR
        / (
            "duplicate_merge_report_v2_"
            f"{timestamp}.json"
        )
    )

    report = {
        "mode":
            "APPLY"
            if apply_changes
            else "DRY_RUN",

        "source":
            str(
                CLASSIFIED_FILE
            ),

        "players_file":
            str(
                PLAYERS_FILE
            ),

        "backup":
            str(
                backup_path
            )
            if backup_path
            else None,

        "counters":
            counters,

        "groups":
            report_groups,
    }

    atomic_save_json(
        report_file,
        report,
    )

    print(
        "\n" + "=" * 90
    )

    print(
        "TAMAMLANDI"
    )

    print(
        "Mod:",
        "APPLY"
        if apply_changes
        else "DRY RUN",
    )

    print(
        "İncelenen grup:",
        counters[
            "groups"
        ],
    )

    print(
        "Birleştirilmeye uygun:",
        counters[
            "merged"
        ],
    )

    print(
        "Q + Q manuel:",
        counters[
            "manual_q_duplicate"
        ],
    )

    print(
        "Doğum tarihi uyuşmazlığı:",
        counters[
            "birthdate_mismatch"
        ],
    )

    print(
        "Eklenecek kulüp:",
        counters[
            "clubs_added"
        ],
    )

    print(
        "Alias nedeniyle atlanan:",
        counters[
            "alias_duplicates_skipped"
        ],
    )

    print(
        "Rezerv/genç filtrelenen:",
        counters[
            "reserve_filtered"
        ],
    )

    print(
        "Eklenecek position:",
        counters[
            "positions_added"
        ],
    )

    print(
        "Eklenecek trophy:",
        counters[
            "trophies_added"
        ],
    )

    print(
        "Silinecek duplicate kayıt:",
        counters[
            "records_to_remove"
        ],
    )

    print(
        "Rapor:",
        report_file,
    )

    if not apply_changes:

        print()
        print(
            "BU SADECE DRY RUN'DI."
        )

        print(
            "players.json değiştirilmedi."
        )


if __name__ == "__main__":
    main()