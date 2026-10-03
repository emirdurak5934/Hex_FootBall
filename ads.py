"""Match-end advertising policy and browser integration.

All provider-specific advertising behavior lives in this module.  The main
application only marks a match outcome and loads the client served here.
"""

import json
import os
import uuid

from flask import Blueprint, Response


ADS_TIMEOUT_MS = int(os.environ.get("FOOTBALL_AD_TIMEOUT_MS", "5000"))
ADS_MODE = os.environ.get("FOOTBALL_AD_MODE", "test").strip().lower()
ADS_ENABLED = os.environ.get("FOOTBALL_ADS_ENABLED", "1" if ADS_MODE == "test" else "0") == "1"
ADS_PROVIDER = "admob" if ADS_ENABLED else "disabled"
IOS_TEST_INTERSTITIAL_ID = "ca-app-pub-3940256099942544/4411468910"


def _local_interstitial_id():
    """Read the developer's local ID file without making it source-controlled config."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reklam_kimligi.txt")
    try:
        with open(path, "r", encoding="utf-8") as source:
            for line in source:
                if "/" in line and "ca-app-pub-" in line:
                    return line.split(":", 1)[-1].strip()
    except OSError:
        pass
    return ""


ADS_UNIT_PATH = (
    IOS_TEST_INTERSTITIAL_ID
    if ADS_MODE == "test"
    else os.environ.get("FOOTBALL_AD_UNIT_PATH", "").strip() or _local_interstitial_id()
)

COMPLETED_OUTCOMES = {"completed_board", "completed_timeout", "completed_win", "completed_draw"}


def mark_match_outcome(state, game_mode, outcome, match_id=None):
    """Attach the stable ad decision consumed by every game client."""
    state["ad_break"] = {
        "eligible": outcome in COMPLETED_OUTCOMES,
        "outcome": outcome,
        "game_mode": game_mode,
        "match_id": str(match_id or uuid.uuid4().hex),
        "timeout_ms": ADS_TIMEOUT_MS,
    }
    return state["ad_break"]


def public_ad_break(state):
    value = state.get("ad_break")
    return dict(value) if value else None


def _client_source():
    config = json.dumps({
        "enabled": ADS_ENABLED,
        "provider": ADS_PROVIDER,
        "unitPath": ADS_UNIT_PATH,
        "timeoutMs": ADS_TIMEOUT_MS,
    })
    return f"""
(() => {{
  'use strict';
  const config = {config};
  const handled = new Set();
  const pending = new Map();

  function overlay() {{
    let node = document.getElementById('matchAdWaiting');
    if (node) return node;
    node = document.createElement('div');
    node.id = 'matchAdWaiting';
    node.hidden = true;
    node.innerHTML = '<div><strong>MAÇ TAMAMLANDI</strong><span>Reklam hazırlanıyor…</span><small>En fazla 5 saniye</small></div>';
    const style = document.createElement('style');
    style.textContent = '#matchAdWaiting{{position:fixed;inset:0;z-index:30000;display:grid;place-items:center;background:#050a12e8;color:#fff;font-family:Arial,sans-serif;text-align:center}}#matchAdWaiting[hidden]{{display:none}}#matchAdWaiting div{{padding:24px;border:1px solid #d4a94e66;border-radius:16px;background:#101824}}#matchAdWaiting strong,#matchAdWaiting span,#matchAdWaiting small{{display:block}}#matchAdWaiting span{{margin-top:10px}}#matchAdWaiting small{{margin-top:7px;color:#aab2bf}}';
    document.head.appendChild(style);
    document.body.appendChild(node);
    return node;
  }}

  async function requestProviderAd(context) {{
    if (!config.enabled || !config.unitPath) return false;
    const provider = window.FootballAdProvider;
    if (!provider || typeof provider.show !== 'function') return false;
    return Boolean(await provider.show({{...context, config}}));
  }}

  function present(adBreak, reveal) {{
    const decision = adBreak || {{eligible: true, match_id: `local-${{Date.now()}}`, timeout_ms: config.timeoutMs}};
    if (!decision.eligible) {{ reveal(); return; }}
    const key = String(decision.match_id || `match-${{Date.now()}}`);
    if (handled.has(key)) {{ reveal(); return; }}
    if (pending.has(key)) {{ pending.get(key).push(reveal); return; }}
    pending.set(key, [reveal]);
    const wait = overlay();
    wait.hidden = false;
    let finished = false;
    const finish = () => {{
      if (finished) return;
      finished = true;
      wait.hidden = true;
      handled.add(key);
      const callbacks = pending.get(key) || [];
      pending.delete(key);
      callbacks.forEach(callback => callback());
    }};
    const timeout = Math.max(0, Math.min(5000, Number(decision.timeout_ms) || config.timeoutMs));
    const timer = setTimeout(finish, timeout);
    requestProviderAd(decision).catch(() => false).finally(() => {{ clearTimeout(timer); finish(); }});
  }}

  window.MatchAds = Object.freeze({{present, config: Object.freeze(config)}});
}})();
"""


def _native_provider_source():
    config = json.dumps({
        "enabled": ADS_ENABLED,
        "provider": ADS_PROVIDER,
        "adId": ADS_UNIT_PATH,
        "testing": ADS_MODE == "test",
        "loadTimeoutMs": min(4500, ADS_TIMEOUT_MS),
    })
    return f"""
