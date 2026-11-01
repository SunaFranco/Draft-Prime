import { API } from "./session.js";

const ACCESS_TOKEN_KEY = "draft_prime_access_token";
const REFRESH_TOKEN_KEY = "draft_prime_refresh_token";

export class AuthClient {
  constructor() {
    this.accessToken = sessionStorage.getItem(ACCESS_TOKEN_KEY);
    this.refreshToken = sessionStorage.getItem(REFRESH_TOKEN_KEY);
    this.profile = null;
  }

  _storeSession(data) {
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
    this.profile = data.profile || null;
    sessionStorage.setItem(ACCESS_TOKEN_KEY, this.accessToken);
    sessionStorage.setItem(REFRESH_TOKEN_KEY, this.refreshToken);
  }

  _clearSession() {
    this.accessToken = null;
    this.refreshToken = null;
    this.profile = null;
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  }

  async _request(path, { method = "GET", body, authenticated = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (authenticated && this.accessToken) headers.Authorization = `Bearer ${this.accessToken}`;
    const response = await fetch(`${API}/auth${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "No se pudo completar la operación.");
    return data;
  }

  async login(email, password) {
    const data = await this._request("/login", {
      method: "POST",
      body: { email, password },
      authenticated: false,
    });
    this._storeSession(data);
    return this.profile;
  }

  async restore() {
    if (!this.accessToken || !this.refreshToken) return null;
    try {
      const data = await this._request("/me");
      this.profile = data.profile;
      return this.profile;
    } catch {
      try {
        const data = await this._request("/refresh", {
          method: "POST",
          body: { refresh_token: this.refreshToken },
          authenticated: false,
        });
        this._storeSession(data);
        return this.profile;
      } catch {
        this._clearSession();
        return null;
      }
    }
  }

  async changeTemporaryPassword(newPassword) {
    await this._request("/change-password", {
      method: "POST",
      body: { new_password: newPassword },
    });
    if (this.profile) this.profile.must_change_password = false;
  }

  async createAccount(account) {
    const data = await this._request("/admin/accounts", { method: "POST", body: account });
    return data.profile;
  }

  getHistory() { return this._request("/me/history"); }
  getTrophies() { return this._request("/me/trophies"); }

  logout() {
    this._clearSession();
  }
}
