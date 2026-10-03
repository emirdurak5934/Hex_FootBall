import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Regression coverage for local rules and the isolated online room flow."""

import app
import time


def events(client, name):
    return [event for event in client.get_received() if event["name"] == name]


def payload(client, name):
    found = events(client, name)
    assert found, f"Expected {name}"
    return found[-1]["args"][0]


def valid_id(state, index, excluded=()):
    row, column = divmod(index, 3)
    answers = app.tiki_engine.cell_answers(state["rows"][row], state["columns"][column])
    return next(player_id for player_id in answers if player_id not in excluded)


def test_rules():
    state = app.create_tiki_state(app.tiki_engine.generate_board())
    public = app.serialize_tiki_state(state)
    for item in public["rows"] + public["columns"]:
        assert item["image"].startswith("/static/")
        assert _path_os.path.isfile(_path_os.path.join(app.app.root_path, item["image"].lstrip("/")))
    correct_id = valid_id(state, 0)
    wrong_id = next(player_id for player_id in app.tiki_engine.players_by_id
                    if not app.tiki_engine.player_matches(player_id, state["rows"][0], state["columns"][0]))
    wrong = app.apply_tiki_move(state, 0, wrong_id, 1)
    assert wrong["accepted"] and not wrong["correct"]
    assert state["board"][0] is None and wrong_id not in state["used_players"]
    assert state["active_player"] == 2
    right = app.apply_tiki_move(state, 0, correct_id, 2)
    assert right["accepted"] and right["correct"] and state["board"][0]["owner"] == 2
    state["active_player"] = 1
    reused = app.apply_tiki_move(state, 1, correct_id, 1)
    assert not reused["accepted"]
    state["board"] = [
        {"owner": 1}, {"owner": 1}, {"owner": 1}, None, None,
        None, None, None, None,
    ]
    assert app.tiki_winner(state["board"]) == 1


def test_turn_timeout():
    board = app.tiki_engine.generate_board()
    state = app.create_tiki_state(board, started=False)
    assert state["turn_deadline"] is None
    token = "test-tiki-turn-timeout"
    with app.tiki_local_games_lock:
        app.tiki_local_games[token] = state
    try:
        client = app.app.test_client()
        started = client.post("/tiki-taka-toe/start", json={"game_token": token}).json
        assert started["accepted"] and started["state"]["turn_remaining_ms"] <= 30000
        assert started["state"]["active_player"] == 1

        state["turn_deadline"] = time.time() - 0.1
        timed_out = client.get(f"/tiki-taka-toe/state/{token}").json
        assert timed_out["state"]["active_player"] == 2
        assert timed_out["state"]["turn_remaining_ms"] > 0

        player_id = valid_id(state, 0)
        state["turn_deadline"] = time.time() - 0.1
        late = app.apply_tiki_move(state, 0, player_id, 2)
        assert not late["accepted"] and state["board"][0] is None
        assert state["active_player"] == 1
    finally:
        with app.tiki_local_games_lock:
            app.tiki_local_games.pop(token, None)


def test_online():
    first = app.socketio.test_client(app.app)
    second = app.socketio.test_client(app.app)
    try:
        first.emit("tiki_create_room")
        created = payload(first, "tiki_room_created")
        room_code = created["room_code"]
        second.emit("tiki_join_room", {"room_code": room_code})
        ready_one = payload(first, "tiki_game_ready")
        ready_two = payload(second, "tiki_game_ready")
        assert ready_one["state"] == ready_two["state"]
        room = app.tiki_rooms[room_code]
        player_id = valid_id(room["state"], 0)
        first.emit("tiki_submit_answer", {"index": 0, "player_id": player_id})
        first_events = first.get_received()
        result = [event for event in first_events if event["name"] == "tiki_move_result"][-1]["args"][0]
        first_notice = [event for event in first_events if event["name"] == "online_answer"][-1]["args"][0]
        first_state = [event for event in first_events if event["name"] == "tiki_game_state"][-1]["args"][0]
        second_events = second.get_received()
        second_state = [event for event in second_events if event["name"] == "tiki_game_state"][-1]["args"][0]
        second_notice = [event for event in second_events if event["name"] == "online_answer"][-1]["args"][0]
        assert result["accepted"] and result["correct"]
        assert first_notice == second_notice and first_notice["duration_ms"] == 2000
        assert first_notice["player_name"]
        assert first_state == second_state and first_state["active_player"] == 2
        room["state"]["turn_deadline"] = time.time() - 0.1
        app.socketio.sleep(0.7)
        first_timeout = payload(first, "tiki_game_state")
        second_timeout = payload(second, "tiki_game_state")
        assert first_timeout == second_timeout and first_timeout["active_player"] == 1
        room["state"].update(finished=True, winner=1, end_reason="test")
        first.emit("tiki_rematch_request")
        first.get_received(); second.get_received()
        second.emit("tiki_rematch_request")
        first_rematch = payload(first, "tiki_rematch_started")["state"]
        second_rematch = payload(second, "tiki_rematch_started")["state"]
        assert first_rematch == second_rematch and first_rematch["started"]
        assert first_rematch["active_player"] == 2
        second.disconnect()
        forfeited = payload(first, "tiki_game_state")
        assert forfeited["finished"] and forfeited["winner"] == 1
    finally:
        if first.is_connected():
            first.disconnect()
        if second.is_connected():
            second.disconnect()


if __name__ == "__main__":
    test_rules()
    test_turn_timeout()
    test_online()
    print({
        "wrong_answer_passes_turn": True,
        "used_player_rejected": True,
        "winner_detection": True,
        "shared_online_state": True,
        "two_party_rematch": True,
        "disconnect_forfeit": True,
        "two_second_answer_notice": True,
        "thirty_second_turn_timeout": True,
    })
