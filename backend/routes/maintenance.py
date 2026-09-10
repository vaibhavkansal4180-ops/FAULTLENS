import random
from datetime import datetime, date, timezone
from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.models import MaintenanceTask, MaintenanceRecord, TransformerAsset, User
from backend.routes.auth import login_required, roles_required, get_current_user

maintenance_bp = Blueprint("maintenance", __name__, url_prefix="/api/maintenance")


@maintenance_bp.route("/tasks", methods=["GET"])
def list_tasks():
    """List maintenance workflow tasks with filtering by status, priority, and asset."""
    query = MaintenanceTask.query

    status = request.args.get("status", "").strip().upper()
    if status and status in MaintenanceTask.WORKFLOW_STAGES:
        query = query.filter(MaintenanceTask.status == status)

    priority = request.args.get("priority", "").strip().upper()
    if priority and priority in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        query = query.filter(MaintenanceTask.priority == priority)

    asset_id = request.args.get("asset_id", type=int)
    if asset_id:
        query = query.filter(MaintenanceTask.asset_id == asset_id)

    tasks = query.order_by(MaintenanceTask.created_at.desc()).all()
    tasks_data = [t.to_dict() for t in tasks]

    # Compute workflow breakdown statistics
    status_counts = {stage: 0 for stage in MaintenanceTask.WORKFLOW_STAGES}
    for t in tasks_data:
        stage = t["status"]
        if stage in status_counts:
            status_counts[stage] += 1

    return jsonify({
        "tasks": tasks_data,
        "workflow_stages": MaintenanceTask.WORKFLOW_STAGES,
        "status_counts": status_counts,
        "total_tasks": len(tasks_data)
    }), 200


@maintenance_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    """Retrieve details of a single maintenance task."""
    task = db.session.get(MaintenanceTask, task_id)
    if not task:
        return jsonify({"error": "Maintenance task not found."}), 404
    return jsonify({"task": task.to_dict()}), 200


@maintenance_bp.route("/tasks", methods=["POST"])
@login_required
@roles_required("ADMIN", "TECHNICIAN")
def create_task():
    """Create a new maintenance action task."""
    data = request.get_json() or {}
    asset_id = data.get("asset_id")
    title = data.get("title", "").strip()
    priority = data.get("priority", "MEDIUM").upper()
    assigned_to_id = data.get("assigned_to_id")
    notes = data.get("notes", "")

    if not asset_id or not title:
        return jsonify({"error": "asset_id and title are required."}), 400

    asset = db.session.get(TransformerAsset, asset_id)
    if not asset:
        return jsonify({"error": "Asset not found."}), 404

    assignee_name = None
    if assigned_to_id:
        assignee = db.session.get(User, assigned_to_id)
        if assignee:
            assignee_name = assignee.full_name or assignee.username

    # Generate unique task code
    task_num = MaintenanceTask.query.count() + 101
    task_code = f"TASK-{date.today().year}-{task_num:03d}"

    due_date = None
    if data.get("due_date"):
        try:
            due_date = datetime.strptime(data["due_date"], "%Y-%m-%d").date()
        except ValueError:
            pass

    initial_status = "ASSIGNED" if assigned_to_id else "DETECTED"

    task = MaintenanceTask(
        task_code=task_code,
        asset_id=asset.id,
        title=title,
        priority=priority if priority in ["LOW", "MEDIUM", "HIGH", "CRITICAL"] else "MEDIUM",
        assigned_to_id=assigned_to_id,
        assigned_to_name=assignee_name,
        status=initial_status,
        due_date=due_date,
        notes=notes
    )
    db.session.add(task)
    db.session.commit()

    return jsonify({
        "message": "Maintenance task created successfully.",
        "task": task.to_dict()
    }), 201


@maintenance_bp.route("/tasks/<int:task_id>/status", methods=["PUT"])
@login_required
@roles_required("ADMIN", "TECHNICIAN")
def update_task_status(task_id):
    """
    Progresses task along the 7-stage workflow:
    DETECTED -> RISK_ASSESSED -> INSPECTION_REQUIRED -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> VERIFIED
    """
    task = db.session.get(MaintenanceTask, task_id)
    if not task:
        return jsonify({"error": "Maintenance task not found."}), 404

    user = get_current_user()
    data = request.get_json() or {}
    new_status = data.get("status", "").strip().upper()

    if new_status not in MaintenanceTask.WORKFLOW_STAGES:
        return jsonify({
            "error": f"Invalid status. Allowed values: {MaintenanceTask.WORKFLOW_STAGES}"
        }), 400

    # Role enforcement for verification stage
    if new_status == "VERIFIED" and user.role != "ADMIN":
        return jsonify({"error": "Only Administrators can mark tasks as VERIFIED."}), 403

    task.status = new_status

    if "resolution_notes" in data:
        task.resolution_notes = data["resolution_notes"]

    if new_status == "RESOLVED" and not task.resolution_notes:
        task.resolution_notes = data.get("notes") or "Work completed by technician."

    if new_status == "VERIFIED":
        task.verified_by_id = user.id
        task.verified_by_name = user.full_name or user.username
        task.verified_at = datetime.now(timezone.utc)

        # Also log a completed MaintenanceRecord if resolving/verifying
        asset = task.asset
        if asset:
            record = MaintenanceRecord(
                asset_id=asset.id,
                maintenance_type="CORRECTIVE" if task.priority in ["HIGH", "CRITICAL"] else "PREVENTIVE",
                performed_by=task.assigned_to_name or user.full_name or "Technician",
                date_performed=date.today(),
                notes=f"Resolved task {task.task_code}: {task.title}. Resolution: {task.resolution_notes}",
                cost_usd=float(data.get("cost_usd", 1200.0)),
                downtime_hours=float(data.get("downtime_hours", 2.5))
            )
            db.session.add(record)
            asset.last_maintenance_date = date.today()

    db.session.commit()

    return jsonify({
        "message": f"Task status updated to {new_status}.",
        "task": task.to_dict()
    }), 200


@maintenance_bp.route("/records", methods=["GET"])
def list_records():
    """Retrieve chronological maintenance intervention history."""
    asset_id = request.args.get("asset_id", type=int)
    query = MaintenanceRecord.query
    if asset_id:
        query = query.filter_by(asset_id=asset_id)

    records = query.order_by(MaintenanceRecord.date_performed.desc()).limit(50).all()
    return jsonify({
        "records": [r.to_dict() for r in records],
        "total": len(records)
    }), 200
