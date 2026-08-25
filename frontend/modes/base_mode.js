/**
 * modes/base_mode.js — Contrato/Interfaz base para los modos de juego en el frontend
 */

export class BaseGameModeUI {
  constructor(key, name) {
    this.key = key;
    this.name = name;
  }

  /**
   * Renderiza el formulario de configuración dinámico en #mode-config-fields.
   */
  renderConfigFields(containerEl, data, isHost) {
    containerEl.innerHTML = "";
  }

  /**
   * Lee y retorna los datos ingresados en el formulario de configuración.
   */
  readConfigFields(containerEl) {
    return {};
  }

  /**
   * Maneja eventos de WebSocket específicos de este modo de juego.
   */
  handleEvent(event, data, context) {
    return false;
  }

  /**
   * Limpia o resetea el estado local de UI del modo.
   */
  resetState() {}
}
