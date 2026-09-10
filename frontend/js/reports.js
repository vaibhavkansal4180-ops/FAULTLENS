/**
 * FaultLens Field Incident Reports Controller
 */

document.addEventListener("DOMContentLoaded", () => {
  loadReports();
  setupFilters();
  setupReportModal();
});

async function loadReports() {
  const tbody = document.getElementById("reportsTableBody");
  if (!tbody) return;

  const category = document.getElementById("reportCategoryFilter").value;
  const severity = document.getElementById("reportSeverityFilter").value;

  try {
    const res = await API.getReports({ category, severity });
    const reports = res.reports || [];

    document.getElementById("reportsCountLabel").textContent = `Displaying ${reports.length} field observations`;

    if (!reports.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">No field reports found.</td></tr>';
      return;
    }

    tbody.innerHTML = reports.map(r => {
      let sevClass = "badge-moderate";
      if (r.severity === "CRITICAL") sevClass = "badge-critical";
      else if (r.severity === "HIGH") sevClass = "badge-high";
      else if (r.severity === "LOW") sevClass = "badge-healthy";

      const timeStr = r.reported_at ? new Date(r.reported_at).toLocaleString() : "Recent";

      return `
        <tr>
          <td style="font-size:12px; font-family:var(--font-mono); color:var(--text-secondary);">${timeStr}</td>
          <td>
            <a href="asset-detail.html?id=${r.asset_id}" style="color:#ffffff; font-weight:700; text-decoration:none;">
              ${r.asset_tag || `Asset #${r.asset_id}`}
            </a>
          </td>
          <td>
            <span class="badge badge-cyan" style="font-size:10px;">${r.category}</span>
          </td>
          <td>
            <span class="badge ${sevClass}">${r.severity}</span>
          </td>
          <td style="max-width:320px;">
            <div style="font-weight:600; color:#ffffff;">${r.title}</div>
            <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">${r.description}</div>
          </td>
          <td style="font-size:12px;">${r.reporter_name}</td>
          <td>
            <span class="badge" style="background:var(--bg-tertiary); color:var(--text-secondary); font-size:10px;">
              ${r.status}
            </span>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.error("Error loading incident reports:", err);
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--status-critical);">Failed to load reports.</td></tr>';
  }
}

function setupFilters() {
  document.getElementById("reportCategoryFilter").addEventListener("change", loadReports);
  document.getElementById("reportSeverityFilter").addEventListener("change", loadReports);
}

async function setupReportModal() {
  const modal = document.getElementById("createReportModal");
  const openBtn = document.getElementById("openReportModalBtn");
  const closeBtn = document.getElementById("closeReportModalBtn");
  const cancelBtn = document.getElementById("cancelReportModalBtn");
  const form = document.getElementById("createReportForm");
  const select = document.getElementById("repAssetSelect");

  try {
    const res = await API.getAssets({ per_page: 50 });
    const assets = res.assets || [];
    select.innerHTML = '<option value="">Select asset...</option>' + assets.map(a => `
      <option value="${a.id}">${a.asset_tag} — ${a.name} [${a.substation}]</option>
    `).join("");
  } catch (e) {}

  if (openBtn) openBtn.addEventListener("click", () => modal.classList.add("open"));
  const closeModal = () => modal.classList.remove("open");
  if (closeBtn) closeBtn.addEventListener("click", closeModal);
  if (cancelBtn) cancelBtn.addEventListener("click", closeModal);

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        asset_id: parseInt(select.value, 10),
        category: document.getElementById("repCategory").value,
        severity: document.getElementById("repSeverity").value,
        title: document.getElementById("repTitle").value.trim(),
        description: document.getElementById("repDescription").value.trim(),
      };

      try {
        const res = await API.createReport(payload);
        closeModal();
        form.reset();
        await loadReports();
        alert(`Observation recorded! Asset risk adjusted to ${res.updated_risk_score} (${res.health_status}).`);
      } catch (err) {
        alert(err.message || "Failed to submit observation.");
      }
    });
  }
}
