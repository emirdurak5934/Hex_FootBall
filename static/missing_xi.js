(() => {
  const data = window.MISSING_XI_DATA;
  const fieldView = document.getElementById("fieldView");
  const wordleView = document.getElementById("wordleView");
  const pitch = document.getElementById("pitch");
  const grid = document.getElementById("wordleGrid");
  const message = document.getElementById("answerMessage");
  const resultModal = document.getElementById("resultModal");
  const rewardHintButton = document.getElementById("rewardHintButton");
  const rewardHintLetters = document.getElementById("rewardHintLetters");
  const slotStates = new Map();
  let activeSlot = null;
  let submitting = false;
  let rewardPending = false;

  function stateFor(slot) {
    if (!slotStates.has(slot)) {
      slotStates.set(slot, {
        attempts: 0, history: [], current: "", keyboard: {},
        hint: null, rewardEarned: false,
      });
    }
    return slotStates.get(slot);
  }

  function sideRank(slot) {
    const position = slot.dataset.position.toUpperCase();
    if (position.startsWith("L")) return 0;
    if (position.startsWith("R")) return 2;
    return 1;
  }

  function positionSlots() {
    let parts = data.match.formation.split("-").map(Number);
    if (parts.some(Number.isNaN) || parts.reduce((a, b) => a + b, 0) !== 10) parts = [4, 3, 3];
    const rows = [[0]];
    let cursor = 1;
    parts.forEach(count => rows.push(Array.from({length: count}, () => cursor++)));
    rows.forEach((row, rowIndex) => {
      const ordered = row.map(slot => pitch.querySelector(`[data-slot="${slot}"]`))
        .sort((left, right) => sideRank(left) - sideRank(right));
      ordered.forEach((el, colIndex) => {
        el.style.left = `${(colIndex + 1) * 100 / (ordered.length + 1)}%`;
        el.style.top = `${91 - rowIndex * 78 / (rows.length - 1)}%`;
      });
    });
  }

  function buildKeyboard() {
    document.querySelectorAll(".keyboard-row").forEach(row => {
      if (row.dataset.actions) {
        const erase = document.createElement("button");
        erase.type = "button"; erase.dataset.key = "BACKSPACE"; erase.textContent = "SİL"; erase.className = "key action-key";
        row.appendChild(erase);
      }
      [...row.dataset.keys].forEach(letter => {
        const key = document.createElement("button");
        key.type = "button"; key.dataset.key = letter; key.textContent = letter; key.className = "key";
        row.appendChild(key);
      });
      if (row.dataset.actions) {
        const enter = document.createElement("button");
        enter.type = "button"; enter.dataset.key = "ENTER"; enter.textContent = "ENTER"; enter.className = "key action-key";
        row.appendChild(enter);
      }
    });
  }

  function renderGrid(revealLast = false) {
    const slot = pitch.querySelector(`[data-slot="${activeSlot}"]`);
    const length = Number(slot.dataset.letterCount);
    const state = stateFor(activeSlot);
    grid.style.setProperty("--letters", length);
    grid.style.width = `${Math.min(100, Math.max(62, length * 11))}%`;
    grid.replaceChildren();
    for (let rowIndex = 0; rowIndex < 6; rowIndex += 1) {
      const row = document.createElement("div");
      row.className = "wordle-row";
      const completed = state.history[rowIndex];
      const text = completed ? completed.guess : rowIndex === state.attempts ? state.current : "";
      for (let column = 0; column < length; column += 1) {
        const cell = document.createElement("span");
        cell.textContent = text[column] || "";
        if (completed) {
          cell.classList.add(completed.feedback[column] || "gray");
          if (revealLast && rowIndex === state.history.length - 1) {
            cell.classList.add("reveal");
            cell.style.animationDelay = `${column * 55}ms`;
          }
        } else if (text[column]) {
          cell.classList.add("filled");
        }
        row.appendChild(cell);
      }
      grid.appendChild(row);
    }
    document.getElementById("attemptLabel").textContent = `TAHMİN ${Math.min(state.attempts + 1, 6)}/6`;
  }

  function renderKeyboard() {
    const knowledge = stateFor(activeSlot).keyboard;
    document.querySelectorAll(".key").forEach(key => {
      key.classList.remove("green", "yellow", "gray");
      if (knowledge[key.dataset.key]) key.classList.add(knowledge[key.dataset.key]);
    });
  }

  function renderRewardHint() {
    const state = stateFor(activeSlot);
    const length = Number(pitch.querySelector(`[data-slot="${activeSlot}"]`).dataset.letterCount);
    const revealed = new Map((state.hint || []).map(item => [Number(item.index), item.letter]));
    rewardHintLetters.replaceChildren();
    for (let index = 0; index < length; index += 1) {
      const cell = document.createElement("span");
      cell.textContent = revealed.get(index) || "·";
      if (revealed.has(index)) cell.classList.add("revealed");
      rewardHintLetters.appendChild(cell);
    }
    rewardHintLetters.classList.toggle("hidden", !state.hint);
    const allRevealed = revealed.size >= length;
    rewardHintButton.disabled = allRevealed || rewardPending;
    rewardHintButton.textContent = allRevealed
      ? "✓ TÜM HARFLER AÇILDI"
      : rewardPending
        ? "REKLAM HAZIRLANIYOR…"
        : state.hint
          ? "▶ REKLAM İZLE · 2 HARF DAHA AÇ"
          : "▶ REKLAM İZLE · 2 HARF AÇ";
  }

  function showFieldView() {
    if (rewardPending) return;
    wordleView.classList.add("leaving");
    setTimeout(() => {
      wordleView.classList.add("hidden"); wordleView.classList.remove("leaving");
      fieldView.classList.remove("hidden"); fieldView.classList.add("entering");
      setTimeout(() => fieldView.classList.remove("entering"), 220);
    }, 170);
  }

  function showWordleView(slot) {
    activeSlot = Number(slot.dataset.slot);
    message.textContent = "";
    document.getElementById("slotTitle").textContent = slot.dataset.position;
    renderGrid(); renderKeyboard(); renderRewardHint();
    fieldView.classList.add("hidden");
    wordleView.classList.remove("hidden"); wordleView.classList.add("entering");
    setTimeout(() => wordleView.classList.remove("entering"), 220);
  }

  function updateKeyboard(guess, feedback) {
    const priority = {gray: 1, yellow: 2, green: 3};
    const knowledge = stateFor(activeSlot).keyboard;
    [...guess].forEach((letter, index) => {
      const next = feedback[index] || "gray";
      if ((priority[next] || 0) > (priority[knowledge[letter]] || 0)) knowledge[letter] = next;
    });
  }

  function typeLetter(letter) {
    if (submitting || activeSlot === null) return;
    const state = stateFor(activeSlot);
    const length = Number(pitch.querySelector(`[data-slot="${activeSlot}"]`).dataset.letterCount);
    if (state.current.length < length) state.current += letter;
    renderGrid();
  }

  function eraseLetter() {
    if (submitting || activeSlot === null) return;
    const state = stateFor(activeSlot);
    state.current = state.current.slice(0, -1);
    message.textContent = "";
    renderGrid();
  }

  async function submitGuess() {
    if (submitting || rewardPending || activeSlot === null) return;
    const state = stateFor(activeSlot);
    const length = Number(pitch.querySelector(`[data-slot="${activeSlot}"]`).dataset.letterCount);
    if (state.current.length !== length) { message.textContent = "Tüm harfleri doldur."; return; }
    submitting = true;
    const response = await fetch("/missing-xi/guess", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({game_token: data.gameToken, match_id: data.match.id, slot: activeSlot, guess: state.current}),
    });
    const result = await response.json();
    submitting = false;
    message.textContent = result.message || "";
    if (!result.accepted) return;
    state.attempts = result.attempt;
    state.history.push({guess: result.guess, feedback: result.feedback});
    state.current = "";
    updateKeyboard(result.guess, result.feedback);
    renderGrid(true); renderKeyboard();
    document.getElementById("errorCount").textContent = result.errors;
    document.getElementById("correctCount").textContent = `${result.correct_count}/11`;
    if (!result.correct && !result.exhausted) return;
    const slot = pitch.querySelector(`[data-slot="${result.slot}"]`);
    slot.classList.add(result.correct ? "found" : "missed");
    slot.querySelector("b").textContent = result.player_name || result.answer;
    slot.disabled = true;
    setTimeout(showFieldView, 750);
    if (result.finished) {
      document.getElementById("finalCorrect").textContent = `${result.correct_count}/11`;
      document.getElementById("finalMissed").textContent = result.missed_count;
      document.getElementById("finalErrors").textContent = result.errors;
      const reveal = () => resultModal.classList.remove("hidden");
      setTimeout(() => {
        if (window.MatchAds) window.MatchAds.present(result.ad_break, reveal);
        else reveal();
      }, 1100);
    }
  }

  async function requestRewardHint(slot, state) {
    const response = await fetch("/missing-xi/reward-hint", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        game_token: data.gameToken,
        match_id: data.match.id,
        slot,
        reward_completed: true,
      }),
    });
    const result = await response.json();
    if (!response.ok || !result.accepted) throw new Error(result.message || "İpucu alınamadı.");
    state.hint = result.hint;
    state.rewardEarned = false;
    message.textContent = result.message || "İki yeni harf açıldı.";
  }

  async function showRewardHint() {
    if (rewardPending || submitting || activeSlot === null) return;
    const slot = activeSlot;
    const state = stateFor(slot);
    const length = Number(pitch.querySelector(`[data-slot="${slot}"]`).dataset.letterCount);
    if ((state.hint || []).length >= length) return;
    rewardPending = true;
    message.textContent = "";
    renderRewardHint();
    try {
      if (!state.rewardEarned) {
        if (!window.MatchAds || typeof window.MatchAds.reward !== "function") {
          throw new Error("Ödüllü reklam yalnızca iPhone uygulamasında kullanılabilir.");
        }
        const earned = await window.MatchAds.reward({game_mode: "missing_xi", slot});
        if (!earned) {
          const detail = typeof window.MatchAds.errorMessage === "function"
            ? window.MatchAds.errorMessage()
            : "";
          throw new Error(detail
            ? `Reklam yüklenemedi · ${detail}`
            : "Reklam tamamlanmadı; ipucu verilmedi.");
        }
        state.rewardEarned = true;
      }
      await requestRewardHint(slot, state);
    } catch (error) {
      message.textContent = error.message || "İpucu şu anda kullanılamıyor.";
    } finally {
      rewardPending = false;
      if (activeSlot === slot) renderRewardHint();
    }
  }

  pitch.addEventListener("click", event => {
    const slot = event.target.closest(".player-slot");
    if (!slot || slot.classList.contains("found") || slot.classList.contains("missed")) return;
    showWordleView(slot);
  });
  document.getElementById("screenKeyboard").addEventListener("click", event => {
    const key = event.target.closest(".key");
    if (!key) return;
    if (key.dataset.key === "BACKSPACE") eraseLetter();
    else if (key.dataset.key === "ENTER") submitGuess();
    else typeLetter(key.dataset.key);
  });
  rewardHintButton.addEventListener("click", showRewardHint);
  document.addEventListener("keydown", event => {
    if (wordleView.classList.contains("hidden")) return;
    if (/^[a-zA-Z]$/.test(event.key)) typeLetter(event.key.toUpperCase());
    else if (event.key === "Backspace") eraseLetter();
    else if (event.key === "Enter") submitGuess();
    else return;
    event.preventDefault();
  });
  document.getElementById("wordleBack").onclick = showFieldView;
  document.getElementById("helpButton").onclick = () => document.getElementById("helpModal").classList.remove("hidden");
  document.querySelectorAll('[data-close="help"]').forEach(el => el.onclick = () => document.getElementById("helpModal").classList.add("hidden"));
  document.getElementById("newMatch").onclick = () => window.MobileBridge ? window.MobileBridge.reload() : window.location.reload();
  buildKeyboard(); positionSlots();
  window.addEventListener("resize", positionSlots);
})();
