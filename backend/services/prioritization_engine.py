from typing import List, Dict, Any

class PrioritizationEngine:
    """
    Industrial Maintenance Resource Prioritization Engine.
    Solves dispatch optimization: Which electrical transformers require intervention first?
    Synthesizes failure probability, risk severity, maintenance overdue gap, telemetry anomalies, and incident reports.
    """

    @classmethod
    def calculate_priority_for_asset(
        cls,
        asset,
        latest_telemetry: dict = None,
        recent_reports_count: int = 0
    ) -> Dict[str, Any]:
        """Calculates a composite priority score and dispatch recommendation for an asset."""
        # 1. Failure Probability Component (35% weight)
        prob_pct = (asset.failure_probability * 100.0) if asset.failure_probability <= 1.0 else asset.failure_probability
        p_prob = min(100.0, max(0.0, prob_pct)) * 0.35

        # 2. Risk Score Component (25% weight)
        r_score = min(100.0, max(0.0, asset.current_risk_score)) * 0.25

        # 3. Maintenance Overdue Factor (15% weight)
        days_maint = asset.days_since_maintenance
        if days_maint > 365:
            overdue_score = 100.0
        elif days_maint > 240:
            overdue_score = 75.0
        elif days_maint > 180:
            overdue_score = 45.0
        else:
            overdue_score = 15.0
        p_overdue = overdue_score * 0.15

        # 4. Telemetry Anomaly Factor (15% weight)
        has_anomaly = False
        anomaly_severity = 0.0
        if latest_telemetry:
            if latest_telemetry.get("is_anomaly"):
                has_anomaly = True
                temp = latest_telemetry.get("temperature_c", 60.0)
                vib = latest_telemetry.get("vibration_mms", 1.5)
                if temp > 95.0 or vib > 4.5:
                    anomaly_severity = 100.0
                elif temp > 85.0 or vib > 3.0:
                    anomaly_severity = 75.0
                else:
                    anomaly_severity = 50.0
            else:
                anomaly_severity = 10.0
        else:
            anomaly_severity = 20.0
        p_anomaly = anomaly_severity * 0.15

        # 5. Incident Reports / Recurrence Factor (10% weight)
        prev_fails = asset.previous_failure_count
        combined_signal = (prev_fails * 20.0) + (recent_reports_count * 25.0)
        p_incident = min(100.0, combined_signal) * 0.10

        # Composite score
        total_priority = round(min(99.0, max(5.0, p_prob + r_score + p_overdue + p_anomaly + p_incident)), 1)

        # Primary drivers identification
        drivers = []
        if prob_pct >= 60.0:
            drivers.append(f"High Failure Probability ({prob_pct:.1f}%)")
        if latest_telemetry and latest_telemetry.get("is_anomaly"):
            drivers.append(latest_telemetry.get("anomaly_details") or "Active Telemetry Anomaly")
        if days_maint > 300:
            drivers.append(f"Maintenance Overdue ({days_maint} days)")
        if prev_fails >= 2:
            drivers.append(f"Recurrent Breakdown History ({prev_fails} prior faults)")
        if recent_reports_count >= 1:
            drivers.append(f"{recent_reports_count} Pending Field Incident Report(s)")

        if not drivers:
            drivers.append("Standard Scheduled Monitoring")

        # Urgency classification
        if total_priority >= 80.0:
            urgency = "IMMEDIATE"
            recommended_window = "Within 24 Hours"
        elif total_priority >= 65.0:
            urgency = "HIGH"
            recommended_window = "Within 48 Hours"
        elif total_priority >= 45.0:
            urgency = "MODERATE"
            recommended_window = "Within 7 Days"
        else:
            urgency = "ROUTINE"
            recommended_window = "Next Standard Cycle (30 Days)"

        return {
            "asset_id": asset.id,
            "asset_tag": asset.asset_tag,
            "asset_name": asset.name,
            "substation": asset.substation,
            "priority_score": total_priority,
            "urgency": urgency,
            "risk_score": asset.current_risk_score,
            "failure_probability_pct": round(prob_pct, 1),
            "health_status": asset.health_status,
            "days_since_maintenance": days_maint,
            "has_active_anomaly": has_anomaly,
            "primary_drivers": drivers,
            "recommended_window": recommended_window,
        }

    @classmethod
    def rank_assets(cls, assets_with_data: List[tuple]) -> List[Dict[str, Any]]:
        """
        Takes a list of tuples: (asset, latest_telemetry_dict, recent_reports_count)
        Returns ranked assets ordered by priority score descending.
        """
        results = []
        for asset, telemetry, rep_count in assets_with_data:
            item = cls.calculate_priority_for_asset(asset, telemetry, rep_count)
            results.append(item)

        results.sort(key=lambda x: x["priority_score"], reverse=True)

        for idx, item in enumerate(results, start=1):
            item["rank"] = idx

        return results
