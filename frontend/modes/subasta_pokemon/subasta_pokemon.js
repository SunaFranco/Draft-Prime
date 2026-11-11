/**
 * frontend/modes/subasta_pokemon/subasta_pokemon.js — UI Controller para Subasta Pokémon
 */

import { BaseGameModeUI } from "../base_mode.js";
import { showScreen } from "../../js/core/ui.js";
import { getMoveTextEs, getAbilityTextEs } from "../../js/showdown_text_es.js";
import {
  renderConfigForm,
  readConfigForm,
  renderAuctionView,
  renderTurnEventsView,
  renderExportView,
  renderAdminAndStandingsView,
  renderMyPokemonInventory,
  renderFarmingView,
  POKEMON_CARD_COLORS,
  formatMoneyCompact,
  NATURE_EFFECTS,
  formatNature,
  getTmMoveName,
  checkTmCompatibility,
  buildItemSpriteUrl,
  buildPokemonSpriteMarkup,
  showBoxOddsModal,
} from "./subasta_ui_components.js";

const ROULETTE_ITEMS = [
  "Leftovers", "Life Orb", "Choice Band", "Choice Specs", "Choice Scarf",
  "Focus Sash", "Assault Vest", "Heavy-Duty Boots", "Eviolite", "Rocky Helmet",
  "Capsula Habilidad", "MT Earthquake", "MT Ice Beam", "MT Flamethrower",
  "MT Thunderbolt", "MT Psychic", "MT Shadow Ball", "MT Protect",
  "MT Substitute", "MT Swords Dance", "MT Calm Mind",
];

function rouletteItemName(item) {
  if (typeof item === "object" && item !== null) {
    return item.name || item.display || "";
  }
  return String(item || "").startsWith("MT ") ? String(item).slice(3) : String(item || "");
}

function rouletteItemImage(item) {
  if (typeof item === "object" && item !== null && item.image) {
    return item.image;
  }
  const rawName = typeof item === "object" && item !== null ? item.name : item;
  return buildItemSpriteUrl(rawName);
}

function buildRouletteItems(count) {
  return Array.from({ length: count }, () => ROULETTE_ITEMS[Math.floor(Math.random() * ROULETTE_ITEMS.length)]);
}

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

const ROULETTE_SPIN_DURATION_MS = 3000;
const ROULETTE_RESULT_PAUSE_MS = 800;

