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

  // MP4 henüz eklenmediyse veya oynatılamazsa açılış ekranında takılma.
  const fallbackTimer = window.setTimeout(finish, 3000);
  if (!video) return;

  const showVideo = () => {
    splash.classList.add("has-video");
    window.clearTimeout(fallbackTimer);
    const playAttempt = video.play();
    if (playAttempt) playAttempt.catch(() => {
      splash.classList.remove("has-video");
      window.setTimeout(finish, 3000);
    });
  };
  if (video.readyState >= 2) showVideo();
  else video.addEventListener("loadeddata", showVideo, { once: true });
  video.addEventListener("ended", finish, { once: true });
  video.addEventListener("error", () => splash.classList.remove("has-video"), { once: true });

  // Hatalı veya aşırı uzun bir dosya uygulamanın açılmasını engellemesin.
  window.setTimeout(finish, 15000);
})();
