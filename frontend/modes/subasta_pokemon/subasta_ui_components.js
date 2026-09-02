/**
 * frontend/modes/subasta_pokemon/subasta_ui_components.js - Componentes de renderizado UI para Subasta Pokémon
 */

export function renderConfigForm(containerEl, data, isHost) {
  const defaults = {
    starting_money: 10000,
    turns_per_year: 3,
    pok_per_player: 2,
    buyout_multiplier: 3.0,
    secret_fee: 500,
  };

  containerEl.innerHTML = `
    <div class="subasta-config-panel">
      <div class="form-group">
        <label for="subasta-money">Presupuesto Inicial ($):</label>
        <input type="number" id="subasta-money" value="${defaults.starting_money}" min="1000" max="100000" ${!isHost ? "disabled" : ""} />
      </div>
      <div class="form-group">
        <label for="subasta-turns">Turnos de Eventos por Año:</label>
        <input type="number" id="subasta-turns" value="${defaults.turns_per_year}" min="1" max="10" ${!isHost ? "disabled" : ""} />
      </div>
      <div class="form-group">
        <label for="subasta-pok-player">Pokémon por Subasta:</label>
        <input type="number" id="subasta-pok-player" value="${defaults.pok_per_player}" min="1" max="6" ${!isHost ? "disabled" : ""} />
      </div>
      <div class="form-group">
        <label for="subasta-buyout-mult">Multiplicador Compra Directa:</label>
        <input type="number" step="0.5" id="subasta-buyout-mult" value="${defaults.buyout_multiplier}" min="1.5" max="10" ${!isHost ? "disabled" : ""} />
      </div>
      <div class="form-group">
        <label for="subasta-secret-fee">Tarifa Pokémon Secreto ($):</label>
        <input type="number" id="subasta-secret-fee" value="${defaults.secret_fee}" min="0" max="5000" ${!isHost ? "disabled" : ""} />
      </div>
    </div>
  `;
}

