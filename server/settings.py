"""Environment-driven server settings; no game code belongs here."""

from dataclasses import dataclass
import os
import secrets


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_DIR = os.path.join(PROJECT_ROOT, "instance")
SECRET_FILE = os.path.join(INSTANCE_DIR, "server_secret.txt")


@dataclass(frozen=True)
class ServerSettings:
    host: str
    port: int
    debug: bool
    tunnel_provider: str
    tunnel_origin: str


def load_settings() -> ServerSettings:
    port = int(os.environ.get("FOOTBALL_MATCH_PORT", "5000"))
    return ServerSettings(
        host=os.environ.get("FOOTBALL_MATCH_HOST", "0.0.0.0"),
        port=port,
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
        tunnel_provider=os.environ.get("FOOTBALL_MATCH_TUNNEL_PROVIDER", "cloudflare"),
        tunnel_origin=os.environ.get(
            "FOOTBALL_MATCH_TUNNEL_ORIGIN",
            f"http://127.0.0.1:{port}",
        ),
    )


def ensure_secret_key() -> str:
    configured = os.environ.get("FOOTBALL_MATCH_SECRET_KEY")
    if configured:
        return configured
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "r", encoding="utf-8") as source:
            configured = source.read().strip()
    if not configured:
        configured = secrets.token_urlsafe(48)
        temporary = f"{SECRET_FILE}.tmp"
        with open(temporary, "w", encoding="utf-8") as target:
            target.write(configured)
        os.replace(temporary, SECRET_FILE)
    os.environ["FOOTBALL_MATCH_SECRET_KEY"] = configured
    return configured

