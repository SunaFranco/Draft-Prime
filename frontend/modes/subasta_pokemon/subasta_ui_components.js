/**
 * frontend/modes/subasta_pokemon/subasta_ui_components.js - Componentes de renderizado UI para Subasta Pokémon
 */

function buildWikidexUrl(name) {
  if (!name) return "";
  const formatted = String(name).trim().replace(/\s+/g, "_").replace(/[()]/g, "");
  return `https://www.wikidex.net/wiki/${encodeURI(formatted)}`;
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
  const slug = String(name || "").trim().toLowerCase().replace(/\s+/g, "-");
  return slug ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/${encodeURIComponent(slug)}.png` : "";
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
      <div class="form-group">
        <label for="subasta-buyout-mult">Multiplicador Compra Directa:</label>
        <input type="number" step="0.5" id="subasta-buyout-mult" value="${config.buyout_multiplier || defaults.buyout_multiplier}" min="1.5" max="10" ${!isHost ? "disabled" : ""} />
      </div>
      <div class="form-group">
        <label for="subasta-secret-fee">Tarifa Pokémon Secreto ($):</label>
        <input type="number" id="subasta-secret-fee" value="${config.secret_fee || defaults.secret_fee}" min="0" max="5000" ${!isHost ? "disabled" : ""} />
      </div>
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
    buyout_multiplier: parseFloat(document.getElementById("subasta-buyout-mult").value),
    secret_fee: parseInt(document.getElementById("subasta-secret-fee").value, 10),
  };
}

export function renderAuctionView(data, sessionClient, isHost) {
  const auction = data.current_auction || {};
  const myData = data.my_data || { money: 0 };
  const hints = auction.hints || {};
  const poke = auction.pokemon || {};

  const isAuctionFinished = Boolean(auction.finished);
  const isWinnerPendingSecret = auction.awaiting_secret_choice && auction.winner === sessionClient.currentUsername;
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
    : hints.ability || "🔒 Incógnito (3.0x)";

  let html = `
    <div class="subasta-header">
      <span class="badge badge-primary">📌 Etapa: ${data.stage_name}</span>
      <span class="badge badge-success">💰 Mi Saldo: $${myData.money}</span>
    </div>

    <div class="auction-grid">
      <!-- Tarjeta del Pokémon Subastado -->
      <div class="card auction-poke-card">
        <h3>${isPokemonRevealed ? `🔍 ${poke.name}` : "🔍 Pokémon Incógnito"}</h3>
        <div class="poke-image-wrapper ${isPokemonRevealed ? 'poke-image-wrapper--revealed' : ''}">
          ${isPokemonRevealed
            ? `<img src="${poke.image_url}" alt="${poke.name}" class="poke-thumb poke-thumb--revealed" />`
            : `<div class="poke-unknown-avatar">❓</div>`}
        </div>
        ${isPokemonRevealed ? `<p class="base-price"><strong>Adjudicado a:</strong> ${auction.winner || "Ninguno"}</p>` : `<p class="base-price">Precio Inicial: <strong>$${auction.base_price || 1000}</strong></p>`}

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
            <li><strong>Letra Inicial:</strong> ${hints.first_letter}</li>
            <li><strong>Región:</strong> ${hints.region || "🔒 Incógnito (2.0x)"}</li>
            <li><strong>Habilidad:</strong> ${hintAbility}</li>
            <li><strong>Tipo Primario:</strong> ${hints.primary_type || "🔒 Incógnito (5.0x)"}</li>
            <li><strong>Mejor Stat Base:</strong> ${hints.highest_stat || "🔒 Incógnito (8.0x)"}</li>
          </ul>
        </div>
      </div>

      <!-- Panel de Puja y Estado -->
      <div class="card auction-controls-card">
        <h3>🔥 Estado de la Puja</h3>
        <p class="current-bid-display ${auction.high_bidder === sessionClient.currentUsername ? 'current-bid-display--win' : 'current-bid-display--lose'}">Puja Actual: <span>$${auction.current_bid || 0}</span></p>
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
            <p>¿Deseas pagar <strong>$${auction.secret_fee}</strong> para ocultar a <strong>${poke.name}</strong> a tus rivales?</p>
            <div class="btn-group">
              <button id="btn-secret-yes" class="btn btn-primary">🔒 Pagar $${auction.secret_fee} y Ocultar</button>
              <button id="btn-secret-no" class="btn btn-secondary">👁️ Mostrar a todos ($0)</button>
            </div>
          </div>
        ` : `
          <div class="bidding-actions">
            <div class="bid-input-group">
              <input type="number" id="custom-bid-amount" value="${(auction.current_bid || 1000) + 500}" step="100" min="${(auction.current_bid || 1000) + 100}" />
              <button id="btn-bid-custom" class="btn btn-success" ${isFolded ? "disabled" : ""}>Pujar</button>
            </div>

            <div class="btn-group">
              <button id="btn-buyout" class="btn btn-warning" ${isFolded ? "disabled" : ""}>⚡ Compra Directa ($${auction.buyout_price || 3000})</button>
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

export function renderExportView(data, sessionClient, isHost) {
  const showdownText = data.showdown_text || "";
  const standings = data.standings || [];
  const players = Object.keys(data.all_players || {});
  const isFinalStage = Number(data.stage) === 12;

  return `
    <div class="card export-card">
      <h2>📋 ${data.stage_name}</h2>
      <p>Copia el siguiente texto para importar tu equipo en <strong>Pokémon Showdown</strong>:</p>

      <textarea id="showdown-text-area" readonly rows="12" class="code-area">${showdownText}</textarea>

      <div class="btn-group">
        <button id="btn-copy-showdown" class="btn btn-success">📋 Copiar al Portapapeles</button>
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
  const shopItems = [
    { name: "Leftovers", price: 1200 },
    { name: "Life Orb", price: 1800 },
    { name: "Choice Band", price: 2000 },
    { name: "Choice Specs", price: 2000 },
    { name: "Choice Scarf", price: 2000 },
    { name: "Eviolite", price: 1500 },
    { name: "Rocky Helmet", price: 1400 },
    { name: "Fire Stone", price: 2000 },
    { name: "Water Stone", price: 2000 },
    { name: "Thunder Stone", price: 2000 },
    { name: "Leaf Stone", price: 2000 },
    { name: "Moon Stone", price: 2000 },
    { name: "Sun Stone", price: 2000 },
    { name: "Shiny Stone", price: 2000 },
    { name: "Dusk Stone", price: 2000 },
    { name: "Dawn Stone", price: 2000 },
    { name: "Ice Stone", price: 2000 },
  ];

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
          const normalizeWikidexName = (name) => encodeURI(String(name).trim().replace(/\s+/g, "_").replace(/[()]/g, ""));
          const abilityHtml = abilityName !== 'Desconocida'
            ? `<a href="https://www.wikidex.net/wiki/${normalizeWikidexName(abilityName)}" target="_blank" rel="noopener noreferrer" class="badge-link">${abilityName}</a>`
            : abilityName;
          const itemHtml = itemName && itemName !== 'Sin ítem' && itemName !== 'Sin item'
            ? `<a href="https://www.wikidex.net/wiki/${normalizeWikidexName(itemName)}" target="_blank" rel="noopener noreferrer" class="badge-link">${itemName}</a>`
            : itemName;
          const nextEvolutionLevel = Number(poke.next_evolution_level ?? 0);
          const evolutionItem = poke.evolution_item || '';
          const hasEvolutionItem = evolutionItem && (bagItems[evolutionItem] || 0) > 0;
          const canEvolve = (() => {
            const currentYear = Number(data.current_year || 1);
            const evolutionAllowed = Boolean(poke.can_evolve || poke.evolution_target);
            if (!evolutionAllowed) return false;

            if (evolutionItem && !hasEvolutionItem) return false;
            if (poke.evolution_trade && !poke.received_by_trade) return false;
            if (currentYear === 1 && !evolutionItem) return false;
            if (nextEvolutionLevel > 0) return poke.level >= nextEvolutionLevel;
            return evolutionItem || poke.evolution_trade || poke.level >= (currentYear === 2 ? 40 : 100);
          })();
          const evolutionButtonContent = evolutionItem
            ? `<img src="${buildItemSpriteUrl(evolutionItem)}" alt="${evolutionItem}" /> Evolucionar`
            : '✨ Evolucionar';

          return `
            <div class="poke-inventory-item" data-poke-idx="${pokeIdx}">
              <div class="poke-inv-header">
                ${poke.image_url && poke.name
                  ? `<a href="${buildWikidexUrl(poke.name)}" target="_blank" rel="noopener noreferrer"><img src="${poke.image_url}" class="poke-thumb" alt="${poke.name}" /></a>`
                  : (poke.image_url ? `<img src="${poke.image_url}" class="poke-thumb" />` : '')}
                <div>
                  <span class="badge">Nv. ${poke.level || levelCap}</span>
                  <span class="badge badge-green">Habilidad: ${abilityHtml}</span>
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

              ${canEvolve ? `<button class="btn btn-small btn-primary btn-evolve-pokemon" data-poke-idx="${pokeIdx}" title="Evolucionar con ${evolutionItem || 'nivel'}">${evolutionButtonContent}</button>` : ""}

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
                      return `
                        <label class="move-label">
                          <input type="checkbox" class="move-chk-${pokeIdx}" value="${m.name}" ${isChecked} />
                          <a href="${moveUrl}" target="_blank" rel="noopener noreferrer" class="move-link">${m.name}</a>
                          <small>(Nv. ${m.level})</small>
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

      <div class="backpack-panel">
        <button type="button" class="btn btn-secondary backpack-toggle" aria-expanded="false">🎒 Mochila</button>
        <div class="backpack-menu">
          <h4>Mochila</h4>
          ${bagEntries.length ? bagEntries.map(([itemName, qty]) => `
            <div class="bag-item-row">
              <img src="${buildItemSpriteUrl(itemName)}" class="item-sprite" alt="" onerror="this.style.display='none'" />
              <a href="${buildWikidexUrl(itemName)}" target="_blank" rel="noopener noreferrer" class="badge-link">${itemName}</a>
              <span class="item-qty">x${qty}</span>
              ${pokemonList.length ? `<select class="bag-item-select" data-item-name="${itemName}">
                ${pokemonList.map((poke, idx) => `<option value="${idx}">${poke.name || `Pokémon ${idx + 1}`}</option>`).join("")}
              </select>
              <button class="btn btn-small btn-secondary btn-item-give" data-item-name="${itemName}">Dar</button>` : ""}
            </div>
          `).join("") : '<p class="text-muted">No tienes items en la mochila.</p>'}

          ${shopOpen ? `
            <div class="shop-panel">
              <h4>Tienda</h4>
              <div class="shop-items">
                ${shopItems.map((shopItem) => `
                  <div class="shop-item-row">
                    <img src="${buildItemSpriteUrl(shopItem.name)}" class="item-sprite" alt="" onerror="this.style.display='none'" />
                    <a href="${buildWikidexUrl(shopItem.name)}" target="_blank" rel="noopener noreferrer" class="badge-link">${shopItem.name}</a>
                    <span>$${shopItem.price}</span>
                    <button class="btn btn-small btn-primary btn-buy-item" data-item-name="${shopItem.name}">Comprar</button>
                  </div>
                `).join("")}
              </div>
            </div>
          ` : ""}
        </div>
      </div>
    </div>
  `;
}

