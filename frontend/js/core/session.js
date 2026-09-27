export const API = window.API_URL || (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" ? "http://localhost:8000" : window.location.origin);
export const WS_BASE = window.WS_URL || `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${new URL(API, window.location.origin).host}`;



export class SessionClient {
  constructor() {
    this.ws = null;
    this.currentSessionId = null;
    this.currentUsername = null;
    this.eventListeners = [];
  }

  async createSession(username) {
    const res = await fetch(`${API}/session/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error al crear sesión");
    return data;
  }

  async getSession(sessionId) {
    const res = await fetch(`${API}/session/${sessionId}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error al obtener sesión");
    return data;
  }

  connectWebSocket(sessionId, username, onMessage, onOpen, onClose, onError) {
    this.currentSessionId = sessionId;
    this.currentUsername = username;

    const url = `${WS_BASE}/session/${sessionId}/ws?username=${encodeURIComponent(username)}`;
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

  saveActiveSession(sessionId, username) {
    localStorage.setItem("draft_prime_session_id", sessionId);
    localStorage.setItem("draft_prime_username", username);
  }

  getSavedSession() {
    const sessionId = localStorage.getItem("draft_prime_session_id");
    const username = localStorage.getItem("draft_prime_username");
    if (sessionId && username) {
      return { sessionId, username };
    }
    return null;
  }

  clearSavedSession() {
    localStorage.removeItem("draft_prime_session_id");
    localStorage.removeItem("draft_prime_username");
  }
}
