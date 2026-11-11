/**
 * frontend/js/pve_battle_ui.js
 * Controlador de combate PVE Mobile-First para Draft Prime.
 */

// Paleta oficial de colores para los tipos de Pokémon
const TYPE_COLORS = {
  Normal: "#94a3b8", Fire: "#ea580c", Water: "#0284c7", Grass: "#16a34a",
  Electric: "#ca8a04", Ice: "#0891b2", Fighting: "#b91c1c", Poison: "#9333ea",
  Ground: "#d97706", Flying: "#7c3aed", Psychic: "#db2777", Bug: "#65a30d",
  Rock: "#78716c", Ghost: "#6b21a8", Dragon: "#4f46e5", Steel: "#64748b",
  Dark: "#334155", Fairy: "#e11d48"
};

// Mapeo básico de especies a IDs de PokeAPI para sprites
const POKE_SPRITE_IDS = {
  charizard: 6, blastoise: 9, venusaur: 3, pikachu: 25, gengar: 94,
  gyarados: 130, lapras: 131, snorlax: 143, aerodactyl: 142, alakazam: 65,
  geodude: 74, onix: 95, golem: 76, kabutops: 141, omastar: 139,
  spiritomb: 442, roserade: 407, togekiss: 468, milotic: 350, garchomp: 445,
  lucario: 448, swampert: 260, sceptile: 254, blaziken: 257, gardevoir: 282,
  tyranitar: 248, scizor: 212, jolteon: 135
};

class PVEBattleController {
  constructor() {
    this.apiUrl = window.API_URL || window.location.origin;
    this.battleId = null;
    this.state = null;
    this.isProcessingTurn = false;
    this.wantsMega = false;

    // Elementos del DOM
    this.dom = {
      txtTrainerName: document.getElementById("txt-trainer-name"),
      txtTurn: document.getElementById("txt-turn"),
      btnExit: document.getElementById("btn-exit"),
      boxDialog: document.getElementById("box-dialog"),
      boxFieldBadges: document.getElementById("box-field-badges"),
      // IA
      txtAiName: document.getElementById("txt-ai-name"),
      txtAiLvl: document.getElementById("txt-ai-lvl"),
      boxAiTypes: document.getElementById("box-ai-types"),
      barAiHp: document.getElementById("bar-ai-hp"),
      txtAiHp: document.getElementById("txt-ai-hp"),
      badgeAiStatus: document.getElementById("badge-ai-status"),
      boxAiModifiers: document.getElementById("box-ai-modifiers"),
      imgAiSprite: document.getElementById("img-ai-sprite"),
      ballsAiBench: document.getElementById("balls-ai-bench"),
      // Jugador
      txtPlayerName: document.getElementById("txt-player-name"),
      txtPlayerLvl: document.getElementById("txt-player-lvl"),
      boxPlayerTypes: document.getElementById("box-player-types"),
      barPlayerHp: document.getElementById("bar-player-hp"),
      txtPlayerHp: document.getElementById("txt-player-hp"),
      badgePlayerStatus: document.getElementById("badge-player-status"),
      boxPlayerModifiers: document.getElementById("box-player-modifiers"),
      imgPlayerSprite: document.getElementById("img-player-sprite"),
      ballsPlayerBench: document.getElementById("balls-player-bench"),
      // Controles
      movesGrid: document.getElementById("moves-grid"),
      btnToggleMega: document.getElementById("btn-toggle-mega"),
      btnOpenSwitch: document.getElementById("btn-open-switch"),
      btnSurrender: document.getElementById("btn-surrender"),
      // Sheet Banca
      sheetSwitch: document.getElementById("sheet-switch"),
      btnCloseSheet: document.getElementById("btn-close-sheet"),
      boxBenchList: document.getElementById("box-bench-list"),
      // Modal Fin
      modalEnd: document.getElementById("modal-end"),
      endTitle: document.getElementById("end-title"),
      endMsg: document.getElementById("end-msg"),
      btnModalReturn: document.getElementById("btn-modal-return"),
    };

    this.bindEvents();
  }

