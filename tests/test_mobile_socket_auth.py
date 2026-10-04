"""Native Socket.IO authentication without relying on WebView cookies."""

from __future__ import annotations

import os as _path_os
import re
import sys as _path_sys


SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)

import app


def register_and_token(username):
    client = app.app.test_client()
    page = client.get("/register").get_data(as_text=True)
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    response = client.post("/register", data={
        "csrf_token": csrf,
        "username": username,
        "password": "socket-test-password",
        "avatar": "captain",
    })
    assert response.status_code == 302
    token_response = client.get("/api/mobile/socket-token")
    assert token_response.status_code == 200
    assert token_response.json["expires_in"] == app.MOBILE_SOCKET_TOKEN_MAX_AGE
    return token_response.json["token"]


def event_payload(client, name):
    events = [event for event in client.get_received() if event["name"] == name]
    return events[-1]["args"][0] if events else None


def main():
    first_token = register_and_token("mobile_socket_one")
    second_token = register_and_token("mobile_socket_two")

    first = app.socketio.test_client(
        app.app, auth={"mobile_token": first_token},
    )
    second = app.socketio.test_client(
        app.app, auth={"mobile_token": second_token},
    )
    invalid = app.socketio.test_client(
        app.app, auth={"mobile_token": first_token + "tampered"},
    )
    try:
        first.emit("find_random_match")
        assert event_payload(first, "matchmaking_waiting")

        second.emit("find_random_match")
        assert event_payload(first, "matchmaking_found")
        assert event_payload(second, "matchmaking_found")

        invalid.emit("find_random_match")
        error = event_payload(invalid, "matchmaking_error")
        assert error and "giriş" in error["message"].lower()
    finally:
        for client in (first, second, invalid):
            if client.is_connected():
                client.disconnect()

    print({
        "http_session_issues_signed_socket_token": True,
        "native_socket_auth_works_without_cookie": True,
        "random_matchmaking_recognizes_accounts": True,
        "tampered_token_rejected": True,
    })


if __name__ == "__main__":
    main()
