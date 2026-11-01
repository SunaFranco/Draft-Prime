/**
 * js/core/ui.js — Gestión de la interfaz de usuario general
 */

const screenHome  = document.getElementById("screen-home");
const screenLobby = document.getElementById("screen-lobby");
const screenMode  = document.getElementById("screen-mode");
const screenDraft = document.getElementById("screen-draft");

const screens = {
  home:  screenHome,
  lobby: screenLobby,
  mode:  screenMode,
  draft: screenDraft,
};

export function showScreen(name) {
  Object.keys(screens).forEach((key) => {
    if (screens[key]) {
      screens[key].classList.toggle("hidden", key !== name);
    }
  });
}

export function setConnectionStatus(text, type = "") {
  const el = document.getElementById("connection-status");
  if (!el) return;
  el.textContent = text;
  el.className = "conn-status " + type;
}

export function logEvent(text) {
  const list = document.getElementById("event-log");
  if (!list) return;
  const item = document.createElement("li");
  item.textContent = text;
  list.prepend(item);
}

export function renderPlayers(players, _host, currentUsername) {
  const grid = document.getElementById("players-grid");
  if (!grid) return;

  grid.innerHTML = "";
  const playerList = Array.isArray(players) ? players : [];

  for (let i = 0; i < 4; i++) {
    const p = playerList[i];
    const card = document.createElement("div");

    if (p) {
      const isMe = p.username === currentUsername;
      card.className = `player-card ${p.ready ? "ready" : ""} ${p.connected ? "" : "disconnected"}`;

      card.innerHTML = `
        <div class="player-name">
          ${p.username}
          ${p.is_admin ? '<span class="badge host">Admin</span>' : ""}
          ${isMe ? '<span class="badge me">Tú</span>' : ""}
        </div>
        <div class="player-status">
          ${p.connected ? (p.ready ? "✓ Listo" : "Esperando...") : "❌ Desconectado"}
        </div>
      `;
    } else {
      card.className = "player-card empty";
      card.innerHTML = `<span class="empty-label">Slot libre</span>`;
    }

    grid.appendChild(card);
  }
}
