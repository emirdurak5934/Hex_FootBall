(() => {
  "use strict";
  const API_ORIGIN = document.documentElement.dataset.apiOrigin || "https://edyn-football.onrender.com";
  const nativeFetch = window.fetch.bind(window);

  function remoteUrl(input) {
    if (typeof input !== "string") return input;
    if (/^(data:|blob:|mailto:|tel:)/i.test(input)) return input;
    const parsed = new URL(input, window.location.origin);
    const localAsset = parsed.pathname.startsWith("/static/") || parsed.pathname.startsWith("/vendor/") ||
      parsed.pathname.startsWith("/mobile-") || parsed.pathname === "/index.html";
    if (parsed.origin === window.location.origin && !localAsset) {
      return `${API_ORIGIN}${parsed.pathname}${parsed.search}${parsed.hash}`;
    }
    return input;
  }

  window.fetch = (input, options = {}) => nativeFetch(remoteUrl(input), {
    credentials: "include",
    ...options,
    headers: {"X-Football-Mobile-Shell": "1", ...(options.headers || {})},
  });

  document.querySelectorAll('script[type="application/json"][data-mobile-config]').forEach(node => {
    try {
      window[node.dataset.mobileConfig] = JSON.parse(node.textContent);
    } catch (error) {
      console.error(`Mobil yapılandırma okunamadı: ${node.dataset.mobileConfig}`, error);
    }
  });

  if (typeof window.io === "function") {
    const socketFactory = window.io;
    window.io = (uri, options = {}) => socketFactory(uri || API_ORIGIN, {
      withCredentials: true,
      transports: ["websocket", "polling"],
      ...options,
    });
  }

  function navigate(target) {
    const url = new URL(target || "/", API_ORIGIN);
    if (url.origin !== API_ORIGIN) {
      window.open(url.href, "_blank", "noopener,noreferrer");
      return;
    }
    window.location.replace(`/index.html#${url.pathname}${url.search}`);
  }

  async function submitForm(form) {
    const method = String(form.method || "GET").toUpperCase();
    const target = new URL(form.action || API_ORIGIN, API_ORIGIN);
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
    sessionStorage.setItem("football-mobile-pending-html", await response.text());
    sessionStorage.setItem("football-mobile-pending-url", response.url || target.href);
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

  window.MobileBridge = Object.freeze({API_ORIGIN, navigate, remoteUrl});
})();
