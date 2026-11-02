/**
 * app.js — Punto de entrada del frontend modularizado
 */

import { SessionClient } from "./js/core/session.js";
import { AuthClient } from "./js/core/auth.js";
import { showScreen, setConnectionStatus, logEvent, renderPlayers } from "./js/core/ui.js";
import { YugiohDraftModeUI } from "./modes/cube_draft_yugioh/yugioh_draft.js";
import { SubastaPokemonModeUI } from "./modes/subasta_pokemon/subasta_pokemon.js";

// Registro de controladores de UI para los modos de juego
const modeUIRegistry = {
  cube_draft_yugioh: new YugiohDraftModeUI(),
  subasta_pokemon: new SubastaPokemonModeUI(),
};

// Cliente de sesión
const sessionClient = new SessionClient();
const authClient = new AuthClient();

// Estado local de la aplicación
let isReady = false;
let isHost = false;
let currentModeKey = null;
let currentModeUI = null;

// Elementos del DOM generales
const btnStartGame = document.getElementById("btn-start-game");
const btnReady = document.getElementById("btn-ready");
const btnLeave = document.getElementById("btn-leave");
const btnForceCloseRoom = document.getElementById("btn-force-close-room");
const btnFinishRoom = document.getElementById("btn-finish-room");
const appUserHeader = document.getElementById("app-user-header");
const profileMenuToggle = document.getElementById("profile-menu-toggle");
const profileMenu = document.getElementById("profile-menu");
const inviteRoomMenu = document.getElementById("invite-room-menu");
const modeGrid = document.getElementById("mode-grid");
const modeConfig = document.getElementById("mode-config");
const btnConfigure = document.getElementById("btn-configure-mode");
const btnStartDraft = document.getElementById("btn-start-draft");
const btnBackToLobby = document.getElementById("btn-back-to-lobby");
const btnBackDraft = document.getElementById("btn-back-to-lobby-draft");
const modalClose = document.getElementById("modal-close");
const modalOverlay = document.getElementById("card-detail-modal");
const btnTogglePicked = document.getElementById("btn-toggle-picked-cards");
const pickedList = document.getElementById("draft-picked-list");
const createRoomForm = document.getElementById("create-room-form");

// ── Al cargar la página ───────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", async () => {
  window.history.replaceState({}, "", window.location.pathname);
  const profile = await authClient.restore();
  sessionClient.setAccessToken(authClient.accessToken, async () => {
    const refreshed = await authClient.restore();
    sessionClient.setAccessToken(authClient.accessToken);
    return refreshed;
  });
  if (profile) {
    renderAuthProfile(profile);
    if (!profile.must_change_password) await refreshRoomDashboard();
  }
});

function renderAuthProfile(profile) {
  closeProfileMenu();
  document.getElementById("auth-login-panel").classList.add("hidden");
  document.getElementById("auth-change-password-panel").classList.add("hidden");
  document.getElementById("auth-account-panel").classList.add("hidden");
  appUserHeader.classList.add("hidden");
  document.getElementById("auth-profile-name").textContent = profile.display_name;
  document.getElementById("auth-profile-username").textContent = `@${profile.username} · ${profile.email}`;
  document.getElementById("auth-profile-role").textContent = profile.is_admin ? "Admin" : "Jugador";
  const avatarIndex = Number((profile.avatar_key || "avatar_01").slice(-2)) - 1;
  document.getElementById("auth-profile-avatar").textContent = ["🎴", "🐉", "⭐", "🛡️", "🔥", "🌙", "⚡", "💎"][avatarIndex] || "🎴";

  if (profile.must_change_password) {
    document.getElementById("auth-change-password-panel").classList.remove("hidden");
    return;
  }

  appUserHeader.classList.remove("hidden");
  document.getElementById("auth-account-panel").classList.remove("hidden");
  document.getElementById("admin-create-account-panel").classList.toggle("hidden", !profile.is_admin);
  createRoomForm.classList.toggle("hidden", !profile.is_admin);
}

function showLoginPanel() {
  closeProfileMenu();
  document.getElementById("auth-login-panel").classList.remove("hidden");
  document.getElementById("auth-change-password-panel").classList.add("hidden");
  document.getElementById("auth-account-panel").classList.add("hidden");
  appUserHeader.classList.add("hidden");
}

