/**
 * frontend/modes/subasta_pokemon/subasta_ui_components.js - Componentes de renderizado UI para Subasta Pokémon
 */

function buildWikidexUrl(name) {
  if (!name) return "";
  const formatted = String(name).trim().replace(/\s+/g, "_").replace(/[()]/g, "");
  return `https://www.wikidex.net/wiki/${encodeURI(formatted)}`;
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

function buildItemSpriteUrl(name) {
  const slugOverrides = { "Capsula Habilidad": "ability-capsule" };
  const tmMove = String(name || "").startsWith("MT ") ? String(name).slice(3) : "";
  const slug = slugOverrides[name] || String(name || "").trim().toLowerCase().replace(/\s+/g, "-");
  const itemSlug = tmMove ? "tm-normal" : slug;
  return itemSlug ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/${encodeURIComponent(itemSlug)}.png` : "";
}

function formatMoneyCompact(value) {
  const amount = Number(value) || 0;
  if (amount >= 1000000) {
    return `${(amount / 1000000).toFixed(amount % 1000000 === 0 ? 0 : 1).replace(/\.0$/, '')}M`;
  }
  if (amount >= 1000) {
    return `${Math.round(amount / 1000)}k`;
  }
  return `${amount}`;
}

function getNextBidValue(currentBid) {
  const current = Number(currentBid) || 0;
  return Math.max(5000, Math.ceil((current + 5000) / 5000) * 5000);
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
    starting_money: 10000,
    turns_per_year: 3,
    pok_per_player: 2,
    year_starting_money_1: 10000,
    year_starting_money_2: 5000,
    year_starting_money_3: 7500,
    year1_tier: "normal",
    year2_tier: "normal",
    year3_tier: "legendary",
    buyout_multiplier: 3.0,
    secret_fee: 500,
  };

  const config = data?.mode_config || {};

  containerEl.innerHTML = `
    <div class="subasta-config-panel">
      <div class="form-group">
        <label for="subasta-turns">Turnos de Eventos por Año:</label>
        <input type="number" id="subasta-turns" value="${config.turns_per_year || defaults.turns_per_year}" min="1" max="10" ${!isHost ? "disabled" : ""} />
      </div>
      <div class="form-group">
        <label for="subasta-pok-player">Pokémon por Subasta (por jugador):</label>
        <input type="number" id="subasta-pok-player" value="${config.pok_per_player || defaults.pok_per_player}" min="1" max="6" ${!isHost ? "disabled" : ""} />
      </div>
      <div class="form-group">
        <label for="subasta-year1-money">Dinero inicial Año 1 ($):</label>
        <input type="number" id="subasta-year1-money" value="${config.year_starting_money_1 ?? config.starting_money ?? defaults.year_starting_money_1}" min="0" max="1000000" ${!isHost ? "disabled" : ""} />
      </div>
      <div class="form-group">
        <label for="subasta-year2-money">Dinero inicial Año 2 ($):</label>
        <input type="number" id="subasta-year2-money" value="${config.year_starting_money_2 ?? defaults.year_starting_money_2}" min="0" max="1000000" ${!isHost ? "disabled" : ""} />
      </div>
      <div class="form-group">
        <label for="subasta-year3-money">Dinero inicial Año Final ($):</label>
        <input type="number" id="subasta-year3-money" value="${config.year_starting_money_3 ?? defaults.year_starting_money_3}" min="0" max="1000000" ${!isHost ? "disabled" : ""} />
      </div>
      <div class="form-group">
        <label for="subasta-year1-tier">Tipo de subasta Año 1:</label>
        <select id="subasta-year1-tier" ${!isHost ? "disabled" : ""}>
          <option value="normal" ${((config.year_tiers && config.year_tiers[1]) || config.year1_tier || defaults.year1_tier) === "normal" ? "selected" : ""}>Normal</option>
          <option value="mega" ${((config.year_tiers && config.year_tiers[1]) || config.year1_tier || defaults.year1_tier) === "mega" ? "selected" : ""}>Mega</option>
          <option value="legendary" ${((config.year_tiers && config.year_tiers[1]) || config.year1_tier || defaults.year1_tier) === "legendary" ? "selected" : ""}>Legendario</option>
        </select>
      </div>
      <div class="form-group">
        <label for="subasta-year2-tier">Tipo de subasta Año 2:</label>
        <select id="subasta-year2-tier" ${!isHost ? "disabled" : ""}>
          <option value="normal" ${((config.year_tiers && config.year_tiers[2]) || config.year2_tier || defaults.year2_tier) === "normal" ? "selected" : ""}>Normal</option>
          <option value="mega" ${((config.year_tiers && config.year_tiers[2]) || config.year2_tier || defaults.year2_tier) === "mega" ? "selected" : ""}>Mega</option>
          <option value="legendary" ${((config.year_tiers && config.year_tiers[2]) || config.year2_tier || defaults.year2_tier) === "legendary" ? "selected" : ""}>Legendario</option>
        </select>
      </div>
      <div class="form-group">
        <label for="subasta-year3-tier">Tipo de subasta Año Final:</label>
        <select id="subasta-year3-tier" ${!isHost ? "disabled" : ""}>
          <option value="normal" ${((config.year_tiers && config.year_tiers[3]) || config.year3_tier || defaults.year3_tier) === "normal" ? "selected" : ""}>Normal</option>
          <option value="mega" ${((config.year_tiers && config.year_tiers[3]) || config.year3_tier || defaults.year3_tier) === "mega" ? "selected" : ""}>Mega</option>
          <option value="legendary" ${((config.year_tiers && config.year_tiers[3]) || config.year3_tier || defaults.year3_tier) === "legendary" ? "selected" : ""}>Legendario</option>
        </select>
    </div>
  `;
}

export function readConfigForm(containerEl) {
  return {
    turns_per_year: parseInt(document.getElementById("subasta-turns").value, 10),
    pok_per_player: parseInt(document.getElementById("subasta-pok-player").value, 10),
    year_starting_money_1: parseInt(document.getElementById("subasta-year1-money").value, 10),
    year_starting_money_2: parseInt(document.getElementById("subasta-year2-money").value, 10),
    year_starting_money_3: parseInt(document.getElementById("subasta-year3-money").value, 10),
    year1_tier: document.getElementById("subasta-year1-tier").value,
    year2_tier: document.getElementById("subasta-year2-tier").value,
    year3_tier: document.getElementById("subasta-year3-tier").value,
    starting_money: parseInt(document.getElementById("subasta-year1-money").value, 10),
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
  const revealHoldUntil = Number(auction.reveal_hold_until || 0) * 1000;
  const revealCountdownMs = revealHoldUntil > 0 ? Math.max(0, revealHoldUntil - Date.now()) : 0;
  const revealPercent = revealHoldUntil > 0 ? Math.max(0, Math.min(100, (revealCountdownMs / 5000) * 100)) : 0;
  const isPubliclyRevealed = Boolean(auction.publicly_revealed === true || (auction.finished && !poke.is_hidden && poke.name && poke.image_url));
  const isPokemonRevealed = Boolean(
    !auction.awaiting_secret_choice &&
    auction.finished &&
    poke &&
    poke.name &&
    poke.image_url &&
    (isPubliclyRevealed || (!auction.reveal_hold_until || revealCountdownMs <= 5000))
  );
  const hintAbility = hints.ability && !String(hints.ability).includes("🔒")
    ? `<a href="${buildWikidexUrl(hints.ability)}" target="_blank" rel="noopener noreferrer" class="badge-link">${hints.ability}</a>`
    : hints.ability || "🔒 Incógnito (8.0x)";

  let html = `
    <div class="subasta-header">
      <span class="badge badge-primary">📌 Etapa: ${data.stage_name}</span>
      <span class="badge badge-success">💰 Mi Saldo: $${myData.money}</span>
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
        ${isPokemonRevealed ? `<p class="base-price"><strong>Adjudicado a:</strong> ${auction.winner || "Ninguno"}</p>` : `<p class="base-price">Precio Inicial: <strong>$${formatMoneyCompact(auction.base_price || 5000)}</strong></p>`}

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
            <li><strong>Región:</strong> ${hints.region || "🔒 Incógnito (2.0x)"}</li>
            <li><strong>Mejor Stat Base:</strong> ${hints.highest_stat || "🔒 Incógnito (3.0x)"}</li>
            <li><strong>Tipo Primario:</strong> ${hints.primary_type || "🔒 Incógnito (5.0x)"}</li>
            <li><strong>Habilidad:</strong> ${hintAbility}</li>
          </ul>
        </div>
      </div>

      <!-- Panel de Puja y Estado -->
      <div class="card auction-controls-card">
        <h3>🔥 Estado de la Puja</h3>
        <p class="current-bid-display ${auction.high_bidder === sessionClient.currentUsername ? 'current-bid-display--win' : 'current-bid-display--lose'}">Puja Actual: <span>$${formatMoneyCompact(auction.current_bid || 0)}</span></p>
        <p class="high-bidder-display">Mayor Pujador: <strong class="${auction.high_bidder === sessionClient.currentUsername ? 'high-bidder-display--win' : 'high-bidder-display--lose'}">${auction.high_bidder || "Ninguno"}</strong></p>

        ${isAuctionFinished && !isWinnerPendingSecret ? `
          <div class="secret-choice-modal">
            <h4>🏁 La subasta ya terminó.</h4>
            <p>Ganador: <strong>${auction.winner || "Ninguno"}</strong></p>
            <p>El Pokémon ya fue adjudicado y la ronda está en espera de confirmación del ganador.</p>
          </div>
        ` : isWinnerPendingSecret ? `
          <div class="secret-choice-modal">
            <h4>🎉 ¡Ganaste la subasta de ${poke.name || 'este Pokémon'}!</h4>
            <p>¿Deseas pagar <strong>$${formatMoneyCompact(Math.ceil((auction.current_bid || 0) * 0.1))}</strong> (10% de tu puja) para ocultar a <strong>${poke.name}</strong> a tus rivales?</p>
            <div class="btn-group">
              <button id="btn-secret-yes" class="btn btn-primary">🔒 Pagar $${formatMoneyCompact(Math.ceil((auction.current_bid || 0) * 0.1))} y Ocultar</button>
              <button id="btn-secret-no" class="btn btn-secondary">👁️ Mostrar a todos ($0)</button>
            </div>
          </div>
        ` : `
          <div class="bidding-actions">
            <div class="bid-input-group">
              <input type="number" id="custom-bid-amount" value="${getNextBidValue(auction.current_bid || 0)}" step="5000" min="${getNextBidValue(auction.current_bid || 0)}" />
              <button id="btn-bid-custom" class="btn btn-success" ${isFolded ? "disabled" : ""}>Pujar</button>
            </div>

            <div class="btn-group">
              <button id="btn-buyout" class="btn btn-warning" ${isFolded ? "disabled" : ""}>⚡ Compra Directa ($${formatMoneyCompact(auction.buyout_price || 5000)})</button>
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
  const pokemonList = myData.pokemon || [];
  const natureNames = Object.keys(NATURE_EFFECTS);
  const isNatureChange = turnEvent.type === "nature_change";
  const isItemReward = turnEvent.reward_is_random === true
    && (turnEvent.granted_item || turnEvent.granted_items?.length);

  return `
    <div class="card event-turn-card">
      <h2>🎲 ${data.stage_name} — Turno ${data.current_turn} de ${data.max_turns}</h2>
      <hr />

      <div class="event-details">
        <h3>${turnEvent.title || "Evento de Turno"}</h3>
        <p>${turnEvent.description || "Un evento ha ocurrido en tu trayectoria."}</p>
      </div>

      <div class="turn-action-box">
        ${isResolved ? `
          <p class="text-success">✓ Has resuelto tu evento de este turno. Esperando a los demás jugadores...</p>
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

export function renderExportView(data, sessionClient, isHost, lockedText = null) {
  const showdownText = lockedText !== null ? lockedText : (data.showdown_text || "");
  const isLocked = lockedText !== null;
  const standings = data.standings || [];
  const players = Object.keys(data.all_players || {});
  const isFinalStage = Number(data.stage) === 12;

  return `
    <div class="card export-card">
      <h2>📋 ${data.stage_name}</h2>
      <p>${isLocked
        ? "Tu equipo ha sido fijado. Copia el texto para importarlo en <strong>Pokémon Showdown</strong>:"
        : "Edita si lo necesitas y luego fija tu equipo para poder copiarlo a <strong>Pokémon Showdown</strong>:"
      }</p>

      <textarea id="showdown-text-area" rows="12" class="code-area" ${isLocked ? "readonly" : ""}>${showdownText}</textarea>

      <div class="btn-group">
        ${isLocked
          ? `<button id="btn-copy-showdown" class="btn btn-success">📋 Copiar al Portapapeles</button>`
          : `<button id="btn-lock-team" class="btn btn-primary">🔒 Fijar Equipo</button>`
        }
      </div>

      ${isHost ? `
        <div class="admin-match-box">
          <h3>⚖️ Registrar resultados de esta fase</h3>
          <div class="form-group">
            <label>Ganador (+3 pts):</label>
            <select id="admin-match-winner">
              ${players.map((p) => `<option value="${p}">${p}</option>`).join("")}
            </select>
          </div>
          <div class="form-group">
            <label>Perdedor (+1 pt):</label>
            <select id="admin-match-loser">
              ${players.map((p) => `<option value="${p}">${p}</option>`).join("")}
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

export function renderMyPokemonInventory(data, sessionClient) {
  const myData = data.my_data || {};
  const pokemonList = myData.pokemon || [];
  const bagItems = normalizeItemMap(myData.items || {});
  const bagEntries = Object.entries(bagItems);
  const currentUsername = sessionClient.currentUsername;
  const tradeSession = data.trade_session;
  const preparationStage = [4, 8, 12, 13].includes(Number(data.stage || 0));
  const tradeTargets = Object.keys(data.all_players || {}).filter((username) => username !== currentUsername);
  const levelCap = data.current_year === 1 ? 20 : (data.current_year === 2 ? 40 : 100);
  const shopOpen = [4, 8, 12, 13].includes(Number(data.stage || 0));
  const shopCatalogByYear = {
    1: [
      { name: "Eviolite", price: 100000 },
      { name: "Sitrus Berry", price: 50000 },
      { name: "MT Fire Punch", price: 30000 },
      { name: "MT Thunder Punch", price: 30000 },
      { name: "MT Ice Punch", price: 30000 },
      { name: "Capsula Habilidad", price: 150000 },
      { name: "Silk Scarf", price: 50000 },
      { name: "Water Stone", price: 100000 },
      { name: "Fire Stone", price: 100000 },
      { name: "Leaf Stone", price: 100000 },
    ],
    2: [
      { name: "Leftovers", price: 1200 },
      { name: "Life Orb", price: 1800 },
      { name: "Choice Band", price: 2000 },
      { name: "Choice Specs", price: 2000 },
      { name: "Choice Scarf", price: 2000 },
      { name: "Rocky Helmet", price: 1400 },
      { name: "Heavy-Duty Boots", price: 1600 },
      { name: "Focus Sash", price: 1700 },
      { name: "Assault Vest", price: 1800 },
      { name: "Capsula Habilidad", price: 2500 },
      { name: "MT Earthquake", price: 2000 },
      { name: "MT Ice Beam", price: 2000 },
      { name: "MT Flamethrower", price: 2000 },
      { name: "MT Thunderbolt", price: 2000 },
      { name: "MT Psychic", price: 2000 },
      { name: "MT Shadow Ball", price: 2000 },
      { name: "MT Protect", price: 1500 },
      { name: "MT Substitute", price: 2000 },
      { name: "MT Swords Dance", price: 2000 },
      { name: "MT Calm Mind", price: 2000 },
    ],
    3: [
      { name: "Leftovers", price: 1200 },
      { name: "Life Orb", price: 1800 },
      { name: "Choice Band", price: 2000 },
      { name: "Choice Specs", price: 2000 },
      { name: "Choice Scarf", price: 2000 },
      { name: "Rocky Helmet", price: 1400 },
      { name: "Heavy-Duty Boots", price: 1600 },
      { name: "Focus Sash", price: 1700 },
      { name: "Assault Vest", price: 1800 },
      { name: "Eviolite", price: 100000 },
      { name: "Sitrus Berry", price: 50000 },
      { name: "Capsula Habilidad", price: 150000 },
      { name: "Water Stone", price: 100000 },
      { name: "Fire Stone", price: 100000 },
      { name: "Leaf Stone", price: 100000 },
      { name: "Thunder Stone", price: 2000 },
      { name: "Moon Stone", price: 2000 },
      { name: "Sun Stone", price: 2000 },
      { name: "Shiny Stone", price: 2000 },
      { name: "Dusk Stone", price: 2000 },
      { name: "Dawn Stone", price: 2000 },
      { name: "Ice Stone", price: 2000 },
      { name: "MT Earthquake", price: 2000 },
      { name: "MT Ice Beam", price: 2000 },
      { name: "MT Flamethrower", price: 2000 },
      { name: "MT Thunderbolt", price: 2000 },
      { name: "MT Psychic", price: 2000 },
      { name: "MT Shadow Ball", price: 2000 },
      { name: "MT Protect", price: 1500 },
      { name: "MT Substitute", price: 2000 },
      { name: "MT Swords Dance", price: 2000 },
      { name: "MT Calm Mind", price: 2000 },
    ],
  };
  const currentYear = Number(data.current_year || 1);
  const currentShopItems = shopCatalogByYear[currentYear] || shopCatalogByYear[1];
  const shopTitle = currentYear === 1 ? "Tienda Año 1" : currentYear === 2 ? "Tienda Año 2" : "Tienda Final";

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
            ${tradeSession.initiator === currentUsername ? '<button class="btn btn-small btn-danger" id="btn-cancel-trade">Rechazar intercambio</button>' : ''}
            <p>${Object.keys(tradeSession.confirms || {}).length}/2 confirmaciones</p>
          ` : tradeSession.target === currentUsername ? `
            <p>Elige uno de tus Pokémon para ofrecerlo:</p>
            <select id="trade-target-pokemon">
              ${(pokemonList || []).map((poke, idx) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`}</option>`).join("")}
            </select>
            <button class="btn btn-small btn-primary" id="btn-select-trade-pokemon">Elegir Pokémon</button>
          ` : '<p>Esperando a que el otro jugador elija su Pokémon.</p>'}
        </div>
      ` : ""}
      ${tradeSession && tradeSession.status === 'completed' && (tradeSession.initiator === currentUsername || tradeSession.target === currentUsername) ? '<div class="trade-panel"><strong>Intercambio realizado.</strong> Los dos Pokémon han cambiado de entrenador.</div>' : ""}
      <div class="inventory-grid">
        ${pokemonList.length ? pokemonList.map((poke, pokeIdx) => {
          const levelUpMoves = (poke.level_up_moves || []).filter((m) => m.level <= levelCap);
          const selectedMoves = poke.selected_moves || [];
          const requiredMoves = Math.min(4, levelUpMoves.length);
          const isSaved = selectedMoves.length >= requiredMoves;
          const itemName = poke.item || poke.held_item || 'Sin ítem';
          const abilityName = poke.ability || 'Desconocida';
          const natureName = formatNature(poke.nature);
          const normalizeWikidexName = (name) => encodeURI(String(name).trim().replace(/\s+/g, "_").replace(/[()]/g, ""));
          const abilityHtml = abilityName !== 'Desconocida'
            ? `<a href="https://www.wikidex.net/wiki/${normalizeWikidexName(abilityName)}" target="_blank" rel="noopener noreferrer" class="badge-link">${abilityName}</a>`
            : abilityName;
          const itemHtml = itemName && itemName !== 'Sin ítem' && itemName !== 'Sin item'
            ? `<a href="https://www.wikidex.net/wiki/${normalizeWikidexName(itemName)}" target="_blank" rel="noopener noreferrer" class="badge-link">${itemName}</a>`
            : itemName;
          const evolutionOptions = Array.isArray(poke.evolution_options) && poke.evolution_options.length > 0
            ? poke.evolution_options
            : (poke.evolution_target ? [{ target: poke.evolution_target, item: poke.evolution_item, level: poke.next_evolution_level, trade: poke.evolution_trade }] : []);

          const validEvolutionOptions = evolutionOptions.filter((opt) => {
            const optItem = opt.item || '';
            const hasOptItem = optItem && (bagItems[optItem] || 0) > 0;
            const currentYear = Number(data.current_year || 1);
            if (optItem && !hasOptItem) return false;
            if (opt.trade && !poke.received_by_trade) return false;
            if (currentYear === 1 && !optItem) return false;
            const optLevel = Number(opt.level ?? 0);
            if (optLevel > 0) return poke.level >= optLevel;
            return optItem || opt.trade || poke.level >= (currentYear === 2 ? 40 : 100);
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
                      const reqText = optItem ? ` (${optItem})` : '';
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
            <div class="poke-inventory-item" data-poke-idx="${pokeIdx}">
              <div class="poke-inv-header">
                ${poke.image_url && poke.name
                  ? `<a href="${buildWikidexUrl(poke.name)}" target="_blank" rel="noopener noreferrer"><img src="${poke.image_url}" class="poke-thumb" alt="${poke.name}" /></a>`
                  : (poke.image_url ? `<img src="${poke.image_url}" class="poke-thumb" />` : '')}
                <div>
                  <span class="badge">Nv. ${poke.level || levelCap}</span>
                  ${poke.is_shiny ? '<span class="badge badge-shiny">✨ SHINY</span>' : ''}
                  <span class="badge badge-green">Habilidad: ${abilityHtml}</span>
                  <span class="badge">Naturaleza: ${natureName}</span>
                </div>
              </div>

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

              ${evolutionHtml}

              <div class="moves-selector-box ${isSaved ? 'moves-saved' : ''}" data-poke-idx="${pokeIdx}">
                <div class="moves-summary-panel">
                  <h5>Movimientos:</h5>
                  <div class="saved-moves-list">
                    ${selectedMoves.map((moveName) => {
                      const wikidexMoveName = encodeURI(String(moveName).trim().replace(/\s+/g, "_").replace(/[()]/g, ""));
                      return `<a href="https://www.wikidex.net/wiki/${wikidexMoveName}" target="_blank" rel="noopener noreferrer" class="move-pill move-pill--link">${moveName}</a>`;
                    }).join("")}
                  </div>
                  <button class="btn btn-small btn-secondary btn-modify-moves" data-poke-idx="${pokeIdx}">✏️ Modificar movimientos</button>
                </div>

                <div class="moves-editor-panel">
                  <h5>Selecciona hasta 4 Movimientos:</h5>
                  <div class="moves-checkboxes">
                    ${levelUpMoves.map((m) => {
                      const isChecked = selectedMoves.includes(m.name) ? 'checked' : '';
                      const moveUrl = buildWikidexUrl(m.name);
                      const moveSourceLabel = m.source === "tm" || m.level === 0 ? "(MT)" : `(Nv. ${m.level})`;
                      return `
                        <label class="move-label">
                          <input type="checkbox" class="move-chk-${pokeIdx}" value="${m.name}" ${isChecked} />
                          <a href="${moveUrl}" target="_blank" rel="noopener noreferrer" class="move-link">${m.name}</a>
                          <small>${moveSourceLabel}</small>
                        </label>
                      `;
                    }).join("")}
                  </div>
                  <button class="btn btn-small btn-primary btn-save-moves" data-poke-idx="${pokeIdx}">💾 Guardar</button>
                </div>
              </div>
            </div>
          `;
        }).join("") : '<p class="text-muted">Aún no has conseguido ningún Pokémon en las subastas.</p>'}
      </div>

      <div class="inventory-actions">
        <div class="backpack-panel">
          <button type="button" class="btn btn-secondary inventory-menu-toggle" data-menu-target="backpack-menu" aria-expanded="false">🎒 Mochila</button>
          <div class="backpack-menu" data-menu="backpack-menu">
          <h4>Mochila</h4>
          ${bagEntries.length ? bagEntries.map(([itemName, qty]) => `
            <div class="bag-item-row">
              <img src="${buildItemSpriteUrl(itemName)}" class="item-sprite" alt="" onerror="this.style.display='none'" />
              <a href="${buildWikidexUrl(getItemWikiName(itemName))}" target="_blank" rel="noopener noreferrer" class="badge-link">${getItemWikiName(itemName)}</a>
              <span class="item-qty">x${qty}</span>
              ${pokemonList.length && itemName === "Capsula Habilidad" ? `<select class="ability-capsule-pokemon-select" data-item-name="${itemName}">
                ${pokemonList.map((poke, idx) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`}</option>`).join("")}
              </select>
              <select class="ability-capsule-select" data-poke-idx="0">
                ${(pokemonList[0]?.abilities || []).filter((ability) => ability !== pokemonList[0]?.ability).map((ability) => `<option value="${ability}">${ability}</option>`).join("")}
              </select>
              <button class="btn btn-small btn-secondary btn-use-ability-capsule" data-item-name="${itemName}">Usar</button>` : pokemonList.length && itemName.startsWith("MT ") ? `<select class="tm-pokemon-select" data-item-name="${itemName}">
                ${pokemonList.map((poke, idx) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`}</option>`).join("")}
              </select>
              <button class="btn btn-small btn-secondary btn-use-tm" data-item-name="${itemName}">Usar</button>` : pokemonList.length ? `<select class="bag-item-select" data-item-name="${itemName}">
                ${pokemonList.map((poke, idx) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`}</option>`).join("")}
              </select>
              <button class="btn btn-small btn-secondary btn-item-give" data-item-name="${itemName}">Dar</button>` : ""}
            </div>
          `).join("") : '<p class="text-muted">No tienes items en la mochila.</p>'}

          </div>
        </div>

        ${shopOpen ? `
          <div class="backpack-panel">
            <button type="button" class="btn btn-secondary inventory-menu-toggle" data-menu-target="shop-menu" aria-expanded="false">🛒 Tienda</button>
            <div class="backpack-menu shop-menu" data-menu="shop-menu">
              <h4>${shopTitle}</h4>
              <p class="shop-balance">Dinero actual: <strong>$${formatMoneyCompact(myData.money || 0)}</strong></p>
              <div class="shop-items">
                ${currentShopItems.map((shopItem) => `
                  <div class="shop-item-row">
                    <img src="${buildItemSpriteUrl(shopItem.name)}" class="item-sprite" alt="" onerror="this.style.display='none'" />
                    <a href="${buildWikidexUrl(getItemWikiName(shopItem.name))}" target="_blank" rel="noopener noreferrer" class="badge-link">${getItemWikiName(shopItem.name)}</a>
                    <span>$${formatMoneyCompact(shopItem.price)}</span>
                    <button class="btn btn-small btn-primary btn-buy-item" data-item-name="${shopItem.name}">Comprar</button>
                  </div>
                `).join("")}
              </div>
            </div>
          </div>
        ` : ""}
        </div>
    </div>
  `;
}

