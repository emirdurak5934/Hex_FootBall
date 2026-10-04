let currentPlayer = 1;

function navigateTo(path) {
    if (window.MobileBridge) window.MobileBridge.navigate(path);
    else window.location.href = path;
}

let selectedIndex = null;

let selectedPlayerId = null;

let gameFinished = false;

let onlineRoomCode = null;

let onlinePlayerNumber = null;

let onlineGame = false;

let onlineMatchStarted = false;

let playerNames = {"1": "OYUNCU 1", "2": "OYUNCU 2"};

const requiresOnlineMatch = Boolean(
    document.getElementById("multiplayerMenu")
);


function canUsePossessionBoard() {

    if (gameFinished) {
        return false;
    }

    if (
        requiresOnlineMatch
        && (!onlineGame || !onlineMatchStarted)
    ) {
        return false;
    }

    return !(
        onlineGame
        && onlinePlayerNumber !== currentPlayer
    );

}


const START_TIME =
    4 * 60;


let playerOneTime =
    START_TIME;

let playerTwoTime =
    START_TIME;


const owners =
    new Map();


let conditions =
    window.GAME_DATA.conditions;


const neighbors =
    window.GAME_DATA.neighbors;


/* ==================================================
   ELEMENTS
================================================== */

const hexes =
    document.querySelectorAll(
        ".hex"
    );


const playerOneScore =
    document.getElementById(
        "playerOneScore"
    );


const playerTwoScore =
    document.getElementById(
        "playerTwoScore"
    );


const playerOneClock =
    document.getElementById(
        "playerOneClock"
    );


const playerTwoClock =
    document.getElementById(
        "playerTwoClock"
    );

const playerOneName = document.getElementById("playerOneName");
const playerTwoName = document.getElementById("playerTwoName");


const turnIndicator =
    document.getElementById(
        "turnIndicator"
    );


const remainingCount =
    document.getElementById(
        "remainingCount"
    );


const modalBackdrop =
    document.getElementById(
        "gameModal"
    );


const modalClickBackdrop =
    document.getElementById(
        "gameModalBackdrop"
    );


const closeModal =
    document.getElementById(
        "closeModalButton"
    );


const cancelButton =
    closeModal;


const checkButton =
    document.getElementById(
        "checkAnswerButton"
    );


const playerInput =
    document.getElementById(
        "playerInput"
    );


const playerSuggestions =
    document.getElementById(
        "playerSuggestions"
    );


const message =
    document.getElementById(
        "answerMessage"
    );


const selectedConditionImage =
    document.getElementById(
        "selectedConditionImage"
    );


const selectedConditionLabel =
    document.getElementById(
        "selectedConditionLabel"
    );


const modalTurn =
    document.querySelector(
        ".modal-eyebrow"
    );


const selectedCondition =
    document.querySelector(
        ".selected-condition"
    );


const neighborGrid =
    document.getElementById(
        "neighborHexes"
    );


const helpButton =
    document.getElementById(
        "helpButton"
    );


const helpBackdrop =
    document.getElementById(
        "helpModal"
    );


const helpClickBackdrop =
    document.getElementById(
        "helpModalBackdrop"
    );


const closeHelp =
    document.getElementById(
        "closeHelpButton"
    );


const forfeitMenuButton = document.getElementById("forfeitMenuButton");
const forfeitModal = document.getElementById("forfeitModal");
const forfeitModalBackdrop = document.getElementById("forfeitModalBackdrop");
const confirmForfeitButton = document.getElementById("confirmForfeitButton");
const cancelForfeitButton = document.getElementById("cancelForfeitButton");


const resultBackdrop =
    document.getElementById(
        "gameOverModal"
    );


const resultWinner =
    document.getElementById(
        "gameOverTitle"
    );


const resultReason =
    document.getElementById(
        "gameOverReason"
    );


const resultScoreOne =
    document.getElementById(
        "finalPlayerOneScore"
    );


const resultScoreTwo =
    document.getElementById(
        "finalPlayerTwoScore"
    );


const rematchButton =
    document.getElementById(
        "playAgainButton"
    );


const mainMenuButton =
    document.getElementById(
        "mainMenuButton"
    );


const rematchStatus =
    document.getElementById(
        "rematchStatus"
    );


/* ==================================================
   TIMER
================================================== */

let timerInterval =
    null;


function startTimer() {

    if (
        timerInterval
    ) {

        clearInterval(
            timerInterval
        );

    }


    timerInterval =
        setInterval(
            () => {

                if (!canUsePossessionBoard()) {

                    return;

                }


                if (
                    currentPlayer === 1
                ) {

                    playerOneTime--;


                    if (
                        playerOneTime <= 0
                    ) {

                        playerOneTime = 0;

                        updateClocks();

                        endByTime(
                            2
                        );

                        return;

                    }

                } else {

                    playerTwoTime--;


                    if (
                        playerTwoTime <= 0
                    ) {

                        playerTwoTime = 0;

                        updateClocks();

                        endByTime(
                            1
                        );

                        return;

                    }

                }


                updateClocks();

            },
            1000
        );

}


/* ==================================================
   CLOCK
================================================== */

function formatTime(
    totalSeconds
) {

    const safeSeconds =
        Math.max(
            0,
            totalSeconds
        );


    const minutes =
        Math.floor(
            safeSeconds / 60
        );


    const seconds =
        safeSeconds % 60;


    return (
        String(
            minutes
        ).padStart(
            2,
            "0"
        )
        +
        ":"
        +
        String(
            seconds
        ).padStart(
            2,
            "0"
        )
    );

}


function updateClocks() {

    playerOneClock.textContent =
        formatTime(
            playerOneTime
        );


    playerTwoClock.textContent =
        formatTime(
            playerTwoTime
        );


    playerOneClock.classList.toggle(
        "active-clock",
        currentPlayer === 1
    );


    playerTwoClock.classList.toggle(
        "active-clock",
        currentPlayer === 2
    );

}


/* ==================================================
   PETEK TIKLAMA
================================================== */

hexes.forEach(
    hex => {

        hex.addEventListener(
            "click",
            () => {

                if (
                    gameFinished
                ) {

                    return;

                }


                if (
                    onlineGame
                    &&
                    onlinePlayerNumber !== currentPlayer
                ) {

                    return;

                }


                const index =
                    Number(
                        hex.dataset.index
                    );


                const owner =
                    owners.get(
                        index
                    ) || 0;


                /*
                    SADECE BOŞ PETEK
                    SEÇİLEBİLİR
                */

                if (
                    owner !== 0
                ) {

                    return;

                }


                openModal(
                    index
                );

            }
        );

    }
);


