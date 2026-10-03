(() => {
  "use strict";
  const splash = document.getElementById("launchSplash");
  if (!splash) return;
  const key = "edyn_games_launch_seen";
  if (sessionStorage.getItem(key)) {
    splash.remove();
    return;
  }
  sessionStorage.setItem(key, "1");
  window.setTimeout(() => {
    splash.classList.add("is-leaving");
    window.setTimeout(() => splash.remove(), 450);
  }, 3000);
})();
