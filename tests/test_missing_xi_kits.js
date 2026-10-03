const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const script = fs.readFileSync(path.join(root, "static/missing_xi_kits.js"), "utf8");
const css = fs.readFileSync(path.join(root, "static/missing_xi_wordle.css"), "utf8");
const template = fs.readFileSync(path.join(root, "templates/missing_xi.html"), "utf8");
const matches = JSON.parse(fs.readFileSync(path.join(root, "data/missing_xi_matches.json"), "utf8"));

function renderKit(team) {
  const classes = new Set();
  const variables = new Map();
  const shirts = Array.from({length: 11}, () => ({className: "mini-shirt", style: {}}));
  const pitch = {
    classList: {add: value => classes.add(value)},
    style: {setProperty: (key, value) => variables.set(key, value)},
    children: shirts,
  };
  vm.runInNewContext(script, {
    document: {getElementById: id => id === "pitch" ? pitch : null},
    window: {MISSING_XI_DATA: {match: {target_team: team}}},
  });
  assert.equal(shirts.length, 11);
  assert.ok(shirts.every(shirt => shirt.className === "mini-shirt"));
  assert.ok(shirts.every(shirt => Object.keys(shirt.style).length === 0));
  return {classes, variables};
}

for (const [team, pattern] of [
  ["REAL MADRID", "solid"],
  ["INTER", "stripes"],
  ["GALATASARAY", "half"],
  ["ARSENAL", "sleeves"],
  ["GERMANY", "centerStripe"],
]) {
  const {classes, variables} = renderKit(team);
  assert.ok(classes.has(`kit-${pattern}`), `${team}: ${pattern}`);
  assert.match(variables.get("--kit-primary"), /^#[0-9a-f]{6}$/i);
  assert.match(variables.get("--kit-secondary"), /^#[0-9a-f]{6}$/i);
  assert.ok(css.includes(`.pitch.kit-${pattern} .mini-shirt`));
}

const fallback = renderKit("UNKNOWN CLUB");
assert.ok(fallback.classes.has("kit-solid"));
assert.equal(fallback.variables.get("--kit-primary"), "#263e72");
assert.ok(renderKit(null).classes.has("kit-solid"));
for (const team of new Set(matches.map(match => match.target_team))) {
  assert.ok(script.includes(`${JSON.stringify(team)}:`), `Missing current team theme: ${team}`);
}
assert.ok(template.includes("{% for player in match.lineup %}"));
assert.ok(template.includes("class=\"mini-shirt\""));
assert.ok(template.includes("missing_xi_kits.js"));
assert.ok(css.includes(".pitch .player-slot.found .mini-shirt"));
assert.ok(css.includes(".pitch .player-slot.missed .mini-shirt"));
assert.ok(css.includes("@media(max-width:400px)"));
assert.ok(css.includes(".missing-app:has(.wordle-view:not(.hidden)) .game-header .back{visibility:hidden}"));
assert.ok(template.includes('id="wordleBack"'));

console.log("Missing XI kit presentation tests passed");
