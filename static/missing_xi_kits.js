// Presentation-only kit themes. Keys match the existing target_team values.
(() => {
  const DEFAULT_KIT = {primary: "#263e72", secondary: "#5874a6", pattern: "solid"};
  const TEAM_KITS = {
    "ARGENTINA": {primary: "#f5f7f6", secondary: "#79c9e8", pattern: "stripes"},
    "ARSENAL": {primary: "#c82132", secondary: "#f5f4ee", pattern: "sleeves"},
    "ATLETICO MADRID": {primary: "#d82637", secondary: "#f5f3ed", pattern: "stripes"},
    "BARCELONA": {primary: "#842345", secondary: "#193b80", pattern: "stripes"},
    "BAYERN MUNICH": {primary: "#c32032", secondary: "#f7f5ee", pattern: "solid"},
    "BELGIUM": {primary: "#c42032", secondary: "#e3bb36", pattern: "solid"},
    "BESIKTAS": {primary: "#f4f4f0", secondary: "#191919", pattern: "stripes"},
    "BORUSSIA DORTMUND": {primary: "#f2d42e", secondary: "#242424", pattern: "solid"},
    "BRAZIL": {primary: "#f2d535", secondary: "#2a8a51", pattern: "solid"},
    "CHELSEA": {primary: "#2155a1", secondary: "#f4f4ef", pattern: "solid"},
    "CROATIA": {primary: "#f2f0eb", secondary: "#d62734", pattern: "stripes"},
    "FENERBAHCE": {primary: "#e8c93a", secondary: "#183965", pattern: "stripes"},
    "FRANCE": {primary: "#203a75", secondary: "#f2f1ed", pattern: "solid"},
    "GALATASARAY": {primary: "#e4ad2e", secondary: "#b62b32", pattern: "half"},
    "GERMANY": {primary: "#f0f0ed", secondary: "#1d242b", pattern: "centerStripe"},
    "INTER": {primary: "#1766af", secondary: "#171a23", pattern: "stripes"},
    "ITALY": {primary: "#2361a5", secondary: "#f5f3ec", pattern: "solid"},
    "JUVENTUS": {primary: "#f4f4ef", secondary: "#1a1a1a", pattern: "stripes"},
    "LIVERPOOL": {primary: "#b92535", secondary: "#e4c998", pattern: "solid"},
    "MANCHESTER CITY": {primary: "#80c6e6", secondary: "#f3f3ee", pattern: "solid"},
    "MANCHESTER UNITED": {primary: "#c32632", secondary: "#191b20", pattern: "solid"},
    "MILAN": {primary: "#c52a38", secondary: "#1c1c22", pattern: "stripes"},
    "NETHERLANDS": {primary: "#e78429", secondary: "#1e2735", pattern: "solid"},
    "PORTUGAL": {primary: "#ba2836", secondary: "#266347", pattern: "half"},
    "REAL MADRID": {primary: "#f5f5f0", secondary: "#c3b5d7", pattern: "solid"},
    "SPAIN": {primary: "#c52736", secondary: "#e3ba38", pattern: "solid"},
    "TOTTENHAM": {primary: "#f4f4f0", secondary: "#223654", pattern: "solid"},
    "URUGUAY": {primary: "#86c8df", secondary: "#f5f4ee", pattern: "solid"}
  };

  function kitFor(team) {
    return TEAM_KITS[String(team || "").trim().toUpperCase()] || DEFAULT_KIT;
  }

  function applyKit(pitch, team) {
    const kit = kitFor(team);
    pitch.classList.add(`kit-${kit.pattern}`);
    pitch.style.setProperty("--kit-primary", kit.primary);
    pitch.style.setProperty("--kit-secondary", kit.secondary);
  }

  const pitch = document.getElementById("pitch");
  if (pitch) applyKit(pitch, window.MISSING_XI_DATA?.match?.target_team);
})();
