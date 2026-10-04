(() => {
  "use strict";
  const STORAGE_KEY = "football-ad-privacy-v1";
  const dialog = document.getElementById("adPrivacyDialog");
  const acceptButton = document.getElementById("adPrivacyAccept");
  const limitedButton = document.getElementById("adPrivacyLimited");
  const policyButton = document.getElementById("adPrivacyPolicy");
  let currentChoice = localStorage.getItem(STORAGE_KEY);
  let resolveInitialChoice;
  const ready = currentChoice
    ? Promise.resolve(currentChoice)
    : new Promise(resolve => { resolveInitialChoice = resolve; });

  function setChoice(choice) {
    currentChoice = choice === "personalized" ? "personalized" : "non_personalized";
    localStorage.setItem(STORAGE_KEY, currentChoice);
    dialog.hidden = true;
    resolveInitialChoice?.(currentChoice);
    resolveInitialChoice = null;
    window.dispatchEvent(new CustomEvent("football-ad-privacy-changed", {
      detail: {choice: currentChoice},
    }));
    return currentChoice;
  }

  function open() {
    dialog.hidden = false;
    return new Promise(resolve => {
      const changed = event => {
        window.removeEventListener("football-ad-privacy-changed", changed);
        resolve(event.detail.choice);
      };
      window.addEventListener("football-ad-privacy-changed", changed);
    });
  }

  acceptButton.addEventListener("click", () => setChoice("personalized"));
  limitedButton.addEventListener("click", () => setChoice("non_personalized"));
  policyButton.addEventListener("click", () => window.MobileShell?.navigate?.("/privacy"));
  if (!currentChoice) dialog.hidden = false;

  window.MobilePrivacy = Object.freeze({
    ready,
    open,
    getChoice: () => currentChoice,
  });
})();
