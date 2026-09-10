import unittest
from datetime import date
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from backend.models import TransformerAsset, TelemetryReading


class TestSimulationRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            self.asset = TransformerAsset(
                asset_tag="FL-042",
                name="Primary Heavy Feeder",
                substation="Metro Substation",
                location="Sector 1",
                installation_date=date(2018, 1, 1),
                manufacturer="Siemens",
                model_number="Troniq T-500",
                rated_capacity_kva=1250.0,
                current_risk_score=60.0,
                failure_probability=0.55
            )
            db.session.add(self.asset)
            db.session.commit()
            self.asset_id = self.asset.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_what_if_simulation_endpoint(self):
        payload = {
            "asset_id": self.asset_id,
            "delta_load_pct": 20.0,
            "delta_temp_c": 10.0,
            "delta_vibration_mms": 1.5,
            "delta_maint_days": 60,
            "delta_faults": 1
        }
        res = self.client.post("/api/simulation/what-if", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("baseline", data)
        self.assertIn("scenario", data)
        self.assertIn("deltas", data)
        # Increasing load and temperature must increase risk score
        self.assertGreater(data["scenario"]["risk_score"], data["baseline"]["risk_score"])
        self.assertGreater(data["deltas"]["risk_score_change"], 0)
        self.assertIn("disclaimer", data)


if __name__ == "__main__":
    unittest.main()