document.getElementById("auth-login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = document.getElementById("auth-login-error");
  errorEl.textContent = "";
  try {
    const profile = await authClient.login(
      document.getElementById("auth-login-email").value,
      document.getElementById("auth-login-password").value,
    );
    sessionClient.setAccessToken(authClient.accessToken, async () => {
      const refreshed = await authClient.restore();
      sessionClient.setAccessToken(authClient.accessToken);
      return refreshed;
    });
    renderAuthProfile(profile);
    await refreshRoomDashboard();
  } catch (error) {
    errorEl.textContent = error.message;
  }
});

document.getElementById("auth-change-password-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = document.getElementById("auth-change-password-error");
  const password = document.getElementById("auth-new-password").value;
  const confirmation = document.getElementById("auth-new-password-confirm").value;
  errorEl.textContent = "";
  if (password !== confirmation) {
    errorEl.textContent = "Las contraseñas no coinciden.";
    return;
  }
  try {
    await authClient.changeTemporaryPassword(password);
    document.getElementById("auth-change-password-form").reset();
    renderAuthProfile(authClient.profile);
    await refreshRoomDashboard();
  } catch (error) {
    errorEl.textContent = error.message;
  }
});

document.getElementById("admin-create-account-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const messageEl = document.getElementById("admin-create-account-message");
  messageEl.textContent = "";
  try {
    const created = await authClient.createAccount({
      email: document.getElementById("admin-account-email").value,
      username: document.getElementById("admin-account-username").value,
      display_name: document.getElementById("admin-account-display-name").value,
      avatar_key: document.getElementById("admin-account-avatar").value,
      is_admin: document.getElementById("admin-account-role").value === "admin",
      temporary_password: document.getElementById("admin-account-temporary-password").value,
    });
    form.reset();
    messageEl.textContent = `Cuenta de ${created.is_admin ? "admin global" : "usuario común"} creada para @${created.username}. Entrégale el email y la contraseña temporal por un canal privado.`;
  } catch (error) {
    messageEl.textContent = error.message;
  }
});

function logoutToLogin() {
  sessionClient.disconnect();
  resetCurrentRoomUi();
  sessionClient.currentSessionId = null;
  sessionClient.currentUsername = null;
  authClient.logout();
  sessionClient.setAccessToken(null, null);
  showLoginPanel();
}

document.getElementById("btn-auth-logout").addEventListener("click", logoutToLogin);
document.getElementById("btn-auth-logout-forced").addEventListener("click", logoutToLogin);

profileMenuToggle.addEventListener("click", () => {
  const opening = profileMenu.classList.contains("hidden");
  profileMenu.classList.toggle("hidden", !opening);
  profileMenuToggle.setAttribute("aria-expanded", String(opening));
});

function closeProfileMenu() {
  profileMenu.classList.add("hidden");
  profileMenuToggle.setAttribute("aria-expanded", "false");
}

document.addEventListener("click", (event) => {
  if (!appUserHeader.contains(event.target)) closeProfileMenu();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeProfileMenu();
});

createRoomForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const error = document.getElementById("rooms-error");
  error.textContent = "";
  let createdRoom = null;
  try {
    const roomName = document.getElementById("create-room-name").value.trim();
    createdRoom = await sessionClient.createSession(roomName);
    form.reset();
    await openRoom(createdRoom.session_id);
  } catch (e) {
    error.textContent = createdRoom
      ? `La sala “${createdRoom.name}” se creó, pero no se pudo abrir: ${e.message}`
      : e.message;
    if (createdRoom) await refreshRoomDashboard();
  }
});
document.getElementById("btn-refresh-rooms").addEventListener("click", refreshRoomDashboard);
btnForceCloseRoom.addEventListener("click", async () => {
  if (!sessionClient.currentSessionId) return;
  try {
    closeProfileMenu();
    await sessionClient.closeRoom(sessionClient.currentSessionId, true);
    sessionClient.disconnect();
    inviteRoomMenu.open = false;
    inviteRoomMenu.classList.add("hidden");
    btnForceCloseRoom.classList.add("hidden");
    btnFinishRoom.classList.add("hidden");
    window.history.replaceState({}, "", window.location.pathname);
    showScreen("home");
    await refreshRoomDashboard();
  } catch (error) { logEvent(`❌ ${error.message}`); }
});
btnFinishRoom.addEventListener("click", async () => {
  if (!sessionClient.currentSessionId) return;
  try {
    closeProfileMenu();
    await sessionClient.closeRoom(sessionClient.currentSessionId, false);
  } catch (error) { logEvent(`❌ ${error.message}`); }
});
document.getElementById("invite-room-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("invite-room-username");
  const username = input.value.trim();
  const message = document.getElementById("invite-room-message");
  message.textContent = "";
  try {
    await sessionClient.invite(sessionClient.currentSessionId, username);
    message.textContent = `Invitación enviada a @${username}.`;
    input.value = "";
  } catch (error) { message.textContent = error.message; }
});
document.getElementById("room-invitations").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-invite-action]");
  if (!button) return;
  try {
    const result = await sessionClient.respondToInvite(button.dataset.inviteId, button.dataset.inviteAction === "accept");
    if (result.session_id) await openRoom(result.session_id);
    await refreshRoomDashboard();
  } catch (e) { document.getElementById("rooms-error").textContent = e.message; }
});
document.getElementById("my-rooms-list").addEventListener("click", async (event) => {
  const openButton = event.target.closest("[data-open-room]");
  try {
    if (openButton) await openRoom(openButton.dataset.openRoom);
  } catch (e) { document.getElementById("rooms-error").textContent = e.message; }
});

async function refreshRoomDashboard() {
  if (!authClient.profile || authClient.profile.must_change_password) return;
  createRoomForm.classList.toggle("hidden", !authClient.profile.is_admin);
  const error = document.getElementById("rooms-error");
  error.textContent = "";
  try {
    const [roomsData, invitesData, historyData, trophiesData] = await Promise.all([
      sessionClient.getMyRooms(), sessionClient.getPendingInvites(), authClient.getHistory(), authClient.getTrophies(),
    ]);
    const rooms = document.getElementById("my-rooms-list");
    rooms.innerHTML = "";
    const visibleRooms = roomsData.rooms.filter((room) => room.status === "active" || room.status === "finished_natural");
    for (const room of visibleRooms) {
      const item = document.createElement("article");
      item.className = "room-dashboard-item";
      const label = document.createElement("strong");
      const statusLabel = room.status === "finished_natural" ? "Finalizada" : "";
      label.textContent = [room.name, room.mode_name || "Lobby", statusLabel].filter(Boolean).join(" · ");
      item.append(label);
      if (room.status === "active") {
        const open = document.createElement("button");
        open.className = "btn-small"; open.type = "button"; open.dataset.openRoom = room.session_id; open.textContent = "Abrir"; item.append(open);
      }
      rooms.append(item);
    }
    if (!visibleRooms.length) rooms.textContent = "Todavía no participás en ninguna sala.";

    const invites = document.getElementById("room-invitations");
    invites.innerHTML = "";
    for (const invite of invitesData.invites) {
      const item = document.createElement("article"); item.className = "room-dashboard-item";
      const label = document.createElement("strong"); label.textContent = `Invitación a “${invite.room_name || "Sala anterior"}” de @${invite.inviter?.username || "admin"}`;
      const accept = document.createElement("button"); accept.className = "btn-small"; accept.type = "button"; accept.dataset.inviteAction = "accept"; accept.dataset.inviteId = invite.id; accept.textContent = "Aceptar";
      const decline = document.createElement("button"); decline.className = "btn-small btn-danger"; decline.type = "button"; decline.dataset.inviteAction = "decline"; decline.dataset.inviteId = invite.id; decline.textContent = "Rechazar";
      item.append(label, accept, decline); invites.append(item);
    }
    const trophiesList = document.getElementById("my-trophies-list");
    trophiesList.innerHTML = "";
    for (const entry of trophiesData.trophies) {
      const item = document.createElement("div"); item.className = "profile-record-item trophy-record";
      const trophy = entry.trophies || {};
      const medal = document.createElement("span");
      medal.className = "trophy-medal";
      medal.textContent = trophy.icon_key || "🏅";
      medal.setAttribute("aria-hidden", "true");
      const title = document.createElement("strong");
      title.className = "trophy-title";
      title.textContent = trophy.title || trophy.id || "Trofeo";
      item.append(medal, title);

      const pokemonNames = { 493: "Arceus", 142: "Aerodactyl", 452: "Drapion", 904: "Overqwil", 28: "Sandslash", 330: "Flygon" };
      const sprites = document.createElement("span");
      sprites.className = "trophy-pokemon-sprites";
      for (const pokemonId of entry.pokemon_ids || trophy.pokemon_ids || []) {
        const img = document.createElement("img");
        const id = Number(pokemonId);
        img.src = `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-viii/icons/${id}.png`;
        img.alt = pokemonNames[id] || `Pokémon ${id}`;
        img.title = img.alt;
        img.loading = "lazy";
        img.onerror = () => {
          img.onerror = null;
          img.src = `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${id}.png`;
        };
        sprites.append(img);
      }
      item.append(sprites);
      item.title = trophy.description || "";
      trophiesList.append(item);
    }
    if (!trophiesData.trophies.length) trophiesList.textContent = "Todavía no obtuviste trofeos.";
    const historyList = document.getElementById("my-history-list");
    historyList.innerHTML = "";
    for (const entry of historyData.history) {
      const item = document.createElement("div"); item.className = "profile-record-item";
      item.textContent = `${entry.room_name || "Sala anterior"} · ${entry.mode || "Sala"} · ${new Date(entry.finished_at).toLocaleDateString()}`;
      historyList.append(item);
    }
    if (!historyData.history.length) historyList.textContent = "Todavía no hay salas finalizadas en tu historial.";
    createRoomForm.classList.toggle("hidden", !authClient.profile.is_admin);
  } catch (e) { error.textContent = e.message; }
}

