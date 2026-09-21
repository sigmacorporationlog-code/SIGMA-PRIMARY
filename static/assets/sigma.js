/* ============================================================
   SIGMA — Utilitaires partagés (auth, API, navigation, contexte)
   Sans framework ni build: chargé en <script> classique par
   chaque page HTML statique de /dashboard/.
   ============================================================ */

const SIGMA_PAGES = [
  { href: "/dashboard/", labelKey: "app.dashboard", tipKey: "navigation.overview_tip" },
  { href: "/dashboard/students.html", labelKey: "app.students", tipKey: "navigation.students_tip" },
  { href: "/dashboard/academic.html", labelKey: "app.academic", tipKey: "navigation.academic_tip" },
  { href: "/dashboard/honor-board.html", labelKey: "app.honor_board", tipKey: "navigation.honor_board_tip" },
  { href: "/dashboard/evaluations.html", labelKey: "app.evaluations", tipKey: "navigation.evaluations_tip" },
  { href: "/dashboard/cards.html", labelKey: "app.cards", tipKey: "navigation.cards_tip" },
  { href: "/dashboard/communication.html", labelKey: "app.communication", tipKey: "navigation.communication_tip" },
  { href: "/dashboard/finance.html", labelKey: "app.finance", tipKey: "navigation.finance_tip" },
  { href: "/dashboard/operations.html", labelKey: "app.operations", tipKey: "navigation.operations_tip" },
  { href: "/dashboard/administration.html", labelKey: "app.settings", tipKey: "navigation.administration_tip" },
  { href: "/dashboard/ai-control.html", labelKey: "app.ai", tipKey: "navigation.ai_tip" },
  { href: "/dashboard/teacher.html", labelKey: "app.teachers", tipKey: "navigation.teacher_tip" },
  { href: "/dashboard/parent.html", labelKey: "app.parent", tipKey: "navigation.parent_tip" },
  { href: "/dashboard/insight.html", labelKey: "app.insight", tipKey: "navigation.insight_tip" },
  { href: "/dashboard/licenses.html", labelKey: "app.licenses", tipKey: "navigation.licenses_tip", superadminOnly: true },
];

