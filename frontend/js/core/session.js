export const API = window.API_URL || (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" ? "http://localhost:8000" : window.location.origin);
export const WS_BASE = window.WS_URL || `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${new URL(API, window.location.origin).host}`;



export class SessionClient {
  constructor() {
    this.ws = null;
    this.currentSessionId = null;
    this.currentUsername = null;
    this.eventListeners = [];
    this.accessToken = null;
    this.refreshAuth = null;
  }

  setAccessToken(token, refreshAuth = null) { this.accessToken = token; this.refreshAuth = refreshAuth; }

  async _request(path, { method = "GET", body } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (this.accessToken) headers.Authorization = `Bearer ${this.accessToken}`;
    let response = await fetch(`${API}/session${path}`, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (response.status === 401 && this.refreshAuth) {
      const profile = await this.refreshAuth();
      if (profile && this.accessToken) {
        headers.Authorization = `Bearer ${this.accessToken}`;
        response = await fetch(`${API}/session${path}`, {
          method, headers, body: body === undefined ? undefined : JSON.stringify(body),
        });
      }
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "No se pudo completar la operación.");
    return data;
  }

  createSession(name, maxPlayers = 4) { return this._request("/create", { method: "POST", body: { name, max_players: maxPlayers } }); }

  getSession(sessionId) { return this._request(`/${encodeURIComponent(sessionId)}`); }
  getMyRooms() { return this._request("/mine/rooms"); }
  getPendingInvites() { return this._request("/invites/pending"); }
  invite(sessionId, username) { return this._request(`/${encodeURIComponent(sessionId)}/invites`, { method: "POST", body: { username } }); }
  respondToInvite(inviteId, accept) { return this._request(`/invites/${encodeURIComponent(inviteId)}/respond`, { method: "POST", body: { accept } }); }
  closeRoom(sessionId, forced = false) { return this._request(`/${encodeURIComponent(sessionId)}/${forced ? "force-close" : "finish"}`, { method: "POST" }); }

  async connectWebSocket(sessionId, username, onMessage, onOpen, onClose, onError) {
    this.currentSessionId = sessionId;
    this.currentUsername = username;
    const { ticket } = await this._request(`/${encodeURIComponent(sessionId)}/websocket-ticket`, { method: "POST" });
    const url = `${WS_BASE}/session/${encodeURIComponent(sessionId)}/ws?ticket=${encodeURIComponent(ticket)}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      if (onOpen) onOpen();
    };

    this.ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (onMessage) onMessage(msg);
      } catch (e) {
        console.error("Error al procesar JSON de WS:", e);
      }
    };

    this.ws.onclose = (evt) => {
      if (onClose) onClose(evt);
    };

    this.ws.onerror = (err) => {
      if (onError) onError(err);
    };
  }

  send(payload) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    } else {
      console.warn("Intento de envío con WebSocket cerrado o no inicializado.");
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

}
