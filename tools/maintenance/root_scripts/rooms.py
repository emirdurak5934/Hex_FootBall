import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import random
import string


# ==================================================
# ODALAR
#
# {
#     "ABC123": {
#         "players": {
#             socket_id: 1,
#             socket_id: 2
#         },
#         "started": False
#     }
# }
# ==================================================

rooms = {}


# ==================================================
# ODA KODU ÜRET
# ==================================================

def generate_room_code():

    while True:

        code = "".join(
            random.choices(
                string.ascii_uppercase
                +
                string.digits,
                k=6
            )
        )

        if code not in rooms:

            return code


# ==================================================
# ODA OLUŞTUR
# ==================================================

def create_room(
    socket_id
):

    room_code = generate_room_code()

    rooms[
        room_code
    ] = {

        "players": {
            socket_id: 1
        },

        "started":
            False

    }

    return room_code


# ==================================================
# ODAYA KATIL
# ==================================================

def add_player_to_room(
    room_code,
    socket_id
):

    room_code = str(
        room_code
    ).strip().upper()

    if room_code not in rooms:

        return {
            "success": False,
            "error": "Oda bulunamadı."
        }

    room = rooms[
        room_code
    ]

    if len(
        room["players"]
    ) >= 2:

        return {
            "success": False,
            "error": "Oda dolu."
        }

    if socket_id in room[
        "players"
    ]:

        return {
            "success": False,
            "error": "Zaten bu odadasın."
        }

    room[
        "players"
    ][
        socket_id
    ] = 2

    room[
        "started"
    ] = True

    return {
        "success": True,
        "player_number": 2
    }


# ==================================================
# ODAYI BUL
# ==================================================

def find_player_room(
    socket_id
):

    for room_code, room in rooms.items():

        if socket_id in room[
            "players"
        ]:

            return room_code

    return None


# ==================================================
# OYUNCU NUMARASI
# ==================================================

def get_player_number(
    room_code,
    socket_id
):

    room = rooms.get(
        room_code
    )

    if not room:

        return None

    return (
        room[
            "players"
        ]
        .get(
            socket_id
        )
    )


# ==================================================
# ODA BİLGİSİ
# ==================================================

def get_room(
    room_code
):

    return rooms.get(
        room_code
    )


# ==================================================
# OYUNCUYU ODADAN ÇIKAR
# ==================================================

def remove_player(
    socket_id
):

    room_code = find_player_room(
        socket_id
    )

    if not room_code:

        return None

    room = rooms[
        room_code
    ]

    player_number = (
        room[
            "players"
        ]
        .pop(
            socket_id,
            None
        )
    )

    # ==================================================
    # ODA BOŞSA SİL
    # ==================================================

    if not room[
        "players"
    ]:

        del rooms[
            room_code
        ]

    else:

        room[
            "started"
        ] = False

    return {

        "room_code":
            room_code,

        "player_number":
            player_number

    }