const Sigma = {
  i18n: {
    locale: "fr",
    catalog: {},
    async load(locale) {
      const wanted = locale === "en" ? "en" : "fr";
      try {
        const res = await fetch(`/i18n/${wanted}.json`, { credentials: "same-origin", cache: "no-store" });
        if (!res.ok) throw new Error(`i18n ${res.status}`);
        this.catalog = await res.json();
        this.locale = wanted;
        document.documentElement.lang = wanted;
      } catch (_) {
        if (wanted !== "fr") { await this.load("fr"); return; }
        this.catalog = {}; this.locale = "fr";
      }
    },
    t(key, fallback = key) {
      return Object.prototype.hasOwnProperty.call(this.catalog, key) ? this.catalog[key] : fallback;
    },
    async init() {
      let locale = null;
      try { locale = localStorage.getItem("sigma_locale"); } catch (_) {}
      if (!locale) locale = (navigator.language || "fr").toLowerCase().startsWith("en") ? "en" : "fr";
      await this.load(locale);
    },
    async setLocale(locale) {
      const next = locale === "en" ? "en" : "fr";
      try { localStorage.setItem("sigma_locale", next); } catch (_) {}
      await this.load(next);
      window.location.reload();
    },
  },
  t(key, fallback = key) { return this.i18n.t(key, fallback); },
  escapeHtml(value) { const d = document.createElement("div"); d.textContent = value == null ? "" : String(value); return d.innerHTML; },
  safeCssHexColor(value, fallback = null) { const v = String(value ?? ""); return /^#[0-9a-f]{3,8}$/i.test(v) ? v : fallback; },

  // ---------- Graphique en anneau (donut) partagé ----------
  // Palette dérivée de la charte graphique SIGMA (vert forêt -> orange vif),
  // pour ne jamais avoir à choisir des couleurs hors charte au cas par cas.
  _donutPalette: ["#11633A", "#FF8A00", "#1a8a54", "#e0a838", "#0c4a2b", "#f2b45c", "#3fae7a", "#c76f00"],
  /**
   * Rend un donut CSS (sans librairie externe) + sa légende dans le conteneur donné.
   * rows: [{label, value}], triés du plus grand au plus petit avant l'appel si besoin.
   * totalLabel: texte sous le total au centre (ex: "Élèves").
   */
  renderDonut(containerId, rows, totalLabel) {
    const el = document.getElementById(containerId);
    if (!el) return;
    const data = (rows || []).filter(r => r.value > 0);
    const total = data.reduce((s, r) => s + r.value, 0);
    if (!total) { el.innerHTML = '<div class="empty-state">Aucune donnée.</div>'; return; }
    let acc = 0;
    const stops = data.map((r, i) => {
      const start = (acc / total) * 100;
      acc += r.value;
      const end = (acc / total) * 100;
      const color = this.safeCssHexColor(r.color, this._donutPalette[i % this._donutPalette.length]);
      return `${color} ${start}% ${end}%`;
    }).join(", ");
    const legend = data.map((r, i) => {
      const color = this.safeCssHexColor(r.color, this._donutPalette[i % this._donutPalette.length]);
      const pct = Math.round((r.value / total) * 100);
      return `<div class="donut-legend-row"><span class="name"><span class="swatch" style="background:${color}"></span>${this.escapeHtml(r.label)}</span><span class="val">${this.escapeHtml(r.value)} (${pct}%)</span></div>`;
    }).join("");
    el.innerHTML = `
      <div class="donut-panel">
        <div class="donut" style="--donut-gradient: ${stops}">
          <div class="donut-center"><div class="donut-total">${this.escapeHtml(total)}</div><div class="donut-total-label">${this.escapeHtml(totalLabel || "")}</div></div>
        </div>
        <div class="donut-legend">${legend}</div>
      </div>`;
  },
  // ---------- Authentification ----------
  _accessToken: null,
  _user: null,
  _refreshPromise: null,
  token() { return this._accessToken; },
  isLoggedIn() { return !!this._accessToken; },
  _persistAccessToken() {
    try {
      if (this._accessToken) sessionStorage.setItem("sigma_access_token", this._accessToken);
      else sessionStorage.removeItem("sigma_access_token");
    } catch (_) {}
  },
  _restoreAccessToken() {
    try {
      const token = sessionStorage.getItem("sigma_access_token");
      if (token) this._accessToken = token;
    } catch (_) {}
    return this._accessToken;
  },
  async refresh() {
    // Une navigation HTML complète efface le token d'accès conservé en mémoire.
    // Le cookie HttpOnly de refresh est donc la source de continuité de session.
    // Déduplique les refresh simultanés au chargement d'une rubrique.
    if (this._refreshPromise) return this._refreshPromise;
    this._refreshPromise = (async () => {
      try {
        const res = await fetch("/api/auth/refresh", { method: "POST", credentials: "same-origin" });
        if (!res.ok) { this._accessToken = null; this._user = null; this._persistAccessToken(); return false; }
        const data = await res.json();
        this._accessToken = data.access_token;
        this._persistAccessToken();
        return true;
      } catch (_) {
        this._accessToken = null; this._user = null; this._persistAccessToken();
        return false;
      } finally {
        this._refreshPromise = null;
      }
    })();
    return this._refreshPromise;
  },
  async logout() {
    try {
      if (this._accessToken) await fetch("/api/auth/logout", { method: "POST", headers: { Authorization: "Bearer " + this._accessToken }, credentials: "same-origin" });
    } catch (_) {}
    this._accessToken = null; this._user = null; this._persistAccessToken();
    window.location.href = "/dashboard/";
  },

  async login(username, password) {
    const res = await fetch("/api/auth/login", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username, password }),
    });
    if (!res.ok) {
      let detail = "Identifiants incorrects.";
      try { detail = (await res.json()).detail || detail; } catch (e) {}
      throw new Error(detail);
    }
    const data = await res.json();
    this._accessToken = data.access_token;
    this._persistAccessToken();
    const me = await fetch("/api/auth/me", { headers: { Authorization: "Bearer " + data.access_token }, credentials: "same-origin" });
    if (me.ok) this._user = await me.json();
    return data;
  },

  // ---------- Appels API ----------
  async api(path, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const cacheKey = method === "GET" ? path : null;
    const headers = { ...(options.headers || {}) };
    if (this.token()) headers.Authorization = "Bearer " + this.token();
    if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
    try {
      let res = await fetch(path, { ...options, headers, credentials: "same-origin" });
      if (res.status === 401 && !options._authRetry) {
        if (await this.refresh()) {
          const retryHeaders = { ...(options.headers || {}) };
          if (this.token()) retryHeaders.Authorization = "Bearer " + this.token();
          if (options.body && !(options.body instanceof FormData) && !retryHeaders["Content-Type"]) retryHeaders["Content-Type"] = "application/json";
          res = await fetch(path, { ...options, headers: retryHeaders, credentials: "same-origin", _authRetry: true });
        }
      }
      if (res.status === 401) { await this.logout(); throw new Error("Session expirée"); }
      if (res.status === 403) {
        try { const e = await res.clone().json(); if (e.detail === "PASSWORD_CHANGE_REQUIRED") { window.location.href = "/dashboard/change-password.html"; throw new Error("Changement de mot de passe requis"); } } catch (_) {}
      }
      if (!res.ok) {
        let detail = `Erreur ${res.status}`;
        try { detail = (await res.json()).detail || detail; } catch (e) {}
        const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
        if (res.status >= 400 && res.status < 500) err._offlinePermanent = true;
        throw err;
      }
      const contentType = res.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const data = await res.json();
        if (cacheKey && window.SigmaOffline) await SigmaOffline.cachePut(cacheKey, data).catch(()=>{});
        return data;
      }
      return res.blob();
    } catch (e) {
      const networkLike = !e._offlinePermanent && (e instanceof TypeError || !navigator.onLine || /Failed to fetch|NetworkError|Load failed/i.test(e.message || ""));
      if (!networkLike) throw e;
      if (method === "GET" && window.SigmaOffline) {
        const cached = await SigmaOffline.cacheGet(path).catch(()=>undefined);
        if (cached !== undefined) { this.offlineState("cached"); return cached; }
      }
      if (["POST","PATCH","PUT","DELETE"].includes(method) && window.SigmaOffline && !options._offlineReplay) {
        if (options.body instanceof FormData) {
          const err = new Error("Cette opération nécessite la connexion au serveur.");
          err._offlinePermanent = true; throw err;
        }
        let body = options.body;
        if (typeof body === "string") { try { body = JSON.parse(body); } catch (_) {} }
        await SigmaOffline.queueMutation({path, method, body});
        this.offlineState("pending");
        if (path === "/api/students") { return {offline:true, queued:true, id:-Date.now(), ...body}; }
        if (path.includes("/results")) return {offline:true, queued:true};
        return {offline:true, queued:true};
      }
      throw e;
    }
  },

  offlineState(state) {
    const el = document.getElementById("sigma-network-status");
    if (el) { el.textContent = state === "pending" ? this.t("common.offline_pending") : state === "cached" ? this.t("common.offline_cached") : this.t("common.online"); el.className = "sigma-network-status " + state; }
  },

  async flushOffline() {
    if (!window.SigmaOffline) return;
    const r = await SigmaOffline.flush(this.api.bind(this));
    this.offlineState(r.remaining ? "pending" : "online");
    if (r.flushed) this.toast(`${r.flushed} ${this.t("common.sync_pending")}`);
    return r;
  },

  postJson(path, body) { return this.api(path, { method: "POST", body: JSON.stringify(body) }); },
  patchJson(path, body) { return this.api(path, { method: "PATCH", body: JSON.stringify(body) }); },

  async downloadBlob(path, filename) {
    const blob = await this.api(path);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  },

  async openBlobInNewTab(path) {
    const blob = await this.api(path);
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
  },

  async loadImageInto(imgEl, path, placeholderHtml) {
    try {
      const blob = await this.api(path);
      imgEl.src = URL.createObjectURL(blob);
    } catch (e) {
      if (placeholderHtml) imgEl.outerHTML = placeholderHtml;
    }
  },

  // ---------- Notifications ----------
  toast(message, type = "success") {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      document.body.appendChild(container);
    }
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  },

  // ---------- En-tête / navigation ----------
  _logoBlobUrlCache: null,
  async _resolveLogoUrl(schoolId) {
    // L'endpoint /api/schools/{id}/asset/logo exige un Authorization: Bearer
    // (isolation multi-établissement), donc une simple balise <img src="..">
    // ne peut pas s'authentifier. On récupère l'image via fetch authentifié
    // et on l'expose en URL blob locale à l'onglet.
    if (this._logoBlobUrlCache) return this._logoBlobUrlCache;
    try {
      const res = await fetch(`/api/schools/${schoolId}/asset/logo`, {
        headers: { Authorization: "Bearer " + this.token() },
        credentials: "same-origin",
      });
      if (!res.ok) return null; // pas de logo téléversé pour cet établissement
      const blob = await res.blob();
      this._logoBlobUrlCache = URL.createObjectURL(blob);
      return this._logoBlobUrlCache;
    } catch (e) {
      return null; // silencieux: l'absence de logo ne doit jamais bloquer l'en-tête
    }
  },

  renderHeader(activeHref) {
    const mount = document.getElementById("sigma-header");
    if (!mount) return;
    const user = this._user;
    // "Licences" pilote les abonnements/clés de licence de TOUS les
    // établissements (endpoint /api/cloud/control-plane) : réservé au
    // superadministrateur, jamais montré à un directeur d'établissement.
    const visiblePages = SIGMA_PAGES.filter(p => !p.superadminOnly || (user && user.is_superadmin));
    const navLinks = visiblePages.map(p =>
      `<a href="${this.escapeHtml(p.href)}" class="${p.href === activeHref ? "active" : ""}" data-tip="${this.escapeHtml(this.t(p.tipKey))}">${this.escapeHtml(this.t(p.labelKey))}</a>`
    ).join("");

    mount.innerHTML = `
      <aside class="sigma-sidebar">
        <div class="sigma-sidebar-brand">
          <img src="/dashboard/assets/sigma-logo.jpg" alt="SIGMA" />
          <div><div class="name">SIGMA</div><div class="tag">Gestion académique</div></div>
        </div>
        <span id="sigma-network-status" class="sigma-network-status">En ligne</span>
        <nav class="sigma-sidebar-nav">${navLinks}</nav>
        ${user ? `
        <div class="sigma-sidebar-user">
          <span class="who" id="sigma-who"><img id="sigma-school-logo" class="sigma-school-logo" alt="" style="display:none" /><span>${this.escapeHtml(user.first_name)} ${this.escapeHtml(user.last_name)}</span></span>
          <select id="sigma-language" aria-label="${this.escapeHtml(this.t("common.language"))}" class="sigma-language"><option value="fr">${this.escapeHtml(this.t("common.french"))}</option><option value="en">${this.escapeHtml(this.t("common.english"))}</option></select><button class="logout" onclick="Sigma.logout()">${this.escapeHtml(this.t("common.logout"))}</button>
        </div>` : ""}
      </aside>`;

    const localeSelect = document.getElementById("sigma-language");
    if (localeSelect) {
      localeSelect.value = this.i18n.locale;
      localeSelect.addEventListener("change", e => this.i18n.setLocale(e.target.value));
    }

    if (user && user.school_id) {
      this._resolveLogoUrl(user.school_id).then(url => {
        if (!url) return; // pas de logo pour cet établissement, on ne montre rien
        const img = document.getElementById("sigma-school-logo");
        if (img) { img.src = url; img.style.display = ""; }
      });
    }
  },

  renderLoginScreen(onSuccess) {
    const mount = document.getElementById("login-screen");
    if (!mount) return;
    mount.innerHTML = `
      <div class="login-screen">
        <div class="brand-row">
          <img src="/dashboard/assets/sigma-logo.jpg" alt="SIGMA" />
          <h2>${this.escapeHtml(this.t("auth.login"))} à SIGMA</h2>
        </div>
        <input id="login-username" placeholder="${this.escapeHtml(this.t("auth.username"))}" value="admin" />
        <input id="login-password" type="password" placeholder="${this.escapeHtml(this.t("auth.password"))}" />
        <div style="margin:8px 0"><a href="/dashboard/forgot-password.html">${this.escapeHtml(this.t("auth.forgot_password"))}</a></div>
        <button class="btn" id="login-btn">${this.escapeHtml(this.t("auth.login_button"))}</button>
        <div id="login-error"></div>
      </div>`;

    document.getElementById("login-btn").addEventListener("click", async () => {
      const username = document.getElementById("login-username").value;
      const password = document.getElementById("login-password").value;
      const errorBox = document.getElementById("login-error");
      errorBox.textContent = "";
      try {
        await this.login(username, password);
        onSuccess();
      } catch (e) {
        errorBox.textContent = e.message;
      }
    });
  },

  // ---------- Point d'entrée de page ----------
  // Affiche l'écran de connexion si nécessaire, sinon révèle #main-screen,
  // dessine l'en-tête, puis appelle onReady().
  boot(activeHref, onReady) {
    const ensureOfflineReady = () => {
      if (window.SigmaOffline) return Promise.resolve();
      const existing = document.querySelector('script[src*="sigma-offline.js"]');
      if (existing) return new Promise(resolve => {
        existing.addEventListener('load', () => resolve(), { once: true });
        existing.addEventListener('error', () => resolve(), { once: true });
      });
      return new Promise(resolve => {
        const sc = document.createElement('script');
        sc.src = '/dashboard/assets/sigma-offline.js';
        sc.onload = () => resolve();
        sc.onerror = () => resolve();
        document.head.appendChild(sc);
      });
    };
    const showMain = async () => {
      await ensureOfflineReady();
      const login = document.getElementById("login-screen");
      if (login) login.style.display = "none";
      const main = document.getElementById("main-screen");
      if (main) main.style.display = "block";
      document.body.classList.add("sigma-authed");
      await this.i18n.init();
      this.renderHeader(activeHref);
      const updateNetwork = async () => {
        if (!window.SigmaOffline) return;
        const st = await SigmaOffline.status();
        this.offlineState(st.online ? (st.pending ? "pending" : "online") : "cached");
        if (st.online && st.pending) await this.flushOffline();
      };
      window.addEventListener('online', updateNetwork);
      window.addEventListener('offline', updateNetwork);
      setTimeout(updateNetwork, 0);
      await onReady();
    };
    const continueAfterAuth = async (refreshAttempted = false) => {
      this._restoreAccessToken();
      // À chaque changement de page, le JS repart de zéro. On tente d'abord
      // de restaurer silencieusement la session via le cookie HttpOnly.
      this._restoreAccessToken();
      if (!this._accessToken) {
        if (!refreshAttempted && await this.refresh()) return continueAfterAuth(true);
        return this.renderLoginScreen(showMain);
      }
      try {
        const me = await fetch("/api/auth/me", { headers: { Authorization: "Bearer " + this._accessToken }, credentials: "same-origin" });
        if (!me.ok) throw new Error("expired");
        this._user = await me.json();
        if (this._user.must_change_password) { window.location.href = "/dashboard/change-password.html"; return; }
        showMain();
      } catch (_) {
        this._accessToken = null; this._user = null; this._persistAccessToken();
        if (!refreshAttempted && await this.refresh()) return continueAfterAuth(true);
        this.renderLoginScreen(showMain);
      }
    };
    continueAfterAuth(false);
  },

  // ---------- Barre de contexte (école / année / classe / période) ----------
  // Persiste la sélection dans localStorage pour qu'elle survive à la
  // navigation entre les pages du tableau de bord.
  context: {
    get() {
      try {
        const raw = localStorage.getItem("sigma_context");
        const value = raw ? JSON.parse(raw) : {};
        return value && typeof value === "object" ? value : {};
      } catch (_) {
        return {};
      }
    },
    set(partial) {
      const current = this.get();
      localStorage.setItem("sigma_context", JSON.stringify({ ...current, ...partial }));
    },
  },

  async renderContextBar(mountId, { showClass = true, showPeriod = true } = {}, onChange) {
    const mount = document.getElementById(mountId);
    if (!mount) return;
    const ctx = this.context.get();

    mount.innerHTML = `
      <div class="context-bar">
        <div class="field">
          <label>${this.escapeHtml(this.t("common.school"))}</label>
          <select id="ctx-school"></select>
        </div>
        <div class="field">
          <label>${this.escapeHtml(this.t("common.school_year"))}</label>
          <select id="ctx-year"></select>
        </div>
        ${showClass ? `<div class="field"><label>${this.escapeHtml(this.t("common.class"))}</label><select id="ctx-class"><option value="">${this.escapeHtml(this.t("common.all"))}</option></select></div>` : ""}
        ${showPeriod ? `<div class="field"><label>${this.escapeHtml(this.t("common.period"))}</label><select id="ctx-period"></select></div>` : ""}
      </div>`;

    const schoolSelect = document.getElementById("ctx-school");
    const yearSelect = document.getElementById("ctx-year");
    const classSelect = showClass ? document.getElementById("ctx-class") : null;
    const periodSelect = showPeriod ? document.getElementById("ctx-period") : null;

    const schools = await this.api(`/api/schools`);
    schoolSelect.innerHTML = schools.map(s => `<option value="${Number(s.id)}">${this.escapeHtml(s.name)}</option>`).join("");
    schoolSelect.value = ctx.school_id || (schools[0] && schools[0].id) || "";

    const loadYears = async () => {
      const years = await this.api(`/api/academic-years?school_id=${schoolSelect.value}`);
      yearSelect.innerHTML = years.map(y => `<option value="${Number(y.id)}">${this.escapeHtml(y.label)}${y.is_current ? ' (' + this.escapeHtml(this.t("common.current")) + ')' : ""}</option>`).join("");
      const currentYear = years.find(y => y.is_current);
      const wanted = String(ctx.academic_year_id || "");
      yearSelect.value = years.some(y => String(y.id) === wanted) ? wanted : String((currentYear && currentYear.id) || (years[0] && years[0].id) || "");
    };

    const loadClasses = async () => {
      if (!classSelect) return;
      const classes = await this.api(`/api/classes?school_id=${schoolSelect.value}&academic_year_id=${yearSelect.value}`);
      classSelect.innerHTML = `<option value="">${this.escapeHtml(this.t("common.all"))}</option>` + classes.map(c => `<option value="${Number(c.id)}">${this.escapeHtml(c.name)}</option>`).join("");
      const wanted = String(ctx.class_id || "");
      classSelect.value = classes.some(c => String(c.id) === wanted) ? wanted : "";
    };

    const loadPeriods = async () => {
      if (!periodSelect) return;
      const periods = await this.api(`/api/academic-periods?academic_year_id=${yearSelect.value}`);
      periodSelect.innerHTML = periods.map(p => `<option value="${Number(p.id)}">${this.escapeHtml(p.name)}</option>`).join("");
      const wanted = String(ctx.academic_period_id || "");
      periodSelect.value = periods.some(p => String(p.id) === wanted) ? wanted : String((periods[0] && periods[0].id) || "");
    };

    const emit = () => {
      this.context.set({
        school_id: schoolSelect.value || null,
        academic_year_id: yearSelect.value || null,
        class_id: classSelect ? (classSelect.value || null) : null,
        academic_period_id: periodSelect ? (periodSelect.value || null) : null,
      });
      if (onChange) onChange(this.context.get());
    };

    await loadYears();
    await loadClasses();
    await loadPeriods();
    emit();

    schoolSelect.addEventListener("change", async () => {
      ctx.academic_year_id = null; ctx.class_id = null; ctx.academic_period_id = null;
      await loadYears(); await loadClasses(); await loadPeriods(); emit();
    });
    yearSelect.addEventListener("change", async () => {
      ctx.class_id = null; ctx.academic_period_id = null;
      await loadClasses(); await loadPeriods(); emit();
    });
    if (classSelect) classSelect.addEventListener("change", emit);
    if (periodSelect) periodSelect.addEventListener("change", emit);
  },
};
