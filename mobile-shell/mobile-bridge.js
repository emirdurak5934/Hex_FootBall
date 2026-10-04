(() => {
  "use strict";
  const API_ORIGIN = document.documentElement.dataset.apiOrigin || "https://edyn-football.onrender.com";
  const nativeFetch = window.fetch.bind(window);
  const LOCAL_BASE_URL = document.baseURI || `${window.location.origin}/`;
  const LOCAL_ORIGIN = new URL(LOCAL_BASE_URL).origin;

  function hostShell() {
    try {
      return window.parent !== window ? window.parent.MobileShell : null;
    } catch (_) {
      return null;
    }
  }

  function currentUrl() {
    const path = document.documentElement.dataset.remotePath || "/";
    return new URL(path, API_ORIGIN).href;
  }

  function remoteUrl(input) {
    if (typeof input !== "string") return input;
    if (/^(data:|blob:|mailto:|tel:)/i.test(input)) return input;
    const parsed = new URL(input, LOCAL_BASE_URL);
    const localAsset = parsed.pathname.startsWith("/static/") || parsed.pathname.startsWith("/vendor/") ||
      parsed.pathname.startsWith("/mobile-") || parsed.pathname === "/index.html";
    if (parsed.origin === LOCAL_ORIGIN && !localAsset) {
      return `${API_ORIGIN}${parsed.pathname}${parsed.search}${parsed.hash}`;
    }
    return input;
  }

  window.fetch = (input, options = {}) => {
    const requestOptions = {
      credentials: "include",
      ...options,
      headers: {"X-Football-Mobile-Shell": "1", ...(options.headers || {})},
    };
    const target = remoteUrl(input);
    const shell = hostShell();
    if (shell?.request) return shell.request(target, requestOptions);
    return nativeFetch(target, requestOptions);
  };

  document.querySelectorAll('script[type="application/json"][data-mobile-config]').forEach(node => {
    try {
      window[node.dataset.mobileConfig] = JSON.parse(node.textContent);
    } catch (error) {
      console.error(`Mobil yapılandırma okunamadı: ${node.dataset.mobileConfig}`, error);
    }
  });

  if (typeof window.io === "function") {
    const socketFactory = window.io;
    window.io = (uri, options = {}) => {
      const socketOptions = {
        withCredentials: true,
        transports: ["websocket", "polling"],
        ...options,
      };
      if (!socketOptions.auth) {
        socketOptions.auth = callback => {
          window.fetch("/api/mobile/socket-token", {cache: "no-store"})
            .then(response => response.ok ? response.json() : Promise.reject(new Error("Socket kimliği alınamadı.")))
            .then(data => callback({mobile_token: data.token}))
            .catch(() => callback({}));
        };
      }
      return socketFactory(uri || API_ORIGIN, socketOptions);
    };
  }

  function navigate(target) {
    const url = new URL(target || "/", API_ORIGIN);
    if (url.origin !== API_ORIGIN) {
      window.open(url.href, "_blank", "noopener,noreferrer");
      return;
    }
    const shell = hostShell();
    if (shell?.navigate) {
      shell.navigate(url.href);
      return;
    }
    history.replaceState(null, "", `/index.html#${url.pathname}${url.search}`);
    window.location.reload();
  }

  function reload() {
    const shell = hostShell();
    if (shell?.reload) {
      shell.reload(currentUrl());
      return;
    }
    window.location.reload();
  }

  async function submitForm(form) {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    const method = String(form.method || "GET").toUpperCase();
    const currentPath = document.documentElement.dataset.remotePath || window.location.hash.replace(/^#/, "") || "/";
    const currentRemoteUrl = new URL(currentPath, API_ORIGIN);
    const action = form.getAttribute("action");
    const target = new URL(action || currentRemoteUrl.href, API_ORIGIN);
    const values = new FormData(form);
    if (method === "GET") {
      target.search = new URLSearchParams(values).toString();
      navigate(target.href);
      return;
    }
    const response = await window.fetch(target.href, {
      method,
      headers: {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
      body: new URLSearchParams(values).toString(),
    });
    const responseHtml = await response.text();
    const responseUrl = response.url || target.href;
    const shell = hostShell();
    if (shell?.render) {
      shell.render(responseHtml, responseUrl);
      return;
    }
    const fallbackUrl = new URL(responseUrl, API_ORIGIN);
    history.replaceState(null, "", `/index.html#${fallbackUrl.pathname}${fallbackUrl.search}`);
    window.location.reload();
  }

  document.addEventListener("click", event => {
    const anchor = event.target.closest("a[href]");
    if (!anchor || event.defaultPrevented || anchor.target === "_blank") return;
    const href = anchor.getAttribute("href");
    if (!href || href.startsWith("#") || /^(mailto:|tel:)/i.test(href)) return;
    const url = new URL(href, API_ORIGIN);
    if (url.origin !== API_ORIGIN) return;
    event.preventDefault();
    navigate(url.href);
  });

  document.addEventListener("submit", event => {
    if (event.defaultPrevented) return;
    const form = event.target.closest("form");
    if (!form) return;
    event.preventDefault();
    submitForm(form).catch(error => {
      console.error(error);
      window.alert("İşlem sırasında bağlantı hatası oluştu. Tekrar dene.");
    });
  });

  function replaceCurrentPath(target) {
    const shell = hostShell();
    if (shell?.replaceCurrentPath) {
      shell.replaceCurrentPath(target);
      document.documentElement.dataset.remotePath = new URL(target || "/", API_ORIGIN).pathname;
      return;
    }
    history.replaceState({}, "", target);
  }

  window.MobileBridge = Object.freeze({
    API_ORIGIN,
    navigate,
    reload,
    remoteUrl,
    currentUrl,
    replaceCurrentPath,
  });
})();
