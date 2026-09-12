import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Verify both Socket.IO clients receive identical extended board payloads."""

from collections import Counter
import json

import app


def event_payload(events, name):
    matches = [event for event in events if event["name"] == name]
    if not matches:
        raise AssertionError(f"Missing Socket.IO event: {name}")
    return matches[-1]["args"][0]


def main():
    first = app.socketio.test_client(app.app)
    second = app.socketio.test_client(app.app)
    try:
        first.emit("create_room")
        room_code = event_payload(first.get_received(), "room_created")["room_code"]
        second.emit("join_game_room", {"room_code": room_code})
        first_ready = event_payload(first.get_received(), "game_ready")
        second_ready = event_payload(second.get_received(), "game_ready")
        first_board = first_ready["state"]["conditions"]
        second_board = second_ready["state"]["conditions"]

        room = app.online_rooms[room_code]
        room["state"]["finished"] = True
        first.emit("request_rematch")
        first.get_received()
        second.get_received()
        second.emit("request_rematch")
        first_rematch = event_payload(first.get_received(), "rematch_started")
        second_rematch = event_payload(second.get_received(), "rematch_started")
        first_new_board = first_rematch["state"]["conditions"]
        second_new_board = second_rematch["state"]["conditions"]

        result = {
            "room_code": room_code,
            "initial_same_for_both_clients": first_board == second_board,
            "initial_count": len(first_board),
            "initial_types": dict(Counter(item["type"] for item in first_board)),
            "rematch_same_for_both_clients": first_new_board == second_new_board,
            "rematch_count": len(first_new_board),
            "rematch_types": dict(Counter(item["type"] for item in first_new_board)),
            "rematch_is_new_board": first_new_board != first_board,
            "initial_continent": [
                item for item in first_board if item["type"] == "continent"
            ],
            "rematch_continent": [
                item for item in first_new_board if item["type"] == "continent"
            ],
            "new_types_serialized": all(
                criterion_type in {item["type"] for item in first_new_board}
                for criterion_type in (
                    "position", "league", "birth_decade", "continent"
                )
            ),
        }
        if not all((
            result["initial_same_for_both_clients"],
            result["rematch_same_for_both_clients"],
            result["rematch_is_new_board"],
            result["new_types_serialized"],
            result["initial_count"] == 31,
            result["rematch_count"] == 31,
            len(result["initial_continent"]) == 1,
            len(result["rematch_continent"]) == 1,
            all(
                item.get("label") and item.get("value") in {
                    "Europe", "South America", "Africa", "Asia"
                }
                for item in (
                    result["initial_continent"] + result["rematch_continent"]
                )
            ),
        )):
            raise AssertionError(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        if first.is_connected():
            first.disconnect()
        if second.is_connected():
            second.disconnect()


if __name__ == "__main__":
    main()
