from datetime import date
from typing import Dict, Any, List, Optional

class RiskEngine:
    """
    Explainable Additive Risk Engine for Electrical Transformers.
    Deconstructs composite infrastructure risk into transparent, quantifiable contributing factors.
    Clearly labeled as 'Prototype Risk Model'.
    """
    MODEL_VERSION = "Prototype Additive Risk Model v1.2"
    DISCLAIMER = (
        "Prototype Risk Model: Risk scores are additive heuristic estimates calculated for "
        "decision support demonstration. Not certified utility engineering analysis."
    )

    @classmethod
    def evaluate_asset_risk(
        cls,
        asset,
        latest_telemetry: Optional[dict] = None,
        recent_reports_count: int = 0
    ) -> Dict[str, Any]:
        """
        Evaluates risk factors and returns a granular explanation with action recommendations.
        """
        factors: List[Dict[str, Any]] = []
        total_score = 0.0

        # --- Factor 1: Temperature Condition & Thermal Headroom ---
        temp_c = 60.0
        if latest_telemetry and "temperature_c" in latest_telemetry:
            temp_c = float(latest_telemetry["temperature_c"])

        temp_impact = 0.0
        if temp_c > 100.0:
            temp_impact = 28.0
            rationale = f"Severe thermal surge ({temp_c:.1f}°C) exceeding insulation rating."
            severity = "CRITICAL"
        elif temp_c > 85.0:
            temp_impact = 22.0
            rationale = f"Elevated winding temperature ({temp_c:.1f}°C) accelerating oil breakdown."
            severity = "HIGH"
        elif temp_c > 72.0:
            temp_impact = 12.0
            rationale = f"Moderate thermal load ({temp_c:.1f}°C) above nominal baseline."
            severity = "MODERATE"
        elif temp_c > 62.0:
            temp_impact = 5.0
            rationale = f"Normal operational temperature ({temp_c:.1f}°C)."
            severity = "LOW"
        else:
            temp_impact = 2.0
            rationale = f"Cool core temperature ({temp_c:.1f}°C)."
            severity = "LOW"

        factors.append({
            "name": "Temperature Anomaly",
            "impact": round(temp_impact, 1),
            "severity": severity,
            "metric_value": f"{temp_c:.1f}°C",
            "rationale": rationale,
            "category": "Thermal"
        })
        total_score += temp_impact

        # --- Factor 2: Mechanical Vibration & Core Harmonics ---
        vib_mms = 1.5
        if latest_telemetry and "vibration_mms" in latest_telemetry:
            vib_mms = float(latest_telemetry["vibration_mms"])

        vib_impact = 0.0
        if vib_mms > 4.5:
            vib_impact = 20.0
            rationale = f"Severe structural vibration ({vib_mms:.2f} mm/s) indicates loose core/coils."
            severity = "CRITICAL"
        elif vib_mms > 3.0:
            vib_impact = 14.0
            rationale = f"Elevated harmonic vibration ({vib_mms:.2f} mm/s) above ISO threshold."
            severity = "HIGH"
        elif vib_mms > 2.2:
            vib_impact = 7.0
            rationale = f"Mild mechanical resonance ({vib_mms:.2f} mm/s)."
            severity = "MODERATE"
        else:
            vib_impact = 2.0
            rationale = f"Vibration within nominal damping limits ({vib_mms:.2f} mm/s)."
            severity = "LOW"

        factors.append({
            "name": "Vibration Stress",
            "impact": round(vib_impact, 1),
            "severity": severity,
            "metric_value": f"{vib_mms:.2f} mm/s",
            "rationale": rationale,
            "category": "Mechanical"
        })
        total_score += vib_impact

        # --- Factor 3: Operational Electrical Load ---
        load_pct = 65.0
        if latest_telemetry and "load_pct" in latest_telemetry:
            load_pct = float(latest_telemetry["load_pct"])

        load_impact = 0.0
        if load_pct > 110.0:
            load_impact = 18.0
            rationale = f"Critical overload ({load_pct:.1f}%) causing cumulative dielectric stress."
            severity = "CRITICAL"
        elif load_pct > 90.0:
            load_impact = 13.0
            rationale = f"Heavy continuous loading ({load_pct:.1f}%) near rated nameplate capacity."
            severity = "HIGH"
        elif load_pct > 75.0:
            load_impact = 7.0
            rationale = f"Standard medium load ({load_pct:.1f}%)."
            severity = "MODERATE"
        else:
            load_impact = 2.0
            rationale = f"Light operational load ({load_pct:.1f}%)."
            severity = "LOW"

        factors.append({
            "name": "Electrical Load Stress",
            "impact": round(load_impact, 1),
            "severity": severity,
            "metric_value": f"{load_pct:.1f}%",
            "rationale": rationale,
            "category": "Electrical"
        })
        total_score += load_impact

        # --- Factor 4: Maintenance Overdue Schedule ---
        days_since_maint = getattr(asset, "days_since_maintenance", 120)
        maint_impact = 0.0
        if days_since_maint > 365:
            maint_impact = 16.0
            rationale = f"Maintenance overdue by {days_since_maint} days (> 12 months)."
            severity = "HIGH"
        elif days_since_maint > 240:
            maint_impact = 11.0
            rationale = f"Scheduled interval approaching limit ({days_since_maint} days ago)."
            severity = "MODERATE"
        elif days_since_maint > 150:
            maint_impact = 5.0
            rationale = f"Routine maintenance window ({days_since_maint} days ago)."
            severity = "LOW"
        else:
            maint_impact = 1.0
            rationale = f"Recently maintained ({days_since_maint} days ago)."
            severity = "LOW"

        factors.append({
            "name": "Maintenance Overdue",
            "impact": round(maint_impact, 1),
            "severity": severity,
            "metric_value": f"{days_since_maint} days",
            "rationale": rationale,
            "category": "Operational"
        })
        total_score += maint_impact

        # --- Factor 5: Historical Failure Recurrence ---
        prev_failures = getattr(asset, "previous_failure_count", 0)
        fail_impact = min(20.0, prev_failures * 7.5)
        if prev_failures >= 3:
            fail_severity = "CRITICAL"
            fail_rationale = f"Chronic fault history with {prev_failures} documented previous breakdowns."
        elif prev_failures >= 1:
            fail_severity = "HIGH" if prev_failures == 2 else "MODERATE"
            fail_rationale = f"Past history of {prev_failures} failure event(s)."
        else:
            fail_severity = "LOW"
            fail_rationale = "Zero prior recorded historical failures."

        factors.append({
            "name": "Historical Failure Count",
            "impact": round(fail_impact, 1),
            "severity": fail_severity,
            "metric_value": f"{prev_failures} failures",
            "rationale": fail_rationale,
            "category": "History"
        })
        total_score += fail_impact

        # --- Factor 6: Asset Age & Dielectric Fatigue ---
        age_years = getattr(asset, "age_years", 5.0)
        age_impact = 0.0
        if age_years > 20.0:
            age_impact = 12.0
            age_rationale = f"End-of-life operating phase ({age_years:.1f} years in service)."
            age_severity = "HIGH"
        elif age_years > 12.0:
            age_impact = 8.0
            age_rationale = f"Mature operating asset ({age_years:.1f} years in service)."
            age_severity = "MODERATE"
        elif age_years > 5.0:
            age_impact = 4.0
            age_rationale = f"Mid-life service cycle ({age_years:.1f} years in service)."
            age_severity = "LOW"
        else:
            age_impact = 1.0
            age_rationale = f"Modern commissioned asset ({age_years:.1f} years in service)."
            age_severity = "LOW"

        factors.append({
            "name": "Asset Aging Degradation",
            "impact": round(age_impact, 1),
            "severity": age_severity,
            "metric_value": f"{age_years:.1f} yrs",
            "rationale": age_rationale,
            "category": "Asset Lifecycle"
        })
        total_score += age_impact

        # --- Factor 7: Technician Incident Report Density ---
        if recent_reports_count > 0:
            rep_impact = min(15.0, recent_reports_count * 5.0)
            rep_severity = "HIGH" if recent_reports_count >= 2 else "MODERATE"
            rep_rationale = f"{recent_reports_count} recent technician field observation(s) filed."
            factors.append({
                "name": "Technician Incident Signals",
                "impact": round(rep_impact, 1),
                "severity": rep_severity,
                "metric_value": f"{recent_reports_count} reports",
                "rationale": rep_rationale,
                "category": "Field Reports"
            })
            total_score += rep_impact

        # Clamp total score 0 to 100
        risk_score = round(max(5.0, min(99.0, total_score)), 1)

        # Classification
        if risk_score >= 81.0:
            health_status = "CRITICAL"
        elif risk_score >= 61.0:
            health_status = "HIGH"
        elif risk_score >= 31.0:
            health_status = "MODERATE"
        else:
            health_status = "HEALTHY"

        # Generate System Recommendations
        recommendations = cls.generate_recommendations(factors, health_status, risk_score)

        return {
            "overall_risk_score": risk_score,
            "health_status": health_status,
            "factors": factors,
            "model_version": cls.MODEL_VERSION,
            "recommendations": recommendations,
            "disclaimer": cls.DISCLAIMER,
        }

    @classmethod
    def generate_recommendations(
        cls,
        factors: List[Dict[str, Any]],
        health_status: str,
        risk_score: float
    ) -> List[Dict[str, str]]:
        """
        Derives actionable industrial engineering recommendations based on active risk drivers.
        """
        recs = []

        # Find factors with HIGH or CRITICAL severity
        high_factors = {f["name"]: f for f in factors if f["severity"] in ("HIGH", "CRITICAL")}

        if "Temperature Anomaly" in high_factors:
            recs.append({
                "action": "Schedule Urgent Thermographic Inspection",
                "urgency": "Immediate (24h)" if health_status == "CRITICAL" else "Priority (48h)",
                "rationale": "Verify internal hotspot formation, Dissolved Gas Analysis (DGA), and cooling radiator flow.",
                "type": "THERMAL"
            })

        if "Vibration Stress" in high_factors:
            recs.append({
                "action": "Inspect Mechanical & Structural Anchor Integrity",
                "urgency": "Immediate" if health_status == "CRITICAL" else "Standard (3 days)",
                "rationale": "Check core clamping torque, foundation bolt damping, and internal coil winding looseness.",
                "type": "MECHANICAL"
            })

        if "Electrical Load Stress" in high_factors:
            recs.append({
                "action": "Perform Feeder Load Balancing / Peak Shedding",
                "urgency": "Operational",
                "rationale": "Redistribute downstream feeder loads across adjacent substations to reduce thermal degradation.",
                "type": "ELECTRICAL"
            })

        if "Maintenance Overdue" in high_factors:
            recs.append({
                "action": "Dispatch Preventive Overhaul Crew",
                "urgency": "Within 7 Days",
                "rationale": "Perform oil dielectric breakdown test, bushing cleaning, and silica gel breather replacement.",
                "type": "PREVENTIVE"
            })

        if "Historical Failure Count" in high_factors:
            recs.append({
                "action": "Initiate Asset Capital Replacement & Life-Extension Review",
                "urgency": "Strategic",
                "rationale": "Asset exhibits recurrent breakdown patterns; evaluate refurbishment vs capital replacement.",
                "type": "CAPITAL"
            })

        if not recs:
            recs.append({
                "action": "Continue Automated Continuous Telemetry Monitoring",
                "urgency": "Routine",
                "rationale": "Asset telemetry operates within acceptable baseline tolerances; maintain standard inspection cycle.",
                "type": "ROUTINE"
            })

        return recs
