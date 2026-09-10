import random
import math
from datetime import datetime, timedelta, timezone

class TelemetryGenerator:
    """
    Physics-coupled simulated IoT telemetry generator for electrical transformers.
    Produces realistic operational relationships:
      - Higher load leads to quadratic temperature increases: ΔT ~ (Load%)²
      - Core & winding vibration scales with mechanical age, loose coils, and electrical harmonics
      - Voltage and current reflect load demand curves
      - Flagged anomalies for thermal surges, harmonic vibration spikes, and low oil levels
    """
    DISCLAIMER = "SIMULATED IoT TELEMETRY: Generated demonstration operational data for FaultLens prototype."

    @staticmethod
    def calculate_physics_values(
        rated_capacity_kva: float,
        base_age_years: float,
        previous_failures: int,
        hour_of_day: int,
        ambient_base: float = 24.0,
        anomaly_mode: str = None
    ) -> dict:
        """
        Computes realistic physical parameters based on diurnal cycles and asset health.
        """
        # Diurnal load curve: peaks during mid-day / early evening (10:00 - 20:00)
        diurnal_factor = math.sin((hour_of_day - 6) * math.pi / 12)
        base_load = 55.0 + (diurnal_factor * 25.0) + random.uniform(-4.0, 4.0)

        # Apply anomaly modes if forced or random stress
        if anomaly_mode == "OVERLOAD":
            load_pct = min(125.0, base_load + random.uniform(25.0, 40.0))
        else:
            load_pct = max(15.0, min(105.0, base_load))

        # Ambient temperature fluctuates diurnally
        ambient_temp = ambient_base + (diurnal_factor * 5.0) + random.uniform(-1.0, 1.0)

        # Thermal physics: Top-oil temperature rise over ambient scales quadratically with load
        # Nominal temperature rise at 100% load is ~45-55°C
        thermal_rise_nominal = 48.0
        load_ratio = load_pct / 100.0
        thermal_rise = thermal_rise_nominal * (0.3 + 0.7 * (load_ratio ** 1.8))

        # Aging and historical faults degrade thermal dissipation
        cooling_degradation = min(15.0, (base_age_years * 0.4) + (previous_failures * 2.5))
        temp_c = ambient_temp + thermal_rise + cooling_degradation

        # Vibration physics: Nominal 1.0 - 2.5 mm/s. Aged/faulty transformers show higher harmonics
        base_vib = 1.2 + (base_age_years * 0.08) + (previous_failures * 0.35)
        vib_load_component = (load_pct / 100.0) * 0.5
        vibration_mms = base_vib + vib_load_component + random.uniform(-0.15, 0.25)

        # Electrical: Nominal 415V secondary, voltage sags slightly under heavy load
        voltage_v = 415.0 - (load_ratio * 9.0) + random.uniform(-2.5, 2.5)
        # 3-phase current: I = (kVA * 1000 * load%) / (sqrt(3) * V)
        current_a = (rated_capacity_kva * 1000.0 * load_ratio) / (math.sqrt(3) * voltage_v)

        # Oil level: Nominal 94-98%
        oil_level_pct = max(60.0, 96.0 - (base_age_years * 0.5) - (previous_failures * 2.0) + random.uniform(-1.0, 1.0))

        # Check for anomaly conditions
        is_anomaly = False
        anomaly_details = []

        if anomaly_mode == "THERMAL_RUNAWAY" or temp_c > 88.0:
            if anomaly_mode == "THERMAL_RUNAWAY":
                temp_c += random.uniform(18.0, 30.0)
            is_anomaly = True
            anomaly_details.append(f"Elevated Winding Temperature ({temp_c:.1f}°C)")

        if anomaly_mode == "VIBRATION_SPIKE" or vibration_mms > 4.2:
            if anomaly_mode == "VIBRATION_SPIKE":
                vibration_mms += random.uniform(2.5, 4.5)
            is_anomaly = True
            anomaly_details.append(f"High Mechanical Vibration ({vibration_mms:.2f} mm/s)")

        if load_pct > 100.0:
            is_anomaly = True
            anomaly_details.append(f"Transformer Overload ({load_pct:.1f}%)")

        if oil_level_pct < 80.0:
            is_anomaly = True
            anomaly_details.append(f"Low Insulating Oil Level ({oil_level_pct:.1f}%)")

        return {
            "temperature_c": round(temp_c, 1),
            "ambient_temp_c": round(ambient_temp, 1),
            "voltage_v": round(voltage_v, 1),
            "current_a": round(current_a, 1),
            "load_pct": round(load_pct, 1),
            "vibration_mms": round(max(0.2, vibration_mms), 2),
            "oil_level_pct": round(oil_level_pct, 1),
            "is_anomaly": is_anomaly,
            "anomaly_details": "; ".join(anomaly_details) if anomaly_details else None,
        }

    @classmethod
    def generate_reading_for_asset(cls, asset, timestamp=None, anomaly_mode=None) -> dict:
        """Generates a single telemetry reading for a given TransformerAsset instance."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        age_years = asset.age_years if hasattr(asset, "age_years") else 5.0
        prev_failures = asset.previous_failure_count if hasattr(asset, "previous_failure_count") else 0
        hour = timestamp.hour

        values = cls.calculate_physics_values(
            rated_capacity_kva=asset.rated_capacity_kva,
            base_age_years=age_years,
            previous_failures=prev_failures,
            hour_of_day=hour,
            anomaly_mode=anomaly_mode
        )
        values["asset_id"] = asset.id
        values["timestamp"] = timestamp
        return values

    @classmethod
    def generate_historical_series(cls, asset, num_days: int = 14, readings_per_day: int = 4) -> list:
        """
        Generates a chronological time-series of telemetry readings demonstrating trends.
        """
        readings = []
        now = datetime.now(timezone.utc)
        step_hours = 24 / readings_per_day
        total_points = num_days * readings_per_day

        for i in range(total_points, -1, -1):
            point_time = now - timedelta(hours=i * step_hours)
            # If asset is high risk or critical, inject intermittent anomalies
            anomaly_mode = None
            if hasattr(asset, "health_status"):
                if asset.health_status == "CRITICAL" and random.random() < 0.45:
                    anomaly_mode = random.choice(["THERMAL_RUNAWAY", "VIBRATION_SPIKE", "OVERLOAD"])
                elif asset.health_status == "HIGH" and random.random() < 0.25:
                    anomaly_mode = random.choice(["THERMAL_RUNAWAY", "OVERLOAD"])

            reading_dict = cls.generate_reading_for_asset(asset, timestamp=point_time, anomaly_mode=anomaly_mode)
            readings.append(reading_dict)

        return readings
