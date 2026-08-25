/**
 * modes/subasta_pokemon/subasta_pokemon.js — Stub para UI del modo Subasta Pokémon
 */

import { BaseGameModeUI } from "../base_mode.js";

export class SubastaPokemonModeUI extends BaseGameModeUI {
  constructor() {
    super("subasta_pokemon", "Subasta (Pokemon)");
  }

  renderConfigFields(containerEl, data, isHost) {
    const cubeSelect = document.getElementById("cube-select");
    const packCount = document.getElementById("pack-count");
    const cardsPerPack = document.getElementById("cards-per-pack");

    // Ocultar controles de draft de Yu-Gi-Oh para subasta
    [cubeSelect, packCount, cardsPerPack].forEach((el) => {
      if (el) {
        el.style.display = "none";
        const label = document.querySelector(`label[for="${el.id}"]`);
        if (label) label.style.display = "none";
      }
    });
  }

  readConfigFields(containerEl) {
    return {};
  }

  handleEvent(event, data, context) {
    return false;
  }
}
