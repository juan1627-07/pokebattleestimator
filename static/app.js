// =============================================
// Pokemon Battle Estimator
// Version 0.1.0
// =============================================

const API_BASE = window.location.origin;

let currentBattleId = null;
let currentBattleMode = "single";
let currentBattleState = null;
let pendingSwitchIndex = null;
let pendingMoveName = null;
let pvpRoomId = null;
let pvpPlayerId = null;
let pvpPollTimer = null;
let pvpSecondsRemaining = null;
let pvpCountdownTimer = null;
let pvpHasLockedMove = false;
let pvpOpponentLockedMove = false;
let lastBattleTurn = null;
let lastAnimatedPvpTurn = null;
let battleAnimationQueue = Promise.resolve();
let battleInputLocked = false;
let battleStateVersion = 0;
let pvpPollRequestId = 0;
let latestAppliedPvpPollRequestId = 0;
let audioEnabled = false;
let audioContext = null;
let musicTimer = null;
let musicStep = 0;

const BATTLE_TYPE_COLORS = {
    normal: "#a8a29e", fire: "#f97316", water: "#3b82f6", electric: "#eab308",
    grass: "#22c55e", ice: "#67e8f9", fighting: "#dc2626", poison: "#a855f7",
    ground: "#b45309", flying: "#818cf8", psychic: "#ec4899", bug: "#84cc16",
    rock: "#a16207", ghost: "#7c3aed", dragon: "#4f46e5", dark: "#334155",
    steel: "#64748b", fairy: "#f472b6"
};

const TYPE_CHART = {
    normal: [[], ["rock", "steel"], ["ghost"]],
    fire: [["grass", "ice", "bug", "steel"], ["fire", "water", "rock", "dragon"], []],
    water: [["fire", "ground", "rock"], ["water", "grass", "dragon"], []],
    electric: [["water", "flying"], ["electric", "grass", "dragon"], ["ground"]],
    grass: [["water", "ground", "rock"], ["fire", "grass", "poison", "flying", "bug", "dragon", "steel"], []],
    ice: [["grass", "ground", "flying", "dragon"], ["fire", "water", "ice", "steel"], []],
    fighting: [["normal", "ice", "rock", "dark", "steel"], ["poison", "flying", "psychic", "bug", "fairy"], ["ghost"]],
    poison: [["grass", "fairy"], ["poison", "ground", "rock", "ghost"], ["steel"]],
    ground: [["fire", "electric", "poison", "rock", "steel"], ["grass", "bug"], ["flying"]],
    flying: [["grass", "fighting", "bug"], ["electric", "rock", "steel"], []],
    psychic: [["fighting", "poison"], ["psychic", "steel"], ["dark"]],
    bug: [["grass", "psychic", "dark"], ["fire", "fighting", "poison", "flying", "ghost", "steel", "fairy"], []],
    rock: [["fire", "ice", "flying", "bug"], ["fighting", "ground", "steel"], []],
    ghost: [["psychic", "ghost"], ["dark"], ["normal"]],
    dragon: [["dragon"], ["steel"], ["fairy"]],
    dark: [["psychic", "ghost"], ["fighting", "dark", "fairy"], []],
    steel: [["ice", "rock", "fairy"], ["fire", "water", "electric", "steel"], []],
    fairy: [["fighting", "dragon", "dark"], ["fire", "poison", "steel"], []]
};

const startBattleBtn = document.getElementById("startBattleBtn");
const startTeamBattleBtn = document.getElementById("startTeamBattleBtn");
const battleArena = document.getElementById("battleArena");
const battleError = document.getElementById("battleError");
const switchModal = document.getElementById("switchModal");
const confirmSwitchBtn = document.getElementById("confirmSwitchBtn");
const cancelSwitchBtn = document.getElementById("cancelSwitchBtn");
const confirmMoveBtn = document.getElementById("confirmMoveBtn");
const audioToggle = document.getElementById("audioToggle");
const cpuModeBtn = document.getElementById("cpuModeBtn");
const pvpModeBtn = document.getElementById("pvpModeBtn");
const pvpBattleSetup = document.getElementById("pvpBattleSetup");
const createPvpRoomBtn = document.getElementById("createPvpRoomBtn");
const joinPvpRoomBtn = document.getElementById("joinPvpRoomBtn");
const submitPvpTeamBtn = document.getElementById("submitPvpTeamBtn");
const battleHomeBtn = document.getElementById("battleHomeBtn");

startBattleBtn.addEventListener("click", startBattle);
startTeamBattleBtn.addEventListener("click", startTeamBattle);
cpuModeBtn.addEventListener("click", () => setBattleSetupMode("cpu"));
pvpModeBtn.addEventListener("click", () => setBattleSetupMode("pvp"));
createPvpRoomBtn.addEventListener("click", createPvpRoom);
joinPvpRoomBtn.addEventListener("click", joinPvpRoom);
submitPvpTeamBtn.addEventListener("click", submitPvpTeam);
cancelSwitchBtn.addEventListener("click", closeSwitchDialog);
confirmSwitchBtn.addEventListener("click", () => {
    if (pendingSwitchIndex !== null) switchPokemon(pendingSwitchIndex);
});
confirmMoveBtn.addEventListener("click", () => {
    if (pendingMoveName && !confirmMoveBtn.disabled) playBattleMove(pendingMoveName);
});
audioToggle.addEventListener("click", toggleAudio);
battleHomeBtn.addEventListener("click", () => {
    document.body.classList.remove("battle-active");
    battleArena.classList.add("hidden");
    window.scrollTo({top: 0, behavior: "smooth"});
});