/* ==================================================
   MODAL
================================================== */

function openModal(
    index
) {

    if (!canUsePossessionBoard()) {
        return;
    }

    const owner =
        owners.get(
            index
        ) || 0;


    if (
        owner !== 0
    ) {

        return;

    }


    selectedIndex =
        index;


    selectedPlayerId =
        null;


    hideSuggestions();


    hexes.forEach(
        hex => {

            hex.classList.remove(
                "selected"
            );

        }
    );


    const selectedHex =
        document.querySelector(
            `.hex[data-index="${index}"]`
        );


    if (
        selectedHex
    ) {

        selectedHex.classList.add(
            "selected"
        );

    }


    const condition =
        conditions[
            index
        ];


    modalTurn.textContent =
        currentPlayer === 1
            ? `${playerNames["1"]} HAMLESİ`
            : `${playerNames["2"]} HAMLESİ`;


    modalTurn.style.color =
        currentPlayer === 1
            ? "#3384ff"
            : "#ef3d48";


    selectedCondition.innerHTML =
        makeMainCard(
            condition
        );


    neighborGrid.innerHTML =
        "";


    const neighborIndexes =
        neighbors[index]
        || [];


    neighborIndexes.forEach(
        neighborIndex => {

            const neighborCondition =
                conditions[
                    neighborIndex
                ];


            const card =
                document.createElement(
                    "div"
                );


            card.className =
                "neighbor-card";


            card.innerHTML =
                makeNeighborCard(
                    neighborCondition
                );


            neighborGrid.appendChild(
                card
            );

        }
    );


    playerInput.value =
        "";


    message.textContent =
        "";


    message.className =
        "message";


    modalBackdrop.classList.remove(
        "hidden"
    );


    setTimeout(
        () => {

            playerInput.focus();

        },
        100
    );

}


/* ==================================================
   CARD HTML
================================================== */

function makeMainCard(
    condition
) {

    return `
        <div class="modal-main-card">

            ${
                condition.image

                    ? `
                        <img
                            src="${condition.image}"
                            alt="${escapeHtml(condition.label)}"
                        >
                    `

                    : `
                        <div class="fallback-icon">
                            ⚽
                        </div>
                    `
            }

            <strong>
                ${escapeHtml(condition.label)}
            </strong>

        </div>
    `;

}


function makeNeighborCard(
    condition
) {

    return `
        ${
            condition.image

                ? `
                    <img
                        src="${condition.image}"
                        alt="${escapeHtml(condition.label)}"
                    >
                `

                : `
                    <div class="fallback-icon">
                        ⚽
                    </div>
                `
        }

        <span>
            ${escapeHtml(condition.label)}
        </span>
    `;

}


/* ==================================================
   PLAYER SEARCH
================================================== */

let searchTimeout =
    null;


let suggestionButtons =
    [];


let activeSuggestionIndex =
    -1;


playerInput.addEventListener(
    "input",
    () => {

        if (!canUsePossessionBoard()) {
            playerInput.value = "";
            hideSuggestions();
            return;
        }

        selectedPlayerId =
            null;


        activeSuggestionIndex =
            -1;


        clearTimeout(
            searchTimeout
        );


        const query =
            playerInput.value.trim();


        if (
            query.length < 2
        ) {

            hideSuggestions();

            return;

        }


        searchTimeout =
            setTimeout(
                () => {

                    searchPlayers(
                        query
                    );

                },
                170
            );

    }
);


async function searchPlayers(
    query
) {

    if (!canUsePossessionBoard()) {
        hideSuggestions();
        return;
    }

    try {

        const response =
            await fetch(
                "/search_players?q="
                +
                encodeURIComponent(
                    query
                )
            );


        if (
            !response.ok
        ) {

            hideSuggestions();

            return;

        }


        const results =
            await response.json();


        showSuggestions(
            results
        );


    } catch (
        error
    ) {

        console.error(
            error
        );


        hideSuggestions();

    }

}


/* ==================================================
   SEARCH RESULTS
================================================== */

function showSuggestions(
    results
) {

    playerSuggestions.innerHTML =
        "";


    suggestionButtons =
        [];


    activeSuggestionIndex =
        -1;


    if (
        !results.length
    ) {

        hideSuggestions();

        return;

    }


    results.forEach(
        player => {

            const button =
                document.createElement(
                    "button"
                );


            button.type =
                "button";


            button.className =
                "player-suggestion";


            let extra =
                "";


            if (
                player.show_age
            ) {

                if (
                    player.age !== null
                    &&
                    player.age !== undefined
                ) {

                    extra =
                        `${player.age} yaş`;

                } else if (
                    player.birth_date
                ) {

                    extra =
                        player.birth_date;

                }

            }


            button.innerHTML =
                `
                    <span
                        class="player-suggestion-name"
                    >
                        ${escapeHtml(player.name)}
                    </span>

                    ${
                        extra

                            ? `
                                <span
                                    class="player-suggestion-extra"
                                >
                                    ${escapeHtml(extra)}
                                </span>
                            `

                            : ""
                    }
                `;


            button.addEventListener(
                "click",
                () => {

                    selectSuggestedPlayer(
                        player
                    );

                }
            );


            playerSuggestions.appendChild(
                button
            );


            suggestionButtons.push(
                button
            );

        }
    );


    playerSuggestions.classList.remove(
        "hidden"
    );

}


/* ==================================================
   SELECT PLAYER
================================================== */

function selectSuggestedPlayer(
    player
) {

    playerInput.value =
        player.name;


    if (
        player.id !== null
        &&
        player.id !== undefined
    ) {

        selectedPlayerId =
            String(
                player.id
            );

    } else {

        selectedPlayerId =
            null;

    }


    hideSuggestions();


    playerInput.focus();

}


/* ==================================================
   SEARCH KEYBOARD
================================================== */

