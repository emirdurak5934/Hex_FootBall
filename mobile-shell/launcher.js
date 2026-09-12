(() => {
  "use strict";

  const DEFAULT_URL = "https://diving-responsibility-annex-look.trycloudflare.com";
  const STORAGE_KEY = "edyn_football_server_url";
  const input = document.getElementById("serverUrl");
  const message = document.getElementById("message");
  const button = document.getElementById("connectButton");

  input.value = localStorage.getItem(STORAGE_KEY) || DEFAULT_URL;

  function normalizeServerUrl(value) {
    const url = new URL(value.trim());
    if (url.protocol !== "https:") {
      throw new Error("Sunucu adresi HTTPS ile başlamalıdır.");
    }
    const allowed = url.hostname.endsWith(".trycloudflare.com") ||
      url.hostname === "api.edynfootball.app";
    if (!allowed) {
      throw new Error("Yalnız EDYN Football veya Cloudflare test adresi kullanılabilir.");
    }
    url.pathname = "/";
    url.search = "";
    url.hash = "";
    return url.toString().replace(/\/$/, "");
  }

  function connect() {
    try {
      const serverUrl = normalizeServerUrl(input.value);
      localStorage.setItem(STORAGE_KEY, serverUrl);
      message.textContent = "Sunucu açılıyor…";
      window.location.assign(serverUrl);
    } catch (error) {
      message.textContent = error.message;
    }
  }

  button.addEventListener("click", connect);
  input.addEventListener("keydown", event => {
    if (event.key === "Enter") connect();
  });
})();
