(() => {
  "use strict";
  const API_ORIGIN = "https://edyn-football.onrender.com";
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

  function addRuntimeScripts(documentNode, originalScripts) {
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
    for (const source of [...new Set(scripts)]) {
      const script = documentNode.createElement("script");
      script.src = source;
      script.defer = false;
      documentNode.body.appendChild(script);
    }
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
    addRuntimeScripts(page, originalScripts);
    try {
      const finalUrl = new URL(responseUrl || API_ORIGIN, API_ORIGIN);
      history.replaceState(null, "", `/index.html#${finalUrl.pathname}${finalUrl.search}`);
    } catch (_) {}
    return `<!doctype html>${page.documentElement.outerHTML}`;
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
      const rendered = prepareDocument(html, finalUrl);
      document.open();
      document.write(rendered);
      document.close();
    } catch (error) {
      console.error(error);
      message.textContent = "Bağlantı kurulamadı. İnternetini kontrol edip yeniden dene.";
      retryButton.classList.remove("hidden");
    }
  }

  retryButton.addEventListener("click", connect);
  connect();
})();
