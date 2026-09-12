"""Command-line entry point for local, public, and tunnel-only operation."""

import argparse
import atexit
import os
import signal

from .settings import PROJECT_ROOT, ensure_secret_key, load_settings
from .tunnels import create_tunnel_provider


def serve(with_tunnel: bool = False) -> None:
    settings = load_settings()
    ensure_secret_key()
    os.chdir(PROJECT_ROOT)
    tunnel_process = None
    if with_tunnel:
        tunnel_process = create_tunnel_provider(settings).start()
        atexit.register(tunnel_process.terminate)

    from app import app, socketio

    print(
        f"FootballDatabase server: http://{settings.host}:{settings.port} "
        f"(tunnel={settings.tunnel_provider if with_tunnel else 'off'})",
        flush=True,
    )
    try:
        socketio.run(
            app,
            host=settings.host,
            port=settings.port,
            debug=settings.debug,
        )
    finally:
        if tunnel_process and tunnel_process.poll() is None:
            tunnel_process.terminate()


def tunnel_only() -> None:
    settings = load_settings()
    process = create_tunnel_provider(settings).start()

    def stop_process(*_args):
        if process.poll() is None:
            process.terminate()

    signal.signal(signal.SIGINT, stop_process)
    signal.signal(signal.SIGTERM, stop_process)
    process.wait()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="FootballDatabase server manager")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("serve", "public", "tunnel"),
        default="serve",
        help="serve: only app, public: app + tunnel, tunnel: only tunnel",
    )
    args = parser.parse_args(argv)
    if args.command == "tunnel":
        tunnel_only()
    else:
        serve(with_tunnel=args.command == "public")

