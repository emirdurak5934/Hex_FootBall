(() => {
  "use strict";
  const API_ORIGIN = "https://edyn-football.onrender.com";
  const TRANSITION_SNAPSHOT_KEY = "football-mobile-transition-snapshot";

  function restoreTransitionSnapshot() {
    const snapshot = sessionStorage.getItem(TRANSITION_SNAPSHOT_KEY);
    sessionStorage.removeItem(TRANSITION_SNAPSHOT_KEY);
    if (!snapshot) return null;
    const frame = document.createElement("iframe");
    frame.id = "mobileTransitionSnapshot";
    frame.setAttribute("sandbox", "allow-same-origin");
    frame.setAttribute("aria-hidden", "true");
    Object.assign(frame.style, {
      position: "fixed",
      inset: "0",
      zIndex: "90000",
      width: "100%",
      height: "100%",
      border: "0",
      background: "#070b13",
      pointerEvents: "none",
      opacity: "1",
      transition: "opacity 120ms ease-out",
    });
    frame.srcdoc = snapshot;
    document.body.appendChild(frame);
    return frame;
  }

  const transitionSnapshot = restoreTransitionSnapshot();
  const message = document.getElementById("message");
  const retryButton = document.getElementById("retryButton");

  function requestedPath() {
    const raw = window.location.hash.replace(/^#/, "");
    return raw && raw.startsWith("/") ? raw : "/";
  }

  function localAsset(path) {
    const url = new URL(path, API_ORIGIN);
    return url.pathname.startsWith("/static/") ? `${url.pathname}${url.search}` : path;
  }

  function runtimeScripts(originalScripts) {
    const scripts = [];
    if (originalScripts.some(script => String(script.src || "").includes("socket.io"))) {
      scripts.push("/vendor/socket.io.min.js");
    }
    scripts.push("/mobile-bridge.js", "/mobile-ads.js");
    for (const script of originalScripts) {
      if (!script.src) continue;
      const source = new URL(script.src, API_ORIGIN);
      if (source.pathname.startsWith("/static/")) scripts.push(`${source.pathname}${source.search}`);
    }
    return [...new Set(scripts)];
  }

  function prepareDocument(html, responseUrl) {
    const page = new DOMParser().parseFromString(html, "text/html");
    const originalScripts = [...page.querySelectorAll("script")];
    for (const script of originalScripts) {
      if (script.type === "application/json" && script.dataset.mobileConfig) continue;
      script.remove();
    }
    page.querySelectorAll('meta[http-equiv="Content-Security-Policy"],base').forEach(node => node.remove());
    page.querySelectorAll("link[href]").forEach(link => {
      link.setAttribute("href", localAsset(link.getAttribute("href")));
    });
    page.querySelectorAll("img[src],video[src],source[src]").forEach(node => {
      node.setAttribute("src", localAsset(node.getAttribute("src")));
    });
    page.querySelectorAll("*").forEach(node => {
      for (const attribute of [...node.attributes]) {
        if (attribute.name.toLowerCase().startsWith("on")) node.removeAttribute(attribute.name);
      }
    });
    page.documentElement.dataset.mobileShell = "true";
    page.documentElement.dataset.apiOrigin = API_ORIGIN;
    try {
      const finalUrl = new URL(responseUrl || API_ORIGIN, API_ORIGIN);
      history.replaceState(null, "", `/index.html#${finalUrl.pathname}${finalUrl.search}`);
    } catch (_) {}
    return {page, scripts: runtimeScripts(originalScripts)};
  }

  function importedChildren(parent) {
    return [...parent.childNodes].map(node => document.importNode(node, true));
  }

  function loadScript(source) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = source;
      script.async = false;
      script.addEventListener("load", resolve, {once: true});
      script.addEventListener("error", () => reject(new Error(`${source} yüklenemedi.`)), {once: true});
      document.body.appendChild(script);
    });
  }

  async function renderDocument(html, responseUrl) {
    const {page, scripts} = prepareDocument(html, responseUrl);
    const snapshotFrame = transitionSnapshot?.isConnected ? transitionSnapshot : null;
    document.title = page.title;
    document.documentElement.lang = page.documentElement.lang || "tr";
    document.documentElement.dataset.mobileShell = "true";
    document.documentElement.dataset.apiOrigin = API_ORIGIN;
    document.head.replaceChildren(...importedChildren(page.head));
    document.body.replaceChildren(...importedChildren(page.body));
    if (snapshotFrame) document.body.appendChild(snapshotFrame);
    for (const source of scripts) await loadScript(source);
    if (snapshotFrame) {
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      snapshotFrame.style.opacity = "0";
      window.setTimeout(() => snapshotFrame.remove(), 140);
    }
  }

  function showFailure(error) {
    console.error(error);
    if (transitionSnapshot?.isConnected) {
      let errorModal = document.getElementById("mobileTransitionError");
      if (!errorModal) {
        errorModal = document.createElement("section");
        errorModal.id = "mobileTransitionError";
        errorModal.setAttribute("role", "alertdialog");
        errorModal.setAttribute("aria-modal", "true");
        const card = document.createElement("div");
        const title = document.createElement("h2");
        title.textContent = "Bağlantı kurulamadı";
        const detail = document.createElement("p");
        detail.textContent = "Bulunduğun ekran korunuyor. İnternetini kontrol edip tekrar dene.";
        const retry = document.createElement("button");
        retry.type = "button";
        retry.textContent = "TEKRAR DENE";
        retry.addEventListener("click", () => {
          errorModal.remove();
          connect();
        });
        card.append(title, detail, retry);
        errorModal.appendChild(card);
        document.body.appendChild(errorModal);
      }
      return;
    }
    const activeMessage = document.getElementById("message");
    const activeRetry = document.getElementById("retryButton");
    if (activeMessage && activeRetry) {
      const activeLauncher = document.getElementById("launcher");
      activeLauncher?.classList.add("is-visible");
      activeLauncher?.removeAttribute("aria-hidden");
      activeMessage.textContent = "Bağlantı kurulamadı. İnternetini kontrol edip yeniden dene.";
      activeRetry.classList.remove("hidden");
      return;
    }
    document.head.replaceChildren();
    const style = document.createElement("style");
    style.textContent = "body{margin:0;min-height:100dvh;display:grid;place-items:center;padding:24px;background:#000;color:#fff;font:16px -apple-system,BlinkMacSystemFont,sans-serif;text-align:center}main{max-width:420px}button{min-height:48px;padding:0 22px;border:0;border-radius:12px;background:#d4a94e;color:#090d13;font-weight:900}";
    document.head.appendChild(style);
    const main = document.createElement("main");
    const title = document.createElement("h1");
    title.textContent = "Uygulama açılamadı";
    const detail = document.createElement("p");
    detail.textContent = "Sunucu bağlantısı veya yerel arayüz yüklenemedi.";
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "TEKRAR DENE";
    retry.addEventListener("click", () => window.location.reload());
    main.append(title, detail, retry);
    document.body.replaceChildren(main);
  }

  async function connect() {
    message.textContent = "Sunucuya bağlanılıyor…";
    retryButton.classList.add("hidden");
    try {
      const pendingHtml = sessionStorage.getItem("football-mobile-pending-html");
      const pendingUrl = sessionStorage.getItem("football-mobile-pending-url");
      sessionStorage.removeItem("football-mobile-pending-html");
      sessionStorage.removeItem("football-mobile-pending-url");
      let html = pendingHtml;
      let finalUrl = pendingUrl;
      if (!html) {
        const response = await fetch(`${API_ORIGIN}${requestedPath()}`, {
          credentials: "include",
          headers: {"X-Football-Mobile-Shell": "1"},
          cache: "no-store",
        });
        if (!response.ok) throw new Error(`Sunucu ${response.status} yanıtı verdi.`);
        html = await response.text();
        finalUrl = response.url;
      }
      await renderDocument(html, finalUrl);
    } catch (error) {
      showFailure(error);
    }
  }

  retryButton.addEventListener("click", connect);
  connect();
})();
