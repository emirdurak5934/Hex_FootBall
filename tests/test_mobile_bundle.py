"""Guardrails for the self-contained Capacitor web bundle."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_mobile_bundle.py")],
        cwd=ROOT,
        check=True,
    )

    config = json.loads((ROOT / "capacitor.config.json").read_text(encoding="utf-8"))
    assert config["webDir"] == "mobile-dist"
    assert "url" not in config.get("server", {})
    assert config["plugins"]["CapacitorHttp"]["enabled"] is True
    assert config["plugins"]["CapacitorCookies"]["enabled"] is True

    bundle = ROOT / "mobile-dist"
    required = (
        "index.html",
        "launcher.js",
        "mobile-bridge.js",
        "mobile-ads.js",
        "vendor/socket.io.min.js",
        "static/game.js",
        "static/heatmap.js",
        "static/missing_xi.js",
        "static/tiki_taka.js",
    )
    for relative_path in required:
        assert (bundle / relative_path).is_file(), relative_path

    launcher = (bundle / "launcher.js").read_text(encoding="utf-8")
    assert "script.remove()" in launcher
    assert 'script.type === "application/json"' in launcher
    assert 'scripts.push("/vendor/socket.io.min.js")' in launcher
    assert 'scripts.push("/mobile-bridge.js", "/mobile-ads.js")' in launcher
    assert "document.write" not in launcher
    assert "document.body.replaceChildren" in launcher

    bridge = (bundle / "mobile-bridge.js").read_text(encoding="utf-8")
    assert 'form.getAttribute("action")' in bridge
    assert "form.action ||" not in bridge
    assert 'window.location.hash.replace(/^#/, "")' in bridge
    assert 'history.replaceState(null, "", `/index.html#${url.pathname}${url.search}`)' in bridge
    assert "window.location.reload()" in bridge
    assert "window.location.replace" not in bridge

    shell = (bundle / "index.html").read_text(encoding="utf-8")
    assert "https://edyn-football.onrender.com" not in shell
    assert 'src="launcher.js"' in shell

    print({
        "local_web_dir": True,
        "remote_server_url_removed": True,
        "local_assets_present": True,
        "remote_scripts_blocked": True,
        "mobile_api_bridge_present": True,
        "forms_post_to_remote_route": True,
        "menu_navigation_forces_shell_reload": True,
        "document_replacement_is_webview_safe": True,
    })


if __name__ == "__main__":
    main()
