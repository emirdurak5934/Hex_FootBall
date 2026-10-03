const heatmapData = window.HEATMAP_DATA;
const cells = heatmapData.cells;
const neighbors = heatmapData.neighbors;
const gameToken = heatmapData.gameToken;
const heated = new Map();
let selectedIndex = null;
let selectedPlayerId = null;
let searchTimer = null;
let heatAnimationGeneration = 0;

const hexes = document.querySelectorAll(".criterion-cell");
const modal = document.getElementById("answerModal");
const playerInput = document.getElementById("playerInput");
const suggestions = document.getElementById("playerSuggestions");
const message = document.getElementById("answerMessage");
const submitButton = document.getElementById("submitAnswer");
const helpModal = document.getElementById("helpModal");

function resetModal() {
    modal.classList.add("hidden");
    modal.classList.remove("closing");
    selectedIndex = null;
    selectedPlayerId = null;
    playerInput.value = "";
    suggestions.classList.add("hidden");
    suggestions.innerHTML = "";
    message.textContent = "";
}

function closeModal({animate = false, afterClose = null} = {}) {
    if (!animate) {
        resetModal();
        afterClose?.();
        return;
    }

    modal.classList.add("closing");
    const closingAnimations = modal.getAnimations({subtree: true});
    if (closingAnimations.length === 0) {
        resetModal();
        afterClose?.();
        return;
    }
    Promise.allSettled(closingAnimations.map(animation => animation.finished))
        .then(() => {
            resetModal();
            afterClose?.();
        });
}

hexes.forEach(hex => hex.addEventListener("click", () => {
    const index = Number(hex.dataset.index);
    if (heated.has(index)) return;
    selectedIndex = index;
    selectedPlayerId = null;
    document.getElementById("selectedLabel").textContent = cells[index].label;
    const selectedImage = document.getElementById("selectedImage");
    selectedImage.src = cells[index].image || "";
    selectedImage.alt = cells[index].label;
    selectedImage.classList.toggle("hidden", !cells[index].image);
    renderNeighborPreviews(index);
    modal.classList.remove("hidden");
    setTimeout(() => playerInput.focus(), 50);
}));

function renderNeighborPreviews(index) {
    const container = document.getElementById("neighborHexes");
    container.innerHTML = "";
    (neighbors[index] || [])
        .filter(neighborIndex => cells[neighborIndex]?.type !== "score")
        .forEach(neighborIndex => {
            const neighbor = cells[neighborIndex];
            const card = document.createElement("div");
            card.className = "neighbor-card";
            if (neighbor.image) {
                const image = document.createElement("img");
                image.src = neighbor.image;
                image.alt = "";
                image.draggable = false;
                card.appendChild(image);
            }
            const label = document.createElement("span");
            label.textContent = neighbor.label;
            card.appendChild(label);
            container.appendChild(card);
        });
}

document.getElementById("closeModal").addEventListener("click", closeModal);
document.getElementById("modalBackdrop").addEventListener("click", closeModal);

function openHelpModal() {
    helpModal.classList.remove("hidden", "closing");
}

function closeHelpModal() {
    helpModal.classList.add("closing");
    const animations = helpModal.getAnimations({subtree: true});
    if (animations.length === 0) {
        helpModal.classList.add("hidden");
        helpModal.classList.remove("closing");
        return;
    }
    Promise.allSettled(animations.map(animation => animation.finished)).then(() => {
        helpModal.classList.add("hidden");
        helpModal.classList.remove("closing");
    });
}

document.getElementById("helpButton").addEventListener("click", openHelpModal);
document.getElementById("closeHelpModal").addEventListener("click", closeHelpModal);
document.getElementById("helpModalBackdrop").addEventListener("click", closeHelpModal);
document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !helpModal.classList.contains("hidden")) {
        closeHelpModal();
    }
});

playerInput.addEventListener("input", () => {
    selectedPlayerId = null;
    clearTimeout(searchTimer);
    const query = playerInput.value.trim();
    if (query.length < 2) {
        suggestions.classList.add("hidden");
        return;
    }
    searchTimer = setTimeout(() => searchPlayers(query), 170);
});