  bindEvents() {
    this.dom.btnExit.addEventListener("click", () => this.handleReturn());
    this.dom.btnModalReturn.addEventListener("click", () => this.handleReturn());
    this.dom.btnSurrender.addEventListener("click", () => this.handleSurrender());

    this.dom.btnToggleMega.addEventListener("click", () => {
      this.wantsMega = !this.wantsMega;
      this.dom.btnToggleMega.classList.toggle("active", this.wantsMega);
      this.dom.btnToggleMega.textContent = this.wantsMega ? "✓ Mega Lista" : "⚡ Megaevolución";
    });

    this.dom.btnOpenSwitch.addEventListener("click", () => this.openBenchSheet());
    this.dom.btnCloseSheet.addEventListener("click", () => this.closeBenchSheet());
  }

  async init() {
    this.setDialog("Conectando con la arena de combate...");

    // 1. Obtener setup guardado en sessionStorage (pasado desde la subasta)
    let setup = null;
    try {
      const raw = sessionStorage.getItem("pve_setup");
      if (raw) setup = JSON.parse(raw);
    } catch (e) {
      console.warn("No se pudo leer pve_setup de sessionStorage:", e);
    }

    // 2. Si no hay setup, usar equipo de prueba por defecto
    if (!setup) {
      setup = {
        preset_id: "brock-rock",
        player_team: [
          {
            species: "Swampert",
            types: ["Water", "Ground"],
            level: 50,
            current_hp: 170, max_hp: 170,
            stats: { hp: 170, atk: 130, def: 110, spa: 105, spd: 110, spe: 80 },
            moves: [
              { name: "Waterfall", type: "Water", category: "physical", base_power: 80, accuracy: 1.0 },
              { name: "Earthquake", type: "Ground", category: "physical", base_power: 100, accuracy: 1.0 },
              { name: "Ice Punch", type: "Ice", category: "physical", base_power: 75, accuracy: 1.0 },
              { name: "Protect", type: "Normal", category: "status", base_power: 0, accuracy: 1.0 },
            ]
          },
          {
            species: "Charizard",
            types: ["Fire", "Flying"],
            level: 50,
            current_hp: 150, max_hp: 150,
            stats: { hp: 150, atk: 100, def: 90, spa: 130, spd: 100, spe: 120 },
            moves: [
              { name: "Flamethrower", type: "Fire", category: "special", base_power: 90, accuracy: 1.0 },
              { name: "Air Slash", type: "Flying", category: "special", base_power: 75, accuracy: 0.95 },
            ]
          }
        ]
      };
    }

    // 3. Iniciar la batalla en el backend
    try {
      const res = await fetch(`${this.apiUrl}/api/pve/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          preset_id: setup.preset_id || "brock-rock",
          player_team: setup.player_team || []
        })
      });

      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();

      this.battleId = data.battle_id;
      this.state = data.state;
      this.dom.txtTrainerName.textContent = data.trainer?.name || "Líder Rival";

      this.render();
      this.setDialog(`¡El combate contra ${data.trainer?.name || "el rival"} ha comenzado!`);
    } catch (err) {
      console.error("Error al iniciar batalla PVE:", err);
      this.setDialog("Error al conectar con el servidor. Reintenta de nuevo.");
    }
  }

  render() {
    if (!this.state) return;

    this.dom.txtTurn.textContent = `Turno ${this.state.turn || 1}`;
    this.renderFieldBadges();

    // Renderizar Rival (IA)
    const ai = this.state.ai_active;
    if (ai) {
      this.dom.txtAiName.textContent = ai.species;
      this.dom.txtAiLvl.textContent = `Lv. ${ai.level || 50}`;
      this.renderTypes(this.dom.boxAiTypes, ai.types || []);
      this.updateHpBar(this.dom.barAiHp, this.dom.txtAiHp, ai.current_hp, ai.max_hp, true);
      this.renderStatusBadge(this.dom.badgeAiStatus, ai.status);
      this.renderSideModifiers(this.dom.boxAiModifiers, ai, this.state.ai_side);
      this.dom.imgAiSprite.src = this.getSpriteUrl(ai, false);
      this.dom.imgAiSprite.onerror = () => {
        const slug = (ai.species || "").toLowerCase().replace("mega ", "").replace("-mega", "").replace(" ", "-").trim();
        this.dom.imgAiSprite.src = `https://play.pokemonshowdown.com/sprites/dex/${slug}.png`;
      };
    }
    this.renderBenchBalls(this.dom.ballsAiBench, this.state.ai_bench || []);

    // Renderizar Jugador
    const player = this.state.player_active;
    if (player) {
      this.dom.txtPlayerName.textContent = player.species;
      this.dom.txtPlayerLvl.textContent = `Lv. ${player.level || 50}`;
      this.renderTypes(this.dom.boxPlayerTypes, player.types || []);
      this.updateHpBar(this.dom.barPlayerHp, this.dom.txtPlayerHp, player.current_hp, player.max_hp, false);
      this.renderStatusBadge(this.dom.badgePlayerStatus, player.status);
      this.renderSideModifiers(this.dom.boxPlayerModifiers, player, this.state.player_side);
      this.dom.imgPlayerSprite.src = this.getSpriteUrl(player, true);
      this.dom.imgPlayerSprite.onerror = () => {
        const slug = (player.species || "").toLowerCase().replace("mega ", "").replace("-mega", "").replace(" ", "-").trim();
        this.dom.imgPlayerSprite.src = `https://play.pokemonshowdown.com/sprites/dex/${slug}.png`;
      };
    }
    this.renderBenchBalls(this.dom.ballsPlayerBench, this.state.player_bench || []);

    // Renderizar Botones de Ataque
    this.renderMoves();

    // Megaevolución
    const canMega = player?.can_mega && !this.state.player_mega_used && !player?.is_mega;
    this.dom.btnToggleMega.style.display = canMega ? "flex" : "none";
  }

