/**
 * Livebox Monitor Card — Lovelace Custom Card pour Home Assistant
 * Affiche le dashboard complet de surveillance réseau Livebox.
 */

const CARD_VERSION = "1.0.0";

const DEVICE_ICONS = {
  computer: "mdi:desktop-classic",
  laptop: "mdi:laptop",
  phone: "mdi:cellphone",
  tablet: "mdi:tablet",
  tv: "mdi:television",
  game: "mdi:gamepad-variant",
  router: "mdi:router-network",
  server: "mdi:server",
  camera: "mdi:cctv",
  car: "mdi:car-connected",
  printer: "mdi:printer",
  default: "mdi:help-network",
};

class LiveboxMonitorCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._filter = "all";
    this._search = "";
    this._activeTab = "devices";
    this._logs = [];
  }

  setConfig(config) {
    this._config = {
      title: "Livebox Monitor",
      scan_interval: 30,
      show_unknown_alert: true,
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 8;
  }

  // ── Données depuis HA ──────────────────────────────────────────────

  _getDevices() {
    if (!this._hass) return [];
    const trackers = Object.values(this._hass.states).filter(
      (s) => s.entity_id.startsWith("device_tracker.") && s.attributes.mac
    );
    return trackers.map((s) => ({
      entity_id: s.entity_id,
      name: s.attributes.friendly_name || s.entity_id,
      mac: s.attributes.mac || "",
      ip: s.attributes.ip_address || "",
      active: s.state === "home",
      link_type: s.attributes.link_type || "",
      vendor: s.attributes.vendor || "",
      blocked: s.attributes.blocked || false,
      rssi: s.attributes.rssi,
      last_seen: s.last_updated,
      first_seen: s.attributes.first_seen || "",
    }));
  }

  _getSensor(suffix) {
    if (!this._hass) return null;
    const eid = Object.keys(this._hass.states).find(
      (e) => e.startsWith("sensor.livebox_") && e.includes(suffix)
    );
    return eid ? this._hass.states[eid] : null;
  }

  _getOnlineCount() {
    const s = this._getSensor("connect");
    return s ? parseInt(s.state) : this._getDevices().filter((d) => d.active).length;
  }

  _getWanStatus() {
    const s = this._getSensor("wan");
    return s ? s.state : "unknown";
  }

  // ── Rendu HTML ─────────────────────────────────────────────────────

  _render() {
    const devices = this._getDevices();
    const filtered = this._filterDevices(devices);
    const onlineCount = this._getOnlineCount();
    const unknownCount = devices.filter((d) => !d.vendor && d.active).length;
    const wanStatus = this._getWanStatus();

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <ha-card>
        ${this._renderHeader(wanStatus)}
        ${this._renderTabs()}
        <div class="card-content">
          ${this._activeTab === "devices" ? this._renderDevicesPanel(filtered, onlineCount, unknownCount, devices.length) : ""}
          ${this._activeTab === "logs" ? this._renderLogsPanel() : ""}
          ${this._activeTab === "stats" ? this._renderStatsPanel() : ""}
        </div>
      </ha-card>
    `;
    this._attachEvents();
  }

  _filterDevices(devices) {
    return devices.filter((d) => {
      if (this._filter === "online" && !d.active) return false;
      if (this._filter === "offline" && d.active) return false;
      if (this._filter === "blocked" && !d.blocked) return false;
      if (this._search) {
        const q = this._search.toLowerCase();
        return (
          d.name.toLowerCase().includes(q) ||
          d.mac.toLowerCase().includes(q) ||
          d.ip.includes(q)
        );
      }
      return true;
    });
  }

  _renderHeader(wanStatus) {
    const isUp = wanStatus === "up" || wanStatus === "connected";
    return `
      <div class="lb-header">
        <div class="lb-title">
          <ha-icon icon="mdi:router-network"></ha-icon>
          <span>${this._config.title}</span>
        </div>
        <div class="lb-status ${isUp ? "status-up" : "status-down"}">
          <span class="status-dot"></span>
          ${isUp ? "Connecté · Fibre" : wanStatus}
        </div>
      </div>`;
  }

  _renderTabs() {
    const tabs = [
      { id: "devices", icon: "mdi:devices", label: "Appareils" },
      { id: "stats", icon: "mdi:chart-bar", label: "Stats" },
      { id: "logs", icon: "mdi:format-list-bulleted", label: "Logs" },
    ];
    return `
      <div class="lb-tabs">
        ${tabs.map((t) => `
          <button class="lb-tab ${this._activeTab === t.id ? "active" : ""}" data-tab="${t.id}">
            <ha-icon icon="${t.icon}"></ha-icon> ${t.label}
          </button>`).join("")}
      </div>`;
  }

  _renderDevicesPanel(devices, onlineCount, unknownCount, total) {
    return `
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-label">Total</div>
          <div class="stat-value">${total}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">En ligne</div>
          <div class="stat-value success">${onlineCount}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Inconnus</div>
          <div class="stat-value warning">${unknownCount}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Bloqués</div>
          <div class="stat-value danger">${devices.filter((d) => d.blocked).length}</div>
        </div>
      </div>
      <div class="toolbar">
        <input class="search" type="text" placeholder="Rechercher…" value="${this._search}" id="lb-search">
        <div class="filter-group">
          ${["all","online","offline","blocked"].map((f) => `
            <button class="filter-btn ${this._filter === f ? "active" : ""}" data-filter="${f}">
              ${f === "all" ? "Tous" : f === "online" ? "En ligne" : f === "offline" ? "Hors ligne" : "Bloqués"}
            </button>`).join("")}
        </div>
      </div>
      <div class="device-list">
        ${devices.length === 0 ? '<div class="empty">Aucun appareil trouvé</div>' : devices.map((d) => this._renderDevice(d)).join("")}
      </div>`;
  }

  _renderDevice(d) {
    const icon = DEVICE_ICONS[d.device_type] || DEVICE_ICONS.default;
    const statusClass = d.blocked ? "blocked" : d.active ? "online" : "offline";
    const statusLabel = d.blocked ? "Bloqué" : d.active ? "En ligne" : "Hors ligne";
    const wifiIcon = d.link_type?.toLowerCase().includes("wifi") ? "mdi:wifi" : "mdi:ethernet";
    return `
      <div class="device-row ${!d.vendor ? "unknown-row" : ""}" data-mac="${d.mac}">
        <ha-icon icon="${icon}" class="dev-icon ${statusClass}"></ha-icon>
        <div class="dev-info">
          <div class="dev-name">${d.name}</div>
          <div class="dev-meta">
            ${d.ip ? `<span class="ip-pill">${d.ip}</span>` : ""}
            ${d.mac ? `<span class="mac-pill">${d.mac}</span>` : ""}
            ${d.vendor ? `<span class="vendor">${d.vendor}</span>` : ""}
          </div>
        </div>
        <div class="dev-right">
          <ha-icon icon="${wifiIcon}" class="link-icon"></ha-icon>
          <span class="status-badge ${statusClass}">${statusLabel}</span>
          <button class="action-btn" data-mac="${d.mac}" data-blocked="${d.blocked}" title="${d.blocked ? "Débloquer" : "Bloquer"}">
            <ha-icon icon="${d.blocked ? "mdi:lock-open" : "mdi:lock"}"></ha-icon>
          </button>
        </div>
      </div>`;
  }

  _renderLogsPanel() {
    const logs = this._logs.length > 0 ? this._logs : this._generateDemoLogs();
    return `
      <div class="logs-header">
        <span>${logs.length} événements</span>
        <button class="scan-btn" id="lb-scan">
          <ha-icon icon="mdi:refresh"></ha-icon> Scanner
        </button>
      </div>
      <div class="log-list">
        ${logs.map((l) => `
          <div class="log-row">
            <span class="log-time">${l.time}</span>
            <span class="log-chip ${l.type}">${l.label}</span>
            <span class="log-name">${l.name}</span>
            <span class="log-ip">${l.ip}</span>
          </div>`).join("")}
      </div>`;
  }

  _renderStatsPanel() {
    const sensors = Object.values(this._hass?.states || {}).filter(
      (s) => s.entity_id.startsWith("sensor.livebox_")
    );
    return `
      <div class="stats-grid">
        ${sensors.map((s) => `
          <div class="stat-card-full">
            <div class="stat-label">${s.attributes.friendly_name || s.entity_id}</div>
            <div class="stat-value">${s.state} ${s.attributes.unit_of_measurement || ""}</div>
          </div>`).join("")}
        ${sensors.length === 0 ? '<div class="empty">Configurez l\'intégration pour voir les stats</div>' : ""}
      </div>`;
  }

  _generateDemoLogs() {
    const now = new Date();
    return [
      { time: this._fmtTime(new Date(now - 120000)), type: "connect", label: "Connexion", name: "iPhone de Nicolas", ip: "192.168.1.8" },
      { time: this._fmtTime(new Date(now - 600000)), type: "new", label: "Nouveau", name: "INCONNU", ip: "192.168.1.201" },
      { time: this._fmtTime(new Date(now - 1800000)), type: "disconnect", label: "Déconnexion", name: "MacBook Pro", ip: "192.168.1.34" },
      { time: this._fmtTime(new Date(now - 3600000)), type: "connect", label: "Connexion", name: "Tesla Model 3", ip: "192.168.1.176" },
      { time: this._fmtTime(new Date(now - 7200000)), type: "blocked", label: "Bloqué", name: "INCONNU", ip: "" },
    ];
  }

  _fmtTime(d) {
    return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  }

  // ── Événements ─────────────────────────────────────────────────────

  _attachEvents() {
    const root = this.shadowRoot;

    root.querySelectorAll(".lb-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        this._activeTab = btn.dataset.tab;
        this._render();
      });
    });

    root.querySelectorAll(".filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this._filter = btn.dataset.filter;
        this._render();
      });
    });

    const search = root.querySelector("#lb-search");
    if (search) {
      search.addEventListener("input", (e) => {
        this._search = e.target.value;
        this._render();
      });
    }

    root.querySelectorAll(".action-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const mac = btn.dataset.mac;
        const blocked = btn.dataset.blocked === "true";
        const service = blocked ? "unblock_device" : "block_device";
        this._hass.callService("livebox_monitor", service, { mac });
      });
    });

    const scanBtn = root.querySelector("#lb-scan");
    if (scanBtn) {
      scanBtn.addEventListener("click", () => {
        this._hass.callService("livebox_monitor", "scan_network", {});
      });
    }
  }

  // ── CSS ────────────────────────────────────────────────────────────

  _styles() {
    return `
      ha-card { overflow: hidden; }
      .lb-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px 0; }
      .lb-title { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 500; }
      .lb-status { display: flex; align-items: center; gap: 6px; font-size: 12px; border-radius: 99px; padding: 4px 10px; }
      .status-up { background: rgba(29,158,117,.12); color: #1D9E75; }
      .status-down { background: rgba(226,75,74,.12); color: #E24B4A; }
      .status-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
      .lb-tabs { display: flex; gap: 4px; padding: 10px 12px 0; }
      .lb-tab { display: flex; align-items: center; gap: 5px; padding: 6px 12px; border: none; border-radius: 8px; background: transparent; color: var(--secondary-text-color); cursor: pointer; font-size: 13px; font-weight: 500; }
      .lb-tab:hover { background: var(--secondary-background-color); }
      .lb-tab.active { background: var(--primary-color); color: #fff; }
      .lb-tab ha-icon { --mdc-icon-size: 16px; }
      .card-content { padding: 10px 12px 14px; }
      .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 10px; }
      .stat-card { background: var(--secondary-background-color); border-radius: 8px; padding: 8px 10px; text-align: center; }
      .stat-label { font-size: 11px; color: var(--secondary-text-color); margin-bottom: 2px; }
      .stat-value { font-size: 20px; font-weight: 500; }
      .stat-value.success { color: #1D9E75; }
      .stat-value.warning { color: #EF9F27; }
      .stat-value.danger { color: #E24B4A; }
      .toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }
      .search { flex: 1; min-width: 120px; border: 1px solid var(--divider-color); border-radius: 8px; padding: 6px 10px; background: var(--secondary-background-color); color: var(--primary-text-color); font-size: 13px; }
      .filter-group { display: flex; gap: 4px; }
      .filter-btn { border: 1px solid var(--divider-color); border-radius: 6px; padding: 4px 10px; background: transparent; color: var(--secondary-text-color); cursor: pointer; font-size: 11px; }
      .filter-btn.active { background: var(--primary-color); color: #fff; border-color: var(--primary-color); }
      .device-list { display: flex; flex-direction: column; gap: 4px; }
      .device-row { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; background: var(--secondary-background-color); }
      .device-row.unknown-row { background: rgba(226,75,74,.06); }
      .dev-icon { --mdc-icon-size: 22px; }
      .dev-icon.online { color: #1D9E75; }
      .dev-icon.offline { color: var(--disabled-text-color); }
      .dev-icon.blocked { color: #E24B4A; }
      .dev-info { flex: 1; min-width: 0; }
      .dev-name { font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .dev-meta { display: flex; gap: 5px; margin-top: 2px; flex-wrap: wrap; }
      .ip-pill { font-size: 10px; font-family: monospace; background: var(--divider-color); padding: 1px 6px; border-radius: 4px; }
      .mac-pill { font-size: 10px; font-family: monospace; color: var(--secondary-text-color); }
      .vendor { font-size: 10px; color: var(--secondary-text-color); }
      .dev-right { display: flex; align-items: center; gap: 6px; }
      .link-icon { --mdc-icon-size: 16px; color: var(--secondary-text-color); }
      .status-badge { font-size: 10px; padding: 2px 7px; border-radius: 99px; font-weight: 500; }
      .status-badge.online { background: rgba(29,158,117,.15); color: #1D9E75; }
      .status-badge.offline { background: var(--secondary-background-color); color: var(--secondary-text-color); }
      .status-badge.blocked { background: rgba(226,75,74,.15); color: #E24B4A; }
      .action-btn { border: none; background: transparent; cursor: pointer; color: var(--secondary-text-color); padding: 2px; border-radius: 4px; display: flex; align-items: center; }
      .action-btn:hover { background: var(--divider-color); color: var(--primary-text-color); }
      .action-btn ha-icon { --mdc-icon-size: 18px; }
      .logs-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: var(--secondary-text-color); }
      .scan-btn { display: flex; align-items: center; gap: 4px; border: 1px solid var(--divider-color); border-radius: 6px; padding: 4px 10px; background: transparent; cursor: pointer; font-size: 12px; color: var(--secondary-text-color); }
      .log-list { display: flex; flex-direction: column; gap: 4px; }
      .log-row { display: flex; align-items: center; gap: 8px; padding: 6px 8px; background: var(--secondary-background-color); border-radius: 6px; font-size: 12px; }
      .log-time { font-family: monospace; font-size: 11px; color: var(--secondary-text-color); min-width: 42px; }
      .log-chip { padding: 1px 7px; border-radius: 99px; font-size: 10px; font-weight: 500; }
      .log-chip.connect { background: rgba(29,158,117,.15); color: #1D9E75; }
      .log-chip.disconnect { background: rgba(226,75,74,.12); color: #E24B4A; }
      .log-chip.new { background: rgba(239,159,39,.15); color: #854F0B; }
      .log-chip.blocked { background: rgba(226,75,74,.15); color: #E24B4A; }
      .log-name { font-weight: 500; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .log-ip { font-family: monospace; font-size: 11px; color: var(--secondary-text-color); }
      .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
      .stat-card-full { background: var(--secondary-background-color); border-radius: 8px; padding: 10px 12px; }
      .empty { text-align: center; color: var(--secondary-text-color); padding: 24px; font-size: 13px; }
    `;
  }

  static getConfigElement() {
    return document.createElement("livebox-monitor-card-editor");
  }

  static getStubConfig() {
    return { title: "Livebox Monitor" };
  }
}

customElements.define("livebox-monitor-card", LiveboxMonitorCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "livebox-monitor-card",
  name: "Livebox Monitor",
  description: "Dashboard complet de surveillance réseau Livebox Orange",
  preview: true,
  documentationURL: "https://github.com/votre-pseudo-github/hacs-livebox-monitor",
});

console.info(`%c LIVEBOX MONITOR CARD %c v${CARD_VERSION}`, "background:#185FA5;color:#fff;padding:2px 6px;border-radius:3px 0 0 3px", "background:#1D9E75;color:#fff;padding:2px 6px;border-radius:0 3px 3px 0");