async function openRoom(sessionId) {
  sessionClient.disconnect();
  resetCurrentRoomUi();
  const profile = authClient.profile;
  const state = await sessionClient.getSession(sessionId);
  setActiveRoomName(state.name);
  showScreen(state.started ? "draft" : "lobby");
  renderPlayers(state.players, state.host, profile.username);
  await connect(sessionId, profile.username);
}

function resetCurrentRoomUi() {
  if (currentModeUI) currentModeUI.resetState();
  currentModeKey = null;
  currentModeUI = null;
  isHost = false;
  isReady = false;
  document.getElementById("active-room-name")?.classList.add("hidden");
  btnForceCloseRoom.classList.add("hidden");
  btnFinishRoom.classList.add("hidden");
  inviteRoomMenu.open = false;
  inviteRoomMenu.classList.add("hidden");
  document.getElementById("draft-grid")?.replaceChildren();
  const draftState = document.getElementById("draft-state");
  if (draftState) draftState.textContent = "";
  const draftSubtitle = document.getElementById("draft-subtitle");
  if (draftSubtitle) draftSubtitle.textContent = "Esperando que el draft comience...";
  pickedList?.replaceChildren();
  document.getElementById("draft-picked")?.classList.add("hidden");
}

function setActiveRoomName(name) {
  const label = document.getElementById("active-room-name");
  if (!label) return;
  label.textContent = `Sala: ${name || "Sala anterior"}`;
  label.classList.remove("hidden");
}

// ── Conexión WebSocket ────────────────────────────────────────────────────
async function connect(sessionId, username) {
  setConnectionStatus("Conectando...", "");
  try {
  await sessionClient.connectWebSocket(
    sessionId,
    username,
    handleWebSocketMessage,
    () => {
      setConnectionStatus("● En línea", "online");
      logEvent("Conectado a la sesión.");
      showScreen("lobby");
    },
    () => {
      setConnectionStatus("○ Desconectado", "offline");
      logEvent("Conexión cerrada.");
    },
    (err) => {
      console.error(err);
      setConnectionStatus("⚠ Error de conexión", "offline");
    }
  );
  } catch (error) {
    setConnectionStatus("⚠ Error de conexión", "offline");
    document.getElementById("rooms-error").textContent = error.message;
  }
}

