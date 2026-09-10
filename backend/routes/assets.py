import json
from datetime import datetime, date
from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.models import (
    TransformerAsset,
    TelemetryReading,
    MaintenanceRecord,
    Inspection,
    IncidentReport,
    Alert,
    MaintenanceTask,
    RiskAssessment
)
from backend.routes.auth import login_required, roles_required
from backend.services.risk_engine import RiskEngine
from backend.services.prediction_engine import PredictionEngine

assets_bp = Blueprint("assets", __name__, url_prefix="/api/assets")


@assets_bp.route("", methods=["GET"])
def list_assets():
    """
    List transformer assets with flexible search, multi-factor filtering, and sorting.
    """
    query = TransformerAsset.query

    # Search filter
    search = request.args.get("search", "").strip()
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (TransformerAsset.asset_tag.ilike(search_fmt)) |
            (TransformerAsset.name.ilike(search_fmt)) |
            (TransformerAsset.substation.ilike(search_fmt)) |
            (TransformerAsset.location.ilike(search_fmt)) |
            (TransformerAsset.manufacturer.ilike(search_fmt))
        )

    # Health / Risk status filter
    health = request.args.get("health", "").strip().upper()
    if health and health in ["HEALTHY", "MODERATE", "HIGH", "CRITICAL"]:
        query = query.filter(TransformerAsset.health_status == health)

    # Operational status filter
    status = request.args.get("status", "").strip().upper()
    if status and status in ["OPERATIONAL", "MAINTENANCE_REQUIRED", "UNDER_MAINTENANCE", "DECOMMISSIONED"]:
        query = query.filter(TransformerAsset.current_status == status)

    # Substation filter
    substation = request.args.get("substation", "").strip()
    if substation:
        query = query.filter(TransformerAsset.substation.ilike(f"%{substation}%"))

    # Sorting
    sort_by = request.args.get("sort_by", "risk_desc").lower()
    if sort_by == "risk_desc":
        query = query.order_by(TransformerAsset.current_risk_score.desc())
    elif sort_by == "risk_asc":
        query = query.order_by(TransformerAsset.current_risk_score.asc())
    elif sort_by == "prob_desc":
        query = query.order_by(TransformerAsset.failure_probability.desc())
    elif sort_by == "prob_asc":
        query = query.order_by(TransformerAsset.failure_probability.asc())
    elif sort_by == "age_desc":
        query = query.order_by(TransformerAsset.installation_date.asc())  # oldest first
    elif sort_by == "failures_desc":
        query = query.order_by(TransformerAsset.previous_failure_count.desc())
    elif sort_by == "tag_asc":
        query = query.order_by(TransformerAsset.asset_tag.asc())
    else:
        query = query.order_by(TransformerAsset.current_risk_score.desc())

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    assets_list = [asset.to_dict(include_counts=True) for asset in pagination.items]

    return jsonify({
        "assets": assets_list,
        "pagination": {
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": pagination.page,
            "per_page": pagination.per_page,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        }
    }), 200


@assets_bp.route("/<int:asset_id>", methods=["GET"])
def get_asset(asset_id):
    """
    Get deep profile for a single transformer asset including telemetry,
    explainable risk factors, failure prediction, maintenance records, and alerts.
    """
    asset = db.session.get(TransformerAsset, asset_id)
    if not asset:
        return jsonify({"error": "Transformer asset not found."}), 404

    # Latest telemetry reading
    latest_telemetry_obj = asset.telemetry_readings.order_by(TelemetryReading.timestamp.desc()).first()
    latest_telemetry = latest_telemetry_obj.to_dict() if latest_telemetry_obj else None

    # Count recent incident reports
    recent_reports_count = asset.incident_reports.filter(
        IncidentReport.status.in_(["SUBMITTED", "REVIEWED"])
    ).count()

    # Re-evaluate explainable risk
    risk_analysis = RiskEngine.evaluate_asset_risk(
        asset,
        latest_telemetry=latest_telemetry,
        recent_reports_count=recent_reports_count
    )

    # ML Failure probability evaluation
    ml_features = {
        "temperature_c": latest_telemetry["temperature_c"] if latest_telemetry else 65.0,
        "vibration_mms": latest_telemetry["vibration_mms"] if latest_telemetry else 1.8,
        "load_pct": latest_telemetry["load_pct"] if latest_telemetry else 68.0,
        "age_years": asset.age_years,
        "previous_failures": asset.previous_failure_count,
        "days_since_maintenance": asset.days_since_maintenance,
        "oil_quality_index": 92.0,
    }
    prediction = PredictionEngine.predict_failure_probability(ml_features)

    # Related logs
    maintenance_records = [m.to_dict() for m in asset.maintenance_records.limit(10).all()]
    inspections = [i.to_dict() for i in asset.inspections.limit(10).all()]
    incident_reports = [r.to_dict() for r in asset.incident_reports.limit(10).all()]
    active_alerts = [a.to_dict() for a in asset.alerts.filter_by(status="ACTIVE").limit(10).all()]
    active_tasks = [t.to_dict() for t in asset.maintenance_tasks.filter(MaintenanceTask.status.notin_(["RESOLVED", "VERIFIED"])).limit(10).all()]

    return jsonify({
        "asset": asset.to_dict(include_counts=True),
        "latest_telemetry": latest_telemetry,
        "risk_analysis": risk_analysis,
        "ml_prediction": prediction,
        "maintenance_records": maintenance_records,
        "inspections": inspections,
        "incident_reports": incident_reports,
        "active_alerts": active_alerts,
        "active_tasks": active_tasks,
    }), 200


