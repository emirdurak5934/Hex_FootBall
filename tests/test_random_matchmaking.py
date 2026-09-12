import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)

"""Regression coverage for account-based random matchmaking."""

import app


USERS = {
    "match-user-one": {"id": "match-user-one", "username": "Emir", "email": "emir@test.local"},
    "match-user-two": {"id": "match-user-two", "username": "Rakip", "email": "rakip@test.local"},
}


def payload(client, event_name):
    found = [event for event in client.get_received() if event["name"] == event_name]
    assert found, f"Expected {event_name}"
    return found[-1]["args"][0]


def from_events(received, event_name):
    found = [event for event in received if event["name"] == event_name]
    assert found, f"Expected {event_name}"
    return found[-1]["args"][0]


def clients():
    original_get_user = app.profile_store.get_user
    app.profile_store.get_user = lambda user_id: USERS.get(user_id)
    flask_clients = [app.app.test_client(), app.app.test_client()]
    for flask_client, user_id in zip(flask_clients, USERS):
        with flask_client.session_transaction() as session:
            session["user_id"] = user_id
    socket_clients = [
        app.socketio.test_client(app.app, flask_test_client=flask_client)
        for flask_client in flask_clients
    ]
    return original_get_user, socket_clients


def test_possession_random_match():
    original_get_user, (first, second) = clients()
    try:
        first.emit("find_random_match")
        waiting = payload(first, "matchmaking_waiting")
        assert waiting["game_mode"] == "possession"
        second.emit("find_random_match")
        first_events, second_events = first.get_received(), second.get_received()
        first_found = from_events(first_events, "matchmaking_found")
        second_found = from_events(second_events, "matchmaking_found")
        first_ready = from_events(first_events, "game_ready")
        second_ready = from_events(second_events, "game_ready")
        assert first_found["room_code"] == second_found["room_code"]
        assert {first_found["player_number"], second_found["player_number"]} == {1, 2}
        assert first_ready["state"] == second_ready["state"]
        assert first_ready["state"]["player_names"] == {"1": "Emir", "2": "Rakip"}
        assert first_ready["state"]["started"]
    finally:
        if first.is_connected(): first.disconnect()
        if second.is_connected(): second.disconnect()
        app.profile_store.get_user = original_get_user


def test_tiki_random_match():
    original_get_user, (first, second) = clients()
    try:
        first.emit("tiki_find_random_match")
        waiting = payload(first, "tiki_matchmaking_waiting")
        assert waiting["game_mode"] == "tiki_taka_toe"
        second.emit("tiki_find_random_match")
        first_events, second_events = first.get_received(), second.get_received()
        first_found = from_events(first_events, "tiki_matchmaking_found")
        second_found = from_events(second_events, "tiki_matchmaking_found")
        first_ready = from_events(first_events, "tiki_game_ready")
        second_ready = from_events(second_events, "tiki_game_ready")
        assert first_found["room_code"] == second_found["room_code"]
        assert {first_found["player_number"], second_found["player_number"]} == {1, 2}
        assert first_ready["state"] == second_ready["state"]
        assert first_ready["state"]["player_names"] == {"1": "Emir", "2": "Rakip"}
        assert first_ready["state"]["started"]
    finally:
        if first.is_connected(): first.disconnect()
        if second.is_connected(): second.disconnect()
        app.profile_store.get_user = original_get_user


if __name__ == "__main__":
    test_possession_random_match()
    test_tiki_random_match()
    print({
        "possession_random_matchmaking": True,
        "tiki_random_matchmaking": True,
        "account_names_shared": True,
    })