  renderFieldBadges() {
    if (!this.dom.boxFieldBadges || !this.state) return;
    const pills = [];
    const weatherMap = {
      Sun: "☀️ Sol",
      Rain: "🌧️ Lluvia",
      Sandstorm: "🏜️ Tormenta Arena",
      Snow: "❄️ Nieve"
    };
    const terrainMap = {
      Electric: "⚡ Campo Eléctrico",
      Grassy: "🌿 Campo Hierba",
      Psychic: "🔮 Campo Psíquico",
      Misty: "🌫️ Campo Niebla"
    };

    if (this.state.weather) {
      const label = weatherMap[this.state.weather] || this.state.weather;
      const turns = this.state.weather_turns ? ` (${this.state.weather_turns}t)` : "";
      pills.push(`<span class="field-pill">${label}${turns}</span>`);
    }
    if (this.state.terrain) {
      const label = terrainMap[this.state.terrain] || this.state.terrain;
      const turns = this.state.terrain_turns ? ` (${this.state.terrain_turns}t)` : "";
      pills.push(`<span class="field-pill">${label}${turns}</span>`);
    }
    if (this.state.trick_room_turns > 0) {
      pills.push(`<span class="field-pill">🌀 Espacio Raro (${this.state.trick_room_turns}t)</span>`);
    }

    this.dom.boxFieldBadges.innerHTML = pills.join("");
  }