@assets_bp.route("", methods=["POST"])
@login_required
@roles_required("ADMIN")
def create_asset():
    """Create a new transformer asset (Admin only)."""
    data = request.get_json() or {}

    tag = data.get("asset_tag", "").strip().upper()
    name = data.get("name", "").strip()
    substation = data.get("substation", "").strip()
    location = data.get("location", "").strip()
    manufacturer = data.get("manufacturer", "").strip()
    model_number = data.get("model_number", "").strip()
    capacity = data.get("rated_capacity_kva")

    if not tag or not name or not substation or not location or not manufacturer or not model_number or not capacity:
        return jsonify({"error": "Missing required asset fields."}), 400

    if TransformerAsset.query.filter_by(asset_tag=tag).first():
        return jsonify({"error": f"Asset with tag '{tag}' already exists."}), 409

    inst_date = date.today()
    if data.get("installation_date"):
        try:
            inst_date = datetime.strptime(data["installation_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "installation_date must be in YYYY-MM-DD format."}), 400

    asset = TransformerAsset(
        asset_tag=tag,
        name=name,
        substation=substation,
        location=location,
        installation_date=inst_date,
        manufacturer=manufacturer,
        model_number=model_number,
        rated_capacity_kva=float(capacity),
        primary_voltage_kv=float(data.get("primary_voltage_kv", 33.0)),
        secondary_voltage_kv=float(data.get("secondary_voltage_kv", 11.0)),
        cooling_type=data.get("cooling_type", "ONAN"),
        current_status=data.get("current_status", "OPERATIONAL"),
        notes=data.get("notes")
    )
    db.session.add(asset)
    db.session.commit()

    return jsonify({
        "message": "Transformer asset created successfully.",
        "asset": asset.to_dict()
    }), 201


@assets_bp.route("/<int:asset_id>", methods=["PUT"])
@login_required
@roles_required("ADMIN")
def update_asset(asset_id):
    """Update transformer asset metadata (Admin only)."""
    asset = db.session.get(TransformerAsset, asset_id)
    if not asset:
        return jsonify({"error": "Transformer asset not found."}), 404

    data = request.get_json() or {}

    if "name" in data:
        asset.name = data["name"].strip()
    if "substation" in data:
        asset.substation = data["substation"].strip()
    if "location" in data:
        asset.location = data["location"].strip()
    if "current_status" in data:
        asset.current_status = data["current_status"].strip().upper()
    if "rated_capacity_kva" in data:
        asset.rated_capacity_kva = float(data["rated_capacity_kva"])
    if "notes" in data:
        asset.notes = data["notes"]
    if "previous_failure_count" in data:
        asset.previous_failure_count = int(data["previous_failure_count"])

    db.session.commit()

    return jsonify({
        "message": "Asset updated successfully.",
        "asset": asset.to_dict()
    }), 200


@assets_bp.route("/<int:asset_id>", methods=["DELETE"])
@login_required
@roles_required("ADMIN")
def delete_asset(asset_id):
    """Delete transformer asset (Admin only)."""
    asset = db.session.get(TransformerAsset, asset_id)
    if not asset:
        return jsonify({"error": "Transformer asset not found."}), 404

    tag = asset.asset_tag
    db.session.delete(asset)
    db.session.commit()

    return jsonify({"message": f"Asset {tag} deleted successfully."}), 200
