from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.models import IncidentReport, Alert, TransformerAsset, User, TelemetryReading
from backend.routes.auth import login_required, get_current_user
from backend.services.risk_engine import RiskEngine

reports_bp = Blueprint("reports", __name__, url_prefix="/api")


@reports_bp.route("/reports", methods=["GET"])
def list_reports():
    """List incident reports with asset and category filtering."""
    query = IncidentReport.query
    asset_id = request.args.get("asset_id", type=int)
    if asset_id:
        query = query.filter_by(asset_id=asset_id)

    category = request.args.get("category", "").strip().upper()
    if category:
        query = query.filter(IncidentReport.category == category)

    severity = request.args.get("severity", "").strip().upper()
    if severity:
        query = query.filter(IncidentReport.severity == severity)

    reports = query.order_by(IncidentReport.reported_at.desc()).limit(100).all()

    return jsonify({
        "reports": [r.to_dict() for r in reports],
        "total": len(reports)
    }), 200


@reports_bp.route("/reports", methods=["POST"])
@login_required
def create_report():
    """
    Submits a technician field observation or incident report.
    Directly feeds into asset risk reassessment and triggers alerts if severe or recurrent.
    """
    user = get_current_user()
    data = request.get_json() or {}

    asset_id = data.get("asset_id")
    category = data.get("category", "OTHER").strip().upper()
    severity = data.get("severity", "MEDIUM").strip().upper()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()

    if not asset_id or not title or not description:
        return jsonify({"error": "asset_id, title, and description are required."}), 400

    asset = db.session.get(TransformerAsset, asset_id)
    if not asset:
        return jsonify({"error": "Transformer asset not found."}), 404

    valid_categories = ["TEMPERATURE", "VOLTAGE", "VIBRATION", "PHYSICAL_DAMAGE", "NOISE", "OIL_LEAK", "OTHER"]
    if category not in valid_categories:
        category = "OTHER"

    if severity not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        severity = "MEDIUM"

    report = IncidentReport(
        asset_id=asset.id,
        reporter_id=user.id if user else None,
        reporter_name=(user.full_name or user.username) if user else (data.get("reporter_name") or "Field Technician"),
        category=category,
        severity=severity,
        title=title,
        description=description,
        status="SUBMITTED",
        reported_at=datetime.now(timezone.utc)
    )
    db.session.add(report)

    # Count recent incident reports for this asset to evaluate density signal
    recent_reports_count = IncidentReport.query.filter_by(asset_id=asset.id).count() + 1

    # Check latest telemetry for risk engine
    latest_telemetry_obj = asset.telemetry_readings.order_by(TelemetryReading.timestamp.desc()).first()
    latest_telemetry = latest_telemetry_obj.to_dict() if latest_telemetry_obj else None

    # Recompute risk with new incident density signal
    risk_res = RiskEngine.evaluate_asset_risk(
        asset,
        latest_telemetry=latest_telemetry,
        recent_reports_count=recent_reports_count
    )
    asset.current_risk_score = risk_res["overall_risk_score"]
    asset.health_status = risk_res["health_status"]

    # Trigger alerts for critical/high severity reports or recurrent incidents
    generated_alerts = []
    if severity in ["HIGH", "CRITICAL"]:
        alert = Alert(
            asset_id=asset.id,
            severity="CRITICAL" if severity == "CRITICAL" else "WARNING",
            alert_type="RAPID_RISK_SURGE",
            title=f"Incident Escalation on {asset.asset_tag}: {title}",
            message=f"Field report ({severity}) filed: {description}. Risk adjusted to {asset.current_risk_score:.1f}."
        )
        db.session.add(alert)
        generated_alerts.append(alert)

    if recent_reports_count >= 3:
        multi_alert = Alert(
            asset_id=asset.id,
            severity="WARNING",
            alert_type="MULTIPLE_INCIDENTS",
            title=f"High Incident Frequency on {asset.asset_tag}",
            message=f"Asset has accumulated {recent_reports_count} field incident reports. Recurring fault risk."
        )
        db.session.add(multi_alert)
        generated_alerts.append(multi_alert)

    db.session.commit()

    return jsonify({
        "message": "Incident report submitted and risk evaluated.",
        "report": report.to_dict(),
        "updated_risk_score": asset.current_risk_score,
        "health_status": asset.health_status,
        "alerts_triggered": [a.to_dict() for a in generated_alerts]
    }), 201


@reports_bp.route("/alerts", methods=["GET"])
def list_alerts():
    """List operational alerts with status and severity filters."""
    query = Alert.query

    status = request.args.get("status", "").strip().upper()
    if status and status in ["ACTIVE", "ACKNOWLEDGED", "RESOLVED"]:
        query = query.filter(Alert.status == status)

    severity = request.args.get("severity", "").strip().upper()
    if severity and severity in ["INFO", "WARNING", "HIGH", "CRITICAL"]:
        query = query.filter(Alert.severity == severity)

    asset_id = request.args.get("asset_id", type=int)
    if asset_id:
        query = query.filter(Alert.asset_id == asset_id)

    alerts = query.order_by(Alert.triggered_at.desc()).limit(100).all()
    alerts_data = [a.to_dict() for a in alerts]

    counts = {
        "active": Alert.query.filter_by(status="ACTIVE").count(),
        "acknowledged": Alert.query.filter_by(status="ACKNOWLEDGED").count(),
        "resolved": Alert.query.filter_by(status="RESOLVED").count(),
        "critical_active": Alert.query.filter_by(status="ACTIVE", severity="CRITICAL").count(),
    }

    return jsonify({
        "alerts": alerts_data,
        "counts": counts,
        "total": len(alerts_data)
    }), 200


@reports_bp.route("/alerts/<int:alert_id>/acknowledge", methods=["PUT"])
@login_required
def acknowledge_alert(alert_id):
    """Acknowledge an active alert."""
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return jsonify({"error": "Alert not found."}), 404

    user = get_current_user()
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = user.full_name or user.username
    db.session.commit()

    return jsonify({
        "message": "Alert acknowledged.",
        "alert": alert.to_dict()
    }), 200


@reports_bp.route("/alerts/<int:alert_id>/resolve", methods=["PUT"])
@login_required
def resolve_alert(alert_id):
    """Resolve an operational alert."""
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return jsonify({"error": "Alert not found."}), 404

    user = get_current_user()
    alert.status = "RESOLVED"
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = user.full_name or user.username
    db.session.commit()

    return jsonify({
        "message": "Alert resolved.",
        "alert": alert.to_dict()
    }), 200
