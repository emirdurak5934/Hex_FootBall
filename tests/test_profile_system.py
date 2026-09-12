import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Account, security, statistics and idempotency tests."""

import os
import tempfile

import app
from profile_store import GAME_MODES, ProfileStore, level_for_xp


def csrf(client):
    with client.session_transaction() as session:
        session["csrf_token"] = "test-csrf"
    return "test-csrf"


def main():
    with tempfile.TemporaryDirectory() as directory:
        store = ProfileStore(os.path.join(directory, "profiles.sqlite3"))
        app.profile_store = store
        client = app.app.test_client()
        token = csrf(client)

        response = client.post("/register", data={
            "csrf_token": token, "username": "TestKaptan",
            "email": "kaptan@example.com", "password": "safe-pass-123",
            "avatar": "captain",
        })
        assert response.status_code == 302
        with client.session_transaction() as session:
            user_id = session["user_id"]

        client.post("/logout", data={"csrf_token": csrf(client)})
        duplicate_name = client.post("/register", data={
            "csrf_token": csrf(client), "username": "TestKaptan",
            "email": "other@example.com", "password": "safe-pass-123",
        })
        assert "zaten" in duplicate_name.get_data(as_text=True)
        duplicate_email = client.post("/register", data={
            "csrf_token": csrf(client), "username": "OtherUser",
            "email": "kaptan@example.com", "password": "safe-pass-123",
        })
        assert "zaten" in duplicate_email.get_data(as_text=True)
        assert client.post("/login", data={
            "csrf_token": csrf(client), "identity": "TestKaptan", "password": "wrong-pass",
        }).status_code == 200
        assert client.post("/login", data={
            "csrf_token": csrf(client), "identity": "TestKaptan", "password": "safe-pass-123",
        }).status_code == 302
        assert client.get("/profile").status_code == 200

        token = csrf(client)
        updated = client.post("/api/profile", json={
            "username": "YeniKaptan", "email": "new@example.com", "avatar": "legend",
        }, headers={"X-CSRF-Token": token})
        assert updated.status_code == 200 and updated.json["user"]["avatar"] == "legend"
        changed = client.post("/api/profile/password", json={
            "current_password": "safe-pass-123", "new_password": "new-safe-pass-456",
        }, headers={"X-CSRF-Token": token})
        assert changed.status_code == 200

        assert store.record_result("match-1", user_id, "possession", "win", captures=8, steals=2)
        assert not store.record_result("match-1", user_id, "possession", "win")
        store.record_result("match-2", user_id, "possession", "win")
        store.record_result("match-3", user_id, "possession", "loss")
        store.record_result("match-4", user_id, "possession", "draw")
        store.record_result("single-1", user_id, "heatmap", "complete", score=42)
        profile = store.profile(user_id)
        possession = profile["games"]["possession"]
        assert possession["played"] == 4
        assert (possession["wins"], possession["losses"], possession["draws"]) == (2, 1, 1)
        assert possession["current_streak"] == 0 and possession["best_streak"] == 2
        assert possession["win_rate"] == 50.0
        assert profile["user"]["total_xp"] == 325
        assert level_for_xp(0) == 1 and level_for_xp(500) == 2
        assert set(profile["games"]) == set(GAME_MODES)
        assert all(profile["games"][mode]["played"] == 0 for mode in ("missing_xi", "tiki_taka_toe"))

        opponent = store.create_user("Opponent", "opponent@example.com", "safe-pass-789")
        room = {
            "state": app.create_match_state(),
            "user_ids": {1: user_id, 2: opponent["id"]},
            "match_id": "online-forfeit-1",
        }
        room["state"]["started"] = True
        app.finish_room_game(room["state"], 1, "disconnect")
        app.record_possession_results("ROOM01", room)
        app.record_possession_results("ROOM01", room)
        assert store.profile(user_id)["games"]["possession"]["played"] == 5
        assert store.profile(opponent["id"])["games"]["possession"]["losses"] == 1
        rematch = {
            "state": app.create_match_state(), "user_ids": room["user_ids"],
            "match_id": "online-rematch-2",
        }
        rematch["state"].update(started=True, finished=True, winner=0)
        app.record_possession_results("ROOM01", rematch)
        assert store.profile(user_id)["games"]["possession"]["played"] == 6

        anonymous = app.app.test_client()
        assert anonymous.get("/api/profile").status_code == 401
        assert anonymous.get("/profile").status_code == 302
        print({
            "register_login_logout": True, "duplicates_rejected": True,
            "profile_and_password_update": True, "unauthorized_blocked": True,
            "idempotent_results": True, "win_loss_draw_streak_rate": True,
            "xp_level": True, "four_empty_game_stats": True,
            "forfeit_and_rematch_results": True,
        })


if __name__ == "__main__":
    main()
