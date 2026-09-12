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
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


PLAYERS_FILE = Path("data/players.json")
REPORT_DIR = Path("data")


# ============================================================
# WEB DOĞRULAMASI SONRASI KESİN KARARLAR
# ============================================================

# Bu synthetic kayıtlar yanlış/kirli duplicate.
# Hiçbir bilgileri Q kaydına aktarılmayacak.
DELETE_SYNTHETIC_IDS = {
    "rm_missing_81": "Laurent Blanc / TM 3113",
    "tm_missing_15420": "Alex Rodrigo Dias da Costa / TM 15420",
    "rm_missing_35": "Edgar Davids / TM 5758",
    "tm_missing_18734": "Gilberto da Silva Melo / TM 18734",
    "tm_missing_156501": "Felipe Augusto de Almeida Monteiro / TM 156501",
}


# TM 125165 gerçekte Jesús Manuel Corona'ya ait.
#
# Q936583 = İspanyol Corona
# Bu oyuncuyu SİLMİYORUZ.
# Sadece yanlış Transfermarkt ID'sini kaldırıyoruz.
WRONG_TM_ASSIGNMENTS = {
    "Q936583": "125165",
}


def load_players():
    with PLAYERS_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def create_backup():
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup = Path(
        "data/"
        "players_before_final_synthetic_fix_"
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
        dir=str(PLAYERS_FILE.parent),
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

    players = load_players()

    original_count = len(players)

    print()
    print("=" * 78)
    print("FINAL SYNTHETIC DUPLICATE FIX")
    print("Mod:", mode)
    print("=" * 78)

    print()
    print("Toplam oyuncu:", original_count)

    by_id = {
        str(player.get("id")): player
        for player in players
        if player.get("id") is not None
    }

    # ========================================================
    # 1. SİLİNECEK 5 SYNTHETIC KAYDI DOĞRULA
    # ========================================================

    confirmed_delete_ids = []

    print()
    print("=" * 78)
    print("SİLİNECEK SYNTHETIC KAYITLAR")
    print("=" * 78)

    for player_id, description in DELETE_SYNTHETIC_IDS.items():

        player = by_id.get(player_id)

        if not player:
            print()
            print(
                "BULUNAMADI:",
                player_id,
                "|",
                description
            )
            continue

        confirmed_delete_ids.append(
            player_id
        )

        print()
        print("ID:", player_id)
        print("Ad:", player.get("name"))
        print(
            "Transfermarkt ID:",
            player.get("transfermarkt_id")
        )
        print(
            "Kulüpler:",
            player.get("clubs", [])
        )
        print(
            "Karar:",
            "SYNTHETIC KAYIT SİLİNECEK"
        )
        print(
            "NOT: Hiçbir veri Q kaydına aktarılmayacak."
        )

    # ========================================================
    # 2. YANLIŞ TM ID ATAMASINI DOĞRULA
    # ========================================================

    tm_fixes = []

    print()
    print("=" * 78)
    print("YANLIŞ TRANSFERMARKT ID ATAMALARI")
    print("=" * 78)

    for player_id, expected_wrong_tm in WRONG_TM_ASSIGNMENTS.items():

        player = by_id.get(player_id)

        if not player:
            print()
            print(
                "BULUNAMADI:",
                player_id
            )
            continue

        current_tm = str(
            player.get("transfermarkt_id")
            or ""
        ).strip()

        print()
        print("ID:", player_id)
        print("Ad:", player.get("name"))
        print(
            "Doğum:",
            player.get("birthDate")
        )
        print(
            "Milliyet:",
            player.get("nationality")
        )
        print(
            "Mevcut TM ID:",
            current_tm
        )

        if current_tm != expected_wrong_tm:
            print(
                "ATLANDI: Beklenen yanlış TM ID artık bu kayıtta yok."
            )
            continue

        tm_fixes.append({
            "player_id": player_id,
            "name": player.get("name"),
            "old_transfermarkt_id": current_tm,
            "new_transfermarkt_id": None,
        })

        print(
            "Karar:",
            f"transfermarkt_id {current_tm} kaldırılacak."
        )
        print(
            "Oyuncu kaydı SİLİNMEYECEK."
        )

    # ========================================================
    # 3. TM 125165'İN DİĞER KAYDINI GÖSTER
    # ========================================================

    print()
    print("=" * 78)
    print("TM 125165 KONTROLÜ")
    print("=" * 78)

    corona_records = []

    for player in players:
        tm_id = str(
            player.get("transfermarkt_id")
            or ""
        ).strip()

        if tm_id == "125165":
            corona_records.append(
                player
            )

    for player in corona_records:
        print()
        print(
            "ID:",
            player.get("id")
        )
        print(
            "Ad:",
            player.get("name")
        )
        print(
            "Doğum:",
            player.get("birthDate")
        )
        print(
            "Milliyet:",
            player.get("nationality")
        )
        print(
            "Kulüpler:",
            player.get("clubs", [])
        )

    print()
    print(
        "TM 125165 kullanan kayıt:",
        len(corona_records)
    )

    # ========================================================
    # DRY RUN ÖZET
    # ========================================================

    print()
    print("=" * 78)
    print("PLAN")
    print("=" * 78)

    print(
        "Silinecek synthetic:",
        len(confirmed_delete_ids)
    )

    print(
        "TM ID kaldırılacak Q kaydı:",
        len(tm_fixes)
    )

    print(
        "Beklenen oyuncu sayısı:",
        original_count
        - len(confirmed_delete_ids)
    )

    # ========================================================
    # APPLY
    # ========================================================

    backup = None

    if args.apply:

        if (
            confirmed_delete_ids
            or tm_fixes
        ):
            backup = create_backup()

            print()
            print(
                "Backup:",
                backup
            )

        delete_set = set(
            confirmed_delete_ids
        )

        # 5 synthetic kaydı kaldır.
        players = [
            player
            for player in players
            if str(
                player.get("id")
            ) not in delete_set
        ]

        # Q936583'ten yanlış TM ID'yi kaldır.
        for fix in tm_fixes:

            for player in players:

                if str(
                    player.get("id")
                ) != fix["player_id"]:
                    continue

                current_tm = str(
                    player.get(
                        "transfermarkt_id"
                    )
                    or ""
                ).strip()

                if (
                    current_tm
                    == fix[
                        "old_transfermarkt_id"
                    ]
                ):
                    player.pop(
                        "transfermarkt_id",
                        None
                    )

                    print()
                    print(
                        "TM ID KALDIRILDI:",
                        fix["player_id"],
                        fix["name"],
                        "|",
                        fix["old_transfermarkt_id"]
                    )

                break

        atomic_save(players)

        print()
        print(
            "players.json kaydedildi."
        )

    # ========================================================
    # RAPOR
    # ========================================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_file = REPORT_DIR / (
        "final_synthetic_fix_report_"
        f"{timestamp}.json"
    )

    report = {
        "mode": mode,
        "players_before": original_count,
        "players_after": (
            len(players)
            if args.apply
            else original_count
            - len(confirmed_delete_ids)
        ),
        "deleted_synthetic_ids":
            confirmed_delete_ids,
        "tm_id_fixes":
            tm_fixes,
        "tm_125165_records_before":
            [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "birthDate":
                        p.get("birthDate"),
                    "nationality":
                        p.get("nationality"),
                }
                for p in corona_records
            ],
        "backup":
            str(backup)
            if backup
            else None,
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
    print("=" * 78)
    print("TAMAMLANDI")
    print("=" * 78)

    print(
        "Mod:",
        mode
    )

    print(
        "Silinecek/Silinen synthetic:",
        len(confirmed_delete_ids)
    )

    print(
        "TM ID düzeltmesi:",
        len(tm_fixes)
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