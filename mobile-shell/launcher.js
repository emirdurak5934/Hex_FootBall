(() => {
  "use strict";

  const SERVER_URL = "https://edyn-football.onrender.com";
  const message = document.getElementById("message");
  const retryButton = document.getElementById("retryButton");

  function connect() {
    message.textContent = "Kalıcı sunucu açılıyor…";
    retryButton.classList.add("hidden");
    window.location.replace(SERVER_URL);
  }

  retryButton.addEventListener("click", connect);
  window.setTimeout(() => {
    message.textContent = "Bağlantı kurulamadıysa internetini kontrol edip tekrar dene.";
    retryButton.classList.remove("hidden");
  }, 8000);
  connect();
})();
