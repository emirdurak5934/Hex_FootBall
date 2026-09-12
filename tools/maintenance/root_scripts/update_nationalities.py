import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import time

from api import get_player_national_team

from database import (
    load_players,
    save_players,
    write_log
)


WAIT_SECONDS = 1

players = load_players()

print(f"Kontrol edilecek oyuncu: {len(players)}")

updated = 0
unchanged = 0
failed = 0


for index, player in enumerate(players[2040:], start=2041):

    player_id = player["id"]
    player_name = player["name"]

    print("\n------------------------------")
    print(f"{index}/{len(players)} - {player_name}")

    try:
        national_teams = get_player_national_team(
            player_id
        )

        if not national_teams:
            print("A milli takım bilgisi bulunamadı.")
            failed += 1

            write_log(
                f"NATIONAL TEAM YOK | "
                f"{player_name} | {player_id}"
            )

            time.sleep(WAIT_SECONDS)
            continue


        print(
            "Bulunan milli takım:",
            national_teams
        )

        national_team = national_teams[0]


        country = (
            national_team
            .replace(
                " men's national association football team",
                ""
            )
            .replace(
                " men's national football team",
                ""
            )
            .replace(
                " national association football team",
                ""
            )
            .replace(
                " national football team",
                ""
            )
            .strip()
        )


        old_value = player.get(
            "nationality",
            ""
        )

        print("Eski:", old_value)
        print("Yeni:", country)


        if old_value != country:

            player["nationality"] = country

            # ÖNEMLİ:
            # Her oyuncudan sonra hemen JSON'a kaydet
            save_players(players)

            updated += 1

            print("GÜNCELLENDİ VE KAYDEDİLDİ")

            write_log(
                f"NATIONAL TEAM UPDATE | "
                f"{player_name} | "
                f"{old_value} -> {country}"
            )

        else:

            unchanged += 1
            print("Değişiklik yok.")


    except Exception as error:

        print("Hata:", error)

        failed += 1

        write_log(
            f"NATIONAL TEAM HATA | "
            f"{player_name} | "
            f"{player_id} | "
            f"{error}"
        )


    time.sleep(WAIT_SECONDS)


print("\n==============================")
print("MİLLİ TAKIM KONTROLÜ TAMAMLANDI")
print("==============================")
print("Güncellenen:", updated)
print("Değişmeyen:", unchanged)
print("Bulunamayan / hata:", failed)
print("==============================")