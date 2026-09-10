from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.models import TransformerAsset, TelemetryReading, Alert
from backend.services.telemetry_generator import TelemetryGenerator
from backend.services.risk_engine import RiskEngine

telemetry_bp = Blueprint("telemetry", __name__, url_prefix="/api/assets")


@telemetry_bp.route("/<int:asset_id>/telemetry", methods=["GET"])
def get_asset_telemetry(asset_id):
    """
    Retrieve chronological telemetry time-series and summary metrics for an asset.
    Includes explicit SIMULATED IoT label and physics relationships.
    """
    asset = db.session.get(TransformerAsset, asset_id)
    if not asset:
        return jsonify({"error": "Transformer asset not found."}), 404

    limit = request.args.get("limit", 48, type=int)
    readings = (
        TelemetryReading.query.filter_by(asset_id=asset_id)
        .order_by(TelemetryReading.timestamp.desc())
        .limit(limit)
        .all()
    )

    # Return in chronological order (oldest to newest) for charting
    readings_data = [r.to_dict() for r in reversed(readings)]

    # Compute summary aggregates
    if readings_data:
        temps = [r["temperature_c"] for r in readings_data]
        loads = [r["load_pct"] for r in readings_data]
        vibs = [r["vibration_mms"] for r in readings_data]

        summary = {
            "avg_temperature_c": round(sum(temps) / len(temps), 1),
            "max_temperature_c": round(max(temps), 1),
            "min_temperature_c": round(min(temps), 1),
            "avg_load_pct": round(sum(loads) / len(loads), 1),
            "max_load_pct": round(max(loads), 1),
            "avg_vibration_mms": round(sum(vibs) / len(vibs), 2),
            "max_vibration_mms": round(max(vibs), 2),
            "anomalies_detected": sum(1 for r in readings_data if r["is_anomaly"]),
        }
    else:
        summary = None

    return jsonify({
        "asset_id": asset.id,
        "asset_tag": asset.asset_tag,
        "disclaimer": TelemetryGenerator.DISCLAIMER,
        "is_simulated": True,
        "summary": summary,
        "readings": readings_data,
        "total_points": len(readings_data)
    }), 200


@telemetry_bp.route("/<int:asset_id>/telemetry/generate", methods=["POST"])
def generate_live_reading(asset_id):
    """
    Simulates real-time IoT packet arrival for an asset.
    Optionally accepts forced anomaly_mode ('THERMAL_RUNAWAY', 'VIBRATION_SPIKE', 'OVERLOAD').
    Persists reading, checks thresholds, and triggers alert if necessary.
    """
    asset = db.session.get(TransformerAsset, asset_id)
    if not asset:
        return jsonify({"error": "Transformer asset not found."}), 404

    data = request.get_json() or {}
    anomaly_mode = data.get("anomaly_mode")

    reading_dict = TelemetryGenerator.generate_reading_for_asset(
        asset=asset,
        timestamp=datetime.now(timezone.utc),
        anomaly_mode=anomaly_mode
    )

    reading = TelemetryReading(
        asset_id=asset.id,
        timestamp=reading_dict["timestamp"],
        temperature_c=reading_dict["temperature_c"],
        ambient_temp_c=reading_dict["ambient_temp_c"],
        voltage_v=reading_dict["voltage_v"],
        current_a=reading_dict["current_a"],
        load_pct=reading_dict["load_pct"],
        vibration_mms=reading_dict["vibration_mms"],
        oil_level_pct=reading_dict["oil_level_pct"],
        is_anomaly=reading_dict["is_anomaly"],
        anomaly_details=reading_dict["anomaly_details"]
    )
    db.session.add(reading)

    # If critical anomaly triggered, generate an active alert
    alert_created = None
    if reading.is_anomaly:
        alert = Alert(
            asset_id=asset.id,
            severity="CRITICAL" if (reading.temperature_c > 95.0 or reading.vibration_mms > 4.5) else "WARNING",
            alert_type="TEMPERATURE_ANOMALY" if reading.temperature_c > 88.0 else "VIBRATION_SPIKE",
            title=f"Telemetry Anomaly on {asset.asset_tag}",
            message=reading.anomaly_details or "Unusual telemetry parameters registered by simulated sensor."
        )
        db.session.add(alert)
        alert_created = alert

    # Recalculate asset risk
    risk_res = RiskEngine.evaluate_asset_risk(asset, latest_telemetry=reading_dict)
    asset.current_risk_score = risk_res["overall_risk_score"]
    asset.health_status = risk_res["health_status"]

    db.session.commit()

    return jsonify({
        "message": "Telemetry reading generated and persisted.",
        "reading": reading.to_dict(),
        "updated_risk": {
            "risk_score": asset.current_risk_score,
            "health_status": asset.health_status
        },
        "alert_triggered": alert_created.to_dict() if alert_created else None
    }), 201
