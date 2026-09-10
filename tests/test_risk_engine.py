import unittest
from datetime import date
from backend.services.risk_engine import RiskEngine


class DummyAsset:
    def __init__(self, age=5.0, days_maint=100, faults=0):
        self.age_years = age
        self.days_since_maintenance = days_maint
        self.previous_failure_count = faults


class TestRiskEngine(unittest.TestCase):
    def test_healthy_asset_evaluation(self):
        asset = DummyAsset(age=2.0, days_maint=30, faults=0)
        telemetry = {"temperature_c": 52.0, "vibration_mms": 1.2, "load_pct": 45.0}

        res = RiskEngine.evaluate_asset_risk(asset, latest_telemetry=telemetry)
        self.assertIn("overall_risk_score", res)
        self.assertEqual(res["health_status"], "HEALTHY")
        self.assertLess(res["overall_risk_score"], 31.0)
        self.assertGreaterEqual(len(res["factors"]), 6)

    def test_critical_asset_evaluation(self):
        asset = DummyAsset(age=22.0, days_maint=420, faults=3)
        telemetry = {"temperature_c": 105.0, "vibration_mms": 5.2, "load_pct": 115.0}

        res = RiskEngine.evaluate_asset_risk(asset, latest_telemetry=telemetry, recent_reports_count=2)
        self.assertEqual(res["health_status"], "CRITICAL")
        self.assertGreaterEqual(res["overall_risk_score"], 80.0)
        
        # Verify factor names and impact values
        factor_names = [f["name"] for f in res["factors"]]
        self.assertIn("Temperature Anomaly", factor_names)
        self.assertIn("Vibration Stress", factor_names)
        self.assertIn("Historical Failure Count", factor_names)
        self.assertIn("Technician Incident Signals", factor_names)

        # Check that recommendations exist
        self.assertGreaterEqual(len(res["recommendations"]), 2)

    def test_risk_score_clamping(self):
        # Even with extreme values, score must stay within [5.0, 99.0]
        asset = DummyAsset(age=50.0, days_maint=1500, faults=10)
        telemetry = {"temperature_c": 200.0, "vibration_mms": 20.0, "load_pct": 200.0}

        res = RiskEngine.evaluate_asset_risk(asset, latest_telemetry=telemetry)
        self.assertLessEqual(res["overall_risk_score"], 99.0)
        self.assertGreaterEqual(res["overall_risk_score"], 5.0)


if __name__ == "__main__":
    unittest.main()
