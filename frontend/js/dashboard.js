/**
 * FaultLens Command Center Dashboard Controller
 */

document.addEventListener("DOMContentLoaded", async () => {
  await loadDashboardStats();
  await loadPriorityQueue();
});

async function loadDashboardStats() {
  try {
    const data = await API.getDashboardStats();
    const m = data.metrics || {};

    // Update KPI numbers
    document.getElementById("kpiTotalAssets").textContent = m.total_assets ?? "--";
    document.getElementById("kpiCritical").textContent = m.critical ?? 0;
    document.getElementById("kpiHigh").textContent = m.high ?? 0;
    document.getElementById("kpiModerate").textContent = m.moderate ?? 0;
    document.getElementById("kpiHealthy").textContent = m.healthy ?? 0;
    document.getElementById("kpiOpenTasks").textContent = m.open_maintenance_tasks ?? 0;
    document.getElementById("kpiActiveAlerts").textContent = m.active_alerts ?? 0;
    document.getElementById("kpiCritAlerts").textContent = `${m.critical_alerts ?? 0} critical severity`;

    // Sidebar badges
    const taskBadge = document.getElementById("sidebarTasksCount");
    if (taskBadge) taskBadge.textContent = m.open_maintenance_tasks ?? 0;
    const alertBadge = document.getElementById("sidebarAlertsCount");
    if (alertBadge) alertBadge.textContent = m.active_alerts ?? 0;

    // Render Risk Distribution Progress Bars
    renderRiskDistribution(data.risk_distribution || [], m.total_assets || 1);

    // Render Recent Alerts Feed
    renderRecentAlerts(data.recent_alerts || []);
  } catch (err) {
    console.error("Error loading dashboard metrics:", err);
  }
}

function renderRiskDistribution(dist, total) {
  const container = document.getElementById("riskDistributionContainer");
  if (!container) return;

  if (!dist.length) {
    container.innerHTML = '<div style="color:var(--text-muted); font-size:12px;">No risk data available.</div>';
    return;
  }

  container.innerHTML = dist.map(item => {
    const pct = total > 0 ? Math.round((item.count / total) * 100) : 0;
    return `
      <div>
        <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
          <span style="font-weight:600; color:${item.color};">${item.tier}</span>
          <span style="color:var(--text-secondary); font-family:var(--font-mono);">${item.count} units (${pct}%)</span>
        </div>
        <div style="height:6px; background:var(--bg-tertiary); border-radius:3px; overflow:hidden;">
          <div style="height:100%; width:${pct}%; background:${item.color}; border-radius:3px; transition:width 0.8s ease;"></div>
        </div>
      </div>
    `;
  }).join("");
}

function renderRecentAlerts(alerts) {
  const container = document.getElementById("dashboardAlertsFeed");
  if (!container) return;

  if (!alerts.length) {
    container.innerHTML = '<div style="color:var(--text-muted); font-size:12px; padding:8px 0;">No active alerts recorded.</div>';
    return;
  }

  container.innerHTML = alerts.slice(0, 4).map(a => {
    const badgeClass = a.severity === "CRITICAL" ? "badge-critical" : "badge-high";
    const timeStr = a.triggered_at ? new Date(a.triggered_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
    return `
      <div style="padding:10px 12px; background:var(--bg-secondary); border:1px solid var(--border-dim); border-radius:var(--radius-md); display:flex; flex-direction:column; gap:4px;">
        <div style="display:flex; align-items:center; justify-content:space-between;">
          <span class="badge ${badgeClass}" style="font-size:10px;">${a.severity}</span>
          <span style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">${timeStr}</span>
        </div>
        <div style="font-size:12px; font-weight:600; color:#ffffff;">${a.title}</div>
        <div style="font-size:11px; color:var(--text-secondary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${a.message}</div>
      </div>
    `;
  }).join("");
}

async function loadPriorityQueue() {
  const tbody = document.getElementById("priorityQueueBody");
  if (!tbody) return;

  try {
    const res = await API.getDashboardPriority(8);
    const assets = res.priority_assets || [];

    if (!assets.length) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">No assets in queue.</td></tr>';
      return;
    }

    tbody.innerHTML = assets.map(a => {
      const probPct = a.failure_probability_pct ?? 0;
      let probBadgeClass = "badge-healthy";
      if (probPct >= 80) probBadgeClass = "badge-critical";
      else if (probPct >= 60) probBadgeClass = "badge-high";
      else if (probPct >= 30) probBadgeClass = "badge-moderate";

      let urgencyBadgeClass = "badge-moderate";
      if (a.urgency === "IMMEDIATE") urgencyBadgeClass = "badge-critical";
      else if (a.urgency === "HIGH") urgencyBadgeClass = "badge-high";

      const driversPills = (a.primary_drivers || []).slice(0, 2).map(d => 
        `<span style="display:inline-block; background:rgba(0,102,255,0.1); border:1px solid rgba(0,229,255,0.2); color:var(--accent-cyan); font-size:11px; padding:1px 6px; border-radius:3px; margin:2px 2px 2px 0;">${d}</span>`
      ).join("");

      return `
        <tr>
          <td style="font-family:var(--font-mono); font-weight:700; color:var(--accent-cyan);">#${a.rank}</td>
          <td>
            <a href="asset-detail.html?id=${a.asset_id}" style="color:#ffffff; font-weight:700; text-decoration:none;">
              ${a.asset_tag}
            </a>
            <div style="font-size:11px; color:var(--text-muted);">${a.asset_name}</div>
          </td>
          <td style="font-size:12px; color:var(--text-secondary);">${a.substation}</td>
          <td>
            <span class="badge ${probBadgeClass}">${probPct}%</span>
          </td>
          <td style="font-family:var(--font-mono); font-weight:700;">
            ${a.risk_score}
          </td>
          <td style="max-width:240px;">
            ${driversPills}
          </td>
          <td>
            <span class="badge ${urgencyBadgeClass}">${a.urgency}</span>
          </td>
          <td>
            <a href="asset-detail.html?id=${a.asset_id}" class="btn btn-outline btn-sm">
              Inspect →
            </a>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Error loading priority queue:", err);
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--status-critical);">Failed to load priority queue.</td></tr>';
  }
}
