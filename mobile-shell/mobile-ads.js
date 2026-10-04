(() => {
  "use strict";
  let config = {enabled: false, provider: "disabled", timeoutMs: 5000, loadTimeoutMs: 4500};
  let initialization = null;
  let preparedInterstitial = false;
  let preparedRewarded = false;
  const handled = new Set();
  const pending = new Map();
  const CONFIG_CACHE_KEY = "football-mobile-ad-config";
  const INITIALIZED_KEY = "football-admob-initialized";
  const CONSENT_KEY = "football-admob-can-request";

  let cachedConfig = null;
  try { cachedConfig = JSON.parse(sessionStorage.getItem(CONFIG_CACHE_KEY) || "null"); }
  catch (_) { sessionStorage.removeItem(CONFIG_CACHE_KEY); }
  if (cachedConfig) config = {...config, ...cachedConfig};

  const configReady = cachedConfig
    ? Promise.resolve(config)
    : fetch("/api/mobile/ad-config", {cache: "no-store"})
      .then(response => response.ok ? response.json() : Promise.reject(new Error("Reklam ayarı alınamadı.")))
      .then(value => {
        config = {...config, ...value};
        sessionStorage.setItem(CONFIG_CACHE_KEY, JSON.stringify(config));
        return config;
      })
      .catch(() => config);

  function admobPlugin() {
    const capacitor = window.Capacitor;
    return capacitor?.Plugins?.AdMob || capacitor?.registerPlugin?.("AdMob");
  }

  async function initialize() {
    await configReady;
    const admob = admobPlugin();
    if (!config.enabled || config.provider !== "admob" || !admob) return false;
    if (initialization) return initialization;
    initialization = (async () => {
      if (sessionStorage.getItem(INITIALIZED_KEY) === "1") {
        return sessionStorage.getItem(CONSENT_KEY) !== "0";
      }
      await admob.initialize({initializeForTesting: Boolean(config.testing), testingDevices: []});
      let consent = await admob.requestConsentInfo();
      if (!consent.canRequestAds && consent.isConsentFormAvailable) consent = await admob.showConsentForm();
      const allowed = Boolean(consent.canRequestAds);
      sessionStorage.setItem(INITIALIZED_KEY, "1");
      sessionStorage.setItem(CONSENT_KEY, allowed ? "1" : "0");
      return allowed;
    })().catch(() => {
      sessionStorage.removeItem(INITIALIZED_KEY);
      return false;
    });
    return initialization;
  }

  async function prepare() {
    if (preparedInterstitial) return true;
    if (!(await initialize()) || !config.adId) return false;
    const admob = admobPlugin();
    try {
      await admob.prepareInterstitial({adId: config.adId, isTesting: Boolean(config.testing)});
      preparedInterstitial = true;
      return true;
    } catch (_) { return false; }
  }

  async function show() {
    const loaded = await Promise.race([
      prepare(),
      new Promise(resolve => setTimeout(() => resolve(false), config.loadTimeoutMs)),
    ]);
    if (!loaded) return false;
    preparedInterstitial = false;
    try {
      await admobPlugin().showInterstitial({adId: config.adId});
      return true;
    } catch (_) { return false; }
    finally { setTimeout(prepare, 250); }
  }

  async function prepareRewarded() {
    if (preparedRewarded) return true;
    if (!(await initialize()) || !config.rewardedAdId) return false;
    try {
      await admobPlugin().prepareRewardVideoAd({
        adId: config.rewardedAdId,
        isTesting: Boolean(config.testing),
      });
      preparedRewarded = true;
      return true;
    } catch (_) { return false; }
  }

  async function showRewarded() {
    const loaded = await Promise.race([
      prepareRewarded(),
      new Promise(resolve => setTimeout(() => resolve(false), config.loadTimeoutMs)),
    ]);
    if (!loaded) return false;
    preparedRewarded = false;
    try {
      return Boolean(await admobPlugin().showRewardVideoAd({adId: config.rewardedAdId}));
    } catch (_) { return false; }
    finally { setTimeout(prepareRewarded, 250); }
  }

  async function privacyOptions() {
    await configReady;
    const admob = admobPlugin();
    if (!admob || !config.enabled) return false;
    try {
      await initialize();
      await admob.showPrivacyOptionsForm();
      const consent = await admob.requestConsentInfo();
      sessionStorage.setItem(CONSENT_KEY, consent.canRequestAds ? "1" : "0");
      return true;
    } catch (_) { return false; }
  }

  function overlay() {
    let node = document.getElementById("matchAdWaiting");
    if (node) return node;
    node = document.createElement("div");
    node.id = "matchAdWaiting";
    node.hidden = true;
    node.innerHTML = "<div><strong>MAÇ TAMAMLANDI</strong><span>Reklam hazırlanıyor…</span><small>En fazla 5 saniye</small></div>";
    const style = document.createElement("style");
    style.textContent = "#matchAdWaiting{position:fixed;inset:0;z-index:30000;display:grid;place-items:center;background:#050a12e8;color:#fff;font-family:Arial,sans-serif;text-align:center}#matchAdWaiting[hidden]{display:none}#matchAdWaiting div{padding:24px;border:1px solid #d4a94e66;border-radius:16px;background:#101824}#matchAdWaiting strong,#matchAdWaiting span,#matchAdWaiting small{display:block}#matchAdWaiting span{margin-top:10px}#matchAdWaiting small{margin-top:7px;color:#aab2bf}";
    document.head.appendChild(style);
    document.body.appendChild(node);
    return node;
  }

  function present(adBreak, reveal) {
    const decision = adBreak || {eligible: true, match_id: `local-${Date.now()}`, timeout_ms: config.timeoutMs};
    if (!decision.eligible) { reveal(); return; }
    const key = String(decision.match_id || `match-${Date.now()}`);
    if (handled.has(key)) { reveal(); return; }
    if (pending.has(key)) { pending.get(key).push(reveal); return; }
    pending.set(key, [reveal]);
    const wait = overlay();
    wait.hidden = false;
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      wait.hidden = true;
      handled.add(key);
      const callbacks = pending.get(key) || [];
      pending.delete(key);
      callbacks.forEach(callback => callback());
    };
    const timeout = Math.max(0, Math.min(5000, Number(decision.timeout_ms) || config.timeoutMs));
    const timer = setTimeout(finish, timeout);
    show().catch(() => false).finally(() => { clearTimeout(timer); finish(); });
  }

  window.FootballAdProvider = Object.freeze({show, prepare, showRewarded, prepareRewarded, privacyOptions});
  window.MatchAds = Object.freeze({present, reward: showRewarded, get config() { return config; }});
})();
