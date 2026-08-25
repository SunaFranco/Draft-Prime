/**
 * modes/cube_draft_yugioh/yugioh_draft.js — UI del modo Cube Draft Yu-Gi-Oh
 */

import { BaseGameModeUI } from "../base_mode.js";
import { showScreen, logEvent } from "../../js/core/ui.js";

export class YugiohDraftModeUI extends BaseGameModeUI {
  constructor() {
    super("cube_draft_yugioh", "Cube Draft (Yugioh)");
    this.currentDraftCards = [];
    this.currentPickedCards = [];
    this.currentDraftPackId = null;
    this.currentDetailCard = null;
    this.lastCompletedCollection = [];
  }

  resetState() {
    this.currentDraftCards = [];
    this.currentPickedCards = [];
    this.currentDraftPackId = null;
    this.currentDetailCard = null;
    this.lastCompletedCollection = [];
  }

  renderConfigFields(containerEl, data, isHost) {
    const cubes = data.available_cubes || [];

    const cubeSelect = document.getElementById("cube-select");
    const packCount = document.getElementById("pack-count");
    const cardsPerPack = document.getElementById("cards-per-pack");

    // Mostrar controles de sobres/cubes
    [cubeSelect, packCount, cardsPerPack].forEach((el) => {
      if (el) {
        el.disabled = !isHost;
        const label = document.querySelector(`label[for="${el.id}"]`);
        if (label) label.style.display = "";
        el.style.display = "";
      }
    });

    if (cubeSelect) {
      cubeSelect.innerHTML = cubes
        .map((c) => `<option value="${c.key}">${c.title}</option>`)
        .join("");
    }
  }

  readConfigFields(containerEl) {
    const cubeSelect = document.getElementById("cube-select");
    const packCount = document.getElementById("pack-count");
    const cardsPerPack = document.getElementById("cards-per-pack");

    return {
      cube_key: cubeSelect ? cubeSelect.value : "",
      pack_count: packCount ? parseInt(packCount.value, 10) : 3,
      cards_per_pack: cardsPerPack ? parseInt(cardsPerPack.value, 10) : 5,
    };
  }

  handleEvent(event, data, context) {
    const { sessionClient, isHost } = context;

    switch (event) {
      case "draft_started":
        showScreen("draft");
        logEvent("🎲 ¡El draft ha comenzado!");
        document.getElementById("draft-subtitle").textContent = "Abriendo el primer sobre...";
        document.getElementById("draft-state").textContent = "Preparando cartas...";
        return true;

      case "draft_open_pack":
        this.currentDraftPackId = data.pack_id;
        this.currentDraftCards = data.cards || [];
        showScreen("draft");
        document.getElementById("draft-subtitle").textContent = `Ronda ${data.round} / ${data.total_rounds} — Paso ${data.step}`;
        document.getElementById("draft-state").textContent = `Selecciona 1 carta de las ${data.remaining} restantes`;
        this.renderPackCards(this.currentDraftCards, sessionClient);
        return true;

      case "draft_pick_confirmed":
        logEvent(`Has elegido: ${data.card.name}`);
        this.currentPickedCards = data.collection || [];
        document.getElementById("draft-state").textContent = "Carta elegida. Esperando a los demás jugadores...";
        document.getElementById("draft-grid").innerHTML = `
          <div class="card empty-pack-msg" style="grid-column: 1 / -1; text-align: center; padding: 2rem;">
            <h3>Carta elegida ✓</h3>
            <p>Esperando a que el resto de los jugadores completen su selección...</p>
          </div>
        `;
        this.renderPickedDrawer();
        return true;

      case "draft_step_progress":
        if (data.picker !== sessionClient.currentUsername) {
          logEvent(`${data.picker} ha realizado su selección (${data.picked_count}/${data.total_players})`);
        }
        return true;

      case "draft_round_start":
        logEvent(`--- INICIO DE LA RONDA ${data.round} DE ${data.total_rounds} ---`);
        return true;

      case "draft_complete":
        logEvent("🎉 ¡El draft ha finalizado!");
        showScreen("draft");
        document.getElementById("draft-subtitle").textContent = "Draft finalizado";
        document.getElementById("draft-state").textContent = "Todas las rondas han completado. Revisa las colecciones de cartas.";
        this.renderDraftResults(data.collections, sessionClient, isHost);
        return true;
    }

    return false;
  }

