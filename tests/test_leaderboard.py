import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
"""Leaderboard SQL ordering, paging and public-profile security tests."""

import os
import tempfile

import app
from profile_store import GAME_MODES, ProfileStore


def seed_user(store, index, xp=0, created=None):
    user_id = f"user-{index:03d}"
    with store.connection() as db:
        db.execute(
            "INSERT INTO users(id,username,email,password_hash,avatar,created_at,total_xp) VALUES(?,?,?,?,?,?,?)",
            (user_id, f"Player{index:03d}", f"p{index}@example.com", "SECRET_HASH", "captain",
             created or f"2025-01-{(index % 28) + 1:02d}T00:00:00+00:00", xp),
        )
        db.executemany("INSERT INTO game_stats(user_id,game_mode) VALUES(?,?)",
                       [(user_id, mode) for mode in GAME_MODES])
        db.commit()
    return user_id


def set_stats(store, user_id, mode, **values):
    allowed = {
        "played", "wins", "losses", "draws", "best_streak", "correct_answers",
        "wrong_answers", "completed", "total_captures", "total_steals", "high_score",
        "best_density", "best_completion_seconds", "fastest_win_seconds",
    }
    values = {key: value for key, value in values.items() if key in allowed}
    assignments = ",".join(f"{key}=?" for key in values)
    with store.connection() as db:
        db.execute(f"UPDATE game_stats SET {assignments} WHERE user_id=? AND game_mode=?",
                   (*values.values(), user_id, mode))
        db.commit()


def main():
    with tempfile.TemporaryDirectory() as directory:
        store = ProfileStore(os.path.join(directory, "leaderboard.sqlite3"))
        first = seed_user(store, 1, 1000, "2024-01-01T00:00:00+00:00")
        second = seed_user(store, 2, 1000, "2024-01-02T00:00:00+00:00")
        third = seed_user(store, 3, 900)
        set_stats(store, first, "possession", played=4, wins=2, total_steals=3, total_captures=10)
        set_stats(store, second, "possession", played=4, wins=3, total_steals=2, total_captures=9)
        set_stats(store, third, "missing_xi", played=2, completed=1, high_score=10,
                  correct_answers=10, wrong_answers=2, best_completion_seconds=0)
        set_stats(store, first, "missing_xi", played=2, completed=1, high_score=10,
                  correct_answers=10, wrong_answers=2, best_completion_seconds=120)
        set_stats(store, first, "heatmap", played=1, best_density=4.2, high_score=126)
        set_stats(store, second, "tiki_taka_toe", played=3, wins=2, best_streak=2, correct_answers=7)

        overall = store.leaderboard("overall")
        assert [item["id"] for item in overall["entries"][:2]] == [second, first]
        assert store.leaderboard("golden_hex")["entries"][0]["id"] == second
        assert store.leaderboard("missing_xi")["entries"][0]["id"] == first
        assert store.leaderboard("heatmap")["entries"][0]["id"] == first
        assert store.leaderboard("tiki_taka_toe")["entries"][0]["id"] == second
        assert third not in [item["id"] for item in store.leaderboard("golden_hex")["entries"]]
        assert store.leaderboard("overall")["entries"][0]["win_rate"] >= 0
        assert store.leaderboard("missing_xi")["entries"][1]["best_completion_seconds"] == 0

        for index in range(4, 57):
            seed_user(store, index, 100 - index)
        tie_a = seed_user(store, 57, 800, "2025-02-01T00:00:00+00:00")
        tie_b = seed_user(store, 58, 800, "2025-02-01T00:00:00+00:00")
        tied_order = [item["id"] for item in store.leaderboard("overall")["entries"]]
        assert tied_order.index(tie_a) < tied_order.index(tie_b)
        page_two = store.leaderboard("overall", 2)
        assert len(store.leaderboard("overall", 1)["entries"]) == 50
        assert page_two["entries"][0]["rank"] == 51
        assert store.leaderboard("overall", -8)["page"] == 1
        assert store.leaderboard("overall", "bad")["page"] == 1
        try:
            store.leaderboard("DROP TABLE users")
            raise AssertionError("Invalid mode accepted")
        except ValueError:
            pass

        app.profile_store = store
        anonymous = app.app.test_client()
        assert anonymous.get(f"/player/{first}").status_code == 200
        public_html = anonymous.get(f"/player/{first}").get_data(as_text=True)
        assert "p1@example.com" not in public_html and "SECRET_HASH" not in public_html
        assert "PROFİLİMİ DÜZENLE" not in public_html
        assert anonymous.get("/player/does-not-exist").status_code == 404
        assert anonymous.get("/api/leaderboard?mode=invalid").status_code == 400

        signed_in = app.app.test_client()
        with signed_in.session_transaction() as session:
            session["user_id"] = first
        html = signed_in.get("/leaderboard").get_data(as_text=True)
        assert "· SEN" in html
        own_profile = signed_in.get(f"/player/{first}").get_data(as_text=True)
        other_profile = signed_in.get(f"/player/{second}").get_data(as_text=True)
        assert "PROFİLİMİ DÜZENLE" in own_profile
        assert "PROFİLİMİ DÜZENLE" not in other_profile
        api_text = signed_in.get("/api/leaderboard").get_data(as_text=True)
        assert "email" not in api_text and "password_hash" not in api_text and "SECRET_HASH" not in api_text
        print({
            "overall_and_ties": True, "deterministic_id_tie": True, "four_mode_orders": True,
            "unplayed_excluded": True, "zero_safe": True, "best_time_zero_not_ranked": True,
            "paging_50_rank_51": True, "invalid_inputs": True, "current_user_marked": True,
            "public_profile_security": True, "missing_profile_404": True,
        })


if __name__ == "__main__":
    main()
