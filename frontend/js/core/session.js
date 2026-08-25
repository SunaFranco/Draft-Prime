/**
 * js/core/session.js — Servicio de red y WebSocket
 */

const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const localApiUrl = "http://localhost:8000";
const defaultApiUrl = isLocalhost ? localApiUrl : window.location.origin;

export const API = window.API_URL || defaultApiUrl;
export const WS_BASE = window.WS_URL || `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${new URL(API).host}`;

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
}
