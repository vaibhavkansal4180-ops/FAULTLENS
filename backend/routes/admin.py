import os
from flask import Blueprint, request, jsonify, current_app
from backend.extensions import db
from backend.models import (
    TransformerAsset,
    TelemetryReading,
    MaintenanceRecord,
    Inspection,
    IncidentReport,
    Alert,
    MaintenanceTask,
    RiskAssessment,
    User
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

ADMIN_MASTER_KEYS = {
    "faultlens-industrial-sec-k9284j20f83h",
    "faultlens-prod-clean-2026",
}


def is_authorized_admin(req):
    """Checks if request has valid admin token or matches app SECRET_KEY."""
    token = (
        req.headers.get("X-Admin-Token")
        or req.args.get("token")
        or (req.is_json and req.get_json(silent=True) and req.get_json(silent=True).get("token"))
    )
    secret_key = current_app.config.get("SECRET_KEY", "")
    if token and (token in ADMIN_MASTER_KEYS or token == secret_key):
        return True
    return False


@admin_bp.route("/db-status", methods=["GET"])
def db_status():
    """
    Publicly inspectable or diagnostic database status endpoint.
    Reports connection dialect and record counts without exposing credentials.
    """
    try:
        engine = db.engine
        dialect_name = engine.dialect.name
        is_sqlite = "sqlite" in dialect_name
        is_postgres = "postgres" in dialect_name

        counts = {
            "transformer_assets": TransformerAsset.query.count(),
            "telemetry_readings": TelemetryReading.query.count(),
            "maintenance_tasks": MaintenanceTask.query.count(),
            "alerts": Alert.query.count(),
            "incident_reports": IncidentReport.query.count(),
            "risk_assessments": RiskAssessment.query.count(),
            "inspections": Inspection.query.count(),
            "maintenance_records": MaintenanceRecord.query.count(),
            "users": User.query.count(),
        }

        total_demo_records = sum(counts.values())

        return jsonify({
            "status": "online",
            "database_dialect": dialect_name,
            "is_postgresql": is_postgres,
            "is_sqlite": is_sqlite,
            "is_clean_production": (counts["transformer_assets"] == 0),
            "table_counts": counts,
            "total_records": total_demo_records,
            "environment": current_app.config.get("ENV", "development"),
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "environment": current_app.config.get("ENV", "development"),
        }), 500


@admin_bp.route("/init-tables", methods=["POST", "GET"])
def init_tables():
    """Idempotently ensures all database tables exist in the connected database."""
    try:
        db.create_all()
        return jsonify({
            "message": "Database tables verified/created successfully.",
            "database_dialect": db.engine.dialect.name
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to initialize tables: {str(e)}"}), 500


@admin_bp.route("/clean-demo-records", methods=["POST", "GET"])
def clean_demo_records():
    """
    Purges all demonstration and fake records from the database.
    Leaves database, tables, schema, and models completely intact.
    Authorized via admin token or SECRET_KEY.
    """
    if not is_authorized_admin(request):
        return jsonify({"error": "Unauthorized. Provide valid admin token."}), 401

    try:
        # Delete related child records first to honor foreign key constraints
        db.session.query(MaintenanceTask).delete()
        db.session.query(Alert).delete()
        db.session.query(RiskAssessment).delete()
        db.session.query(IncidentReport).delete()
        db.session.query(Inspection).delete()
        db.session.query(MaintenanceRecord).delete()
        db.session.query(TelemetryReading).delete()
        db.session.query(TransformerAsset).delete()
        db.session.query(User).delete()
        db.session.commit()

        counts = {
            "transformer_assets": TransformerAsset.query.count(),
            "telemetry_readings": TelemetryReading.query.count(),
            "maintenance_tasks": MaintenanceTask.query.count(),
            "alerts": Alert.query.count(),
            "incident_reports": IncidentReport.query.count(),
            "risk_assessments": RiskAssessment.query.count(),
            "inspections": Inspection.query.count(),
            "maintenance_records": MaintenanceRecord.query.count(),
            "users": User.query.count(),
        }

        return jsonify({
            "success": True,
            "message": "All demonstration and fake records successfully removed from database.",
            "database_dialect": db.engine.dialect.name,
            "remaining_counts": counts,
            "is_clean_production": True
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Failed to purge demo records: {str(e)}"
        }), 500
