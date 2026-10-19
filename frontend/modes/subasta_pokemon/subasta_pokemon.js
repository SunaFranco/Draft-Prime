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
        $0
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
      counter.textContent = `$${current.toLocaleString()}`;
      const progress = current / maxAmount;
      // Empieza en 350ms y se va ralentizando hasta ~950ms conforme sube el valor
      const delay = 350 + progress * 600;
      await wait(delay);
    }
    counter.textContent = `$${finalAmount.toLocaleString()}`;
    counter.style.color = "#22c55e";
    status.innerHTML = `<span style="color: #22c55e; font-size: 1.1rem; font-weight: bold;">¡Vendido por $${finalAmount.toLocaleString()}!</span>`;
  }

  await wait(3000);
  overlay.remove();
  onComplete();
}

export class SubastaPokemonModeUI extends BaseGameModeUI {
  constructor() {
    super("subasta_pokemon", "Subasta (Pokemon)");
    this.latestState = null;
    this._lockedShowdownText = null;
    this._isRouletteSpinning = false;
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
    }
    if (event === "subasta_state_update" || (event === "session_state" && data.draft_state)) {
      const state = event === "subasta_state_update" ? data : data.draft_state;
      if (!state || Object.keys(state).length === 0) return false;

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


    const stage = state.stage || 2;

    let html = "";
    if ([2, 6, 10].includes(stage)) {
      // Subastas (Año 1, 2, 3)
      html = renderAuctionView(state, sessionClient, isHost);
    } else if ([3, 7, 11].includes(stage)) {
      // Eventos de Turno (Año 1, 2, 3)
      html = renderTurnEventsView(state, sessionClient, isHost);
    } else if ([4, 8, 12].includes(stage)) {
      // Exportación a Showdown (Año 1, 2, 3)
      html = renderExportView(state, sessionClient, isHost, this._lockedShowdownText);
    } else {
      // Resultados y Administración (Etapa 13 o intermedia)
      html = renderAdminAndStandingsView(state, sessionClient, isHost);
    }

    const openModal = document.querySelector(".inventory-modal-overlay.is-open");
    const currentlyOpenTarget = openModal ? openModal.dataset.modal : null;
    document.querySelectorAll("body > .inventory-modal-overlay").forEach((el) => el.remove());

    const inventoryHtml = renderMyPokemonInventory(state, sessionClient);
    draftContainer.innerHTML = html + "<br/>" + inventoryHtml;
    this.attachEventListeners(state, sessionClient, isHost);

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
        const winner = document.getElementById("admin-match-winner").value;
        const loser = document.getElementById("admin-match-loser").value;
        if (winner && loser && winner !== loser) {
          sessionClient.send({ action: "subasta_admin_submit_match", winner, loser });
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