// ── Manejador Principal de Eventos WebSocket ──────────────────────────────
function handleWebSocketMessage(msg) {
  const event = msg.event;
  const data = msg.data || {};
  if (event === "session_state" || event === "subasta_state_update") {
    const modeState = event === "session_state" ? (data.draft_state || data) : data;
    const isSubasta = (data.mode || currentModeKey) === "subasta_pokemon";
    const trophySelectionPending = isSubasta
      && modeState.event_finished === true
      && modeState.trophy_ready_to_close === false;
    btnFinishRoom.disabled = Boolean(trophySelectionPending);
    btnFinishRoom.title = trophySelectionPending
      ? "Cada ganador debe guardar seis Pokémon para su trofeo."
      : "";
  }

  if (event === "session_state") {
    setActiveRoomName(data.name);
    isHost = data.can_control === true;
    btnForceCloseRoom.classList.toggle("hidden", !isHost);
    inviteRoomMenu.classList.toggle("hidden", !isHost);
    const naturallyFinished = Boolean(data.draft_state?.finished || data.draft_state?.event_finished || data.event_finished);
    btnFinishRoom.classList.toggle("hidden", !isHost || !naturallyFinished);

    const nextModeKey = data.mode || null;
    if (nextModeKey !== currentModeKey) {
      if (currentModeUI) currentModeUI.resetState();
      currentModeKey = nextModeKey;
      currentModeUI = nextModeKey ? modeUIRegistry[nextModeKey] || null : null;
    }
  }

  if (event === "draft_finished" || event === "draft_complete" || event === "event_finished") {
    if (isHost) btnFinishRoom.classList.remove("hidden");
  }
  if (isHost && (data.finished === true || data.event_finished === true || data.draft_state?.finished === true || data.draft_state?.event_finished === true)) {
    btnFinishRoom.classList.remove("hidden");
  }

  // Intentar delegar primero al controlador de UI del modo de juego activo
  if (currentModeUI) {
    const handled = currentModeUI.handleEvent(event, data, {
      sessionClient,
      isHost,
    });
    if (handled && event !== "session_state") return;
  }

  // Eventos generales del Lobby
  switch (event) {
    case "session_state":
      updateLobbyState(data);
      break;

    case "player_joined":
      logEvent(data.reconnected ? `⚡ ${data.username} se reconectó` : `👤 ${data.username} se unió a la sala`);
      updatePlayersAndHost(data.players, data.host);
      break;

    case "player_left":
      logEvent(`🚪 ${data.username} salió de la sala`);
      updatePlayersAndHost(data.players, data.host);
      break;

    case "player_ready":
      logEvent(`${data.ready ? "✓" : "⏳"} ${data.username} ${data.ready ? "está listo" : "no está listo"}`);
      updatePlayersAndHost(data.players, data.host);
      break;

    case "all_ready":
      logEvent("✨ ¡Todos los jugadores están listos!");
      updatePlayersAndHost(data.players, data.host);
      break;

    case "mode_selection":
      inviteRoomMenu.open = false;
      showScreen("mode");
      renderModeSelection(data.available_modes);
      break;

    case "mode_config":
      inviteRoomMenu.open = false;
      if (currentModeKey !== data.mode && currentModeUI) currentModeUI.resetState();
      currentModeKey = data.mode || null;
      currentModeUI = currentModeKey ? modeUIRegistry[currentModeKey] || null : null;
      setupModeConfig(data);
      break;

    case "mode_configured":
      logEvent(`Modo '${data.mode_name}' configurado por un admin participante.`);
      if (btnStartDraft) {
        btnStartDraft.classList.toggle("hidden", !isHost);
      }
      break;

    case "draft_started":
      inviteRoomMenu.open = false;
      showScreen("draft");
      logEvent("¡La partida ha comenzado!");
      break;


    case "error":
      logEvent(`❌ Error: ${data.message}`);
      alert(data.message);
      break;

    case "room_closed":
      closeProfileMenu();
      if (data.finish_type !== "forced") logEvent("La sala finalizó.");
      sessionClient.disconnect();
      btnForceCloseRoom.classList.add("hidden");
      btnFinishRoom.classList.add("hidden");
      inviteRoomMenu.open = false;
      inviteRoomMenu.classList.add("hidden");
      resetCurrentRoomUi();
      window.history.replaceState({}, "", window.location.pathname);
      showScreen("home");
      refreshRoomDashboard();
      break;
  }
}

// ── Helpers de actualización de Estado de Lobby ───────────────────────────
function updateLobbyState(data) {
  updatePlayersAndHost(data.players, data.host);

  if (data.started) {
    showScreen("draft");
  } else {
    showScreen("lobby");
  }
}

