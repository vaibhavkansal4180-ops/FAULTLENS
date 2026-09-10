import unittest
from datetime import date
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from backend.models import TransformerAsset, TelemetryReading, Alert
from backend.services.telemetry_generator import TelemetryGenerator


class TestTelemetry(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            self.asset = TransformerAsset(
                asset_tag="FL-042",
                name="Test Unit",
                substation="Substation A",
                location="Vault 1",
                installation_date=date(2018, 1, 1),
                manufacturer="Siemens",
                model_number="T-500",
                rated_capacity_kva=1000.0,
                current_risk_score=50.0,
                failure_probability=0.5
            )
            db.session.add(self.asset)
            db.session.commit()
            self.asset_id = self.asset.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_physics_relationships(self):
        # Normal reading vs heavy overload
        normal = TelemetryGenerator.calculate_physics_values(
            rated_capacity_kva=1000.0,
            base_age_years=5.0,
            previous_failures=0,
            hour_of_day=14
        )
        overload = TelemetryGenerator.calculate_physics_values(
            rated_capacity_kva=1000.0,
            base_age_years=5.0,
            previous_failures=0,
            hour_of_day=14,
            anomaly_mode="OVERLOAD"
        )
        self.assertGreater(overload["load_pct"], normal["load_pct"])
        self.assertGreater(overload["temperature_c"], normal["temperature_c"])

    def test_thermal_anomaly_mode(self):
        anomaly = TelemetryGenerator.calculate_physics_values(
            rated_capacity_kva=1000.0,
            base_age_years=10.0,
            previous_failures=2,
            hour_of_day=14,
            anomaly_mode="THERMAL_RUNAWAY"
        )
        self.assertTrue(anomaly["is_anomaly"])
        self.assertGreater(anomaly["temperature_c"], 85.0)

    def test_get_telemetry_endpoint(self):
        with self.app.app_context():
            # Seed 5 readings
            for i in range(5):
                r = TelemetryReading(
                    asset_id=self.asset_id,
                    temperature_c=65.0 + i,
                    voltage_v=415.0,
                    current_a=700.0,
                    load_pct=70.0,
                    vibration_mms=1.8
                )
                db.session.add(r)
            db.session.commit()

        res = self.client.get(f"/api/assets/{self.asset_id}/telemetry")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["is_simulated"])
        self.assertEqual(len(data["readings"]), 5)
        self.assertEqual(data["summary"]["avg_temperature_c"], 67.0)

    def test_generate_live_telemetry_api(self):
        res = self.client.post(
            f"/api/assets/{self.asset_id}/telemetry/generate",
            json={"anomaly_mode": "THERMAL_RUNAWAY"}
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["reading"]["is_anomaly"])
        self.assertIsNotNone(data["alert_triggered"])


if __name__ == "__main__":
    unittest.main()