  renderPackCards(cards, sessionClient) {
    const grid = document.getElementById("draft-grid");
    if (!grid) return;
    grid.innerHTML = "";

    cards.forEach((card) => {
      const cardEl = document.createElement("div");
      cardEl.className = "card draft-card";

      const hasImg = Boolean(card.image_url);
      const imgHtml = hasImg
        ? `<img class="draft-card-img" src="${card.image_url}" alt="${card.name}" loading="lazy" />`
        : `<div class="draft-card-fallback">${card.name}</div>`;

      cardEl.innerHTML = `
        <div class="draft-card-preview">${imgHtml}</div>
        <div class="draft-card-body">
          <div class="draft-card-title">${card.name}</div>
          <div class="draft-card-type">${card.type || "Yu-Gi-Oh!"}</div>
        </div>
      `;

      cardEl.addEventListener("click", () => {
        this.openCardModal(card, sessionClient);
      });

      grid.appendChild(cardEl);
    });
  }

  renderPickedDrawer() {
    const drawer = document.getElementById("draft-picked");
    const list = document.getElementById("draft-picked-list");
    if (!drawer || !list) return;

    if (this.currentPickedCards.length > 0) {
      drawer.classList.remove("hidden");
    }

    list.innerHTML = "";
    this.currentPickedCards.forEach((c) => {
      const item = document.createElement("div");
      item.className = "draft-picked-item";
      item.textContent = c.name;
      list.appendChild(item);
    });
  }

  renderDraftResults(collections, sessionClient, isHost) {
    const grid = document.getElementById("draft-grid");
    if (!grid) return;

    const myCollection = collections[sessionClient.currentUsername] || [];
    this.currentPickedCards = myCollection;
    this.renderPickedDrawer();

    let html = `
      <div class="card results-card" style="grid-column: 1 / -1; padding: 2rem;">
        <h2>🏆 Resumen de Cartas Elegidas</h2>
        <p style="color: var(--muted); margin-bottom: 1.5rem;">A continuación se muestran los mazos drafteados por cada jugador:</p>
        <div class="collections-grid" style="display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));">
    `;

    Object.entries(collections).forEach(([uname, cardList]) => {
      html += `
        <div class="card" style="background: rgba(255,255,255,0.03); border: 1px solid var(--border);">
          <h3>${uname} (${cardList.length} cartas)</h3>
          <ul style="max-height: 250px; overflow-y: auto; font-size: 0.9rem; margin-top: 0.5rem; padding-left: 1.2rem;">
            ${cardList.map((c) => `<li>${c.name}</li>`).join("")}
          </ul>
        </div>
      `;
    });

    html += `</div></div>`;
    grid.innerHTML = html;

    const btnBack = document.getElementById("btn-back-to-lobby-draft");
    if (btnBack) btnBack.classList.remove("hidden");
  }

  openCardModal(card, sessionClient) {
    this.currentDetailCard = card;

    const modal = document.getElementById("card-detail-modal");
    const nameEl = document.getElementById("modal-card-name");
    const typeEl = document.getElementById("modal-card-type");
    const subtypeEl = document.getElementById("modal-card-subtype");
    const statsEl = document.getElementById("modal-card-stats");
    const descEl = document.getElementById("modal-card-desc");
    const imgEl = document.getElementById("modal-card-image");
    const actionsEl = document.getElementById("modal-card-actions");

    if (!modal) return;

    nameEl.textContent = card.name || "Carta";
    typeEl.textContent = card.type ? `Tipo: ${card.type}` : "";
    subtypeEl.textContent = card.race ? `Raza / Atributo: ${card.race} ${card.attribute ? "/ " + card.attribute : ""}` : "";

    let statsStr = "";
    if (card.level !== undefined && card.level !== null) statsStr += `Nivel: ${card.level} ★  `;
    if (card.atk !== undefined && card.atk !== null) statsStr += `ATK: ${card.atk}  `;
    if (card.def !== undefined && card.def !== null) statsStr += `DEF: ${card.def}`;
    statsEl.textContent = statsStr;

    descEl.textContent = card.desc || "Sin descripción.";

    if (card.image_url) {
      imgEl.innerHTML = `<img src="${card.image_url}" alt="${card.name}" style="max-width: 100%; border-radius: 8px;" />`;
    } else {
      imgEl.innerHTML = `<div class="draft-card-fallback" style="padding: 2rem;">${card.name}</div>`;
    }

    actionsEl.innerHTML = `
      <button id="btn-modal-pick-card" class="btn-primary" style="width: 100%;">Elegir esta carta 🎴</button>
    `;

    document.getElementById("btn-modal-pick-card").onclick = () => {
      this.closeCardModal();
      sessionClient.send({
        action: "draft_pick_card",
        card_name: card.name,
      });
    };

    modal.classList.remove("hidden");
  }

  closeCardModal() {
    const modal = document.getElementById("card-detail-modal");
    if (modal) modal.classList.add("hidden");
  }
}
