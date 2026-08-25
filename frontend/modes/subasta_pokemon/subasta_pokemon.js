/**
 * modes/subasta_pokemon/subasta_pokemon.js — Stub para UI del modo Subasta Pokémon
 */

import { BaseGameModeUI } from "../base_mode.js";
import { showScreen, logEvent } from "../../js/core/ui.js";

export class SubastaPokemonModeUI extends BaseGameModeUI {
  constructor() {
    super("subasta_pokemon", "Subasta (Pokemon)");
  }

  renderConfigFields(containerEl, data, isHost) {
    containerEl.innerHTML = `
      <div class="card" style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px;">
        <p style="color: var(--muted); font-size: 0.9rem;">
          Este modo utilizará la subasta de Pokémon. Las configuraciones específicas estarán disponibles próximamente.
        </p>
      </div>
    `;
  }

  readConfigFields(containerEl) {
    return {};
  }

  handleEvent(event, data, context) {
    // Stub preparado para recibir eventos de subasta Pokémon en el futuro
    return false;
  }
}
