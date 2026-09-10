from flask import Blueprint, jsonify, request
from backend.models import (
    TransformerAsset,
    Alert,
    MaintenanceTask,
    IncidentReport,
    TelemetryReading
)
from backend.services.prioritization_engine import PrioritizationEngine

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/stats", methods=["GET"])
def get_dashboard_stats():
    """
    Computes top-level industrial operations center metrics:
    Asset counts by health tier, open maintenance tasks, active alerts, and incident trends.
    """
    total_assets = TransformerAsset.query.count()
    healthy_count = TransformerAsset.query.filter_by(health_status="HEALTHY").count()
    moderate_count = TransformerAsset.query.filter_by(health_status="MODERATE").count()
    high_count = TransformerAsset.query.filter_by(health_status="HIGH").count()
    critical_count = TransformerAsset.query.filter_by(health_status="CRITICAL").count()

    active_alerts_count = Alert.query.filter_by(status="ACTIVE").count()
    critical_alerts_count = Alert.query.filter_by(status="ACTIVE", severity="CRITICAL").count()

    open_tasks_count = MaintenanceTask.query.filter(
        MaintenanceTask.status.notin_(["RESOLVED", "VERIFIED"])
    ).count()

    pending_reports_count = IncidentReport.query.filter_by(status="SUBMITTED").count()

    # Recent alerts
    recent_alerts = [
        a.to_dict()
        for a in Alert.query.order_by(Alert.triggered_at.desc()).limit(6).all()
    ]

    # Quick summary of average fleet health
    avg_risk = 0.0
    if total_assets > 0:
        assets_all = TransformerAsset.query.all()
        avg_risk = round(sum(a.current_risk_score for a in assets_all) / total_assets, 1)

    return jsonify({
        "metrics": {
            "total_assets": total_assets,
            "healthy": healthy_count,
            "moderate": moderate_count,
            "high": high_count,
            "critical": critical_count,
            "active_alerts": active_alerts_count,
            "critical_alerts": critical_alerts_count,
            "open_maintenance_tasks": open_tasks_count,
            "pending_reports": pending_reports_count,
            "fleet_average_risk": avg_risk,
        },
        "risk_distribution": [
            {"tier": "HEALTHY", "count": healthy_count, "color": "#00e676"},
            {"tier": "MODERATE", "count": moderate_count, "color": "#ffb300"},
            {"tier": "HIGH", "count": high_count, "color": "#ff9100"},
            {"tier": "CRITICAL", "count": critical_count, "color": "#ff3d00"},
        ],
        "recent_alerts": recent_alerts
    }), 200


@dashboard_bp.route("/priority", methods=["GET"])
def get_priority_ranking():
    """
    Returns dynamically prioritized queue of transformer assets requiring maintenance dispatch.
    Powered by PrioritizationEngine using failure probability, risk, anomalies, overdue status, and incidents.
    """
    limit = request.args.get("limit", 10, type=int)

    # Fetch all assets
    assets = TransformerAsset.query.all()
    assets_with_data = []

    for asset in assets:
        # Fetch latest telemetry reading
        latest_tel = asset.telemetry_readings.order_by(TelemetryReading.timestamp.desc()).first()
        tel_dict = latest_tel.to_dict() if latest_tel else None

        # Fetch recent incident reports count
        rep_count = asset.incident_reports.filter(IncidentReport.status == "SUBMITTED").count()

        assets_with_data.append((asset, tel_dict, rep_count))

    ranked_list = PrioritizationEngine.rank_assets(assets_with_data)

    return jsonify({
        "priority_assets": ranked_list[:limit],
        "total_ranked": len(ranked_list)
    }), 200
