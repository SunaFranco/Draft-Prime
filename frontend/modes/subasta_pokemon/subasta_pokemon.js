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

    // Avanzar Etapa (Host)
    const btnForceNext = document.getElementById("btn-force-next-stage");
    const btnNextStageExport = document.getElementById("btn-next-stage-export");
    [btnForceNext, btnNextStageExport].forEach((btn) => {
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
        // no-op; el texto ya se actualiza al renderizar el estado
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