  renderSideModifiers(container, poke, sideCond) {
    if (!container) return;
    const pills = [];

    // 1. Etapas de estadísticas (Boosts / Unboosts)
    const boosts = poke?.boosts || {};
    const statLabels = {
      atk: "Atk", def: "Def", spa: "SpA", spd: "SpD", spe: "Spe", accuracy: "Acc", evasion: "Eva"
    };
    Object.entries(statLabels).forEach(([key, label]) => {
      const stage = Number(boosts[key] || 0);
      if (stage > 0) {
        pills.push(`<span class="mod-pill boost-up">+${stage} ${label}</span>`);
      } else if (stage < 0) {
        pills.push(`<span class="mod-pill boost-down">${stage} ${label}</span>`);
      }
    });

    // 2. Estados volátiles activos
    const vols = poke?.volatiles || {};
    if (poke?.substitute_hp > 0 || vols.substitute) {
      pills.push(`<span class="mod-pill volatile">🛡️ Sustituto</span>`);
    }
    if (vols.leech_seed) {
      pills.push(`<span class="mod-pill volatile">🌱 Drenadoras</span>`);
    }
    if (vols.taunt) {
      pills.push(`<span class="mod-pill volatile">💢 Mofa (${vols.taunt})</span>`);
    }
    if (vols.confusion) {
      pills.push(`<span class="mod-pill volatile">💫 Confuso</span>`);
    }
    if (vols.partially_trapped) {
      pills.push(`<span class="mod-pill volatile">🔥 Atrapado</span>`);
    }

    // 3. Condiciones del lado (Hazards y Pantallas)
    if (sideCond) {
      if (sideCond.stealth_rock) pills.push(`<span class="mod-pill hazard">🪨 Trampa Rocas</span>`);
      if (sideCond.spikes > 0) pills.push(`<span class="mod-pill hazard">📌 Púas x${sideCond.spikes}</span>`);
      if (sideCond.toxic_spikes > 0) pills.push(`<span class="mod-pill hazard">☠️ P. Tóxicas x${sideCond.toxic_spikes}</span>`);
      if (sideCond.sticky_web) pills.push(`<span class="mod-pill hazard">🕸️ Red Viscosa</span>`);
      if (sideCond.reflect_turns > 0) pills.push(`<span class="mod-pill screen">🛡️ Reflejo (${sideCond.reflect_turns})</span>`);
      if (sideCond.light_screen_turns > 0) pills.push(`<span class="mod-pill screen">✨ P. Luz (${sideCond.light_screen_turns})</span>`);
      if (sideCond.aurora_veil_turns > 0) pills.push(`<span class="mod-pill screen">❄️ Velo Aurora (${sideCond.aurora_veil_turns})</span>`);
      if (sideCond.tailwind_turns > 0) pills.push(`<span class="mod-pill screen">🍃 Viento Afín (${sideCond.tailwind_turns})</span>`);
    }

    container.innerHTML = pills.join("");
  }

  renderMoves() {
    this.dom.movesGrid.innerHTML = "";
    const player = this.state?.player_active;
    if (!player || player.is_fainted) return;

    (player.moves || []).forEach(move => {
      const btn = document.createElement("button");
      btn.className = "btn-move";
      const color = TYPE_COLORS[move.type] || "#475569";
      btn.style.backgroundColor = color;
      btn.disabled = this.isProcessingTurn;

      const ppText = move.max_pp ? `PP ${move.pp ?? move.max_pp}/${move.max_pp}` : "";
      btn.innerHTML = `
        <span class="move-name">${move.name}</span>
        <div class="move-meta">
          <span>${move.type} · ${move.base_power > 0 ? `BP ${move.base_power}` : "Estado"}</span>
          <span>${ppText}</span>
        </div>
      `;

      btn.addEventListener("click", () => {
        this.sendAction("MOVE", move.id, this.wantsMega);
      });

      this.dom.movesGrid.appendChild(btn);
    });
  }

  renderTypes(container, types) {
    container.innerHTML = types.map(t => {
      const bg = TYPE_COLORS[t] || "#64748b";
      return `<span class="type-badge" style="background-color: ${bg};">${t}</span>`;
    }).join("");
  }