playerInput.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "ArrowDown"
            &&
            suggestionButtons.length
        ) {

            event.preventDefault();


            activeSuggestionIndex =
                Math.min(
                    activeSuggestionIndex + 1,
                    suggestionButtons.length - 1
                );


            updateSuggestionHighlight();

            return;

        }


        if (
            event.key === "ArrowUp"
            &&
            suggestionButtons.length
        ) {

            event.preventDefault();


            activeSuggestionIndex =
                Math.max(
                    activeSuggestionIndex - 1,
                    0
                );


            updateSuggestionHighlight();

            return;

        }


        if (
            event.key === "Enter"
        ) {

            event.preventDefault();


            if (
                activeSuggestionIndex >= 0
                &&
                suggestionButtons[
                    activeSuggestionIndex
                ]
            ) {

                suggestionButtons[
                    activeSuggestionIndex
                ].click();

                return;

            }


            if (
                !selectedPlayerId
            ) {

                showError(
                    "Futbolcuyu listeden seç."
                );

                return;

            }


            checkAnswer();

            return;

        }


        if (
            event.key === "Escape"
        ) {

            hideSuggestions();

        }

    }
);


function updateSuggestionHighlight() {

    suggestionButtons.forEach(
        (
            button,
            index
        ) => {

            button.classList.toggle(
                "keyboard-active",
                index ===
                activeSuggestionIndex
            );

        }
    );

}


/* ==================================================
   HIDE SUGGESTIONS
================================================== */

function hideSuggestions() {

    playerSuggestions.classList.add(
        "hidden"
    );


    playerSuggestions.innerHTML =
        "";


    suggestionButtons =
        [];


    activeSuggestionIndex =
        -1;

}


/* ==================================================
   ESCAPE HTML
================================================== */

function escapeHtml(
    text
) {

    return String(
        text ?? ""
    )
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );

}


/* ==================================================
   MODAL CLOSE
================================================== */

function closeGameModal() {

    modalBackdrop.classList.add(
        "hidden"
    );


    hideSuggestions();


    hexes.forEach(
        hex => {

            hex.classList.remove(
                "selected"
            );

        }
    );


    selectedIndex =
        null;


    selectedPlayerId =
        null;


    playerInput.value =
        "";


    message.textContent =
        "";

}


closeModal.addEventListener(
    "click",
    closeGameModal
);


cancelButton.addEventListener(
    "click",
    closeGameModal
);


modalClickBackdrop.addEventListener(
    "click",
    closeGameModal
);


/* ==================================================
   CHECK
================================================== */

checkButton.addEventListener(
    "click",
    checkAnswer
);


async function checkAnswer() {

    if (
        selectedIndex === null
        ||
        gameFinished
    ) {

        return;

    }


    const playerName =
        playerInput.value.trim();


    if (
        !playerName
    ) {

        showError(
            "Bir futbolcu seç."
        );

        return;

    }


    /*
        LISTEDEN FUTBOLCU
        SEÇMEK ZORUNLU
    */

    if (
        !selectedPlayerId
    ) {

        showError(
            "Futbolcuyu listeden seç."
        );

        return;

    }


    hideSuggestions();


    checkButton.disabled =
        true;


    if (
        onlineGame
    ) {

        socket.emit(
            "submit_move",
            {
                index:
                    selectedIndex,

                player_id:
                    selectedPlayerId
            }
        );

        return;

    }


    try {

        const response =
            await fetch(
                "/check",
                {

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            player:
                                playerName,

                            player_id:
                                selectedPlayerId,

                            index:
                                selectedIndex

                        })

                }
            );


        const data =
            await response.json();


        /*
            YANLIŞ
        */

        if (
            !data.correct
        ) {

            showError(
                data.message
            );


            await delay(
                650
            );


            finishTurn();

            return;

        }


        /*
            DOĞRU
        */

        const sourceIndex =
            selectedIndex;


        /*
            ÖNCE MODAL KAPANIR
        */

        closeGameModal();


        await delay(
            100
        );


        /*
            RENK BULAŞMA
        */

        await claimHexesWithFlow(
            sourceIndex,
            data.solved
        );


        updateScores();


        if (
            gameFinished
        ) {

            return;

        }


        /*
            SIRA RAKİBE
        */

        currentPlayer =
            currentPlayer === 1
                ? 2
                : 1;


        updateTurnUI();


    } catch (
        error
    ) {

        console.error(
            error
        );


    } finally {

        checkButton.disabled =
            false;

    }

}


/* ==================================================
   CLAIM + FLOW
================================================== */

async function claimHexesWithFlow(
    sourceIndex,
    indexes
) {

    const sourceHex =
        document.querySelector(
            `.hex[data-index="${sourceIndex}"]`
        );


    if (
        !sourceHex
    ) {

        return;

    }


    const sourceOwner =
        owners.get(
            sourceIndex
        ) || 0;


    /*
        ANA PETEK MUTLAKA
        BOŞ OLMALI
    */

    if (
        sourceOwner !== 0
    ) {

        return;

    }


    /*
        ANA PETEĞİ AL
    */

    await applyOwnerToHex(
        sourceIndex,
        false
    );


    /*
        ANA PETEK PARLAR
    */

    if (
        currentPlayer === 1
    ) {

        sourceHex.classList.add(
            "source-pulse-one"
        );

    } else {

        sourceHex.classList.add(
            "source-pulse-two"
        );

    }


    await delay(
        240
    );


    sourceHex.classList.remove(
        "source-pulse-one",
        "source-pulse-two"
    );


    const realNeighbors =
        neighbors[
            sourceIndex
        ] || [];


    /*
        SADECE DOĞRUDAN
        KOMŞULAR ETKİLENİR
    */

    for (
        const targetIndex of indexes
    ) {

        if (
            targetIndex ===
            sourceIndex
        ) {

            continue;

        }


        if (
            !realNeighbors.includes(
                targetIndex
            )
        ) {

            continue;

        }


        const previousOwner =
            owners.get(
                targetIndex
            ) || 0;


        /*
            ZATEN BİZİMSE
            HİÇBİR ŞEY YOK
        */

        if (
            previousOwner ===
            currentPlayer
        ) {

            continue;

        }


        const targetHex =
            document.querySelector(
                `.hex[data-index="${targetIndex}"]`
            );


        if (
            !targetHex
        ) {

            continue;

        }


        await animateFlowBetweenHexes(
            sourceHex,
            targetHex
        );


        await applyOwnerToHex(
            targetIndex,
            true
        );


        await delay(
            60
        );

    }

}


/* ==================================================
   APPLY OWNER
================================================== */

