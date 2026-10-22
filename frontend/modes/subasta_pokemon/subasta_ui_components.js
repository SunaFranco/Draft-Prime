/**
 * frontend/modes/subasta_pokemon/subasta_ui_components.js - Componentes de renderizado UI para Subasta Pokémon
 */

const POKEMON_TYPES = [
  "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison",
  "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark",
  "Steel", "Fairy",
];

export const POKEMON_CARD_COLORS = {
  green: { label: "Verde", hex: "#10b981", rgb: "16, 185, 129" },
  blue: { label: "Azul", hex: "#3b82f6", rgb: "59, 130, 246" },
  purple: { label: "Morado", hex: "#a855f7", rgb: "168, 85, 247" },
  red: { label: "Rojo", hex: "#ef4444", rgb: "239, 68, 68" },
  orange: { label: "Naranja", hex: "#f97316", rgb: "249, 115, 22" },
  yellow: { label: "Amarillo", hex: "#eab308", rgb: "234, 179, 8" },
};

const POKEMON_COLORS = {
  black: { label: "Negro", hex: "#303030" },
  blue: { label: "Azul", hex: "#6890f0" },
  brown: { label: "Marrón", hex: "#a07850" },
  gray: { label: "Gris", hex: "#a8a8a8" },
  green: { label: "Verde", hex: "#78c850" },
  pink: { label: "Rosa", hex: "#f85888" },
  purple: { label: "Morado", hex: "#a040a0" },
  red: { label: "Rojo", hex: "#f05030" },
  white: { label: "Blanco", hex: "#f8f8f8" },
  yellow: { label: "Amarillo", hex: "#f8d030" },
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function buildWikidexUrl(name) {
  if (!name) return "";
  const megaInfo = getMegaInfo(name);
  const raw = String(
    megaInfo?.baseName || (typeof name === "object" ? name.name : name) || ""
  ).trim();
  if (!raw) return "";

  // Detectar variantes regionales (ej: "Rattata-alola", "Rattata Alola", "Meowth Galar", "Growlithe Hisui", "Wooper Paldea")
  const regionalMatch = raw.match(/^(.*?)(?:[-_\s]+|\s*\()(alola|galar|hisui|paldea|paldean)\)?$/i);
  if (regionalMatch) {
    let base = regionalMatch[1].trim().replace(/[()]/g, "");
    let region = regionalMatch[2].toLowerCase();
    if (region === "paldean") region = "paldea";
    const capitalizedRegion = region.charAt(0).toUpperCase() + region.slice(1);

    base = base.replace(/[-_]+/g, " ");
    const formattedBase = base
      .split(/\s+/)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join("_");

    const finalName = `${formattedBase}_de_${capitalizedRegion}`;
    return `https://www.wikidex.net/wiki/${encodeURI(finalName)}`;
  }

  const formatted = raw.replace(/[()]/g, "").replace(/\s+/g, "_");
  return `https://www.wikidex.net/wiki/${encodeURI(formatted)}`;
}

export const TM_MOVES = {
  "MT Earthquake": "Earthquake",
  "MT Ice Beam": "Ice Beam",
  "MT Flamethrower": "Flamethrower",
  "MT Thunderbolt": "Thunderbolt",
  "MT Psychic": "Psychic",
  "MT Shadow Ball": "Shadow Ball",
  "MT Protect": "Protect",
  "MT Substitute": "Substitute",
  "MT Swords Dance": "Swords Dance",
  "MT Calm Mind": "Calm Mind",
  "MT Surf": "Surf",
  "MT Dragon Claw": "Dragon Claw",
  "MT Stone Edge": "Stone Edge",
  "MT U-turn": "U Turn",
  "MT Volt Switch": "Volt Switch",
  "MT Stealth Rock": "Stealth Rock",
  "MT Spikes": "Spikes",
  "MT Toxic": "Toxic",
  "MT Roost": "Roost",
  "MT Iron Head": "Iron Head",
  "MT Close Combat": "Close Combat",
  "MT Dazzling Gleam": "Dazzling Gleam",
  "MT Energy Ball": "Energy Ball",
  "MT Dark Pulse": "Dark Pulse",
  "MT Sludge Bomb": "Sludge Bomb",
  "MT Focus Blast": "Focus Blast",
  "MT Thunder Wave": "Thunder Wave",
  "MT Will-O-Wisp": "Will O Wisp",
  "MT Taunt": "Taunt",
  "MT Trick Room": "Trick Room",
  "MT Giga Drain": "Giga Drain",
  "MT Brick Break": "Brick Break",
  "MT Knock Off": "Knock Off",
  "MT Ice Spinner": "Ice Spinner",
  "MT Fire Punch": "Fire Punch",
  "MT Thunder Punch": "Thunder Punch",
  "MT Ice Punch": "Ice Punch",
};

export function getTmMoveName(itemName) {
  if (!itemName) return "";
  if (TM_MOVES[itemName]) return TM_MOVES[itemName];
  if (String(itemName).startsWith("MT ")) {
    return String(itemName).slice(3).replace(/-/g, " ").trim();
  }
  return String(itemName).trim();
}

function normalizeMoveIdentifier(name) {
  return String(name || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

export function checkTmCompatibility(poke, itemNameOrMoveName) {
  if (!poke) {
    return { canLearn: false, reason: "no_poke", label: "No seleccionado", badgeClass: "badge-muted" };
  }
  const moveName = getTmMoveName(itemNameOrMoveName);
  const targetNorm = normalizeMoveIdentifier(moveName);
  if (!targetNorm) {
    return { canLearn: false, reason: "unknown_move", label: "Desconocido", badgeClass: "badge-muted" };
  }

  const learnedTmMoves = (poke.learned_tm_moves || []).map(normalizeMoveIdentifier);
  const selectedMoves = (poke.selected_moves || []).map(normalizeMoveIdentifier);

  if (learnedTmMoves.includes(targetNorm) || selectedMoves.includes(targetNorm)) {
    return { canLearn: false, reason: "already_learned", label: "⚠️ Ya la sabe", badgeClass: "badge-warning" };
  }

  const tmMoves = (poke.tm_moves || []).map(normalizeMoveIdentifier);
  if (tmMoves.includes(targetNorm)) {
    return { canLearn: true, reason: "can_learn", label: "✅ Puede aprender", badgeClass: "badge-success" };
  }

  return { canLearn: false, reason: "incompatible", label: "❌ No puede", badgeClass: "badge-danger" };
}

function getItemWikiName(itemName) {
  const name = String(itemName || "");
  return name.startsWith("MT ") ? name.slice(3) : name;
}

function normalizeItemMap(items) {
  if (!items) return {};
  if (Array.isArray(items)) {
    const counts = {};
    items.forEach((item) => {
      const key = String(item || "").trim();
      if (!key) return;
      counts[key] = (counts[key] || 0) + 1;
    });
    return counts;
  }
  return Object.entries(items).reduce((acc, [key, value]) => {
    const qty = Number(value) || 0;
    if (qty > 0) acc[String(key)] = qty;
    return acc;
  }, {});
}

export function buildItemSpriteUrl(name) {
  const slugOverrides = {
    "Capsula Habilidad": "ability-capsule",
    "Caja Misteriosa I": "relic-silver",
    "Caja Misteriosa 1": "relic-silver",
    "Regalo del Primo jeque": "relic-gold",
    "Up-Grade": "up-grade",
    "Mejora": "up-grade",
  };
  const tmMove = String(name || "").startsWith("MT ") ? String(name).slice(3) : "";
  const slug = slugOverrides[name] || String(name || "").trim().toLowerCase().replace(/\s+/g, "-");
  const itemSlug = tmMove ? "tm-normal" : slug;
  return itemSlug ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/${encodeURIComponent(itemSlug)}.png` : "";
}

export function formatMoneyCompact(value) {
  const amount = Number(value) || 0;
  return `${(amount / 1000).toFixed(3).replace(/\.?0+$/, "")}K`;
}

function getNextBidValue(currentBid) {
  const current = Number(currentBid) || 0;
  return Math.max(5000, Math.ceil((current + 5000) / 5000) * 5000);
}

export const MEGA_DATA = {
  "venusaur-mega": { baseName: "Venusaur", megaStone: "Venusaurite" },
  "charizard-mega-x": { baseName: "Charizard", megaStone: "Charizardite X" },
  "charizard-mega-y": { baseName: "Charizard", megaStone: "Charizardite Y" },
  "blastoise-mega": { baseName: "Blastoise", megaStone: "Blastoisinite" },
  "beedrill-mega": { baseName: "Beedrill", megaStone: "Beedrillite" },
  "pidgeot-mega": { baseName: "Pidgeot", megaStone: "Pidgeotite" },
  "alakazam-mega": { baseName: "Alakazam", megaStone: "Alakazite" },
  "slowbro-mega": { baseName: "Slowbro", megaStone: "Slowbronite" },
  "gengar-mega": { baseName: "Gengar", megaStone: "Gengarite" },
  "kangaskhan-mega": { baseName: "Kangaskhan", megaStone: "Kangaskhanite" },
  "pinsir-mega": { baseName: "Pinsir", megaStone: "Pinsirite" },
  "gyarados-mega": { baseName: "Gyarados", megaStone: "Gyaradosite" },
  "aerodactyl-mega": { baseName: "Aerodactyl", megaStone: "Aerodactylite" },
  "mewtwo-mega-x": { baseName: "Mewtwo", megaStone: "Mewtwonite X" },
  "mewtwo-mega-y": { baseName: "Mewtwo", megaStone: "Mewtwonite Y" },
  "ampharos-mega": { baseName: "Ampharos", megaStone: "Ampharosite" },
  "steelix-mega": { baseName: "Steelix", megaStone: "Steelixite" },
  "scizor-mega": { baseName: "Scizor", megaStone: "Scizorite" },
  "heracross-mega": { baseName: "Heracross", megaStone: "Heracronite" },
  "houndoom-mega": { baseName: "Houndoom", megaStone: "Houndoominite" },
  "tyranitar-mega": { baseName: "Tyranitar", megaStone: "Tyranitarite" },
  "sceptile-mega": { baseName: "Sceptile", megaStone: "Sceptilite" },
  "blaziken-mega": { baseName: "Blaziken", megaStone: "Blazikenite" },
  "swampert-mega": { baseName: "Swampert", megaStone: "Swampertite" },
  "gardevoir-mega": { baseName: "Gardevoir", megaStone: "Gardevoirite" },
  "sableye-mega": { baseName: "Sableye", megaStone: "Sablenite" },
  "mawile-mega": { baseName: "Mawile", megaStone: "Mawilite" },
  "aggron-mega": { baseName: "Aggron", megaStone: "Aggronite" },
  "medicham-mega": { baseName: "Medicham", megaStone: "Medichamite" },
  "manectric-mega": { baseName: "Manectric", megaStone: "Manectite" },
  "sharpedo-mega": { baseName: "Sharpedo", megaStone: "Sharpedonite" },
  "camerupt-mega": { baseName: "Camerupt", megaStone: "Cameruptite" },
  "altaria-mega": { baseName: "Altaria", megaStone: "Altarianite" },
  "banette-mega": { baseName: "Banette", megaStone: "Banettite" },
  "absol-mega": { baseName: "Absol", megaStone: "Absolite" },
  "glalie-mega": { baseName: "Glalie", megaStone: "Glalitite" },
  "salamence-mega": { baseName: "Salamence", megaStone: "Salamencite" },
  "metagross-mega": { baseName: "Metagross", megaStone: "Metagrossite" },
  "latias-mega": { baseName: "Latias", megaStone: "Latiasite" },
  "latios-mega": { baseName: "Latios", megaStone: "Latiosite" },
  "kyogre-primal": { baseName: "Kyogre", megaStone: "Blue Orb" },
  "groudon-primal": { baseName: "Groudon", megaStone: "Red Orb" },
  "rayquaza-mega": { baseName: "Rayquaza", megaStone: "Life Orb" },
  "lopunny-mega": { baseName: "Lopunny", megaStone: "Lopunnite" },
  "garchomp-mega-z": { baseName: "Garchomp", megaStone: "Garchompite Z" },
  "lucario-mega-z": { baseName: "Lucario", megaStone: "Lucarionite Z" },
  "abomasnow-mega": { baseName: "Abomasnow", megaStone: "Abomasite" },
  "gallade-mega": { baseName: "Gallade", megaStone: "Galladite" },
  "audino-mega": { baseName: "Audino", megaStone: "Audinite" },
  "diancie-mega": { baseName: "Diancie", megaStone: "Diancite" },
  "clefable-mega": { baseName: "Clefable", megaStone: "Clefablite" },
  "victreebel-mega": { baseName: "Victreebel", megaStone: "Victreebelite" },
  "starmie-mega": { baseName: "Starmie", megaStone: "Starmite" },
  "dragonite-mega": { baseName: "Dragonite", megaStone: "Dragoninite" },
  "meganium-mega": { baseName: "Meganium", megaStone: "Meganiumite" },
  "feraligatr-mega": { baseName: "Feraligatr", megaStone: "Feraligatite" },
  "skarmory-mega": { baseName: "Skarmory", megaStone: "Skarmorite" },
  "froslass-mega": { baseName: "Froslass", megaStone: "Froslassite" },
  "emboar-mega": { baseName: "Emboar", megaStone: "Emboarite" },
  "excadrill-mega": { baseName: "Excadrill", megaStone: "Excadrillite" },
  "scolipede-mega": { baseName: "Scolipede", megaStone: "Scolipite" },
  "scrafty-mega": { baseName: "Scrafty", megaStone: "Scraftite" },
  "eelektross-mega": { baseName: "Eelektross", megaStone: "Eelektrossite" },
  "chandelure-mega": { baseName: "Chandelure", megaStone: "Chandelurite" },
  "chesnaught-mega": { baseName: "Chesnaught", megaStone: "Chesnaughtite" },
  "delphox-mega": { baseName: "Delphox", megaStone: "Delphoxite" },
  "greninja-mega": { baseName: "Greninja", megaStone: "Greninjite" },
  "pyroar-mega": { baseName: "Pyroar", megaStone: "Pyroarite" },
  "malamar-mega": { baseName: "Malamar", megaStone: "Malamarite" },
  "barbaracle-mega": { baseName: "Barbaracle", megaStone: "Barbaracite" },
  "dragalge-mega": { baseName: "Dragalge", megaStone: "Dragalgite" },
  "hawlucha-mega": { baseName: "Hawlucha", megaStone: "Hawluchanite" },
  "drampa-mega": { baseName: "Drampa", megaStone: "Drampanite" },
  "falinks-mega": { baseName: "Falinks", megaStone: "Falinksite" },
  "raichu-mega-x": { baseName: "Raichu", megaStone: "Raichunite X" },
  "raichu-mega-y": { baseName: "Raichu", megaStone: "Raichunite Y" },
  "chimecho-mega": { baseName: "Chimecho", megaStone: "Chimechonite" },
  "staraptor-mega": { baseName: "Staraptor", megaStone: "Staraptorite" },
  "golurk-mega": { baseName: "Golurk", megaStone: "Golurkite" },
  "meowstic-mega": { baseName: "Meowstic", megaStone: "Meowsticite" },
  "crabominable-mega": { baseName: "Crabominable", megaStone: "Crabominite" },
  "golisopod-mega": { baseName: "Golisopod", megaStone: "Golisopodite" },
  "scovillain-mega": { baseName: "Scovillain", megaStone: "Scovillainite" },
  "baxcalibur-mega": { baseName: "Baxcalibur", megaStone: "Baxcalibrite" },
};

export function normalizeMegaSlug(name) {
  let slug = String(name || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  if (slug.startsWith("mega-")) {
    const parts = slug.split("-");
    if (parts.length === 2) {
      slug = `${parts[1]}-mega`;
    } else if (parts.length >= 3) {
      slug = `${parts[1]}-mega-${parts.slice(2).join("-")}`;
    }
  } else if (slug.startsWith("primal-")) {
    const parts = slug.split("-");
    if (parts.length >= 2) {
      slug = `${parts[1]}-primal`;
    }
  }
  return slug;
}

export function getMegaInfo(pokeOrName) {
  if (!pokeOrName) return null;
  if (typeof pokeOrName === "object") {
    if (pokeOrName.is_mega && pokeOrName.base_species && pokeOrName.mega_stone) {
      return {
        isMega: true,
        baseName: pokeOrName.base_species,
        megaStone: pokeOrName.mega_stone,
      };
    }
    const name = pokeOrName.name || "";
    const slug = normalizeMegaSlug(name);
    if (MEGA_DATA[slug]) {
      return { isMega: true, ...MEGA_DATA[slug] };
    }
    if (slug.includes("-mega") || slug.startsWith("mega-")) {
      const cleanBase = slug.replace(/-mega|mega-/g, "").replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      return { isMega: true, baseName: cleanBase, megaStone: `${cleanBase}ite` };
    }
    return null;
  }
  const slug = normalizeMegaSlug(pokeOrName);
  if (MEGA_DATA[slug]) {
    return { isMega: true, ...MEGA_DATA[slug] };
  }
  if (slug.includes("-mega") || slug.startsWith("mega-")) {
    const cleanBase = slug.replace(/-mega|mega-/g, "").replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    return { isMega: true, baseName: cleanBase, megaStone: `${cleanBase}ite` };
  }
  return null;
}

export function isMegaPokemon(pokeOrName) {
  return Boolean(getMegaInfo(pokeOrName));
}

export const NATURE_EFFECTS = {
  Hardy: ["", ""], Lonely: ["Attack", "Defense"], Brave: ["Attack", "Speed"], Adamant: ["Attack", "Sp. Atk"], Naughty: ["Attack", "Sp. Def"],
  Bold: ["Defense", "Attack"], Docile: ["", ""], Relaxed: ["Defense", "Speed"], Impish: ["Defense", "Sp. Atk"], Lax: ["Defense", "Sp. Def"],
  Timid: ["Speed", "Attack"], Hasty: ["Speed", "Defense"], Serious: ["", ""], Jolly: ["Speed", "Sp. Atk"], Naive: ["Speed", "Sp. Def"],
  Modest: ["Sp. Atk", "Attack"], Mild: ["Sp. Atk", "Defense"], Quiet: ["Sp. Atk", "Speed"], Bashful: ["", ""], Rash: ["Sp. Atk", "Sp. Def"],
  Calm: ["Sp. Def", "Attack"], Gentle: ["Sp. Def", "Defense"], Sassy: ["Sp. Def", "Speed"], Careful: ["Sp. Def", "Sp. Atk"], Quirky: ["", ""],
};

export function formatNature(nature) {
  const name = nature || "Desconocida";
  const effects = NATURE_EFFECTS[name];
  if (!effects) return name;
  if (!effects[0]) return `${name} (sin cambios)`;
  return `${name} (+${effects[0]}, -${effects[1]})`;
}

export function renderConfigForm(containerEl, data, isHost) {
  const defaults = {
    turns_per_year: 3,
    yearly_money: 1000000,
    year_event_counts: {
      1: { positive: 3, neutral: 0, negative: 0 },
      2: { positive: 3, neutral: 0, negative: 0 },
      3: { positive: 3, neutral: 0, negative: 0 },
    },
    year_pools: {
      1: { normal: 2, mega: 0, legendary: 0 },
      2: { normal: 2, mega: 1, legendary: 0 },
      3: { normal: 0, mega: 1, legendary: 2 },
    },
  };

  const config = data?.mode_config || {};
  const yp = config.year_pools || defaults.year_pools;
  const y1 = yp[1] || yp["1"] || defaults.year_pools[1];
  const y2 = yp[2] || yp["2"] || defaults.year_pools[2];
  const y3 = yp[3] || yp["3"] || defaults.year_pools[3];

  const y1_norm = config.year1_normal ?? y1.normal ?? 2;
  const y1_mega = config.year1_mega ?? y1.mega ?? 0;
  const y1_leg = config.year1_legendary ?? y1.legendary ?? 0;

  const y2_norm = config.year2_normal ?? y2.normal ?? 2;
  const y2_mega = config.year2_mega ?? y2.mega ?? 1;
  const y2_leg = config.year2_legendary ?? y2.legendary ?? 0;

  const y3_norm = config.year3_normal ?? y3.normal ?? 0;
  const y3_mega = config.year3_mega ?? y3.mega ?? 1;
  const y3_leg = config.year3_legendary ?? y3.legendary ?? 2;

  const legacyEventCount = config.turns_per_year ?? defaults.turns_per_year;
  const legacyEventCounts = {
    1: { positive: legacyEventCount, neutral: 0, negative: 0 },
    2: { positive: legacyEventCount, neutral: 0, negative: 0 },
    3: { positive: legacyEventCount, neutral: 0, negative: 0 },
  };
  const eventCounts = config.year_event_counts || legacyEventCounts;
  const y1_events = eventCounts[1] || eventCounts["1"] || defaults.year_event_counts[1];
  const y2_events = eventCounts[2] || eventCounts["2"] || defaults.year_event_counts[2];
  const y3_events = eventCounts[3] || eventCounts["3"] || defaults.year_event_counts[3];

  const yearly_money = config.yearly_money ?? config.starting_money ?? config.year_starting_money_1 ?? defaults.yearly_money;

  containerEl.innerHTML = `
    <div class="subasta-config-container">
      <div class="config-section-title">⚙️ Configuración General</div>
      <div class="subasta-config-panel">
        <div class="form-group">
          <label for="subasta-yearly-money">💰 Dinero Inicial / Añadido por Año (K):</label>
          <input type="number" id="subasta-yearly-money" value="${yearly_money / 1000}" min="0" step="50" ${!isHost ? "disabled" : ""} />
        </div>
      </div>

      <div class="config-section-title" style="margin-top: 1rem;">🏆 Rondas de Subasta por Año (Pokémon por jugador)</div>
      <p class="config-help-text">Establece cuántos Pokémon conseguirá cada jugador en cada pool por año. La subasta irá pasando de una pool a la siguiente en orden.</p>

      <div class="year-pools-config-grid">
        <!-- AÑO 1 -->
        <div class="year-pool-card">
          <div class="year-pool-card-header">
            <h4>Año 1 (Cap Nv. 20)</h4>
          </div>
          <div class="pool-input-row">
            <label for="subasta-year1-normal">🔵 Pool Normal:</label>
            <input type="number" id="subasta-year1-normal" value="${y1_norm}" min="0" max="10" ${!isHost ? "disabled" : ""} />
          </div>
          <div class="pool-input-row">
            <label for="subasta-year1-mega">🟣 Pool Mega:</label>
            <input type="number" id="subasta-year1-mega" value="${y1_mega}" min="0" max="10" ${!isHost ? "disabled" : ""} />
          </div>
          <div class="pool-input-row">
            <label for="subasta-year1-legendary">🟡 Pool Legendaria:</label>
            <input type="number" id="subasta-year1-legendary" value="${y1_leg}" min="0" max="10" ${!isHost ? "disabled" : ""} />
          </div>
        </div>

        <!-- AÑO 2 -->
        <div class="year-pool-card">
          <div class="year-pool-card-header">
            <h4>Año 2 (Cap Nv. 40)</h4>
          </div>
          <div class="pool-input-row">
            <label for="subasta-year2-normal">🔵 Pool Normal:</label>
            <input type="number" id="subasta-year2-normal" value="${y2_norm}" min="0" max="10" ${!isHost ? "disabled" : ""} />
          </div>
          <div class="pool-input-row">
            <label for="subasta-year2-mega">🟣 Pool Mega:</label>
            <input type="number" id="subasta-year2-mega" value="${y2_mega}" min="0" max="10" ${!isHost ? "disabled" : ""} />
          </div>
          <div class="pool-input-row">
            <label for="subasta-year2-legendary">🟡 Pool Legendaria:</label>
            <input type="number" id="subasta-year2-legendary" value="${y2_leg}" min="0" max="10" ${!isHost ? "disabled" : ""} />
          </div>
        </div>

        <!-- AÑO 3 -->
        <div class="year-pool-card">
          <div class="year-pool-card-header">
            <h4>Año 3 (Cap Nv. 100)</h4>
          </div>
          <div class="pool-input-row">
            <label for="subasta-year3-normal">🔵 Pool Normal:</label>
            <input type="number" id="subasta-year3-normal" value="${y3_norm}" min="0" max="10" ${!isHost ? "disabled" : ""} />
          </div>
          <div class="pool-input-row">
            <label for="subasta-year3-mega">🟣 Pool Mega:</label>
            <input type="number" id="subasta-year3-mega" value="${y3_mega}" min="0" max="10" ${!isHost ? "disabled" : ""} />
          </div>
          <div class="pool-input-row">
            <label for="subasta-year3-legendary">🟡 Pool Legendaria:</label>
            <input type="number" id="subasta-year3-legendary" value="${y3_leg}" min="0" max="10" ${!isHost ? "disabled" : ""} />
          </div>
        </div>
      </div>

      <div class="config-section-title" style="margin-top: 1rem;">🎲 Eventos por Categoría y Año</div>
      <p class="config-help-text">La suma de las cantidades determina el total de turnos de eventos de cada año. Cada turno recibe un evento de la categoría elegida.</p>
      <div class="year-pools-config-grid">
        ${[
          { year: 1, counts: y1_events, neutral: true, negative: true },
          { year: 2, counts: y2_events, neutral: true, negative: true },
          { year: 3, counts: y3_events, neutral: true, negative: false },
        ].map(({ year, counts, neutral, negative }) => `
          <div class="year-pool-card">
            <div class="year-pool-card-header"><h4>Año ${year}</h4></div>
            <div class="pool-input-row">
              <label for="subasta-year${year}-events-positive">✨ Positivos:</label>
              <input type="number" id="subasta-year${year}-events-positive" value="${counts.positive ?? 3}" min="0" max="10" ${!isHost ? "disabled" : ""} />
            </div>
            <div class="pool-input-row">
              <label for="subasta-year${year}-events-neutral">⚖️ Neutrales:</label>
              <input type="number" id="subasta-year${year}-events-neutral" value="${counts.neutral ?? 0}" min="0" max="10" ${!isHost || !neutral ? "disabled" : ""} />
            </div>
            <div class="pool-input-row">
              <label for="subasta-year${year}-events-negative">⚠️ Negativos:</label>
              <input type="number" id="subasta-year${year}-events-negative" value="${counts.negative ?? 0}" min="0" max="10" ${!isHost || !negative ? "disabled" : ""} />
            </div>
            ${!negative ? `<p class="config-help-text">El Pokémon Ciego no puede aplicarse después del último año de subastas.</p>` : ""}
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

export function readConfigForm(containerEl) {
  const getInt = (id, fallback = 0) => {
    const el = document.getElementById(id);
    return el ? parseInt(el.value, 10) || 0 : fallback;
  };

  const y1_norm = getInt("subasta-year1-normal", 2);
  const y1_mega = getInt("subasta-year1-mega", 0);
  const y1_leg = getInt("subasta-year1-legendary", 0);

  const y2_norm = getInt("subasta-year2-normal", 2);
  const y2_mega = getInt("subasta-year2-mega", 1);
  const y2_leg = getInt("subasta-year2-legendary", 0);

  const y3_norm = getInt("subasta-year3-normal", 0);
  const y3_mega = getInt("subasta-year3-mega", 1);
  const y3_leg = getInt("subasta-year3-legendary", 2);

  const year_event_counts = {
    1: {
      positive: getInt("subasta-year1-events-positive", 3),
      neutral: getInt("subasta-year1-events-neutral", 0),
      negative: getInt("subasta-year1-events-negative", 0),
    },
    2: {
      positive: getInt("subasta-year2-events-positive", 3),
      neutral: getInt("subasta-year2-events-neutral", 0),
      negative: getInt("subasta-year2-events-negative", 0),
    },
    3: {
      positive: getInt("subasta-year3-events-positive", 3),
      neutral: getInt("subasta-year3-events-neutral", 0),
      negative: getInt("subasta-year3-events-negative", 0),
    },
  };

  const yearly_money = getInt("subasta-yearly-money", 1000) * 1000;

  return {
    year_event_counts,
    starting_money: yearly_money,
    yearly_money: yearly_money,
    year_starting_money_1: yearly_money,
    year_starting_money_2: yearly_money,
    year_starting_money_3: yearly_money,
    year_pools: {
      1: { normal: y1_norm, mega: y1_mega, legendary: y1_leg },
      2: { normal: y2_norm, mega: y2_mega, legendary: y2_leg },
      3: { normal: y3_norm, mega: y3_mega, legendary: y3_leg },
    },
    year1_normal: y1_norm,
    year1_mega: y1_mega,
    year1_legendary: y1_leg,
    year2_normal: y2_norm,
    year2_mega: y2_mega,
    year2_legendary: y2_leg,
    year3_normal: y3_norm,
    year3_mega: y3_mega,
    year3_legendary: y3_leg,
  };
}

export function renderAuctionView(data, sessionClient, isHost) {
  const auction = data.current_auction || {};
  const myData = data.my_data || { money: 0 };
  const hints = auction.hints || {};
  const poke = auction.pokemon || {};

  const isAuctionFinished = Boolean(auction.finished);
  const isWinnerPendingSecret = auction.awaiting_secret_choice && auction.winner === sessionClient.currentUsername;
  const canWinnerPreviewPokemon = isWinnerPendingSecret && poke.name && poke.image_url;
  const isFolded = (auction.folded_players || []).includes(sessionClient.currentUsername);
  const isHighBidder = auction.high_bidder === sessionClient.currentUsername;
  const canFold = !isFolded && !isHighBidder && !isWinnerPendingSecret;
  const pokeradarTypes = (auction.pokeradar_types || []).map((pokemonType) => escapeHtml(pokemonType));
  const pokeradarTypesReminder = pokeradarTypes.length
    ? ` <span>Tipos elegidos: <strong>${pokeradarTypes.join(" / ")}</strong>.</span>`
    : "";
  const pokeradarDiscount = auction.pokeradar_discount === true;
  const noSeContarActive = auction.no_se_contar_active === true;
  const aDeudaActive = auction.a_deuda_active === true;
  const noTouchBlocked = auction.no_touch_blocked === true;
  const minimumBidIncrement = noSeContarActive ? 50000 : 5000;
  const nextBidValue = noSeContarActive
    ? (Number(auction.current_bid) || 0) + minimumBidIncrement
    : getNextBidValue(auction.current_bid || 0);
  const getEffectiveAuctionCost = (bid) => {
    const discountedBid = pokeradarDiscount ? Math.floor(bid / 2) : bid;
    return aDeudaActive ? Math.ceil(discountedBid * 1.25) : discountedBid;
  };
  const discountedWinningBid = pokeradarDiscount
    ? Math.floor((auction.current_bid || 0) / 2)
    : (auction.current_bid || 0);
  const effectiveWinningBid = getEffectiveAuctionCost(auction.current_bid || 0);
  const secretCost = Math.ceil(effectiveWinningBid * 0.1);
  const revealHoldUntil = Number(auction.reveal_hold_until || 0) * 1000;
  const revealCountdownMs = revealHoldUntil > 0 ? Math.max(0, revealHoldUntil - Date.now()) : 0;
  const revealPercent = revealHoldUntil > 0 ? Math.max(0, Math.min(100, (revealCountdownMs / 5000) * 100)) : 0;
  const isPubliclyRevealed = Boolean(auction.publicly_revealed === true || (auction.finished && !poke.is_hidden && poke.name && poke.image_url));
  const isPokemonRevealed = Boolean(
    auction.early_reveal === true ||
    (
      !auction.awaiting_secret_choice &&
      auction.finished &&
      poke &&
      poke.name &&
      poke.image_url &&
      (isPubliclyRevealed || (!auction.reveal_hold_until || revealCountdownMs <= 5000))
    )
  );
  const hintAbility = hints.ability && !String(hints.ability).includes("🔒")
    ? `<a href="${buildWikidexUrl(hints.ability)}" target="_blank" rel="noopener noreferrer" class="badge-link">${hints.ability}</a>`
    : hints.ability || "🔒 Incógnito (4.0x)";
  const colorHint = hints.color;
  const pokemonColor = colorHint && Object.prototype.hasOwnProperty.call(POKEMON_COLORS, colorHint)
    ? POKEMON_COLORS[colorHint]
    : null;
  const colorHintDisplay = colorHint === undefined
    ? "🔒 Incógnito (1.5x)"
    : pokemonColor
      ? `<span role="img" aria-label="Color principal: ${pokemonColor.label}" title="${pokemonColor.label}" style="display:inline-block;width:1rem;height:1rem;margin:0 0.35rem;vertical-align:middle;border:1px solid currentColor;border-radius:3px;background-color:${pokemonColor.hex};"></span>${pokemonColor.label}`
      : "No disponible";

  const tier = data.current_phase_tier || (auction.phase_tier || (isMegaPokemon(poke) ? "mega" : "normal"));
  const tierDisplayName = tier === "mega" ? "🟣 Pool Mega" : (tier === "legendary" ? "🟡 Pool Legendaria" : "🔵 Pool Normal");
  const myWon = data.my_phase_pokemon_won ?? 0;
  const quota = data.current_phase_quota ?? auction.phase_quota ?? 1;
  const currentPhaseIdx = (data.current_pool_phase_index ?? 0) + 1;
  const totalPhases = (data.current_year_phases?.length) || 1;

  let html = `
    <div class="subasta-header">
      <span class="badge badge-primary">📌 ${data.stage_name}</span>
      <span class="badge badge-gold">🏆 ${tierDisplayName} (Fase ${currentPhaseIdx}/${totalPhases} • ${myWon}/${quota} míos)</span>
      <span class="badge badge-success">💰 Mi Saldo: $${formatMoneyCompact(myData.money || 0)}</span>
    </div>

    <div class="auction-grid">
      <!-- Tarjeta del Pokémon Subastado -->
      <div class="card auction-poke-card">
        <h3 class="auction-pokemon-title ${canWinnerPreviewPokemon ? 'auction-pokemon-title--winner' : ''}">${isPokemonRevealed || canWinnerPreviewPokemon ? `${poke.is_shiny ? '✨ ' : '🔍 '}${poke.name}${poke.is_shiny ? ' ✨' : ''}` : "🔍 Pokémon Incógnito"}</h3>
        <div class="poke-image-wrapper ${isPokemonRevealed || canWinnerPreviewPokemon ? 'poke-image-wrapper--revealed' : ''}">
          ${isPokemonRevealed || canWinnerPreviewPokemon
            ? `<img src="${poke.image_url}" alt="${poke.name}" class="poke-thumb poke-thumb--revealed" />`
            : `<div class="poke-unknown-avatar">❓</div>`}
        </div>
        ${isPokemonRevealed && auction.finished ? `<p class="base-price"><strong>Adjudicado a:</strong> ${auction.winner || "Ninguno"}</p>` : `<p class="base-price">Precio Inicial: <strong>$${formatMoneyCompact(auction.base_price || 5000)}</strong></p>`}

        ${auction.reveal_hold_until ? `
          <div class="reveal-countdown" style="margin-top: 12px;">
            <div style="display:flex; justify-content:space-between; font-size: 12px; margin-bottom: 6px; color: #e5e7eb;">
              <span>Revelando</span>
              <span>${Math.max(0, Math.ceil(revealCountdownMs / 1000))}s</span>
            </div>
            <div data-reveal-bar style="direction: rtl; width: 100%; height: 10px; background: rgba(255,255,255,0.12); border-radius: 999px; overflow: hidden;">
              <div data-reveal-fill style="height: 100%; width: ${revealPercent}%; background: linear-gradient(90deg, #fbbf24, #f59e0b, #ef4444); border-radius: 999px; transition: width 0.12s linear;"></div>
            </div>
          </div>
        ` : ""}

        <div class="hints-box">
          <h4>💡 Pistas Desbloqueadas:</h4>
          <ul>
            <li><strong>Letra Inicial:</strong> ${hints.first_letter || "?"} (1.0x)</li>
            <li><strong>Color principal:</strong> ${colorHintDisplay} (1.5x)</li>
            <li><strong>Región:</strong> ${hints.region || "🔒 Incógnito (2.0x)"}</li>
            <li><strong>Mejor Stat Base:</strong> ${hints.highest_stat || "🔒 Incógnito (3.0x)"}</li>
            <li><strong>Tipo Primario:</strong> ${hints.primary_type || "🔒 Incógnito (3.5x)"}</li>
            <li><strong>Habilidad:</strong> ${hintAbility}</li>
          </ul>
        </div>
      </div>

      <!-- Panel de Puja y Estado -->
      <div class="card auction-controls-card">
        <h3>🔥 Estado de la Puja</h3>
        <p class="current-bid-display ${auction.high_bidder === sessionClient.currentUsername ? 'current-bid-display--win' : 'current-bid-display--lose'}">Puja Actual: <span>$${formatMoneyCompact(auction.current_bid || 0)}</span></p>
        <p class="high-bidder-display">Mayor Pujador: <strong class="${auction.high_bidder === sessionClient.currentUsername ? 'high-bidder-display--win' : 'high-bidder-display--lose'}">${auction.high_bidder || "Ninguno"}</strong></p>
        ${auction.pokeradar_blocked ? `
          <p class="text-warning">📡 Tu Pokeradar no permite pujar por este Pokémon: no es de ninguno de los dos tipos elegidos.${pokeradarTypesReminder}</p>
        ` : pokeradarDiscount ? `
          <p class="text-success">📡 Pokeradar: reduce a la mitad el precio de tu puja ($${formatMoneyCompact(discountedWinningBid)} antes de otros efectos).${pokeradarTypesReminder}</p>
        ` : ""}
        ${noSeContarActive ? `
          <p class="text-warning">🧮 No Sé Contar: tus pujas deben aumentar de $50K en $50K hasta que ganes una subasta.</p>
        ` : ""}
        ${aDeudaActive ? `
          <p class="text-warning">💸 A Deuda: pagarás un 25% extra al ganar. ${auction.current_bid ? `Coste actual: $${formatMoneyCompact(effectiveWinningBid)}.` : ""} El efecto termina cuando ganes una subasta.</p>
        ` : ""}
        ${noTouchBlocked ? `
          <p class="text-warning">👀 Se Mira Pero NO se Toca: no puedes apostar en esta ronda; puedes ver el Pokémon desde el comienzo.</p>
        ` : ""}

        ${isAuctionFinished && !isWinnerPendingSecret ? `
          <div class="secret-choice-modal">
            <h4>🏁 La subasta ya terminó.</h4>
            <p>Ganador: <strong>${auction.winner || "Ninguno"}</strong></p>
            <p>El Pokémon ya fue adjudicado y la ronda está en espera de confirmación del ganador.</p>
          </div>
        ` : isWinnerPendingSecret ? `
          <div class="secret-choice-modal">
            <h4>🎉 ¡Ganaste la subasta de ${poke.name || 'este Pokémon'}!</h4>
            <p>¿Deseas pagar <strong>$${formatMoneyCompact(secretCost)}</strong> (10% del coste de adquisición${pokeradarDiscount ? " con Pokeradar" : ""}) para ocultar a <strong>${poke.name}</strong> a tus rivales?</p>
            <div class="btn-group">
              <button id="btn-secret-yes" class="btn btn-primary">🔒 Pagar $${formatMoneyCompact(secretCost)} y Ocultar</button>
              <button id="btn-secret-no" class="btn btn-secondary">👁️ Mostrar a todos ($0K)</button>
            </div>
          </div>
        ` : `
          <div class="bidding-actions">
            ${isHighBidder ? `
              <div class="high-bidder-winning-notice">
                <span class="high-bidder-icon">👑</span>
                <div>
                  <strong>¡Vas ganando la subasta!</strong>
                  <p>Espera a que otro jugador puje o se retire para no gastar de más.</p>
                </div>
              </div>
            ` : `
              <div class="bid-input-group">
                <input type="number" id="custom-bid-amount" value="${nextBidValue}" step="${minimumBidIncrement}" min="${nextBidValue}" />
                <button id="btn-bid-custom" class="btn btn-success" ${isFolded || auction.pokeradar_blocked || noTouchBlocked ? "disabled" : ""}>Pujar</button>
              </div>
            `}

            <div class="btn-group">
              ${!isHighBidder ? `
                <button id="btn-buyout" class="btn btn-warning" ${isFolded || auction.pokeradar_blocked || noTouchBlocked ? "disabled" : ""}>⚡ Compra Directa ($${formatMoneyCompact(getEffectiveAuctionCost(auction.buyout_price || 5000))}${pokeradarDiscount ? " con Pokeradar" : ""}${aDeudaActive ? " con A Deuda" : ""})</button>
              ` : ""}
              <button id="btn-fold" class="btn btn-danger" ${!canFold ? "disabled" : ""}>${isFolded ? "Retirado" : isHighBidder ? "🔒 Mayor Pujador" : "🚪 Retirarse"}</button>
            </div>
          </div>
        `}
      </div>
    </div>
  `;

  return html;
}

export function renderTurnEventsView(data, sessionClient, isHost) {
  const turnEvent = data.current_turn_event || {};
  const myData = data.my_data || {};
  const isResolved = myData.resolved_turn;
  const isAwaitingResultConfirmation = turnEvent.awaiting_confirmation === true;
  const pokemonList = myData.pokemon || [];
  const natureNames = Object.keys(NATURE_EFFECTS);
  const isNatureChange = turnEvent.type === "nature_change";
  const isPokemonTraffic = turnEvent.type === "pokemon_traffic";
  const isWonderTrade = turnEvent.type === "wonder_trade";
  const isCoinflip = turnEvent.type === "coinflip";
  const isMasterDisk = turnEvent.type === "master_disk";
  const isGholdengo = turnEvent.type === "gholdengo_usurer";
  const isPokeradar = turnEvent.type === "pokeradar";
  const availableGholdengoTargets = Object.entries(data.all_players || {})
    .filter(([username, player]) => username !== sessionClient.currentUsername && (player.pokemon_count || 0) > 0)
    .map(([username]) => username);
  const playerMoney = Number(myData.money || 0);
  const eventCategory = {
    positive: "✨ Evento positivo",
    neutral: "⚖️ Evento neutral",
    negative: "⚠️ Evento negativo",
  }[turnEvent.category] || "🎲 Evento";
  const isItemReward = turnEvent.reward_is_random === true
    && (turnEvent.granted_item || turnEvent.granted_items?.length);

  return `
    <div class="card event-turn-card">
      <h2>🎲 ${data.stage_name} — Turno ${data.current_turn} de ${data.max_turns}</h2>
      <hr />

      <div class="event-details">
        <span class="badge badge-primary">${eventCategory}</span>
        <h3>${turnEvent.title || "Evento de Turno"}</h3>
        <p>${turnEvent.description || "Un evento ha ocurrido en tu trayectoria."}</p>
      </div>

      <div class="turn-action-box">
        ${isResolved ? `
          <p class="text-success">✓ Has resuelto tu evento de este turno. Esperando a los demás jugadores...</p>
          ${turnEvent.result_message ? `<p>${turnEvent.result_message}</p>` : ""}
          ${turnEvent.type === "wonder_trade" && turnEvent.result_pokemon ? `
            <div class="wonder-trade-result">
              <h3>🎁 Pokémon obtenido: ${turnEvent.result_pokemon.name}</h3>
              ${turnEvent.result_pokemon.image_url ? `<img src="${turnEvent.result_pokemon.image_url}" alt="${turnEvent.result_pokemon.name}" style="width: 160px; height: 160px; object-fit: contain;" />` : ""}
            </div>
          ` : ""}
        ` : isAwaitingResultConfirmation && turnEvent.type === "wonder_trade" ? `
          <p class="text-success">${turnEvent.result_message || "Intercambio realizado."}</p>
          ${turnEvent.result_pokemon ? `
            <div class="wonder-trade-result">
              <h3>🎁 Pokémon obtenido: ${turnEvent.result_pokemon.name}</h3>
              ${turnEvent.result_pokemon.image_url ? `<img src="${turnEvent.result_pokemon.image_url}" alt="${turnEvent.result_pokemon.name}" style="width: 160px; height: 160px; object-fit: contain;" />` : ""}
            </div>
          ` : ""}
          <button id="btn-confirm-event-result" class="btn btn-primary btn-large">Aceptar y continuar</button>
        ` : isAwaitingResultConfirmation && turnEvent.type === "coinflip" ? `
          <p class="text-success">${turnEvent.result_message || "Mira el resultado de la animación para continuar."}</p>
          <p>Confirma el resultado desde la animación de Coinflip para avanzar.</p>
        ` : isNatureChange ? `
          <div class="nature-change-form">
            <label for="nature-change-pokemon">Pokémon:</label>
            <select id="nature-change-pokemon" ${pokemonList.length ? "" : "disabled"}>
              ${pokemonList.map((poke, idx) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`} — ${formatNature(poke.nature)}</option>`).join("")}
            </select>
            <label for="nature-change-nature">Nueva naturaleza:</label>
            <select id="nature-change-nature" ${pokemonList.length ? "" : "disabled"}>
              ${natureNames.filter((nature) => nature !== (pokemonList[0]?.nature || "")).map((nature) => `<option value="${nature}">${formatNature(nature)}</option>`).join("")}
            </select>
            <button id="btn-change-nature" class="btn btn-primary btn-large" ${pokemonList.length ? "" : "disabled"}>Cambiar naturaleza</button>
          </div>
        ` : isPokemonTraffic ? `
          <div class="pokemon-traffic-form">
            <p>Elige un Pokémon para vender:</p>
            <select id="traffic-pokemon-select" ${pokemonList.length ? "" : "disabled"}>
              ${pokemonList.map((poke, idx) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`}</option>`).join("")}
            </select>
            <div style="display: flex; gap: 0.75rem; margin-top: 0.75rem; flex-wrap: wrap;">
              <button id="btn-pokemon-traffic-sell" class="btn btn-primary btn-large" ${pokemonList.length ? "" : "disabled"}>💰 Vender Pokémon</button>
              <button id="btn-pokemon-traffic-skip" class="btn btn-secondary btn-large">❌ Rechazar oferta</button>
            </div>
            <p style="font-size: 0.85rem; color: #9ca3af; margin-top: 0.5rem;">Perderás el Pokémon y ganarás entre $0K y $125K</p>
          </div>
        ` : isWonderTrade ? `
          <div class="pokemon-traffic-form">
            ${pokemonList.length ? `
              <p>Elige el Pokémon que quieres intercambiar:</p>
              <select id="wonder-trade-pokemon-select">
                ${pokemonList.map((poke, idx) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`}</option>`).join("")}
              </select>
              <button id="btn-wonder-trade" class="btn btn-primary btn-large">🔄 Intercambiar Pokémon</button>
            ` : `
              <p>No tienes Pokémon para intercambiar.</p>
              <button id="btn-resolve-event" class="btn btn-secondary btn-large">Resolver evento</button>
            `}
          </div>
        ` : isCoinflip ? `
          <div class="pokemon-traffic-form">
            <label for="coinflip-amount">Cantidad a apostar (máximo $100K):</label>
            <input type="number" id="coinflip-amount" min="0.001" max="${Math.min(100, Math.floor(playerMoney) / 1000)}" step="0.001" value="${Math.min(100, Math.floor(playerMoney) / 1000)}" ${playerMoney >= 1 ? "" : "disabled"} />
            <div style="display:flex;gap:0.75rem;margin-top:0.75rem;flex-wrap:wrap;">
              <button id="btn-coinflip-accept" class="btn btn-primary btn-large" ${playerMoney >= 1 ? "" : "disabled"}>🪙 Apostar</button>
              <button id="btn-coinflip-decline" class="btn btn-secondary btn-large">Rechazar oferta</button>
            </div>
          </div>
        ` : isMasterDisk ? `
          <div class="pokemon-traffic-form">
            <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
              <button id="btn-master-disk-accept" class="btn btn-primary btn-large" ${playerMoney >= 100000 ? "" : "disabled"}>💿 Pagar $100K</button>
              <button id="btn-master-disk-decline" class="btn btn-secondary btn-large">Rechazar oferta</button>
            </div>
            ${playerMoney < 100000 ? '<p>No tienes suficiente dinero para aceptar.</p>' : ""}
          </div>
        ` : isGholdengo ? `
          <div class="pokemon-traffic-form">
            ${availableGholdengoTargets.length >= 2 ? `
              <p>Elige dos rivales. Gholdengo tomará un Pokémon aleatorio de cada uno.</p>
              <label for="gholdengo-target-one">Primer rival:</label>
              <select id="gholdengo-target-one">
                ${availableGholdengoTargets.map((username) => `<option value="${username}">${username}</option>`).join("")}
              </select>
              <label for="gholdengo-target-two">Segundo rival:</label>
              <select id="gholdengo-target-two">
                ${availableGholdengoTargets.map((username, index) => `<option value="${username}" ${index === 1 ? "selected" : ""}>${username}</option>`).join("")}
              </select>
              <div style="display:flex;gap:0.75rem;margin-top:0.75rem;flex-wrap:wrap;">
                <button id="btn-gholdengo-accept" class="btn btn-primary btn-large" ${playerMoney >= 1000000 ? "" : "disabled"}>🪙 Pagar $1000K y robar</button>
                <button id="btn-gholdengo-decline" class="btn btn-secondary btn-large">Rechazar oferta</button>
              </div>
              ${playerMoney < 1000000 ? '<p>No tienes suficiente dinero para aceptar.</p>' : ""}
            ` : `
              <p>No hay dos rivales con Pokémon disponibles para elegir.</p>
              <button id="btn-gholdengo-decline" class="btn btn-secondary btn-large">Rechazar oferta</button>
            `}
          </div>
        ` : isPokeradar ? `
          <div class="pokemon-traffic-form">
            <p>Elige dos tipos. Durante todo el próximo año solo podrás pujar por Pokémon de esos tipos y pagarás la mitad al conseguirlos.</p>
            <label for="pokeradar-type-one">Primer tipo:</label>
            <select id="pokeradar-type-one">
              ${POKEMON_TYPES.map((pokemonType) => `<option value="${pokemonType}">${pokemonType}</option>`).join("")}
            </select>
            <label for="pokeradar-type-two">Segundo tipo:</label>
            <select id="pokeradar-type-two">
              ${POKEMON_TYPES.map((pokemonType, index) => `<option value="${pokemonType}" ${index === 1 ? "selected" : ""}>${pokemonType}</option>`).join("")}
            </select>
            <div style="display:flex;gap:0.75rem;margin-top:0.75rem;flex-wrap:wrap;">
              <button id="btn-pokeradar-accept" class="btn btn-primary btn-large">📡 Activar Pokeradar</button>
            </div>
          </div>
        ` : isItemReward ? `
          <button id="btn-resolve-event" class="btn btn-primary btn-large">🎰 Girar la ruleta</button>
        ` : `
          <button id="btn-resolve-event" class="btn btn-primary btn-large">✨ Resolver Evento</button>
        `}
      </div>

      ${isHost ? `
        <div class="host-stage-bar">
          <button id="btn-force-next-stage" class="btn btn-secondary btn-small">⏩ Saltar/Avanzar Etapa (Host)</button>
        </div>
      ` : ""}
    </div>
  `;
}

export function renderExportView(data, sessionClient, isHost, lockedText = null, teamLocked = false) {
  const showdownText = lockedText !== null ? lockedText : (data.showdown_text || "");
  const isLocked = lockedText !== null;
  const standings = data.standings || [];
  const players = Object.keys(data.all_players || {});
  const isFinalStage = Number(data.stage) === 12;
  const myData = data.my_data || {};
  const isInDebt = Number(myData.money || 0) < 0;
  const pokemonForSale = myData.pokemon || [];

  return `
    <div class="card export-card">
      <h2>📋 ${data.stage_name}</h2>
      ${teamLocked ? `
        <div role="status" style="min-height: 45vh; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
          <span aria-hidden="true" style="font-size: clamp(7rem, 25vw, 14rem); line-height: 1;">🔒</span>
          <h2 style="font-size: clamp(1.5rem, 5vw, 2.5rem);">Esperando a que el host avance de fase</h2>
        </div>
      ` : `
        <p>${isLocked
          ? "Tu equipo ha sido fijado. Copia el texto para importarlo en <strong>Pokémon Showdown</strong>:"
          : "Edita si lo necesitas y luego fija tu equipo para poder copiarlo a <strong>Pokémon Showdown</strong>:"
        }</p>
      `}

      ${teamLocked ? "" : isInDebt ? `
        <div class="debt-warning" role="alert">
          <strong>Saldo negativo: no puedes fijar tu equipo todavía.</strong>
          <p>Vende Pokémon a la máquina por el 25% de su precio de compra inmediata para recuperar saldo.</p>
        </div>
        <div class="pokemon-sale-list">
          ${pokemonForSale.map((pokemon, index) => `
            <div class="pokemon-sale-row">
              <span>${pokemon.name || `Pokémon ${index + 1}`}</span>
              <button class="btn btn-small btn-warning btn-sell-pokemon" data-pokemon-index="${index}">
                Vender · $${formatMoneyCompact(pokemon.sell_value || 0)}
              </button>
            </div>
          `).join("") || '<p class="text-muted">No tienes Pokémon para vender.</p>'}
        </div>
      ` : `<textarea id="showdown-text-area" rows="12" class="code-area" ${isLocked ? "readonly" : ""}>${showdownText}</textarea>`}

      ${teamLocked ? "" : `<div class="btn-group">
        ${isLocked
          ? `<button id="btn-copy-showdown" class="btn btn-success">📋 Copiar al Portapapeles</button>`
          : `<button id="btn-lock-team" class="btn btn-primary" ${isInDebt ? "disabled" : ""}>🔒 Fijar Equipo</button>`
        }
      </div>`}

      ${isHost ? `
        <div class="admin-match-box">
          <div class="solvency-status">
            <strong>Jugadores con saldo positivo: ${data.positive_player_count || 0}/${data.total_player_count || players.length}</strong>
            ${data.negative_players?.length
              ? `<p>En negativo: ${data.negative_players.join(", ")}</p>`
              : '<p>Todos los jugadores están en positivo.</p>'}
          </div>
          <h3>⚖️ Registrar resultados de esta fase</h3>
          <div class="form-group">
            <label>Jugador 1:</label>
            <select id="admin-match-player-one">
              ${players.map((p) => `<option value="${p}">${p}</option>`).join("")}
            </select>
            <label for="admin-match-points-one">Puntos (0–3):</label>
            <select id="admin-match-points-one">
              ${[0, 1, 2, 3].map((points) => `<option value="${points}" ${points === 3 ? "selected" : ""}>${points}</option>`).join("")}
            </select>
          </div>
          <div class="form-group">
            <label>Jugador 2:</label>
            <select id="admin-match-player-two">
              ${players.map((p) => `<option value="${p}">${p}</option>`).join("")}
            </select>
            <label for="admin-match-points-two">Puntos (0–3):</label>
            <select id="admin-match-points-two">
              ${[0, 1, 2, 3].map((points) => `<option value="${points}" ${points === 1 ? "selected" : ""}>${points}</option>`).join("")}
            </select>
          </div>
          <button id="btn-submit-match" class="btn btn-secondary">Registrar resultado</button>
          <button id="btn-finalize-event" class="btn btn-primary">${isFinalStage ? "Finalizar evento y revelar ganador" : "Finalizar evento"}</button>
        </div>
      ` : ""}

      <div class="standings-card">
        <h3>Clasificación acumulada</h3>
        <table class="standings-table">
          <thead><tr><th>Posición</th><th>Jugador</th><th>Puntos</th></tr></thead>
          <tbody>${standings.map((s, idx) => `
            <tr><td>#${idx + 1}</td><td><strong>${s.username}</strong></td><td>${s.points} pts</td></tr>
          `).join("")}</tbody>
        </table>
      </div>
    </div>
  `;
}

export function renderAdminAndStandingsView(data, sessionClient, isHost) {
  const standings = data.standings || [];
  const winner = standings[0];
  const removedPokemon = data.removed_pokemon || [];

  return `
    <div class="card standings-card">
      <h2>🏆 ${data.stage_name}</h2>
      <hr />

      ${data.event_finished && winner ? `
        <div class="secret-choice-modal">
          <h2>🏆 Evento finalizado</h2>
          <p>El ganador es <strong>${winner.username}</strong> con <strong>${winner.points} pts</strong>.</p>
        </div>
      ` : ""}

      ${data.event_finished ? `
        <section class="secret-choice-modal">
          <h3>Pokémon no encontrados en PokeAPI</h3>
          ${removedPokemon.length ? `
            <ul>
              ${removedPokemon.map((entry) => `
                <li>
                  <strong>${escapeHtml(entry.pokemon_name || "Nombre desconocido")}</strong>
                  ${entry.api_name && entry.api_name !== entry.pokemon_name
                    ? `(forma consultada: ${escapeHtml(entry.api_name)})`
                    : ""}
                  — Año ${escapeHtml(entry.year)}, pool ${escapeHtml(entry.pool || "")}
                  (${entry.database_removed ? "eliminado de la base de datos" : "no se pudo confirmar su eliminación de la base de datos"})
                </li>
              `).join("")}
            </ul>
          ` : "<p>No se retiraron Pokémon por errores 404 de PokeAPI.</p>"}
        </section>
      ` : ""}

      <table class="standings-table">
        <thead>
          <tr>
            <th>Posición</th>
            <th>Jugador</th>
            <th>Puntos</th>
          </tr>
        </thead>
        <tbody>
          ${standings.map((s, idx) => `
            <tr>
              <td>#${idx + 1}</td>
              <td><strong>${s.username}</strong></td>
              <td>${s.points} pts</td>
            </tr>
          `).join("")}
        </tbody>
      </table>

    </div>
  `;
}

export function renderMyPokemonInventory(data, sessionClient, isHost, activeBoxId = null, pokemonCardColors = {}, pokemonMoveUiStates = {}) {
  const myData = data.my_data || {};
  const pokemonList = myData.pokemon || [];
  const bagItems = normalizeItemMap(myData.items || {});
  const bagEntries = Object.entries(bagItems);
  const currentUsername = sessionClient.currentUsername;
  const connectedPlayers = (data.connected_players || []).filter((username) => username !== currentUsername);
  const tradeSession = data.trade_session;
  const preparationStage = [4, 8, 12, 13].includes(Number(data.stage || 0));
  const auctionOrEventStage = [2, 3, 6, 7, 10, 11].includes(Number(data.stage || 0));
  const tradeTargets = Object.keys(data.all_players || {}).filter((username) => username !== currentUsername);
  const levelCap = data.current_year === 1 ? 20 : (data.current_year === 2 ? 40 : 100);
  const shopVisible = preparationStage || auctionOrEventStage;
  const pokemonBoxes = Array.isArray(myData.pokemon_boxes) && myData.pokemon_boxes.length
    ? myData.pokemon_boxes
    : [{ id: "box-1", name: "Caja 1" }];
  const activeBox = pokemonBoxes.find((box) => box.id === activeBoxId) || pokemonBoxes[0];
  const boxCounts = pokemonBoxes.map((box) => ({
    ...box,
    count: pokemonList.filter((poke) => (poke.box_id || pokemonBoxes[0].id) === box.id).length,
  }));
  const shopCatalogByYear = {
    1: [
      { name: "Caja Misteriosa I", price: 100000, isBox: true, description: "Oran Berry 75%, MT Earthquake 5%, MT Flamethrower 5%, MT Shadow Ball 5%, Cápsula Hab. 5%, Porygon + Objeto Mejora 3%, Pokémon Shiny 1%, $500K 1%" },
      { name: "Regalo del Primo jeque", price: 250000, isBox: true, description: "Galvantula 25%, Scolipede 25%, Sawk 25%, Gardevoir 25% (con Naturaleza y Habilidad aleatorias)" },
      { name: "Eviolite", price: 100000 },
      { name: "Sitrus Berry", price: 50000 },
      { name: "MT Fire Punch", price: 30000 },
      { name: "MT Thunder Punch", price: 30000 },
      { name: "MT Ice Punch", price: 30000 },
      { name: "Capsula Habilidad", price: 150000 },
      { name: "Cambia Formas", price: 75000 },
      { name: "Silk Scarf", price: 50000 },
      { name: "Water Stone", price: 100000 },
      { name: "Fire Stone", price: 100000 },
      { name: "Leaf Stone", price: 100000 },
    ],
    2: [
      { name: "Ruleta Plates", price: 20000, isRoulette: true, description: "Gana una Plate aleatoria entre las 17 Plates de tipo." },
      { name: "Capsula Habilidad", price: 150000 },
      { name: "Cambia Formas", price: 75000 },
      { name: "Flame Orb", price: 50000 },
      { name: "Sitrus Berry", price: 50000 },
      { name: "MT Toxic", price: 100000 },
      { name: "MT Protect", price: 20000 },
      { name: "Ruleta Piedras", price: 20000, isRoulette: true, description: "Gana una piedra evolutiva aleatoria entre las 10 disponibles." },
    ],
    3: [
      { name: "Life Orb", price: 100000 },
      { name: "Assault Vest", price: 100000 },
      { name: "Focus Sash", price: 100000 },
      { name: "Capsula Habilidad", price: 150000 },
      { name: "Ruleta Mentas", price: 30000, isRoulette: true, description: "Gana una de las 25 Mentas de naturaleza, todas con la misma probabilidad." },
      { name: "Leftovers", price: 200000 },
      { name: "Ruleta Choice", price: 150000, isRoulette: true, description: "Gana una Choice Scarf, Choice Band o Choice Specs, todas con la misma probabilidad." },
      { name: "Ruleta MT OP", price: 100000, isRoulette: true, description: "Gana una MT competitiva aleatoria, todas con la misma probabilidad." },
      { name: "OmniPiedra", price: 100000 },
    ],
  };
  const currentYear = Number(data.current_year || 1);
  const currentShopItems = shopCatalogByYear[currentYear] || shopCatalogByYear[1];
  const isPriorityShopItem = (item) => Boolean(
    item.isBox ||
    item.isRoulette ||
    item.name.startsWith("Caja Misteriosa") ||
    item.name.startsWith("Regalo del Primo")
  );
  const orderedShopItems = [
    ...currentShopItems.filter(isPriorityShopItem),
    ...currentShopItems.filter((item) => !isPriorityShopItem(item)),
  ];
  const shopTitle = currentYear === 1 ? "Tienda Año 1" : currentYear === 2 ? "Tienda Año 2" : "Tienda Año 3";

  return `
    <div class="card inventory-card">
      <h3>Mis Pokémon Conseguidos (Level Cap: Nv. ${levelCap})</h3>
      ${preparationStage && (!tradeSession || ['completed', 'cancelled'].includes(tradeSession.status)) && bagItems["Cable Link"] && tradeTargets.length && pokemonList.length ? `
        <div class="trade-panel">
          <h4>🔗 Intercambio con Cable Link</h4>
          <select id="trade-target-player">
            ${tradeTargets.map((username) => `<option value="${username}">${username}</option>`).join("")}
          </select>
          <select id="trade-own-pokemon">
            ${pokemonList.map((poke, idx) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`}</option>`).join("")}
          </select>
          <button class="btn btn-small btn-primary" id="btn-start-trade">Usar Cable Link</button>
        </div>
      ` : ""}
      ${tradeSession && tradeSession.status !== 'completed' && tradeSession.status !== 'cancelled' && (tradeSession.initiator === currentUsername || tradeSession.target === currentUsername) ? `
        <div class="trade-panel">
          <h4>🔗 Intercambio: ${tradeSession.initiator} ↔ ${tradeSession.target}</h4>
          ${tradeSession.target_pokemon ? `
            <p><strong>${tradeSession.initiator_pokemon.name}</strong> ↔ <strong>${tradeSession.target_pokemon.name}</strong></p>
            <button class="btn btn-small btn-primary" id="btn-confirm-trade">Confirmar intercambio</button>
            ${tradeSession.initiator === currentUsername ? '<button class="btn btn-small btn-danger" id="btn-cancel-trade">Cancelar intercambio</button>' : ''}
            <p>${Object.keys(tradeSession.confirms || {}).length}/2 confirmaciones</p>
          ` : tradeSession.target === currentUsername ? `
            <p>Elige uno de tus Pokémon para ofrecerlo:</p>
            <select id="trade-target-pokemon">
              ${(pokemonList || []).map((poke, idx) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`}</option>`).join("")}
            </select>
            <button class="btn btn-small btn-primary" id="btn-select-trade-pokemon">Elegir Pokémon</button>
          ` : `
            <p>Esperando a que el otro jugador elija su Pokémon.</p>
            ${tradeSession.initiator === currentUsername ? '<button class="btn btn-small btn-danger" id="btn-cancel-trade">Cancelar solicitud</button>' : ''}
          `}
        </div>
      ` : ""}
      ${tradeSession && tradeSession.status === 'completed' && (tradeSession.initiator === currentUsername || tradeSession.target === currentUsername) ? `
        <div class="trade-panel">
          <span><strong>Intercambio realizado.</strong> Los dos Pokémon han cambiado de entrenador.</span>
          ${tradeSession.initiator === currentUsername ? '<button class="btn btn-small btn-secondary" id="btn-cancel-trade" style="margin-left: 8px;">Cerrar</button>' : ''}
        </div>
      ` : ""}
      <div class="pokemon-boxes" role="tablist" aria-label="Cajas de Pokémon">
        ${boxCounts.map((box) => `
          <button type="button" class="pokemon-box-tab ${box.id === activeBox.id ? 'is-active' : ''}" data-pokemon-box-id="${box.id}" role="tab" aria-selected="${box.id === activeBox.id}">
            ${box.name} <span>${box.count}</span>
          </button>
        `).join("")}
        <button type="button" class="btn btn-small btn-secondary btn-create-pokemon-box">＋ Crear caja</button>
      </div>
      <div class="inventory-grid">
        ${pokemonList.length ? pokemonList.map((poke, pokeIdx) => {
          if ((poke.box_id || pokemonBoxes[0].id) !== activeBox.id) return "";
          const isMega = isMegaPokemon(poke);
          const levelUpMoves = (poke.level_up_moves || []).filter((m) => m.level <= levelCap);
          const selectedMoves = poke.selected_moves || [];
          const moveUiState = pokemonMoveUiStates[pokeIdx]?.name === poke.name
            ? pokemonMoveUiStates[pokeIdx]
            : null;
          const displayedMoves = moveUiState?.selectedMoves || selectedMoves;
          const movesPanelMode = moveUiState?.mode || "closed";
          const itemName = poke.item || poke.held_item || 'Sin ítem';
          const abilityName = poke.ability || 'Desconocida';
          const natureName = formatNature(poke.nature);
          const pokemonCardColorId = POKEMON_CARD_COLORS[pokemonCardColors[pokeIdx]]
            ? pokemonCardColors[pokeIdx]
            : "green";
          const pokemonCardColor = POKEMON_CARD_COLORS[pokemonCardColorId];
          const pokemonColorOptions = Object.entries(POKEMON_CARD_COLORS).map(([colorId, color]) => `
            <button
              type="button"
              class="pokemon-color-option${pokemonCardColorId === colorId ? " is-selected" : ""}"
              data-poke-idx="${pokeIdx}"
              data-color-id="${colorId}"
              aria-label="Color ${color.label}"
              title="${color.label}"
              style="--color-swatch: ${color.hex}"
            ></button>
          `).join("");
          const normalizeWikidexName = (name) => encodeURI(String(name).trim().replace(/\s+/g, "_").replace(/[()]/g, ""));
          const abilityHtml = abilityName !== 'Desconocida'
            ? `<a href="https://www.wikidex.net/wiki/${normalizeWikidexName(abilityName)}" target="_blank" rel="noopener noreferrer" class="badge-link">${abilityName}</a>`
            : abilityName;
          const itemHtml = itemName && itemName !== 'Sin ítem' && itemName !== 'Sin item'
            ? `<a href="https://www.wikidex.net/wiki/${normalizeWikidexName(itemName)}" target="_blank" rel="noopener noreferrer" class="badge-link">${itemName}</a>`
            : itemName;
          const evolutionOptions = isMega ? [] : (Array.isArray(poke.evolution_options) && poke.evolution_options.length > 0
            ? poke.evolution_options
            : (poke.evolution_target ? [{ target: poke.evolution_target, item: poke.evolution_item, level: poke.next_evolution_level, trade: poke.evolution_trade, friendship: poke.evolution_friendship }] : []));
          const hasOmniPiedra = (bagItems["OmniPiedra"] || 0) > 0;

          const validEvolutionOptions = evolutionOptions.filter((opt) => {
            const optItem = opt.item || '';
            const hasOptItem = optItem && (
              (bagItems[optItem] || 0) > 0 ||
              (optItem.replace(/\s+/g, "-") && (bagItems[optItem.replace(/\s+/g, "-")] || 0) > 0) ||
              (optItem.replace(/-/g, " ") && (bagItems[optItem.replace(/-/g, " ")] || 0) > 0) ||
              (optItem.toLowerCase().includes("grade") && ((bagItems["Up-Grade"] || 0) > 0 || (bagItems["Up Grade"] || 0) > 0 || (bagItems["Mejora"] || 0) > 0))
            );
            const currentYear = Number(data.current_year || 1);
            const currentLevel = Number(poke.level || (currentYear === 1 ? 20 : (currentYear === 2 ? 40 : 100)));

            if (optItem && !hasOptItem && !hasOmniPiedra) return false;
            if (opt.trade && !optItem && !poke.received_by_trade) return false;
            if (opt.friendship && currentYear < 2) return false;
            if (currentYear === 1 && !optItem) return false;

            const optLevel = Number(opt.level ?? 0);
            if (optLevel > 0 && currentLevel < optLevel) return false;

            return true;
          });

          const canEvolve = validEvolutionOptions.length > 0;
          let evolutionHtml = '';
          if (canEvolve) {
            if (validEvolutionOptions.length > 1) {
              evolutionHtml = `
                <div class="evolution-menu-container" style="position: relative; display: inline-block;">
                  <button type="button" class="btn btn-small btn-primary btn-toggle-evolution-menu" data-poke-idx="${pokeIdx}">
                    ✨ Evolucionar (${validEvolutionOptions.length}) ▾
                  </button>
                  <div class="evolution-menu hidden" id="evo-menu-${pokeIdx}" style="position: absolute; bottom: 100%; left: 0; z-index: 100; background: #1f293d; border: 1px solid #3b82f6; border-radius: 8px; padding: 6px; box-shadow: 0 8px 16px rgba(0,0,0,0.6); min-width: 170px;">
                    <div style="font-size: 0.72rem; color: #9ca3af; margin-bottom: 6px; font-weight: bold; text-transform: uppercase;">Elegir evolución:</div>
                    ${validEvolutionOptions.map((opt) => {
                      const optItem = opt.item || '';
                      const itemSprite = optItem ? `<img src="${buildItemSpriteUrl(optItem)}" alt="${optItem}" style="width:16px;height:16px;margin-right:4px;vertical-align:middle;" />` : '';
                      const reqText = optItem ? ` (${optItem} o OmniPiedra)` : '';
                      return `
                        <button type="button" class="btn btn-small btn-secondary btn-evolve-target-option" data-poke-idx="${pokeIdx}" data-target-name="${opt.target}" style="width:100%; text-align:left; margin-bottom:4px; display:flex; align-items:center; justify-content:flex-start; font-size:0.8rem;">
                          ${itemSprite} <span>${opt.target}${reqText}</span>
                        </button>
                      `;
                    }).join("")}
                  </div>
                </div>
              `;
            } else {
              const singleOpt = validEvolutionOptions[0];
              const singleItem = singleOpt.item || '';
              const singleButtonContent = singleItem
                ? `<img src="${buildItemSpriteUrl(singleItem)}" alt="${singleItem}" /> Evolucionar (${singleOpt.target})`
                : `✨ Evolucionar (${singleOpt.target})`;
              evolutionHtml = `<button type="button" class="btn btn-small btn-primary btn-evolve-pokemon" data-poke-idx="${pokeIdx}" data-target-name="${singleOpt.target}" title="Evolucionar a ${singleOpt.target}">${singleButtonContent}</button>`;
            }
          }

          return `
            <details
              class="poke-inventory-item"
              data-poke-idx="${pokeIdx}"
              data-pokemon-color-key="${pokeIdx}"
              data-color-id="${pokemonCardColorId}"
              style="--pokemon-accent: ${pokemonCardColor.hex}; --pokemon-accent-rgb: ${pokemonCardColor.rgb}"
            >
              <summary class="poke-inventory-summary">
                <span class="poke-inventory-name">${poke.name || `Pokémon ${pokeIdx + 1}`}</span>
                <span class="poke-inventory-chevron" aria-hidden="true">▾</span>
              </summary>
              <div class="poke-inventory-details">
                ${pokemonBoxes.length > 1 ? `
                  <label class="pokemon-box-move">
                    Caja:
                    <select class="pokemon-box-select" data-poke-idx="${pokeIdx}" aria-label="Mover ${poke.name || 'Pokémon'} a otra caja">
                      ${pokemonBoxes.map((box) => `<option value="${box.id}" ${(poke.box_id || pokemonBoxes[0].id) === box.id ? "selected" : ""}>${box.name}</option>`).join("")}
                    </select>
                  </label>
                ` : ""}
              <div class="poke-inv-header">
                ${poke.image_url && poke.name
                  ? `<a href="${buildWikidexUrl(poke)}" target="_blank" rel="noopener noreferrer"><img src="${poke.image_url}" class="poke-thumb" alt="${poke.name}" /></a>`
                  : (poke.image_url ? `<img src="${poke.image_url}" class="poke-thumb" />` : '')}
                <div>
                  <div class="pokemon-level-color-row">
                    <span class="badge poke-inv-level">Nv. ${poke.level || levelCap}</span>
                    <div class="pokemon-color-picker">
                      <button
                        type="button"
                        class="pokemon-color-toggle"
                        data-poke-idx="${pokeIdx}"
                        aria-label="Cambiar color de ${poke.name || `Pokémon ${pokeIdx + 1}`}"
                        aria-expanded="false"
                        title="Cambiar color"
                      ></button>
                      <div class="pokemon-color-options hidden" role="group" aria-label="Colores para ${poke.name || `Pokémon ${pokeIdx + 1}`}">
                        ${pokemonColorOptions}
                      </div>
                    </div>
                  </div>
                  ${poke.is_shiny ? '<span class="badge badge-shiny">✨ SHINY</span>' : ''}
                  <span class="badge badge-green">Habilidad: ${abilityHtml}</span>
                  <span class="badge">Naturaleza: ${natureName}</span>
                </div>
              </div>

              ${isMega ? '' : `
                <div class="poke-item-line">
                  <span class="badge badge-item"><strong>Ítem:</strong> ${itemHtml}
                    ${itemName !== 'Sin ítem' && itemName !== 'Sin item'
                      ? `<button type="button" class="btn-remove-item" data-poke-idx="${pokeIdx}" aria-label="Quitar ${itemName}" title="Quitar objeto">✕</button>`
                      : ''}
                  </span>
                  ${bagEntries.length ? `
                    <div class="item-equip-box">
                      <select class="poke-item-select" data-poke-idx="${pokeIdx}">
                        <option value="">-- Cambiar item --</option>
                        ${bagEntries.map(([itemName, qty]) => `<option value="${itemName}">${itemName} (x${qty})</option>`).join("")}
                      </select>
                      <button class="btn btn-small btn-primary btn-equip-item" data-poke-idx="${pokeIdx}">Cambiar</button>
                    </div>
                  ` : ""}
                </div>
              `}

              ${evolutionHtml}

              <div class="moves-selector-box" data-poke-idx="${pokeIdx}" data-mode="${movesPanelMode}">
                <div class="saved-moves-list">
                  ${displayedMoves.length
                    ? displayedMoves.map((moveName) => `<span class="move-pill">${escapeHtml(moveName)}</span>`).join("")
                    : '<span class="text-muted">Sin movimientos seleccionados</span>'}
                </div>
                <button type="button" class="btn btn-small btn-secondary btn-open-moves" data-poke-idx="${pokeIdx}">Movimientos</button>
                <div class="moves-editor-panel">
                  <div class="move-controls move-view-actions">
                    <button type="button" class="btn btn-small btn-secondary btn-back-moves" data-poke-idx="${pokeIdx}">Volver</button>
                    <button type="button" class="btn btn-small btn-primary btn-edit-moves" data-poke-idx="${pokeIdx}">Modificar</button>
                  </div>
                  <div class="move-controls move-edit-actions">
                    <button type="button" class="btn btn-small btn-secondary btn-back-moves" data-poke-idx="${pokeIdx}">Volver</button>
                    <button type="button" class="btn btn-small btn-primary btn-save-moves" data-poke-idx="${pokeIdx}">Guardar</button>
                  </div>
                  <div class="moves-checkboxes">
                    ${levelUpMoves.map((m) => {
                      const isSelected = displayedMoves.includes(m.name);
                      const isInitiallySelected = selectedMoves.includes(m.name);
                      const moveUrl = buildWikidexUrl(m.name);
                      return `
                        <a href="${moveUrl}" target="_blank" rel="noopener noreferrer" class="move-link${isSelected ? " is-selected" : ""}" data-poke-idx="${pokeIdx}" data-move-name="${escapeHtml(m.name)}" data-initially-selected="${isInitiallySelected ? "true" : "false"}">${escapeHtml(m.name)}</a>
                      `;
                    }).join("")}
                  </div>
                </div>
              </div>
              </div>
            </details>
          `;
        }).join("") : '<p class="text-muted">Aún no has conseguido ningún Pokémon en las subastas.</p>'}
        ${pokemonList.length && !pokemonList.some((poke) => (poke.box_id || pokemonBoxes[0].id) === activeBox.id)
          ? '<p class="text-muted">Esta caja está vacía. Elige una caja en un Pokémon para moverlo aquí.</p>'
          : ""}
      </div>

      <div class="inventory-actions">
        <div class="backpack-panel">
          <button type="button" class="btn btn-secondary inventory-menu-toggle" data-menu-target="backpack-menu" aria-expanded="false">🎒 Mochila</button>
        </div>
        ${isHost ? `
          <div class="backpack-panel">
            <button type="button" class="btn btn-small btn-secondary inventory-menu-toggle" data-menu-target="host-transfer-menu" aria-expanded="false">👑 Transferir host</button>
          </div>
        ` : ""}
        ${shopVisible ? `
          <div class="backpack-panel">
            <button type="button" class="btn btn-secondary inventory-menu-toggle" data-menu-target="shop-menu" aria-expanded="false">🛒 Tienda</button>
          </div>
        ` : ""}
      </div>

      ${isHost ? `
        <div class="inventory-modal-overlay" data-modal="host-transfer-menu" aria-hidden="true">
          <div class="backpack-menu" data-menu="host-transfer-menu">
            <div class="backpack-menu-header">
              <h4>👑 Transferir host</h4>
              <button type="button" class="btn-close-menu" aria-label="Cerrar">✕</button>
            </div>
            <div class="backpack-menu-body">
              ${connectedPlayers.length ? `
                <label for="host-transfer-target">Nuevo host:</label>
                <select id="host-transfer-target">
                  ${connectedPlayers.map((username) => `<option value="${escapeHtml(username)}">${escapeHtml(username)}</option>`).join("")}
                </select>
                <button type="button" class="btn btn-small btn-primary" id="btn-transfer-host">Transferir host</button>
              ` : '<p class="text-muted">No hay otros jugadores conectados.</p>'}
            </div>
          </div>
        </div>
      ` : ""}

      <div class="inventory-modal-overlay" data-modal="backpack-menu" aria-hidden="true">
        <div class="backpack-menu" data-menu="backpack-menu">
          <div class="backpack-menu-header">
            <h4>🎒 Mochila</h4>
            <button type="button" class="btn-close-menu" aria-label="Cerrar">✕</button>
          </div>
          <div class="backpack-menu-body">
            ${bagEntries.length ? bagEntries.map(([itemName, qty]) => `
              <details class="bag-item-row" data-item-name="${itemName}">
                <summary class="bag-item-summary">
                  <img src="${buildItemSpriteUrl(itemName)}" class="item-sprite" alt="" onerror="this.style.display='none'" />
                  <span class="bag-item-name">${getItemWikiName(itemName)}</span>
                  <span class="bag-item-chevron" aria-hidden="true">▾</span>
                </summary>
                <div class="bag-item-actions">
                <span class="item-qty">x${qty}</span>
                ${pokemonList.length && itemName === "Capsula Habilidad" ? `<select class="ability-capsule-pokemon-select" data-item-name="${itemName}">
                  ${pokemonList.map((poke, idx) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`}</option>`).join("")}
                </select>
                <select class="ability-capsule-select" data-poke-idx="0">
                  ${(pokemonList[0]?.abilities || []).filter((ability) => ability !== pokemonList[0]?.ability).map((ability) => `<option value="${ability}">${ability}</option>`).join("")}
                </select>
                <button class="btn btn-small btn-secondary btn-use-ability-capsule" data-item-name="${itemName}">Usar</button>` : pokemonList.length && itemName.endsWith(" Mint") ? (() => {
                  const mintNature = itemName.slice(0, -5);
                  const canUseMint = pokemonList.some((poke) => poke.nature !== mintNature);
                  return `
                    <select class="mint-pokemon-select" data-item-name="${itemName}">
                      ${pokemonList.map((poke, idx) => `<option value="${idx}" ${poke.nature === mintNature ? "disabled" : ""}>${poke.name || `Pokémon ${idx + 1}`} — ${formatNature(poke.nature)}${poke.nature === mintNature ? " (ya tiene esta naturaleza)" : ""}</option>`).join("")}
                    </select>
                    <button class="btn btn-small btn-secondary btn-use-mint" data-item-name="${itemName}" ${canUseMint ? "" : "disabled"}>Usar</button>
                  `;
                })() : pokemonList.length && itemName === "Cambia Formas" ? (() => {
                  const selectedPoke = pokemonList[0];
                  const formOptions = Array.isArray(selectedPoke?.regional_form_options) ? selectedPoke.regional_form_options : [];
                  return `
                    <select class="form-change-pokemon-select" data-item-name="${itemName}">
                      ${pokemonList.map((poke, idx) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`}</option>`).join("")}
                    </select>
                    <select class="form-change-form-select" data-poke-idx="0">
                      ${formOptions.length ? formOptions.map((option) => `<option value="${option.target_name}">${option.display_name}</option>`).join("") : `<option value="">Sin formas regionales</option>`}
                    </select>
                    <button class="btn btn-small btn-secondary btn-use-form-change" data-item-name="${itemName}">Usar</button>
                  `;
                })() : pokemonList.length && itemName.startsWith("MT ") ? (() => {
                  const moveName = getTmMoveName(itemName);
                  const classified = pokemonList.map((poke, idx) => {
                    const compat = checkTmCompatibility(poke, moveName);
                    return { poke, idx, compat };
                  });

                  classified.sort((a, b) => {
                    const score = (reason) => (reason === "can_learn" ? 0 : reason === "already_learned" ? 1 : 2);
                    const diff = score(a.compat.reason) - score(b.compat.reason);
                    if (diff !== 0) return diff;
                    return a.idx - b.idx;
                  });

                  const hasCompatible = classified.some((c) => c.compat.reason === "can_learn");
                  const firstChoice = classified[0];
                  const initialCompat = hasCompatible
                    ? firstChoice.compat
                    : { reason: "incompatible", label: "❌ Sin compatibles", badgeClass: "badge-danger" };
                  const canUseInitial = hasCompatible && firstChoice.compat.canLearn;
                  const selectStateClass = !hasCompatible
                    ? "is-incompatible"
                    : canUseInitial
                    ? "is-compatible"
                    : firstChoice?.compat?.reason === "already_learned"
                    ? "is-warning"
                    : "is-incompatible";

                  const optionsHtml = classified.map(({ poke, idx, compat }) => {
                    let tag = "❌";
                    let note = "No";
                    if (compat.reason === "can_learn") {
                      tag = "✅";
                      note = "Aprende";
                    } else if (compat.reason === "already_learned") {
                      tag = "⚠️";
                      note = "Ya sabe";
                    }
                    return `<option value="${idx}">${tag} ${poke.name || `Pokémon ${idx + 1}`} (${note})</option>`;
                  }).join("");

                  return `
                    <div class="tm-action-group">
                      <select class="tm-pokemon-select ${selectStateClass}" data-item-name="${itemName}">
                        ${!hasCompatible ? `<option value="" disabled selected>❌ Sin compatibles</option>` : ""}
                        ${optionsHtml}
                      </select>
                      <span class="tm-compat-status badge ${initialCompat.badgeClass}">${initialCompat.label}</span>
                      <button class="btn btn-small btn-secondary btn-use-tm" data-item-name="${itemName}" ${canUseInitial ? "" : "disabled"} title="${canUseInitial ? `Enseñar ${moveName} a ${firstChoice?.poke?.name}` : 'Selecciona un Pokémon compatible'}">Usar</button>
                    </div>
                  `;
                })() : pokemonList.length ? (() => {
                  const eligiblePokes = pokemonList
                    .map((poke, idx) => ({ poke, idx }))
                    .filter(({ poke }) => !isMegaPokemon(poke));
                  if (!eligiblePokes.length) {
                    return `<span class="text-muted" style="font-size:0.75rem; margin-left:6px;">(Sin Pokémon para equipar)</span>`;
                  }
                  return `
                    <select class="bag-item-select" data-item-name="${itemName}">
                      ${eligiblePokes.map(({ poke, idx }) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`}</option>`).join("")}
                    </select>
                    <button class="btn btn-small btn-secondary btn-item-give" data-item-name="${itemName}">Dar</button>
                  `;
                })() : ""}
              </div>
              </details>
            `).join("") : '<p class="text-muted">No tienes items en la mochila.</p>'}
          </div>
        </div>
      </div>

      ${shopVisible ? `
        <div class="inventory-modal-overlay" data-modal="shop-menu" aria-hidden="true">
          <div class="backpack-menu shop-menu" data-menu="shop-menu">
            <div class="backpack-menu-header">
              <h4>🛒 ${shopTitle}</h4>
              <button type="button" class="btn-close-menu" aria-label="Cerrar">✕</button>
            </div>
            <p class="shop-balance">Dinero actual: <strong>$${formatMoneyCompact(myData.money || 0)}</strong></p>
            ${auctionOrEventStage ? '<p class="text-muted">Solo consulta durante la subasta y los eventos. Podrás comprar en la fase de confirmación de Showdown.</p>' : ""}
            <div class="backpack-menu-body shop-items">
              ${orderedShopItems.map((shopItem) => {
                const isBox = isPriorityShopItem(shopItem);
                const tooltipAttr = shopItem.description ? `title="${shopItem.description}"` : '';
                return `
                <div class="shop-item-row ${isBox ? 'shop-item-row--box' : ''}">
                  <span class="shop-item-icon" aria-hidden="true">
                    <img src="${buildItemSpriteUrl(shopItem.name)}" alt="" onerror="this.parentElement.classList.add('is-fallback'); this.remove()" />
                  </span>
                  ${isBox ? `
                    <span class="badge-link shop-box-link" ${tooltipAttr} style="display:inline-flex;align-items:center;gap:4px;">
                      <span>${shopItem.name}</span>
                      <button type="button" class="btn-show-box-odds" data-box-name="${shopItem.name}" title="Ver probabilidades de esta caja">
                        🎰 Ruleta ℹ️
                      </button>
                    </span>
                  ` : `
                    <a href="${buildWikidexUrl(getItemWikiName(shopItem.name))}" target="_blank" rel="noopener noreferrer" class="badge-link shop-item-name">${getItemWikiName(shopItem.name)}</a>
                  `}
                  <span class="shop-item-price">$${formatMoneyCompact(shopItem.price)}</span>
                  ${preparationStage ? `<button class="btn btn-small btn-primary btn-buy-item" data-item-name="${shopItem.name}">Comprar</button>` : ""}
                </div>
              `;
              }).join("")}
            </div>
          </div>
        </div>
      ` : ""}
    </div>
  `;
}

export const BOX_ODDS_DATA = {
  "Ruleta Mentas": {
    title: "Ruleta Mentas",
    price: "$30K",
    note: "Al comprarla, obtienes una Menta aleatoria. Las 25 Mentas tienen la misma probabilidad:",
    items: [
      "Adamant Mint", "Bashful Mint", "Bold Mint", "Brave Mint", "Calm Mint",
      "Careful Mint", "Docile Mint", "Gentle Mint", "Hardy Mint", "Hasty Mint",
      "Impish Mint", "Jolly Mint", "Lax Mint", "Lonely Mint", "Mild Mint",
      "Modest Mint", "Naive Mint", "Naughty Mint", "Quiet Mint", "Quirky Mint",
      "Rash Mint", "Relaxed Mint", "Sassy Mint", "Serious Mint", "Timid Mint",
    ].map((name) => ({ name, rate: "1/25", tier: "common", image: buildItemSpriteUrl(name) }))
  },
  "Ruleta Choice": {
    title: "Ruleta Choice",
    price: "$150K",
    note: "Al comprarla, obtienes uno de estos tres objetos Choice con la misma probabilidad:",
    items: ["Choice Scarf", "Choice Band", "Choice Specs"]
      .map((name) => ({ name, rate: "1/3", tier: "rare", image: buildItemSpriteUrl(name) }))
  },
  "Ruleta MT OP": {
    title: "Ruleta MT OP",
    price: "$100K",
    note: "Al comprarla, obtienes una MT competitiva aleatoria. Todas tienen la misma probabilidad:",
    items: [
      "MT Earthquake", "MT Ice Beam", "MT Flamethrower", "MT Thunderbolt",
      "MT Shadow Ball", "MT Stone Edge", "MT U-turn", "MT Close Combat",
      "MT Energy Ball", "MT Dark Pulse", "MT Sludge Bomb", "MT Knock Off",
    ].map((name) => ({ name, rate: "1/12", tier: "rare", image: buildItemSpriteUrl(name) }))
  },
  "Ruleta Plates": {
    title: "Ruleta Plates",
    price: "$20K",
    note: "Al comprarla, obtienes una Plate aleatoria. Todas tienen la misma probabilidad:",
    items: [
      "Fist Plate", "Sky Plate", "Flame Plate", "Splash Plate", "Zap Plate",
      "Meadow Plate", "Icicle Plate", "Toxic Plate", "Earth Plate", "Mind Plate",
      "Insect Plate", "Stone Plate", "Spooky Plate", "Draco Plate", "Dread Plate",
      "Iron Plate", "Pixie Plate",
    ].map((name) => ({ name, rate: "1/17", tier: "common", image: buildItemSpriteUrl(name) }))
  },
  "Ruleta Piedras": {
    title: "Ruleta Piedras",
    price: "$20K",
    note: "Al comprarla, obtienes una piedra evolutiva aleatoria. Todas tienen la misma probabilidad:",
    items: [
      "Fire Stone", "Water Stone", "Thunder Stone", "Leaf Stone", "Moon Stone",
      "Sun Stone", "Shiny Stone", "Dusk Stone", "Dawn Stone", "Ice Stone",
    ].map((name) => ({ name, rate: "1/10", tier: "common", image: buildItemSpriteUrl(name) }))
  },
  "Caja Misteriosa I": {
    title: "Caja Misteriosa I",
    price: "$100K",
    note: "Al comprarla, la ruleta girará y obtendrás exactamente una de las siguientes recompensas según sus probabilidades:",
    items: [
      { name: "Oran Berry (x1)", rate: "75%", tier: "common", image: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/oran-berry.png" },
      { name: "MT Earthquake", rate: "5%", tier: "rare", image: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/tm-normal.png" },
      { name: "MT Flamethrower", rate: "5%", tier: "rare", image: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/tm-normal.png" },
      { name: "MT Shadow Ball", rate: "5%", tier: "rare", image: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/tm-normal.png" },
      { name: "Cápsula Habilidad", rate: "5%", tier: "rare", image: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/ability-capsule.png" },
      { name: "Porygon (aleatorio) + Objeto Mejora (Up-Grade)", rate: "3%", tier: "epic", image: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/137.png" },
      { name: "$500K en efectivo", rate: "1%", tier: "legendary", image: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/big-nugget.png" },
      { name: "Pokémon Shiny aleatorio (Pool normal)", rate: "1%", tier: "legendary", image: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/shiny-stone.png" },
    ]
  },
  "Regalo del Primo jeque": {
    title: "Regalo del Primo jeque",
    price: "$250K",
    note: "Al comprarla, la ruleta girará entre los 4 Pokémon del jeque (todos Nv. 20, con naturaleza y habilidad aleatorias):",
    items: [
      { name: "Galvantula", rate: "25%", tier: "rare", image: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/596.png" },
      { name: "Scolipede", rate: "25%", tier: "rare", image: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/545.png" },
      { name: "Sawk", rate: "25%", tier: "rare", image: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/539.png" },
      { name: "Gardevoir", rate: "25%", tier: "rare", image: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/282.png" },
    ]
  }
};
BOX_ODDS_DATA["Caja Misteriosa 1"] = BOX_ODDS_DATA["Caja Misteriosa I"];

export function showBoxOddsModal(boxName) {
  const data = BOX_ODDS_DATA[boxName];
  if (!data) return;

  document.querySelectorAll(".box-odds-modal-overlay").forEach((el) => el.remove());

  const overlay = document.createElement("div");
  overlay.className = "box-odds-modal-overlay";
  overlay.innerHTML = `
    <div class="box-odds-modal" role="dialog" aria-modal="true" aria-labelledby="box-odds-title">
      <div class="box-odds-header">
        <h3 id="box-odds-title">🎁 ${data.title} <span style="font-size:0.85rem;color:var(--text-muted);font-weight:normal;">(${data.price})</span></h3>
        <button type="button" class="btn-close-menu btn-close-odds" aria-label="Cerrar">✕</button>
      </div>
      <p class="box-odds-note">${data.note}</p>
      <div class="box-odds-list">
        ${data.items.map((item) => `
          <div class="box-odds-item">
            <div class="box-odds-item-info">
              <img src="${item.image}" alt="${item.name}" onerror="this.style.display='none'" />
              <span>${item.name}</span>
            </div>
            <span class="box-odds-rate box-odds-rate--${item.tier || 'common'}">${item.rate}</span>
          </div>
        `).join("")}
      </div>
      <div class="box-odds-actions">
        <button type="button" class="btn btn-primary btn-small btn-close-odds">Entendido</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  const closeModal = () => {
    overlay.remove();
  };

  overlay.querySelectorAll(".btn-close-odds").forEach((btn) => {
    btn.addEventListener("click", closeModal);
  });
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeModal();
  });
}