  updateHpBar(barElem, textElem, currentHp, maxHp, isPercentOnly) {
    const pct = Math.max(0, Math.min(100, Math.round((currentHp / Math.max(1, maxHp)) * 100)));
    barElem.style.width = `${pct}%`;

    if (pct > 50) barElem.style.backgroundColor = "var(--hp-green)";
    else if (pct > 20) barElem.style.backgroundColor = "var(--hp-yellow)";
    else barElem.style.backgroundColor = "var(--hp-red)";

    if (isPercentOnly) {
      textElem.textContent = `${pct}%`;
    } else {
      textElem.textContent = `${currentHp} / ${maxHp} HP`;
    }
  }

  renderStatusBadge(elem, status) {
    if (!status) {
      elem.textContent = "";
      elem.className = "";
      return;
    }
    elem.textContent = status;
    elem.className = `status-badge status-${status}`;
  }

  renderBenchBalls(container, bench) {
    if (!bench || bench.length === 0) {
      container.innerHTML = `<span style="font-size: 0.7rem; color: var(--text-muted);">Sin banca</span>`;
      return;
    }
    const aliveCount = bench.filter(p => !p.is_fainted && p.current_hp > 0).length;
    container.innerHTML = `
      <div class="bench-indicator">
        <span class="bench-label">Banca:</span>
        <div class="bench-dots">
          ${bench.map(p => {
            const isFainted = p.is_fainted || p.current_hp <= 0;
            return `<span class="pokeball-dot ${isFainted ? 'fainted' : 'alive'}" title="${p.species} (${p.current_hp}/${p.max_hp} HP)"></span>`;
          }).join("")}
        </div>
        <span class="bench-count">${aliveCount}/${bench.length}</span>
      </div>
    `;
  }

  getSpriteUrl(poke, isPlayer) {
    if (poke && typeof poke === "object") {
      if (poke.image_url) return poke.image_url;
      var name = poke.species || poke.name || "";
    } else {
      var name = String(poke || "");
    }

    const clean = name.toLowerCase().replace("mega ", "").replace("-mega", "").replace(" ", "-").trim();
    // Pokédex sprite oficial de Showdown (reconoce a todos los Pokémon de todas las generaciones por nombre)
    return `https://play.pokemonshowdown.com/sprites/gen5/${clean}.png`;
  }

