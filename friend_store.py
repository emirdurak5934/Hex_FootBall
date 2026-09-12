"""SQLite persistence for the social layer; game state remains in Socket.IO."""

import sqlite3
from profile_store import utc_now


class FriendStore:
    def __init__(self, profile_store):
        self.profile_store = profile_store
        self.init_schema()

    def init_schema(self):
        with self.profile_store.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS friendships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requester_id TEXT NOT NULL,
                    addressee_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending','accepted')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    CHECK(requester_id <> addressee_id),
                    FOREIGN KEY(requester_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(addressee_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_friendships_pair
                    ON friendships(CASE WHEN requester_id < addressee_id THEN requester_id ELSE addressee_id END,
                                   CASE WHEN requester_id < addressee_id THEN addressee_id ELSE requester_id END);
                CREATE INDEX IF NOT EXISTS idx_friendships_addressee_status
                    ON friendships(addressee_id, status);
            """)
            db.commit()

    def _relation(self, db, first_id, second_id):
        return db.execute("""SELECT * FROM friendships WHERE
            (requester_id=? AND addressee_id=?) OR (requester_id=? AND addressee_id=?)""",
            (first_id, second_id, second_id, first_id)).fetchone()

    def send_friend_request(self, requester_id, addressee_id):
        if not requester_id or requester_id == addressee_id:
            raise ValueError("Kendine arkadaşlık isteği gönderemezsin.")
        with self.profile_store.connection() as db:
            if not db.execute("SELECT 1 FROM users WHERE id=?", (addressee_id,)).fetchone():
                raise ValueError("Kullanıcı bulunamadı.")
            db.execute("BEGIN IMMEDIATE")
            relation = self._relation(db, requester_id, addressee_id)
            if relation:
                if relation["status"] == "accepted":
                    raise ValueError("Zaten arkadaşsınız.")
                if relation["requester_id"] == requester_id:
                    raise ValueError("Arkadaşlık isteği zaten gönderildi.")
                raise ValueError("Bu kullanıcının senden bekleyen isteği var.")
            now = utc_now()
            db.execute("INSERT INTO friendships(requester_id,addressee_id,status,created_at,updated_at) VALUES(?,?, 'pending',?,?)",
                       (requester_id, addressee_id, now, now))
            db.commit()

    def accept_friend_request(self, user_id, requester_id):
        with self.profile_store.connection() as db:
            result = db.execute("UPDATE friendships SET status='accepted',updated_at=? WHERE requester_id=? AND addressee_id=? AND status='pending'",
                                (utc_now(), requester_id, user_id))
            db.commit()
        if not result.rowcount: raise ValueError("Bekleyen arkadaşlık isteği bulunamadı.")

    def reject_friend_request(self, user_id, requester_id):
        with self.profile_store.connection() as db:
            result = db.execute("DELETE FROM friendships WHERE requester_id=? AND addressee_id=? AND status='pending'", (requester_id, user_id))
            db.commit()
        if not result.rowcount: raise ValueError("Bekleyen arkadaşlık isteği bulunamadı.")

    def cancel_friend_request(self, user_id, addressee_id):
        with self.profile_store.connection() as db:
            result = db.execute("DELETE FROM friendships WHERE requester_id=? AND addressee_id=? AND status='pending'", (user_id, addressee_id))
            db.commit()
        if not result.rowcount: raise ValueError("Bekleyen arkadaşlık isteği bulunamadı.")

    def remove_friend(self, user_id, friend_id):
        with self.profile_store.connection() as db:
            result = db.execute("DELETE FROM friendships WHERE status='accepted' AND ((requester_id=? AND addressee_id=?) OR (requester_id=? AND addressee_id=?))", (user_id, friend_id, friend_id, user_id))
            db.commit()
        if not result.rowcount: raise ValueError("Arkadaşlık bulunamadı.")

    def get_friendship_status(self, user_id, other_id):
        with self.profile_store.connection() as db: relation = self._relation(db, user_id, other_id)
        if not relation: return "none"
        if relation["status"] == "accepted": return "friends"
        return "outgoing_pending" if relation["requester_id"] == user_id else "incoming_pending"

    def are_friends(self, user_id, friend_id):
        return self.get_friendship_status(user_id, friend_id) == "friends"

    def get_friends(self, user_id):
        with self.profile_store.connection() as db:
            rows = db.execute("""SELECT u.id,u.username,u.avatar FROM friendships f JOIN users u ON u.id=
                CASE WHEN f.requester_id=? THEN f.addressee_id ELSE f.requester_id END
                WHERE (f.requester_id=? OR f.addressee_id=?) AND f.status='accepted' ORDER BY u.username COLLATE NOCASE""",
                (user_id, user_id, user_id)).fetchall()
        return [dict(row) for row in rows]

    def get_incoming_friend_requests(self, user_id):
        with self.profile_store.connection() as db:
            rows = db.execute("SELECT u.id,u.username,u.avatar FROM friendships f JOIN users u ON u.id=f.requester_id WHERE f.addressee_id=? AND f.status='pending' ORDER BY f.created_at DESC", (user_id,)).fetchall()
        return [dict(row) for row in rows]

    def search_users(self, user_id, query, limit=12):
        query = query.strip()
        if len(query) < 2: return []
        with self.profile_store.connection() as db:
            rows = db.execute("SELECT id,username,avatar FROM users WHERE id<>? AND username LIKE ? COLLATE NOCASE ORDER BY username LIMIT ?", (user_id, f"%{query}%", limit)).fetchall()
        result = [dict(row) for row in rows]
        for item in result: item["friendship_status"] = self.get_friendship_status(user_id, item["id"])
        return result