buildPvpTeamInputs();
renderPvpOpponentPreview();

function setBattleSetupMode(mode) {
    const isPvp = mode === "pvp";
    cpuModeBtn.classList.toggle("active", !isPvp);
    pvpModeBtn.classList.toggle("active", isPvp);
    document.getElementById("cpuTeamBattleSetup").classList.toggle("hidden", isPvp);
    document.getElementById("cpuBattleDivider").classList.toggle("hidden", isPvp);
    document.getElementById("cpuSingleBattleSetup").classList.toggle("hidden", isPvp);
    pvpBattleSetup.classList.toggle("hidden", !isPvp);
}

function buildPvpTeamInputs() {
    const container = document.getElementById("pvpTeamInputs");
    const defaults = ["Pikachu", "Charizard", "Blastoise", "Venusaur", "Gengar", "Dragonite"];
    container.replaceChildren();
    defaults.forEach((name, index) => {
        const input = document.createElement("input");
        input.value = name;
        input.placeholder = "Search Pokémon name or ID";
        input.autocomplete = "off";
        input.setAttribute("list", "pokemonSuggestions");
        input.className = "pokemon-autocomplete";
        input.addEventListener("input", () => {
            submitPvpTeamBtn.disabled = getPvpTeamNames().length !== 6 || !pvpRoomId || !pvpPlayerId;
        });
        container.appendChild(input);
    });
}

function getPvpTeamNames() {
    return Array.from(document.querySelectorAll("#pvpTeamInputs input"))
        .map(input => input.value.trim())
        .filter(Boolean);
}

function renderPvpOpponentPreview(ready = false) {
    const container = document.getElementById("pvpOpponentPreview");
    container.replaceChildren();
    for (let index = 0; index < 6; index += 1) {
        const slot = document.createElement("div");
        slot.className = `pvp-shadow-slot ${ready ? "ready" : ""}`;
        slot.textContent = ready ? "Locked" : "?";
        container.appendChild(slot);
    }
}

