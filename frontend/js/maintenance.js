/**
 * FaultLens Maintenance Action Tracker Controller
 * Handles 7-Stage Industrial Workflow State Transitions
 */

const WORKFLOW_ORDER = [
  "DETECTED",
  "RISK_ASSESSED",
  "INSPECTION_REQUIRED",
  "ASSIGNED",
  "IN_PROGRESS",
  "RESOLVED",
  "VERIFIED"
];

document.addEventListener("DOMContentLoaded", () => {
  loadTasks();
  setupFilters();
  setupTaskModal();
});

async function loadTasks() {
  const tbody = document.getElementById("tasksTableBody");
  if (!tbody) return;

  const status = document.getElementById("taskStatusFilter").value;
  const priority = document.getElementById("taskPriorityFilter").value;

  try {
    const res = await API.getTasks({ status, priority });
    const tasks = res.tasks || [];
    const counts = res.status_counts || {};

    // Render 7-stage summary bar
    renderWorkflowBar(counts);

    document.getElementById("tasksCountLabel").textContent = `Showing ${tasks.length} total work orders`;

    if (!tasks.length) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">No maintenance tasks match criteria.</td></tr>';
      return;
    }

    tbody.innerHTML = tasks.map(t => {
      const priorityClass = t.priority === "CRITICAL" ? "badge-critical" : (t.priority === "HIGH" ? "badge-high" : "badge-moderate");
      const currentIdx = WORKFLOW_ORDER.indexOf(t.status);
      const nextStage = currentIdx >= 0 && currentIdx < WORKFLOW_ORDER.length - 1 ? WORKFLOW_ORDER[currentIdx + 1] : null;

      let actionBtn = "";
      if (nextStage) {
        let label = `Advance to ${nextStage.replace("_", " ")}`;
        if (nextStage === "RESOLVED") label = "Mark Resolved";
        else if (nextStage === "VERIFIED") label = "Verify (Admin)";
        else if (nextStage === "IN_PROGRESS") label = "Start Work";

        actionBtn = `
          <button class="btn btn-outline btn-sm" onclick="advanceTask(${t.id}, '${nextStage}')">
            ${label} →
          </button>
        `;
      } else {
        actionBtn = `<span class="badge badge-healthy" style="font-size:10px;">✓ Complete</span>`;
      }

      return `
        <tr>
          <td style="font-family:var(--font-mono); font-weight:700; color:var(--accent-cyan);">
            ${t.task_code}
          </td>
          <td>
            <a href="asset-detail.html?id=${t.asset_id}" style="color:#ffffff; font-weight:600; text-decoration:none;">
              ${t.asset_tag}
            </a>
          </td>
          <td style="max-width:240px;">
            <div style="font-weight:600; color:#ffffff;">${t.title}</div>
            <div style="font-size:11px; color:var(--text-muted);">${t.notes || "No notes"}</div>
          </td>
          <td>
            <span class="badge ${priorityClass}">${t.priority}</span>
          </td>
          <td style="font-size:12px;">
            ${t.assigned_to_name || '<span style="color:var(--text-muted);">Unassigned</span>'}
          </td>
          <td>
            <span class="badge badge-cyan" style="font-size:10px;">
              ${t.status.replace("_", " ")}
            </span>
          </td>
          <td style="font-size:12px; font-family:var(--font-mono); color:var(--text-secondary);">
            ${t.due_date || "Open"}
          </td>
          <td>
            ${actionBtn}
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.error("Error loading maintenance tasks:", err);
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--status-critical);">Failed to load tasks.</td></tr>';
  }
}

function renderWorkflowBar(counts) {
  const bar = document.getElementById("workflowProgressBar");
  if (!bar) return;

  bar.innerHTML = WORKFLOW_ORDER.map((stage, idx) => {
    const c = counts[stage] || 0;
    return `
      <div class="stage-pill ${c > 0 ? 'active' : ''}">
        <span>${idx + 1}. ${stage.replace("_", " ")}</span>
        <span class="stage-count">${c}</span>
      </div>
    `;
  }).join("");
}

function setupFilters() {
  document.getElementById("taskStatusFilter").addEventListener("change", loadTasks);
  document.getElementById("taskPriorityFilter").addEventListener("change", loadTasks);
}

async function advanceTask(taskId, nextStage) {
  let notes = "";
  if (nextStage === "RESOLVED") {
    notes = prompt("Enter resolution summary notes for this maintenance task:", "Repairs successfully verified. Re-energized and monitored within nominal telemetry tolerances.");
    if (notes === null) return;
  }

  try {
    await API.updateTaskStatus(taskId, nextStage, notes);
    await loadTasks();
  } catch (err) {
    alert(err.message || "Failed to update task workflow status.");
  }
}

async function setupTaskModal() {
  const modal = document.getElementById("createTaskModal");
  const openBtn = document.getElementById("openCreateTaskBtn");
  const closeBtn = document.getElementById("closeTaskModalBtn");
  const cancelBtn = document.getElementById("cancelTaskModalBtn");
  const form = document.getElementById("createTaskForm");
  const assetSelect = document.getElementById("taskAssetSelect");

  // Populate assets for dropdown
  try {
    const res = await API.getAssets({ per_page: 50 });
    const assets = res.assets || [];
    assetSelect.innerHTML = '<option value="">Select an asset...</option>' + assets.map(a => `
      <option value="${a.id}">${a.asset_tag} — ${a.name} [Risk: ${a.current_risk_score}]</option>
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
        asset_id: parseInt(assetSelect.value, 10),
        title: document.getElementById("taskTitle").value.trim(),
        priority: document.getElementById("taskPriority").value,
        due_date: document.getElementById("taskDueDate").value || null,
        notes: document.getElementById("taskNotes").value.trim()
      };

      try {
        await API.createTask(payload);
        closeModal();
        form.reset();
        await loadTasks();
      } catch (err) {
        alert(err.message || "Failed to create task.");
      }
    });
  }
}

window.advanceTask = advanceTask;