async function applyOwnerToHex(
    index,
    impact = false
) {

    const hex =
        document.querySelector(
            `.hex[data-index="${index}"]`
        );


    if (
        !hex
    ) {

        return;

    }


    hex.classList.remove(
        "owner-one",
        "owner-two",
        "selected",
        "source-pulse-one",
        "source-pulse-two",
        "target-impact-one",
        "target-impact-two"
    );


    if (
        impact
    ) {

        if (
            currentPlayer === 1
        ) {

            hex.classList.add(
                "target-impact-one"
            );

        } else {

            hex.classList.add(
                "target-impact-two"
            );

        }


        await delay(
            300
        );


        hex.classList.remove(
            "target-impact-one",
            "target-impact-two"
        );

    }


    if (
        currentPlayer === 1
    ) {

        hex.classList.add(
            "owner-one"
        );

    } else {

        hex.classList.add(
            "owner-two"
        );

    }


    hex.dataset.owner =
        String(
            currentPlayer
        );


    owners.set(
        index,
        currentPlayer
    );

}


/* ==================================================
   FLOW BETWEEN HEXES
================================================== */

function animateFlowBetweenHexes(
    sourceHex,
    targetHex,
    playerNumber = currentPlayer
) {

    return new Promise(
        resolve => {

            const sourceRect =
                sourceHex.getBoundingClientRect();


            const targetRect =
                targetHex.getBoundingClientRect();


            const startX =
                sourceRect.left
                +
                sourceRect.width / 2;


            const startY =
                sourceRect.top
                +
                sourceRect.height / 2;


            const endX =
                targetRect.left
                +
                targetRect.width / 2;


            const endY =
                targetRect.top
                +
                targetRect.height / 2;


            const deltaX =
                endX - startX;


            const deltaY =
                endY - startY;


            const distance =
                Math.sqrt(
                    deltaX * deltaX
                    +
                    deltaY * deltaY
                );


            const angle =
                Math.atan2(
                    deltaY,
                    deltaX
                )
                *
                180
                /
                Math.PI;


            const line =
                document.createElement(
                    "div"
                );


            line.className =
                "hex-flow-line";


            if (
                playerNumber === 1
            ) {

                line.classList.add(
                    "player-one-flow"
                );

            } else {

                line.classList.add(
                    "player-two-flow"
                );

            }


            line.style.left =
                `${startX}px`;


            line.style.top =
                `${startY}px`;


            line.style.width =
                `${distance}px`;


            line.style.setProperty(
                "--flow-angle",
                `${angle}deg`
            );


            document.body.appendChild(
                line
            );


            setTimeout(
                () => {

                    line.remove();

                    resolve();

                },
                360
            );

        }
    );

}


/* ==================================================
   SCORE
================================================== */

function updateScores() {

    let one =
        0;


    let two =
        0;


    owners.forEach(
        owner => {

            if (
                owner === 1
            ) {

                one++;

            }


            if (
                owner === 2
            ) {

                two++;

            }

        }
    );


    playerOneScore.textContent =
        one;


    playerTwoScore.textContent =
        two;


    remainingCount.textContent =
        Math.max(
            0,
            31 - owners.size
        );


    if (
        owners.size === 31
    ) {

        finishGame();

    }

}


/* ==================================================
   WRONG ANSWER TURN
================================================== */

function finishTurn() {

    if (
        gameFinished
        ||
        onlineGame
    ) {

        return;

    }


    closeGameModal();


    currentPlayer =
        currentPlayer === 1
            ? 2
            : 1;


    updateTurnUI();

}


/* ==================================================
   TURN UI
================================================== */

function updateTurnUI() {

    if (
        currentPlayer === 1
    ) {

        turnIndicator.textContent =
            `SIRA: ${playerNames["1"]}`;


        turnIndicator.classList.add(
            "player-one-turn"
        );


        turnIndicator.classList.remove(
            "player-two-turn"
        );

    } else {

        turnIndicator.textContent =
            `SIRA: ${playerNames["2"]}`;


        turnIndicator.classList.add(
            "player-two-turn"
        );


        turnIndicator.classList.remove(
            "player-one-turn"
        );

    }


    updateClocks();

}


/* ==================================================
   ERROR
================================================== */

function showError(
    text
) {

    message.textContent =
        "✕ "
        +
        text;


    message.className =
        "message error";

}


/* ==================================================
   HELP
================================================== */

helpButton.addEventListener(
    "click",
    () => {

        helpBackdrop.classList.remove(
            "hidden"
        );

    }
);


closeHelp.addEventListener(
    "click",
    () => {

        helpBackdrop.classList.add(
            "hidden"
        );

    }
);


helpClickBackdrop.addEventListener(
    "click",
    () => {

        helpBackdrop.classList.add(
            "hidden"
        );

    }
);


/* ==================================================
   TIME OUT
================================================== */

function endByTime(
    winner
) {

    if (
        gameFinished
    ) {

        return;

    }


    gameFinished =
        true;


    clearInterval(
        timerInterval
    );


    showResultModal(
        winner,
        "Rakibin süresi bitti."
    );

}


/* ==================================================
   FINISH GAME
================================================== */

function finishGame() {

    if (
        gameFinished
    ) {

        return;

    }


    gameFinished =
        true;


    clearInterval(
        timerInterval
    );


    const one =
        Number(
            playerOneScore.textContent
        );


    const two =
        Number(
            playerTwoScore.textContent
        );


    const winner =
        one > two
            ? 1
            : 2;


    showResultModal(
        winner,
        "Tüm petekler doldu."
    );

}


/* ==================================================
   RESULT MODAL
================================================== */

