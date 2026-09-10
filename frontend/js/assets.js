/**
 * FaultLens Transformer Fleet Catalog Controller
 */

let currentPage = 1;
const perPage = 15;
let debounceTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  loadAssets();

  // Search filter
  const searchInput = document.getElementById("assetSearchInput");
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        currentPage = 1;
        loadAssets();
      }, 300);
    });
  }

  // Filter selects
  document.getElementById("healthFilter").addEventListener("change", () => {
    currentPage = 1;
    loadAssets();
  });
  document.getElementById("statusFilter").addEventListener("change", () => {
    currentPage = 1;
    loadAssets();
  });
  document.getElementById("sortBySelect").addEventListener("change", () => {
    currentPage = 1;
    loadAssets();
  });

  // Reset button
  document.getElementById("resetFiltersBtn").addEventListener("click", () => {
    document.getElementById("assetSearchInput").value = "";
    document.getElementById("healthFilter").value = "";
    document.getElementById("statusFilter").value = "";
    document.getElementById("sortBySelect").value = "risk_desc";
    currentPage = 1;
    loadAssets();
  });

  // Pagination buttons
  document.getElementById("prevPageBtn").addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      loadAssets();
    }
  });
  document.getElementById("nextPageBtn").addEventListener("click", () => {
    currentPage++;
    loadAssets();
  });

  // Admin Modal handlers
  setupModal();
});

async function loadAssets() {
  const tbody = document.getElementById("assetsTableBody");
  if (!tbody) return;

  const search = document.getElementById("assetSearchInput").value.trim();
  const health = document.getElementById("healthFilter").value;
  const status = document.getElementById("statusFilter").value;
  const sortBy = document.getElementById("sortBySelect").value;

  const params = {
    page: currentPage,
    per_page: perPage,
    search,
    health,
    status,
    sort_by: sortBy,
  };

  try {
    const res = await API.getAssets(params);
    const assets = res.assets || [];
    const p = res.pagination || {};

    document.getElementById("assetCountSubtitle").textContent = `Displaying ${assets.length} of ${p.total || 0} assets`;
    document.getElementById("paginationInfo").textContent = `Page ${p.current_page || 1} of ${p.pages || 1}`;

    document.getElementById("prevPageBtn").disabled = !p.has_prev;
    document.getElementById("nextPageBtn").disabled = !p.has_next;

    if (!assets.length) {
      tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; color:var(--text-muted);">No transformer assets matched criteria.</td></tr>';
      return;
    }

    tbody.innerHTML = assets.map(a => {
      let badgeClass = "badge-healthy";
      if (a.health_status === "CRITICAL") badgeClass = "badge-critical";
      else if (a.health_status === "HIGH") badgeClass = "badge-high";
      else if (a.health_status === "MODERATE") badgeClass = "badge-moderate";

      const probPct = a.failure_probability_pct ?? 0;
      let probClass = "badge-healthy";
      if (probPct >= 80) probClass = "badge-critical";
      else if (probPct >= 60) probClass = "badge-high";
      else if (probPct >= 30) probClass = "badge-moderate";

      const overdueDays = a.days_since_maintenance ?? 0;
      const overdueColor = overdueDays > 300 ? "var(--status-critical)" : (overdueDays > 200 ? "var(--status-moderate)" : "var(--text-secondary)");

      return `
        <tr>
          <td>
            <a href="asset-detail.html?id=${a.id}" style="color:#ffffff; font-weight:700; text-decoration:none; font-family:var(--font-mono);">
              ${a.asset_tag}
            </a>
          </td>
          <td>
            <div style="font-weight:600; color:#ffffff;">${a.name}</div>
            <div style="font-size:11px; color:var(--text-muted);">${a.substation}</div>
          </td>
          <td>
            <span class="badge ${badgeClass}">${a.health_status}</span>
          </td>
          <td style="font-family:var(--font-mono); font-weight:700;">
            ${a.current_risk_score}
          </td>
          <td>
            <span class="badge ${probClass}">${probPct}%</span>
          </td>
          <td style="font-family:var(--font-mono); font-size:12px;">
            ${a.rated_capacity_kva} kVA
          </td>
          <td style="font-size:12px; color:var(--text-secondary);">
            ${a.age_years} yrs
          </td>
          <td style="font-size:12px; font-family:var(--font-mono); color:${overdueColor};">
            ${overdueDays}d ago
          </td>
          <td style="font-size:12px; text-align:center;">
            ${a.previous_failure_count > 0 ? `<span style="color:var(--status-critical); font-weight:700;">${a.previous_failure_count}</span>` : '0'}
          </td>
          <td>
            <a href="asset-detail.html?id=${a.id}" class="btn btn-outline btn-sm">
              Profile →
            </a>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Error loading assets catalog:", err);
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; color:var(--status-critical);">Failed to load transformer catalog.</td></tr>';
  }
}

function setupModal() {
  const modal = document.getElementById("createAssetModal");
  const openBtn = document.getElementById("openCreateModalBtn");
  const closeBtn = document.getElementById("closeModalBtn");
  const cancelBtn = document.getElementById("cancelModalBtn");
  const form = document.getElementById("createAssetForm");

  const today = new Date().toISOString().split("T")[0];
  const dateInput = document.getElementById("newInstallDate");
  if (dateInput) dateInput.value = today;

  if (openBtn) {
    openBtn.addEventListener("click", () => modal.classList.add("open"));
  }
  const closeModal = () => modal.classList.remove("open");
  if (closeBtn) closeBtn.addEventListener("click", closeModal);
  if (cancelBtn) cancelBtn.addEventListener("click", closeModal);

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const newAsset = {
        asset_tag: document.getElementById("newTag").value.trim().toUpperCase(),
        name: document.getElementById("newName").value.trim(),
        substation: document.getElementById("newSubstation").value.trim(),
        location: document.getElementById("newLocation").value.trim(),
        manufacturer: document.getElementById("newMfr").value.trim(),
        model_number: document.getElementById("newModel").value.trim(),
        rated_capacity_kva: parseFloat(document.getElementById("newCapacity").value),
        installation_date: document.getElementById("newInstallDate").value,
      };

      try {
        await API.createAsset(newAsset);
        closeModal();
        form.reset();
        loadAssets();
      } catch (err) {
        alert(err.message || "Failed to create asset.");
      }
    });
  }
}
