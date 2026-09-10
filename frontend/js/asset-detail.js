/**
 * FaultLens Asset Deep Profile & Telemetry Chart Controller
 * Pure Vanilla JavaScript & Zero-dependency SVG Sparkline Rendering
 */

let currentAssetId = null;

document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  currentAssetId = urlParams.get("id") || 1;

  document.getElementById("openSimulatorForAssetBtn").href = `simulation.html?asset_id=${currentAssetId}`;

  await loadAssetProfile();
  await loadAssetTelemetry();

  // Ingest live telemetry simulation button
  const simBtn = document.getElementById("triggerSimReadingBtn");
  if (simBtn) {
    simBtn.addEventListener("click", async () => {
      simBtn.disabled = true;
      simBtn.textContent = "⚡ Ingesting Stream...";
      try {
        await API.generateTelemetry(currentAssetId);
        await loadAssetProfile();
        await loadAssetTelemetry();
      } catch (err) {
        alert(err.message || "Failed to generate live telemetry.");
      } finally {
        simBtn.disabled = false;
        simBtn.textContent = "⚡ Ingest Live Telemetry";
      }
    });
  }
});

async function loadAssetProfile() {
  try {
    const data = await API.getAsset(currentAssetId);
    const a = data.asset || {};
    const risk = data.risk_analysis || {};
    const ml = data.ml_prediction || {};

    // Header & Badges
    document.getElementById("headerAssetTag").textContent = `${a.asset_tag} — Deep Profile`;
    document.getElementById("detailAssetTag").textContent = a.asset_tag;
    document.getElementById("detailAssetName").textContent = a.name;
    document.getElementById("detailSubstation").textContent = `${a.substation} • ${a.location}`;
    document.getElementById("detailRiskScore").textContent = a.current_risk_score;
    document.getElementById("detailProbScore").textContent = `${a.failure_probability_pct}%`;

    const healthBadge = document.getElementById("detailHealthBadge");
    healthBadge.textContent = a.health_status;
    healthBadge.className = `badge ${getBadgeClass(a.health_status)}`;

    document.getElementById("detailOpStatus").textContent = a.current_status.replace("_", " ");

    // Metadata Grid
    document.getElementById("metaCapacity").textContent = `${a.rated_capacity_kva} kVA`;
    document.getElementById("metaAge").textContent = `${a.age_years} yrs`;
    document.getElementById("metaMfr").textContent = `${a.manufacturer} (${a.model_number})`;
    document.getElementById("metaCooling").textContent = a.cooling_type;
    document.getElementById("metaLastMaint").textContent = `${a.days_since_maintenance}d ago`;
    document.getElementById("metaFaults").textContent = `${a.previous_failure_count} breakdowns`;

    // Render Explainable Risk Factor Breakdown Table
    renderExplainableRisk(risk.factors || [], a.current_risk_score);

    // Render ML Feature Attribution Table
    renderMLContributions(ml.feature_contributions || []);

    // Render System Recommendations
    renderRecommendations(risk.recommendations || []);

    // Render Historical Logs
    renderHistoryLogs(data.maintenance_records || [], data.inspections || []);

  } catch (err) {
    console.error("Error loading asset profile:", err);
  }
}

async function loadAssetTelemetry() {
  try {
    const res = await API.getTelemetry(currentAssetId, 36);
    const readings = res.readings || [];
    const summary = res.summary || {};

    if (!readings.length) return;

    const latest = readings[readings.length - 1];
    document.getElementById("liveTemp").textContent = `${latest.temperature_c}°C`;
    document.getElementById("liveLoad").textContent = `${latest.load_pct}%`;
    document.getElementById("liveVib").textContent = `${latest.vibration_mms} mm/s`;
    document.getElementById("liveOil").textContent = `${latest.oil_level_pct}%`;

    // Update Stats Strings
    document.getElementById("chartTempStats").textContent = `Avg: ${summary.avg_temperature_c}°C | Max: ${summary.max_temperature_c}°C`;
    document.getElementById("chartLoadStats").textContent = `Avg: ${summary.avg_load_pct}% | Max: ${summary.max_load_pct}%`;
    document.getElementById("chartVibStats").textContent = `Avg: ${summary.avg_vibration_mms} mm/s | Max: ${summary.max_vibration_mms} mm/s`;

    // Render Pure SVG Charts
    drawSvgChart("svgTempChart", readings.map(r => r.temperature_c), "#ff9100", 30, 110, "°C");
    drawSvgChart("svgLoadChart", readings.map(r => r.load_pct), "#00e5ff", 20, 125, "%");
    drawSvgChart("svgVibChart", readings.map(r => r.vibration_mms), "#b388ff", 0.5, 6.0, "mm/s");

  } catch (err) {
    console.error("Error loading telemetry series:", err);
  }
}