function showResultModal(
    winner,
    reason,
    scores = null,
    adBreak = null,
    adsHandled = false
) {

    if (!adsHandled && window.MatchAds) {
        const inferred = adBreak || {
            eligible: reason !== "forfeit" && !String(reason).toLowerCase().includes("bağlantısı kesildi"),
            match_id: `possession-${onlineRoomCode || "local"}-${Date.now()}`,
            timeout_ms: 5000
        };
        window.MatchAds.present(
            inferred,
            () => showResultModal(winner, reason, scores, inferred, true)
        );
        return;
    }

    const one =
        scores
            ? Number(scores["1"])
            : Number(playerOneScore.textContent);


    const two =
        scores
            ? Number(scores["2"])
            : Number(playerTwoScore.textContent);


    resultScoreOne.textContent =
        one;


    resultScoreTwo.textContent =
        two;


    resultReason.textContent =
        reason === "forfeit"
            ? "Rakibin pes etti. Maçı kazandın."
            : reason;


    resultWinner.classList.remove(
        "player-one-winner",
        "player-two-winner",
        "draw-result"
    );


    resultBackdrop.classList.remove(
        "local-win",
        "local-loss",
        "draw-result"
    );


    if (
        winner === 1
    ) {

        resultWinner.textContent =
            `${playerNames["1"]} KAZANDI`;


        resultWinner.classList.add(
            "player-one-winner"
        );

    } else if (
        winner === 2
    ) {

        resultWinner.textContent =
            `${playerNames["2"]} KAZANDI`;


        resultWinner.classList.add(
            "player-two-winner"
        );

    } else {

        resultWinner.textContent =
            "BERABERE";


        resultWinner.classList.add(
            "draw-result"
        );

    }


    if (
        winner === null
        ||
        winner === "draw"
    ) {

        resultBackdrop.classList.add(
            "draw-result"
        );

    } else if (
        onlineGame
        &&
        onlinePlayerNumber === Number(winner)
    ) {

        resultBackdrop.classList.add(
            "local-win"
        );

    } else if (
        onlineGame
    ) {

        resultBackdrop.classList.add(
            "local-loss"
        );

    }


    resultBackdrop.classList.remove(
        "hidden"
    );

}


/* ==================================================
   REMATCH
================================================== */

function returnToMainMenu() {

    if (
        onlineGame
    ) {

        socket.emit(
            "leave_game_room"
        );

    }


    navigateTo("/");

}


rematchButton.addEventListener(
    "click",
    () => {

        if (
            !onlineGame
        ) {

            returnToMainMenu();

            return;

        }


        rematchButton.disabled =
            true;


        rematchButton.textContent =
            "BEKLENİYOR...";


        socket.emit(
            "request_rematch"
        );

    }
);


function closeForfeitModal() {
    forfeitModal.classList.add("hidden");
    confirmForfeitButton.disabled = false;
}


forfeitMenuButton.addEventListener("click", () => {
    if (gameFinished) {
        navigateTo(forfeitMenuButton.dataset.homeUrl);
        return;
    }
    if (onlineGame && onlineMatchStarted) {
        forfeitModal.classList.remove("hidden");
    } else {
        navigateTo(forfeitMenuButton.dataset.homeUrl);
    }
});


cancelForfeitButton.addEventListener("click", closeForfeitModal);
forfeitModalBackdrop.addEventListener("click", closeForfeitModal);


confirmForfeitButton.addEventListener("click", () => {
    confirmForfeitButton.disabled = true;
    socket.emit("forfeit_match", response => {
        if (response && response.ok) {
            navigateTo(forfeitMenuButton.dataset.homeUrl);
            return;
        }
        confirmForfeitButton.disabled = false;
    });
});


mainMenuButton.addEventListener(
    "click",
    returnToMainMenu
);


/* ==================================================
   ESC
================================================== */

document.addEventListener(
    "keydown",
    event => {

        if (
            event.key !== "Escape"
        ) {

            return;

        }


        if (
            !helpBackdrop.classList.contains(
                "hidden"
            )
        ) {

            helpBackdrop.classList.add(
                "hidden"
            );

            return;

        }


        if (
            !modalBackdrop.classList.contains(
                "hidden"
            )
        ) {

            /*
                ESC HAMLE YAKMAZ
            */

            closeGameModal();

        }

    }
);


/* ==================================================
   DELAY
================================================== */

function delay(
    milliseconds
) {

    return new Promise(
        resolve => {

            setTimeout(
                resolve,
                milliseconds
            );

        }
    );

}


/* ==================================================
   START
================================================== */

updateClocks();

updateTurnUI();

if (
    !document.getElementById(
        "multiplayerMenu"
    )
) {

    startTimer();

}
/* ==================================================
MULTIPLAYER
================================================== */

const socket =
    io();


let pendingOnlineAnimation =
    null;


const ownershipVisualTimers =
    new Map();


/* ==================================================
ELEMENTS
================================================== */

const multiplayerMenu =
    document.getElementById(
        "multiplayerMenu"
    );


const gameApp = document.getElementById("app");
const lobbyMainActions = document.getElementById("lobbyMainActions");
const joinRoomPanel = document.getElementById("joinRoomPanel");
const showJoinRoomButton = document.getElementById("showJoinRoomButton");
const joinLobbyBackButton = document.getElementById("joinLobbyBackButton");


const createRoomButton =
    document.getElementById(
        "createRoomButton"
    );

const findRandomMatchButton = document.getElementById("findRandomMatchButton");
const waitingTitle = document.getElementById("waitingTitle");
const roomCodeBlock = document.getElementById("roomCodeBlock");
const matchmakingPlayers = document.getElementById("matchmakingPlayers");
const onlineAnswerToast = document.getElementById("onlineAnswerToast");
const onlineAnswerAccount = document.getElementById("onlineAnswerAccount");
const onlineAnswerPlayer = document.getElementById("onlineAnswerPlayer");
const onlineAnswerResult = document.getElementById("onlineAnswerResult");
let onlineAnswerTimer = null;
let onlineAnswerHideTimer = null;
let lastOnlineAnswerId = null;

function showOnlineAnswer(data) {
    if (!onlineAnswerToast || !data) return;
    if (data.notice_id && data.notice_id === lastOnlineAnswerId) return;
    const remainingDuration = data.expires_at_ms
        ? Number(data.expires_at_ms) - Date.now()
        : Number(data.duration_ms) || 2000;
    if (remainingDuration <= 0) return;
    lastOnlineAnswerId = data.notice_id || null;
    clearTimeout(onlineAnswerTimer);
    clearTimeout(onlineAnswerHideTimer);
    const answerHex = Number.isInteger(Number(data.hex_index))
        ? document.querySelector(`.hex[data-index="${Number(data.hex_index)}"]`)
        : null;

    onlineAnswerToast.classList.toggle("on-possession-hex", Boolean(answerHex));
    if (answerHex) {
        const rect = answerHex.getBoundingClientRect();
        onlineAnswerToast.style.left = `${rect.left + rect.width / 2}px`;
        onlineAnswerToast.style.top = `${rect.top + rect.height / 2}px`;
        onlineAnswerToast.style.width = `${Math.max(52, rect.width * 0.86)}px`;
        onlineAnswerToast.style.maxHeight = `${Math.max(48, rect.height * 0.72)}px`;
    } else {
        onlineAnswerToast.style.removeProperty("left");
        onlineAnswerToast.style.removeProperty("top");
        onlineAnswerToast.style.removeProperty("width");
        onlineAnswerToast.style.removeProperty("max-height");
    }
    onlineAnswerToast.classList.remove("hidden", "hiding", "correct", "wrong");
    onlineAnswerToast.classList.add(data.correct ? "correct" : "wrong");
    onlineAnswerAccount.textContent = data.account_name;
    onlineAnswerPlayer.textContent = data.player_name;
    onlineAnswerResult.textContent = data.correct ? "DOĞRU CEVAP" : "YANLIŞ CEVAP";
    onlineAnswerTimer = setTimeout(() => {
        onlineAnswerToast.classList.add("hiding");
        onlineAnswerHideTimer = setTimeout(() => {
            onlineAnswerToast.classList.add("hidden");
            onlineAnswerToast.classList.remove("on-possession-hex");
            onlineAnswerToast.style.removeProperty("left");
            onlineAnswerToast.style.removeProperty("top");
            onlineAnswerToast.style.removeProperty("width");
            onlineAnswerToast.style.removeProperty("max-height");
        }, 180);
    }, Math.min(2000, remainingDuration));
}


