"""Build the self-contained Capacitor web bundle used by the iOS app."""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "mobile-shell"
DESTINATION = ROOT / "mobile-dist"
STATIC_SOURCE = ROOT / "static"
SOCKET_CLIENT = ROOT / "node_modules" / "socket.io-client" / "dist" / "socket.io.min.js"


def main():
    if not SOURCE.joinpath("index.html").is_file():
        raise SystemExit("mobile-shell/index.html bulunamadı.")
    if not SOCKET_CLIENT.is_file():
        raise SystemExit("Socket.IO istemcisi eksik. Önce pnpm install çalıştırın.")

    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    shutil.copytree(SOURCE, DESTINATION)
    shutil.copytree(STATIC_SOURCE, DESTINATION / "static")
    vendor = DESTINATION / "vendor"
    vendor.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOCKET_CLIENT, vendor / "socket.io.min.js")

    required = (
        DESTINATION / "index.html",
        DESTINATION / "launcher.js",
        DESTINATION / "mobile-bridge.js",
        DESTINATION / "mobile-ads.js",
        DESTINATION / "vendor" / "socket.io.min.js",
        DESTINATION / "static" / "game.js",
    )
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Mobil paket eksik dosyalar içeriyor: " + ", ".join(missing))
    print(f"Mobil arayüz paketi hazır: {DESTINATION}")


if __name__ == "__main__":
    main()
