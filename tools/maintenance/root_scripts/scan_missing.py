import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json
from collections import Counter
from pathlib import Path


PLAYERS_FILE = Path("data/players.json")
REPORT_FILE = Path("data/missing_players_report.json")


def is_empty(value):
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, (list, dict)):
        return len(value) == 0

    return False


with PLAYERS_FILE.open(
    "r",
    encoding="utf-8"
) as file:

    players = json.load(file)


print(f"\nToplam oyuncu: {len(players)}")


field_counts = Counter()

players_with_missing = []

changed = 0


for index, player in enumerate(
    players,
    start=1
):

    missing = []

    # ==========================
    # TEMEL ALANLAR
    # ==========================

    if is_empty(
        player.get("birthDate")
    ):
        missing.append(
            "birthDate"
        )

    if is_empty(
        player.get("positions")
    ):
        missing.append(
            "positions"
        )

    if is_empty(
        player.get("clubs")
    ):
        missing.append(
            "clubs"
        )

    if is_empty(
        player.get("nationality")
    ):
        missing.append(
            "nationality"
        )

    if is_empty(
        player.get("transfermarkt_id")
    ):
        missing.append(
            "transfermarkt_id"
        )

    # ==========================
    # KUPALAR
    # ==========================

    trophies_checked = (
        player.get(
            "team_trophies_checked_v2"
        )
        is True
    )

    if not trophies_checked:
        missing.append(
            "trophies_check"
        )

    # ==========================
    # ENRICHMENT FLAG
    # ==========================

    enrichment_fields = {
        "birthDate",
        "positions",
        "clubs",
        "nationality",
    }

    needs_enrichment = any(
        field in enrichment_fields
        for field in missing
    )

    if needs_enrichment:

        if (
            player.get(
                "needs_enrichment"
            )
            is not True
        ):

            player[
                "needs_enrichment"
            ] = True

            changed += 1

    # ==========================
    # RAPOR
    # ==========================

    if missing:

        for field in missing:
            field_counts[field] += 1

        players_with_missing.append(
            {
                "index": index,
                "id": player.get(
                    "id",
                    ""
                ),
                "name": player.get(
                    "name",
                    ""
                ),
                "transfermarkt_id":
                    player.get(
                        "transfermarkt_id",
                        ""
                    ),
                "missing": missing,
            }
        )


# ==============================
# PLAYERS.JSON KAYDET
# ==============================

with PLAYERS_FILE.open(
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        players,
        file,
        ensure_ascii=False,
        indent=2
    )


# ==============================
# RAPOR
# ==============================

report = {
    "total_players":
        len(players),

    "players_with_missing":
        len(players_with_missing),

    "needs_enrichment_added":
        changed,

    "missing_counts":
        dict(field_counts),

    "players":
        players_with_missing,
}


with REPORT_FILE.open(
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        report,
        file,
        ensure_ascii=False,
        indent=2
    )


# ==============================
# TERMINAL RAPORU
# ==============================

print("\n==============================")
print("DATABASE KONTROL RAPORU")
print("==============================")

print(
    f"Toplam oyuncu: "
    f"{len(players)}"
)

print(
    f"Eksiği bulunan oyuncu: "
    f"{len(players_with_missing)}"
)

print(
    f"needs_enrichment eklenen: "
    f"{changed}"
)

print("\nEksik alanlar:\n")

for field, count in (
    field_counts.most_common()
):

    print(
        f"{field:<25} {count}"
    )


print(
    "\nDetaylı rapor:"
)

print(
    REPORT_FILE
)