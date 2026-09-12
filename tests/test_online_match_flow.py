import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Regression test for authoritative online Possession start/turn/timer flow."""

import app


def events_by_name(client, name):
    return [event for event in client.get_received() if event["name"] == name]


def last_payload(events):
    if not events:
        raise AssertionError("Expected Socket.IO event was not received")
    return events[-1]["args"][0]


def matching_player_id(condition):
    key = app.criterion_engine._key(condition)
    player_index = next(iter(app.criterion_engine.answer_sets[key]))
    return str(app.players[player_index]["id"])


def first_empty_move(state):
    index = state["owners"].index(0)
    return {
        "index": index,
        "player_id": matching_player_id(state["conditions"][index]),
    }


def main():
    first = app.socketio.test_client(app.app)
    second = app.socketio.test_client(app.app)
    try:
        first.emit("create_room")
        created = last_payload(events_by_name(first, "room_created"))
        room_code = created["room_code"]
        room = app.online_rooms[room_code]

        waiting_times = dict(room["state"]["times"])
        first.emit("submit_move", {"index": 0, "player_id": "missing"})
        waiting_rejection = last_payload(events_by_name(first, "move_result"))
        app.socketio.sleep(1.1)

        assert not room["state"]["started"]
        assert room["state"]["times"] == waiting_times == {"1": 240, "2": 240}
        assert not waiting_rejection["accepted"]
        assert room["state"]["owners"] == [0] * 31

        second.emit("join_game_room", {"room_code": room_code})
        second_events = second.get_received()
        first_ready = last_payload(events_by_name(first, "game_ready"))
        second_ready = last_payload([
            event for event in second_events if event["name"] == "game_ready"
        ])
        state = first_ready["state"]

        assert state == second_ready["state"]
        assert state["started"] and not state["finished"]
        assert state["active_player"] == 1
        assert state["remaining_times"] == {"1": 240, "2": 240}
        assert state["scores"] == {"1": 0, "2": 0}

        app.socketio.sleep(1.1)
        first_tick = last_payload(events_by_name(first, "game_state"))
        second_tick = last_payload(events_by_name(second, "game_state"))
        assert first_tick == second_tick
        assert first_tick["remaining_times"]["1"] < 240
        assert first_tick["remaining_times"]["2"] == 240

        first.emit("submit_move", first_empty_move(state))
        first_move_events = first.get_received()
        first_move_result = last_payload([
            event for event in first_move_events if event["name"] == "move_result"
        ])
        first_answer_notice = last_payload([
            event for event in first_move_events if event["name"] == "online_answer"
        ])
        first_after = last_payload([
            event for event in first_move_events if event["name"] == "game_state"
        ])
        second_move_events = second.get_received()
        second_after = last_payload([
            event for event in second_move_events if event["name"] == "game_state"
        ])
        second_answer_notice = last_payload([
            event for event in second_move_events if event["name"] == "online_answer"
        ])
        assert first_move_result["accepted"] and first_move_result["correct"]
        assert first_answer_notice == second_answer_notice
        assert first_answer_notice["duration_ms"] == 2000
        assert first_answer_notice["player_name"]
        assert first_answer_notice["hex_index"] == first_move_result["source"]
        assert first_answer_notice["notice_id"]
        assert first_after["latest_answer"] == first_answer_notice
        assert first_after == second_after
        assert first_after["active_player"] == 2
        assert any(first_after["owners"])

        first.emit("submit_move", first_empty_move({
            **first_after, "conditions": state["conditions"]
        }))
        wrong_turn = last_payload(events_by_name(first, "move_result"))
        assert not wrong_turn["accepted"]

        player_one_time = first_after["remaining_times"]["1"]
        app.socketio.sleep(1.1)
        second_turn_tick = last_payload(events_by_name(second, "game_state"))
        first.get_received()
        assert second_turn_tick["remaining_times"]["1"] == player_one_time
        assert second_turn_tick["remaining_times"]["2"] < 240

        second.emit("submit_move", first_empty_move({
            **second_turn_tick, "conditions": state["conditions"]
        }))
        second_move_events = second.get_received()
        second_move_result = last_payload([
            event for event in second_move_events if event["name"] == "move_result"
        ])
        second_after = last_payload([
            event for event in second_move_events if event["name"] == "game_state"
        ])
        first_after_second = last_payload(events_by_name(first, "game_state"))
        assert second_move_result["accepted"] and second_move_result["correct"]
        assert second_after == first_after_second
        assert second_after["active_player"] == 1

        room["state"]["finished"] = True
        first.emit("request_rematch")
        first_status = last_payload(events_by_name(first, "rematch_status"))
        second.get_received()
        assert first_status["accepted"] and not first_status["started"]
        assert room["state"]["finished"]

        second.emit("request_rematch")
        first_rematch = last_payload(events_by_name(first, "rematch_started"))
        second_rematch = last_payload(events_by_name(second, "rematch_started"))
        assert first_rematch["state"] == second_rematch["state"]
        assert first_rematch["state"]["started"]
        assert first_rematch["state"]["remaining_times"] == {"1": 240, "2": 240}

        second.disconnect()
        disconnect_events = first.get_received()
        disconnect_state = last_payload([
            event for event in disconnect_events if event["name"] == "game_state"
        ])
        opponent_left = last_payload([
            event for event in disconnect_events if event["name"] == "opponent_left"
        ])
        assert disconnect_state["finished"]
        assert disconnect_state["winner"] == 1
        assert opponent_left["match_finished"]

        print({
            "waiting_board_locked_by_server": True,
            "waiting_timer_unchanged": True,
            "shared_game_ready_state": True,
            "server_authoritative_turns": True,
            "active_player_timer_only": True,
            "two_party_rematch": True,
            "disconnect_forfeit": True,
            "two_second_answer_notice": True,
        })
    finally:
        if first.is_connected():
            first.disconnect()
        if second.is_connected():
            second.disconnect()


if __name__ == "__main__":
    main()