const joinRoomButton =
    document.getElementById(
        "joinRoomButton"
    );


const roomCodeInput =
    document.getElementById(
        "roomCodeInput"
    );


const roomStatus =
    document.getElementById(
        "roomStatus"
    );


const possessionHomeButton =
    document.getElementById(
        "possessionHomeButton"
    );


if (possessionHomeButton) {

    possessionHomeButton.addEventListener(
        "click",
        returnToMainMenu
    );

}


const roomWaitingScreen =
    document.getElementById(
        "roomWaitingScreen"
    );


const createdRoomCode =
    document.getElementById(
        "createdRoomCode"
    );


const waitingMessage =
    document.getElementById(
        "waitingMessage"
    );


const leaveRoomButton =
    document.getElementById(
        "leaveRoomButton"
    );


const copyRoomCodeButton = document.getElementById("copyRoomCodeButton");
const copyRoomCodeStatus = document.getElementById("copyRoomCodeStatus");


function showMainLobby() {
    lobbyMainActions.classList.remove("hidden");
    joinRoomPanel.classList.add("hidden");
    roomStatus.textContent = "";
    roomCodeInput.value = "";
}


showJoinRoomButton.addEventListener("click", () => {
    lobbyMainActions.classList.add("hidden");
    joinRoomPanel.classList.remove("hidden");
    roomStatus.textContent = "";
    setTimeout(() => roomCodeInput.focus(), 50);
});


joinLobbyBackButton.addEventListener("click", showMainLobby);


copyRoomCodeButton.addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(createdRoomCode.textContent.trim());
        copyRoomCodeStatus.textContent = "Kopyalandı";
    } catch (error) {
        copyRoomCodeStatus.textContent = "Kod kopyalanamadı";
    }

    setTimeout(() => {
        copyRoomCodeStatus.textContent = "";
    }, 1600);
});


/* ==================================================
ONLINE STATE
================================================== */

function setHexVisualOwner(
    hex,
    owner
) {

    hex.classList.remove(
        "owner-one",
        "owner-two"
    );


    if (
        owner === 1
    ) {

        hex.classList.add(
            "owner-one"
        );

    }


    if (
        owner === 2
    ) {

        hex.classList.add(
            "owner-two"
        );

    }

}


function applyRoomConditions(
    nextConditions
) {

    if (
        !Array.isArray(nextConditions)
        ||
        nextConditions.length !== hexes.length
    ) {

        return;

    }


    conditions =
        nextConditions;


    hexes.forEach(
        (hex, index) => {

            const condition =
                conditions[index];


            hex.dataset.label =
                condition.label;

            hex.dataset.type =
                condition.type;

            hex.dataset.value =
                condition.value;

            hex.dataset.image =
                condition.image || "";


            const image =
                hex.querySelector(
                    ".hex-image"
                );

            const label =
                hex.querySelector(
                    ".hex-label"
                );


            if (
                image
            ) {

                image.src =
                    condition.image || "";

                image.alt =
                    condition.label;

            }


            if (
                label
            ) {

                label.textContent =
                    condition.label;

            }

        }
    );

}


function resetRematchVisuals() {

    ownershipVisualTimers.forEach(
        timer => clearTimeout(timer)
    );

    ownershipVisualTimers.clear();

    pendingOnlineAnimation =
        null;

    closeGameModal();

    document.querySelectorAll(
        ".hex-flow-line"
    ).forEach(
        line => line.remove()
    );

    hexes.forEach(
        hex => {

            hex.classList.remove(
                "owner-one",
                "owner-two",
                "selected",
                "source-pulse-one",
                "source-pulse-two",
                "target-impact-one",
                "target-impact-two"
            );

            hex.dataset.owner =
                "0";

        }
    );

    message.textContent =
        "";

    resultBackdrop.classList.add(
        "hidden"
    );

    rematchButton.disabled =
        false;

    rematchButton.textContent =
        "TEKRAR OYNA";

}


function animateOnlineOwnership(
    animation,
    targetOwners
) {

    const source =
        Number(
            animation.source
        );


    const directNeighbors =
        neighbors[source]
        || [];


    const targetIndexes = [
        ...new Set(
            animation.claimed.filter(
            index => (
                index !== source
                &&
                directNeighbors.includes(
                    index
                )
            )
            )
        )
    ];


    const sourceHex =
        document.querySelector(
            `.hex[data-index="${source}"]`
        );


    if (
        !sourceHex
    ) {

        return;

    }


    setHexVisualOwner(
        sourceHex,
        Number(
            targetOwners[source]
        )
    );


    const sourceClass =
        `source-pulse-${animation.player_number === 1 ? "one" : "two"}`;


    sourceHex.classList.add(
        sourceClass
    );


    sourceHex.addEventListener(
        "animationend",
        () => sourceHex.classList.remove(
            sourceClass
        ),
        {
            once: true
        }
    );


    targetIndexes.forEach(
        (index, order) => {

            const hex =
                document.querySelector(
                    `.hex[data-index="${index}"]`
                );


            if (
                !hex
            ) {

                return;

            }


            const delay =
                70 * order;


            const timer =
                setTimeout(
                    async () => {

                        await animateFlowBetweenHexes(
                            sourceHex,
                            hex,
                            animation.player_number
                        );


                        ownershipVisualTimers.delete(
                            index
                        );


                        setHexVisualOwner(
                            hex,
                            Number(
                                targetOwners[index]
                            )
                        );


                        const impactClass =
                            `target-impact-${animation.player_number === 1 ? "one" : "two"}`;


                        hex.classList.remove(
                            "target-impact-one",
                            "target-impact-two"
                        );


                        void hex.offsetWidth;


                        hex.classList.add(
                            impactClass
                        );


                        hex.addEventListener(
                            "animationend",
                            () => hex.classList.remove(
                                impactClass
                            ),
                            {
                                once: true
                            }
                        );

                    },
                    delay
                );


            ownershipVisualTimers.set(
                index,
                timer
            );

        }
    );

}


