/**
 * frontend/modes/subasta_pokemon/subasta_pve_team_builder.js
 * Modal de selección y preparación de equipo PVE con mini-caja 2x3 (6 slots).
 * Soporta Drag & Drop (Pointer Events) y selección táctil/clic rápida para móvil y desktop.
 */

import { buildPokemonSpriteMarkup } from "./subasta_ui_components.js";

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

const TYPE_COLORS = {
  normal: "#94a3b8", fire: "#f97316", water: "#38bdf8", electric: "#facc15",
  grass: "#4ade80", ice: "#67e8f9", fighting: "#e11d48", poison: "#a855f7",
  ground: "#d97706", flying: "#818cf8", psychic: "#f43f5e", bug: "#84cc16",
  rock: "#b45309", ghost: "#7e22ce", dragon: "#6366f1", steel: "#64748b",
  fairy: "#f472b6", dark: "#334155"
};

function getPokemonCleanName(poke) {
  if (!poke) return "";
  const name = poke.species || poke.name || "";
  return String(name).toLowerCase().replace("mega ", "").replace("-mega", "").replace(" ", "-").trim();
}

function getShowdownSpriteUrl(poke) {
  if (!poke) return "";
  const clean = getPokemonCleanName(poke);
  return `https://play.pokemonshowdown.com/sprites/gen5/${clean}.png`;
}

/**
 * Abre el modal con la mini-caja 2x3 para armar el equipo de combate PVE.
 * @param {Object} state Estado de la subasta/draft
 * @param {string} initialPresetId ID del rival predeterminado (ej: 'brock-rock')
 */