/**
 * Pure SVG responsive line chart generator with baseline reference & area fill
 */
function drawSvgChart(svgId, dataPoints, strokeColor, minY, maxY, unit) {
  const svg = document.getElementById(svgId);
  if (!svg || dataPoints.length < 2) return;

  const width = 600;
  const height = 120;
  const padding = 15;

  const plotW = width - padding * 2;
  const plotH = height - padding * 2;

  const min = Math.min(minY, Math.min(...dataPoints));
  const max = Math.max(maxY, Math.max(...dataPoints));
  const range = max - min || 1;

  const points = dataPoints.map((val, idx) => {
    const x = padding + (idx / (dataPoints.length - 1)) * plotW;
    const y = height - padding - ((val - min) / range) * plotH;
    return { x: x.toFixed(1), y: y.toFixed(1), val };
  });

  const polylineStr = points.map(p => `${p.x},${p.y}`).join(" ");
  const areaStr = `${points[0].x},${height - padding} ${polylineStr} ${points[points.length - 1].x},${height - padding}`;

  svg.innerHTML = `
    <defs>
      <linearGradient id="grad-${svgId}" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="${strokeColor}" stop-opacity="0.35" />
        <stop offset="100%" stop-color="${strokeColor}" stop-opacity="0.0" />
      </linearGradient>
    </defs>
    <!-- Background Grid Lines -->
    <line x1="${padding}" y1="${padding}" x2="${width - padding}" y2="${padding}" stroke="#1a2744" stroke-dasharray="3,3" />
    <line x1="${padding}" y1="${height / 2}" x2="${width - padding}" y2="${height / 2}" stroke="#1a2744" stroke-dasharray="3,3" />
    <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="#1a2744" />
    
    <!-- Area & Line -->
    <polygon points="${areaStr}" fill="url(#grad-${svgId})" />
    <polyline fill="none" stroke="${strokeColor}" stroke-width="2" points="${polylineStr}" stroke-linecap="round" stroke-linejoin="round" />
    
    <!-- Current Endpoint Dot -->
    <circle cx="${points[points.length - 1].x}" cy="${points[points.length - 1].y}" r="4" fill="${strokeColor}" />
    <text x="${points[points.length - 1].x - 10}" y="${points[points.length - 1].y - 8}" fill="#ffffff" font-size="10" font-family="monospace" font-weight="bold">${points[points.length - 1].val}${unit}</text>
  `;
}

function renderExplainableRisk(factors, totalScore) {
  const container = document.getElementById("riskFactorsContainer");
  if (!container) return;

  container.innerHTML = factors.map(f => {
    let badgeClass = "badge-healthy";
    if (f.severity === "CRITICAL") badgeClass = "badge-critical";
    else if (f.severity === "HIGH") badgeClass = "badge-high";
    else if (f.severity === "MODERATE") badgeClass = "badge-moderate";

    return `
      <div style="padding:10px 14px; background:var(--bg-secondary); border:1px solid var(--border-dim); border-radius:var(--radius-md); display:flex; flex-direction:column; gap:4px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="font-weight:700; color:#ffffff; font-size:13px; display:flex; align-items:center; gap:8px;">
            <span>${f.name}</span>
            <span class="badge ${badgeClass}" style="font-size:10px;">${f.severity}</span>
          </div>
          <div style="font-family:var(--font-mono); font-weight:800; color:var(--accent-cyan); font-size:14px;">
            +${f.impact}
          </div>
        </div>
        <div style="font-size:12px; color:var(--text-secondary);">${f.rationale}</div>
        <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">Observed Metric: ${f.metric_value}</div>
      </div>
    `;
  }).join("") + `
    <div style="display:flex; justify-content:space-between; padding:12px 14px; background:var(--bg-tertiary); border-radius:var(--radius-md); border:1px solid var(--border-bright); margin-top:4px;">
      <span style="font-weight:800; text-transform:uppercase; letter-spacing:1px; color:#ffffff;">Composite Risk Total</span>
      <span style="font-family:var(--font-mono); font-weight:900; font-size:16px; color:#ffffff;">${totalScore} / 100</span>
    </div>
  `;
}