function applyOnlineState(
    state
) {

    if (
        !state
    ) {

        return;

    }

    if (state.latest_answer) {
        showOnlineAnswer(state.latest_answer);
    }


    if (
        state.conditions
    ) {

        applyRoomConditions(
            state.conditions
        );

    }

    if (state.player_names) {
        playerNames = {
            "1": state.player_names["1"] || "OYUNCU 1",
            "2": state.player_names["2"] || "OYUNCU 2"
        };
        if (playerOneName) playerOneName.textContent = playerNames["1"];
        if (playerTwoName) playerTwoName.textContent = playerNames["2"];
        if (matchmakingPlayers) {
            matchmakingPlayers.textContent = `${playerNames["1"]} vs ${playerNames["2"]}`;
        }
    }


    onlineMatchStarted =
        Boolean(state.started)
        && !Boolean(state.finished);


    currentPlayer =
        Number(
            state.active_player
        );


    const serverTimes =
        state.remaining_times
        || state.times;


    playerOneTime =
        Number(
            serverTimes["1"]
        );


    playerTwoTime =
        Number(
            serverTimes["2"]
        );


    gameFinished =
        Boolean(
            state.finished
        );


    owners.clear();


    state.owners.forEach(
        (owner, index) => {

            const hex =
                document.querySelector(
                    `.hex[data-index="${index}"]`
                );


            if (
                !hex
            ) {

                return;

            }


            hex.dataset.owner =
                String(
                    owner
                );


            if (
                !ownershipVisualTimers.has(
                    index
                )
                &&
                !(
                    pendingOnlineAnimation
                    &&
                    pendingOnlineAnimation.claimed.includes(
                        index
                    )
                )
            ) {

                setHexVisualOwner(
                    hex,
                    owner
                );

            }


            if (
                owner !== 0
            ) {

                owners.set(
                    index,
                    owner
                );

            }

        }
    );


    playerOneScore.textContent =
        state.scores["1"];


    playerTwoScore.textContent =
        state.scores["2"];


    remainingCount.textContent =
        Math.max(
            0,
            31 - owners.size
        );


    if (
        pendingOnlineAnimation
    ) {

        animateOnlineOwnership(
            pendingOnlineAnimation,
            state.owners
        );


        pendingOnlineAnimation =
            null;

    }


    document.getElementById(
        "board"
    ).classList.toggle(
        "opponent-turn",
        !canUsePossessionBoard()
    );


    document.getElementById(
        "board"
    ).classList.toggle(
        "game-finished",
        !canUsePossessionBoard()
    );


    updateTurnUI();


    if (
        gameFinished
        &&
        resultBackdrop.classList.contains(
            "hidden"
        )
    ) {

        clearInterval(
            timerInterval
        );


        showResultModal(
            state.winner,
            state.end_reason,
            state.scores,
            state.ad_break || null
        );

    }

}


/* ==================================================
SOCKET CONNECT
================================================== */

socket.on(
    "connect",
    () => {

        console.log(
            "Socket bağlandı:",
            socket.id
        );

        const routeUrl = window.MobileBridge?.currentUrl?.() || window.location.href;
        const invitedRoom = new URL(routeUrl, window.location.href).searchParams.get("room");
        if (invitedRoom && /^[A-Z0-9]{6}$/.test(invitedRoom)) {
            socket.emit("join_game_room", { room_code: invitedRoom });
            if (window.MobileBridge) window.MobileBridge.replaceCurrentPath("/possession");
            else window.history.replaceState({}, "", "/possession");
        }

    }
);

socket.on("online_answer", showOnlineAnswer);


/* ==================================================
ODA KUR
================================================== */

if (
    createRoomButton
) {

    createRoomButton.addEventListener(
        "click",
        () => {

            roomStatus.textContent =
                "Oda oluşturuluyor...";


            socket.emit(
                "create_room"
            );

        }
    );

}

if (findRandomMatchButton) {
    findRandomMatchButton.addEventListener("click", () => {
        roomStatus.textContent = "Rastgele rakip aranıyor...";
        waitingTitle.textContent = "RAKİP ARANIYOR";
        roomCodeBlock.classList.add("hidden");
        waitingMessage.textContent = "Uygun bir oyuncu bekleniyor...";
        matchmakingPlayers.textContent = "";
        roomWaitingScreen.classList.remove("hidden");
        socket.emit("find_random_match");
    });
}

socket.on("matchmaking_waiting", () => {
    roomStatus.textContent = "";
    waitingTitle.textContent = "RAKİP ARANIYOR";
    roomCodeBlock.classList.add("hidden");
    waitingMessage.textContent = "Uygun bir oyuncu bekleniyor...";
});

socket.on("matchmaking_found", data => {
    onlineRoomCode = data.room_code;
    onlinePlayerNumber = data.player_number;
    onlineGame = true;
    waitingTitle.textContent = "RAKİP BULUNDU";
    waitingMessage.textContent = "Maç hazırlanıyor...";
});

socket.on("matchmaking_error", data => {
    roomWaitingScreen.classList.add("hidden");
    roomStatus.textContent = data.message || "Eşleştirme başlatılamadı.";
});


/* ==================================================
ODA OLUŞTU
================================================== */

socket.on(
    "room_created",
    data => {

        onlineRoomCode =
            data.room_code;


        onlinePlayerNumber =
            data.player_number;


        onlineGame =
            true;


        onlineMatchStarted =
            false;


        closeGameModal();


        createdRoomCode.textContent =
            onlineRoomCode;

        waitingTitle.textContent = "ODA HAZIR";
        roomCodeBlock.classList.remove("hidden");


        waitingMessage.textContent =
            "Rakip bekleniyor...";


        roomStatus.textContent =
            "";


        roomWaitingScreen.classList.remove(
            "hidden"
        );


        console.log(
            "Oda:",
            onlineRoomCode
        );


        console.log(
            "Oyuncu:",
            onlinePlayerNumber
        );

    }
);


