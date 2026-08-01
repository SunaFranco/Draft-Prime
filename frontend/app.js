/**
 * app.js — Lógica del frontend
 *
 * Maneja:
 *  - Crear sesión (POST /session/create)
 *  - Unirse a sesión (via WebSocket)
 *  - Recibir y mostrar eventos en tiempo real
 *  - Leer el session_id de la URL al cargar (si viene de un link de invitación)
 */

const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const localApiUrl = "http://localhost:8000";
const defaultApiUrl = isLocalhost ? localApiUrl : window.location.origin;
const API = window.API_URL || defaultApiUrl;
const WS_BASE = window.WS_URL || `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${new URL(API).host}`;

// ── Estado local ───────────────────────────────────────────────────────────
let ws = null;
let currentSessionId = null;
let currentUsername = null;
let isReady = false;
let isHost = false;
let currentDraftCards = [];
let currentPickedCards = [];
let currentDraftPackId = null;
let currentDetailCard = null;

// ── Elementos del DOM ──────────────────────────────────────────────────────
const screenHome    = document.getElementById("screen-home");
const screenLobby   = document.getElementById("screen-lobby");
const screenMode    = document.getElementById("screen-mode");
const screenDraft   = document.getElementById("screen-draft");
const btnStartGame  = document.getElementById("btn-start-game");
const modeGrid      = document.getElementById("mode-grid");
const modeSubtitle  = document.getElementById("mode-subtitle");
const modeConfig    = document.getElementById("mode-config");
const cubeSelect    = document.getElementById("cube-select");
const packCount     = document.getElementById("pack-count");
const cardsPerPack  = document.getElementById("cards-per-pack");
const btnConfigure  = document.getElementById("btn-configure-mode");
const btnStartDraft = document.getElementById("btn-start-draft");
const draftSubtitle = document.getElementById("draft-subtitle");
const draftState    = document.getElementById("draft-state");
const draftPicked   = document.getElementById("draft-picked");
const draftPickedList = document.getElementById("draft-picked-list");
const btnTogglePickedCards = document.getElementById("btn-toggle-picked-cards");
const draftGrid     = document.getElementById("draft-grid");
const btnBackDraft  = document.getElementById("btn-back-to-lobby-draft");
const cardDetailModal = document.getElementById("card-detail-modal");
const modalCloseButton = document.getElementById("modal-close");
const modalCardImage = document.getElementById("modal-card-image");
const modalCardName = document.getElementById("modal-card-name");
const modalCardType = document.getElementById("modal-card-type");
const modalCardSubtype = document.getElementById("modal-card-subtype");
const modalCardStats = document.getElementById("modal-card-stats");
const modalCardDesc = document.getElementById("modal-card-desc");

// ── Al cargar la página: leer ?session= de la URL ─────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const sessionFromUrl = params.get("session");
  if (sessionFromUrl) {
    // Si viene con link de invitación, mostrar pantalla especial de unirse
    document.getElementById("invite-session-id").textContent = sessionFromUrl;
    document.getElementById("invite-banner").classList.remove("hidden");
    document.getElementById("home-cards").classList.add("hidden");
  }
});

// Unirse desde link de invitación
document.getElementById("btn-join-invite").addEventListener("click", () => {
  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get("session");
  const username = document.getElementById("invite-username").value.trim();
  const errEl = document.getElementById("invite-error");
  errEl.textContent = "";

  if (!username) { errEl.textContent = "Ingresá tu nombre."; return; }
  if (!sessionId) { errEl.textContent = "No se encontró el ID de sesión."; return; }

  connectWebSocket(sessionId, username);
});

// ══════════════════════════════════════════════════════════════════════════
// CREAR SESIÓN
// ══════════════════════════════════════════════════════════════════════════