async function createPvpRoom() {
    createPvpRoomBtn.disabled = true;
    try {
        const response = await fetch(`${API_BASE}/api/pvp/create`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({name: document.getElementById("pvpNameInput").value.trim() || "Player 1"})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Unable to create room.");
        applyPvpRoom(data.room, data.player_id);
        document.getElementById("pvpStatusText").textContent = "Room created. Share the code with your friend.";
    } catch (error) {
        showBattleError(error.message);
    } finally {
        createPvpRoomBtn.disabled = false;
    }
}

async function joinPvpRoom() {
    const roomCode = document.getElementById("pvpRoomInput").value.trim().toUpperCase();
    if (!roomCode) return showBattleError("Enter a room code.");
    joinPvpRoomBtn.disabled = true;
    try {
        const response = await fetch(`${API_BASE}/api/pvp/${roomCode}/join`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({name: document.getElementById("pvpNameInput").value.trim() || "Player 2"})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Unable to join room.");
        applyPvpRoom(data.room, data.player_id);
        document.getElementById("pvpStatusText").textContent = "Joined. Build and lock your team.";
    } catch (error) {
        showBattleError(error.message);
    } finally {
        joinPvpRoomBtn.disabled = false;
    }
}

async function submitPvpTeam() {
    const team = getPvpTeamNames();
    if (team.length !== 6) return showBattleError("Choose exactly six Pokemon.");
    submitPvpTeamBtn.disabled = true;
    submitPvpTeamBtn.textContent = "Locking...";
    try {
        const response = await fetch(`${API_BASE}/api/pvp/${pvpRoomId}/team`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({player_id: pvpPlayerId, team})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Unable to lock team.");
        applyPvpRoom(data.room);
    } catch (error) {
        showBattleError(error.message);
        submitPvpTeamBtn.disabled = false;
    } finally {
        submitPvpTeamBtn.textContent = "Lock Team";
    }
}

function applyPvpRoom(room, playerId = pvpPlayerId) {
    pvpRoomId = room.room_id;
    pvpPlayerId = playerId;
    currentBattleMode = "pvp";
    document.getElementById("pvpRoomCode").textContent = `Room ${room.room_id}`;
    submitPvpTeamBtn.disabled = getPvpTeamNames().length !== 6
        || !pvpPlayerId
        || room.status === "waiting"
        || room.players?.[room.player]?.ready;
    const opponentKey = room.player === "p1" ? "p2" : "p1";
    pvpHasLockedMove = Boolean(room.choices?.you);
    pvpOpponentLockedMove = Boolean(room.choices?.opponent_locked);
    renderPvpOpponentPreview(Boolean(room.players?.[opponentKey]?.ready));
    if (room.status === "battle" && room.battle) {
        currentBattleId = room.room_id;
        battleArena.classList.remove("hidden");
        document.body.classList.add("battle-active");
        const shouldAnimateTurn = room.battle.turn !== lastAnimatedPvpTurn && room.battle.log?.some(entry => entry.move);
        battleInputLocked = shouldAnimateTurn;
        const renderedVersion = renderBattle(room.battle);
        if (shouldAnimateTurn) {
            queueBattleAnimation(room.battle.log, renderedVersion).then(() => {
                battleInputLocked = false;
                if (renderedVersion === battleStateVersion) renderBattle(currentBattleState);
            });
            playTurnSounds(room.battle.log);
            lastAnimatedPvpTurn = room.battle.turn;
        }
        setPvpCountdown(room.seconds_remaining);
    } else {
        document.getElementById("pvpStatusText").textContent =
            room.status === "waiting" ? "Waiting for your friend to join." : "Lock your team. Opponent picks stay hidden.";
    }
    startPvpPolling();
}

function startPvpPolling() {
    if (pvpPollTimer) clearInterval(pvpPollTimer);
    pvpPollTimer = setInterval(refreshPvpRoom, 1600);
}

function setPvpCountdown(seconds) {
    pvpSecondsRemaining = Number.isFinite(seconds) ? seconds : null;
    if (pvpCountdownTimer) clearInterval(pvpCountdownTimer);
    updateTurnBadge();
    if (pvpSecondsRemaining === null) return;
    pvpCountdownTimer = setInterval(() => {
        pvpSecondsRemaining = Math.max(0, pvpSecondsRemaining - 1);
        updateTurnBadge();
    }, 1000);
}

function updateTurnBadge() {
    if (!currentBattleState) return;
    let turnText = currentBattleState.status === "finished"
        ? "Battle over"
        : currentBattleState.status === "awaiting_user_switch"
            ? "Switch Pokemon"
            : currentBattleState.status === "awaiting_opponent_switch"
                ? "Opponent switching"
                : pvpHasLockedMove
                    ? "Waiting for opponent"
                    : "Your turn";
    if (currentBattleMode === "pvp" && pvpSecondsRemaining !== null) {
        if (currentBattleState.status === "awaiting_user_switch") {
            turnText = `Switch Pokemon (${pvpSecondsRemaining}s)`;
        } else if (currentBattleState.status === "awaiting_opponent_switch") {
            turnText = `Opponent switching (${pvpSecondsRemaining}s)`;
        } else if (pvpHasLockedMove) {
            turnText = `Waiting for opponent (${pvpSecondsRemaining}s)`;
        } else {
            turnText = `Your turn (${pvpSecondsRemaining}s)`;
        }
    }
    document.getElementById("battleTurn").textContent = turnText;
}

async function refreshPvpRoom() {
    if (!pvpRoomId || !pvpPlayerId) return;
    const requestedRoomId = pvpRoomId;
    const requestId = ++pvpPollRequestId;
    try {
        const response = await fetch(`${API_BASE}/api/pvp/${requestedRoomId}?player_id=${encodeURIComponent(pvpPlayerId)}`);
        const data = await response.json();
        if (requestedRoomId !== pvpRoomId) return;
        if (response.ok && requestId >= latestAppliedPvpPollRequestId) {
            latestAppliedPvpPollRequestId = requestId;
            applyPvpRoom(data.room);
        }
    } catch (error) {
        console.debug("PVP polling unavailable", error);
    }
}

async function startTeamBattle() {
    startBattleAudio();
    pvpHasLockedMove = false;
    pvpOpponentLockedMove = false;
    lastAnimatedPvpTurn = null;
    startTeamBattleBtn.disabled = true;
    startTeamBattleBtn.textContent = "Building two teams...";
    try {
        const response = await fetch(`${API_BASE}/api/team-battle/start`, {method: "POST"});
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Unable to create teams.");
        currentBattleId = data.battle_id;
        currentBattleMode = "team";
        battleError.classList.add("hidden");
        battleArena.classList.remove("hidden");
        document.body.classList.add("battle-active");
        renderBattle(data.battle);
        playPokemonCry(data.battle.user);
    } catch (error) {
        showBattleError(error.message);
    } finally {
        startTeamBattleBtn.disabled = false;
        startTeamBattleBtn.textContent = "Generate Teams & Battle";
    }
}

async function startBattle() {
    startBattleAudio();
    pvpHasLockedMove = false;
    pvpOpponentLockedMove = false;
    lastAnimatedPvpTurn = null;
    const user = document.getElementById("battleUserInput").value.trim();
    const opponent = document.getElementById("battleOpponentInput").value.trim();
    if (!user || !opponent) return showBattleError("Choose two PokÃ©mon.");
    setBattleBusy(true, "Loading battle...");
    try {
        const response = await fetch(`${API_BASE}/api/battle/start`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({user, opponent})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Unable to start battle.");
        currentBattleId = data.battle_id;
        currentBattleMode = "single";
        battleError.classList.add("hidden");
        battleArena.classList.remove("hidden");
        document.body.classList.add("battle-active");
        renderBattle(data.battle);
        playPokemonCry(data.battle.user);
    } catch (error) {
        showBattleError(error.message);
    } finally {
        setBattleBusy(false, "Start Battle");
    }
}

async function playBattleMove(move) {
    if (!currentBattleId) return;
    if (currentBattleState?.status === "awaiting_user_switch") {
        return showBattleError("Choose a healthy replacement before selecting a move.");
    }
    battleInputLocked = true;
    setMoveButtonsDisabled(true);
    confirmMoveBtn.disabled = true;
    confirmMoveBtn.textContent = `Using ${prettyName(move)}...`;
    try {
        const route = currentBattleMode === "pvp"
            ? `${API_BASE}/api/pvp/${currentBattleId}/turn`
            : currentBattleMode === "team"
                ? `${API_BASE}/api/team-battle/${currentBattleId}/turn`
                : `${API_BASE}/api/battle/${currentBattleId}/turn`;
        const body = currentBattleMode === "pvp"
            ? {player_id: pvpPlayerId, move}
            : {move};
        const response = await fetch(route, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Turn failed.");
        pendingMoveName = null;
        if (currentBattleMode === "pvp") {
            battleInputLocked = false;
            applyPvpRoom(data.room);
        } else {
            const renderedVersion = renderBattle(data.battle);
            await queueBattleAnimation(data.battle.log, renderedVersion);
            playTurnSounds(data.battle.log);
            battleInputLocked = false;
            if (renderedVersion === battleStateVersion) renderBattle(currentBattleState);
        }
    } catch (error) {
        showBattleError(error.message);
        battleInputLocked = false;
        setMoveButtonsDisabled(false);
        renderBattle(currentBattleState);
    }
}

async function switchPokemon(index) {
    if (!currentBattleId || !["team", "pvp"].includes(currentBattleMode)) return;
    battleInputLocked = true;
    setMoveButtonsDisabled(true);
    try {
        const route = currentBattleMode === "pvp"
            ? `${API_BASE}/api/pvp/${currentBattleId}/turn`
            : `${API_BASE}/api/team-battle/${currentBattleId}/turn`;
        const body = currentBattleMode === "pvp"
            ? {player_id: pvpPlayerId, switch_index: index}
            : {switch_index: index};
        const response = await fetch(route, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Switch failed.");
        closeSwitchDialog();
        if (currentBattleMode === "pvp") {
            battleInputLocked = false;
            applyPvpRoom(data.room);
        } else {
            const renderedVersion = renderBattle(data.battle);
            await queueBattleAnimation(data.battle.log, renderedVersion);
            playPokemonCry(data.battle.user);
            battleInputLocked = false;
            if (renderedVersion === battleStateVersion) renderBattle(currentBattleState);
        }
    } catch (error) {
        showBattleError(error.message);
        battleInputLocked = false;
        setMoveButtonsDisabled(false);
        renderBattle(currentBattleState);
    }
}

function renderBattle(state) {
    battleStateVersion += 1;
    const renderedVersion = battleStateVersion;
    const previousPendingMove = pendingMoveName;
    const sameTurn = lastBattleTurn === state.turn;
    const canKeepPendingMove = state.status === "active"
        && sameTurn
        && state.user.moves.some(move => move.name === previousPendingMove);
    currentBattleState = state;
    lastBattleTurn = state.turn;
    pendingMoveName = canKeepPendingMove ? previousPendingMove : null;
    const inputLocked = battleInputLocked || (currentBattleMode === "pvp" && pvpHasLockedMove);
    confirmMoveBtn.disabled = !pendingMoveName || state.status !== "active" || inputLocked;
    confirmMoveBtn.textContent = pendingMoveName ? `Use ${prettyName(pendingMoveName)}` : "Select a move";
    renderBattleSide("User", state.user);
    renderBattleSide("Opponent", state.opponent);
    renderTeamRosters(state);
    updateTurnBadge();
    document.getElementById("battlePrompt").textContent = state.status === "awaiting_user_switch"
        ? "Choose a healthy PokÃ©mon from your party."
        : state.status === "awaiting_opponent_switch"
            ? "Waiting for your opponent to send out a replacement."
            : state.status === "active" ? `What will ${state.user.name} do?` : "The battle is over.";

    const moves = document.getElementById("battleMoves");
    moves.replaceChildren();
    state.user.moves.forEach(move => {
        const button = document.createElement("button");
        button.className = `move-button move-${move.type}`;
        button.type = "button";
        button.style.setProperty("--move-color", BATTLE_TYPE_COLORS[move.type] || "#64748b");
        const movePower = move.power || "Status";
        const movePp = move.current_pp ?? move.pp ?? "--";
        const maxPp = move.pp ?? "--";
        const noPp = Number.isFinite(move.current_pp) && move.current_pp <= 0;
        const recharging = Boolean(state.user.recharging);
        const disabledReason = noPp ? "No PP" : recharging ? "Recharging" : "";
        button.innerHTML = `
            <strong>${prettyName(move.name)}</strong>
            <span>${move.type.toUpperCase()} Â· ${movePower} Â· PP ${movePp}/${maxPp}${disabledReason ? ` Â· ${disabledReason}` : ""}</span>
        `;
        button.disabled = state.status !== "active" || inputLocked || noPp || recharging;
        if (move.name === pendingMoveName) button.classList.add("selected");
        button.addEventListener("click", () => selectBattleMove(move.name, button));
        moves.appendChild(button);
    });

    const log = document.getElementById("battleLog");
    log.replaceChildren();
    const shownLog = state.history && state.history.length ? state.history : state.log;
    const entries = shownLog.length ? shownLog : [{message: "Choose your opening move."}];
    entries.forEach(entry => {
        const row = document.createElement("p");
        row.className = entry.actor ? `log-${entry.actor}` : "";
        row.textContent = entry.message;
        log.appendChild(row);
    });
    log.scrollTop = log.scrollHeight;
    renderBattleResult(state);
    return renderedVersion;
}

function renderBattleResult(state) {
    const result = document.getElementById("battleResult");
    result.classList.remove("ko-flash", "win-flash", "lose-flash");
    if (state.status === "finished") {
        if (state.winner === "tie") {
            result.textContent = "Draw!";
            return;
        }
        const userWon = state.winner === "user";
        result.textContent = userWon ? "You win!" : "You lost!";
        result.classList.add(userWon ? "win-flash" : "lose-flash");
        return;
    }
    if (state.status === "awaiting_user_switch" || state.status === "awaiting_opponent_switch") {
        result.textContent = "K.O.";
        result.classList.add("ko-flash");
        return;
    }
    result.textContent = "";
}

function selectBattleMove(moveName, button) {
    if (!currentBattleState || currentBattleState.status !== "active") return;
    if (battleInputLocked || (currentBattleMode === "pvp" && pvpHasLockedMove) || button.disabled) return;
    pendingMoveName = moveName;
    document.querySelectorAll("#battleMoves .move-button").forEach(element => element.classList.remove("selected"));
    button.classList.add("selected");
    confirmMoveBtn.disabled = false;
    confirmMoveBtn.textContent = `Use ${prettyName(moveName)}`;
    document.getElementById("battlePrompt").textContent =
        `Use ${prettyName(moveName)}?`;
}

function renderTeamRosters(state) {
    const overview = document.getElementById("teamOverview");
    if (!["team", "pvp"].includes(state.mode)) {
        overview.classList.add("hidden");
        return;
    }
    overview.classList.remove("hidden");
    renderRoster("userTeamRoster", state.user_team, state.user_active, true, state.status);
    const revealed = new Set(state.revealed?.opponent || [state.opponent_active]);
    revealed.add(state.opponent_active);
    const opponentTeam = state.opponent_team.map((member, index) => {
        if (member.hidden || member.current_hp <= 0 || revealed.has(index)) return member;
        return {hidden: true, name: "Hidden", current_hp: 1, max_hp: 1};
    });
    renderRoster("opponentTeamRoster", opponentTeam, state.opponent_active, false, state.status);
}

function renderRoster(containerId, team, activeIndex, interactive, battleStatus) {
    const container = document.getElementById(containerId);
    container.replaceChildren();
    team.forEach((member, index) => {
        const element = document.createElement(interactive ? "button" : "div");
        const hidden = !interactive && member.hidden;
        const fainted = member.current_hp <= 0;
        element.className = `team-member ${interactive ? "user-member" : ""} ${index === activeIndex ? "active" : ""} ${fainted ? "fainted" : ""} ${hidden ? "hidden-member" : ""}`;
        if (interactive) {
            element.type = "button";
            element.disabled = fainted
                || index === activeIndex
                || battleStatus === "finished"
                || battleStatus === "awaiting_opponent_switch"
                || battleInputLocked
                || (currentBattleMode === "pvp" && pvpHasLockedMove);
            element.addEventListener("click", () => openSwitchDialog(index, member));
        }
        const image = document.createElement(hidden ? "div" : "img");
        if (hidden) {
            image.className = "hidden-slot-mark";
            image.textContent = "?";
            image.setAttribute("aria-label", "Hidden opponent Pokemon");
        } else {
            image.src = member.front_image || member.image || "";
            image.alt = member.name;
        }
        const info = document.createElement("span");
        if (hidden) {
            info.innerHTML = "<strong>Hidden</strong><small>Not revealed</small>";
        } else {
            const hpPercent = Math.max(0, Math.round(member.current_hp / member.max_hp * 100));
            const condition = fainted ? "Fainted" : `${member.tier || "Unranked"} Â· ${hpPercent}% HP`;
            info.innerHTML = `<strong>${member.name}</strong><small>${condition}</small>`;
        }
        element.append(image, info);
        container.appendChild(element);
    });
}

function openSwitchDialog(index, member) {
    pendingSwitchIndex = index;
    document.getElementById("switchPokemonImage").src = member.front_image || member.image || "";
    document.getElementById("switchModalMessage").textContent =
        currentBattleState?.status === "awaiting_user_switch"
            ? `Send out ${member.name} to continue the battle.`
            : `Send out ${member.name}? This uses your action for the turn.`;
    switchModal.classList.remove("hidden");
}

function closeSwitchDialog() {
    pendingSwitchIndex = null;
    switchModal.classList.add("hidden");
}

function renderBattleSide(prefix, side) {
    const image = side.front_image || side.image;
    const sprite = document.getElementById(`battle${prefix}Image`);
    const nextImage = image || "";
    if (sprite.dataset.src !== nextImage) {
        sprite.dataset.src = nextImage;
        sprite.style.visibility = nextImage ? "hidden" : "visible";
        sprite.onload = () => {
            if (sprite.dataset.src === nextImage) sprite.style.visibility = "visible";
        };
        sprite.onerror = () => {
            if (sprite.dataset.src === nextImage) sprite.style.visibility = "visible";
        };
        sprite.src = nextImage;
    }
    sprite.alt = side.name;
    document.getElementById(`battle${prefix}Name`).textContent = side.name;
    document.getElementById(`battle${prefix}Details`).textContent =
        `${side.tier || "Unranked"} Tier  â€¢  ${side.ability || "No ability"}  â€¢  ${side.item || "No item"}`;
    document.getElementById(`battle${prefix}Hp`).textContent = `${side.current_hp} / ${side.max_hp} HP`;
    const percent = Math.max(0, side.current_hp / side.max_hp * 100);
    const fighter = document.getElementById(`${prefix === "User" ? "user" : "opponent"}Fighter`);
    fighter.classList.toggle("critical-hp", prefix === "User" && side.current_hp > 0 && side.current_hp < 20);
    fighter.classList.toggle("fighter-faint", side.current_hp <= 0);
    const bar = document.getElementById(`battle${prefix}HpBar`);
    bar.style.width = `${percent}%`;
    bar.className = `hp-fill ${percent <= 25 ? "hp-low" : percent <= 50 ? "hp-mid" : ""}`;
    const statusPill = document.getElementById(`battle${prefix}Status`);
    const lowLife = side.current_hp > 0 && percent < 20;
    const condition = lowLife ? "Low life" : "Healthy";
    statusPill.textContent = side.current_hp <= 0
        ? "Fainted"
        : side.status
            ? `${prettyName(side.status)} - ${condition}`
            : condition;
    statusPill.classList.toggle("status-low", lowLife);
    statusPill.classList.toggle("status-fainted", side.current_hp <= 0);
}

function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function queueBattleAnimation(log, expectedVersion = battleStateVersion) {
    battleAnimationQueue = battleAnimationQueue
        .catch(() => {})
        .then(() => animateBattleTurn(log, expectedVersion));
    return battleAnimationQueue;
}

async function animateBattleTurn(log, expectedVersion) {
    const actions = log.filter(entry => entry.move || entry.damage || entry.healing || entry.status || entry.hazard || entry.switch !== undefined);
    if (!actions.length) return;
    const stage = document.getElementById("battleStage");
    for (const action of actions) {
        if (expectedVersion !== battleStateVersion) return;
        clearBattleAnimationClasses();
        const actor = document.getElementById(action.actor === "user" ? "userFighter" : "opponentFighter");
        const target = document.getElementById(action.actor === "user" ? "opponentFighter" : "userFighter");
        void stage.offsetWidth;
        if (action.move && !action.damage && !action.healing && !action.status && !action.hazard) {
            actor.classList.add("fighter-attacking");
            await wait(520);
        } else if (action.damage) {
            target.classList.add("fighter-hit");
            stage.classList.add("battlefield-shake");
            await wait(520);
        } else if (action.healing || action.status || action.hazard || action.switch !== undefined || action.move) {
            actor.classList.add("fighter-buff");
            await wait(620);
        }
        clearBattleAnimationClasses();
    }
    if (expectedVersion !== battleStateVersion) return;
    if (currentBattleState?.user?.current_hp <= 0) {
        document.getElementById("userFighter").classList.add("fighter-faint");
        document.getElementById("battleResult").textContent = "K.O.";
        document.getElementById("battleResult").classList.add("ko-flash");
        await wait(520);
    }
    if (currentBattleState?.opponent?.current_hp <= 0) {
        document.getElementById("opponentFighter").classList.add("fighter-faint");
        document.getElementById("battleResult").textContent = "K.O.";
        document.getElementById("battleResult").classList.add("ko-flash");
        await wait(520);
    }
}

function clearBattleAnimationClasses() {
    const stage = document.getElementById("battleStage");
    stage.classList.remove("battlefield-shake");
    document.querySelectorAll(".battle-fighter").forEach(fighter => {
        fighter.classList.remove("fighter-attacking", "fighter-hit", "fighter-buff");
    });
}

function prettyName(value) {
    return String(value).split("-").map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

function ensureAudioContext() {
    if (!audioContext) audioContext = new (window.AudioContext || window.webkitAudioContext)();
    if (audioContext.state === "suspended") audioContext.resume();
    return audioContext;
}

function synthNote(frequency, duration = 0.12, type = "square", volume = 0.025) {
    if (!audioEnabled) return;
    const context = ensureAudioContext();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = type;
    oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(volume, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + duration);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + duration);
}

function startBattleAudio() {
    if (!audioEnabled) return;
    ensureAudioContext();
    if (musicTimer) return;
    const melody = [220, 277, 330, 440, 330, 294, 247, 330];
    musicTimer = setInterval(() => {
        synthNote(melody[musicStep % melody.length], 0.14, "square", 0.012);
        if (musicStep % 2 === 0) synthNote(melody[musicStep % melody.length] / 2, 0.2, "triangle", 0.01);
        musicStep += 1;
    }, 230);
}

function toggleAudio() {
    audioEnabled = !audioEnabled;
    audioToggle.setAttribute("aria-pressed", String(audioEnabled));
    audioToggle.textContent = audioEnabled ? "ðŸ”Š Audio On" : "ðŸ”‡ Audio Off";
    if (audioEnabled) {
        startBattleAudio();
        if (currentBattleState) playPokemonCry(currentBattleState.user);
    } else if (musicTimer) {
        clearInterval(musicTimer);
        musicTimer = null;
    }
}

function playPokemonCry(side) {
    if (!audioEnabled || !side?.cry) return;
    const cry = new Audio(side.cry);
    cry.volume = 0.22;
    cry.play().catch(() => {});
}

function playTurnSounds(log) {
    if (!audioEnabled) return;
    const action = log.find(entry => entry.move);
    if (action) synthNote(action.damage ? 150 : 520, action.damage ? 0.18 : 0.12, action.damage ? "sawtooth" : "sine", 0.035);
    if (log.some(entry => entry.switch !== undefined) && currentBattleState) {
        playPokemonCry(currentBattleState.opponent);
    }
}

function setBattleBusy(disabled, text) {
    startBattleBtn.disabled = disabled;
    startBattleBtn.textContent = text;
}

function setMoveButtonsDisabled(disabled) {
    document.querySelectorAll("#battleMoves button, .user-member").forEach(button => button.disabled = disabled);
    confirmMoveBtn.disabled = disabled || !pendingMoveName;
    if (!disabled && currentBattleState) renderTeamRosters(currentBattleState);
}

function showBattleError(message) {
    battleError.textContent = message;
    battleError.classList.remove("hidden");
}


const pokemonTier =
document.getElementById("pokemonTier");

const battleScore =
document.getElementById("battleScore");

const recommendedMoves =
document.getElementById("recommendedMoves");



const pokemonGeneration = document.getElementById("pokemonGeneration");
const pokemonRegion = document.getElementById("pokemonRegion");
const pokemonRole = document.getElementById("pokemonRole");

const bestNature = document.getElementById("bestNature");
const bestAbility = document.getElementById("bestAbility");
const bestItem = document.getElementById("bestItem");

// DOM Elements
const searchBtn = document.getElementById("searchBtn");
const pokemonInput = document.getElementById("pokemonInput");

const pokemonImage = document.getElementById("pokemonImage");
const imagePlaceholder = document.getElementById("imagePlaceholder");

const pokemonName = document.getElementById("pokemonName");
const pokemonTypes = document.getElementById("pokemonTypes");

const statsContainer = document.getElementById("statsContainer");
const abilityContainer = document.getElementById("abilityContainer");

const moveContainer = document.getElementById("moveContainer");
const moveCount = document.getElementById("moveCount");
const pokemonNumber = document.getElementById("pokemonNumber");


// =============================================
// Search Events
// =============================================

searchBtn.addEventListener("click", () => {

    searchPokemon();

});

pokemonInput.addEventListener("keypress", (e) => {

    if (e.key === "Enter") {

        searchPokemon();

    }

});

let autocompleteTimer = null;
document.querySelectorAll(".pokemon-autocomplete, #pokemonInput").forEach(input => {
    input.addEventListener("input", () => {
        clearTimeout(autocompleteTimer);
        const query = input.value.trim();
        if (query.length < 3 && !/^\d+$/.test(query)) return;
        autocompleteTimer = setTimeout(() => loadPokemonSuggestions(query), 180);
    });
});

async function loadPokemonSuggestions(query) {
    try {
        const response = await fetch(`${API_BASE}/api/pokemon-names?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        const list = document.getElementById("pokemonSuggestions");
        list.replaceChildren();
        (data.names || []).forEach(name => {
            const option = document.createElement("option");
            option.value = name;
            list.appendChild(option);
        });
    } catch (error) {
        console.debug("Autocomplete unavailable", error);
    }
}


// =============================================
// Main Search
// =============================================

async function searchPokemon() {

    const name = pokemonInput.value.trim();

    if (!name) return;

    showLoading();

    try {

        const response = await fetch(

            `${API_BASE}/api/pokemon/${encodeURIComponent(name)}`

        );

        if (!response.ok) {

            const error = await response.json();

            showError(error.message);

            return;

        }

        const data = await response.json();

        renderPokemon(data.pokemon);

    }

    catch (err) {

        console.error(err);

        showError("Cannot connect to backend.");

    }

}


// =============================================
// Render Everything
// =============================================

function renderPokemon(pokemon){

    pokemonImage.src =

        pokemon.images.official_artwork ||

        pokemon.images.pokemon_home ||

        pokemon.images.front_default;

    pokemonImage.classList.remove("hidden");

    imagePlaceholder.classList.add("hidden");

    pokemonName.textContent = pokemon.name;

    pokemonGeneration.textContent = pokemon.metadata.generation;

    pokemonRegion.textContent = pokemon.metadata.region;

    bestNature.textContent =
    pokemon.battle?.recommended_nature?.name || "Analyzing...";

    bestAbility.textContent =
    pokemon.battle?.recommended_ability?.name || "Analyzing...";

    bestItem.textContent =
    pokemon.battle?.recommended_item?.name || "Analyzing...";

    pokemonRole.textContent =
    pokemon.battle.role || "-";

pokemonTier.textContent =
    pokemon.battle.tier || "Generated";
pokemonTier.style.color = pokemon.battle?.tier_analysis?.color || "#cbd5e1";

document.getElementById("movesSource").textContent = pokemon.battle?.moves_source
    ? `${pokemon.battle.moves_source} Â· ${pokemon.battle.smogon_month || "current"}`
    : "Generated recommendation";

battleScore.textContent =
    pokemon.battle.competitive_score ??
    "--";

    pokemonRole.textContent =
    pokemon.battle?.role || "-";

    pokemonNumber.textContent = `PokÃ©dex #${pokemon.metadata.pokedex_number}`;

    renderTypes(pokemon.types);

    renderStats(pokemon.stats);

    renderAbilities(pokemon.abilities);

    renderMoves(pokemon.moves);

    renderRecommendedMoves(pokemon.battle.recommended_moves);

    renderCounters(pokemon.name, pokemon.battle.counters || []);

}

function renderCounters(targetName, counters) {
    const section = document.getElementById("counterSection");
    const container = document.getElementById("counterContainer");
    document.getElementById("counterTarget").textContent = targetName;
    container.replaceChildren();
    counters.forEach(counter => {
        const card = document.createElement("article");
        card.className = "counter-card";
        const image = document.createElement("img");
        image.src = counter.image;
        image.alt = counter.name;
        const content = document.createElement("div");
        content.innerHTML = `<strong>${counter.name}</strong><span>${counter.tier} Â· ${counter.reason}</span>`;
        card.append(image, content);
        container.appendChild(card);
    });
    section.classList.toggle("hidden", counters.length === 0);
}


// =============================================
// Types
// =============================================

function renderTypes(types){

    pokemonTypes.innerHTML = "";

    types.forEach(type=>{

        pokemonTypes.innerHTML +=

        `
        <span
            class="px-3 py-1 rounded-full text-sm font-bold text-white"
            style="background:${type.color}"
        >
            ${type.name.toUpperCase()}
        </span>
        `;

    });

}


// =============================================
// Stats
// =============================================

function renderStats(stats){

    statsContainer.innerHTML = "";

    stats.forEach(stat=>{

        const percent =

            Math.min((stat.value / 255) * 100,100);

        statsContainer.innerHTML +=

        `
        <div>

            <div class="flex justify-between text-sm mb-1">

                <span>${stat.name}</span>

                <span>${stat.value}</span>

            </div>

            <div class="bg-slate-700 rounded-full h-3">

                <div

                    class="bg-green-500 h-3 rounded-full transition-all duration-700"

                    style="width:${percent}%">

                </div>

            </div>

        </div>
        `;

    });

}


// =============================================
// Abilities
// =============================================

function renderAbilities(abilities){

    abilityContainer.innerHTML = "";

    abilities.forEach(ability=>{

        abilityContainer.innerHTML +=

        `
        <div class="bg-slate-800 rounded-lg p-3">

            <div class="font-bold">

                ${ability.name}

            </div>

            <div class="text-sm text-slate-400">
                ${ability.type}
                ${ability.recommended ? " â­ Recommended" : ""}
            </div>

        </div>
        `;

    });

}


// =============================================
// Moves
// =============================================

function renderMoves(moves){

    moveContainer.innerHTML = "";

    moveCount.textContent =

        `${moves.length} Moves`;

    moves.slice(0,40).forEach(move=>{

        moveContainer.innerHTML +=

        `
        <div class="bg-slate-800 rounded-lg p-2 text-center text-sm">

            ${move.name}

        </div>
        `;

    });

}


// =============================================
// Loading
// =============================================

function showLoading(){

    pokemonName.textContent = "Loading...";

    pokemonTypes.innerHTML = "";

    statsContainer.innerHTML = "";

    abilityContainer.innerHTML = "";

    moveContainer.innerHTML = "";

    moveCount.textContent = "";

}

function renderRecommendedMoves(moves){

    recommendedMoves.innerHTML = "";

    if(!moves || moves.length===0){

        recommendedMoves.innerHTML=

        `
        <div class="text-slate-500">

            No competitive moves generated.

        </div>
        `;

        return;

    }

    moves.forEach(move=>{

        recommendedMoves.innerHTML +=

        `
        <div
        class="bg-slate-800 rounded-lg px-3 py-2">

            ${prettyName(move)}

        </div>
        `;

    });

}


// =============================================
// Error
// =============================================

function showError(message){

    pokemonImage.classList.add("hidden");

    imagePlaceholder.classList.remove("hidden");

    imagePlaceholder.textContent = "âŒ";

    pokemonName.textContent = message;

    pokemonTypes.innerHTML = "";

    statsContainer.innerHTML = "";

    abilityContainer.innerHTML = "";

    moveContainer.innerHTML = "";

    moveCount.textContent = "";

}
