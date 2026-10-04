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
        "privacy-consent.js",
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
    assert "frame.srcdoc = prepared.source" in launcher
    assert "previousFrame?.remove()" in launcher
    assert "pageReady(sourceWindow)" in launcher
    assert "window.location.reload" not in launcher

    bridge = (bundle / "mobile-bridge.js").read_text(encoding="utf-8")
    assert 'form.getAttribute("action")' in bridge
    assert "form.action ||" not in bridge
    assert 'window.location.hash.replace(/^#/, "")' in bridge
    assert 'history.replaceState(null, "", `/index.html#${url.pathname}${url.search}`)' in bridge
    assert "window.location.reload()" in bridge
    assert "window.location.replace" not in bridge
    assert "document.activeElement.blur()" in bridge
    assert 'window.fetch("/api/mobile/socket-token"' in bridge
    assert "mobile_token: data.token" in bridge
    assert "navigate," in bridge and "reload," in bridge and "remoteUrl," in bridge
    assert "saveTransitionSnapshot" not in bridge
    assert "window.parent.MobileShell" in bridge
    assert "shell?.request" in bridge
    assert "return shell.request(target, requestOptions)" in bridge
    assert "shell?.navigate" in bridge
    assert "shell?.render" in bridge
    assert "document.documentElement.dataset.remotePath" in bridge

    viewport_css = (bundle / "static" / "fixed_viewport.css").read_text(encoding="utf-8")
    assert 'input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"])' in viewport_css
    assert "font-size: 16px;" in viewport_css
    assert "var(--app-viewport-height, 100svh)" in viewport_css
    assert "100dvh" not in viewport_css

    shell = (bundle / "index.html").read_text(encoding="utf-8")
    assert "https://edyn-football.onrender.com" not in shell
    assert 'src="launcher.js"' in shell
    assert 'id="launcher" aria-hidden="true"' in shell
    assert "#mobileTransitionSnapshot" not in shell
    assert "#mobileTransitionError" in shell
    assert "overflow:hidden;overscroll-behavior:none" in shell
    assert "body{position:fixed;inset:0}" in shell
    assert 'id="adPrivacyDialog"' in shell
    assert 'src="privacy-consent.js"' in shell
    privacy_consent = (bundle / "privacy-consent.js").read_text(encoding="utf-8")
    assert 'STORAGE_KEY = "football-ad-privacy-v1"' in privacy_consent
    assert '"personalized"' in privacy_consent
    assert '"non_personalized"' in privacy_consent
    launcher_css = (bundle / "launcher.css").read_text(encoding="utf-8")
    assert ".launcher.is-visible { display: block; }" in launcher_css

    scene_delegate = (ROOT / "mobile-assets" / "SceneDelegate.swift").read_text(encoding="utf-8")
    assert "FootballBridgeViewController" in scene_delegate
    assert "webView.isOpaque = false" in scene_delegate
    assert "webView.underPageBackgroundColor = appBackground" in scene_delegate
    assert "appWindow.backgroundColor = appBackground" in scene_delegate
    assert "scrollView.bounces = false" in scene_delegate
    assert "scrollView.alwaysBounceVertical = false" in scene_delegate
    assert "scrollView.alwaysBounceHorizontal = false" in scene_delegate
    assert "scrollView.contentInsetAdjustmentBehavior = .never" in scene_delegate
    ios_workflow = (ROOT / ".github" / "workflows" / "ios-unsigned-ipa.yml").read_text(encoding="utf-8")
    assert 'cp "mobile-assets/SceneDelegate.swift" "ios/App/App/SceneDelegate.swift"' in ios_workflow

    release_workflow = (ROOT / ".github" / "workflows" / "ios-testflight-release.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in release_workflow
    assert "runs-on: macos-26" in release_workflow
    assert "BUNDLE_ID: app.edynfootball.mobile" in release_workflow
    assert "APPLE_TEAM_ID: 6UV8K8XK57" in release_workflow
    assert 'APP_STORE_APP_ID: "6819015024"' in release_workflow
    assert "IOS_DISTRIBUTION_CERT_BASE64" in release_workflow
    assert "IOS_PROVISIONING_PROFILE_BASE64" in release_workflow
    assert "APP_STORE_CONNECT_API_KEY_BASE64" in release_workflow
    assert "ITSAppUsesNonExemptEncryption false" in release_workflow
    assert "GADIsAdManagerApp true" in release_workflow
    assert "Validate exported IPA metadata" in release_workflow
    assert "Package debug symbols" in release_workflow
    assert "xcodebuild" in release_workflow and "archive" in release_workflow
    assert "-exportArchive" in release_workflow
    assert "altool --validate-app" in release_workflow
    assert "altool --upload-app" in release_workflow
    assert "base64 -D" in release_workflow
    assert "find . -maxdepth" not in release_workflow
    assert "Clean signing material" in release_workflow

    mobile_ads = (bundle / "mobile-ads.js").read_text(encoding="utf-8")
    assert 'CONFIG_CACHE_KEY = "football-mobile-ad-config"' in mobile_ads
    assert 'INITIALIZED_KEY = "football-admob-initialized"' in mobile_ads
    assert 'sessionStorage.getItem(INITIALIZED_KEY) === "1"' in mobile_ads
    assert 'onRewardedVideoAdFailedToLoad' in mobile_ads
    assert 'errorMessage()' in mobile_ads
    assert 'config.testing || sessionStorage.getItem(CONSENT_KEY) !== "0"' in mobile_ads
    assert 'if (!allowed && !config.testing)' in mobile_ads
    assert "Promise.allSettled([prepare(), prepareRewarded()])" in mobile_ads
    assert "requestTrackingAuthorization" in mobile_ads
    assert 'npa: choice !== "personalized"' in mobile_ads
    assert "setStableViewportHeight()" in launcher
    assert "request: (input, options) => window.fetch(input, options)" in launcher
    assert 'style.setProperty("--app-viewport-height"' in launcher
    assert 'top: "env(safe-area-inset-top, 0px)"' in launcher
    assert 'height: "calc(100% - env(safe-area-inset-top, 0px))"' in launcher
    assert "frame.getBoundingClientRect().height" in launcher
    assert "window.requestAnimationFrame(() => window.requestAnimationFrame(() =>" in launcher
    assert "Bulunduğun ekran korunuyor." in launcher
    for script_name in ("heatmap.js", "missing_xi.js", "profile.js", "public_profile.js"):
        script = (bundle / "static" / script_name).read_text(encoding="utf-8")
        assert "MobileBridge.reload()" in script

    print({
        "local_web_dir": True,
        "remote_server_url_removed": True,
        "local_assets_present": True,
        "remote_scripts_blocked": True,
        "mobile_api_bridge_present": True,
        "forms_post_to_remote_route": True,
        "menu_navigation_uses_background_frame": True,
        "ios_input_focus_zoom_prevented": True,
        "transition_loader_hidden_until_error": True,
        "admob_initializes_once_per_app_session": True,
        "ads_preload_after_privacy_choice": True,
        "previous_screen_preserved_during_navigation": True,
        "connection_error_uses_overlay": True,
        "page_frames_are_disposed_between_routes": True,
        "ios_webview_background_is_dark": True,
    })


if __name__ == "__main__":
    main()