(() => {{
  'use strict';
  const config = Object.freeze({config});
  const capacitor = window.Capacitor;
  const admob = capacitor?.Plugins?.AdMob || capacitor?.registerPlugin?.('AdMob');
  let initialization = null;
  let preparation = null;
  let preparedAdId = null;

  function nativeAvailable() {{
    return Boolean(
      config.enabled && config.provider === 'admob' && config.adId && admob &&
      (typeof capacitor.isNativePlatform !== 'function' || capacitor.isNativePlatform())
    );
  }}

  async function initialize() {{
    if (!nativeAvailable()) return false;
    if (initialization) return initialization;
    initialization = (async () => {{
      await admob.initialize({{
        initializeForTesting: config.testing,
        testingDevices: [],
      }});
      let consent = await admob.requestConsentInfo();
      if (!consent.canRequestAds && consent.isConsentFormAvailable) {{
        consent = await admob.showConsentForm();
      }}
      return Boolean(consent.canRequestAds);
    }})().catch(() => false);
    return initialization;
  }}

  async function prepare() {{
    if (preparedAdId) return true;
    if (preparation) return preparation;
    preparation = (async () => {{
      if (!(await initialize())) return false;
      const loaded = await admob.prepareInterstitial({{
        adId: config.adId,
        isTesting: config.testing,
      }});
      preparedAdId = loaded?.adUnitId || config.adId;
      return true;
    }})().catch(() => false).finally(() => {{ preparation = null; }});
    return preparation;
  }}

  async function show() {{
    if (!nativeAvailable()) return false;
    const loaded = await Promise.race([
      prepare(),
      new Promise(resolve => setTimeout(() => resolve(false), config.loadTimeoutMs)),
    ]);
    if (!loaded || !preparedAdId) return false;
    const adId = preparedAdId;
    preparedAdId = null;
    try {{
      await admob.showInterstitial({{adId}});
      return true;
    }} catch (error) {{
      return false;
    }} finally {{
      setTimeout(() => {{ prepare(); }}, 250);
    }}
  }}

  async function privacyOptions() {{
    if (!(await initialize())) return false;
    try {{
      await admob.showPrivacyOptionsForm();
      return true;
    }} catch (error) {{
      return false;
    }}
  }}

  window.FootballAdProvider = Object.freeze({{show, prepare, privacyOptions, config}});
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', () => {{ prepare(); }}, {{once: true}});
  }} else {{
    prepare();
  }}
}})();
"""


def register_ads(app):
    blueprint = Blueprint("match_ads", __name__)

    @blueprint.get("/ads/client.js")
    def client_script():
        return Response(_client_source(), mimetype="application/javascript", headers={"Cache-Control": "no-store"})

    @blueprint.get("/ads/native-provider.js")
    def native_provider_script():
        return Response(
            _native_provider_source(),
            mimetype="application/javascript",
            headers={"Cache-Control": "no-store"},
        )

    app.register_blueprint(blueprint)