async function searchPlayers(query) {
    try {
        const response = await fetch(`/search_players?q=${encodeURIComponent(query)}`);
        const results = response.ok ? await response.json() : [];
        suggestions.innerHTML = "";
        results.forEach(player => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "player-suggestion";
            const name = document.createElement("span");
            name.className = "player-suggestion-name";
            name.textContent = player.name;
            button.appendChild(name);
            if (player.show_age) {
                const detail = document.createElement("small");
                detail.className = "player-suggestion-extra";
                detail.textContent = player.age !== null ? `${player.age} yaş` : player.birth_date;
                button.appendChild(detail);
            }
            button.addEventListener("click", () => {
                playerInput.value = player.name;
                selectedPlayerId = String(player.id);
                suggestions.classList.add("hidden");
            });
            suggestions.appendChild(button);
        });
        suggestions.classList.toggle("hidden", results.length === 0);
    } catch (error) {
        suggestions.classList.add("hidden");
    }
}

submitButton.addEventListener("click", submitAnswer);
playerInput.addEventListener("keydown", event => {
    if (event.key === "Enter") {
        event.preventDefault();
        submitAnswer();
    }
});

async function submitAnswer() {
    if (selectedIndex === null || !selectedPlayerId || heated.has(selectedIndex)) {
        message.textContent = "Futbolcuyu listeden seç.";
        message.className = "answer-message error";
        return;
    }
    submitButton.disabled = true;
    try {
        const response = await fetch("/heatmap/check", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({game_token: gameToken, index: selectedIndex, player_id: selectedPlayerId})
        });
        const data = await response.json();
        document.getElementById("moveCount").textContent = `HAMLE ${data.moves ?? 0}`;
        if (!data.accepted || !data.correct) {
            if (data.accepted && data.correct === false) {
                const newScore = data.totalScore ?? data.score;
                const penalty = data.scorePenalty ?? 1;
                closeModal({
                    animate: true,
                    afterClose: () => {
                        if (Number.isFinite(Number(newScore))) {
                            document.getElementById("scoreValue").textContent = newScore;
                        }
                        showWrongFeedback(penalty);
                    },
                });
            } else {
                message.textContent = data.message || "Yanlış cevap.";
                message.className = "answer-message error";
            }
            return;
        }

        closeModal();
        const newlyHeated = data.newlyHeated || data.heated || [];
        const heatLevels = data.heatLevels || {};
        newlyHeated.forEach(index => {
            const heatLevel = Number(heatLevels[index] || data.comboCount || data.combo_level || 1);
            heated.set(index, {state: "heated", heatLevel});
            const hex = document.querySelector(`.criterion-cell[data-index="${index}"]`);
            if (hex) hex.disabled = true;
        });
        (data.reheated || []).forEach(index => {
            const heatLevel = Number(heatLevels[index] || 1);
            heated.set(index, {state: "heated", heatLevel});
            const hex = document.querySelector(`.criterion-cell[data-index="${index}"]`);
            if (hex) hex.disabled = true;
        });
        document.getElementById("scoreValue").textContent = data.score;
        showComboFeedback(data.comboCount ?? data.combo_level, data.moveScore ?? data.gained_score, data.reheatScore || 0);
        animateHeatmapMove({
            sourceIndex: data.source,
            newlyHeated,
            reheated: data.reheated || [],
            heatLevels,
        });
        if (data.finished) showResult(data.score, data.moves, data.ad_break);
    } catch (error) {
        message.textContent = "Bağlantı hatası. Tekrar dene.";
        message.className = "answer-message error";
    } finally {
        submitButton.disabled = false;
    }
}

function setHeatLevel(hex, heatLevel) {
    if (!hex) return;
    hex.classList.remove(...[1, 2, 3, 4, 5].map(level => `combo-level-${level}`));
    hex.classList.add("heated", `combo-level-${Math.min(heatLevel, 5)}`);
}

const HEAT_FLOW_COLORS = ["", "#e8c96f", "#d5a943", "#d47a32", "#b94735", "#7e2928"];