export function openPveTeamBuilderModal(state, initialPresetId = "brock-rock") {
  const existingOverlay = document.getElementById("pve-team-builder-overlay");
  if (existingOverlay) existingOverlay.remove();

  const myData = state?.my_data || {};
  const allPokemon = myData.pokemon || [];
  if (!allPokemon || allPokemon.length === 0) {
    alert("No tienes Pokémon en tus cajas para combatir.");
    return;
  }

  const boxes = myData.pokemon_boxes || [{ id: "box-1", name: "Caja 1" }];
  let activeBoxId = boxes[0]?.id || "box-1";

  // Intentar restaurar equipo guardado previamente de localStorage
  let savedIndices = [];
  try {
    const rawSaved = localStorage.getItem("pve_team_saved_order");
    if (rawSaved) savedIndices = JSON.parse(rawSaved);
  } catch (e) {
    console.warn("No se pudo leer pve_team_saved_order:", e);
  }

  // Mini-caja de 6 slots (2 filas x 3 columnas)
  // currentTeamSlots contiene los índices de allPokemon colocados en cada slot (0..5) o null
  const currentTeamSlots = [null, null, null, null, null, null];

  if (Array.isArray(savedIndices) && savedIndices.length > 0) {
    savedIndices.slice(0, 6).forEach((idx, slotIdx) => {
      if (typeof idx === "number" && allPokemon[idx]) {
        currentTeamSlots[slotIdx] = idx;
      }
    });
  } else {
    // Si no hay guardado, autollenar con los primeros hasta 6 Pokémon
    for (let i = 0; i < Math.min(6, allPokemon.length); i++) {
      currentTeamSlots[i] = i;
    }
  }

  let selectedPreset = initialPresetId;

  // Crear el contenedor Overlay del modal
  const overlay = document.createElement("div");
  overlay.id = "pve-team-builder-overlay";
  overlay.className = "pve-builder-overlay";

  overlay.innerHTML = `
    <div class="pve-builder-modal" role="dialog" aria-modal="true" aria-labelledby="pve-builder-title">
      <div class="pve-builder-header">
        <div>
          <h3 id="pve-builder-title">⚔️ Preparar Equipo de Combate</h3>
          <p class="pve-builder-subtitle">Arrastra tus Pokémon a la mini-caja 2×3 para definir tu alineación. El <strong>Slot #1</strong> será tu Pokémon Líder.</p>
        </div>
        <button type="button" class="btn-close-builder" aria-label="Cerrar modal">✕</button>
      </div>

      <div class="pve-builder-body">
        <!-- SECCIÓN 1: MINI-CAJA 2x3 (6 SLOTS) -->
        <section class="pve-team-section">
          <div class="pve-team-section-header">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="pve-section-title">🥊 Mini-Caja del Equipo (2×3)</span>
              <span id="pve-team-count-badge" class="pve-team-count-badge">0 / 6 Listos</span>
            </div>
            <div class="pve-quick-actions">
              <button type="button" id="btn-team-autofill" class="btn btn-small btn-secondary" title="Llena los slots vacíos con los primeros Pokémon disponibles">⚡ Autollenar 6</button>
              <button type="button" id="btn-team-clear" class="btn btn-small btn-secondary" title="Vaciar todos los slots">🧹 Vaciar</button>
            </div>
          </div>

          <div class="pve-team-box-grid" id="pve-team-box-grid">
            <!-- Se renderiza dinámicamente -->
          </div>
        </section>

        <!-- SECCIÓN 2: SELECCIÓN DE RIVAL -->
        <section class="pve-preset-section">
          <label for="select-modal-preset" class="pve-preset-label">🎯 Entrenador Rival:</label>
          <select id="select-modal-preset" class="pve-preset-select">
            <option value="brock-rock" ${selectedPreset === "brock-rock" ? "selected" : ""}>Líder Brock (Roca · Fácil)</option>
            <option value="cynthia-sinnoh" ${selectedPreset === "cynthia-sinnoh" ? "selected" : ""}>Campeona Cynthia (Balanceado · Difícil)</option>
            <option value="red-kanto" ${selectedPreset === "red-kanto" ? "selected" : ""}>Entrenador Red (Kanto · Difícil)</option>
          </select>
        </section>

        <!-- SECCIÓN 3: CAJAS DE POKÉMON DEL JUGADOR (ORIGEN) -->
        <section class="pve-boxes-section">
          <div class="pve-boxes-section-header">
            <span class="pve-section-title">📦 Tus Pokémon en Cajas</span>
            <span class="pve-boxes-hint">Toca o arrastra para añadir / quitar</span>
          </div>

          <!-- Pestañas de cajas si hay más de una -->
          ${boxes.length > 1 ? `
            <div class="pve-box-tabs" role="tablist">
              ${boxes.map((b, idx) => `
                <button type="button" class="pve-box-tab ${b.id === activeBoxId ? 'is-active' : ''}" data-box-id="${escapeHtml(b.id)}">
                  ${escapeHtml(b.name || `Caja ${idx + 1}`)}
                </button>
              `).join("")}
            </div>
          ` : ""}

          <div class="pve-source-grid" id="pve-source-grid">
            <!-- Se renderiza dinámicamente -->
          </div>
        </section>
      </div>

      <div class="pve-builder-footer">
        <button type="button" id="btn-builder-cancel" class="btn btn-secondary">Cancelar</button>
        <button type="button" id="btn-builder-launch" class="btn btn-warning btn-start-battle">⚔️ ¡Entrar al Combate!</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  // Funciones de renderizado reactivo
  const renderTeamGrid = () => {
    const gridEl = overlay.querySelector("#pve-team-box-grid");
    if (!gridEl) return;

    gridEl.innerHTML = currentTeamSlots.map((pokeIdx, slotIdx) => {
      const isLeader = slotIdx === 0;
      const slotLabel = isLeader ? "👑 Slot 1 (Líder)" : `Slot ${slotIdx + 1}`;
      const poke = pokeIdx !== null ? allPokemon[pokeIdx] : null;

      if (!poke) {
        return `
          <div class="pve-team-slot is-empty" data-team-slot="${slotIdx}" tabindex="0" role="button" aria-label="${slotLabel} vacío">
            <div class="pve-slot-header">
              <span class="pve-slot-num">${slotLabel}</span>
            </div>
            <div class="pve-slot-empty-content">
              <span class="pve-empty-plus">+</span>
              <span class="pve-empty-text">Arrastra o toca un Pokémon</span>
            </div>
          </div>
        `;
      }

      const clean = getPokemonCleanName(poke);
      const showdownSprite = getShowdownSpriteUrl(poke);
      const fallbackSprite = poke.image_url || `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${poke.id || 1}.png`;
      const pokeTypes = poke.types || [];

      return `
        <div class="pve-team-slot is-filled ${isLeader ? 'is-team-leader' : ''}" data-team-slot="${slotIdx}" data-poke-idx="${pokeIdx}" draggable="true" role="button" tabindex="0">
          <div class="pve-slot-header">
            <span class="pve-slot-num">${slotLabel}</span>
            <button type="button" class="btn-remove-slot" data-remove-slot="${slotIdx}" title="Quitar Pokémon del equipo">✕</button>
          </div>
          <div class="pve-slot-content">
            <img class="pve-slot-sprite" src="${showdownSprite}" alt="${escapeHtml(poke.name || poke.species)}"
              onerror="if (!this.dataset.fallback) { this.dataset.fallback = '1'; this.src = '${escapeHtml(fallbackSprite)}'; } else { this.style.visibility = 'hidden'; }" />
            <div class="pve-slot-info">
              <span class="pve-slot-name">${escapeHtml(poke.name || poke.species || "Pokémon")}</span>
              <span class="pve-slot-lvl">Lv. ${poke.level || 50}</span>
              <div class="pve-slot-types">
                ${pokeTypes.map(t => {
                  const bg = TYPE_COLORS[t.toLowerCase()] || "#64748b";
                  return `<span class="pve-type-mini" style="background-color: ${bg};">${t.slice(0, 3)}</span>`;
                }).join("")}
              </div>
            </div>
          </div>
        </div>
      `;
    }).join("");

    // Actualizar badge de contador
    const activeCount = currentTeamSlots.filter(s => s !== null).length;
    const badgeEl = overlay.querySelector("#pve-team-count-badge");
    if (badgeEl) {
      badgeEl.textContent = `${activeCount} / 6 Listos`;
      badgeEl.className = `pve-team-count-badge ${activeCount > 0 ? 'has-pokemon' : ''}`;
    }

    attachTeamSlotEvents();
  };

  const renderSourceBoxes = () => {
    const sourceGridEl = overlay.querySelector("#pve-source-grid");
    if (!sourceGridEl) return;

    // Filtrar Pokémon pertenecientes a la caja activa
    const boxPokemonEntries = allPokemon
      .map((poke, index) => ({ poke, index }))
      .filter(({ poke }) => (poke.box_id || boxes[0]?.id || "box-1") === activeBoxId);

    if (boxPokemonEntries.length === 0) {
      sourceGridEl.innerHTML = `<div class="pve-empty-box-msg">No hay Pokémon en esta caja.</div>`;
      return;
    }

    sourceGridEl.innerHTML = boxPokemonEntries.map(({ poke, index }) => {
      const isAssigned = currentTeamSlots.includes(index);
      const assignedSlotIdx = isAssigned ? currentTeamSlots.indexOf(index) : -1;
      const showdownSprite = getShowdownSpriteUrl(poke);
      const fallbackSprite = poke.image_url || `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${poke.id || 1}.png`;

      return `
        <div class="pve-source-poke ${isAssigned ? 'is-assigned' : ''}" data-poke-idx="${index}" draggable="true" tabindex="0" role="button"
          title="${escapeHtml(poke.name)} — Clic para asignar o arrastra a la mini-caja">
          ${isAssigned ? `<span class="pve-assigned-badge">#${assignedSlotIdx + 1}</span>` : ""}
          <img class="pve-source-sprite" src="${showdownSprite}" alt="${escapeHtml(poke.name)}" loading="lazy"
            onerror="if (!this.dataset.fallback) { this.dataset.fallback = '1'; this.src = '${escapeHtml(fallbackSprite)}'; } else { this.style.visibility = 'hidden'; }" />
          <div class="pve-source-details">
            <span class="pve-source-name">${escapeHtml(poke.name || poke.species)}</span>
            <span class="pve-source-lvl">Lv. ${poke.level || 50}</span>
          </div>
        </div>
      `;
    }).join("");

    attachSourcePokeEvents();
  };

  // Asignar un Pokémon a un slot específico de la mini-caja
  const assignToSlot = (sourcePokeIdx, targetSlotIdx) => {
    if (typeof sourcePokeIdx !== "number" || targetSlotIdx < 0 || targetSlotIdx > 5) return;

    // Si el Pokémon ya estaba en otro slot de la mini-caja, lo movemos (intercambio)
    const existingSlot = currentTeamSlots.indexOf(sourcePokeIdx);
    const prevInTarget = currentTeamSlots[targetSlotIdx];

    if (existingSlot !== -1) {
      currentTeamSlots[existingSlot] = prevInTarget;
    }
    currentTeamSlots[targetSlotIdx] = sourcePokeIdx;

    renderTeamGrid();
    renderSourceBoxes();
  };

  // Clic rápido en un Pokémon de la caja de origen
  const toggleFromSource = (pokeIdx) => {
    const existingSlot = currentTeamSlots.indexOf(pokeIdx);
    if (existingSlot !== -1) {
      // Si ya está asignado, quitarlo
      currentTeamSlots[existingSlot] = null;
    } else {
      // Asignar al primer slot libre (0..5)
      const firstFreeSlot = currentTeamSlots.findIndex(s => s === null);
      if (firstFreeSlot !== -1) {
        currentTeamSlots[firstFreeSlot] = pokeIdx;
      } else {
        // Si todos están llenos, reemplazar el último slot (slot 5)
        currentTeamSlots[5] = pokeIdx;
      }
    }
    renderTeamGrid();
    renderSourceBoxes();
  };

  // Drag & Drop con Pointer Events y Drag Events
  let draggingPokeIdx = null;
  let draggingFromSlot = null;
  let dragGhost = null;

  const clearDragHighlights = () => {
    overlay.querySelectorAll(".pve-team-slot.drop-hover").forEach(el => el.classList.remove("drop-hover"));
  };

  const attachTeamSlotEvents = () => {
    // Botones de remoción individual
    overlay.querySelectorAll(".btn-remove-slot").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const slotIdx = Number(btn.dataset.removeSlot);
        if (!isNaN(slotIdx) && slotIdx >= 0 && slotIdx <= 5) {
          currentTeamSlots[slotIdx] = null;
          renderTeamGrid();
          renderSourceBoxes();
        }
      });
    });

    // Slots de la mini-caja como Drop Targets
    overlay.querySelectorAll(".pve-team-slot").forEach(slotEl => {
      const slotIdx = Number(slotEl.dataset.teamSlot);

      // Dragstart desde la mini-caja para reordenar
      slotEl.addEventListener("dragstart", (e) => {
        const pokeIdx = Number(slotEl.dataset.pokeIdx);
        if (!isNaN(pokeIdx)) {
          draggingPokeIdx = pokeIdx;
          draggingFromSlot = slotIdx;
          e.dataTransfer.setData("text/plain", String(pokeIdx));
          e.dataTransfer.effectAllowed = "move";
        }
      });

      slotEl.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        slotEl.classList.add("drop-hover");
      });

      slotEl.addEventListener("dragleave", () => {
        slotEl.classList.remove("drop-hover");
      });

      slotEl.addEventListener("drop", (e) => {
        e.preventDefault();
        slotEl.classList.remove("drop-hover");
        const idx = draggingPokeIdx !== null ? draggingPokeIdx : Number(e.dataTransfer.getData("text/plain"));
        if (!isNaN(idx) && allPokemon[idx]) {
          assignToSlot(idx, slotIdx);
        }
        draggingPokeIdx = null;
        draggingFromSlot = null;
      });

      // Pointer events para soporte táctil / mobile
      let pointerStartX = 0;
      let pointerStartY = 0;
      let isDraggingPointer = false;

      slotEl.addEventListener("pointerdown", (e) => {
        if (e.target.closest(".btn-remove-slot")) return;
        const pokeIdx = Number(slotEl.dataset.pokeIdx);
        if (isNaN(pokeIdx)) return;

        pointerStartX = e.clientX;
        pointerStartY = e.clientY;
        isDraggingPointer = false;
        draggingPokeIdx = pokeIdx;
        draggingFromSlot = slotIdx;

        const onPointerMove = (ev) => {
          const dist = Math.hypot(ev.clientX - pointerStartX, ev.clientY - pointerStartY);
          if (dist > 8 && !isDraggingPointer) {
            isDraggingPointer = true;
            dragGhost = slotEl.cloneNode(true);
            dragGhost.className = "pve-drag-ghost";
            dragGhost.style.left = `${ev.clientX}px`;
            dragGhost.style.top = `${ev.clientY}px`;
            document.body.appendChild(dragGhost);
          }
          if (isDraggingPointer && dragGhost) {
            dragGhost.style.left = `${ev.clientX}px`;
            dragGhost.style.top = `${ev.clientY}px`;
            clearDragHighlights();
            const target = document.elementFromPoint(ev.clientX, ev.clientY)?.closest(".pve-team-slot");
            if (target) target.classList.add("drop-hover");
          }
        };

        const onPointerUp = (ev) => {
          window.removeEventListener("pointermove", onPointerMove);
          window.removeEventListener("pointerup", onPointerUp);
          window.removeEventListener("pointercancel", onPointerUp);
          if (dragGhost) {
            dragGhost.remove();
            dragGhost = null;
          }
          clearDragHighlights();

          if (isDraggingPointer) {
            const target = document.elementFromPoint(ev.clientX, ev.clientY)?.closest(".pve-team-slot");
            if (target) {
              const targetSlot = Number(target.dataset.teamSlot);
              if (!isNaN(targetSlot)) {
                assignToSlot(draggingPokeIdx, targetSlot);
              }
            }
          }
          draggingPokeIdx = null;
          draggingFromSlot = null;
        };

        window.addEventListener("pointermove", onPointerMove);
        window.addEventListener("pointerup", onPointerUp);
        window.addEventListener("pointercancel", onPointerUp);
      });
    });
  };

  const attachSourcePokeEvents = () => {
    overlay.querySelectorAll(".pve-source-poke").forEach(pokeEl => {
      const pokeIdx = Number(pokeEl.dataset.pokeIdx);

      // Clic directo
      pokeEl.addEventListener("click", () => {
        toggleFromSource(pokeIdx);
      });

      // Drag nativo de escritorio
      pokeEl.addEventListener("dragstart", (e) => {
        draggingPokeIdx = pokeIdx;
        draggingFromSlot = null;
        e.dataTransfer.setData("text/plain", String(pokeIdx));
        e.dataTransfer.effectAllowed = "copyMove";
      });

      // Pointer events para drag táctil
      let pointerStartX = 0;
      let pointerStartY = 0;
      let isDraggingPointer = false;

      pokeEl.addEventListener("pointerdown", (e) => {
        pointerStartX = e.clientX;
        pointerStartY = e.clientY;
        isDraggingPointer = false;
        draggingPokeIdx = pokeIdx;
        draggingFromSlot = null;

        const onPointerMove = (ev) => {
          const dist = Math.hypot(ev.clientX - pointerStartX, ev.clientY - pointerStartY);
          if (dist > 8 && !isDraggingPointer) {
            isDraggingPointer = true;
            dragGhost = pokeEl.cloneNode(true);
            dragGhost.className = "pve-drag-ghost";
            dragGhost.style.left = `${ev.clientX}px`;
            dragGhost.style.top = `${ev.clientY}px`;
            document.body.appendChild(dragGhost);
          }
          if (isDraggingPointer && dragGhost) {
            dragGhost.style.left = `${ev.clientX}px`;
            dragGhost.style.top = `${ev.clientY}px`;
            clearDragHighlights();
            const target = document.elementFromPoint(ev.clientX, ev.clientY)?.closest(".pve-team-slot");
            if (target) target.classList.add("drop-hover");
          }
        };

        const onPointerUp = (ev) => {
          window.removeEventListener("pointermove", onPointerMove);
          window.removeEventListener("pointerup", onPointerUp);
          window.removeEventListener("pointercancel", onPointerUp);
          if (dragGhost) {
            dragGhost.remove();
            dragGhost = null;
          }
          clearDragHighlights();

          if (isDraggingPointer) {
            const target = document.elementFromPoint(ev.clientX, ev.clientY)?.closest(".pve-team-slot");
            if (target) {
              const targetSlot = Number(target.dataset.teamSlot);
              if (!isNaN(targetSlot)) {
                assignToSlot(draggingPokeIdx, targetSlot);
              }
            }
          }
          draggingPokeIdx = null;
        };

        window.addEventListener("pointermove", onPointerMove);
        window.addEventListener("pointerup", onPointerUp);
        window.addEventListener("pointercancel", onPointerUp);
      });
    });
  };

  // Botones rápidos de autollenar y vaciar
  const btnAutofill = overlay.querySelector("#btn-team-autofill");
  if (btnAutofill) {
    btnAutofill.addEventListener("click", () => {
      const assigned = new Set(currentTeamSlots.filter(s => s !== null));
      for (let s = 0; s < 6; s++) {
        if (currentTeamSlots[s] === null) {
          const nextFreePoke = allPokemon.findIndex((_, idx) => !assigned.has(idx));
          if (nextFreePoke !== -1) {
            currentTeamSlots[s] = nextFreePoke;
            assigned.add(nextFreePoke);
          }
        }
      }
      renderTeamGrid();
      renderSourceBoxes();
    });
  }

  const btnClear = overlay.querySelector("#btn-team-clear");
  if (btnClear) {
    btnClear.addEventListener("click", () => {
      for (let s = 0; s < 6; s++) {
        currentTeamSlots[s] = null;
      }
      renderTeamGrid();
      renderSourceBoxes();
    });
  }

  // Cambio de pestaña de cajas de origen
  overlay.querySelectorAll(".pve-box-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      const boxId = tab.dataset.boxId;
      if (boxId && boxId !== activeBoxId) {
        activeBoxId = boxId;
        overlay.querySelectorAll(".pve-box-tab").forEach(t => t.classList.toggle("is-active", t.dataset.boxId === boxId));
        renderSourceBoxes();
      }
    });
  });

  // Selector de Preset Rival
  const selectPresetEl = overlay.querySelector("#select-modal-preset");
  if (selectPresetEl) {
    selectPresetEl.addEventListener("change", () => {
      selectedPreset = selectPresetEl.value;
    });
  }

  // Cierre del modal
  const closeModal = () => {
    overlay.classList.add("closing");
    setTimeout(() => overlay.remove(), 200);
  };

  overlay.querySelector(".btn-close-builder")?.addEventListener("click", closeModal);
  overlay.querySelector("#btn-builder-cancel")?.addEventListener("click", closeModal);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeModal();
  });

  // Botón Lanzar Batalla
  const btnLaunch = overlay.querySelector("#btn-builder-launch");
  if (btnLaunch) {
    btnLaunch.addEventListener("click", () => {
      const selectedIndices = currentTeamSlots.filter(idx => idx !== null);
      if (selectedIndices.length === 0) {
        alert("Debes seleccionar al menos 1 Pokémon en la mini-caja para combatir.");
        return;
      }

      // Guardar el equipo elegido ordenado en el storage
      const finalTeam = selectedIndices.map(idx => allPokemon[idx]);
      try {
        localStorage.setItem("pve_team_saved_order", JSON.stringify(currentTeamSlots));
      } catch (e) {
        console.warn("Error guardando pve_team_saved_order:", e);
      }

      const currentYear = state.current_year || (state.current_stage <= 5 ? 1 : (state.current_stage <= 9 ? 2 : 3));
      const setup = {
        preset_id: selectedPreset || "brock-rock",
        year: currentYear,
        player_team: finalTeam,
        return_url: window.location.href,
      };

      try {
        sessionStorage.setItem("pve_setup", JSON.stringify(setup));
      } catch (e) {
        console.warn("Error guardando pve_setup:", e);
      }

      window.location.href = "pve_battle.html";
    });
  }

  // Render inicial
  renderTeamGrid();
  renderSourceBoxes();
}