function updatePlayersAndHost(players, host) {
  const playerList = Array.isArray(players) ? players : [];
  const me = playerList.find((p) => p && p.username === sessionClient.currentUsername);
  isHost = Boolean(me && me.is_admin);
  btnForceCloseRoom.classList.toggle("hidden", !isHost);
  inviteRoomMenu.classList.toggle("hidden", !isHost);
  if (me) {
    isReady = me.ready;
    btnReady.textContent = isReady ? "Cancelar Listo" : "Listo ✓";
    btnReady.className = isReady ? "btn-danger" : "";
  }

  updateHostUI();
  renderPlayers(playerList, host, sessionClient.currentUsername);
}

function updateHostUI() {
  if (btnStartGame) {
    btnStartGame.classList.toggle("hidden", !isHost);
  }
}

// ── Pantalla de Selección y Configuración de Modo ─────────────────────────
function renderModeSelection(modes) {
  if (!modeGrid) return;
  modeGrid.innerHTML = "";
  if (modeConfig) modeConfig.classList.add("hidden");

  modes.forEach((mode) => {
    const card = document.createElement("div");
    card.className = "card mode-card";
    card.innerHTML = `
      <h3>${mode.name}</h3>
      <p class="subtitle">Haz clic para seleccionar este modo de juego</p>
      ${isHost ? '<button class="btn-small">Seleccionar</button>' : '<span class="badge">Esperando a un admin participante</span>'}
    `;

    if (isHost) {
      card.addEventListener("click", () => {
        sessionClient.send({
          action: "choose_mode",
          mode: mode.key,
        });
      });
    }

    modeGrid.appendChild(card);
  });
}

function setupModeConfig(data) {
  currentModeKey = data.mode;
  currentModeUI = modeUIRegistry[data.mode] || null;

  if (modeConfig) modeConfig.classList.remove("hidden");
  document.getElementById("mode-config-title").textContent = `Configurar ${data.mode_name}`;

  // Cada modo reutiliza el mismo panel: quitar los campos anteriores antes de dibujar el nuevo.
  const modeConfigFields = document.getElementById("mode-config-fields");
  if (modeConfigFields) modeConfigFields.replaceChildren();

  if (currentModeUI) {
    currentModeUI.resetState();
    currentModeUI.renderConfigFields(modeConfig, data, isHost);
  }

  if (btnConfigure) btnConfigure.classList.toggle("hidden", !isHost);
  if (btnStartDraft) btnStartDraft.classList.add("hidden");
}

// ── Botones y Acciones Interactivas ───────────────────────────────────────
if (btnReady) {
  btnReady.addEventListener("click", () => {
    sessionClient.send({ action: "toggle_ready" });
  });
}

if (btnStartGame) {
  btnStartGame.addEventListener("click", () => {
    sessionClient.send({ action: "start_game" });
  });
}

if (btnLeave) {
  btnLeave.addEventListener("click", () => {
    sessionClient.disconnect();
    isHost = false;
    btnForceCloseRoom.classList.add("hidden");
    btnFinishRoom.classList.add("hidden");
    inviteRoomMenu.open = false;
    inviteRoomMenu.classList.add("hidden");
    resetCurrentRoomUi();
    showScreen("home");
    window.history.replaceState({}, "", window.location.pathname);
  });
}

if (btnConfigure) {
  btnConfigure.addEventListener("click", () => {
    if (!currentModeUI) return;
    const configPayload = currentModeUI.readConfigFields(modeConfig);
    sessionClient.send({
      action: "configure_mode",
      ...configPayload,
    });
  });
}

if (btnStartDraft) {
  btnStartDraft.addEventListener("click", () => {
    sessionClient.send({ action: "start_draft" });
  });
}

if (btnBackToLobby) {
  btnBackToLobby.addEventListener("click", () => {
    showScreen("lobby");
  });
}

if (btnBackDraft) {
  btnBackDraft.addEventListener("click", () => {
    showScreen("lobby");
  });
}

if (modalClose) {
  modalClose.addEventListener("click", () => {
    if (modalOverlay) modalOverlay.classList.add("hidden");
  });
}

if (btnTogglePicked) {
  btnTogglePicked.addEventListener("click", () => {
    if (!pickedList) return;
    const isOpening = pickedList.classList.contains("hidden");
    pickedList.classList.toggle("hidden", !isOpening);
    btnTogglePicked.setAttribute("aria-expanded", String(isOpening));
  });
}