document.getElementById("btn-create").addEventListener("click", async () => {
  const username = document.getElementById("create-username").value.trim();
  const errEl = document.getElementById("create-error");
  errEl.textContent = "";

  if (!username) { errEl.textContent = "Ingresá tu nombre."; return; }

  try {
    const res = await fetch(`${API}/session/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username }),
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.detail; return; }

    // Actualizar URL con el session_id (para poder compartir el link)
    window.history.pushState({}, "", `?session=${data.session_id}`);

    // Mostrar el lobby de inmediato con los datos del creador
    // (no esperar al WebSocket para la transición de pantalla)
    document.getElementById("session-id-display").textContent = data.id;
    showScreen("lobby");
    renderPlayers(data.players, data.host);
    setConnectionStatus("Conectando...", "");

    // Conectar via WebSocket (en paralelo, sin bloquear la UI)
    connectWebSocket(data.session_id, username);

  } catch (e) {
    errEl.textContent = "No se pudo conectar al servidor.";
  }
});

// ══════════════════════════════════════════════════════════════════════════
// UNIRSE A SESIÓN
// ══════════════════════════════════════════════════════════════════════════

document.getElementById("btn-join").addEventListener("click", () => {
  const username  = document.getElementById("join-username").value.trim();
  const sessionId = document.getElementById("join-session-id").value.trim();
  const errEl     = document.getElementById("join-error");
  errEl.textContent = "";

  if (!username)  { errEl.textContent = "Ingresá tu nombre."; return; }
  if (!sessionId) { errEl.textContent = "Ingresá el ID de sesión."; return; }

  window.history.pushState({}, "", `?session=${sessionId}`);
  connectWebSocket(sessionId, username);
});

// ══════════════════════════════════════════════════════════════════════════
// WEBSOCKET
// ══════════════════════════════════════════════════════════════════════════

function connectWebSocket(sessionId, username) {
  currentSessionId = sessionId;
  currentUsername  = username;

  const url = `${WS_BASE}/session/${sessionId}/ws?username=${encodeURIComponent(username)}`;
  ws = new WebSocket(url);

  ws.onopen = () => {
    setConnectionStatus("Conectado ✓", "ok");
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    handleEvent(msg);
  };

  ws.onerror = () => {
    const errEl = document.getElementById("join-error") || document.getElementById("create-error");
    if (errEl) errEl.textContent = "Error de conexión. ¿Está el servidor corriendo?";
    setConnectionStatus("Error de conexión", "error");
  };

  ws.onclose = (e) => {
    // Código 4003 = sesión llena, 4004 = no existe
    if (e.code === 4003) {
      alert("La sesión está llena (máx. 4 jugadores).");
      showScreen("home");
    } else if (e.code === 4004) {
      alert("La sesión no existe.");
      showScreen("home");
    } else {
      setConnectionStatus("Desconectado", "error");
    }
  };
}

// ══════════════════════════════════════════════════════════════════════════
// MANEJO DE EVENTOS DEL SERVIDOR
// ══════════════════════════════════════════════════════════════════════════

function handleEvent(msg) {
  const { event, data } = msg;

  switch (event) {

    case "session_state":
      // Estado inicial al conectarse: renderizar todo
      document.getElementById("session-id-display").textContent = data.id;
      renderPlayers(data.players, data.host);
      isReady = data.players.some((p) => p.username === currentUsername && p.ready);
      updateReadyButton();
      updateLobbyControls(data.players, data.host);

      if (data.started) {
        draftSubtitle.textContent = `Draft iniciado: ${data.mode_name || "Modo"}`;
        showScreen("draft");
      } else if (data.mode && !data.mode_config) {
        renderModeSelection({
          host: data.host,
          players: data.players,
          available_modes: [{ key: "cube_draft_yugioh", name: "Draft cube yugioh" }, { key: "subasta_pokemon", name: "Subasta pokemon" }],
        });
        showScreen("mode");
      } else if (data.mode && data.mode_config) {
        renderModeConfigured(data);
        showScreen("mode");
      } else {
        showScreen("lobby");
      }

      logEvent(`Conectado a la sesión como ${currentUsername}`);
      break;

    case "player_joined":
      renderPlayers(data.players, data.host);
      updateLobbyControls(data.players, data.host);
      logEvent(
        data.reconnected
          ? `${data.username} se reconectó 🔄`
          : `${data.username} se unió al lobby 👋`
      );
      break;

    case "player_left":
      renderPlayers(data.players, data.host);
      updateLobbyControls(data.players, data.host);
      logEvent(`${data.username} se desconectó 🚪`);
      break;

    case "player_ready":
      renderPlayers(data.players, data.host);
      updateLobbyControls(data.players, data.host);
      logEvent(`${data.username} ${data.ready ? "está listo ✅" : "canceló su ready ❌"}`);
      // Sincronizar estado del botón si somos nosotros
      if (data.username === currentUsername) {
        isReady = data.ready;
        updateReadyButton();
      }
      break;

    case "all_ready":
      renderPlayers(data.players, data.host);
      updateLobbyControls(data.players, data.host);
      logEvent(`Todos están listos. El host puede empezar la partida.`);
      break;

    case "mode_selection":
      renderPlayers(data.players, data.host);
      updateLobbyControls(data.players, data.host);
      renderModeSelection(data);
      showScreen("mode");
      logEvent(`¡Listo! Elegí un modo de juego.`);
      break;

    case "mode_config":
      renderPlayers(data.players, data.host);
      updateLobbyControls(data.players, data.host);
      renderModeConfig(data);
      showScreen("mode");
      logEvent(`Modo seleccionado: ${data.mode_name}. Configurá el cube draft.`);
      break;

    case "mode_configured":
      renderPlayers(data.players, data.host);
      updateLobbyControls(data.players, data.host);
      renderModeConfigured(data);
      showScreen("mode");
      logEvent(`Configuración guardada. Listo para iniciar el draft.`);
      break;

    case "draft_started":
      renderPlayers(data.players, data.host);
      updateLobbyControls(data.players, data.host);
      draftSubtitle.textContent = `Draft iniciado: ${data.mode_name}`;
      draftState.innerHTML = `<p>El draft comenzó con el cube <strong>${data.mode_config.cube_key}</strong>.</p>`;
      showScreen("draft");
      break;

    case "draft_open_pack":
      showScreen("draft");
      renderDraftPack(data);
      break;

    case "draft_pick_confirmed":
      currentPickedCards.push(data.card);
      renderPickedCards();
      document.querySelectorAll(".btn-pick-card").forEach(btn => {
        btn.disabled = true;
        btn.style.opacity = "0.5";
        btn.style.cursor = "not-allowed";
        btn.textContent = "Elegida ✓";
      });
      if (document.getElementById("pick-status-banner")) {
        document.getElementById("pick-status-banner").innerHTML = `✅ Elegiste <strong>${data.card.name}</strong>. Esperando a los demás jugadores...`;
      } else {
        draftState.innerHTML += `
          <div id="pick-status-banner" style="margin-top:0.75rem; padding:0.65rem 1rem; background:rgba(16,185,129,0.15); border:1px solid var(--accent-success); border-radius:var(--radius-md); font-size:0.9rem; color:var(--text-main);">
            ✅ Elegiste <strong>${data.card.name}</strong>. Esperando a los demás jugadores...
          </div>
        `;
      }
      break;

    case "draft_step_progress":
      logEvent(`Pick en progreso: ${data.picked_count}/${data.total_players} jugadores eligieron.`);
      break;

    case "draft_round_start":
      logEvent(`🔔 ¡Comienza la Ronda ${data.round} de ${data.total_rounds}! Abriendo sobres nuevos...`);
      break;

    case "draft_complete":
      renderDraftComplete(data);
      break;


    case "host_changed":
      renderPlayers(data.players || [], data.new_host);
      updateLobbyControls(data.players || [], data.new_host);
      logEvent(`Nuevo host: ${data.new_host} 👑`);
      break;

    case "error":
      logEvent(`⚠️ Error: ${data.message}`);
      break;
  }
}

// ══════════════════════════════════════════════════════════════════════════
// ACCIONES DEL USUARIO
// ══════════════════════════════════════════════════════════════════════════

// Botón "Listo"
document.getElementById("btn-ready").addEventListener("click", () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "toggle_ready" }));
  }
});

// Botón "Salir"
document.getElementById("btn-leave").addEventListener("click", () => {
  if (ws) ws.close();
  window.history.pushState({}, "", "/");
  showScreen("home");
  logEvent("");   // limpiar log
});

// Botón "Empezar partida" (solo host cuando todos están listos)
btnStartGame.addEventListener("click", () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "start_game" }));
  }
});

// Botones de selección de modo
document.addEventListener("click", (event) => {
  const target = event.target;
  if (target.matches(".mode-card")) {
    const mode = target.dataset.mode;
    if (mode && ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: "choose_mode", mode }));
    }
  }
});

document.getElementById("btn-back-to-lobby").addEventListener("click", () => {
  showScreen("lobby");
});

btnConfigure.addEventListener("click", () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({
    action: "configure_mode",
    cube_key: cubeSelect.value,
    pack_count: packCount.value,
    cards_per_pack: cardsPerPack.value,
  }));
});

btnStartDraft.addEventListener("click", () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ action: "start_draft" }));
});

btnBackDraft.addEventListener("click", () => {
  showScreen("lobby");
});

// Botón "Copiar link"
document.getElementById("btn-copy-link").addEventListener("click", () => {
  const url = window.location.href;
  navigator.clipboard.writeText(url).then(() => {
    document.getElementById("btn-copy-link").textContent = "¡Copiado!";
    setTimeout(() => {
      document.getElementById("btn-copy-link").textContent = "Copiar link";
    }, 1500);
  });
});

// ══════════════════════════════════════════════════════════════════════════
// RENDER
// ══════════════════════════════════════════════════════════════════════════

/**
 * Dibuja los slots de jugadores (siempre 4 slots, vacíos o con jugador).
 * @param {Array}  players  - Lista de jugadores de la sesión
 * @param {string|null} host - Username del host (null = no actualizar)
 */
function renderPlayers(players, host) {
  const grid = document.getElementById("players-grid");
  grid.innerHTML = "";

  for (let i = 0; i < 4; i++) {
    const player = players[i];
    const slot   = document.createElement("div");

    if (player) {
      const isHost = player.username === (host || "");
      const isMe   = player.username === currentUsername;

      slot.className = "player-slot occupied"
        + (player.ready     ? " ready"        : "")
        + (isMe             ? " me"            : "")
        + (!player.connected ? " disconnected" : "");

      slot.innerHTML = `
        <div class="player-avatar">${player.username[0].toUpperCase()}</div>
        <div class="player-info">
          <span class="player-name">
            ${player.username}
            ${isHost ? " 👑" : ""}
            ${isMe   ? " (vos)" : ""}
          </span>
          <span class="player-status">
            ${!player.connected ? "Desconectado" : player.ready ? "Listo ✅" : "Esperando..."}
          </span>
        </div>
      `;
    } else {
      slot.className = "player-slot empty";
      slot.innerHTML = `<span class="empty-label">Slot vacío</span>`;
    }

    grid.appendChild(slot);
  }
}

/**
 * Agrega un mensaje al log de eventos visible en la UI.
 */
function logEvent(message) {
  if (!message) {
    document.getElementById("event-log").innerHTML = "";
    return;
  }
  const log = document.getElementById("event-log");
  const li  = document.createElement("li");
  li.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  log.prepend(li);   // Nuevo arriba
}

function playersAllReady(players) {
  const connectedPlayers = players.filter((player) => player.connected);
  return connectedPlayers.length > 0 && connectedPlayers.every((player) => player.ready);
}

function renderModeSelection(data) {
  if (!modeGrid) return;

  const isCurrentHost = data.host === currentUsername;
  if (modeSubtitle) {
    modeSubtitle.textContent = isCurrentHost
      ? "Elegí un modo de juego para empezar la partida."
      : "Esperando a que el host defina el modo de juego...";
  }

  if (!isCurrentHost) {
    modeGrid.innerHTML = `
      <div class="mode-waiting">
        <p>El host <strong>${data.host}</strong> está eligiendo el modo.</p>
        <p>Por favor, esperá mientras se define la regla.</p>
      </div>
    `;
    modeConfig.classList.add("hidden");
    return;
  }

  const modes = (data.available_modes || []).map((mode) => {
    if (typeof mode === "string") {
      return { key: mode, name: mode };
    }
    return mode;
  });

  if (modes.length === 0) {
    modeGrid.innerHTML = `<div class="mode-empty">No hay modos disponibles por ahora.</div>`;
    return;
  }

  modeGrid.innerHTML = modes
    .map((mode) => `<button type="button" class="mode-card" data-mode="${mode.key}">${mode.name}</button>`)
    .join("\n");
  modeConfig.classList.add("hidden");
}

function renderModeConfig(data) {
  if (!modeConfig) return;
  const isCurrentHost = data.host === currentUsername;
  if (!isCurrentHost) {
    modeGrid.innerHTML = `
      <div class="mode-waiting">
        <p>El host <strong>${data.host}</strong> eligió el modo <strong>${data.mode_name}</strong>.</p>
        <p>Esperá a que configure el cube y los sobres.</p>
      </div>
    `;
    modeConfig.classList.add("hidden");
    return;
  }

  modeGrid.innerHTML = "";
  modeConfig.classList.remove("hidden");
  btnStartDraft.classList.add("hidden");
  populateCubeOptions(data.available_cubes || []);
}

function renderModeConfigured(data) {
  if (!modeConfig) return;
  const isCurrentHost = data.host === currentUsername;
  if (!isCurrentHost) {
    modeGrid.innerHTML = `
      <div class="mode-waiting">
        <p>El host <strong>${data.host}</strong> ya configuró el modo <strong>${data.mode_name}</strong>.</p>
        <p>Esperá a que inicie el draft.</p>
      </div>
    `;
    modeConfig.classList.add("hidden");
    return;
  }

  modeConfig.classList.remove("hidden");
  modeGrid.innerHTML = "";
  modeSubtitle.textContent = `Modo elegido: ${data.mode_name}.`;
  btnStartDraft.classList.remove("hidden");

  if (data.mode_config) {
    cubeSelect.value = data.mode_config.cube_key || cubeSelect.value;
    packCount.value = String(data.mode_config.pack_count || packCount.value);
    cardsPerPack.value = String(data.mode_config.cards_per_pack || cardsPerPack.value);
  }
}

function populateCubeOptions(cubes) {
  if (!cubeSelect) return;
  cubeSelect.innerHTML = cubes
    .map((cube) => `<option value="${cube.key}">${cube.title}</option>`)
    .join("\n");
}

function renderDraftPack(data) {
  if (!draftGrid || !draftState || !draftPicked) return;
  const cards = Array.isArray(data.cards) ? data.cards : [];
  const packId = data.pack_id || "";
  const roundText = data.round && data.total_rounds ? `Ronda ${data.round} de ${data.total_rounds}` : '';
  const stepText = data.step ? `Pick ${data.step}` : '';

  const existingBanner = document.getElementById("pick-status-banner");
  if (existingBanner) {
    existingBanner.remove();
  }

  draftState.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem; background: var(--bg-surface-card); padding: 1.25rem 1.5rem; border-radius: var(--radius-lg); border: 1px solid var(--border-dim);">
      <div>
        <h2 style="font-size: 1.3rem; margin: 0; color: var(--accent-gold); display: flex; align-items: center; gap: 0.5rem;">
          🃏 <span>${roundText} — ${stepText}</span>
        </h2>
        <p style="margin: 0.2rem 0 0 0; font-size: 0.85rem; color: var(--text-muted);">
          Sobre actual: <code style="color: var(--text-main);">${packId}</code>
        </p>
      </div>
      <div style="text-align: right;">
        <span style="font-size: 1.2rem; font-weight: 800; color: var(--accent-purple);">${data.remaining}</span>
        <span style="font-size: 0.85rem; color: var(--text-muted); display: block;">cartas en sobre</span>
      </div>
    </div>
  `;

  currentDraftPackId = packId;
  currentDraftCards = cards.map((card) => ({ ...card, _pack_id: packId }));
  renderPickedCards();
  draftGrid.classList.remove("hidden");

  if (cards.length === 0) {
    draftGrid.innerHTML = `
      <div style="padding: 1.5rem; border: 1px dashed var(--border-dim); border-radius: var(--radius-lg); background: rgba(255,255,255,0.04); color: var(--text-muted);">
        No hay cartas disponibles en este sobre.
      </div>
    `;
    return;
  }

  draftGrid.innerHTML = cards
    .map((card, index) => {
      const backgroundStyle = card.image_url
        ? `background-image: url('${card.image_url}');`
        : "";

      return `
        <button type="button" data-index="${index}" class="card-tile card-image-card" style="${backgroundStyle}" title="Ver detalles de ${card.name}">
          ${card.image_url ? "" : `<span class=\"card-image-fallback\">${card.name}</span>`}
        </button>
      `;
    })
    .join("\n");
}

function renderDraftComplete(data) {
  if (!draftGrid || !draftState || !draftPicked) return;
  const myCollection = (data.collections && data.collections[currentUsername]) || [];

  draftState.innerHTML = `
    <div style="text-align: center; padding: 2rem; background: var(--bg-surface-card); border-radius: var(--radius-xl); border: 1px solid var(--accent-gold); box-shadow: var(--shadow-glow-gold);">
      <h2 style="font-size: 2rem; color: var(--accent-gold); margin-bottom: 0.5rem;">🎉 ¡Draft Completado con Éxito!</h2>
      <p style="color: var(--text-muted); font-size: 1.05rem;">Has seleccionado <strong>${myCollection.length} cartas</strong> para armar tu mazo.</p>
    </div>
  `;

  draftPickedList.innerHTML = myCollection
    .map((card, index) => {
      const imageHtml = card.image_url
        ? `<img src="${card.image_url}" alt="${card.name}" class="card-image" />`
        : `<div class="card-image card-image--placeholder">?</div>`;

      const metaLines = [];
      if (card.level) metaLines.push(`Nivel: ${card.level}`);
      if (card.race) metaLines.push(`Raza: ${card.race}`);
      if (card.atk) metaLines.push(`ATK: ${card.atk}`);
      if (card.def) metaLines.push(`DEF: ${card.def}`);

      return `
        <div class="card-tile" style="border-color: rgba(245, 158, 11, 0.3);">
          ${imageHtml}
          <div class="card-info">
            <strong>${card.name}</strong>
            <p class="card-meta">${[card.type || "Carta", ...metaLines].filter(Boolean).join(" · ")}</p>
            ${card.desc ? `<p class="card-desc">${card.desc}</p>` : ""}
          </div>
          <div class="card-actions">
            <span style="background: rgba(245, 158, 11, 0.15); color: var(--accent-gold); border: 1px solid rgba(245, 158, 11, 0.3); padding: 0.35rem 0.75rem; border-radius: var(--radius-sm); font-size: 0.8rem; font-weight: 700; text-align: center;">Drafteada</span>
          </div>
        </div>
      `;
    })
    .join("\n");

  if (myCollection.length > 0) {
    draftPicked.classList.remove("hidden");
    btnTogglePickedCards.textContent = `▶ Mis cartas elegidas (${myCollection.length})`;
    draftPickedList.classList.add("hidden");
  } else {
    draftPicked.classList.add("hidden");
  }

  btnBackDraft.classList.remove("hidden");
}

function renderPickedCards() {
  if (!draftPicked || !draftPickedList) return;

  if (currentPickedCards.length === 0) {
    draftPicked.classList.add("hidden");
    draftPickedList.innerHTML = "";
    draftPickedList.classList.add("hidden");
    return;
  }

  draftPicked.classList.remove("hidden");
  btnTogglePickedCards.textContent = `▶ Mis cartas elegidas (${currentPickedCards.length})`;
  draftPickedList.innerHTML = currentPickedCards
    .map((card, index) => {
      const imageHtml = card.image_url
        ? `<img src="${card.image_url}" alt="${card.name}" class="picked-card-thumb" />`
        : `<div class="picked-card-thumb picked-card-thumb--fallback">${card.name}</div>`;
      const description = card.desc ? card.desc : "Sin descripción disponible.";

      return `
        <button type="button" data-picked-index="${index}" class="picked-card-row" title="Ver detalles de ${card.name}">
          <div class="picked-card-thumb-wrapper">${imageHtml}</div>
          <div class="picked-card-info">
            <strong>${card.name}</strong>
            <p>${description}</p>
          </div>
        </button>
      `;
    })
    .join("");
  draftPickedList.classList.add("hidden");
}


function updateLobbyControls(players, host) {
  isHost = host === currentUsername;
  const startButton = document.getElementById("btn-start-game");
  const canStart = isHost && playersAllReady(players);

  if (canStart) {
    startButton.classList.remove("hidden");
  } else {
    startButton.classList.add("hidden");
  }
}

document.addEventListener("click", (event) => {
  const target = event.target;

  const imageCardButton = target.closest(".card-image-card, .card-image-button");
  if (imageCardButton && imageCardButton.dataset.index != null) {
    const index = Number(imageCardButton.dataset.index);
    const card = currentDraftCards[index];
    if (card) {
      openCardDetailModal(card);
    }
    return;
  }

  const togglePickedButton = target.closest("#btn-toggle-picked-cards");
  if (togglePickedButton) {
    if (!draftPickedList || !btnTogglePickedCards) return;
    const isHidden = draftPickedList.classList.toggle("hidden");
    const count = currentPickedCards.length;
    btnTogglePickedCards.textContent = isHidden
      ? `▶ Mis cartas elegidas (${count})`
      : `▼ Mis cartas elegidas (${count})`;
    return;
  }

  const pickedCardRow = target.closest(".picked-card-row");
  if (pickedCardRow && pickedCardRow.dataset.pickedIndex != null) {
    const index = Number(pickedCardRow.dataset.pickedIndex);
    const card = currentPickedCards[index];
    if (card) {
      openCardDetailModal(card);
    }
    return;
  }

  const pickedCardButton = target.closest(".picked-card-thumb, .card-thumb");
  if (pickedCardButton && pickedCardButton.dataset.pickedIndex != null) {
    const index = Number(pickedCardButton.dataset.pickedIndex);
    const card = currentPickedCards[index];
    if (card) {
      openCardDetailModal(card);
    }
    return;
  }

  if (target.matches(".btn-pick-card")) {
    const packId = target.dataset.pack;
    const cardName = target.dataset.card;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: "draft_pick_card", pack_id: packId, card_name: cardName }));
    }
  }

  if (target.matches("#modal-close") || target.matches(".modal-overlay")) {
    closeCardDetailModal();
  }
});

function openCardDetailModal(card) {
  if (!cardDetailModal) return;

  cardDetailModal.classList.remove("hidden");
  cardDetailModal.setAttribute("aria-hidden", "false");
  modalCardName.textContent = card.name || "Carta desconocida";
  modalCardType.textContent = card.type ? `Tipo: ${card.type}` : "Tipo: desconocido";

  const subtypeParts = [];
  if (card.race) subtypeParts.push(card.race);
  if (card.attribute) subtypeParts.push(card.attribute);
  if (card.frameType) subtypeParts.push(card.frameType);
  modalCardSubtype.textContent = subtypeParts.length > 0
    ? `Subtipo: ${subtypeParts.join(" · ")}`
    : "Subtipo: desconocido";

  const statLines = [];
  if (card.level) statLines.push(`Nivel: ${card.level}`);
  if (card.atk) statLines.push(`ATK: ${card.atk}`);
  if (card.def) statLines.push(`DEF: ${card.def}`);
  modalCardStats.textContent = statLines.join(" · ") || "";

  if (card.desc) {
    modalCardDesc.innerHTML = card.desc.replace(/\n/g, "<br />");
  } else {
    modalCardDesc.textContent = "Sin descripción disponible.";
  }

  modalCardImage.textContent = "";
  if (card.image_url) {
    modalCardImage.style.backgroundImage = `url('${card.image_url}')`;
  } else {
    modalCardImage.style.backgroundImage = "none";
    modalCardImage.textContent = "Sin imagen";
  }

  const canPick = currentDraftPackId && currentDraftCards.some((packCard) => packCard.name === card.name);
  currentDetailCard = card;
  const actionArea = document.getElementById("modal-card-actions");
  if (actionArea) {
    actionArea.innerHTML = canPick
      ? `<button type="button" class="btn-pick-card" data-pack="${currentDraftPackId}" data-card="${card.name}">Elegir esta carta</button>`
      : "";
  }
}

function closeCardDetailModal() {
  if (!cardDetailModal) return;
  cardDetailModal.classList.add("hidden");
  cardDetailModal.setAttribute("aria-hidden", "true");
  modalCardImage.style.backgroundImage = "none";
  modalCardImage.textContent = "";
}

function setConnectionStatus(text, type) {
  const el = document.getElementById("connection-status");
  el.textContent = text;
  el.className   = `conn-status ${type}`;
}

function updateReadyButton() {
  const btn = document.getElementById("btn-ready");
  btn.textContent = isReady ? "Cancelar ready ✗" : "Listo ✓";
  btn.classList.toggle("active", isReady);
}

function showScreen(name) {
  screenHome.classList.toggle("hidden",  name !== "home");
  screenLobby.classList.toggle("hidden", name !== "lobby");
  screenMode.classList.toggle("hidden",  name !== "mode");
  screenDraft.classList.toggle("hidden", name !== "draft");
}
