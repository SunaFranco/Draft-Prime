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
} from "./subasta_ui_components.js";

export class SubastaPokemonModeUI extends BaseGameModeUI {
  constructor() {
    super("subasta_pokemon", "Subasta (Pokemon)");
    this.latestState = null;
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
      html = renderExportView(state, sessionClient, isHost);
    } else {
      // Resultados y Administración (Etapa 13 o intermedia)
      html = renderAdminAndStandingsView(state, sessionClient, isHost);
    }

    const inventoryHtml = renderMyPokemonInventory(state, sessionClient);
    draftContainer.innerHTML = html + "<br/>" + inventoryHtml;
    this.attachEventListeners(state, sessionClient, isHost);
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
          sessionClient.send({ action: "subasta_bid", bid_amount: val });
        }
      });
    }

    // Compra Directa
    const btnBuyout = document.getElementById("btn-buyout");
    if (btnBuyout) {
      btnBuyout.addEventListener("click", () => {
        sessionClient.send({ action: "subasta_buyout" });
      });
    }

    // Retirarse (Fold)
    const btnFold = document.getElementById("btn-fold");
    if (btnFold) {
      btnFold.addEventListener("click", () => {
        sessionClient.send({ action: "subasta_fold" });
      });
    }

    // Elección Secreta (Ganador)
    const btnSecretYes = document.getElementById("btn-secret-yes");
    const btnSecretNo = document.getElementById("btn-secret-no");
    if (btnSecretYes) {
      btnSecretYes.addEventListener("click", () => {
        sessionClient.send({ action: "subasta_secret_choice", keep_secret: true });
      });
    }
    if (btnSecretNo) {
      btnSecretNo.addEventListener("click", () => {
        sessionClient.send({ action: "subasta_secret_choice", keep_secret: false });
      });
    }

    // Resolver Evento de Turno
    const btnResolveEvent = document.getElementById("btn-resolve-event");
    if (btnResolveEvent) {
      btnResolveEvent.addEventListener("click", () => {
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

    // Avanzar Etapa (Host)
    const btnForceNext = document.getElementById("btn-force-next-stage");
    [btnForceNext].forEach((btn) => {
      if (btn) {
        btn.addEventListener("click", () => {
          sessionClient.send({ action: "subasta_next_stage" });
        });
      }
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
        sessionClient.send({ action: "subasta_evolve_pokemon", poke_index: pokeIdx });
      });
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

    document.querySelectorAll(".backpack-toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        const menu = btn.parentElement?.querySelector(".backpack-menu");
        if (!menu) return;
        const isOpen = menu.classList.toggle("backpack-menu--open");
        btn.setAttribute("aria-expanded", String(isOpen));
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

    document.querySelectorAll(".btn-use-tm").forEach((btn) => {
      btn.addEventListener("click", () => {
        const row = btn.closest(".bag-item-row");
        const pokemonSelect = row?.querySelector(".tm-pokemon-select");
        if (!pokemonSelect) return;
        sessionClient.send({
          action: "subasta_use_tm",
          poke_index: parseInt(pokemonSelect.value, 10),
          item_name: btn.getAttribute("data-item-name"),
        });
      });
    });

    document.querySelectorAll(".btn-buy-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        const itemName = btn.getAttribute("data-item-name");
        if (!itemName) return;
        sessionClient.send({ action: "subasta_shop_buy", item_name: itemName });
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

