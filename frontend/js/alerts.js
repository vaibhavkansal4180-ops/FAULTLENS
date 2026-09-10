/**
 * FaultLens Operational Alerts Controller
 */

let currentAlertStatus = "ACTIVE";

document.addEventListener("DOMContentLoaded", () => {
  loadAlerts();
  setupTabs();
});

function setupTabs() {
  document.querySelectorAll(".alert-tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".alert-tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentAlertStatus = btn.getAttribute("data-status");
      loadAlerts();
    });
  });
}

async function loadAlerts() {
  const tbody = document.getElementById("alertsTableBody");
  if (!tbody) return;

  try {
    const res = await API.getAlerts({ status: currentAlertStatus });
    const alerts = res.alerts || [];
    const counts = res.counts || {};

    document.getElementById("activeCountBadge").textContent = counts.active ?? 0;
    document.getElementById("ackCountBadge").textContent = counts.acknowledged ?? 0;
    document.getElementById("resCountBadge").textContent = counts.resolved ?? 0;

    if (!alerts.length) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">No ${currentAlertStatus.toLowerCase()} alerts.</td></tr>`;
      return;
    }

    tbody.innerHTML = alerts.map(a => {
      let sevClass = "badge-moderate";
      if (a.severity === "CRITICAL") sevClass = "badge-critical";
      else if (a.severity === "WARNING" || a.severity === "HIGH") sevClass = "badge-high";

      const timeStr = a.triggered_at ? new Date(a.triggered_at).toLocaleString() : "Recent";

      let actions = "";
      if (a.status === "ACTIVE") {
        actions = `
          <div style="display:flex; gap:6px;">
            <button class="btn btn-outline btn-sm" onclick="ackAlert(${a.id})">Acknowledge</button>
            <button class="btn btn-primary btn-sm" onclick="resolveAlertItem(${a.id})">Resolve</button>
          </div>
        `;
      } else if (a.status === "ACKNOWLEDGED") {
        actions = `
          <button class="btn btn-primary btn-sm" onclick="resolveAlertItem(${a.id})">Resolve</button>
        `;
      } else {
        actions = `<span style="font-size:11px; color:var(--text-muted);">Resolved by ${a.resolved_by || "System"}</span>`;
      }

      return `
        <tr>
          <td style="font-size:12px; font-family:var(--font-mono); color:var(--text-secondary);">${timeStr}</td>
          <td>
            <span class="badge ${sevClass}">${a.severity}</span>
          </td>
          <td>
            <a href="asset-detail.html?id=${a.asset_id}" style="color:#ffffff; font-weight:700; text-decoration:none;">
              ${a.asset_tag || `Asset #${a.asset_id}`}
            </a>
          </td>
          <td>
            <span class="badge badge-cyan" style="font-size:10px;">${a.alert_type}</span>
          </td>
          <td style="max-width:320px;">
            <div style="font-weight:600; color:#ffffff;">${a.title}</div>
            <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">${a.message}</div>
          </td>
          <td>
            <span class="badge" style="font-size:10px; background:var(--bg-tertiary); color:var(--text-secondary);">
              ${a.status}
            </span>
          </td>
          <td>
            ${actions}
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.error("Error loading alerts:", err);
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--status-critical);">Failed to load alerts.</td></tr>';
  }
}

async function ackAlert(id) {
  try {
    await API.acknowledgeAlert(id);
    await loadAlerts();
  } catch (err) {
    alert(err.message || "Failed to acknowledge alert.");
  }
}

async function resolveAlertItem(id) {
  try {
    await API.resolveAlert(id);
    await loadAlerts();
  } catch (err) {
    alert(err.message || "Failed to resolve alert.");
  }
}

window.ackAlert = ackAlert;
window.resolveAlertItem = resolveAlertItem;