  async sendAction(type, choice, isMega = false) {
    if (this.isProcessingTurn || !this.battleId) return;
    this.isProcessingTurn = true;
    this.setControlsDisabled(true);

    try {
      const res = await fetch(`${this.apiUrl}/api/pve/turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          battle_id: this.battleId,
          action: { type: type, choice: choice, mega: isMega }
        })
      });

      if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
      const data = await res.json();

      // Reproducir eventos secuencialmente con pausas
      await this.playEvents(data.events || []);

      // Actualizar estado final del turno
      this.state = data.state;
      this.wantsMega = false;
      this.dom.btnToggleMega.classList.remove("active");
      this.dom.btnToggleMega.textContent = "⚡ Megaevolución";
      this.render();

      // Chequear si el combate terminó o si hay cambio forzado
      if (data.battle_status === "won") {
        this.showEndModal(true, "¡Has derrotado a todo el equipo rival! Eres el vencedor.");
      } else if (data.battle_status === "lost") {
        this.showEndModal(false, "Todos tus Pokémon se han debilitado.");
      } else if (data.battle_status === "waiting_player_switch") {
        this.setDialog("Tu Pokémon cayó. ¡Debes enviar un reemplazo!");
        this.openBenchSheet(true); // Cambio forzado
      }
    } catch (err) {
      console.error("Error al procesar turno:", err);
      this.setDialog("Error de comunicación durante el turno.");
    } finally {
      this.isProcessingTurn = false;
      this.setControlsDisabled(false);
    }
  }

  async playEvents(events) {
    for (const ev of events) {
      if (ev.text) this.setDialog(ev.text);

      if (["DAMAGE", "HAZARD_DAMAGE", "WEATHER_DAMAGE", "STATUS_DAMAGE"].includes(ev.type)) {
        const targetSprite = ev.side === "ai" ? this.dom.imgAiSprite : this.dom.imgPlayerSprite;
        targetSprite.classList.add("shake");
        setTimeout(() => targetSprite.classList.remove("shake"), 350);

        if (ev.remaining_hp !== undefined && ev.max_hp !== undefined) {
          if (ev.side === "ai") {
            this.updateHpBar(this.dom.barAiHp, this.dom.txtAiHp, ev.remaining_hp, ev.max_hp, true);
          } else {
            this.updateHpBar(this.dom.barPlayerHp, this.dom.txtPlayerHp, ev.remaining_hp, ev.max_hp, false);
          }
        }
      } else if (ev.type === "HEAL" && ev.remaining_hp !== undefined && ev.max_hp !== undefined) {
        if (ev.side === "ai") {
          this.updateHpBar(this.dom.barAiHp, this.dom.txtAiHp, ev.remaining_hp, ev.max_hp, true);
        } else {
          this.updateHpBar(this.dom.barPlayerHp, this.dom.txtPlayerHp, ev.remaining_hp, ev.max_hp, false);
        }
      }

      await this.sleep(650);
    }
  }

  openBenchSheet(isForced = false) {
    this.dom.boxBenchList.innerHTML = "";
    const bench = this.state?.player_bench || [];

    bench.forEach(poke => {
      const isDead = poke.is_fainted || poke.current_hp <= 0;
      const card = document.createElement("div");
      card.className = `bench-card ${isDead ? 'fainted' : ''}`;

      card.innerHTML = `
        <img class="bench-sprite" src="${this.getSpriteUrl(poke.species, true)}" alt="${poke.species}">
        <div class="bench-details">
          <div style="font-weight: 800; color: white;">${poke.species} (Lv. ${poke.level})</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${poke.current_hp} / ${poke.max_hp} HP</div>
        </div>
      `;

      if (!isDead) {
        card.addEventListener("click", () => {
          this.closeBenchSheet();
          this.sendAction("SWITCH", poke.id);
        });
      }

      this.dom.boxBenchList.appendChild(card);
    });

    this.dom.sheetSwitch.classList.add("open");
  }

  closeBenchSheet() {
    this.dom.sheetSwitch.classList.remove("open");
  }

  setControlsDisabled(disabled) {
    const btns = this.dom.movesGrid.querySelectorAll("button");
    btns.forEach(b => b.disabled = disabled);
    this.dom.btnOpenSwitch.disabled = disabled;
    this.dom.btnSurrender.disabled = disabled;
  }

  setDialog(msg) {
    this.dom.boxDialog.textContent = msg;
  }

  showEndModal(isWon, msg) {
    this.dom.endTitle.textContent = isWon ? "¡VICTORIA!" : "DERROTA";
    this.dom.endTitle.className = `end-title ${isWon ? 'won' : 'lost'}`;
    this.dom.endMsg.textContent = msg;
    this.dom.modalEnd.classList.add("open");
  }

  async handleSurrender() {
    if (!this.battleId || !confirm("¿Estás seguro de que quieres rendirte?")) return;
    try {
      await fetch(`${this.apiUrl}/api/pve/surrender`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ battle_id: this.battleId })
      });
      this.showEndModal(false, "Te has rendido de la batalla.");
    } catch (e) {
      this.handleReturn();
    }
  }

  handleReturn() {
    // Regresar a la página principal de la subasta
    window.location.href = "index.html";
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Iniciar al cargar la página
window.addEventListener("DOMContentLoaded", () => {
  const controller = new PVEBattleController();
  controller.init();
});