export function readConfigForm(containerEl) {
  return {
    starting_money: parseInt(document.getElementById("subasta-money").value, 10),
    turns_per_year: parseInt(document.getElementById("subasta-turns").value, 10),
    pok_per_player: parseInt(document.getElementById("subasta-pok-player").value, 10),
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
  const revealHoldUntil = Number(auction.reveal_hold_until || 0) * 1000;
  const revealCountdownMs = revealHoldUntil > 0 ? Math.max(0, revealHoldUntil - Date.now()) : 0;
  const revealPercent = revealHoldUntil > 0 ? Math.max(0, Math.min(100, (revealCountdownMs / 5000) * 100)) : 0;
  const isPokemonRevealed = Boolean(
    !auction.awaiting_secret_choice &&
    auction.finished &&
    poke &&
    !poke.is_hidden &&
    poke.name &&
    poke.image_url &&
    (!auction.reveal_hold_until || revealCountdownMs <= 5000)
  );

  let html = `
    <div class="subasta-header">
      <span class="badge badge-primary">📌 Etapa: ${data.stage_name}</span>
      <span class="badge badge-success">💰 Mi Saldo: $${myData.money}</span>
    </div>

    <div class="auction-grid">
      <!-- Tarjeta del Pokémon Subastado -->
      <div class="card auction-poke-card">
        <h3>${isPokemonRevealed ? `🔍 ${poke.name}` : "🔍 Pokémon Incógnito"}</h3>
        <div class="poke-image-wrapper">
          ${isPokemonRevealed
            ? `<img src="${poke.image_url}" alt="${poke.name}" class="poke-thumb" style="max-width: 180px; width: 100%; object-fit: contain;" />`
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
            <li><strong>Habilidad:</strong> ${hints.ability || "🔒 Incógnito (3.0x)"}</li>
            <li><strong>Tipo Primario:</strong> ${hints.primary_type || "🔒 Incógnito (5.0x)"}</li>
            <li><strong>Mejor Stat Base:</strong> ${hints.highest_stat || "🔒 Incógnito (8.0x)"}</li>
          </ul>
        </div>
      </div>

      <!-- Panel de Puja y Estado -->
      <div class="card auction-controls-card">
        <h3>🔥 Estado de la Puja</h3>
        <p class="current-bid-display">Puja Actual: <span>$${auction.current_bid || 0}</span></p>
        <p class="high-bidder-display">Mayor Pujador: <strong>${auction.high_bidder || "Ninguno"}</strong></p>

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
              <button id="btn-fold" class="btn btn-danger" ${isFolded ? "disabled" : ""}>${isFolded ? "Retirado" : "🚪 Retirarse"}</button>
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

  return `
    <div class="card export-card">
      <h2>📋 ${data.stage_name}</h2>
      <p>Copia el siguiente texto para importar tu equipo en <strong>Pokémon Showdown</strong>:</p>

      <textarea id="showdown-text-area" readonly rows="12" class="code-area">${showdownText}</textarea>

      <div class="btn-group">
        <button id="btn-copy-showdown" class="btn btn-success">📋 Copiar al Portapapeles</button>
        ${isHost ? `<button id="btn-next-stage-export" class="btn btn-primary">➡️ Avanzar a la Siguiente Etapa (Host)</button>` : ""}
      </div>
    </div>
  `;
}

export function renderAdminAndStandingsView(data, sessionClient, isHost) {
  const standings = data.standings || [];
  const players = Object.keys(data.all_players || {});

  return `
    <div class="card standings-card">
      <h2>🏆 ${data.stage_name}</h2>
      <hr />

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

      ${isHost ? `
        <div class="admin-match-box">
          <h3>⚖️ Panel de Administrador: Cargar Resultado de Enfrentamiento</h3>
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
          <button id="btn-submit-match" class="btn btn-primary">Registrar Resultado</button>
        </div>
      ` : ""}
    </div>
  `;
}

export function renderMyPokemonInventory(data, sessionClient) {
  const myData = data.my_data || {};
  const pokemonList = myData.pokemon || [];
  const levelCap = data.current_year === 1 ? 20 : (data.current_year === 2 ? 40 : 100);

  if (pokemonList.length === 0) {
    return `
      <div class="card inventory-card">
        <h3>🎒 Mis Pokémon Conseguidos</h3>
        <p class="text-muted">Aún no has conseguido ningún Pokémon en las subastas.</p>
      </div>
    `;
  }

  return `
    <div class="card inventory-card">
      <h3>🎒 Mis Pokémon Conseguidos (Level Cap: Nv. ${levelCap})</h3>
      <div class="inventory-grid">
        ${pokemonList.map((poke, pokeIdx) => {
          const levelUpMoves = (poke.level_up_moves || []).filter((m) => m.level <= levelCap);
          const selectedMoves = poke.selected_moves || [];

          return `
            <div class="poke-inventory-item" data-poke-idx="${pokeIdx}">
              <div class="poke-inv-header">
                ${poke.image_url ? `<img src="${poke.image_url}" class="poke-thumb" />` : ''}
                <div>
                  <span class="badge">Nv. ${poke.level || levelCap}</span>
                  <span class="badge badge-gold">Habilidad: ${poke.ability || 'Desconocida'}</span>
                </div>
              </div>

              <div class="moves-selector-box">
                <h5>⚔️ Selecciona hasta 4 Movimientos (por nivel):</h5>
                <div class="moves-checkboxes">
                  ${levelUpMoves.map((m) => {
                    const isChecked = selectedMoves.includes(m.name) ? 'checked' : '';
                    return `
                      <label class="move-label">
                        <input type="checkbox" class="move-chk-${pokeIdx}" value="${m.name}" ${isChecked} />
                        ${m.name} <small>(Nv. ${m.level})</small>
                      </label>
                    `;
                  }).join("")}
                </div>
                <button class="btn btn-small btn-primary btn-save-moves" data-poke-idx="${pokeIdx}">💾 Guardar 4 Movimientos</button>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    </div>
  `;
}