function renderMLContributions(contributions) {
  const container = document.getElementById("mlContributionsContainer");
  if (!container) return;

  container.innerHTML = contributions.slice(0, 5).map(c => {
    const isInc = c.direction === "RISK_INCREASE";
    const color = isInc ? "var(--status-critical)" : "var(--status-healthy)";
    const sign = c.importance_score > 0 ? `+${c.importance_score}` : `${c.importance_score}`;

    return `
      <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; padding:6px 0; border-bottom:1px solid var(--border-dim);">
        <div>
          <span style="font-weight:600; color:#ffffff;">${c.feature}</span>
          <span style="color:var(--text-muted); font-family:var(--font-mono); margin-left:6px;">(${c.value})</span>
        </div>
        <div style="font-family:var(--font-mono); font-weight:700; color:${color};">
          ${sign}
        </div>
      </div>
    `;
  }).join("");
}

function renderRecommendations(recs) {
  const container = document.getElementById("recommendationsContainer");
  if (!container) return;

  container.innerHTML = recs.map(r => `
    <div style="padding:12px; background:var(--bg-secondary); border-left:3px solid var(--accent-cyan); border-radius:0 var(--radius-md) var(--radius-md) 0;">
      <div style="font-size:11px; font-family:var(--font-mono); color:var(--accent-cyan); font-weight:700; text-transform:uppercase;">
        Directive [${r.urgency}]
      </div>
      <div style="font-size:13px; font-weight:700; color:#ffffff; margin:2px 0;">${r.action}</div>
      <div style="font-size:12px; color:var(--text-secondary);">${r.rationale}</div>
    </div>
  `).join("");
}

function renderHistoryLogs(maintRecords, inspections) {
  const tbody = document.getElementById("maintenanceHistoryBody");
  if (!tbody) return;

  const combined = [
    ...maintRecords.map(m => ({
      date: m.date_performed,
      type: `Maintenance: ${m.maintenance_type}`,
      actor: m.performed_by,
      notes: m.notes,
      downtime: `${m.downtime_hours}h ($${m.cost_usd})`,
    })),
    ...inspections.map(i => ({
      date: i.inspection_date,
      type: `Inspection: ${i.thermal_imaging_status}`,
      actor: i.inspector_name,
      notes: `${i.findings} (Oil Index: ${i.oil_quality_index}/100)`,
      downtime: "Routine",
    }))
  ];

  combined.sort((a, b) => new Date(b.date) - new Date(a.date));

  if (!combined.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">No records found.</td></tr>';
    return;
  }

  tbody.innerHTML = combined.slice(0, 10).map(row => `
    <tr>
      <td style="font-family:var(--font-mono); font-size:12px;">${row.date}</td>
      <td style="font-weight:600; font-size:12px; color:var(--accent-cyan);">${row.type}</td>
      <td style="font-size:12px;">${row.actor}</td>
      <td style="font-size:12px; color:var(--text-secondary); max-width:280px;">${row.notes}</td>
      <td style="font-size:12px; font-family:var(--font-mono);">${row.downtime}</td>
    </tr>
  `).join("");
}

function getBadgeClass(status) {
  switch (status) {
    case "CRITICAL": return "badge-critical";
    case "HIGH": return "badge-high";
    case "MODERATE": return "badge-moderate";
    default: return "badge-healthy";
  }
}
