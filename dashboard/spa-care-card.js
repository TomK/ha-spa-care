import { LitElement, html, css } from "https://unpkg.com/lit?module";

const PRODUCTS = [
  { value: "brominating_granules", label: "Brominating granules (~60% BCDMH)" },
  { value: "dry_acid", label: "Dry acid (sodium bisulphate)" },
  { value: "ph_up", label: "pH up (sodium carbonate)" },
  { value: "ta_up", label: "TA increaser (sodium bicarbonate)" },
  { value: "ch_up", label: "Calcium hardness increaser (calcium chloride)" },
  { value: "spa_no_scale", label: "Spa No Scale (sequestrant)" },
  { value: "mps_shock", label: "Non-chlorine shock (MPS)" },
  { value: "filter_cleaner", label: "Filter cartridge cleaner" },
  { value: "surface_cleaner", label: "Surface cleaner" },
  { value: "defoamer", label: "Defoamer" },
  { value: "clarifier", label: "Clarifier" },
  { value: "sodium_bromide", label: "Sodium bromide reserve" },
  { value: "bromine_tablets", label: "Bromine tablets (BCDMH 20 g floater)" },
];

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

  static getConfigElement() {
    return document.createElement("spa-care-card-editor");
  }

  static getStubConfig() {
    return { device_id: "" };
  }

  _resolveEntities() {
    const all = Object.values(this.hass.entities || {});
    const mine = all.filter((e) => e.device_id === this._config.device_id);
    // hass.entities is the abbreviated display registry — it has device_id
    // but not unique_id. Match by entity_id suffix instead. Safe because
    // we're already constrained to one device.
    const byKey = (suffix) =>
      mine.find((e) => (e.entity_id || "").endsWith(suffix));
    return {
      tb: byKey("_total_bromine"),
      ph: byKey("_ph"),
      ta: byKey("_total_alkalinity"),
      ch: byKey("_calcium_hardness"),
      tbOOR: byKey("_tb_out_of_range"),
      phOOR: byKey("_ph_out_of_range"),
      taOOR: byKey("_ta_out_of_range"),
      chOOR: byKey("_ch_out_of_range"),
      testDue: byKey("_test_due"),
      recommended: byKey("_recommended_action"),
      nextRetest: byKey("_next_retest_at"),
      logRecommended: byKey("_log_recommended_doses"),
    };
  }

  _device() {
    if (!this._config?.device_id) return null;
    return this.hass.devices?.[this._config.device_id] ?? null;
  }

  _statusText(testDueState) {
    if (!testDueState) return "";
    const reasons = testDueState.attributes?.reasons || [];
    if (testDueState.state !== "on") return "✅ All good";
    const set = new Set(reasons);
    if (set.has("post_dose") && set.has("routine")) {
      return "🔔 Retest pending — also overdue";
    }
    if (set.has("post_dose")) return "⏱ Retest pending";
    if (set.has("routine")) return "🔔 Test overdue (no reading in 5+ days)";
    return "⚠️ Test due";
  }

  _renderReadingRow(label, numEntity, oorEntity, unit) {
    if (!numEntity) return html``;
    const numState = this.hass.states[numEntity.entity_id];
    const oorState = oorEntity ? this.hass.states[oorEntity.entity_id] : null;
    const value = numState?.state;
    const isUnknown = value === undefined || value === "unknown" || value === null;
    let badge = html``;
    if (!isUnknown && oorState) {
      badge = oorState.state === "on"
        ? html`<span class="badge" title="Out of range">⚠️</span>`
        : html`<span class="badge" title="In range">✓</span>`;
    }
    const onChange = (ev) => {
      const newValue = parseFloat(ev.target.value);
      if (Number.isNaN(newValue)) return;
      this.hass.callService("number", "set_value", {
        entity_id: numEntity.entity_id,
        value: newValue,
      });
    };
    return html`
      <div class="row">
        <div class="label">${label}</div>
        <input
          class="input"
          type="number"
          step=${numState?.attributes?.step ?? "any"}
          .value=${isUnknown ? "" : value}
          @change=${onChange}
        />
        ${unit ? html`<span>${unit}</span>` : ""}
        ${badge}
      </div>
    `;
  }

  _renderRecommendations(recommendedEntity) {
    if (!recommendedEntity) return html``;
    const state = this.hass.states[recommendedEntity.entity_id];
    const actions = state?.attributes?.actions || [];
    if (!actions.length) return html``;
    return html`
      <div class="section-title">Recommended</div>
      <ul class="actions">
        ${actions.map((a) => html`<li>${a}</li>`)}
      </ul>
    `;
  }

  _renderPrimaryButton(buttonEntity, recommendedEntity) {
    if (!buttonEntity) return html``;
    const recState = this.hass.states[recommendedEntity?.entity_id];
    const actions = recState?.attributes?.actions || [];
    const disabled = actions.length === 0;
    const onClick = () => {
      this.hass.callService("button", "press", {
        entity_id: buttonEntity.entity_id,
      });
    };
    return html`
      <mwc-button
        class="primary-button"
        raised
        ?disabled=${disabled}
        @click=${onClick}
      >Log Recommended Doses</mwc-button>
    `;
  }

  _renderSecondaryButton() {
    const onClick = () => {
      this._showCustomDose = !this._showCustomDose;
    };
    return html`
      <mwc-button class="secondary-button" @click=${onClick}>
        ${this._showCustomDose ? "Cancel" : "+ Log dose"}
      </mwc-button>
    `;
  }

  _renderCustomDoseForm() {
    if (!this._showCustomDose) return html``;
    const onSubmit = () => {
      const product = this.renderRoot.getElementById("dose-product")?.value;
      const amountRaw = this.renderRoot.getElementById("dose-amount")?.value;
      const amount = parseFloat(amountRaw);
      if (!product || Number.isNaN(amount)) return;
      this.hass.callService("spa_care", "log_dose", { product, amount });
      this._showCustomDose = false;
    };
    return html`
      <div class="custom-dose-form">
        <div class="field">
          <label for="dose-product">Product:</label>
          <select id="dose-product">
            ${PRODUCTS.map(
              (p) => html`<option value=${p.value}>${p.label}</option>`
            )}
          </select>
        </div>
        <div class="field">
          <label for="dose-amount">Amount:</label>
          <input id="dose-amount" type="number" step="any" value="0" />
        </div>
        <mwc-button raised @click=${onSubmit}>Add</mwc-button>
      </div>
    `;
  }

  _renderRetest(nextRetestEntity) {
    if (!nextRetestEntity) return html``;
    const state = this.hass.states[nextRetestEntity.entity_id];
    if (!state || state.state === "unknown" || state.state === "unavailable") {
      return html``;
    }
    const target = new Date(state.state);
    if (Number.isNaN(target.getTime())) return html``;
    const diffMs = target.getTime() - Date.now();
    const sign = diffMs >= 0 ? "in" : "ago";
    const abs = Math.abs(diffMs);
    const hours = Math.floor(abs / 3_600_000);
    const minutes = Math.floor((abs % 3_600_000) / 60_000);
    const text = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
    return html`
      <div class="retest">Retest ${sign}: ${text}</div>
    `;
  }

  render() {
    if (!this.hass || !this._config) {
      return html`<ha-card><div class="error">Loading…</div></ha-card>`;
    }
    const device = this._device();
    if (!device) {
      return html`<ha-card><div class="error">
        Configure a device — open the card config and pick your Spa Care device.
      </div></ha-card>`;
    }
    const entities = this._resolveEntities();
    if (!entities.tb || !entities.recommended || !entities.logRecommended) {
      return html`<ha-card><div class="error">
        Spa Care card is incompatible with this integration version
        (missing expected entities).
      </div></ha-card>`;
    }
    const title = device.name_by_user || device.name || "Spa Care";
    const testDueState = this.hass.states[entities.testDue?.entity_id];
    return html`
      <ha-card>
        <div class="header">${title}</div>
        <div class="status">${this._statusText(testDueState)}</div>
        ${this._renderReadingRow("Total Bromine", entities.tb, entities.tbOOR, "ppm")}
        ${this._renderReadingRow("pH", entities.ph, entities.phOOR, "")}
        ${this._renderReadingRow("Total Alkalinity", entities.ta, entities.taOOR, "ppm")}
        ${this._renderReadingRow("Hardness", entities.ch, entities.chOOR, "ppm")}
        ${this._renderRecommendations(entities.recommended)}
        <div class="button-row">
          ${this._renderPrimaryButton(entities.logRecommended, entities.recommended)}
          ${this._renderSecondaryButton()}
        </div>
        ${this._renderCustomDoseForm()}
        ${this._renderRetest(entities.nextRetest)}
      </ha-card>
    `;
  }
}

customElements.define("spa-care-card", SpaCareCard);


class SpaCareCardEditor extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
  };

  static styles = css`
    .editor {
      display: flex;
      flex-direction: column;
      padding: 12px;
      gap: 12px;
    }
  `;

  setConfig(config) {
    this._config = config || {};
  }

  _deviceChanged(ev) {
    const newConfig = { ...this._config, device_id: ev.detail.value };
    this.dispatchEvent(
      new CustomEvent("config-changed", { detail: { config: newConfig } })
    );
  }

  render() {
    if (!this._config) return html``;
    return html`
      <div class="editor">
        <ha-selector
          .hass=${this.hass}
          .selector=${{ device: { integration: "spa_care" } }}
          .value=${this._config.device_id || ""}
          label="Spa device"
          @value-changed=${this._deviceChanged}
        ></ha-selector>
      </div>
    `;
  }
}

customElements.define("spa-care-card-editor", SpaCareCardEditor);


window.customCards = window.customCards || [];
window.customCards.push({
  type: "spa-care-card",
  name: "Spa Care",
  description: "Workflow card for the Spa Care integration",
});
