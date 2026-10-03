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

  const video = document.getElementById("launchVideo");
  let finished = false;
  const finish = () => {
    if (finished) return;
    finished = true;
    splash.classList.add("is-leaving");
    window.setTimeout(() => splash.remove(), 450);
  };

  let fallbackFinishTimer;
  const showFallback = () => {
    if (finished || splash.classList.contains("has-video")) return;
    splash.classList.add("use-fallback");
    window.clearTimeout(fallbackFinishTimer);
    fallbackFinishTimer = window.setTimeout(finish, 3000);
  };

  // Video çok geç yüklenirse veya oynatılamazsa açılış ekranında takılma.
  const loadTimer = window.setTimeout(showFallback, 5000);
  if (!video) return;

  const showVideo = () => {
    window.clearTimeout(loadTimer);
    window.clearTimeout(fallbackFinishTimer);
    splash.classList.remove("use-fallback");
    splash.classList.add("has-video");
    const playAttempt = video.play();
    if (playAttempt) playAttempt.catch(() => {
      splash.classList.remove("has-video");
      showFallback();
    });
  };
  if (video.readyState >= 2) showVideo();
  else video.addEventListener("loadeddata", showVideo, { once: true });
  video.addEventListener("ended", finish, { once: true });
  video.addEventListener("error", () => {
    window.clearTimeout(loadTimer);
    splash.classList.remove("has-video");
    showFallback();
  }, { once: true });

  // Hatalı veya aşırı uzun bir dosya uygulamanın açılmasını engellemesin.
  window.setTimeout(finish, 15000);
})();
