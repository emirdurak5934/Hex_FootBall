(() => {
  "use strict";
  const API_ORIGIN = "https://edyn-football.onrender.com";
  const FRAME_READY_TIMEOUT_MS = 15000;
  const message = document.getElementById("message");
  const retryButton = document.getElementById("retryButton");
  const launcher = document.getElementById("launcher");
  let activeFrame = null;
  let pendingFrame = null;
  let pendingTimeout = null;
  let navigationSequence = 0;
  let navigationController = null;

  function setStableViewportHeight() {
    const height = Math.round(window.innerHeight);
    if (height > 0) {
      document.documentElement.style.setProperty("--app-viewport-height", `${height}px`);
    }
  }

  setStableViewportHeight();
  window.addEventListener("orientationchange", () => {
    window.setTimeout(setStableViewportHeight, 250);
  });

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

  function preparedFrameDocument(html, responseUrl) {
    const page = new DOMParser().parseFromString(html, "text/html");
    const originalScripts = [...page.querySelectorAll("script")];
    for (const script of originalScripts) {
      if (script.type === "application/json" && script.dataset.mobileConfig) continue;
      script.remove();
    }
    page.querySelectorAll('meta[http-equiv="Content-Security-Policy"],base').forEach(node => node.remove());

    const base = page.createElement("base");
    base.href = `${window.location.origin}/`;
    page.head.prepend(base);
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

    const finalUrl = new URL(responseUrl || API_ORIGIN, API_ORIGIN);
    page.documentElement.dataset.mobileShell = "true";
    page.documentElement.dataset.apiOrigin = API_ORIGIN;
    page.documentElement.dataset.remotePath = `${finalUrl.pathname}${finalUrl.search}`;

    const viewportStyle = page.createElement("style");
    viewportStyle.dataset.mobileViewport = "true";
    viewportStyle.textContent = `:root{--app-viewport-height:${Math.round(window.innerHeight)}px}`;
    page.head.appendChild(viewportStyle);

    const capacitorBootstrap = page.createElement("script");
    capacitorBootstrap.textContent = "if(!window.Capacitor&&window.parent!==window&&window.parent.Capacitor){window.Capacitor=window.parent.Capacitor;}";
    page.body.appendChild(capacitorBootstrap);
    for (const source of runtimeScripts(originalScripts)) {
      const script = page.createElement("script");
      script.src = source;
      page.body.appendChild(script);
    }
    const readySignal = page.createElement("script");
    readySignal.textContent = "window.parent.MobileShell.pageReady(window);";
    page.body.appendChild(readySignal);
    return {source: `<!doctype html>${page.documentElement.outerHTML}`, finalUrl};
  }

  function removePendingFrame() {
    if (pendingTimeout !== null) {
      window.clearTimeout(pendingTimeout);
      pendingTimeout = null;
    }
    pendingFrame?.remove();
    pendingFrame = null;
  }

  function createFrame(html, responseUrl, sequence) {
    const prepared = preparedFrameDocument(html, responseUrl);
    if (sequence !== navigationSequence) return;
    removePendingFrame();

    const frame = document.createElement("iframe");
    frame.className = "mobile-page-frame";
    frame.title = prepared.finalUrl.pathname === "/" ? "Football Match: HEX" : "Oyun ekranı";
    frame.dataset.navigationSequence = String(sequence);
    Object.assign(frame.style, {
      position: "fixed",
      inset: "0",
      zIndex: "1",
      width: "100%",
      height: "100%",
      border: "0",
      background: "#070b13",
      visibility: "hidden",
    });
    pendingFrame = frame;
    document.body.appendChild(frame);
    frame.srcdoc = prepared.source;
    pendingTimeout = window.setTimeout(() => {
      if (pendingFrame !== frame) return;
      removePendingFrame();
      showFailure(new Error("Yeni ekran zamanında hazırlanamadı."));
    }, FRAME_READY_TIMEOUT_MS);
  }

  function pageReady(sourceWindow) {
    const frame = pendingFrame;
    if (!frame || frame.contentWindow !== sourceWindow) return;
    const sequence = Number(frame.dataset.navigationSequence);
    if (sequence !== navigationSequence) {
      frame.remove();
      return;
    }
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
      if (pendingFrame !== frame) return;
      if (pendingTimeout !== null) window.clearTimeout(pendingTimeout);
      pendingTimeout = null;
      const previousFrame = activeFrame;
      activeFrame = frame;
      pendingFrame = null;
      frame.style.visibility = "visible";
      previousFrame?.remove();
      launcher.classList.remove("is-visible");
      launcher.setAttribute("aria-hidden", "true");
      document.getElementById("mobileTransitionError")?.remove();
    }));
  }

  async function loadRoute(target, providedHtml = null, providedUrl = null) {
    const url = new URL(target || requestedPath(), API_ORIGIN);
    if (url.origin !== API_ORIGIN) {
      window.open(url.href, "_blank", "noopener,noreferrer");
      return;
    }

    navigationSequence += 1;
    const sequence = navigationSequence;
    navigationController?.abort();
    navigationController = new AbortController();
    removePendingFrame();
    history.replaceState(null, "", `/index.html#${url.pathname}${url.search}`);
    retryButton.classList.add("hidden");
    message.textContent = "Sunucuya bağlanılıyor…";

    try {
      let html = providedHtml;
      let finalUrl = providedUrl || url.href;
      if (html === null) {
        const response = await fetch(url.href, {
          credentials: "include",
          headers: {"X-Football-Mobile-Shell": "1"},
          cache: "no-store",
          signal: navigationController.signal,
        });
        if (!response.ok) throw new Error(`Sunucu ${response.status} yanıtı verdi.`);
        html = await response.text();
        finalUrl = response.url || url.href;
      }
      if (sequence !== navigationSequence) return;
      const resolved = new URL(finalUrl, API_ORIGIN);
      history.replaceState(null, "", `/index.html#${resolved.pathname}${resolved.search}`);
      createFrame(html, resolved.href, sequence);
    } catch (error) {
      if (error?.name === "AbortError") return;
      if (sequence === navigationSequence) showFailure(error);
    }
  }

  function showFailure(error) {
    console.error(error);
    if (activeFrame) {
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
          loadRoute(requestedPath());
        });
        card.append(title, detail, retry);
        errorModal.appendChild(card);
        document.body.appendChild(errorModal);
      }
      return;
    }
    launcher.classList.add("is-visible");
    launcher.removeAttribute("aria-hidden");
    message.textContent = "Bağlantı kurulamadı. İnternetini kontrol edip yeniden dene.";
    retryButton.classList.remove("hidden");
  }

  function replaceCurrentPath(target) {
    const url = new URL(target || "/", API_ORIGIN);
    if (url.origin === API_ORIGIN) {
      history.replaceState(null, "", `/index.html#${url.pathname}${url.search}`);
    }
  }

  window.MobileShell = Object.freeze({
    navigate: target => loadRoute(target),
    render: (html, responseUrl) => loadRoute(responseUrl || requestedPath(), html, responseUrl),
    reload: target => loadRoute(target || requestedPath()),
    replaceCurrentPath,
    pageReady,
  });

  retryButton.addEventListener("click", () => loadRoute(requestedPath()));
  loadRoute(requestedPath());
})();
