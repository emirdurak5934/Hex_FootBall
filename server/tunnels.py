"""Replaceable public-tunnel providers for development and remote testing."""

from abc import ABC, abstractmethod
import os
import json
import re
import shutil
import subprocess
import threading

from .settings import PROJECT_ROOT, ServerSettings


PUBLIC_URL_PATTERN = re.compile(r"https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com")
TUNNEL_STATE_FILE = os.path.join(PROJECT_ROOT, "instance", "active_tunnel.json")


def _write_tunnel_state(url: str, process_id: int) -> None:
    os.makedirs(os.path.dirname(TUNNEL_STATE_FILE), exist_ok=True)
    temporary = f"{TUNNEL_STATE_FILE}.tmp"
    with open(temporary, "w", encoding="utf-8") as target:
        json.dump({"url": url, "pid": process_id}, target)
    os.replace(temporary, TUNNEL_STATE_FILE)


def _clear_tunnel_state(process_id: int | None = None) -> None:
    if process_id is not None and os.path.isfile(TUNNEL_STATE_FILE):
        try:
            with open(TUNNEL_STATE_FILE, "r", encoding="utf-8") as source:
                if json.load(source).get("pid") != process_id:
                    return
        except (OSError, ValueError):
            pass
    try:
        os.remove(TUNNEL_STATE_FILE)
    except FileNotFoundError:
        pass


class TunnelProvider(ABC):
    @abstractmethod
    def start(self) -> subprocess.Popen:
        raise NotImplementedError


def resolve_cloudflared() -> str:
    configured = os.environ.get("CLOUDFLARED_BIN")
    candidates = [
        configured,
        shutil.which("cloudflared"),
        os.path.join(PROJECT_ROOT, "tools", "bin", "cloudflared.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "cloudflared", "cloudflared.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "cloudflared", "cloudflared.exe"),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return os.path.abspath(candidate)
    raise FileNotFoundError(
        "cloudflared bulunamadı. CLOUDFLARED_BIN ortam değişkenini ayarla "
        "veya tools/bin/cloudflared.exe konumuna yerleştir."
    )


class CloudflareQuickTunnel(TunnelProvider):
    def __init__(self, origin: str):
        self.origin = origin

    def start(self) -> subprocess.Popen:
        executable = resolve_cloudflared()
        _clear_tunnel_state()
        process = subprocess.Popen(
            [executable, "tunnel", "--url", self.origin, "--no-autoupdate"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        def relay_output():
            assert process.stdout is not None
            announced = False
            try:
                for line in process.stdout:
                    print(f"[tunnel] {line}", end="", flush=True)
                    match = PUBLIC_URL_PATTERN.search(line)
                    if match and not announced:
                        announced = True
                        url = match.group(0)
                        _write_tunnel_state(url, process.pid)
                        print("\n" + "=" * 72, flush=True)
                        print(f"TELEFONDAN AÇILACAK SUNUCU ADRESİ:\n{url}", flush=True)
                        print(f"PUBLIC_URL={url}", flush=True)
                        print("=" * 72 + "\n", flush=True)
            finally:
                _clear_tunnel_state(process.pid)

        threading.Thread(target=relay_output, daemon=True).start()
        return process


def create_tunnel_provider(settings: ServerSettings) -> TunnelProvider:
    if settings.tunnel_provider == "cloudflare":
        return CloudflareQuickTunnel(settings.tunnel_origin)
    raise ValueError(f"Desteklenmeyen tünel sağlayıcısı: {settings.tunnel_provider}")
