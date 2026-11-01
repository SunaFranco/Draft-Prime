/**
 * app.js — Punto de entrada del frontend modularizado
 */

import { SessionClient } from "./js/core/session.js";
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

// Estado local de la aplicación
let isReady = false;
let isHost = false;
let currentModeKey = null;
let currentModeUI = null;

// Elementos del DOM generales
const btnStartGame = document.getElementById("btn-start-game");
const btnReady = document.getElementById("btn-ready");
const btnLeave = document.getElementById("btn-leave");
const btnCopyLink = document.getElementById("btn-copy-link");
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

// ── Al cargar la página ───────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const sessionFromUrl = params.get("session");

  const saved = sessionClient.getSavedSession();
  if (saved && saved.sessionId === sessionFromUrl) {
    connect(saved.sessionId, saved.username);
    return;
  }

  if (sessionFromUrl) {
    document.getElementById("invite-session-id").textContent = sessionFromUrl;
    document.getElementById("invite-banner").classList.remove("hidden");
    document.getElementById("home-cards").classList.add("hidden");
  }
});

// Unirse por link de invitación
document.getElementById("btn-join-invite").addEventListener("click", () => {
  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get("session");
  const username = document.getElementById("invite-username").value.trim();
  const errEl = document.getElementById("invite-error");
  const btnJoinInvite = document.getElementById("btn-join-invite");
  errEl.textContent = "";

  if (!username) { errEl.textContent = "Ingresá tu nombre."; return; }
  if (!sessionId) { errEl.textContent = "No se encontró el ID de sesión."; return; }

  const originalText = btnJoinInvite.textContent;
  btnJoinInvite.disabled = true;
  btnJoinInvite.textContent = "Uniendo...";

  try {
    connect(sessionId, username);
  } finally {
    btnJoinInvite.disabled = false;
    btnJoinInvite.textContent = originalText;
  }
});

// Crear sesión
document.getElementById("btn-create").addEventListener("click", async () => {
  const username = document.getElementById("create-username").value.trim();
  const errEl = document.getElementById("create-error");
  const btnCreate = document.getElementById("btn-create");
  errEl.textContent = "";

  if (!username) { errEl.textContent = "Ingresá tu nombre."; return; }

  const originalText = btnCreate.textContent;
  btnCreate.disabled = true;
  btnCreate.textContent = "Creando lobby...";

  try {
    const data = await sessionClient.createSession(username);
    const sessionId = data.session_id || data.id;
    window.history.pushState({}, "", `?session=${sessionId}`);

    document.getElementById("session-id-display").textContent = sessionId;
    showScreen("lobby");
    renderPlayers(data.players, data.host, username);
    setConnectionStatus("Conectando...", "");

    connect(sessionId, username);
  } catch (e) {
    errEl.textContent = e.message || "No se pudo conectar al servidor.";
  } finally {
    btnCreate.disabled = false;
    btnCreate.textContent = originalText;
  }
});

// Unirse con ID manual
document.getElementById("btn-join").addEventListener("click", () => {
  const username  = document.getElementById("join-username").value.trim();
  const sessionId = document.getElementById("join-session-id").value.trim();
  const errEl     = document.getElementById("join-error");
  const btnJoin   = document.getElementById("btn-join");
  errEl.textContent = "";

  if (!username)  { errEl.textContent = "Ingresá tu nombre."; return; }
  if (!sessionId) { errEl.textContent = "Ingresá el ID de sesión."; return; }

  const originalText = btnJoin.textContent;
  btnJoin.disabled = true;
  btnJoin.textContent = "Uniendo...";

  try {
    window.history.pushState({}, "", `?session=${sessionId}`);
    connect(sessionId, username);
  } finally {
    btnJoin.disabled = false;
    btnJoin.textContent = originalText;
  }
});

// ── Conexión WebSocket ────────────────────────────────────────────────────
function connect(sessionId, username) {
  setConnectionStatus("Conectando...", "");

  sessionClient.connectWebSocket(
    sessionId,
    username,
    handleWebSocketMessage,
    () => {
      setConnectionStatus("● En línea", "online");
      logEvent("Conectado a la sesión.");
      document.getElementById("session-id-display").textContent = sessionId;
      showScreen("lobby");
      sessionClient.saveActiveSession(sessionId, username);
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
}

// ── Manejador Principal de Eventos WebSocket ──────────────────────────────
function handleWebSocketMessage(msg) {
  const event = msg.event;
  const data = msg.data || {};

  if (event === "session_state") {
    isHost = data.host === sessionClient.currentUsername;

    if (data.mode) {
      currentModeKey = data.mode;
      currentModeUI = modeUIRegistry[data.mode] || null;
    }
  } else if (event === "host_changed") {
    isHost = data.new_host === sessionClient.currentUsername;
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

    case "host_changed":
      logEvent(`👑 El nuevo host es ${data.new_host}`);
      isHost = data.new_host === sessionClient.currentUsername;
      updateHostUI();
      break;

    case "mode_selection":
      showScreen("mode");
      renderModeSelection(data.available_modes);
      break;

    case "mode_config":
      setupModeConfig(data);
      break;

    case "mode_configured":
      logEvent(`Modo '${data.mode_name}' configurado por el host.`);
      if (btnStartDraft) {
        btnStartDraft.classList.toggle("hidden", !isHost);
      }
      break;

    case "draft_started":
      showScreen("draft");
      logEvent("¡La partida ha comenzado!");
      break;


    case "error":
      logEvent(`❌ Error: ${data.message}`);
      alert(data.message);
      break;
  }
}

// ── Helpers de actualización de Estado de Lobby ───────────────────────────
function updateLobbyState(data) {
  isHost = data.host === sessionClient.currentUsername;
  updatePlayersAndHost(data.players, data.host);

  if (data.started) {
    showScreen("draft");
  } else {
    showScreen("lobby");
  }
}

function updatePlayersAndHost(players, host) {
  isHost = host === sessionClient.currentUsername;
  const playerList = Array.isArray(players) ? players : [];
  const me = playerList.find((p) => p && p.username === sessionClient.currentUsername);
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
      ${isHost ? '<button class="btn-small">Seleccionar</button>' : '<span class="badge">Esperando al host</span>'}
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
    sessionClient.clearSavedSession();
    if (currentModeUI) currentModeUI.resetState();
    currentModeUI = null;
    currentModeKey = null;
    showScreen("home");
    window.history.pushState({}, "", window.location.pathname);
  });
}

if (btnCopyLink) {
  btnCopyLink.addEventListener("click", () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
      btnCopyLink.textContent = "¡Copiado!";
      setTimeout(() => (btnCopyLink.textContent = "Copiar link"), 2000);
    });
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
