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
    this.sessionClient = null;
    this.markedCardKeys = new Set();
  }

  resetState() {
    this.currentDraftCards = [];
    this.currentPickedCards = [];
    this.currentDraftPackId = null;
    this.currentDetailCard = null;
    this.lastCompletedCollection = [];
    this.sessionClient = null;
    this.markedCardKeys = new Set();
  }

  renderConfigFields(containerEl, data, isHost) {
    const cubes = data.available_cubes || [];

    const cubeSelect = document.getElementById("cube-select");
    const packCount = document.getElementById("pack-count");
    const cardsPerPack = document.getElementById("cards-per-pack");

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
    this.sessionClient = sessionClient;

    switch (event) {
      case "session_state":
        if (data.draft_state) {
          const ds = data.draft_state;
          this.currentPickedCards = ds.collection || [];
          this.renderPickedDrawer(sessionClient);

          if (ds.finished) {
            showScreen("draft");
            document.getElementById("draft-subtitle").textContent = "Draft finalizado";
            document.getElementById("draft-state").textContent = "Todas las rondas han completado. Revisa las colecciones de cartas.";
            this.renderDraftResults(ds.collections, sessionClient, isHost);
          } else {
            showScreen("draft");
            if (ds.has_picked_this_step) {
              document.getElementById("draft-subtitle").textContent = `Ronda ${ds.round} / ${ds.total_rounds} — Paso ${ds.step}`;
              document.getElementById("draft-state").textContent = `Carta elegida. Esperando a los demás jugadores... (${ds.picked_count}/${ds.total_players})`;
              document.getElementById("draft-grid").innerHTML = `
                <div class="card empty-pack-msg" style="grid-column: 1 / -1; text-align: center; padding: 2rem;">
                  <h3>Carta elegida ✓</h3>
                  <p>Esperando a que el resto de los jugadores completen su selección... <strong>(${ds.picked_count}/${ds.total_players})</strong></p>
                </div>
              `;
            } else if (ds.current_pack) {
              this.currentDraftPackId = ds.current_pack.pack_id;
              this.currentDraftCards = ds.current_pack.cards || [];
              document.getElementById("draft-subtitle").textContent = `Ronda ${ds.round} / ${ds.total_rounds} — Paso ${ds.step}`;
              document.getElementById("draft-state").textContent = `Selecciona 1 carta de las ${this.currentDraftCards.length} restantes`;
              this.renderPackCards(this.currentDraftCards, sessionClient);
            }
          }
        }
        return true;

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
        this.renderPickedDrawer(sessionClient);
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
        this.renderPickedDrawer(sessionClient);
        return true;

      case "draft_step_progress":
        if (data.picker !== sessionClient.currentUsername) {
          logEvent(`${data.picker} ha realizado su selección (${data.picked_count}/${data.total_players})`);
        }
        {
          const stateEl = document.getElementById("draft-state");
          if (stateEl && stateEl.textContent.includes("Esperando")) {
            stateEl.textContent = `Carta elegida. Esperando a los demás jugadores... (${data.picked_count}/${data.total_players})`;
          }
          const waitMsg = document.querySelector(".empty-pack-msg p");
          if (waitMsg) {
            waitMsg.innerHTML = `Esperando a que el resto de los jugadores completen su selección... <strong>(${data.picked_count}/${data.total_players})</strong>`;
          }
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

  /**
   * Renderiza las cartas del sobre activo mostrando únicamente la imagen entera como marco clickeable.
   */
  renderPackCards(cards, sessionClient) {
    const grid = document.getElementById("draft-grid");
    if (!grid) return;
    grid.innerHTML = "";

    cards.forEach((card) => {
      const cardEl = document.createElement("div");
      cardEl.className = "draft-card-only-img";
      const cardKey = card.draft_card_key;
      if (cardKey && this.markedCardKeys.has(cardKey)) cardEl.classList.add("is-marked");
      cardEl.dataset.draftCardKey = cardKey || "";

      if (card.image_url) {
        cardEl.innerHTML = `<img src="${card.image_url}" alt="${card.name}" class="card-image-full" loading="lazy" />`;
      } else {
        cardEl.innerHTML = `<div class="card-image-fallback-full"><span>${card.name}</span></div>`;
      }

      cardEl.addEventListener("click", () => {
        this.openCardModal(card, sessionClient, true);
      });

      grid.appendChild(cardEl);
    });
  }

  /**
   * Renderiza el apartado inferior de cartas elegidas con botón desplegable y miniaturas interactiva.
   */
  renderPickedDrawer(sessionClient) {
    const drawer = document.getElementById("draft-picked");
    const list = document.getElementById("draft-picked-list");
    const toggleBtn = document.getElementById("btn-toggle-picked-cards");
    if (!drawer || !list) return;

    if (this.currentPickedCards.length > 0) {
      drawer.classList.remove("hidden");
    }

    if (toggleBtn) {
      toggleBtn.innerHTML = `Mis cartas elegidas <span class="draft-picked-count">${this.currentPickedCards.length}</span><span class="draft-picked-chevron" aria-hidden="true">⌄</span>`;
    }

    list.innerHTML = "";

    if (this.currentPickedCards.length === 0) {
      list.innerHTML = `<div style="padding: 1rem; text-align: center; color: var(--text-muted); font-size: 0.9rem;">Aún no has elegido ninguna carta.</div>`;
      return;
    }

    this.currentPickedCards.forEach((c, index) => {
      const item = document.createElement("article");
      item.className = "picked-card-item";
      const stats = [
        c.type,
        c.race,
        c.level !== undefined && c.level !== null ? `Nivel ${c.level} ★` : null,
        c.atk !== undefined && c.atk !== null ? `ATK ${c.atk}` : null,
        c.def !== undefined && c.def !== null ? `DEF ${c.def}` : null,
      ].filter(Boolean).join(" · ");
      const nameButton = document.createElement("button");
      nameButton.className = "picked-card-name";
      nameButton.type = "button";
      nameButton.setAttribute("aria-expanded", "false");
      nameButton.setAttribute("aria-controls", `picked-card-detail-${index}`);
      const name = document.createElement("span");
      name.textContent = c.name || "Carta sin nombre";
      const chevron = document.createElement("span");
      chevron.className = "picked-card-chevron";
      chevron.setAttribute("aria-hidden", "true");
      chevron.textContent = "⌄";
      nameButton.append(name, chevron);

      const detail = document.createElement("div");
      detail.className = "picked-card-detail hidden";
      detail.id = `picked-card-detail-${index}`;
      let image;
      if (c.image_url) {
        image = document.createElement("img");
        image.src = c.image_url;
        image.alt = c.name || "Carta";
        image.loading = "lazy";
        image.className = "picked-card-detail-image";
      } else {
        image = document.createElement("div");
        image.className = "picked-card-detail-image picked-card-detail-fallback";
        image.textContent = c.name || "Carta sin imagen";
      }
      const info = document.createElement("div");
      info.className = "picked-card-detail-info";
      const wikiLink = document.createElement("a");
      wikiLink.className = "picked-card-wiki-link";
      wikiLink.href = `https://yugioh.fandom.com/wiki/${encodeURIComponent(c.name || "")}`;
      wikiLink.target = "_blank";
      wikiLink.rel = "noopener noreferrer";
      wikiLink.setAttribute("aria-label", `Abrir ${c.name || "la carta"} en Yu-Gi-Oh! Wiki`);
      wikiLink.title = "Ver carta en Yu-Gi-Oh! Wiki";
      wikiLink.textContent = "🌐";
      info.appendChild(wikiLink);
      if (stats) {
        const meta = document.createElement("p");
        meta.className = "picked-card-detail-meta";
        meta.textContent = stats;
        info.appendChild(meta);
      }
      if (c.desc) {
        const description = document.createElement("p");
        description.className = "picked-card-detail-desc";
        description.textContent = c.desc;
        info.appendChild(description);
      }
      detail.append(image, info);
      item.append(nameButton, detail);
      nameButton.addEventListener("click", () => {
        const opening = detail.classList.contains("hidden");
        detail.classList.toggle("hidden", !opening);
        nameButton.setAttribute("aria-expanded", String(opening));
      });
      list.appendChild(item);
    });
  }

  renderDraftResults(collections, sessionClient, isHost) {
    const grid = document.getElementById("draft-grid");
    if (!grid) return;

    const myCollection = collections[sessionClient.currentUsername] || [];
    this.currentPickedCards = myCollection;
    this.renderPickedDrawer(sessionClient);
    const pickedDrawer = document.getElementById("draft-picked");
    if (pickedDrawer) pickedDrawer.classList.add("hidden");
    const names = myCollection.map((card) => card.name).filter(Boolean).join("\n");
    grid.innerHTML = `
      <section class="draft-results-simple">
        <h2>Resumen de tus cartas (${myCollection.length})</h2>
        <p>Un nombre por línea. Puedes seleccionar el texto o copiar la lista completa.</p>
        <textarea class="draft-results-names" aria-label="Nombres de tus cartas" wrap="off" readonly></textarea>
        <button class="btn-primary draft-results-copy" type="button">Copiar nombres</button>
        <span class="draft-results-copy-status" role="status" aria-live="polite"></span>
      </section>`;

    const namesField = grid.querySelector(".draft-results-names");
    const copyButton = grid.querySelector(".draft-results-copy");
    const copyStatus = grid.querySelector(".draft-results-copy-status");
    namesField.value = names;
    copyButton.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(names);
        copyStatus.textContent = "Copiado al portapapeles.";
      } catch {
        namesField.focus();
        namesField.select();
        copyStatus.textContent = "Texto seleccionado; cópialo desde aquí.";
      }
    });

    const btnBack = document.getElementById("btn-back-to-lobby-draft");
    if (btnBack) btnBack.classList.remove("hidden");
  }

  openCardModal(card, sessionClient, allowPick = true) {
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

    if (allowPick) {
      actionsEl.innerHTML = `
        <button id="btn-modal-pick-card" class="btn-primary" style="width: 100%;">Elegir esta carta 🎴</button>
      `;

      const markButton = document.createElement("button");
      markButton.className = "btn-modal-mark-card";
      markButton.type = "button";
      const updateMarkButton = () => {
        const marked = Boolean(card.draft_card_key && this.markedCardKeys.has(card.draft_card_key));
        markButton.textContent = marked ? "★ Marcada" : "☆ Marcar carta";
        markButton.setAttribute("aria-pressed", String(marked));
      };
      updateMarkButton();
      markButton.addEventListener("click", () => {
        if (!card.draft_card_key) return;
        if (this.markedCardKeys.has(card.draft_card_key)) {
          this.markedCardKeys.delete(card.draft_card_key);
        } else {
          this.markedCardKeys.add(card.draft_card_key);
        }
        const cardEl = [...document.querySelectorAll(".draft-card-only-img")]
          .find((element) => element.dataset.draftCardKey === card.draft_card_key);
        if (cardEl) cardEl.classList.toggle("is-marked", this.markedCardKeys.has(card.draft_card_key));
        updateMarkButton();
      });
      actionsEl.appendChild(markButton);

      document.getElementById("btn-modal-pick-card").onclick = () => {
        this.closeCardModal();
        sessionClient.send({
          action: "draft_pick_card",
          card_name: card.name,
        });
      };
    } else {
      actionsEl.innerHTML = `
        <div style="padding: 0.6rem; text-align: center; color: var(--accent-gold); background: rgba(245, 158, 11, 0.1); border: 1px solid var(--border-gold); border-radius: var(--radius-sm); font-size: 0.9rem; font-weight: 600;">
          Carta en colección ✓
        </div>
      `;
    }

    const wikiLink = document.createElement("a");
    wikiLink.className = "picked-card-wiki-link modal-card-wiki-link";
    wikiLink.href = `https://yugioh.fandom.com/wiki/${encodeURIComponent(card.name || "")}`;
    wikiLink.target = "_blank";
    wikiLink.rel = "noopener noreferrer";
    wikiLink.setAttribute("aria-label", `Abrir ${card.name || "la carta"} en Yu-Gi-Oh! Wiki`);
    wikiLink.title = "Ver carta en Yu-Gi-Oh! Wiki";
    wikiLink.textContent = "🌐";
    actionsEl.appendChild(wikiLink);

    modal.classList.remove("hidden");
  }

  closeCardModal() {
    const modal = document.getElementById("card-detail-modal");
    if (modal) modal.classList.add("hidden");
  }
}
