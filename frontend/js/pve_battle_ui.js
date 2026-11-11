/**
 * frontend/js/pve_battle_ui.js
 * Controlador de combate PVE Mobile-First para Draft Prime.
 */

import { getMoveTextEs, getAbilityTextEs, getItemTextEs } from "./showdown_text_es.js";

// Paleta oficial de colores para los tipos de Pokémon
const TYPE_COLORS = {
  Normal: "#94a3b8", Fire: "#ea580c", Water: "#0284c7", Grass: "#16a34a",
  Electric: "#ca8a04", Ice: "#0891b2", Fighting: "#b91c1c", Poison: "#9333ea",
  Ground: "#d97706", Flying: "#7c3aed", Psychic: "#db2777", Bug: "#65a30d",
  Rock: "#78716c", Ghost: "#6b21a8", Dragon: "#4f46e5", Steel: "#64748b",
  Dark: "#334155", Fairy: "#e11d48"
};

const TYPE_LABELS_ES = {
  Normal: "Normal", Fire: "Fuego", Water: "Agua", Grass: "Planta",
  Electric: "Eléctrico", Ice: "Hielo", Fighting: "Lucha", Poison: "Veneno",
  Ground: "Tierra", Flying: "Volador", Psychic: "Psíquico", Bug: "Bicho",
  Rock: "Roca", Ghost: "Fantasma", Dragon: "Dragón", Steel: "Acero",
  Dark: "Siniestro", Fairy: "Hada", Stellar: "Astral"
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
      boxAiMeta: document.getElementById("box-ai-meta"),
      boxAiModifiers: document.getElementById("box-ai-modifiers"),
      imgAiSprite: document.getElementById("img-ai-sprite"),
      // Jugador
      txtPlayerName: document.getElementById("txt-player-name"),
      txtPlayerLvl: document.getElementById("txt-player-lvl"),
      boxPlayerTypes: document.getElementById("box-player-types"),
      barPlayerHp: document.getElementById("bar-player-hp"),
      txtPlayerHp: document.getElementById("txt-player-hp"),
      badgePlayerStatus: document.getElementById("badge-player-status"),
      boxPlayerMeta: document.getElementById("box-player-meta"),
      boxPlayerModifiers: document.getElementById("box-player-modifiers"),
      imgPlayerSprite: document.getElementById("img-player-sprite"),
      // Vista 6v6 Minisprites
      teamIconsPlayer: document.getElementById("team-icons-player"),
      teamIconsAi: document.getElementById("team-icons-ai"),
      // Controles
      movesGrid: document.getElementById("moves-grid"),
      btnToggleMega: document.getElementById("btn-toggle-mega"),
      btnOpenSwitch: document.getElementById("btn-open-switch"),
      btnSurrender: document.getElementById("btn-surrender"),
      boxBattleLog: document.getElementById("box-battle-log"),
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
          year: setup.year || null,
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

    // Renderizar Rival (IA) y Jugador
    if (this.state.ai_active) {
      this.renderActivePokemon("ai", this.state.ai_active);
    }
    if (this.state.player_active) {
      this.renderActivePokemon("player", this.state.player_active);
    }

    // Renderizar Vista 6v6 de Minisprites debajo de los movimientos
    this.renderTeamsOverview();

    // Renderizar Botones de Ataque
    this.renderMoves();

    // Megaevolución
    const player = this.state.player_active;
    const canMega = player?.can_mega && !this.state.player_mega_used && !player?.is_mega;
    this.dom.btnToggleMega.style.display = canMega ? "flex" : "none";
  }

  renderActivePokemon(side, poke) {
    if (!poke) return;
    if (side === "ai") {
      this.dom.txtAiName.textContent = poke.species;
      this.dom.txtAiLvl.textContent = `Lv. ${poke.level || 50}`;
      this.renderTypes(this.dom.boxAiTypes, poke.types || []);
      this.updateHpBar(this.dom.barAiHp, this.dom.txtAiHp, poke.current_hp, poke.max_hp, true);
      this.renderStatusBadge(this.dom.badgeAiStatus, poke.status);
      this.renderPokeMeta(this.dom.boxAiMeta, poke);
      this.renderSideModifiers(this.dom.boxAiModifiers, poke, this.state?.ai_side);
      this.dom.imgAiSprite.src = this.getSpriteUrl(poke, false);
      this.dom.imgAiSprite.onerror = () => {
        const slug = (poke.species || "").toLowerCase().replace("mega ", "").replace("-mega", "").replace(" ", "-").trim();
        this.dom.imgAiSprite.src = `https://play.pokemonshowdown.com/sprites/dex/${slug}.png`;
      };
    } else {
      this.dom.txtPlayerName.textContent = poke.species;
      this.dom.txtPlayerLvl.textContent = `Lv. ${poke.level || 50}`;
      this.renderTypes(this.dom.boxPlayerTypes, poke.types || []);
      this.updateHpBar(this.dom.barPlayerHp, this.dom.txtPlayerHp, poke.current_hp, poke.max_hp, false);
      this.renderStatusBadge(this.dom.badgePlayerStatus, poke.status);
      this.renderPokeMeta(this.dom.boxPlayerMeta, poke);
      this.renderSideModifiers(this.dom.boxPlayerModifiers, poke, this.state?.player_side);
      this.dom.imgPlayerSprite.src = this.getSpriteUrl(poke, true);
      this.dom.imgPlayerSprite.onerror = () => {
        const slug = (poke.species || "").toLowerCase().replace("mega ", "").replace("-mega", "").replace(" ", "-").trim();
        this.dom.imgPlayerSprite.src = `https://play.pokemonshowdown.com/sprites/dex/${slug}.png`;
      };
    }
  }

  renderTeamsOverview() {
    if (!this.state) return;

    // 1. Equipo del Jugador (6 minisprites a la izquierda, siempre visibles)
    if (this.dom.teamIconsPlayer) {
      const playerTeam = [this.state.player_active, ...(this.state.player_bench || [])]
        .filter(Boolean)
        .sort((a, b) => (a.slot_index ?? 0) - (b.slot_index ?? 0));
      const activeId = this.state.player_active?.id;

      this.dom.teamIconsPlayer.innerHTML = playerTeam.map(p => {
        const isFainted = p.is_fainted || p.current_hp <= 0;
        const isActive = p.id === activeId && !isFainted;
        const spriteUrl = this.getSpriteUrl(p, true);
        const title = `${p.species} (Lv. ${p.level || 50}) — ${p.current_hp}/${p.max_hp} HP${isFainted ? ' [Debilitado]' : ''}`;
        return `
          <div class="team-mini-slot ${isActive ? 'active-slot' : ''} ${isFainted ? 'fainted' : ''}" title="${title}">
            <img class="team-mini-img" src="${spriteUrl}" alt="${p.species}" onerror="this.src='https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png'">
          </div>
        `;
      }).join("");
    }

    // 2. Equipo Rival (6 minisprites a la derecha; Pokéball si aún no ha sido revelado)
    if (this.dom.teamIconsAi) {
      const aiTeam = [this.state.ai_active, ...(this.state.ai_bench || [])]
        .filter(Boolean)
        .sort((a, b) => (a.slot_index ?? 0) - (b.slot_index ?? 0));
      const activeId = this.state.ai_active?.id;
      const pokeballUrl = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png";

      this.dom.teamIconsAi.innerHTML = aiTeam.map(p => {
        const isFainted = p.is_fainted || p.current_hp <= 0;
        const isActive = p.id === activeId && !isFainted;
        const isRevealed = Boolean(p.revealed || p.id === activeId || isFainted);

        if (!isRevealed) {
          return `
            <div class="team-mini-slot" title="Pokémon rival sin revelar">
              <img class="team-mini-img pokeball-unrevealed" src="${pokeballUrl}" alt="Sin revelar">
            </div>
          `;
        }

        const spriteUrl = this.getSpriteUrl(p, false);
        const pct = Math.max(0, Math.min(100, Math.round((p.current_hp / Math.max(1, p.max_hp)) * 100)));
        const title = `${p.species} (Lv. ${p.level || 50}) — ${isFainted ? 'Debilitado' : pct + '% HP'}`;
        return `
          <div class="team-mini-slot ${isActive ? 'active-slot' : ''} ${isFainted ? 'fainted' : ''}" title="${title}">
            <img class="team-mini-img" src="${spriteUrl}" alt="${p.species}" onerror="this.src='${pokeballUrl}'">
          </div>
        `;
      }).join("");
    }
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
    } else {
      pills.push(`<span class="field-pill neutral">🌤️ Clima: Despejado</span>`);
    }
    if (this.state.terrain) {
      const label = terrainMap[this.state.terrain] || this.state.terrain;
      const turns = this.state.terrain_turns ? ` (${this.state.terrain_turns}t)` : "";
      pills.push(`<span class="field-pill">${label}${turns}</span>`);
    } else {
      pills.push(`<span class="field-pill neutral">🌱 Terreno: Normal</span>`);
    }
    if (this.state.trick_room_turns > 0) {
      pills.push(`<span class="field-pill">🌀 Espacio Raro (${this.state.trick_room_turns}t)</span>`);
    }

    this.dom.boxFieldBadges.innerHTML = pills.join("");
  }

  renderPokeMeta(container, poke) {
    if (!container || !poke) return;
    const tags = [];
    let abilityDesc = "";
    if (poke.ability) {
      const abInfo = getAbilityTextEs(poke.ability);
      const abNameEs = poke.ability_es || abInfo.es || poke.ability;
      abilityDesc = abInfo.desc || poke.ability_desc || "";
      tags.push(`<span class="meta-tag" title="${abilityDesc || 'Habilidad'}">🧬 ${abNameEs}</span>`);
    }
    if (poke.item) {
      const itInfo = getItemTextEs(poke.item);
      const itNameEs = poke.item_es || itInfo.es || poke.item;
      const itDesc = itInfo.desc || poke.item_desc || "Objeto equipado";
      tags.push(`<span class="meta-tag" title="${itDesc}">🎒 ${itNameEs}</span>`);
    }
    if (poke.stats?.spe) {
      tags.push(`<span class="meta-tag" title="Velocidad Base">⚡ Vel ${poke.stats.spe}</span>`);
    }
    if (abilityDesc) {
      tags.push(`<div class="ability-desc-line">ℹ️ ${abilityDesc}</div>`);
    }
    container.innerHTML = tags.join("");
  }

  renderSideModifiers(container, poke, sideCond) {
    if (!container) return;
    const pills = [];

    // 1. Etapas de estadísticas (Boosts positivos y negativos estilo Showdown)
    const boosts = poke?.boosts || {};
    const statLabels = [
      { keys: ["atk"], label: "Ata" },
      { keys: ["def", "def_"], label: "Def" },
      { keys: ["spa"], label: "At.Esp" },
      { keys: ["spd"], label: "Def.Esp" },
      { keys: ["spe"], label: "Vel" },
      { keys: ["accuracy"], label: "Prec" },
      { keys: ["evasion"], label: "Eva" }
    ];
    statLabels.forEach(({ keys, label }) => {
      let stage = 0;
      for (const k of keys) {
        if (boosts[k] !== undefined && boosts[k] !== null && Number(boosts[k]) !== 0) {
          stage = Number(boosts[k]);
          break;
        }
      }
      if (stage > 0) {
        pills.push(`<span class="mod-pill boost-up">▲ +${stage} ${label}</span>`);
      } else if (stage < 0) {
        pills.push(`<span class="mod-pill boost-down">▼ ${stage} ${label}</span>`);
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
    if (vols.curse) {
      pills.push(`<span class="mod-pill volatile">👻 Maldición</span>`);
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

      const mvInfo = getMoveTextEs(move.name || move.id);
      const moveNameEs = mvInfo.es || move.name_es || move.name;
      // Priorizar la descripción competitiva shortDesc de Pokémon Showdown (con porcentajes exactos y etapas)
      const moveDescEs = mvInfo.desc || move.desc_es || "";
      const typeEs = TYPE_LABELS_ES[move.type] || move.type;

      const ppText = move.max_pp ? `PP ${move.pp ?? move.max_pp}/${move.max_pp}` : "";
      const catIcon = move.category === "physical" ? "💥 Fís" : (move.category === "special" ? "✨ Esp" : "🛡️ Est");
      const accText = move.never_miss ? "—%" : `${Math.round((move.accuracy ?? 1.0) * 100)}%`;
      const effectFallback = !moveDescEs ? this.describeMoveEffect(move) : "";

      btn.title = moveDescEs ? `${moveNameEs} (${move.name}): ${moveDescEs}` : moveNameEs;
      btn.innerHTML = `
        <span class="move-name">${moveNameEs}</span>
        ${moveDescEs ? `<span class="move-flavor-desc">${moveDescEs}</span>` : ""}
        ${effectFallback ? `<span class="move-effect-desc">${effectFallback}</span>` : ""}
        <div class="move-meta">
          <span>${typeEs} · ${catIcon} · ${move.base_power > 0 ? `Pot ${move.base_power} · Prec ${accText}` : `Prec ${accText}`}</span>
          <span>${ppText}</span>
        </div>
      `;

      btn.addEventListener("click", () => {
        this.sendAction("MOVE", move.id, this.wantsMega);
      });

      this.dom.movesGrid.appendChild(btn);
    });
  }

  describeMoveEffect(move) {
    const parts = [];
    if (move.priority && move.priority !== 0) {
      parts.push(`Prio ${move.priority > 0 ? "+" + move.priority : move.priority}`);
    }
    if (move.drain_percent > 0) parts.push(`Drena ${Math.round(move.drain_percent * 100)}%`);
    if (move.recoil_percent > 0) parts.push(`Retroceso ${Math.round(move.recoil_percent * 100)}%`);
    if (move.heal_fraction > 0) parts.push(`Cura ${Math.round(move.heal_fraction * 100)}%`);
    if (move.crit_ratio > 1) parts.push("Crítico alto");
    if (move.multi_hit) parts.push(`${move.multi_hit[0]}-${move.multi_hit[1]} golpes`);
    if (move.target_status) parts.push(`Causa ${move.target_status}`);
    if (move.volatile_status) {
      const vMap = { protect: "Protección", substitute: "Sustituto (25% HP)", leech_seed: "Drenadoras", taunt: "Mofa (3t)", confusion: "Confusión", partially_trapped: "Atrapa" };
      parts.push(vMap[move.volatile_status] || move.volatile_status);
    }
    if (move.side_condition) {
      const scMap = { stealth_rock: "Trampa Rocas", spikes: "Púas", toxic_spikes: "Púas Tóxicas", sticky_web: "Red Viscosa", reflect: "Reflejo", light_screen: "Pantalla Luz", aurora_veil: "Velo Aurora", tailwind: "Viento Afín" };
      parts.push(scMap[move.side_condition] || move.side_condition);
    }
    if (move.weather) parts.push(`Clima: ${move.weather}`);
    if (move.terrain) parts.push(`Campo: ${move.terrain}`);
    if (move.pseudo_weather === "trick_room") parts.push("Espacio Raro");
    if (move.hazard_clear) parts.push("Limpia Hazards");
    if (move.self_switch) parts.push("Cambia tras usar");
    if (move.force_switch) parts.push("Fuerza cambio rival");
    if (move.self_boosts) {
      const bStr = Object.entries(move.self_boosts).map(([k, v]) => `${v > 0 ? "+" + v : v} ${k.toUpperCase()}`).join(" ");
      parts.push(bStr);
    }
    if (move.boosts) {
      const bStr = Object.entries(move.boosts).map(([k, v]) => `${v > 0 ? "+" + v : v} ${k.toUpperCase()} rival`).join(" ");
      parts.push(bStr);
    }
    if (move.secondary) {
      const pct = Math.round((move.secondary.chance || 1) * 100);
      if (move.secondary.status) parts.push(`${pct}% ${move.secondary.status}`);
      if (move.secondary.flinch) parts.push(`${pct}% Retroceso`);
      if (move.secondary.volatile_status) parts.push(`${pct}% Confusión`);
      if (move.secondary.boosts) {
        const sb = Object.entries(move.secondary.boosts).map(([k, v]) => `${v} ${k.toUpperCase()}`).join("");
        parts.push(`${pct}% ${sb}`);
      }
      if (move.secondary.self_boosts) {
        const sb = Object.entries(move.secondary.self_boosts).map(([k, v]) => `+${v} ${k.toUpperCase()}`).join("");
        parts.push(`${pct}% ${sb}`);
      }
    }
    return parts.slice(0, 2).join(" · ");
  }

  renderTypes(container, types) {
    container.innerHTML = types.map(t => {
      const bg = TYPE_COLORS[t] || "#64748b";
      const label = TYPE_LABELS_ES[t] || t;
      return `<span class="type-badge" style="background-color: ${bg};">${label}</span>`;
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
    if (this.dom.boxBattleLog && this.state?.turn) {
      const turnHeader = document.createElement("div");
      turnHeader.className = "log-turn-header";
      turnHeader.textContent = `=== Turno ${this.state.turn} ===`;
      this.dom.boxBattleLog.appendChild(turnHeader);
    }

    for (const ev of events) {
      if (ev.text) {
        this.setDialog(ev.text);
        this.appendBattleLog(ev);
      }

      // 1. Animación de Cambio de Pokémon (sale el actual, se actualiza la tarjeta y entra el nuevo)
      if (ev.type === "SWITCH") {
        const isAi = ev.side === "ai";
        const spriteEl = isAi ? this.dom.imgAiSprite : this.dom.imgPlayerSprite;
        const outClass = isAi ? "switch-out-ai" : "switch-out-player";
        const inClass = isAi ? "switch-in-ai" : "switch-in-player";

        // Fase 1: Sale el Pokémon actual
        spriteEl.classList.remove(inClass, "shake");
        spriteEl.classList.add(outClass);
        await this.sleep(420);

        // Fase 2: Actualizar el Pokémon activo en estado local y HUD inmediatamente
        if (this.state) {
          const benchKey = isAi ? "ai_bench" : "player_bench";
          const activeKey = isAi ? "ai_active" : "player_active";
          const prevActive = this.state[activeKey];
          const benchArr = this.state[benchKey] || [];
          let incoming = ev.pokemon_state;

          if (!incoming) {
            incoming = benchArr.find(b => b.species === ev.pokemon);
          }

          if (incoming) {
            incoming.revealed = true;
            this.state[benchKey] = benchArr.filter(b => b.id !== incoming.id && b.species !== incoming.species);
            if (prevActive && prevActive.id !== incoming.id) {
              prevActive.boosts = { atk: 0, def: 0, spa: 0, spd: 0, spe: 0, accuracy: 0, evasion: 0 };
              prevActive.volatiles = {};
              this.state[benchKey].push(prevActive);
            }
            this.state[activeKey] = incoming;
            this.renderActivePokemon(ev.side, incoming);
            this.renderTeamsOverview();
          }
        }

        await this.sleep(220);

        // Fase 3: Entra el nuevo Pokémon
        spriteEl.classList.remove(outClass);
        spriteEl.classList.add(inClass);
        await this.sleep(480);
        spriteEl.classList.remove(inClass);

        // Pausa de lectura para asimilar la entrada del nuevo Pokémon
        await this.sleep(1250);
        continue;
      }

      // 2. Daño directo o residual
      if (["DAMAGE", "HAZARD_DAMAGE", "WEATHER_DAMAGE", "STATUS_DAMAGE"].includes(ev.type)) {
        const targetSprite = ev.side === "ai" ? this.dom.imgAiSprite : this.dom.imgPlayerSprite;
        targetSprite.classList.add("shake");
        setTimeout(() => targetSprite.classList.remove("shake"), 400);

        if (ev.remaining_hp !== undefined && ev.max_hp !== undefined) {
          if (ev.side === "ai") {
            if (this.state?.ai_active) this.state.ai_active.current_hp = ev.remaining_hp;
            this.updateHpBar(this.dom.barAiHp, this.dom.txtAiHp, ev.remaining_hp, ev.max_hp, true);
          } else {
            if (this.state?.player_active) this.state.player_active.current_hp = ev.remaining_hp;
            this.updateHpBar(this.dom.barPlayerHp, this.dom.txtPlayerHp, ev.remaining_hp, ev.max_hp, false);
          }
        }
        await this.sleep(1250);
        continue;
      } else if (ev.type === "HEAL" && ev.remaining_hp !== undefined && ev.max_hp !== undefined) {
        if (ev.side === "ai") {
          if (this.state?.ai_active) this.state.ai_active.current_hp = ev.remaining_hp;
          this.updateHpBar(this.dom.barAiHp, this.dom.txtAiHp, ev.remaining_hp, ev.max_hp, true);
        } else {
          if (this.state?.player_active) this.state.player_active.current_hp = ev.remaining_hp;
          this.updateHpBar(this.dom.barPlayerHp, this.dom.txtPlayerHp, ev.remaining_hp, ev.max_hp, false);
        }
        await this.sleep(1200);
        continue;
      } else if (ev.type === "BOOST" || ev.type === "UNBOOST") {
        // 3. Visualización inmediata de cambios de estadísticas (positivos y negativos)
        const isAi = ev.side === "ai";
        const targetPoke = isAi ? this.state?.ai_active : this.state?.player_active;
        const targetBox = isAi ? this.dom.boxAiModifiers : this.dom.boxPlayerModifiers;
        const targetSideCond = isAi ? this.state?.ai_side : this.state?.player_side;
        const targetSprite = isAi ? this.dom.imgAiSprite : this.dom.imgPlayerSprite;

        if (targetPoke) {
          if (ev.boosts) {
            targetPoke.boosts = ev.boosts;
          } else if (ev.stat) {
            targetPoke.boosts = targetPoke.boosts || {};
            const key = ev.stat === "def_" ? "def" : ev.stat;
            targetPoke.boosts[key] = Math.max(-6, Math.min(6, Number(targetPoke.boosts[key] || 0) + Number(ev.stages || 0)));
          }
          this.renderSideModifiers(targetBox, targetPoke, targetSideCond);
        }

        const glowClass = ev.type === "BOOST" ? "boost-glow" : "unboost-glow";
        targetSprite.classList.remove("boost-glow", "unboost-glow");
        void targetSprite.offsetWidth;
        targetSprite.classList.add(glowClass);
        setTimeout(() => targetSprite.classList.remove(glowClass), 550);
        await this.sleep(1300);
        continue;
      } else if (ev.type === "CLEAR_BOOST") {
        if (ev.side === "both") {
          if (this.state?.player_active) {
            this.state.player_active.boosts = ev.player_boosts || {};
            this.renderSideModifiers(this.dom.boxPlayerModifiers, this.state.player_active, this.state?.player_side);
          }
          if (this.state?.ai_active) {
            this.state.ai_active.boosts = ev.ai_boosts || {};
            this.renderSideModifiers(this.dom.boxAiModifiers, this.state.ai_active, this.state?.ai_side);
          }
        } else {
          const isAi = ev.side === "ai";
          const targetPoke = isAi ? this.state?.ai_active : this.state?.player_active;
          const targetBox = isAi ? this.dom.boxAiModifiers : this.dom.boxPlayerModifiers;
          const targetSideCond = isAi ? this.state?.ai_side : this.state?.player_side;
          if (targetPoke) {
            targetPoke.boosts = ev.boosts || {};
            this.renderSideModifiers(targetBox, targetPoke, targetSideCond);
          }
        }
        await this.sleep(1250);
        continue;
      } else if (ev.type === "STATUS") {
        const isAi = ev.side === "ai";
        const targetPoke = isAi ? this.state?.ai_active : this.state?.player_active;
        const badgeEl = isAi ? this.dom.badgeAiStatus : this.dom.badgePlayerStatus;
        if (targetPoke) targetPoke.status = ev.status;
        this.renderStatusBadge(badgeEl, ev.status);
        await this.sleep(1300);
        continue;
      } else if (ev.type === "FAINT") {
        const isAi = ev.side === "ai";
        const targetPoke = isAi ? this.state?.ai_active : this.state?.player_active;
        if (targetPoke) {
          targetPoke.is_fainted = true;
          targetPoke.current_hp = 0;
        }
        this.renderTeamsOverview();
        await this.sleep(1500);
        continue;
      } else if (ev.type === "MOVE") {
        // Pausa para leer el movimiento anunciado
        await this.sleep(1350);
        continue;
      }

      // Eventos narrativos o de estado con texto (efectividades, climas, campos, etc.)
      const textDelay = ev.text ? Math.max(1250, Math.min(2400, ev.text.length * 40)) : 1000;
      await this.sleep(textDelay);
    }
  }

  openBenchSheet(isForced = false) {
    this.dom.boxBenchList.innerHTML = "";
    const bench = this.state?.player_bench || [];

    bench.forEach(poke => {
      const isDead = poke.is_fainted || poke.current_hp <= 0;
      const card = document.createElement("div");
      card.className = `bench-card ${isDead ? 'fainted' : ''}`;

      const abInfo = poke.ability ? getAbilityTextEs(poke.ability) : null;
      const abNameEs = poke.ability_es || abInfo?.es || poke.ability || "";
      const abDescEs = poke.ability_desc || abInfo?.desc || "";
      const movesEs = (poke.moves || []).map(m => m.name_es || getMoveTextEs(m.name || m.id).es).join(" · ");

      card.innerHTML = `
        <img class="bench-sprite" src="${this.getSpriteUrl(poke, true)}" alt="${poke.species}">
        <div class="bench-details">
          <div style="font-weight: 800; color: white;">${poke.species} (Lv. ${poke.level})</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${poke.current_hp} / ${poke.max_hp} HP</div>
          ${abNameEs ? `<div style="font-size: 0.7rem; color: #93c5fd; margin-top: 2px;">🧬 <strong>${abNameEs}</strong>${abDescEs ? `: ${abDescEs}` : ""}</div>` : ""}
          ${movesEs ? `<div style="font-size: 0.68rem; color: #cbd5e1; margin-top: 2px;">⚔️ ${movesEs}</div>` : ""}
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

  appendBattleLog(ev) {
    if (!this.dom.boxBattleLog || !ev?.text) return;
    const line = document.createElement("div");
    let cls = "log-entry";
    if (["DAMAGE", "HAZARD_DAMAGE", "WEATHER_DAMAGE", "STATUS_DAMAGE", "FAINT"].includes(ev.type)) cls += " dmg";
    else if (ev.type === "HEAL") cls += " heal";
    else if (["BOOST", "UNBOOST", "MEGA_EVOLVE"].includes(ev.type)) cls += " boost";
    else if (["WEATHER", "TERRAIN", "FIELD", "SIDE_CONDITION"].includes(ev.type)) cls += " field";
    line.className = cls;
    line.textContent = `• ${ev.text}`;
    this.dom.boxBattleLog.appendChild(line);
    this.dom.boxBattleLog.scrollTop = this.dom.boxBattleLog.scrollHeight;
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