/* ==================================================
ODA KODU INPUT
================================================== */

if (
    roomCodeInput
) {

    roomCodeInput.addEventListener(
        "input",
        () => {

            roomCodeInput.value =
                roomCodeInput
                    .value
                    .toUpperCase()
                    .replace(
                        /[^A-Z0-9]/g,
                        ""
                    )
                    .slice(
                        0,
                        6
                    );

        }
    );

}


/* ==================================================
ODAYA KATIL
================================================== */

if (
    joinRoomButton
) {

    joinRoomButton.addEventListener(
        "click",
        () => {

            const code =
                roomCodeInput
                    .value
                    .trim()
                    .toUpperCase();


            if (
                code.length !== 6
            ) {

                roomStatus.textContent =
                    "6 haneli oda kodunu gir.";

                return;

            }


            roomStatus.textContent =
                "Odaya bağlanılıyor...";


            socket.emit(
                "join_game_room",
                {
                    room_code:
                        code
                }
            );

        }
    );

}


/* ==================================================
ODAYA GİRİLDİ
================================================== */

socket.on(
    "room_joined",
    data => {

        onlineRoomCode =
            data.room_code;


        onlinePlayerNumber =
            data.player_number;


        onlineGame =
            true;


        createdRoomCode.textContent =
            onlineRoomCode;

        waitingTitle.textContent = "ODA HAZIR";
        roomCodeBlock.classList.remove("hidden");


        waitingMessage.textContent =
            "Oyuna bağlanılıyor...";


        roomStatus.textContent =
            "";


        roomWaitingScreen.classList.remove(
            "hidden"
        );


        console.log(
            "Odaya girdin:",
            onlineRoomCode
        );


        console.log(
            "Oyuncu:",
            onlinePlayerNumber
        );

    }
);


/* ==================================================
OYUN HAZIR
================================================== */

socket.on(
    "game_ready",
    data => {

        onlineGame =
            true;


        onlineRoomCode =
            data.room_code;


        applyOnlineState(
            data.state
        );


        waitingMessage.textContent =
            "Rakip bulundu!";


        console.log(
            "GAME READY:",
            data
        );


        setTimeout(
            () => {

                gameApp.classList.remove(
                    "hidden"
                );

                roomWaitingScreen
                    .classList
                    .add(
                        "hidden"
                    );


                if (
                    multiplayerMenu
                ) {

                    multiplayerMenu
                        .classList
                        .add(
                            "hidden"
                        );

                }


                /* ==========================================
                MEVCUT OYUNDA OYUNCU NUMARASI
                ========================================== */

                if (
                    typeof currentPlayer
                    !== "undefined"
                ) {

                    /*
                    ŞİMDİLİK currentPlayer'a
                    dokunmuyoruz.

                    Bir sonraki aşamada currentPlayer
                    server tarafından yönetilecek.
                    */

                }

            },
            700
        );

    }
);


/* ==================================================
SUNUCU HAMLE SONUCU
================================================== */

socket.on(
    "rematch_status",
    data => {

        if (
            !data.accepted
        ) {

            rematchButton.disabled =
                false;

            rematchButton.textContent =
                "TEKRAR OYNA";

            rematchStatus.textContent =
                data.message
                ||
                "Rövanş isteği kabul edilmedi.";

            return;

        }


        if (
            data.started
        ) {

            return;

        }


        if (
            Number(data.requested_by) === onlinePlayerNumber
        ) {

            rematchButton.disabled =
                true;

            rematchButton.textContent =
                "BEKLENİYOR...";

            rematchStatus.textContent =
                "Rakibin rövanş isteği bekleniyor...";

        } else {

            rematchStatus.textContent =
                "Rakibin rövanş istiyor.";

        }

    }
);


socket.on(
    "rematch_started",
    data => {

        resetRematchVisuals();

        rematchStatus.textContent =
            "";

        onlineGame =
            true;


        onlineMatchStarted =
            false;


        closeGameModal();

        applyOnlineState(
            data.state
        );

    }
);


socket.on(
    "move_result",
    data => {

        checkButton.disabled =
            false;


        if (
            !data.accepted
        ) {

            showError(
                data.message
                ||
                "Hamle kabul edilmedi."
            );

            return;

        }


        if (
            !data.correct
        ) {

            showError(
                data.message
            );


            setTimeout(
                closeGameModal,
                650
            );

            return;

        }


        closeGameModal();

    }
);


socket.on(
    "move_animation",
    data => {

        pendingOnlineAnimation =
            data;

    }
);


socket.on(
    "game_state",
    state => {

        applyOnlineState(
            state
        );

    }
);


socket.on("forfeit_result", data => {
    if (!data.accepted) {
        confirmForfeitButton.disabled = false;
    }
});


/* ==================================================
ODA HATASI
================================================== */

socket.on(
    "room_error",
    data => {

        roomStatus.textContent =
            data.message
            ||
            "Oda hatası.";

    }
);


/* ==================================================
ODADAN ÇIK
================================================== */

if (
    leaveRoomButton
) {

    leaveRoomButton.addEventListener(
        "click",
        () => {

            socket.emit(
                "leave_game_room"
            );
            socket.emit("cancel_random_match");


            onlineRoomCode =
                null;


            onlinePlayerNumber =
                null;


            onlineGame =
                false;


            onlineMatchStarted =
                false;


            roomWaitingScreen
                .classList
                .add(
                    "hidden"
                );


            gameApp.classList.add("hidden");
            multiplayerMenu.classList.remove("hidden");
            showMainLobby();


            roomStatus.textContent =
                "";


            roomCodeInput.value =
                "";

            waitingTitle.textContent = "ODA HAZIR";
            roomCodeBlock.classList.remove("hidden");
            matchmakingPlayers.textContent = "";

        }
    );

}


/* ==================================================
RAKİP AYRILDI
================================================== */

socket.on(
    "opponent_left",
    data => {

        console.log(
            "Rakip ayrıldı"
        );


        onlineGame =
            false;


        onlineMatchStarted =
            false;


        if (
            data.match_finished
            || data.match_was_already_finished
        ) {

            roomWaitingScreen
                .classList
                .add(
                    "hidden"
                );

            return;

        }


        waitingMessage.textContent =
            data.message
            ||
            "Rakip ayrıldı.";


        roomWaitingScreen
            .classList
            .remove(
                "hidden"
            );

    }
);
