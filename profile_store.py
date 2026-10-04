"""SQLite-backed Football Match accounts and atomic game statistics."""

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash


XP_REWARDS = {"win": 100, "draw": 50, "loss": 25, "complete": 50}
GAME_MODES = ("possession", "missing_xi", "heatmap", "tiki_taka_toe")
AVATARS = ("captain", "keeper", "striker", "playmaker", "defender", "legend")
LEADERBOARD_MODES = {
    "golden_hex": "possession",
    "missing_xi": "missing_xi",
    "heatmap": "heatmap",
    "tiki_taka_toe": "tiki_taka_toe",
}
LEADERBOARD_PAGE_SIZE = 50


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def level_for_xp(total_xp):
    return int(total_xp or 0) // 500 + 1


class ProfileStore:
    def __init__(self, path):
        self.path = path
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        self.init_schema()

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def init_schema(self):
        with self.connection() as db:
            existing_columns = {
                row["name"] for row in db.execute("PRAGMA table_info(users)")
            }
            if "email" in existing_columns:
                db.execute("PRAGMA foreign_keys = OFF")
                db.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE users_without_email (
                        id TEXT PRIMARY KEY,
                        username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                        password_hash TEXT NOT NULL,
                        avatar TEXT NOT NULL DEFAULT 'captain',
                        created_at TEXT NOT NULL,
                        last_login_at TEXT,
                        total_xp INTEGER NOT NULL DEFAULT 0 CHECK(total_xp >= 0)
                    );
                    INSERT INTO users_without_email(
                        id,username,password_hash,avatar,created_at,last_login_at,total_xp
                    )
                    SELECT id,username,password_hash,avatar,created_at,last_login_at,total_xp
                    FROM users;
                    DROP TABLE users;
                    ALTER TABLE users_without_email RENAME TO users;
                    COMMIT;
                """)
                db.execute("PRAGMA foreign_keys = ON")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    password_hash TEXT NOT NULL,
                    avatar TEXT NOT NULL DEFAULT 'captain',
                    created_at TEXT NOT NULL,
                    last_login_at TEXT,
                    total_xp INTEGER NOT NULL DEFAULT 0 CHECK(total_xp >= 0)
                );
                CREATE TABLE IF NOT EXISTS game_stats (
                    user_id TEXT NOT NULL,
                    game_mode TEXT NOT NULL,
                    played INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    draws INTEGER NOT NULL DEFAULT 0,
                    current_streak INTEGER NOT NULL DEFAULT 0,
                    best_streak INTEGER NOT NULL DEFAULT 0,
                    play_seconds INTEGER NOT NULL DEFAULT 0,
                    correct_answers INTEGER NOT NULL DEFAULT 0,
                    wrong_answers INTEGER NOT NULL DEFAULT 0,
                    completed INTEGER NOT NULL DEFAULT 0,
                    total_captures INTEGER NOT NULL DEFAULT 0,
                    total_steals INTEGER NOT NULL DEFAULT 0,
                    max_captures INTEGER NOT NULL DEFAULT 0,
                    high_score INTEGER NOT NULL DEFAULT 0,
                    best_density REAL NOT NULL DEFAULT 0,
                    best_completion_seconds INTEGER,
                    fastest_win_seconds INTEGER,
                    PRIMARY KEY(user_id, game_mode),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS match_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    game_mode TEXT NOT NULL,
                    result TEXT NOT NULL,
                    xp_awarded INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL,
                    UNIQUE(match_id, user_id),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_users_leaderboard
                    ON users(total_xp DESC, created_at ASC, id ASC);
                CREATE INDEX IF NOT EXISTS idx_game_stats_mode_rank
                    ON game_stats(game_mode, played, wins DESC, user_id);
                CREATE INDEX IF NOT EXISTS idx_match_results_user_result
                    ON match_results(user_id, result);
            """)
            db.commit()

    def create_user(self, username, password, avatar="captain"):
        username = username.strip()
        if len(username) < 3 or len(username) > 24:
            raise ValueError("Kullanıcı adı 3-24 karakter olmalı.")
        if len(password) < 8:
            raise ValueError("Parola en az 8 karakter olmalı.")
        if avatar not in AVATARS:
            avatar = "captain"
        user_id, now = uuid.uuid4().hex, utc_now()
        try:
            with self.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute(
                    "INSERT INTO users(id,username,password_hash,avatar,created_at) VALUES(?,?,?,?,?)",
                    (user_id, username, generate_password_hash(password), avatar, now),
                )
                db.executemany(
                    "INSERT INTO game_stats(user_id,game_mode) VALUES(?,?)",
                    [(user_id, mode) for mode in GAME_MODES],
                )
                db.commit()
        except sqlite3.IntegrityError as error:
            message = str(error).lower()
            if "username" in message:
                raise ValueError("Bu kullanıcı adı zaten kullanılıyor.") from error
            raise
        return self.get_user(user_id)

    def authenticate(self, identity, password):
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
                (identity.strip(),),
            ).fetchone()
            if not row or not check_password_hash(row["password_hash"], password):
                return None
            now = utc_now()
            db.execute("UPDATE users SET last_login_at=? WHERE id=?", (now, row["id"]))
            db.commit()
        return self.get_user(row["id"])

    def get_user(self, user_id):
        if not user_id:
            return None
        with self.connection() as db:
            row = db.execute(
                "SELECT id,username,avatar,created_at,last_login_at,total_xp FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        user = dict(row)
        user["level"] = level_for_xp(user["total_xp"])
        user["level_progress"] = user["total_xp"] % 500
        return user

    def update_profile(self, user_id, username, avatar):
        username = username.strip()
        if len(username) < 3 or len(username) > 24:
            raise ValueError("Kullanıcı adı 3-24 karakter olmalı.")
        if avatar not in AVATARS:
            raise ValueError("Geçersiz avatar.")
        try:
            with self.connection() as db:
                db.execute("UPDATE users SET username=?,avatar=? WHERE id=?",
                           (username, avatar, user_id))
                db.commit()
        except sqlite3.IntegrityError as error:
            raise ValueError("Bu kullanıcı adı zaten kullanılıyor.") from error
        return self.get_user(user_id)

    def change_password(self, user_id, current_password, new_password):
        if len(new_password) < 8:
            raise ValueError("Yeni parola en az 8 karakter olmalı.")
        with self.connection() as db:
            row = db.execute("SELECT password_hash FROM users WHERE id=?", (user_id,)).fetchone()
            if not row or not check_password_hash(row["password_hash"], current_password):
                raise ValueError("Mevcut parola yanlış.")
            db.execute("UPDATE users SET password_hash=? WHERE id=?",
                       (generate_password_hash(new_password), user_id))
            db.commit()

    def delete_account(self, user_id, current_password):
        """Permanently delete an account and all rows linked by foreign keys."""
        if not user_id or not current_password:
            raise ValueError("Hesabı silmek için mevcut parolanı girmelisin.")
        with self.connection() as db:
            row = db.execute(
                "SELECT password_hash FROM users WHERE id=?", (user_id,)
            ).fetchone()
            if not row or not check_password_hash(row["password_hash"], current_password):
                raise ValueError("Mevcut parola yanlış.")
            db.execute("BEGIN IMMEDIATE")
            deleted = db.execute("DELETE FROM users WHERE id=?", (user_id,))
            db.commit()
        if not deleted.rowcount:
            raise ValueError("Hesap bulunamadı.")
        return True

    def record_result(self, match_id, user_id, game_mode, result, **metrics):
        if not user_id or game_mode not in GAME_MODES or result not in XP_REWARDS:
            return False
        xp = XP_REWARDS[result]
        with self.connection() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                db.execute(
                    "INSERT INTO match_results(match_id,user_id,game_mode,result,xp_awarded,recorded_at) VALUES(?,?,?,?,?,?)",
                    (str(match_id), user_id, game_mode, result, xp, utc_now()),
                )
            except sqlite3.IntegrityError:
                db.rollback()
                return False
            db.execute("INSERT OR IGNORE INTO game_stats(user_id,game_mode) VALUES(?,?)", (user_id, game_mode))
            won, lost, drawn = int(result == "win"), int(result == "loss"), int(result == "draw")
            streak = "current_streak + 1" if won else "0"
            db.execute(f"""
                UPDATE game_stats SET
                    played=played+1,wins=wins+?,losses=losses+?,draws=draws+?,
                    current_streak={streak},
                    best_streak=MAX(best_streak, CASE WHEN ? THEN current_streak+1 ELSE best_streak END),
                    play_seconds=play_seconds+?,correct_answers=correct_answers+?,wrong_answers=wrong_answers+?,
                    completed=completed+?,total_captures=total_captures+?,total_steals=total_steals+?,
                    max_captures=MAX(max_captures,?),high_score=MAX(high_score,?),best_density=MAX(best_density,?),
                    best_completion_seconds=CASE WHEN ? IS NULL THEN best_completion_seconds WHEN best_completion_seconds IS NULL THEN ? ELSE MIN(best_completion_seconds,?) END,
                    fastest_win_seconds=CASE WHEN ? IS NULL THEN fastest_win_seconds WHEN fastest_win_seconds IS NULL THEN ? ELSE MIN(fastest_win_seconds,?) END
                WHERE user_id=? AND game_mode=?
            """, (
                won, lost, drawn, won, int(metrics.get("play_seconds", 0)),
                int(metrics.get("correct_answers", 0)), int(metrics.get("wrong_answers", 0)),
                int(metrics.get("completed", 0)), int(metrics.get("captures", 0)),
                int(metrics.get("steals", 0)), int(metrics.get("captures", 0)),
                int(metrics.get("score", 0)), float(metrics.get("density", 0)),
                metrics.get("completion_seconds"), metrics.get("completion_seconds"), metrics.get("completion_seconds"),
                metrics.get("fastest_win_seconds"), metrics.get("fastest_win_seconds"), metrics.get("fastest_win_seconds"),
                user_id, game_mode,
            ))
            db.execute("UPDATE users SET total_xp=total_xp+? WHERE id=?", (xp, user_id))
            db.commit()
        return True

    def profile(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return None
        with self.connection() as db:
            rows = db.execute("SELECT * FROM game_stats WHERE user_id=?", (user_id,)).fetchall()
            competitive_results = db.execute(
                "SELECT result FROM match_results WHERE user_id=? AND result IN ('win','loss','draw') ORDER BY id",
                (user_id,),
            ).fetchall()
        stats = {mode: self._empty_stats() for mode in GAME_MODES}
        for row in rows:
            stats[row["game_mode"]] = dict(row)
        for values in stats.values():
            values["win_rate"] = round(values["wins"] * 100 / values["played"], 1) if values["played"] else 0
            attempts = values["correct_answers"] + values["wrong_answers"]
            values["accuracy"] = round(values["correct_answers"] * 100 / attempts, 1) if attempts else 0
        overall = {
            "played": sum(item["played"] for item in stats.values()),
            "wins": sum(item["wins"] for item in stats.values()),
            "losses": sum(item["losses"] for item in stats.values()),
            "draws": sum(item["draws"] for item in stats.values()),
            "play_seconds": sum(item["play_seconds"] for item in stats.values()),
            "current_streak": 0,
            "best_streak": 0,
        }
        for row in competitive_results:
            overall["current_streak"] = overall["current_streak"] + 1 if row["result"] == "win" else 0
            overall["best_streak"] = max(overall["best_streak"], overall["current_streak"])
        overall["win_rate"] = round(overall["wins"] * 100 / overall["played"], 1) if overall["played"] else 0
        return {"user": user, "overall": overall, "games": stats}

    def public_profile(self, user_id):
        profile = self.profile(user_id)
        if not profile:
            return None
        user = profile["user"]
        profile["user"] = {
            key: user[key] for key in (
                "id", "username", "avatar", "created_at", "total_xp",
                "level", "level_progress",
            )
        }
        return profile

    def leaderboard(self, mode="overall", page=1):
        if mode != "overall" and mode not in LEADERBOARD_MODES:
            raise ValueError("Geçersiz liderlik modu.")
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
        page = max(1, page)
        offset = (page - 1) * LEADERBOARD_PAGE_SIZE

        with self.connection() as db:
            if mode == "overall":
                count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                rows = db.execute("""
                    SELECT u.id,u.username,u.avatar,u.total_xp,u.created_at,
                           COALESCE(SUM(g.played),0) AS played,
                           COALESCE(SUM(g.wins),0) AS wins,
                           COALESCE(SUM(g.losses),0) AS losses,
                           COALESCE(SUM(g.draws),0) AS draws
                    FROM users u LEFT JOIN game_stats g ON g.user_id=u.id
                    GROUP BY u.id
                    ORDER BY u.total_xp DESC,wins DESC,played DESC,u.created_at ASC,u.id ASC
                    LIMIT ? OFFSET ?
                """, (LEADERBOARD_PAGE_SIZE, offset)).fetchall()
            else:
                game_mode = LEADERBOARD_MODES[mode]
                count = db.execute(
                    "SELECT COUNT(*) FROM game_stats WHERE game_mode=? AND played>0",
                    (game_mode,),
                ).fetchone()[0]
                order_by = {
                    "golden_hex": "g.wins DESC,win_rate DESC,g.total_steals DESC,g.total_captures DESC,g.played DESC,u.id ASC",
                    "missing_xi": "g.high_score DESC,g.completed DESC,accuracy DESC,CASE WHEN g.best_completion_seconds>0 THEN g.best_completion_seconds ELSE 2147483647 END ASC,g.played DESC,u.id ASC",
                    "heatmap": "g.best_density DESC,g.high_score DESC,accuracy DESC,g.played DESC,u.id ASC",
                    "tiki_taka_toe": "g.wins DESC,win_rate DESC,g.best_streak DESC,g.correct_answers DESC,g.played DESC,u.id ASC",
                }[mode]
                rows = db.execute(f"""
                    SELECT u.id,u.username,u.avatar,u.total_xp,u.created_at,
                           g.*,
                           CASE WHEN g.played>0 THEN ROUND(g.wins*100.0/g.played,1) ELSE 0 END AS win_rate,
                           CASE WHEN g.correct_answers+g.wrong_answers>0
                                THEN ROUND(g.correct_answers*100.0/(g.correct_answers+g.wrong_answers),1)
                                ELSE 0 END AS accuracy
                    FROM game_stats g JOIN users u ON u.id=g.user_id
                    WHERE g.game_mode=? AND g.played>0
                    ORDER BY {order_by}
                    LIMIT ? OFFSET ?
                """, (game_mode, LEADERBOARD_PAGE_SIZE, offset)).fetchall()

        total_pages = max(1, (count + LEADERBOARD_PAGE_SIZE - 1) // LEADERBOARD_PAGE_SIZE)
        entries = []
        for index, row in enumerate(rows, start=offset + 1):
            entry = dict(row)
            entry["rank"] = index
            entry["level"] = level_for_xp(entry["total_xp"])
            entry["win_rate"] = entry.get("win_rate", round(entry["wins"] * 100 / entry["played"], 1) if entry["played"] else 0)
            entry["accuracy"] = entry.get("accuracy", 0)
            entries.append(entry)
        return {
            "mode": mode, "page": page, "page_size": LEADERBOARD_PAGE_SIZE,
            "total": count, "total_pages": total_pages, "entries": entries,
        }

    @staticmethod
    def _empty_stats():
        return {key: 0 for key in (
            "played", "wins", "losses", "draws", "current_streak", "best_streak",
            "play_seconds", "correct_answers", "wrong_answers", "completed",
            "total_captures", "total_steals", "max_captures", "high_score", "best_density",
        )} | {"best_completion_seconds": None, "fastest_win_seconds": None}