function animateHeatmapMove({sourceIndex, newlyHeated, reheated, heatLevels}) {
    const generation = ++heatAnimationGeneration;
    const currentTargets = new Set([...newlyHeated, ...reheated]);
    heated.forEach((state, index) => {
        if (index === sourceIndex || currentTargets.has(index)) return;
        setHeatLevel(
            document.querySelector(`.criterion-cell[data-index="${index}"]`),
            state.heatLevel,
        );
    });
    document.querySelectorAll(".heat-flow-line").forEach(line => line.remove());
    const sourceHex = document.querySelector(`.criterion-cell[data-index="${sourceIndex}"]`);
    if (!sourceHex) return;

    const sourceLevel = Number(heatLevels[sourceIndex] || 1);
    setHeatLevel(sourceHex, sourceLevel);
    restartHeatAnimation(sourceHex, "heat-source-pulse");

    const targets = [
        ...newlyHeated
            .filter(index => index !== sourceIndex && index !== heatmapData.scoreIndex)
            .map(index => ({index, reheat: false})),
        ...reheated
            .filter(index => index !== heatmapData.scoreIndex)
            .map(index => ({index, reheat: true})),
    ];

    targets.forEach((target, order) => {
        window.setTimeout(() => {
            const targetHex = document.querySelector(`.criterion-cell[data-index="${target.index}"]`);
            const targetLevel = Number(heatLevels[target.index] || 1);
            if (!targetHex) return;
            animateHeatFlowBetweenHexes(sourceHex, targetHex, targetLevel)
                .catch(() => undefined)
                .finally(() => {
                    if (generation !== heatAnimationGeneration) return;
                    setHeatLevel(targetHex, targetLevel);
                    restartHeatAnimation(
                        targetHex,
                        target.reheat ? "heat-reheat-impact" : "heat-target-impact",
                    );
                });
        }, order * 70);
    });
}

function animateHeatFlowBetweenHexes(sourceHex, targetHex, heatLevel) {
    const sourceRect = sourceHex.getBoundingClientRect();
    const targetRect = targetHex.getBoundingClientRect();
    const startX = sourceRect.left + sourceRect.width / 2;
    const startY = sourceRect.top + sourceRect.height / 2;
    const endX = targetRect.left + targetRect.width / 2;
    const endY = targetRect.top + targetRect.height / 2;
    const deltaX = endX - startX;
    const deltaY = endY - startY;
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    const angle = Math.atan2(deltaY, deltaX) * 180 / Math.PI;
    const line = document.createElement("div");
    line.className = "heat-flow-line";
    line.style.left = `${startX}px`;
    line.style.top = `${startY}px`;
    line.style.width = `${distance}px`;
    line.style.setProperty("--heat-flow-angle", `${angle}deg`);
    line.style.setProperty("--heat-flow-color", HEAT_FLOW_COLORS[Math.min(heatLevel, 5)]);
    document.body.appendChild(line);

    const animation = line.getAnimations()[0];
    if (!animation) {
        line.remove();
        return Promise.resolve();
    }
    return animation.finished.finally(() => line.remove());
}

function restartHeatAnimation(hex, className) {
    hex.classList.remove(className);
    void hex.offsetWidth;
    hex.classList.add(className);
    hex.addEventListener("animationend", () => hex.classList.remove(className), {once: true});
}

function showComboFeedback(level, gained, reheatScore) {
    const feedback = document.getElementById("comboFeedback");
    const comboText = level > 1 || reheatScore > 0 ? `${level}'Lİ KOMBO` : `+${gained}`;
    feedback.textContent = reheatScore > 0
        ? `${comboText} · REHEAT +${reheatScore} · TOPLAM +${gained}`
        : comboText;
    feedback.classList.remove("hidden");
    setTimeout(() => feedback.classList.add("hidden"), 1300);
}

function showWrongFeedback(penalty) {
    const feedback = document.getElementById("scorePenaltyFeedback");
    feedback.textContent = `-${penalty}`;
    feedback.classList.remove("visible");
    void feedback.offsetWidth;
    feedback.classList.add("visible");
    feedback.addEventListener("animationend", () => {
        feedback.classList.remove("visible");
        feedback.textContent = "";
    }, {once: true});
}

function showResult(score, moves, adBreak) {
    document.getElementById("finalScore").textContent = score;
    document.getElementById("finalMoves").textContent = moves;
    const reveal = () => document.getElementById("resultModal").classList.remove("hidden");
    setTimeout(() => {
        if (window.MatchAds) window.MatchAds.present(adBreak, reveal);
        else reveal();
    }, 500);
}

document.getElementById("restartGame").addEventListener("click", () => window.location.reload());
