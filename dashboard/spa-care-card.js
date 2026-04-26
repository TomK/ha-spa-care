import { LitElement, html, css } from "https://unpkg.com/lit?module";

class SpaCareCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
    _showCustomDose: { state: true },
  };

  static styles = css`
    ha-card {
      padding: 16px;
    }
    .header {
      font-size: 1.25rem;
      font-weight: 500;
      margin-bottom: 4px;
    }
    .status {
      color: var(--secondary-text-color);
      margin-bottom: 16px;
    }
    .row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 6px 0;
    }
    .row .label { flex: 1; }
    .row .input { width: 90px; }
    .row .badge { width: 24px; text-align: center; }
    .section-title {
      margin-top: 16px;
      font-weight: 500;
      color: var(--secondary-text-color);
    }
    .actions {
      margin: 8px 0;
      padding-left: 20px;
    }
    .button-row {
      display: flex;
      gap: 8px;
      margin-top: 12px;
      align-items: center;
    }
    .primary-button {
      flex: 1;
    }
    .secondary-button {
      flex: 0 0 auto;
    }
    .custom-dose-form {
      margin-top: 12px;
      padding: 12px;
      background: var(--secondary-background-color);
      border-radius: 8px;
    }
    .custom-dose-form .field {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }
    .retest {
      margin-top: 16px;
      color: var(--secondary-text-color);
    }
    .error {
      color: var(--error-color);
      padding: 16px;
    }
  `;

  setConfig(config) {
    if (!config || !config.device_id) {
      throw new Error("device_id is required");
    }
    this._config = config;
    this._showCustomDose = false;
  }

  getCardSize() {
    return 6;
  }

  render() {
    if (!this.hass || !this._config) {
      return html`<ha-card><div class="error">Loading…</div></ha-card>`;
    }
    return html`
      <ha-card>
        <div class="header">Spa Care</div>
        <div class="status">device_id: ${this._config.device_id}</div>
      </ha-card>
    `;
  }
}

customElements.define("spa-care-card", SpaCareCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "spa-care-card",
  name: "Spa Care",
  description: "Workflow card for the Spa Care integration",
});
