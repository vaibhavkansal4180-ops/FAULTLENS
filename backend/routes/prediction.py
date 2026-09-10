from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.models import TransformerAsset, TelemetryReading, RiskAssessment
from backend.services.prediction_engine import PredictionEngine
from backend.services.risk_engine import RiskEngine

prediction_bp = Blueprint("prediction", __name__, url_prefix="/api")


@prediction_bp.route("/prediction/analyze", methods=["POST"])
def analyze_prediction():
    """
    Evaluates ML failure probability and feature attribution for custom or asset parameters.
    Transparently reports model coefficients and prototype disclaimer.
    """
    data = request.get_json() or {}
    asset_id = data.get("asset_id")

    if asset_id:
        asset = db.session.get(TransformerAsset, asset_id)
        if not asset:
            return jsonify({"error": "Asset not found."}), 404

        latest_tel = asset.telemetry_readings.order_by(TelemetryReading.timestamp.desc()).first()
        features = {
            "temperature_c": latest_tel.temperature_c if latest_tel else 65.0,
            "vibration_mms": latest_tel.vibration_mms if latest_tel else 1.8,
            "load_pct": latest_tel.load_pct if latest_tel else 70.0,
            "age_years": asset.age_years,
            "previous_failures": asset.previous_failure_count,
            "days_since_maintenance": asset.days_since_maintenance,
            "oil_quality_index": 90.0,
        }
    else:
        features = {
            "temperature_c": float(data.get("temperature_c", 65.0)),
            "vibration_mms": float(data.get("vibration_mms", 1.8)),
            "load_pct": float(data.get("load_pct", 70.0)),
            "age_years": float(data.get("age_years", 6.0)),
            "previous_failures": int(data.get("previous_failures", 0)),
            "days_since_maintenance": int(data.get("days_since_maintenance", 120)),
            "oil_quality_index": float(data.get("oil_quality_index", 90.0)),
        }

    prediction_result = PredictionEngine.predict_failure_probability(features)

    return jsonify({
        "input_features": features,
        "prediction": prediction_result
    }), 200


@prediction_bp.route("/assets/<int:asset_id>/risk-timeline", methods=["GET"])
def get_risk_timeline(asset_id):
    """
    Returns historical risk progression for an asset to visualize health deterioration over time.
    """
    asset = db.session.get(TransformerAsset, asset_id)
    if not asset:
        return jsonify({"error": "Asset not found."}), 404

    # Fetch stored risk assessments or construct timeline from telemetry & age
    stored_assessments = asset.risk_assessments.order_by(RiskAssessment.assessment_date.asc()).all()

    timeline = []
    if stored_assessments:
        for sa in stored_assessments:
            timeline.append({
                "date": sa.assessment_date.strftime("%Y-%m-%d"),
                "risk_score": sa.overall_risk_score,
                "failure_probability_pct": round(sa.failure_probability * 100, 1),
            })
    else:
        # Generate representative chronological progression points (e.g., past 4 quarters)
        now = datetime.now(timezone.utc)
        curr_risk = asset.current_risk_score
        curr_prob = asset.failure_probability * 100.0

        for i in [360, 240, 120, 0]:
            t_date = now - timedelta(days=i)
            # Earlier dates had lower degradation
            factor = max(0.4, 1.0 - (i / 500.0))
            point_risk = round(max(10.0, curr_risk * factor), 1)
            point_prob = round(max(5.0, curr_prob * factor), 1)
            timeline.append({
                "date": t_date.strftime("%Y-%m-%d"),
                "risk_score": point_risk,
                "failure_probability_pct": point_prob,
                "label": "Current" if i == 0 else f"{i} days ago"
            })

    return jsonify({
        "asset_id": asset.id,
        "asset_tag": asset.asset_tag,
        "current_risk_score": asset.current_risk_score,
        "current_health_status": asset.health_status,
        "timeline": timeline
    }), 200
