(() => {
    const config = window.TIKI_CONFIG;
    const $ = id => document.getElementById(id);
    const ids = [
        "modePanel", "gamePanel", "criteriaGrid", "turnPill", "statusText", "turnClock",
        "modeLabel", "localButton", "randomMatchButton", "createRoomButton",
        "joinRoomButton", "roomCodeInput", "roomStatus", "playerModal",
        "closeModal", "modalTitle", "playerSearch", "searchResults",
        "resultModal", "resultTitle", "resultReason", "rematchButton",
        "onlinePlayerNames", "tikiPlayerOneName", "tikiPlayerTwoName"
        , "onlineAnswerToast", "onlineAnswerAccount", "onlineAnswerPlayer", "onlineAnswerResult"
    ];
    const el = Object.fromEntries(ids.map(id => [id, $(id)]));
    let state = config.initialState;
    let mode = null;
    let playerNumber = null;
    let selectedCell = null;
    let searchTimer;
    let matchmaking = false;
    let playerNames = {"1": "OYUNCU 1", "2": "OYUNCU 2"};
    let onlineAnswerTimer = null;
    let turnEndsAt = null;
    let localStatePolling = false;
    const socket = typeof io === "function" ? io() : null;

    function displayName(number) {
        return playerNames[String(number)] || `OYUNCU ${number}`;
    }

    function showOnlineAnswer(data) {
        if (!el.onlineAnswerToast || !data) return;
        clearTimeout(onlineAnswerTimer);
        el.onlineAnswerToast.classList.remove("hidden", "hiding", "correct", "wrong");
        el.onlineAnswerToast.classList.add(data.correct ? "correct" : "wrong");
        el.onlineAnswerAccount.textContent = data.account_name;
        el.onlineAnswerPlayer.textContent = data.player_name;
        el.onlineAnswerResult.textContent = data.correct ? "DOĞRU CEVAP" : "YANLIŞ CEVAP";
        onlineAnswerTimer = setTimeout(() => {
            el.onlineAnswerToast.classList.add("hiding");
            setTimeout(() => el.onlineAnswerToast.classList.add("hidden"), 180);
        }, Number(data.duration_ms) || 2000);
    }

    function applyPlayerNames(next) {
        if (next.player_names) {
            playerNames = {
                "1": next.player_names["1"] || "OYUNCU 1",
                "2": next.player_names["2"] || "OYUNCU 2"
            };
        }
        el.tikiPlayerOneName.textContent = displayName(1);
        el.tikiPlayerTwoName.textContent = displayName(2);
        el.onlinePlayerNames.classList.toggle("hidden", mode !== "online");
    }

    function criterion(item) {
        const node = document.createElement("div");
        node.className = "criterion";
        node.setAttribute("aria-label", item.label);
        node.title = item.label;
        const logo = document.createElement("img");
        logo.src = item.image;
        logo.alt = item.label;
        logo.loading = "eager";
        node.appendChild(logo);
        return node;
    }

    function updateTurnClock() {
        if (!state.started || state.finished || turnEndsAt === null) {
            el.turnClock.textContent = "00:00";
            el.turnClock.classList.remove("urgent");
            return;
        }
        const seconds = Math.max(0, Math.ceil((turnEndsAt - Date.now()) / 1000));
        el.turnClock.textContent = `00:${String(seconds).padStart(2, "0")}`;
        el.turnClock.classList.toggle("urgent", seconds <= 10);
    }

    function render(next) {
        if (state.started && next.started && state.turn_deadline && next.turn_deadline &&
                next.turn_deadline < state.turn_deadline) return;
        if (state.turn_deadline !== next.turn_deadline &&
                !el.playerModal.classList.contains("hidden")) closeModal();
        state = next;
        turnEndsAt = state.started && !state.finished
            ? Date.now() + Number(state.turn_remaining_ms || 0) : null;
        updateTurnClock();
        applyPlayerNames(state);
        el.criteriaGrid.innerHTML = "";
        const corner = document.createElement("div");
        corner.className = "corner";
        corner.textContent = "×";
        el.criteriaGrid.appendChild(corner);
        state.columns.forEach(item => el.criteriaGrid.appendChild(criterion(item)));
        state.rows.forEach((row, rowIndex) => {
            el.criteriaGrid.appendChild(criterion(row));
            state.columns.forEach((column, columnIndex) => {
                const index = rowIndex * 3 + columnIndex;
                const value = state.board[index];
                const button = document.createElement("button");
                button.type = "button";
                button.className = `cell${value ? ` p${value.owner}` : ""}`;
                button.disabled = Boolean(value) || state.finished || !state.started
                    || (mode === "online" && playerNumber !== state.active_player);
                button.innerHTML = value
                    ? `<span class="mark">${value.owner === 1 ? "X" : "O"}</span><span class="answer"></span>`
                    : `<span class="mark">?</span>`;
                if (value) button.querySelector(".answer").textContent = value.player_name;
                button.addEventListener("click", () => openModal(index, row, column));
                el.criteriaGrid.appendChild(button);
            });
        });
        el.turnPill.textContent = `${displayName(state.active_player)} • ${state.active_player === 1 ? "X" : "O"}`;
        el.statusText.textContent = state.finished ? state.end_reason : `${displayName(state.active_player)} OYNUYOR`;
        if (state.finished) showResult();
    }

    function start(nextMode) {
        mode = nextMode;
        delete el.resultModal.dataset.adsHandled;
        el.modePanel.classList.add("hidden");
        el.gamePanel.classList.remove("hidden");
        el.modeLabel.textContent = mode === "local" ? "TEK CİHAZ" : `ONLINE • ${displayName(playerNumber)}`;
        render(state);
    }

    function openModal(index, row, column) {
        selectedCell = index;
        el.modalTitle.textContent = `${row.label} + ${column.label}`;
        el.playerSearch.value = "";
        el.searchResults.innerHTML = "";
        el.playerModal.classList.remove("hidden");
        el.playerSearch.focus();
    }

    function closeModal() {
        el.playerModal.classList.add("hidden");
        selectedCell = null;
    }

    async function submit(playerId) {
        if (selectedCell === null) return;
        const index = selectedCell;
        closeModal();
        if (mode === "online") {
            socket.emit("tiki_submit_answer", {index, player_id: playerId});
            return;
        }
        const response = await fetch(config.moveUrl, {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({game_token: config.gameToken, index, player_id: playerId, player_number: state.active_player})
        });
        const payload = await response.json();
        if (payload.state) render(payload.state);
        if (!payload.accepted) el.statusText.textContent = payload.message;
    }

    el.playerSearch.addEventListener("input", () => {
        clearTimeout(searchTimer);
        const query = el.playerSearch.value.trim();
        if (query.length < 2) { el.searchResults.innerHTML = ""; return; }
        searchTimer = setTimeout(async () => {
            const response = await fetch(`${config.searchUrl}?q=${encodeURIComponent(query)}`);
            const players = (await response.json()).slice(0, 20);
            el.searchResults.innerHTML = "";
            players.forEach(player => {
                const button = document.createElement("button");
                button.type = "button";
                button.textContent = player.name;
                if (player.birth_date) {
                    const detail = document.createElement("small");
                    detail.textContent = player.birth_date;
                    button.appendChild(detail);
                }
                button.addEventListener("click", () => submit(player.id));
                el.searchResults.appendChild(button);
            });
        }, 180);
    });

    function showResult() {
        if (window.MatchAds && !el.resultModal.dataset.adsHandled) {
            window.MatchAds.present(state.ad_break || {
                eligible: !String(state.end_reason).toLowerCase().includes("bağlantısı kesildi"),
                match_id: `tiki-${config.gameToken}-local`,
                timeout_ms: 5000
            }, () => {
                el.resultModal.dataset.adsHandled = "1";
                showResult();
            });
            return;
        }
        el.resultTitle.textContent = state.winner ? `${displayName(state.winner)} KAZANDI` : "BERABERE";
        el.resultReason.textContent = state.end_reason;
        el.resultModal.classList.remove("hidden");
    }

    el.localButton.addEventListener("click", async () => {
        el.localButton.disabled = true;
        try {
            const response = await fetch(config.startUrl, {
                method: "POST", headers: {"Content-Type": "application/json"},
                body: JSON.stringify({game_token: config.gameToken})
            });
            const payload = await response.json();
            if (!payload.accepted) throw new Error(payload.message || "Oyun başlatılamadı.");
            state = payload.state;
            start("local");
        } catch (error) {
            el.roomStatus.textContent = error.message;
            el.localButton.disabled = false;
        }
    });
    el.closeModal.addEventListener("click", closeModal);
    el.playerModal.addEventListener("click", event => { if (event.target === el.playerModal) closeModal(); });
    el.createRoomButton.addEventListener("click", () => {
        if (socket) { socket.emit("tiki_create_room"); el.roomStatus.textContent = "Oda oluşturuluyor..."; }
    });
    el.joinRoomButton.addEventListener("click", () => socket && socket.emit("tiki_join_room", {room_code: el.roomCodeInput.value}));
    el.randomMatchButton.addEventListener("click", () => {
        if (!socket) return;
        if (matchmaking) {
            socket.emit("tiki_cancel_random_match");
            matchmaking = false;
            el.randomMatchButton.textContent = "RASTGELE RAKİP BUL";
            el.roomStatus.textContent = "Eşleştirme iptal edildi.";
            return;
        }
        matchmaking = true;
        el.randomMatchButton.textContent = "ARAMAYI İPTAL ET";
        el.roomStatus.textContent = "Rastgele rakip aranıyor...";
        socket.emit("tiki_find_random_match");
    });
    el.rematchButton.addEventListener("click", async () => {
        if (mode === "online") {
            socket.emit("tiki_rematch_request");
            el.rematchButton.disabled = true;
            el.resultReason.textContent = "Rakip bekleniyor...";
            return;
        }
        const response = await fetch(config.rematchUrl, {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({game_token: config.gameToken})
        });
        const payload = await response.json();
        if (payload.accepted) { delete el.resultModal.dataset.adsHandled; el.resultModal.classList.add("hidden"); render(payload.state); }
    });

    if (socket) {
        socket.on("tiki_room_created", payload => {
            playerNumber = payload.player_number;
            el.roomStatus.textContent = `ODA KODU: ${payload.room_code} • Rakip bekleniyor`;
        });
        socket.on("tiki_room_joined", payload => { playerNumber = payload.player_number; });
        socket.on("tiki_matchmaking_waiting", () => { el.roomStatus.textContent = "Uygun bir rakip bekleniyor..."; });
        socket.on("tiki_matchmaking_found", payload => {
            matchmaking = false;
            playerNumber = payload.player_number;
            el.randomMatchButton.textContent = "RASTGELE RAKİP BUL";
            el.roomStatus.textContent = "Rakip bulundu. Maç hazırlanıyor...";
        });
        socket.on("tiki_matchmaking_cancelled", () => { matchmaking = false; });
        socket.on("tiki_matchmaking_error", payload => {
            matchmaking = false;
            el.randomMatchButton.textContent = "RASTGELE RAKİP BUL";
            el.roomStatus.textContent = payload.message;
        });
        socket.on("tiki_game_ready", payload => { state = payload.state; start("online"); });
        socket.on("online_answer", showOnlineAnswer);
        socket.on("tiki_game_state", render);
        socket.on("tiki_move_result", payload => { if (!payload.accepted) el.statusText.textContent = payload.message; });
        socket.on("tiki_room_error", payload => { el.roomStatus.textContent = payload.message; });
        socket.on("tiki_opponent_left", payload => {
            if (payload.match_was_already_finished) return;
            el.statusText.textContent = payload.message;
        });
        socket.on("tiki_rematch_started", payload => {
            el.rematchButton.disabled = false;
            delete el.resultModal.dataset.adsHandled;
            el.resultModal.classList.add("hidden");
            render(payload.state);
        });
    }

    setInterval(updateTurnClock, 250);
    setInterval(async () => {
        if (mode !== "local" || !state.started || state.finished || localStatePolling) return;
        localStatePolling = true;
        try {
            const response = await fetch(config.stateUrl);
            if (!response.ok) return;
            const payload = await response.json();
            if (payload.accepted && payload.state.turn_deadline !== state.turn_deadline) {
                render(payload.state);
            }
        } catch (error) {
            // Geçici bağlantı hatasında mevcut ekranı koru; sonraki aralıkta yeniden dene.
        } finally {
            localStatePolling = false;
        }
    }, 1000);
})();
