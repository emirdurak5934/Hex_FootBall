import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import time

from api import (
    get_team_players,
    get_player_full_history
)

from database import (
    load_players,
    merge_player,
    write_log
)


TEAMS = [
    {
        "name": "Galatasaray",
        "id": "Q495299"
    },
    {
        "name": "Fenerbahçe",
        "id": "Q6601875"
    },
    {
        "name": "Beşiktaş",
        "id": "Q172567"
    },
    {
        "name": "Trabzonspor",
        "id": "Q192641"
    }
]

START_YEAR = 1990
WAIT_SECONDS = 1





all_players = load_players()

print(
    f"Veritabanındaki toplam oyuncu sayısı: "
    f"{len(all_players)}"
)


for team_index, team in enumerate(TEAMS, start=1):

    team_name = team["name"]
    team_id = team["id"]

    print("\n======================================")
    print(
        f"ZENGİNLEŞTİRME {team_index}/{len(TEAMS)}: "
        f"{team_name}"
    )
    print("======================================")

    try:
        team_players = get_team_players(
            team_id,
            START_YEAR
        )

    except Exception as error:
        print(f"{team_name} oyuncuları alınamadı.")
        print(error)

        write_log(
            f"ENRICH TAKIM HATA | "
            f"{team_name} | {error}"
        )

        continue


    team_player_ids = {
        player["id"]
        for player in team_players
    }


    players_to_update = [
        player
        for player in all_players
        if player["id"] in team_player_ids
    ]


    print(
        f"Güncellenecek oyuncu: "
        f"{len(players_to_update)}"
    )


    updated = 0
    failed = 0


    for player_index, player in enumerate(
        players_to_update,
        start=1
    ):

        player_id = player["id"]
        player_name = player["name"]

        print("\n------------------------------")
        print(
            f"{team_name} | "
            f"{player_index}/{len(players_to_update)}"
        )
        print(
            f"Zenginleştiriliyor: {player_name}"
        )

        try:
            new_data = get_player_full_history(
                player_id,
                player_name
            )

            if not new_data:

                print(
                    "Yeni veri alınamadı. Atlandı."
                )

                write_log(
                    f"ENRICH ATLANDI | "
                    f"{team_name} | "
                    f"{player_name} | veri yok"
                )

                failed += 1

                time.sleep(
                    WAIT_SECONDS
                )

                continue


            print(
                "Bulunan kulüp sayısı:",
                len(new_data["clubs"])
            )

            print(
                "Kulüpler:",
                new_data["clubs"]
            )


            success = merge_player(
                player_id,
                new_data
            )


            if success:

                updated += 1

                write_log(
                    f"ENRICH OK | "
                    f"{team_name} | "
                    f"{player_name} | "
                    f"{len(new_data['clubs'])} kulüp"
                )

            else:

                failed += 1

                write_log(
                    f"ENRICH HATA | "
                    f"{team_name} | "
                    f"{player_name} | "
                    f"merge başarısız"
                )


        except Exception as error:

            print("Hata:")
            print(error)

            write_log(
                f"ENRICH HATA | "
                f"{team_name} | "
                f"{player_name} | "
                f"{player_id} | "
                f"{error}"
            )

            failed += 1


        time.sleep(
            WAIT_SECONDS
        )


    print("\n======================================")
    print(
        f"{team_name} ZENGİNLEŞTİRME TAMAMLANDI"
    )
    print(
        f"Güncellenen: {updated}"
    )
    print(
        f"Başarısız: {failed}"
    )
    print("======================================")


print("\n######################################")
print("TÜM TAKIMLARIN ZENGİNLEŞTİRMESİ BİTTİ!")
print("######################################")