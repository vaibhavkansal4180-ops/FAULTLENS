/**
 * FaultLens Centralized API Client
 * Production-ready relative API communication utilizing window.location.origin
 */

const API_BASE = `${window.location.origin}/api`;

const API = {
  /**
   * Generic request wrapper handling JSON formatting, cookies, and standard errors
   */
  async request(endpoint, options = {}) {
    const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;
    
    const defaultHeaders = {
      "Content-Type": "application/json",
      "Accept": "application/json",
    };

    // Include stored user ID header if present (supports headless/stateless dev)
    const storedUserId = localStorage.getItem("faultlens_user_id");
    if (storedUserId) {
      defaultHeaders["X-User-Id"] = storedUserId;
    }

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {}),
      },
      credentials: "same-origin",
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMsg = data.error || data.message || `Request failed with status ${response.status}`;
        throw new Error(errorMsg);
      }

      return data;
    } catch (err) {
      console.error(`[API Error] ${endpoint}:`, err);
      throw err;
    }
  },

  get(endpoint, params = {}) {
    const query = new URLSearchParams(params).toString();
    const fullUrl = query ? `${endpoint}?${query}` : endpoint;
    return this.request(fullUrl, { method: "GET" });
  },

  post(endpoint, body = {}) {
    return this.request(endpoint, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  put(endpoint, body = {}) {
    return this.request(endpoint, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: "DELETE" });
  },

  // --- Auth APIs ---
  async login(username, password) {
    const res = await this.post("/auth/login", { username, password });
    if (res.user && res.user.id) {
      localStorage.setItem("faultlens_user_id", res.user.id);
      localStorage.setItem("faultlens_user_role", res.user.role);
      localStorage.setItem("faultlens_username", res.user.username);
    }
    return res;
  },

  async register(username, email, password, role = "VIEWER", full_name = "") {
    const res = await this.post("/auth/register", {
      username,
      email,
      password,
      role,
      full_name,
    });
    if (res.user && res.user.id) {
      localStorage.setItem("faultlens_user_id", res.user.id);
      localStorage.setItem("faultlens_user_role", res.user.role);
      localStorage.setItem("faultlens_username", res.user.username);
    }
    return res;
  },

  async logout() {
    try {
      await this.post("/auth/logout");
    } finally {
      localStorage.removeItem("faultlens_user_id");
      localStorage.removeItem("faultlens_user_role");
      localStorage.removeItem("faultlens_username");
      window.location.href = "/login.html";
    }
  },

  getMe() {
    return this.get("/auth/me");
  },

  // --- Dashboard APIs ---
  getDashboardStats() {
    return this.get("/dashboard/stats");
  },

  getDashboardPriority(limit = 10) {
    return this.get("/dashboard/priority", { limit });
  },

  // --- Asset APIs ---
  getAssets(params = {}) {
    return this.get("/assets", params);
  },

  getAsset(id) {
    return this.get(`/assets/${id}`);
  },

  createAsset(data) {
    return this.post("/assets", data);
  },

  updateAsset(id, data) {
    return this.put(`/assets/${id}`, data);
  },

  deleteAsset(id) {
    return this.delete(`/assets/${id}`);
  },

  // --- Telemetry APIs ---
  getTelemetry(assetId, limit = 48) {
    return this.get(`/assets/${assetId}/telemetry`, { limit });
  },

  generateTelemetry(assetId, anomalyMode = null) {
    return this.post(`/assets/${assetId}/telemetry/generate`, { anomaly_mode: anomalyMode });
  },

  // --- Maintenance & Workflow APIs ---
  getTasks(params = {}) {
    return this.get("/maintenance/tasks", params);
  },

  getTask(id) {
    return this.get(`/maintenance/tasks/${id}`);
  },

  createTask(data) {
    return this.post("/maintenance/tasks", data);
  },

  updateTaskStatus(id, status, notes = "") {
    return this.put(`/maintenance/tasks/${id}/status`, { status, resolution_notes: notes });
  },

  getMaintenanceRecords(assetId = null) {
    const params = assetId ? { asset_id: assetId } : {};
    return this.get("/maintenance/records", params);
  },

  // --- Incident Reports & Alerts ---
  getReports(params = {}) {
    return this.get("/reports", params);
  },

  createReport(data) {
    return this.post("/reports", data);
  },

  getAlerts(params = {}) {
    return this.get("/alerts", params);
  },

  acknowledgeAlert(id) {
    return this.put(`/alerts/${id}/acknowledge`);
  },

  resolveAlert(id) {
    return this.put(`/alerts/${id}/resolve`);
  },

  // --- ML Prediction & Risk Timeline ---
  analyzePrediction(data) {
    return this.post("/prediction/analyze", data);
  },

  getRiskTimeline(assetId) {
    return this.get(`/assets/${assetId}/risk-timeline`);
  },

  // --- What-If Simulation ---
  simulateWhatIf(data) {
    return this.post("/simulation/what-if", data);
  }
};

window.API = API;