async function playMysteryBoxRoulette(boxData, onComplete) {
  const overlay = document.createElement("div");
  overlay.className = "event-roulette-overlay";
  overlay.innerHTML = `
    <div class="event-roulette-modal">
      <div class="event-roulette-kicker">🎁 ${boxData.store_title || "TIENDA DEL PRIMER AÑO"}</div>
      <h2>${boxData.box_name || "Caja Misteriosa"}</h2>
      <div class="event-roulette-stage">
        <div class="event-roulette-pointer">▼</div>
        <div class="event-roulette-window"><div class="event-roulette-strip"></div></div>
      </div>
      <p class="event-roulette-status">La suerte está girando...</p>
      <div class="event-roulette-actions" style="margin-top: 1.25rem; display: none;">
        <button type="button" class="btn btn-primary btn-large btn-roulette-close">¡Genial!</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  const strip = overlay.querySelector(".event-roulette-strip");
  const rouletteWindow = overlay.querySelector(".event-roulette-window");
  const status = overlay.querySelector(".event-roulette-status");
  const actionsEl = overlay.querySelector(".event-roulette-actions");
  const closeBtn = overlay.querySelector(".btn-roulette-close");

  const pool = Array.isArray(boxData.pool) && boxData.pool.length > 0 ? boxData.pool : ROULETTE_ITEMS;
  const reward = boxData.reward || { name: "Recompensa", display: "Recompensa" };

  const targetIndex = 22 + Math.floor(Math.random() * 5);
  const options = [
    ...Array.from({ length: targetIndex }, () => pool[Math.floor(Math.random() * pool.length)]),
    reward,
    ...Array.from({ length: 6 }, () => pool[Math.floor(Math.random() * pool.length)]),
  ];

  strip.innerHTML = options.map((item, idx) => `
    <div class="event-roulette-slot" data-slot-index="${idx}">
      <img src="${rouletteItemImage(item)}" alt="" onerror="this.style.display='none'" />
      <span>${rouletteItemName(item)}</span>
    </div>
  `).join("");

  strip.classList.remove("event-roulette-strip--spinning");
  strip.style.transition = "none";
  strip.style.transform = "translateX(0)";
  void strip.offsetWidth;

  const targetOffset = targetIndex * 125 - (rouletteWindow.clientWidth / 2 - 62.5);
  strip.style.transition = `transform ${ROULETTE_SPIN_DURATION_MS}ms cubic-bezier(0.12, 0.7, 0.18, 1)`;
  strip.style.transform = `translateX(-${targetOffset}px)`;

  await wait(ROULETTE_SPIN_DURATION_MS);

  const winningSlot = strip.querySelector(`[data-slot-index="${targetIndex}"]`);
  if (winningSlot) {
    winningSlot.classList.add("is-winner");
  }

  status.innerHTML = `<span style="color: var(--accent-gold); font-size: 1.1rem; font-weight: bold;">Has obtenido: ${reward.display || rouletteItemName(reward)}</span>`;
  actionsEl.style.display = "block";

  const closeOverlay = () => {
    overlay.remove();
    if (onComplete) onComplete();
  };

  closeBtn.addEventListener("click", closeOverlay);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeOverlay();
  });
}

async function playEventRoulette(event, onComplete) {
  const rewards = event.granted_items?.length ? event.granted_items : [event.granted_item];
  const overlay = document.createElement("div");
  overlay.className = "event-roulette-overlay";
  overlay.innerHTML = `
    <div class="event-roulette-modal">
      <div class="event-roulette-kicker">RECOMPENSA DEL EVENTO</div>
      <h2>${event.title || "Ruleta de objetos"}</h2>
      <div class="event-roulette-stage">
        <div class="event-roulette-pointer">▼</div>
        <div class="event-roulette-window"><div class="event-roulette-strip"></div></div>
      </div>
      <p class="event-roulette-status">La suerte está girando...</p>
    </div>
  `;
  document.body.appendChild(overlay);
  const strip = overlay.querySelector(".event-roulette-strip");
  const rouletteWindow = overlay.querySelector(".event-roulette-window");
  const status = overlay.querySelector(".event-roulette-status");

  const pool = Array.isArray(event.roulette_pool) && event.roulette_pool.length > 0
    ? event.roulette_pool
    : ROULETTE_ITEMS;
  const buildItems = (count) => Array.from({ length: count }, () => pool[Math.floor(Math.random() * pool.length)]);

  for (let index = 0; index < rewards.length; index += 1) {
    const reward = rewards[index];
    const targetIndex = 18 + Math.floor(Math.random() * 5);
    const options = [
      ...buildItems(targetIndex),
      reward,
      ...buildItems(6),
    ];
    strip.innerHTML = options.map((item) => `
      <div class="event-roulette-slot">
        <img src="${rouletteItemImage(item)}" alt="" onerror="this.style.display='none'" />
        <span>${rouletteItemName(item)}</span>
      </div>
    `).join("");
    strip.classList.remove("event-roulette-strip--spinning");
    strip.style.transition = "none";
    strip.style.transform = "translateX(0)";
    void strip.offsetWidth;
    const targetOffset = targetIndex * 125 - (rouletteWindow.clientWidth / 2 - 62.5);
    strip.style.transition = `transform ${ROULETTE_SPIN_DURATION_MS}ms cubic-bezier(0.12, 0.7, 0.18, 1)`;
    strip.style.transform = `translateX(-${targetOffset}px)`;
    await wait(ROULETTE_SPIN_DURATION_MS);
    status.textContent = rewards.length > 1 ? `Premio ${index + 1} de ${rewards.length}: ${rouletteItemName(reward)}` : `Has obtenido: ${rouletteItemName(reward)}`;
    await wait(ROULETTE_RESULT_PAUSE_MS);
  }

  overlay.remove();
  onComplete();
}

async function playTrafficAnimation(finalAmount, onComplete) {
  const overlay = document.createElement("div");
  overlay.className = "event-roulette-overlay";
  overlay.innerHTML = `
    <div class="event-roulette-modal">
      <div class="event-roulette-kicker">🕶️ TRÁFICO POKÉMON</div>
      <h2>💰 Vendiendo Pokémon...</h2>
      <div class="traffic-counter" style="font-size: 2.5rem; font-weight: bold; color: #f59e0b; margin: 1.5rem 0; text-align: center;">
        $0K
      </div>
      <p class="event-roulette-status">Negociando el precio...</p>
    </div>
  `;
  document.body.appendChild(overlay);

  const counter = overlay.querySelector(".traffic-counter");
  const status = overlay.querySelector(".event-roulette-status");

  const step = 5000;
  const maxAmount = 125000;

  if (finalAmount === 0) {
    await wait(1800);
    counter.style.color = "#ef4444";
    status.innerHTML = `<span style="color: #ef4444; font-size: 1.1rem; font-weight: bold;">¡Te estafaron! No recibiste nada y perdiste tu Pokémon...</span>`;
  } else {
    // Animación notablemente más lenta para generar suspenso
    for (let current = step; current <= finalAmount; current += step) {
      counter.textContent = `$${formatMoneyCompact(current)}`;
      const progress = current / maxAmount;
      // Empieza en 350ms y se va ralentizando hasta ~950ms conforme sube el valor
      const delay = 350 + progress * 600;
      await wait(delay);
    }
    counter.textContent = `$${formatMoneyCompact(finalAmount)}`;
    counter.style.color = "#22c55e";
    status.innerHTML = `<span style="color: #22c55e; font-size: 1.1rem; font-weight: bold;">¡Vendido por $${formatMoneyCompact(finalAmount)}!</span>`;
  }

  await wait(3000);
  overlay.remove();
  onComplete();
}

async function playCoinflipAnimation(event, onAccept) {
  const won = event.coinflip_won === true;
  const amount = formatMoneyCompact(event.coinflip_amount || 0);
  const overlay = document.createElement("div");
  overlay.className = "event-roulette-overlay coinflip-overlay";
  overlay.innerHTML = `
    <div class="event-roulette-modal coinflip-modal">
      <div class="event-roulette-kicker">🪙 COINFLIP</div>
      <h2>¡La moneda está en el aire!</h2>
      <div class="coinflip-coin" aria-live="polite">🪙</div>
      <p class="event-roulette-status">Apostaste $${amount}</p>
    </div>
  `;
  document.body.appendChild(overlay);
  await wait(1900);

  const modal = overlay.querySelector(".coinflip-modal");
  modal.classList.add(won ? "coinflip-modal--won" : "coinflip-modal--lost");
  modal.querySelector("h2").textContent = won ? "¡Ganaste!" : "No hubo suerte";
  modal.querySelector(".coinflip-coin").textContent = won ? "🎉" : "💸";
  modal.querySelector(".event-roulette-status").textContent = won
    ? `Ganaste $${amount}`
    : `Perdiste $${amount}`;
  const acceptButton = document.createElement("button");
  acceptButton.className = "btn btn-primary btn-large";
  acceptButton.textContent = "Aceptar y continuar";
  acceptButton.addEventListener("click", () => {
    acceptButton.disabled = true;
    overlay.remove();
    onAccept();
  });
  modal.appendChild(acceptButton);
}

export class SubastaPokemonModeUI extends BaseGameModeUI {
  constructor() {
    super("subasta_pokemon", "Subasta (Pokemon)");
    this.latestState = null;
    this._lockedShowdownText = null;
    this._lockedShowdownStage = null;
    this._isRouletteSpinning = false;
    this._lastCoinflipAnimationKey = null;
    this._activePokemonBoxId = null;
    this._selectedPokemonIndex = null;
    this._pokemonColorStorageKey = null;
    this._pokemonCardColors = {};
    this._pokemonMoveUiStates = {};
    this._lastFusionResult = null;
    this._lastFusionFailureMessage = null;
  }

  renderConfigFields(containerEl, data, isHost) {
    const cubeSelect = document.getElementById("cube-select");
    const packCount = document.getElementById("pack-count");
    const cardsPerPack = document.getElementById("cards-per-pack");

    [cubeSelect, packCount, cardsPerPack].forEach((el) => {
      if (el) {
        el.style.display = "none";
        const label = document.querySelector(`label[for="${el.id}"]`);
        if (label) label.style.display = "none";
      }
    });

    const fieldsContainer = document.getElementById("mode-config-fields") || containerEl;
    renderConfigForm(fieldsContainer, data, isHost);
  }

  readConfigFields(containerEl) {
    const fieldsContainer = document.getElementById("mode-config-fields") || containerEl;
    return readConfigForm(fieldsContainer);
  }

  handleEvent(event, data, context) {
    if (event === "subasta_fusion_preview") {
      const container = document.getElementById("fusion-preview-results");
      if (container) {
        const entries = Array.isArray(data.pokemon) ? data.pokemon : [];
        container.replaceChildren();
        const combinations = document.createElement("p");
        combinations.textContent = entries.length
          ? `Combinaciones disponibles: ${(data.combinations || []).map((entry) => entry.types.join(" / ")).join(", ")}`
          : data.message || "No hay combinaciones disponibles para estos Pokémon.";
        container.appendChild(combinations);
        const fusionButton = document.getElementById("btn-fuse-pokemon");
        if (fusionButton) {
          fusionButton.dataset.hasCombinations = String(entries.length > 0);
          fusionButton.disabled = !entries.length || fusionButton.dataset.hasSplicers !== "true";
        }
        if (entries.length) {
          const list = document.createElement("ul");
          entries.forEach((entry) => {
            const row = document.createElement("li");
            row.textContent = `${entry.name} — ${((entry.probability || 0) * 100).toFixed(2)}%${entry.tier === "legendary" ? " (legendario)" : ""}`;
            list.appendChild(row);
          });
          if (data.failure_chance && data.failure_chance > 0) {
            const failRow = document.createElement("li");
            failRow.style.color = "#ef4444";
            failRow.textContent = `Fallo (se pierden ambos Pokémon) — ${(data.failure_chance * 100).toFixed(2)}%`;
            list.appendChild(failRow);
          }
          container.appendChild(list);
        }
      }
      return true;
    }
    if (event === "subasta_fusion_result") {
      const names = (data.sacrificed || []).join(" y ");
      if (data.failed || !data.pokemon) {
        this._lastFusionResult = null;
        this._lastFusionFailureMessage = data.message || "algo fallo y los dos pokemon fallecieron";
        this.renderFusionFailure(this._lastFusionFailureMessage);
      } else {
        this._lastFusionFailureMessage = null;
        this._lastFusionResult = data.pokemon;
        this.renderFusionResult(data.pokemon, `¡Fusión completada! ${names} se fusionaron.`);
      }
      return true;
    }
    if (event === "subasta_mystery_box_result") {
      playMysteryBoxRoulette(data, () => {
        this._isRouletteSpinning = false;
      });
      return true;
    }
    if (event === "error") {
      this._isRouletteSpinning = false;
    }
    if (event === "player_joined" || event === "player_left") {
      if (this.latestState && Array.isArray(data.players)) {
        this.latestState.connected_players = (data.players || [])
          .filter((player) => player.connected)
          .map((player) => player.username);
      }
      if (this.latestState) {
        this.renderCurrentStageView(this.latestState, context.sessionClient, context.isHost);
      }
      return false;
    }

    if (event === "subasta_state_update" || (event === "session_state" && data.draft_state)) {
      const state = event === "subasta_state_update" ? data : data.draft_state;
      if (!state || Object.keys(state).length === 0) return false;

      if (event === "session_state") {
        state.connected_players = (data.players || [])
          .filter((player) => player.connected)
          .map((player) => player.username);
      }
      this.latestState = state;
      this.renderCurrentStageView(state, context.sessionClient, context.isHost);
      return true;
    }
    return false;
  }

  renderFusionResult(pokemon, message = "") {
    const resultSlot = document.getElementById("fusion-result-slot");
    const resultArt = document.getElementById("fusion-result-art");
    const resultName = document.getElementById("fusion-result-name");
    const resultMessage = document.getElementById("fusion-result-message");
    if (!resultSlot || !resultArt || !resultName || !pokemon) return;

    resultSlot.classList.remove("has-failed");
    resultSlot.classList.add("has-pokemon");
    resultArt.innerHTML = buildPokemonSpriteMarkup(pokemon);
    resultName.textContent = pokemon.name || "Pokémon fusionado";
    if (resultMessage) {
      resultMessage.textContent = message || "Resultado de la fusión.";
      resultMessage.style.color = "";
    }
  }

  renderFusionFailure(message = "algo fallo y los dos pokemon fallecieron") {
    const resultSlot = document.getElementById("fusion-result-slot");
    const resultArt = document.getElementById("fusion-result-art");
    const resultName = document.getElementById("fusion-result-name");
    const resultMessage = document.getElementById("fusion-result-message");
    if (!resultSlot || !resultArt || !resultName) return;

    resultSlot.classList.remove("has-pokemon");
    resultSlot.classList.add("has-failed");
    resultArt.innerHTML = '<span style="font-size: 2rem;">💀</span>';
    resultName.textContent = "Fusión fallida";
    if (resultMessage) {
      resultMessage.textContent = message;
      resultMessage.style.color = "#ef4444";
    }
  }

  renderCurrentStageView(state, sessionClient, isHost) {
    showScreen("draft");
    const draftContainer = document.getElementById("screen-draft");
    if (!draftContainer) return;

    const colorStorageKey = `draft_prime_subasta_pokemon_colors:${sessionClient.currentSessionId}:${sessionClient.currentUsername}`;
    const sessionChanged = this._pokemonColorStorageKey !== colorStorageKey;
    if (sessionChanged) {
      this._pokemonColorStorageKey = colorStorageKey;
      this._pokemonCardColors = {};
      this._pokemonMoveUiStates = {};
      try {
        const savedColors = JSON.parse(localStorage.getItem(colorStorageKey) || "{}");
        if (savedColors && typeof savedColors === "object" && !Array.isArray(savedColors)) {
          this._pokemonCardColors = Object.fromEntries(
            Object.entries(savedColors).filter(([, colorId]) => Object.prototype.hasOwnProperty.call(POKEMON_CARD_COLORS, colorId))
          );
        }
      } catch (error) {
        console.warn("No se pudieron cargar los colores de Pokémon guardados:", error);
      }
    }

    if (!sessionChanged) draftContainer.querySelectorAll(".moves-selector-box").forEach((panel) => {
      const pokeIdx = panel.dataset.pokeIdx;
      const pokemon = state.my_data?.pokemon?.[Number(pokeIdx)];
      if (!pokemon || panel.dataset.mode === "closed") {
        delete this._pokemonMoveUiStates[pokeIdx];
        return;
      }
      this._pokemonMoveUiStates[pokeIdx] = {
        name: pokemon.name,
        mode: panel.dataset.mode,
        selectedMoves: Array.from(panel.querySelectorAll(".move-link.is-selected"))
          .map((move) => move.dataset.moveName),
      };
    });
    const bagItemState = Array.from(document.querySelectorAll(".bag-item-row")).map((item) => ({
      name: item.dataset.itemName,
      isOpen: item.open,
    }));

    const stage = state.stage || 2;
    if (this._lockedShowdownStage !== null && this._lockedShowdownStage !== stage) {
      this._lockedShowdownText = null;
      this._lockedShowdownStage = null;
    }
    const isTeamLocked = this._lockedShowdownStage === stage;

    let html = "";
    if ([2, 6, 10].includes(stage)) {
      // Subastas (Año 1, 2, 3)
      html = renderAuctionView(state, sessionClient, isHost);
    } else if ([3, 7, 11].includes(stage)) {
      // Eventos de Turno (Año 1, 2, 3)
      html = renderTurnEventsView(state, sessionClient, isHost);
    } else if ([4, 8, 12].includes(stage)) {
      // Exportación a Showdown (Año 1, 2, 3)
      html = renderExportView(state, sessionClient, isHost, this._lockedShowdownText, isTeamLocked);
    } else if ([5, 9].includes(stage)) {
      // Fase de Farmeo (Año 1, 2)
      html = renderFarmingView(state, sessionClient, isHost);
    } else {
      // Resultados y Administración (Etapa 13 o intermedia)
      html = renderAdminAndStandingsView(state, sessionClient, isHost);
    }

    const auctionStages = [2, 6, 10];
    const playerMoney = Number(state.my_data?.money);
    const balanceHtml = !auctionStages.includes(Number(stage))
      && state.my_data?.money !== null
      && state.my_data?.money !== undefined
      && Number.isFinite(playerMoney)
      ? `
        <div class="subasta-header subasta-player-balance">
          <span class="badge badge-success">💰 Mi Saldo: $${formatMoneyCompact(playerMoney)}</span>
        </div>
      `
      : "";

    const openModal = isTeamLocked ? null : document.querySelector(".inventory-modal-overlay.is-open");
    const currentlyOpenTarget = openModal ? openModal.dataset.modal : null;
    document.querySelectorAll("body > .inventory-modal-overlay").forEach((el) => el.remove());

    const boxes = state.my_data?.pokemon_boxes || [];
    const pokemon = state.my_data?.pokemon || [];
    if (!this._activePokemonBoxId || !boxes.some((box) => box.id === this._activePokemonBoxId)) {
      this._activePokemonBoxId = boxes[0]?.id || "box-1";
    }
    const pokemonInActiveBox = pokemon
      .map((poke, index) => ({ poke, index }))
      .filter(({ poke }) => (poke.box_id || boxes[0]?.id || "box-1") === this._activePokemonBoxId);
    if (!pokemonInActiveBox.some(({ index }) => index === this._selectedPokemonIndex)) {
      this._selectedPokemonIndex = pokemonInActiveBox[0]?.index ?? null;
    }

    const inventoryHtml = isTeamLocked ? "" : renderMyPokemonInventory(
      state,
      sessionClient,
      isHost,
      this._activePokemonBoxId,
      this._pokemonCardColors,
      this._pokemonMoveUiStates,
      this._selectedPokemonIndex
    );
    draftContainer.innerHTML = balanceHtml + html + "<br/>" + inventoryHtml;
    if (this._lastFusionResult) {
      this.renderFusionResult(this._lastFusionResult);
    } else if (this._lastFusionFailureMessage) {
      this.renderFusionFailure(this._lastFusionFailureMessage);
    }
    this.attachEventListeners(state, sessionClient, isHost);

    bagItemState.forEach(({ name, isOpen }) => {
      const item = Array.from(draftContainer.querySelectorAll(".bag-item-row"))
        .find((candidate) => candidate.dataset.itemName === name);
      if (item) item.open = isOpen;
    });

    if (currentlyOpenTarget) {
      const modalToRestore = document.querySelector(`.inventory-modal-overlay[data-modal="${currentlyOpenTarget}"]`);
      if (modalToRestore) {
        document.body.appendChild(modalToRestore);
        modalToRestore.classList.add("is-open");
        modalToRestore.setAttribute("aria-hidden", "false");
        const btn = document.querySelector(`[data-menu-target="${currentlyOpenTarget}"]`);
        if (btn) btn.setAttribute("aria-expanded", "true");
        document.body.style.overflow = "hidden";
      }
    }
  }


  attachEventListeners(state, sessionClient, isHost) {
    this.startRevealCountdown(state);

    const stage = Number(state.stage || 0);
    if ([5, 9].includes(stage)) {
      this.attachFarmingEventListeners(state, sessionClient, isHost);
    }

    const updateMoveUiState = (panel, mode) => {
      const pokeIdx = panel.dataset.pokeIdx;
      const pokemon = state.my_data?.pokemon?.[Number(pokeIdx)];
      if (!pokemon) return;
      panel.dataset.mode = mode;
      this._pokemonMoveUiStates[pokeIdx] = {
        name: pokemon.name,
        mode,
        selectedMoves: Array.from(panel.querySelectorAll(".move-link.is-selected"))
          .map((move) => move.dataset.moveName),
      };
    };

    const refreshSelectedMoves = (panel) => {
      const selectedMoves = Array.from(panel.querySelectorAll(".move-link.is-selected"))
        .map((move) => move.dataset.moveName);
      const selectedMovesList = panel.querySelector(".saved-moves-list");
      if (selectedMovesList) {
        const movePills = selectedMoves.map((moveName) => {
          const mvInfo = getMoveTextEs(moveName);
          const pill = document.createElement("span");
          pill.className = "move-pill";
          pill.title = mvInfo.desc || mvInfo.en;
          const strong = document.createElement("strong");
          strong.textContent = mvInfo.es;
          pill.appendChild(strong);
          if (mvInfo.desc) {
            const small = document.createElement("small");
            small.style.cssText = "display:block;font-size:0.68rem;opacity:0.88;font-weight:normal;margin-top:2px;";
            small.textContent = mvInfo.desc;
            pill.appendChild(small);
          }
          return pill;
        });
        if (!movePills.length) {
          const emptyLabel = document.createElement("span");
          emptyLabel.className = "text-muted";
          emptyLabel.textContent = "Sin movimientos seleccionados";
          movePills.push(emptyLabel);
        }
        selectedMovesList.replaceChildren(...movePills);
      }
      updateMoveUiState(panel, panel.dataset.mode);
    };

    document.querySelectorAll(".btn-open-moves").forEach((button) => {
      button.addEventListener("click", () => {
        const panel = button.closest(".moves-selector-box");
        if (panel) updateMoveUiState(panel, "view");
      });
    });

    document.querySelectorAll(".btn-edit-moves").forEach((button) => {
      button.addEventListener("click", () => {
        const panel = button.closest(".moves-selector-box");
        if (panel) updateMoveUiState(panel, "editing");
      });
    });

    document.querySelectorAll(".btn-back-moves").forEach((button) => {
      button.addEventListener("click", () => {
        const panel = button.closest(".moves-selector-box");
        if (!panel) return;
        if (panel.dataset.mode === "editing") {
          panel.querySelectorAll(".move-link").forEach((move) => {
            move.classList.toggle("is-selected", move.dataset.initiallySelected === "true");
          });
          refreshSelectedMoves(panel);
          updateMoveUiState(panel, "view");
        } else {
          panel.dataset.mode = "closed";
          delete this._pokemonMoveUiStates[panel.dataset.pokeIdx];
        }
      });
    });

    document.querySelectorAll(".move-link").forEach((move) => {
      move.addEventListener("click", (event) => {
        const panel = move.closest(".moves-selector-box");
        if (panel?.dataset.mode !== "editing") return;
        event.preventDefault();
        move.classList.toggle("is-selected");
        refreshSelectedMoves(panel);
      });
    });

    document.querySelectorAll(".pokemon-color-toggle").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const options = button.parentElement?.querySelector(".pokemon-color-options");
        if (!options) return;
        const shouldOpen = options.classList.contains("hidden");
        document.querySelectorAll(".pokemon-color-options").forEach((menu) => {
          menu.classList.add("hidden");
          menu.parentElement?.querySelector(".pokemon-color-toggle")?.setAttribute("aria-expanded", "false");
        });
        options.classList.toggle("hidden", !shouldOpen);
        button.setAttribute("aria-expanded", String(shouldOpen));
      });
    });

    document.querySelectorAll(".pokemon-color-option").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const colorId = button.dataset.colorId;
        const color = POKEMON_CARD_COLORS[colorId];
        const card = button.closest(".poke-inventory-item");
        if (!color || !card) return;

        card.dataset.colorId = colorId;
        card.style.setProperty("--pokemon-accent", color.hex);
        card.style.setProperty("--pokemon-accent-rgb", color.rgb);
        const pokemonSlot = document.querySelector(`.pokemon-box-slot[data-poke-idx="${card.dataset.pokeIdx}"]`);
        pokemonSlot?.style.setProperty("--pokemon-accent", color.hex);
        pokemonSlot?.style.setProperty("--pokemon-accent-rgb", color.rgb);
        card.querySelectorAll(".pokemon-color-option").forEach((option) => {
          option.classList.toggle("is-selected", option.dataset.colorId === colorId);
        });
        const options = button.closest(".pokemon-color-options");
        options?.classList.add("hidden");
        card.querySelector(".pokemon-color-toggle")?.setAttribute("aria-expanded", "false");

        this._pokemonCardColors[card.dataset.pokemonColorKey] = colorId;
        try {
          localStorage.setItem(this._pokemonColorStorageKey, JSON.stringify(this._pokemonCardColors));
        } catch (error) {
          console.warn("No se pudo guardar el color del Pokémon:", error);
        }
      });
    });

    const turnEvent = state.current_turn_event || {};
    if (
      turnEvent.type === "coinflip"
      && turnEvent.awaiting_confirmation === true
      && typeof turnEvent.coinflip_won === "boolean"
    ) {
      const animationKey = `${state.current_year}:${state.current_turn}:${sessionClient.currentUsername}`;
      if (animationKey !== this._lastCoinflipAnimationKey) {
        this._lastCoinflipAnimationKey = animationKey;
        playCoinflipAnimation(turnEvent, () => {
          sessionClient.send({ action: "subasta_confirm_event_result" });
        });
      }
    }

    const startTradeButton = document.getElementById("btn-start-trade");
    if (startTradeButton) {
      startTradeButton.addEventListener("click", () => {
        sessionClient.send({
          action: "subasta_trade_start",
          target_username: document.getElementById("trade-target-player").value,
          poke_index: parseInt(document.getElementById("trade-own-pokemon").value, 10),
        });
      });
    }

    const selectTradeButton = document.getElementById("btn-select-trade-pokemon");
    if (selectTradeButton) {
      selectTradeButton.addEventListener("click", () => {
        sessionClient.send({
          action: "subasta_trade_select",
          poke_index: parseInt(document.getElementById("trade-target-pokemon").value, 10),
        });
      });
    }

    const confirmTradeButton = document.getElementById("btn-confirm-trade");
    if (confirmTradeButton) {
      confirmTradeButton.addEventListener("click", () => {
        sessionClient.send({ action: "subasta_trade_confirm" });
      });
    }

    const cancelTradeButton = document.getElementById("btn-cancel-trade");
    if (cancelTradeButton) {
      cancelTradeButton.addEventListener("click", () => {
        sessionClient.send({ action: "subasta_trade_cancel" });
      });
    }

    // Puja Personalizada
    const btnBidCustom = document.getElementById("btn-bid-custom");
    if (btnBidCustom) {
      btnBidCustom.addEventListener("click", () => {
        const val = parseInt(document.getElementById("custom-bid-amount").value, 10);
        if (val) {
          btnBidCustom.disabled = true;
          sessionClient.send({ action: "subasta_bid", bid_amount: val });
        }
      });
    }

    // Compra Directa
    const btnBuyout = document.getElementById("btn-buyout");
    if (btnBuyout) {
      btnBuyout.addEventListener("click", () => {
        btnBuyout.disabled = true;
        sessionClient.send({ action: "subasta_buyout" });
      });
    }

    // Retirarse (Fold)
    const btnFold = document.getElementById("btn-fold");
    if (btnFold) {
      btnFold.addEventListener("click", () => {
        btnFold.disabled = true;
        sessionClient.send({ action: "subasta_fold" });
      });
    }

    // Elección Secreta (Ganador)
    const btnSecretYes = document.getElementById("btn-secret-yes");
    const btnSecretNo = document.getElementById("btn-secret-no");
    if (btnSecretYes) {
      btnSecretYes.addEventListener("click", () => {
        btnSecretYes.disabled = true;
        if (btnSecretNo) btnSecretNo.disabled = true;
        sessionClient.send({ action: "subasta_secret_choice", keep_secret: true });
      });
    }
    if (btnSecretNo) {
      btnSecretNo.addEventListener("click", () => {
        btnSecretNo.disabled = true;
        if (btnSecretYes) btnSecretYes.disabled = true;
        sessionClient.send({ action: "subasta_secret_choice", keep_secret: false });
      });
    }

    // Resolver Evento de Turno
    const btnResolveEvent = document.getElementById("btn-resolve-event");
    if (btnResolveEvent) {
      btnResolveEvent.addEventListener("click", () => {
        const event = state.current_turn_event || {};
        const isRouletteEvent = event.reward_is_random === true
          && (event.granted_item || event.granted_items?.length);
        if (isRouletteEvent) {
          btnResolveEvent.disabled = true;
          playEventRoulette(event, () => sessionClient.send({ action: "subasta_resolve_event" }));
          return;
        }
        sessionClient.send({ action: "subasta_resolve_event" });
      });
    }

    const btnConfirmEventResult = document.getElementById("btn-confirm-event-result");
    if (btnConfirmEventResult) {
      btnConfirmEventResult.addEventListener("click", () => {
        btnConfirmEventResult.disabled = true;
        sessionClient.send({ action: "subasta_confirm_event_result" });
      });
    }

    const btnChangeNature = document.getElementById("btn-change-nature");
    if (btnChangeNature) {
      const pokemonSelect = document.getElementById("nature-change-pokemon");
      const natureSelect = document.getElementById("nature-change-nature");
      const natureNames = Object.keys(NATURE_EFFECTS);
      const updateNatureOptions = () => {
        const selectedPokemon = state.my_data?.pokemon?.[parseInt(pokemonSelect.value, 10)];
        const currentNature = selectedPokemon?.nature || "";
        natureSelect.innerHTML = natureNames
          .filter((nature) => nature !== currentNature)
          .map((nature) => `<option value="${nature}">${formatNature(nature)}</option>`)
          .join("");
      };
      if (pokemonSelect && natureSelect) {
        pokemonSelect.addEventListener("change", updateNatureOptions);
        btnChangeNature.addEventListener("click", () => {
          sessionClient.send({
            action: "subasta_change_nature",
            poke_index: parseInt(pokemonSelect.value, 10),
            nature: natureSelect.value,
          });
        });
      }
    }

    // Tráfico Pokémon
    const btnTrafficSell = document.getElementById("btn-pokemon-traffic-sell");
    if (btnTrafficSell) {
      btnTrafficSell.addEventListener("click", () => {
        const select = document.getElementById("traffic-pokemon-select");
        const pokeIdx = parseInt(select.value, 10);
        const event = state.current_turn_event || {};
        btnTrafficSell.disabled = true;
        const skipBtn = document.getElementById("btn-pokemon-traffic-skip");
        if (skipBtn) skipBtn.disabled = true;
        playTrafficAnimation(event.traffic_amount || 0, () => {
          sessionClient.send({ action: "subasta_pokemon_traffic", poke_index: pokeIdx });
        });
      });
    }
    const btnTrafficSkip = document.getElementById("btn-pokemon-traffic-skip");
    if (btnTrafficSkip) {
      btnTrafficSkip.addEventListener("click", () => {
        btnTrafficSkip.disabled = true;
        const sellBtn = document.getElementById("btn-pokemon-traffic-sell");
        if (sellBtn) sellBtn.disabled = true;
        sessionClient.send({ action: "subasta_pokemon_traffic", poke_index: -1 });
      });
    }

    const btnWonderTrade = document.getElementById("btn-wonder-trade");
    if (btnWonderTrade) {
      btnWonderTrade.addEventListener("click", () => {
        const select = document.getElementById("wonder-trade-pokemon-select");
        if (!select || select.value === "") return;
        btnWonderTrade.disabled = true;
        sessionClient.send({
          action: "subasta_wonder_trade",
          poke_index: parseInt(select.value, 10),
        });
      });
    }

    const resolveEventButtons = [
      "btn-coinflip-decline",
      "btn-master-disk-decline",
      "btn-gholdengo-decline",
    ];
    resolveEventButtons.forEach((buttonId) => {
      const button = document.getElementById(buttonId);
      if (button) {
        button.addEventListener("click", () => {
          button.disabled = true;
          sessionClient.send({ action: "subasta_resolve_event" });
        });
      }
    });

    const btnCoinflip = document.getElementById("btn-coinflip-accept");
    if (btnCoinflip) {
      btnCoinflip.addEventListener("click", () => {
        const amountInThousands = Number(document.getElementById("coinflip-amount")?.value);
        const amount = Math.round(amountInThousands * 1000);
        if (!Number.isInteger(amount) || amount < 1 || amount > 100000) return;
        btnCoinflip.disabled = true;
        document.getElementById("btn-coinflip-decline").disabled = true;
        sessionClient.send({ action: "subasta_event_coinflip", amount });
      });
    }

    const btnMasterDisk = document.getElementById("btn-master-disk-accept");
    if (btnMasterDisk) {
      btnMasterDisk.addEventListener("click", () => {
        btnMasterDisk.disabled = true;
        document.getElementById("btn-master-disk-decline").disabled = true;
        sessionClient.send({ action: "subasta_event_master_disk", accept: true });
      });
    }

    const gholdengoTargetOne = document.getElementById("gholdengo-target-one");
    const gholdengoTargetTwo = document.getElementById("gholdengo-target-two");
    if (gholdengoTargetOne && gholdengoTargetTwo) {
      const updateGholdengoTargets = () => {
        Array.from(gholdengoTargetTwo.options).forEach((option) => {
          option.disabled = option.value === gholdengoTargetOne.value;
        });
        if (gholdengoTargetTwo.value === gholdengoTargetOne.value) {
          gholdengoTargetTwo.value = Array.from(gholdengoTargetTwo.options)
            .find((option) => !option.disabled)?.value || "";
        }
      };
      gholdengoTargetOne.addEventListener("change", updateGholdengoTargets);
      updateGholdengoTargets();
    }

    const btnGholdengo = document.getElementById("btn-gholdengo-accept");
    if (btnGholdengo) {
      btnGholdengo.addEventListener("click", () => {
        const targetOne = gholdengoTargetOne?.value;
        const targetTwo = gholdengoTargetTwo?.value;
        if (!targetOne || !targetTwo || targetOne === targetTwo) return;
        btnGholdengo.disabled = true;
        document.getElementById("btn-gholdengo-decline").disabled = true;
        sessionClient.send({
          action: "subasta_event_gholdengo",
          targets: [targetOne, targetTwo],
        });
      });
    }

    const pokeradarTypeOne = document.getElementById("pokeradar-type-one");
    const pokeradarTypeTwo = document.getElementById("pokeradar-type-two");
    if (pokeradarTypeOne && pokeradarTypeTwo) {
      const updatePokeradarTypes = () => {
        Array.from(pokeradarTypeTwo.options).forEach((option) => {
          option.disabled = option.value === pokeradarTypeOne.value;
        });
        if (pokeradarTypeTwo.value === pokeradarTypeOne.value) {
          pokeradarTypeTwo.value = Array.from(pokeradarTypeTwo.options)
            .find((option) => !option.disabled)?.value || "";
        }
      };
      pokeradarTypeOne.addEventListener("change", updatePokeradarTypes);
      updatePokeradarTypes();
    }

    const btnPokeradar = document.getElementById("btn-pokeradar-accept");
    if (btnPokeradar) {
      btnPokeradar.addEventListener("click", () => {
        const typeOne = pokeradarTypeOne?.value;
        const typeTwo = pokeradarTypeTwo?.value;
        if (!typeOne || !typeTwo || typeOne === typeTwo) return;
        btnPokeradar.disabled = true;
        sessionClient.send({
          action: "subasta_event_pokeradar",
          types: [typeOne, typeTwo],
        });
      });
    }

    // Avanzar Etapa (Host)
    const btnForceNext = document.getElementById("btn-force-next-stage");
    [btnForceNext].forEach((btn) => {
      if (btn) {
        btn.addEventListener("click", () => {
          sessionClient.send({ action: "subasta_next_stage" });
        });
      }
    });

    // Fijar Equipo – bloquear edición permanentemente
    const btnLockTeam = document.getElementById("btn-lock-team");
    if (btnLockTeam) {
      btnLockTeam.addEventListener("click", () => {
        const area = document.getElementById("showdown-text-area");
        if (area) {
          this._lockedShowdownText = area.value;
        }
        this._lockedShowdownStage = Number(state.stage || 2);
        // Re-renderizar para que se refleje el estado fijado
        this.renderCurrentStageView(state, sessionClient, isHost);
      });
    }

    document.querySelectorAll(".btn-sell-pokemon").forEach((button) => {
      button.addEventListener("click", () => {
        const pokemonIndex = parseInt(button.getAttribute("data-pokemon-index"), 10);
        button.disabled = true;
        sessionClient.send({ action: "subasta_sell_pokemon", pokemon_index: pokemonIndex });
      });
    });

    // Desafío PVE contra IA
    const btnLaunchPve = document.getElementById("btn-launch-pve");
    if (btnLaunchPve) {
      btnLaunchPve.addEventListener("click", () => {
        const myData = state.my_data || {};
        const myPokemon = myData.pokemon || [];
        if (!myPokemon || myPokemon.length === 0) {
          alert("No tienes Pokémon en tu equipo para combatir.");
          return;
        }

        const presetId = document.getElementById("select-pve-preset")?.value || "brock-rock";
        const currentYear = state.current_year || (state.current_stage <= 5 ? 1 : (state.current_stage <= 9 ? 2 : 3));
        const setup = {
          preset_id: presetId,
          year: currentYear,
          player_team: myPokemon,
          return_url: window.location.href,
        };

        try {
          sessionStorage.setItem("pve_setup", JSON.stringify(setup));
        } catch (e) {
          console.warn("Error guardando pve_setup:", e);
        }

        // Salto directo a la página dedicada y responsive de combate
        window.location.href = "pve_battle.html";
      });
    }

    // Copiar Showdown Text
    const btnCopyShowdown = document.getElementById("btn-copy-showdown");
    if (btnCopyShowdown) {
      btnCopyShowdown.addEventListener("click", () => {
        const area = document.getElementById("showdown-text-area");
        if (area) {
          area.select();
          navigator.clipboard.writeText(area.value).then(() => {
            btnCopyShowdown.textContent = "¡Copiado!";
            setTimeout(() => (btnCopyShowdown.textContent = "📋 Copiar al Portapapeles"), 2000);
          });
        }
      });
    }

    const btnFinalizeEvent = document.getElementById("btn-finalize-event");
    if (btnFinalizeEvent) {
      btnFinalizeEvent.addEventListener("click", () => {
        sessionClient.send({ action: "subasta_finalize_event" });
      });
    }

    const trophyCheckboxes = Array.from(document.querySelectorAll(".trophy-pokemon-checkbox"));
    const trophyCount = document.getElementById("trophy-selection-count");
    const saveTrophySelection = document.getElementById("btn-save-trophy-selection");
    const updateTrophySelectionControls = () => {
      const checked = trophyCheckboxes.filter((checkbox) => checkbox.checked);
      if (trophyCount) trophyCount.textContent = String(checked.length);
      if (saveTrophySelection) saveTrophySelection.disabled = checked.length !== 6;
      if (checked.length >= 6) {
        trophyCheckboxes.filter((checkbox) => !checkbox.checked).forEach((checkbox) => { checkbox.disabled = true; });
      } else {
        trophyCheckboxes.forEach((checkbox) => { checkbox.disabled = false; });
      }
    };
    trophyCheckboxes.forEach((checkbox) => checkbox.addEventListener("change", updateTrophySelectionControls));
    if (saveTrophySelection) {
      updateTrophySelectionControls();
      saveTrophySelection.addEventListener("click", () => {
        const pokemonIndices = trophyCheckboxes.filter((checkbox) => checkbox.checked).map((checkbox) => Number(checkbox.value));
        if (pokemonIndices.length !== 6) return;
        sessionClient.send({ action: "subasta_save_trophy_selection", pokemon_indices: pokemonIndices });
      });
    }

    // Registrar Resultado de Enfrentamiento (Admin / Host)
    const btnSubmitMatch = document.getElementById("btn-submit-match");
    if (btnSubmitMatch) {
      btnSubmitMatch.addEventListener("click", () => {
        const playerOne = document.getElementById("admin-match-player-one").value;
        const playerTwo = document.getElementById("admin-match-player-two").value;
        const pointsOne = Number(document.getElementById("admin-match-points-one").value);
        const pointsTwo = Number(document.getElementById("admin-match-points-two").value);
        if (playerOne && playerTwo && playerOne !== playerTwo) {
          sessionClient.send({
            action: "subasta_admin_submit_match",
            player_one: playerOne,
            points_one: pointsOne,
            player_two: playerTwo,
            points_two: pointsTwo,
          });
        } else {
          alert("Selecciona dos jugadores diferentes.");
        }
      });
    }
    // Guardar 4 Movimientos Seleccionados
    document.querySelectorAll(".btn-save-moves").forEach((btn) => {
      btn.addEventListener("click", () => {
        const pokeIdx = parseInt(btn.getAttribute("data-poke-idx"), 10);
        const panel = btn.closest(".moves-selector-box");
        if (!panel) return;
        const selectedMoves = Array.from(panel.querySelectorAll(".move-link.is-selected"))
          .map((move) => move.dataset.moveName);

        if (selectedMoves.length > 4) {
          alert("Solo puedes seleccionar un máximo de 4 movimientos.");
          return;
        }

        refreshSelectedMoves(panel);
        panel.dataset.mode = "closed";
        delete this._pokemonMoveUiStates[pokeIdx];
        sessionClient.send({
          action: "subasta_select_moves",
          poke_index: pokeIdx,
          selected_moves: selectedMoves,
        });
      });
    });

    document.querySelectorAll(".btn-evolve-pokemon").forEach((btn) => {
      btn.addEventListener("click", () => {
        const pokeIdx = parseInt(btn.getAttribute("data-poke-idx"), 10);
        const targetName = btn.getAttribute("data-target-name") || undefined;
        sessionClient.send({ action: "subasta_evolve_pokemon", poke_index: pokeIdx, target_name: targetName });
      });
    });

    document.querySelectorAll(".btn-toggle-evolution-menu").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const pokeIdx = btn.getAttribute("data-poke-idx");
        const menu = document.getElementById(`evo-menu-${pokeIdx}`);
        if (menu) {
          document.querySelectorAll(".evolution-menu").forEach((m) => {
            if (m !== menu) m.classList.add("hidden");
          });
          menu.classList.toggle("hidden");
        }
      });
    });

    document.querySelectorAll(".btn-evolve-target-option").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const pokeIdx = parseInt(btn.getAttribute("data-poke-idx"), 10);
        const targetName = btn.getAttribute("data-target-name");
        if (!targetName) return;
        sessionClient.send({ action: "subasta_evolve_pokemon", poke_index: pokeIdx, target_name: targetName });
      });
    });

    document.addEventListener("click", () => {
      document.querySelectorAll(".evolution-menu").forEach((m) => m.classList.add("hidden"));
    });

    document.querySelectorAll(".btn-equip-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        const pokeIdx = parseInt(btn.getAttribute("data-poke-idx"), 10);
        const select = document.querySelector(`.poke-item-select[data-poke-idx="${pokeIdx}"]`);
        const itemName = select ? select.value : "";
        if (!itemName) return;
        sessionClient.send({ action: "subasta_item_assign", poke_index: pokeIdx, item_name: itemName });
      });
    });

    document.querySelectorAll(".btn-remove-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        const pokeIdx = parseInt(btn.getAttribute("data-poke-idx"), 10);
        sessionClient.send({ action: "subasta_item_remove", poke_index: pokeIdx });
      });
    });

    const closeAllInventoryModals = () => {
      document.querySelectorAll(".inventory-modal-overlay.is-open").forEach((modal) => {
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        const target = modal.dataset.modal;
        const btn = document.querySelector(`[data-menu-target="${target}"]`);
        if (btn) btn.setAttribute("aria-expanded", "false");
      });
      document.body.style.overflow = "";
    };

    document.querySelectorAll(".btn-close-menu").forEach((closeBtn) => {
      closeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        closeAllInventoryModals();
      });
    });

    document.querySelectorAll(".inventory-modal-overlay").forEach((overlay) => {
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) {
          closeAllInventoryModals();
        }
      });
    });

    document.querySelectorAll(".inventory-menu-toggle").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const target = btn.dataset.menuTarget;
        const modal = document.querySelector(`.inventory-modal-overlay[data-modal="${target}"]`);
        if (!modal) return;

        const willOpen = !modal.classList.contains("is-open");
        closeAllInventoryModals();

        if (willOpen) {
          if (modal.parentElement !== document.body) {
            document.body.appendChild(modal);
          }
          modal.classList.add("is-open");
          modal.setAttribute("aria-hidden", "false");
          btn.setAttribute("aria-expanded", "true");
          document.body.style.overflow = "hidden";
        }
      });
    });

    document.querySelectorAll(".pokemon-box-tab").forEach((button) => {
      button.addEventListener("click", () => {
        this._activePokemonBoxId = button.dataset.pokemonBoxId;
        const nextBoxPokemon = (state.my_data?.pokemon || [])
          .map((poke, index) => ({ poke, index }))
          .find(({ poke }) => (poke.box_id || state.my_data?.pokemon_boxes?.[0]?.id || "box-1") === this._activePokemonBoxId);
        this._selectedPokemonIndex = nextBoxPokemon?.index ?? null;
        this.renderCurrentStageView(state, sessionClient, isHost);
      });
    });

    document.querySelectorAll(".pokemon-box-slot[data-poke-idx]").forEach((slot) => {
      slot.addEventListener("click", (event) => {
        if (slot.dataset.dragged === "true") {
          event.preventDefault();
          slot.dataset.dragged = "false";
          return;
        }
        this._selectedPokemonIndex = Number(slot.dataset.pokeIdx);
        this.renderCurrentStageView(state, sessionClient, isHost);
        if (window.matchMedia("(max-width: 760px)").matches) {
          document.querySelector(".pokemon-info-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      });

      let holdTimer = null;
      let dragStarted = false;
      let startX = 0;
      let startY = 0;
      let pointerId = null;
      let dragGhost = null;
      const clearDropTargets = () => document.querySelectorAll(".pokemon-box-drop-target")
        .forEach((target) => target.classList.remove("pokemon-box-drop-target"));
      const startDrag = () => {
        if (dragStarted) return;
        dragStarted = true;
        slot.classList.add("pokemon-box-slot--dragging");
        slot.dataset.dragged = "true";
        dragGhost = slot.cloneNode(true);
        dragGhost.classList.add("pokemon-box-drag-ghost");
        dragGhost.style.transform = `translate3d(${startX}px, ${startY}px, 0) translate(-50%, -50%) scale(1.12)`;
        document.body.appendChild(dragGhost);
        if (pointerId !== null) slot.setPointerCapture?.(pointerId);
      };

      slot.addEventListener("pointerdown", (event) => {
        if (event.pointerType === "mouse" && event.button !== 0) return;
        startX = event.clientX;
        startY = event.clientY;
        pointerId = event.pointerId;
        dragStarted = false;
        if (event.pointerType === "mouse") {
          slot.setPointerCapture?.(pointerId);
        } else {
          holdTimer = window.setTimeout(() => {
            holdTimer = null;
            startDrag();
          }, 180);
        }
      });

      slot.addEventListener("pointermove", (event) => {
        if (pointerId === null || event.pointerId !== pointerId) return;
        const distance = Math.hypot(event.clientX - startX, event.clientY - startY);
        if (!dragStarted && event.pointerType === "mouse" && distance > 5) startDrag();
        if (!dragStarted && holdTimer && distance > 24) {
          window.clearTimeout(holdTimer);
          holdTimer = null;
        }
        if (!dragStarted) return;
        event.preventDefault();
        if (dragGhost) {
          dragGhost.style.transform = `translate3d(${event.clientX}px, ${event.clientY}px, 0) translate(-50%, -50%) scale(1.12)`;
        }
        clearDropTargets();
        const target = document.elementFromPoint(event.clientX, event.clientY)
          ?.closest(".pokemon-box-slot, .pokemon-box-tab");
        target?.classList.add("pokemon-box-drop-target");
      });

      const finishDrag = (event) => {
        if (holdTimer) window.clearTimeout(holdTimer);
        holdTimer = null;
        if (!dragStarted) {
          pointerId = null;
          return;
        }
        event.preventDefault();
        const sourceIndex = Number(slot.dataset.pokeIdx);
        const target = document.elementFromPoint(event.clientX, event.clientY)
          ?.closest(".pokemon-box-slot, .pokemon-box-tab");
        clearDropTargets();
        slot.classList.remove("pokemon-box-slot--dragging");
        dragGhost?.remove();
        dragGhost = null;
        dragStarted = false;
        pointerId = null;
        const sourcePokemon = state.my_data?.pokemon?.[sourceIndex];
        if (!sourcePokemon || !target) return;

        this._selectedPokemonIndex = sourceIndex;
        if (target.classList.contains("pokemon-box-tab")) {
          const targetBoxId = target.dataset.pokemonBoxId;
          if (!targetBoxId || targetBoxId === this._activePokemonBoxId) return;
          this._activePokemonBoxId = targetBoxId;
          sessionClient.send({ action: "subasta_move_pokemon_box", poke_index: sourceIndex, box_id: targetBoxId });
          return;
        }

        const targetPosition = Number(target.dataset.slotPosition);
        if (Number.isInteger(targetPosition) && targetPosition >= 0) {
          const boxIndexes = (state.my_data?.pokemon || [])
            .map((poke, index) => ({ poke, index }))
            .filter(({ poke }) => (poke.box_id || state.my_data?.pokemon_boxes?.[0]?.id || "box-1") === this._activePokemonBoxId)
            .map(({ index }) => index);
          this._selectedPokemonIndex = boxIndexes[Math.min(targetPosition, boxIndexes.length - 1)] ?? sourceIndex;
          sessionClient.send({
            action: "subasta_reorder_pokemon",
            poke_index: sourceIndex,
            box_id: this._activePokemonBoxId,
            target_position: targetPosition,
          });
        }
      };

      slot.addEventListener("pointerup", finishDrag);
      slot.addEventListener("pointercancel", (event) => {
        if (holdTimer) window.clearTimeout(holdTimer);
        holdTimer = null;
        dragStarted = false;
        pointerId = null;
        slot.classList.remove("pokemon-box-slot--dragging");
        slot.dataset.dragged = "false";
        dragGhost?.remove();
        dragGhost = null;
        clearDropTargets();
      });
    });

    document.querySelectorAll(".btn-create-pokemon-box").forEach((button) => {
      button.addEventListener("click", () => {
        const boxCount = state.my_data?.pokemon_boxes?.length || 1;
        this._activePokemonBoxId = `box-${boxCount + 1}`;
        sessionClient.send({ action: "subasta_create_pokemon_box" });
      });
    });

    document.querySelectorAll(".pokemon-box-select").forEach((select) => {
      select.addEventListener("change", () => {
        const pokeIdx = parseInt(select.dataset.pokeIdx, 10);
        if (Number.isNaN(pokeIdx) || !select.value) return;
        sessionClient.send({
          action: "subasta_move_pokemon_box",
          poke_index: pokeIdx,
          box_id: select.value,
        });
      });
    });

    document.querySelectorAll(".btn-item-give").forEach((btn) => {
      btn.addEventListener("click", () => {
        const itemName = btn.getAttribute("data-item-name");
        const row = btn.closest(".bag-item-row");
        const select = row ? row.querySelector(".bag-item-select") : null;
        const pokeIdx = select ? parseInt(select.value, 10) : -1;
        if (!itemName || pokeIdx < 0) return;
        sessionClient.send({ action: "subasta_item_assign", poke_index: pokeIdx, item_name: itemName });
      });
    });

    document.querySelectorAll(".ability-capsule-pokemon-select").forEach((pokemonSelect) => {
      const row = pokemonSelect.closest(".bag-item-row");
      const abilitySelect = row?.querySelector(".ability-capsule-select");
      const updateAbilities = () => {
        const poke = state.my_data?.pokemon?.[parseInt(pokemonSelect.value, 10)];
        if (!abilitySelect) return;
        abilitySelect.dataset.pokeIdx = pokemonSelect.value;
        abilitySelect.innerHTML = (poke?.abilities || [])
          .filter((ability) => ability !== poke?.ability)
          .map((ability) => {
            const abEs = getAbilityTextEs(ability);
            return `<option value="${ability}">${abEs.es}${abEs.desc ? ` — ${abEs.desc}` : ""}</option>`;
          })
          .join("");
      };
      pokemonSelect.addEventListener("change", updateAbilities);
      updateAbilities();
    });

    document.querySelectorAll(".btn-use-ability-capsule").forEach((btn) => {
      btn.addEventListener("click", () => {
        const row = btn.closest(".bag-item-row");
        const pokemonSelect = row?.querySelector(".ability-capsule-pokemon-select");
        const abilitySelect = row?.querySelector(".ability-capsule-select");
        if (!pokemonSelect || !abilitySelect || !abilitySelect.value) return;
        sessionClient.send({
          action: "subasta_use_ability_capsule",
          poke_index: parseInt(pokemonSelect.value, 10),
          ability: abilitySelect.value,
        });
      });
    });

    document.querySelectorAll(".btn-use-mint").forEach((btn) => {
      btn.addEventListener("click", () => {
        const row = btn.closest(".bag-item-row");
        const pokemonSelect = row?.querySelector(".mint-pokemon-select");
        const itemName = btn.getAttribute("data-item-name");
        if (!pokemonSelect || !itemName || pokemonSelect.value === "") return;
        sessionClient.send({
          action: "subasta_use_mint",
          poke_index: parseInt(pokemonSelect.value, 10),
          item_name: itemName,
        });
      });
    });

    document.querySelectorAll(".tm-pokemon-select").forEach((pokemonSelect) => {
      const row = pokemonSelect.closest(".bag-item-row");
      const useBtn = row?.querySelector(".btn-use-tm");
      const statusBadge = row?.querySelector(".tm-compat-status");
      const itemName = pokemonSelect.getAttribute("data-item-name");
      const moveName = getTmMoveName(itemName);

      const updateCompatibility = () => {
        const val = pokemonSelect.value;
        if (val === "" || val === undefined || isNaN(parseInt(val, 10))) {
          pokemonSelect.classList.remove("is-compatible", "is-warning");
          pokemonSelect.classList.add("is-incompatible");
          if (statusBadge) {
            statusBadge.className = "tm-compat-status badge badge-danger";
            statusBadge.textContent = "❌ Sin compatibles";
          }
          if (useBtn) {
            useBtn.disabled = true;
            useBtn.title = "Ningún Pokémon compatible seleccionado";
          }
          return;
        }
        const pokeIdx = parseInt(val, 10);
        const poke = state.my_data?.pokemon?.[pokeIdx];
        const compat = checkTmCompatibility(poke, moveName);

        pokemonSelect.classList.remove("is-compatible", "is-incompatible", "is-warning");
        if (compat.canLearn) {
          pokemonSelect.classList.add("is-compatible");
        } else if (compat.reason === "already_learned") {
          pokemonSelect.classList.add("is-warning");
        } else {
          pokemonSelect.classList.add("is-incompatible");
        }

        if (statusBadge) {
          statusBadge.className = `tm-compat-status badge ${compat.badgeClass}`;
          statusBadge.textContent = compat.label;
        }
        if (useBtn) {
          useBtn.disabled = !compat.canLearn;
          useBtn.title = compat.canLearn
            ? `Enseñar ${moveName} a ${poke?.name || "Pokémon"}`
            : `${poke?.name || "Este Pokémon"} no puede aprender esta MT`;
        }
      };

      pokemonSelect.addEventListener("change", updateCompatibility);
    });

    document.querySelectorAll(".btn-use-tm").forEach((btn) => {
      btn.addEventListener("click", () => {
        const row = btn.closest(".bag-item-row");
        const pokemonSelect = row?.querySelector(".tm-pokemon-select");
        if (!pokemonSelect) return;
        const rawVal = pokemonSelect.value;
        if (rawVal === "" || isNaN(parseInt(rawVal, 10))) {
          alert("Selecciona un Pokémon que pueda aprender esta MT.");
          return;
        }
        const pokeIdx = parseInt(rawVal, 10);
        const itemName = btn.getAttribute("data-item-name");
        const poke = state.my_data?.pokemon?.[pokeIdx];
        const moveName = getTmMoveName(itemName);
        const compat = checkTmCompatibility(poke, moveName);

        if (!compat.canLearn) {
          if (compat.reason === "already_learned") {
            alert(`⚠️ ${poke?.name || "Este Pokémon"} ya conoce el movimiento ${moveName}.`);
          } else {
            alert(`❌ ${poke?.name || "Este Pokémon"} no puede aprender la ${itemName}.`);
          }
          return;
        }

        sessionClient.send({
          action: "subasta_use_tm",
          poke_index: pokeIdx,
          item_name: itemName,
        });
      });
    });

    document.querySelectorAll(".form-change-pokemon-select").forEach((pokemonSelect) => {
      const row = pokemonSelect.closest(".bag-item-row");
      const formSelect = row?.querySelector(".form-change-form-select");
      const updateFormOptions = () => {
        const poke = state.my_data?.pokemon?.[parseInt(pokemonSelect.value, 10)];
        if (!formSelect) return;
        const formOptions = Array.isArray(poke?.regional_form_options) ? poke.regional_form_options : [];
        formSelect.innerHTML = formOptions.length
          ? formOptions.map((option) => `<option value="${option.target_name}">${option.display_name}</option>`).join("")
          : '<option value="">Sin formas regionales</option>';
      };
      pokemonSelect.addEventListener("change", updateFormOptions);
      updateFormOptions();
    });

    document.querySelectorAll(".btn-use-form-change").forEach((btn) => {
      btn.addEventListener("click", () => {
        const row = btn.closest(".bag-item-row");
        const pokemonSelect = row?.querySelector(".form-change-pokemon-select");
        const formSelect = row?.querySelector(".form-change-form-select");
        if (!pokemonSelect || !formSelect || !formSelect.value) return;
        sessionClient.send({
          action: "subasta_use_form_change",
          poke_index: parseInt(pokemonSelect.value, 10),
          target_form: formSelect.value,
        });
      });
    });

    document.querySelectorAll(".btn-buy-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (this._isRouletteSpinning) return;
        const itemName = btn.getAttribute("data-item-name");
        if (!itemName) return;
        if (
          itemName.startsWith("Caja Misteriosa")
          || itemName.startsWith("Regalo del Primo")
          || itemName === "Ruleta Plates"
          || itemName === "Ruleta Piedras"
          || itemName === "Ruleta Mentas"
          || itemName === "Ruleta Choice"
          || itemName === "Ruleta MT OP"
        ) {
          this._isRouletteSpinning = true;
        }
        sessionClient.send({ action: "subasta_shop_buy", item_name: itemName });
      });
    });

    const fusionOne = document.getElementById("fusion-pokemon-one");
    const fusionTwo = document.getElementById("fusion-pokemon-two");
    const fusionPicker = document.getElementById("fusion-picker");
    const fusionPickerTitle = document.getElementById("fusion-picker-title");
    const fusionPickerMessage = document.getElementById("fusion-picker-message");
    let activeFusionSlot = null;
    const getFusionPokemon = (select) => {
      if (!select || select.value === "") return null;
      return state.my_data?.pokemon?.[Number(select.value)] || null;
    };
    const updateFusionSlot = (slot) => {
      const select = slot === "one" ? fusionOne : fusionTwo;
      const pokemon = getFusionPokemon(select);
      const button = document.querySelector(`[data-fusion-slot="${slot}"]`);
      if (!button) return;
      const art = button.querySelector(".fusion-slot-art");
      const name = button.querySelector(".fusion-slot-name");
      button.classList.toggle("has-pokemon", Boolean(pokemon));
      if (art) art.innerHTML = pokemon ? buildPokemonSpriteMarkup(pokemon) : "＋";
      if (name) name.textContent = pokemon?.name || (slot === "one" ? "Primer Pokémon" : "Segundo Pokémon");
    };
    const updateFusionButton = () => {
      const button = document.getElementById("btn-fuse-pokemon");
      if (button) {
        button.disabled = !fusionOne?.value
          || !fusionTwo?.value
          || fusionOne.value === fusionTwo.value
          || button.dataset.hasSplicers !== "true"
          || button.dataset.hasCombinations !== "true";
      }
    };
    const requestFusionPreview = () => {
      if (!fusionOne?.value || !fusionTwo?.value || fusionOne.value === fusionTwo.value) return;
      sessionClient.send({
        action: "subasta_fusion_preview",
        pokemon_index_one: parseInt(fusionOne.value, 10),
        pokemon_index_two: parseInt(fusionTwo.value, 10),
      });
    };
    const closeFusionPicker = () => {
      if (fusionPicker) fusionPicker.hidden = true;
      activeFusionSlot = null;
    };
    document.querySelectorAll("[data-fusion-slot]").forEach((slotButton) => {
      slotButton.addEventListener("click", () => {
        if (!fusionPicker || !fusionPickerTitle) return;
        activeFusionSlot = slotButton.dataset.fusionSlot;
        fusionPickerTitle.textContent = activeFusionSlot === "one" ? "Elige el primer Pokémon" : "Elige el segundo Pokémon";
        const selectedPokemon = activeFusionSlot === "one" ? fusionOne?.value : fusionTwo?.value;
        const otherPokemon = activeFusionSlot === "one" ? fusionTwo?.value : fusionOne?.value;
        fusionPicker.querySelectorAll(".fusion-pokemon-option").forEach((option) => {
          const isSelectedElsewhere = option.dataset.pokemonIndex === otherPokemon;
          option.disabled = isSelectedElsewhere;
          option.classList.toggle("is-selected", option.dataset.pokemonIndex === selectedPokemon);
          option.classList.toggle("is-unavailable", isSelectedElsewhere);
        });
        if (fusionPickerMessage) fusionPickerMessage.textContent = "";
        fusionPicker.hidden = false;
        fusionPicker.scrollIntoView({ block: "nearest", behavior: "smooth" });
      });
    });
    fusionPicker?.querySelector("#fusion-picker-close")?.addEventListener("click", closeFusionPicker);
    fusionPicker?.querySelectorAll(".fusion-pokemon-option").forEach((option) => {
      option.addEventListener("click", () => {
        if (!activeFusionSlot) return;
        const targetSelect = activeFusionSlot === "one" ? fusionOne : fusionTwo;
        if (!targetSelect) return;
        targetSelect.value = option.dataset.pokemonIndex;
        this._lastFusionResult = null;
        this._lastFusionFailureMessage = null;
        const fusionButton = document.getElementById("btn-fuse-pokemon");
        if (fusionButton) fusionButton.dataset.hasCombinations = "false";
        const resultSlot = document.getElementById("fusion-result-slot");
        const resultArt = document.getElementById("fusion-result-art");
        const resultName = document.getElementById("fusion-result-name");
        const resultMessage = document.getElementById("fusion-result-message");
        resultSlot?.classList.remove("has-pokemon", "has-failed");
        if (resultArt) resultArt.textContent = "?";
        if (resultName) resultName.textContent = "Resultado";
        if (resultMessage) {
          resultMessage.textContent = "El Pokémon fusionado aparecerá aquí.";
          resultMessage.style.color = "";
        }
        updateFusionSlot(activeFusionSlot);
        closeFusionPicker();
        updateFusionButton();
        const preview = document.getElementById("fusion-preview-results");
        if (preview) {
          preview.innerHTML = fusionOne?.value && fusionTwo?.value
            ? '<p class="text-muted">Consultando combinaciones...</p>'
            : '<p class="text-muted">Elige el otro Pokémon para consultar las combinaciones.</p>';
        }
        requestFusionPreview();
      });
    });
    updateFusionSlot("one");
    updateFusionSlot("two");
    updateFusionButton();
    const fusionButton = document.getElementById("btn-fuse-pokemon");
    fusionButton?.addEventListener("click", () => {
      if (!fusionOne?.value || !fusionTwo?.value || fusionButton.disabled || fusionOne.value === fusionTwo.value) return;
      fusionButton.disabled = true;
      sessionClient.send({
        action: "subasta_fusion",
        pokemon_index_one: parseInt(fusionOne.value, 10),
        pokemon_index_two: parseInt(fusionTwo.value, 10),
      });
    });

    document.querySelectorAll(".btn-show-box-odds").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        e.preventDefault();
        const boxName = btn.getAttribute("data-box-name");
        if (boxName) {
          showBoxOddsModal(boxName);
        }
      });
    });

  }

  startRevealCountdown(state) {
    const revealUntil = Number((state.current_auction || {}).reveal_hold_until || 0) * 1000;
    const revealBar = document.querySelector("[data-reveal-bar]");
    const revealFill = document.querySelector("[data-reveal-fill]");

    if (!revealUntil || !revealBar || !revealFill) {
      if (window.__subastaRevealTimer) {
        clearInterval(window.__subastaRevealTimer);
        window.__subastaRevealTimer = null;
      }
      return;
    }

    const tick = () => {
      const remaining = Math.max(0, revealUntil - Date.now());
      const percent = Math.max(0, Math.min(100, (remaining / 5000) * 100));
      revealFill.style.width = `${percent}%`;
      const text = document.querySelector("[data-reveal-bar] ~ div");
      if (text && text.tagName === "DIV") {
      }
      if (remaining <= 0) {
        clearInterval(window.__subastaRevealTimer);
        window.__subastaRevealTimer = null;
      }
    };

    if (window.__subastaRevealTimer) {
      clearInterval(window.__subastaRevealTimer);
    }
    tick();
    window.__subastaRevealTimer = setInterval(tick, 100);
  }

  attachFarmingEventListeners(state, sessionClient, isHost) {
    const farming = state.farming_phase || {};
    const status = farming.status || "planning";

    // --- SUBFASE DE REVELACIÓN DE RECOMPENSAS ---
    if (status === "revealing") {
      const revealButtons = document.querySelectorAll(".btn-reveal-reward");

      const revealButton = (btn) => {
        if (!btn || btn.dataset.revealed === "true") return;
        btn.dataset.revealed = "true";
        const isSuccess = btn.dataset.success === "1";
        const rewardText = btn.dataset.rewardText || "";
        const sprite = btn.dataset.sprite || "";
        const category = btn.dataset.category || "";

        const slot = btn.closest(".farming-reward-slot");
        if (!slot) return;

        let content = "";
        if (isSuccess) {
          if (category === "money") {
            content = `<span class="farming-revealed-val success money">💰 ${rewardText}</span>`;
          } else {
            const imgTag = sprite ? `<img src="${sprite}" alt="" class="farming-reward-icon" onerror="this.style.display='none'" /> ` : "";
            content = `<span class="farming-revealed-val success item">${imgTag}${rewardText}</span>`;
          }
        } else {
          content = `<span class="farming-revealed-val failure">❌ Sin recompensa</span>`;
        }

        slot.innerHTML = content;
        slot.classList.add("is-revealed");
      };

      revealButtons.forEach((btn) => {
        btn.addEventListener("click", () => revealButton(btn));
      });

      const revealAllBtn = document.getElementById("btn-reveal-all-rewards");
      if (revealAllBtn) {
        revealAllBtn.addEventListener("click", () => {
          document.querySelectorAll(".btn-reveal-reward").forEach((btn, index) => {
            setTimeout(() => revealButton(btn), index * 80);
          });
        });
      }

      const advanceBtn = document.getElementById("btn-advance-farming");
      if (advanceBtn) {
        advanceBtn.addEventListener("click", () => {
          sessionClient.send({ action: "subasta_admin_advance_from_farming" });
        });
      }

      const skipBtn = document.getElementById("btn-skip-farming");
      if (skipBtn) {
        skipBtn.addEventListener("click", () => {
          if (confirm("¿Estás seguro de que deseas saltar esta fase de farmeo?")) {
            sessionClient.send({ action: "subasta_admin_skip_farming" });
          }
        });
      }
      return;
    }

    // --- SUBFASE DE PLANIFICACIÓN (ASIGNACIÓN) ---
    const isConfirmed = Boolean(farming.is_confirmed);
    const myAssignments = JSON.parse(JSON.stringify(farming.my_assignments || {}));

    const confirmBtn = document.getElementById("btn-confirm-farming");
    if (confirmBtn) {
      confirmBtn.addEventListener("click", () => {
        sessionClient.send({ action: "subasta_confirm_farming" });
      });
    }

    const forceResolveBtn = document.getElementById("btn-force-resolve-farming");
    if (forceResolveBtn) {
      forceResolveBtn.addEventListener("click", () => {
        if (confirm("¿Forzar la resolución de la fase de farmeo con las asignaciones actuales?")) {
          sessionClient.send({ action: "subasta_admin_force_resolve_farming" });
        }
      });
    }

    const skipBtn = document.getElementById("btn-skip-farming");
    if (skipBtn) {
      skipBtn.addEventListener("click", () => {
        if (confirm("¿Estás seguro de que deseas saltar esta fase de farmeo?")) {
          sessionClient.send({ action: "subasta_admin_skip_farming" });
        }
      });
    }

    if (isConfirmed) return;

    const saveAssignments = () => {
      sessionClient.send({
        action: "subasta_set_farming_assignment",
        assignments: myAssignments,
      });
      // Actualización optimista inmediata para respuesta visual instantánea
      if (!state.farming_phase) state.farming_phase = {};
      state.farming_phase.my_assignments = myAssignments;
      this.renderCurrentStageView(state, sessionClient, isHost);
    };

    // Botones para quitar Pokémon de un slot asignado
    document.querySelectorAll(".btn-remove-farming-slot").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const zoneKey = btn.dataset.zoneKey;
        const pokeIdx = Number(btn.dataset.pokeIdx);
        if (myAssignments[zoneKey]) {
          myAssignments[zoneKey] = myAssignments[zoneKey].filter((i) => i !== pokeIdx);
          saveAssignments();
        }
      });
    });

    const assignPokeToZone = (pokeIdx, zoneKey) => {
      pokeIdx = Number(pokeIdx);
      if (isNaN(pokeIdx)) return;

      Object.keys(myAssignments).forEach((zk) => {
        myAssignments[zk] = (myAssignments[zk] || []).filter((i) => i !== pokeIdx);
      });

      if (!myAssignments[zoneKey]) myAssignments[zoneKey] = [];
      if (myAssignments[zoneKey].length < 3) {
        myAssignments[zoneKey].push(pokeIdx);
      } else {
        alert("Esta zona ya tiene el límite de 3 Pokémon.");
        return;
      }

      saveAssignments();
    };

    // Selección por clic (compatible con táctil / mouse)
    let selectedPokeIdx = null;
    const pokeItems = document.querySelectorAll(".farming-poke-item");
    pokeItems.forEach((item) => {
      item.addEventListener("click", () => {
        const pokeIdx = Number(item.dataset.pokeIdx);
        if (selectedPokeIdx === pokeIdx) {
          selectedPokeIdx = null;
          item.classList.remove("is-selected");
        } else {
          pokeItems.forEach((el) => el.classList.remove("is-selected"));
          selectedPokeIdx = pokeIdx;
          item.classList.add("is-selected");
        }
      });
    });

    document.querySelectorAll(".farming-zone-slot, .farming-zone-card").forEach((target) => {
      target.addEventListener("click", () => {
        if (selectedPokeIdx === null) return;
        const zoneKey = target.dataset.zoneKey || target.closest(".farming-zone-card")?.dataset.zoneKey;
        if (zoneKey) {
          assignPokeToZone(selectedPokeIdx, zoneKey);
          selectedPokeIdx = null;
        }
      });
    });

    // Drag & Drop con Pointer Events reutilizando el estilo fluido de las cajas
    pokeItems.forEach((item) => {
      let startX = 0;
      let startY = 0;
      let pointerId = null;
      let dragStarted = false;
      let dragGhost = null;
      let autoScrollRaf = null;
      let autoScrollSpeed = 0;

      const startAutoScroll = () => {
        if (autoScrollRaf) return;
        const step = () => {
          if (autoScrollSpeed !== 0) {
            window.scrollBy(0, autoScrollSpeed);
          }
          autoScrollRaf = requestAnimationFrame(step);
        };
        autoScrollRaf = requestAnimationFrame(step);
      };

      const stopAutoScroll = () => {
        if (autoScrollRaf) {
          cancelAnimationFrame(autoScrollRaf);
          autoScrollRaf = null;
        }
        autoScrollSpeed = 0;
      };

      const clearDropTargets = () => {
        document.querySelectorAll(".farming-zone-card, .farming-zone-slot")
          .forEach((t) => t.classList.remove("farming-drop-target"));
      };

      const startDrag = () => {
        if (dragStarted) return;
        dragStarted = true;
        item.classList.add("is-dragging");
        dragGhost = item.cloneNode(true);
        dragGhost.classList.add("farming-drag-ghost");
        dragGhost.style.transform = `translate3d(${startX}px, ${startY}px, 0) translate(-50%, -50%) scale(1.08)`;
        document.body.appendChild(dragGhost);
        if (pointerId !== null) item.setPointerCapture?.(pointerId);
      };

      item.addEventListener("pointerdown", (e) => {
        if (e.pointerType === "mouse" && e.button !== 0) return;
        startX = e.clientX;
        startY = e.clientY;
        pointerId = e.pointerId;
        dragStarted = false;
        if (e.pointerType === "mouse") {
          item.setPointerCapture?.(pointerId);
        }
      });

      item.addEventListener("pointermove", (e) => {
        if (pointerId === null || e.pointerId !== pointerId) return;
        const dist = Math.hypot(e.clientX - startX, e.clientY - startY);
        if (!dragStarted && dist > 5) startDrag();

        if (dragStarted && dragGhost) {
          dragGhost.style.transform = `translate3d(${e.clientX}px, ${e.clientY}px, 0) translate(-50%, -50%) scale(1.08)`;
          clearDropTargets();
          const under = document.elementFromPoint(e.clientX, e.clientY);
          const zoneTarget = under?.closest("[data-zone-key]");
          if (zoneTarget) zoneTarget.closest(".farming-zone-card")?.classList.add("farming-drop-target");

          // Auto-scroll al acercarse a los bordes superior/inferior (crucial en celulares)
          const edgeThreshold = 100;
          const vh = window.innerHeight;
          const y = e.clientY;

          if (y < edgeThreshold) {
            const intensity = Math.min(1, Math.max(0, (edgeThreshold - y) / edgeThreshold));
            autoScrollSpeed = -Math.round(6 + intensity * 18);
            startAutoScroll();
          } else if (y > vh - edgeThreshold) {
            const intensity = Math.min(1, Math.max(0, (y - (vh - edgeThreshold)) / edgeThreshold));
            autoScrollSpeed = Math.round(6 + intensity * 18);
            startAutoScroll();
          } else {
            autoScrollSpeed = 0;
          }
        }
      });

      const endDrag = (e) => {
        stopAutoScroll();
        if (pointerId === null || e.pointerId !== pointerId) return;
        if (dragStarted) {
          try {
            if (pointerId !== null) item.releasePointerCapture?.(pointerId);
          } catch (_) {}
          const under = document.elementFromPoint(e.clientX, e.clientY);
          const zoneTarget = under?.closest("[data-zone-key]");
          const zoneKey = zoneTarget?.dataset?.zoneKey || zoneTarget?.closest(".farming-zone-card")?.dataset?.zoneKey;
          if (zoneKey) {
            const pokeIdx = Number(item.dataset.pokeIdx);
            assignPokeToZone(pokeIdx, zoneKey);
          }
          if (dragGhost) {
            dragGhost.remove();
            dragGhost = null;
          }
          item.classList.remove("is-dragging");
          clearDropTargets();
        } else {
          try {
            if (pointerId !== null) item.releasePointerCapture?.(pointerId);
          } catch (_) {}
        }
        pointerId = null;
        dragStarted = false;
      };

      item.addEventListener("pointerup", endDrag);
      item.addEventListener("pointercancel", endDrag);
    });
  }

  resetState() {
    this.latestState = null;
    this._lastFusionResult = null;
    this._lastFusionFailureMessage = null;
  }
}
