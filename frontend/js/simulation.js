/**
 * FaultLens What-If Simulator Controller
 */

let currentSimAssetId = null;
let simDebounceTimer = null;

document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const targetId = urlParams.get("asset_id");

  await populateAssetDropdown(targetId);
  setupSliders();
  triggerSimulation();

  document.getElementById("resetScenarioBtn").addEventListener("click", () => {
    document.getElementById("sliderLoad").value = 0;
    document.getElementById("sliderTemp").value = 0;
    document.getElementById("sliderVib").value = 0;
    document.getElementById("sliderMaint").value = 0;
    document.getElementById("sliderFaults").value = 0;
    updateSliderLabels();
    triggerSimulation();
  });
});

async function populateAssetDropdown(targetId) {
  const select = document.getElementById("simAssetSelect");
  try {
    const res = await API.getAssets({ per_page: 50 });
    const assets = res.assets || [];

    if (!assets.length) {
      select.innerHTML = '<option value="">Generic Synthetic Transformer (Default Baseline)</option>';
      currentSimAssetId = null;
    } else {
      select.innerHTML = assets.map(a => `
        <option value="${a.id}">${a.asset_tag} — ${a.name} (${a.substation}) [Risk: ${a.current_risk_score}]</option>
      `).join("");

      if (targetId && assets.some(a => a.id == targetId)) {
        select.value = targetId;
        currentSimAssetId = targetId;
      } else {
        currentSimAssetId = assets[0].id;
      }
    }

    select.addEventListener("change", () => {
      currentSimAssetId = select.value || null;
      triggerSimulation();
    });
  } catch (err) {
    console.error("Error populating asset select:", err);
  }
}

function setupSliders() {
  const sliders = ["sliderLoad", "sliderTemp", "sliderVib", "sliderMaint", "sliderFaults"];
  sliders.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", () => {
        updateSliderLabels();
        clearTimeout(simDebounceTimer);
        simDebounceTimer = setTimeout(triggerSimulation, 150);
      });
    }
  });
  updateSliderLabels();
}

function updateSliderLabels() {
  const load = parseInt(document.getElementById("sliderLoad").value, 10);
  const temp = parseInt(document.getElementById("sliderTemp").value, 10);
  const vib = parseFloat(document.getElementById("sliderVib").value);
  const maint = parseInt(document.getElementById("sliderMaint").value, 10);
  const faults = parseInt(document.getElementById("sliderFaults").value, 10);

  document.getElementById("valLoadDelta").textContent = `${load >= 0 ? "+" : ""}${load}%`;
  document.getElementById("valTempDelta").textContent = `${temp >= 0 ? "+" : ""}${temp}°C`;
  document.getElementById("valVibDelta").textContent = `${vib >= 0 ? "+" : ""}${vib.toFixed(1)} mm/s`;
  document.getElementById("valMaintDelta").textContent = `+${maint} days`;
  document.getElementById("valFaultsDelta").textContent = `+${faults} fault${faults === 1 ? "" : "s"}`;
}

async function triggerSimulation() {
  const payload = {
    delta_load_pct: parseFloat(document.getElementById("sliderLoad").value),
    delta_temp_c: parseFloat(document.getElementById("sliderTemp").value),
    delta_vibration_mms: parseFloat(document.getElementById("sliderVib").value),
    delta_maint_days: parseInt(document.getElementById("sliderMaint").value, 10),
    delta_faults: parseInt(document.getElementById("sliderFaults").value, 10),
  };

  if (currentSimAssetId) {
    payload.asset_id = parseInt(currentSimAssetId, 10);
  } else {
    payload.base_temp = 65.0;
    payload.base_vib = 1.8;
    payload.base_load = 68.0;
    payload.base_days_maint = 120;
    payload.base_faults = 0;
  }

  try {
    const res = await API.simulateWhatIf(payload);
    const b = res.baseline || {};
    const s = res.scenario || {};
    const d = res.deltas || {};

    // Delta Banner
    const riskDeltaEl = document.getElementById("deltaRiskScore");
    riskDeltaEl.textContent = `${d.risk_score_change >= 0 ? "+" : ""}${d.risk_score_change}`;
    riskDeltaEl.style.color = d.risk_score_change > 0 ? "var(--status-critical)" : "var(--status-healthy)";

    const probDeltaEl = document.getElementById("deltaProbPct");
    probDeltaEl.textContent = `${d.failure_probability_pct_change >= 0 ? "+" : ""}${d.failure_probability_pct_change}%`;

    const healthEl = document.getElementById("deltaHealthStatus");
    healthEl.textContent = s.health_status;
    healthEl.style.color = getHealthColor(s.health_status);

    // Baseline Card
    document.getElementById("baseRiskScore").textContent = b.risk_score;
    document.getElementById("baseProbPct").textContent = `${b.failure_probability_pct}%`;
    document.getElementById("baseTemp").textContent = `${b.temperature_c}°C`;
    document.getElementById("baseLoad").textContent = `${b.load_pct}%`;
    document.getElementById("baseVib").textContent = `${b.vibration_mms} mm/s`;
    document.getElementById("baseMaint").textContent = `${b.days_since_maintenance} days`;

    const baseBadge = document.getElementById("baseHealthBadge");
    baseBadge.textContent = b.health_status;
    baseBadge.className = `badge ${getBadgeClass(b.health_status)}`;

    // Projected Card
    document.getElementById("projRiskScore").textContent = s.risk_score;
    document.getElementById("projProbPct").textContent = `${s.failure_probability_pct}%`;
    document.getElementById("projTemp").textContent = `${s.temperature_c}°C`;
    document.getElementById("projLoad").textContent = `${s.load_pct}%`;
    document.getElementById("projVib").textContent = `${s.vibration_mms} mm/s`;
    document.getElementById("projMaint").textContent = `${s.days_since_maintenance} days`;

    const projBadge = document.getElementById("projHealthBadge");
    projBadge.textContent = s.health_status;
    projBadge.className = `badge ${getBadgeClass(s.health_status)}`;

    // Projected Recommendations
    const recsContainer = document.getElementById("simRecsContainer");
    if (recsContainer && s.recommendations) {
      recsContainer.innerHTML = s.recommendations.map(r => `
        <div style="padding:8px 12px; background:var(--bg-secondary); border-left:3px solid var(--accent-cyan); border-radius:4px; font-size:12px;">
          <div style="font-weight:700; color:#ffffff;">${r.action} (${r.urgency})</div>
          <div style="color:var(--text-secondary); font-size:11px;">${r.rationale}</div>
        </div>
      `).join("");
    }

  } catch (err) {
    console.error("Error in simulation execution:", err);
  }
}

function getBadgeClass(status) {
  switch (status) {
    case "CRITICAL": return "badge-critical";
    case "HIGH": return "badge-high";
    case "MODERATE": return "badge-moderate";
    default: return "badge-healthy";
  }
}

function getHealthColor(status) {
  switch (status) {
    case "CRITICAL": return "var(--status-critical)";
    case "HIGH": return "var(--status-high)";
    case "MODERATE": return "var(--status-moderate)";
    default: return "var(--status-healthy)";
  }
}
