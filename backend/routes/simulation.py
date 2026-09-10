from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.models import TransformerAsset, TelemetryReading
from backend.services.risk_engine import RiskEngine
from backend.services.prediction_engine import PredictionEngine

simulation_bp = Blueprint("simulation", __name__, url_prefix="/api/simulation")


@simulation_bp.route("/what-if", methods=["POST"])
def simulate_what_if():
    """
    Evaluates hypothetical operational adjustments on an asset or baseline parameters.
    Calculates delta risk change, projected failure probability, and factor impacts.
    Explicitly frames results as heuristic decision-support simulation.
    """
    data = request.get_json() or {}
    asset_id = data.get("asset_id")

    # Baseline asset values
    if asset_id:
        asset = db.session.get(TransformerAsset, asset_id)
        if not asset:
            return jsonify({"error": "Asset not found."}), 404

        latest_tel = asset.telemetry_readings.order_by(TelemetryReading.timestamp.desc()).first()

        base_temp = latest_tel.temperature_c if latest_tel else 65.0
        base_vib = latest_tel.vibration_mms if latest_tel else 1.8
        base_load = latest_tel.load_pct if latest_tel else 68.0
        base_days_maint = asset.days_since_maintenance
        base_faults = asset.previous_failure_count
        base_age = asset.age_years
        asset_tag = asset.asset_tag
        asset_name = asset.name
    else:
        base_temp = float(data.get("base_temp", 65.0))
        base_vib = float(data.get("base_vib", 1.8))
        base_load = float(data.get("base_load", 68.0))
        base_days_maint = int(data.get("base_days_maint", 120))
        base_faults = int(data.get("base_faults", 0))
        base_age = float(data.get("base_age", 5.0))
        asset_tag = "SYNTHETIC-SIM"
        asset_name = "Generic Scenario Transformer"

    # Delta adjustments from user sliders
    delta_load_pct = float(data.get("delta_load_pct", 0.0))         # e.g., +15%
    delta_temp_c = float(data.get("delta_temp_c", 0.0))             # e.g., +8°C
    delta_vibration_mms = float(data.get("delta_vibration_mms", 0.0)) # e.g., +1.2 mm/s
    delta_maint_days = int(data.get("delta_maint_days", 0))         # e.g., +90 days
    delta_faults = int(data.get("delta_faults", 0))                 # e.g., +1 fault

    # Projected operational conditions
    proj_load = max(10.0, min(140.0, base_load + delta_load_pct))
    proj_temp = max(30.0, min(130.0, base_temp + delta_temp_c))
    proj_vib = max(0.5, min(8.0, base_vib + delta_vibration_mms))
    proj_days_maint = max(0, base_days_maint + delta_maint_days)
    proj_faults = max(0, base_faults + delta_faults)

    # 1. Evaluate baseline risk & prediction
    class DummyAsset:
        def __init__(self, age, days, faults):
            self.age_years = age
            self.days_since_maintenance = days
            self.previous_failure_count = faults

    baseline_dummy = DummyAsset(base_age, base_days_maint, base_faults)
    base_risk_res = RiskEngine.evaluate_asset_risk(
        baseline_dummy,
        latest_telemetry={"temperature_c": base_temp, "vibration_mms": base_vib, "load_pct": base_load}
    )
    base_pred_res = PredictionEngine.predict_failure_probability({
        "temperature_c": base_temp,
        "vibration_mms": base_vib,
        "load_pct": base_load,
        "age_years": base_age,
        "previous_failures": base_faults,
        "days_since_maintenance": base_days_maint,
        "oil_quality_index": 90.0,
    })

    # 2. Evaluate projected risk & prediction under scenario
    projected_dummy = DummyAsset(base_age, proj_days_maint, proj_faults)
    proj_risk_res = RiskEngine.evaluate_asset_risk(
        projected_dummy,
        latest_telemetry={"temperature_c": proj_temp, "vibration_mms": proj_vib, "load_pct": proj_load}
    )
    proj_pred_res = PredictionEngine.predict_failure_probability({
        "temperature_c": proj_temp,
        "vibration_mms": proj_vib,
        "load_pct": proj_load,
        "age_years": base_age,
        "previous_failures": proj_faults,
        "days_since_maintenance": proj_days_maint,
        "oil_quality_index": max(40.0, 90.0 - (delta_temp_c * 0.4) - (delta_maint_days * 0.03)),
    })

    # Deltas
    risk_delta = round(proj_risk_res["overall_risk_score"] - base_risk_res["overall_risk_score"], 1)
    prob_delta_pct = round(proj_pred_res["failure_probability_pct"] - base_pred_res["failure_probability_pct"], 1)

    return jsonify({
        "asset_tag": asset_tag,
        "asset_name": asset_name,
        "baseline": {
            "load_pct": round(base_load, 1),
            "temperature_c": round(base_temp, 1),
            "vibration_mms": round(base_vib, 2),
            "days_since_maintenance": base_days_maint,
            "previous_faults": base_faults,
            "risk_score": base_risk_res["overall_risk_score"],
            "health_status": base_risk_res["health_status"],
            "failure_probability_pct": base_pred_res["failure_probability_pct"],
            "factors": base_risk_res["factors"],
        },
        "scenario": {
            "load_pct": round(proj_load, 1),
            "temperature_c": round(proj_temp, 1),
            "vibration_mms": round(proj_vib, 2),
            "days_since_maintenance": proj_days_maint,
            "previous_faults": proj_faults,
            "risk_score": proj_risk_res["overall_risk_score"],
            "health_status": proj_risk_res["health_status"],
            "failure_probability_pct": proj_pred_res["failure_probability_pct"],
            "factors": proj_risk_res["factors"],
            "recommendations": proj_risk_res["recommendations"],
        },
        "deltas": {
            "risk_score_change": risk_delta,
            "failure_probability_pct_change": prob_delta_pct,
            "load_change": delta_load_pct,
            "temp_change": delta_temp_c,
            "vibration_change": delta_vibration_mms,
            "maintenance_delay_days": delta_maint_days,
            "faults_added": delta_faults,
        },
        "disclaimer": (
            "WHAT-IF SIMULATION TOOL: Sensitivity and decision-support modeling only. "
            "Does not represent guaranteed real-world physical failure forecasting."
        )
    }), 200
