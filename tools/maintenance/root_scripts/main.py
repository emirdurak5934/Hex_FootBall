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
    get_player_by_id
)

from database import (
    add_player,
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







for team_index, team in enumerate(TEAMS, start=1):

    team_name = team["name"]
    team_id = team["id"]

    print("\n======================================")
    print(
        f"TAKIM {team_index}/{len(TEAMS)}: "
        f"{team_name}"
    )
    print("======================================")

    try:
        players = get_team_players(
            team_id,
            START_YEAR
        )

    except Exception as error:
        print(
            f"{team_name} oyuncuları alınamadı:"
        )
        print(error)

        write_log(
            f"TAKIM HATA | {team_name} | {error}"
        )

        continue

    print(
        f"{team_name} için bulunan oyuncu: "
        f"{len(players)}"
    )

    for player_index, player in enumerate(
        players,
        start=1
    ):

        player_id = player["id"]
        player_name = player["name"]

        print("\n------------------------------")
        print(
            f"{team_name} | "
            f"{player_index}/{len(players)}"
        )
        print(f"İşleniyor: {player_name}")
        print(f"ID: {player_id}")

        try:
            full_player = get_player_by_id(
                player_id
            )

            if not full_player:
                print(
                    "Oyuncu verisi alınamadı. Atlandı."
                )

                write_log(
                    f"ATLANDI | {team_name} | "
                    f"{player_name} | veri alınamadı"
                )

                time.sleep(WAIT_SECONDS)
                continue

            if full_player["name"].startswith("Q"):
                print(
                    "İsim bilgisi eksik. Atlandı."
                )

                write_log(
                    f"ATLANDI | {team_name} | "
                    f"{player_id} | isim eksik"
                )

                time.sleep(WAIT_SECONDS)
                continue

            if not full_player["birthDate"]:
                print(
                    "Doğum tarihi eksik. Atlandı."
                )

                write_log(
                    f"ATLANDI | {team_name} | "
                    f"{player_name} | "
                    f"doğum tarihi eksik"
                )

                time.sleep(WAIT_SECONDS)
                continue

            added = add_player(
                full_player
            )

            if added:
                write_log(
                    f"EKLENDI | {team_name} | "
                    f"{player_name} | {player_id}"
                )

            else:
                write_log(
                    f"ZATEN VAR | {team_name} | "
                    f"{player_name} | {player_id}"
                )

        except Exception as error:

            print("Oyuncu işlenirken hata:")
            print(error)

            write_log(
                f"HATA | {team_name} | "
                f"{player_name} | "
                f"{player_id} | {error}"
            )

        time.sleep(WAIT_SECONDS)

    print("\n======================================")
    print(f"{team_name} TAMAMLANDI!")
    print("======================================")

    write_log(
        f"TAKIM TAMAMLANDI | {team_name}"
    )


print("\n######################################")
print("TÜM TAKIMLAR TAMAMLANDI!")
print("######################################")