/**
 * frontend/modes/subasta_pokemon/subasta_pokemon.js — UI Controller para Subasta Pokémon
 */

import { BaseGameModeUI } from "../base_mode.js";
import { showScreen } from "../../js/core/ui.js";
import {
  renderConfigForm,
  readConfigForm,
  renderAuctionView,
  renderTurnEventsView,
  renderExportView,
  renderAdminAndStandingsView,
  renderMyPokemonInventory,
  POKEMON_CARD_COLORS,
  formatMoneyCompact,
  NATURE_EFFECTS,
  formatNature,
  getTmMoveName,
  checkTmCompatibility,
  buildItemSpriteUrl,
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
    this._pokemonColorStorageKey = null;
    this._pokemonCardColors = {};
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
    if (event === "subasta_mystery_box_result") {
      playMysteryBoxRoulette(data, () => {
        this._isRouletteSpinning = false;
      });
      return true;
    }
    if (event === "error") {
      this._isRouletteSpinning = false;
      const btnTransferHost = document.getElementById("btn-transfer-host");
      if (btnTransferHost) btnTransferHost.disabled = false;
    }
    if (event === "player_joined" || event === "player_left" || event === "host_changed") {
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

  renderCurrentStageView(state, sessionClient, isHost) {
    showScreen("draft");
    const draftContainer = document.getElementById("screen-draft");
    if (!draftContainer) return;

    const colorStorageKey = `draft_prime_subasta_pokemon_colors:${sessionClient.currentSessionId}:${sessionClient.currentUsername}`;
    if (this._pokemonColorStorageKey !== colorStorageKey) {
      this._pokemonColorStorageKey = colorStorageKey;
      this._pokemonCardColors = {};
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

    const pokemonCardState = Array.from(draftContainer.querySelectorAll(".poke-inventory-item")).map((card) => ({
      index: card.dataset.pokeIdx,
      name: card.querySelector(".poke-inventory-name")?.textContent,
      isOpen: card.open,
    }));
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
    } else {
      // Resultados y Administración (Etapa 13 o intermedia)
      html = renderAdminAndStandingsView(state, sessionClient, isHost);
    }

    const openModal = isTeamLocked ? null : document.querySelector(".inventory-modal-overlay.is-open");
    const currentlyOpenTarget = openModal ? openModal.dataset.modal : null;
    document.querySelectorAll("body > .inventory-modal-overlay").forEach((el) => el.remove());

    const inventoryHtml = isTeamLocked ? "" : renderMyPokemonInventory(
      state,
      sessionClient,
      isHost,
      this._activePokemonBoxId,
      this._pokemonCardColors
    );
    draftContainer.innerHTML = html + "<br/>" + inventoryHtml;
    this.attachEventListeners(state, sessionClient, isHost);

    pokemonCardState.forEach(({ index, name, isOpen }) => {
      const pokemon = state.my_data?.pokemon?.[Number(index)];
      if (!pokemon || pokemon.name !== name) return;
      const card = draftContainer.querySelector(`.poke-inventory-item[data-poke-idx="${index}"]`);
      if (!card) return;
      card.open = isOpen;
    });

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

    const btnTransferHost = document.getElementById("btn-transfer-host");
    if (btnTransferHost) {
      btnTransferHost.addEventListener("click", () => {
        const targetUsername = document.getElementById("host-transfer-target")?.value;
        if (!targetUsername) return;
        btnTransferHost.disabled = true;
        sessionClient.send({
          action: "transfer_host",
          target_username: targetUsername,
        });
      });
    }

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
        const checkedInputs = document.querySelectorAll(`.move-chk-${pokeIdx}:checked`);
        const selectedMoves = Array.from(checkedInputs).map((el) => el.value);

        if (selectedMoves.length > 4) {
          alert("Solo puedes seleccionar un máximo de 4 movimientos.");
          return;
        }

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
        this.renderCurrentStageView(state, sessionClient, isHost);
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
          .map((ability) => `<option value="${ability}">${ability}</option>`)
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

    document.querySelectorAll(".btn-modify-moves").forEach((btn) => {
      btn.addEventListener("click", () => {
        const box = btn.closest(".moves-selector-box");
        if (box) {
          box.classList.remove("moves-saved");
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

  resetState() {
    this.latestState = null;
  }
}
