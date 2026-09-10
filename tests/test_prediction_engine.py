import unittest
from backend.services.prediction_engine import PredictionEngine


class TestPredictionEngine(unittest.TestCase):
    def test_benign_features_yield_low_probability(self):
        features = {
            "temperature_c": 50.0,
            "vibration_mms": 1.1,
            "load_pct": 40.0,
            "age_years": 2.0,
            "previous_failures": 0,
            "days_since_maintenance": 40,
            "oil_quality_index": 98.0,
        }
        res = PredictionEngine.predict_failure_probability(features)
        self.assertIn("failure_probability", res)
        self.assertIn("failure_probability_pct", res)
        self.assertEqual(res["risk_tier"], "LOW")
        self.assertLess(res["failure_probability"], 0.35)

    def test_stressed_features_yield_high_or_critical_probability(self):
        features = {
            "temperature_c": 110.0,
            "vibration_mms": 5.5,
            "load_pct": 120.0,
            "age_years": 24.0,
            "previous_failures": 4,
            "days_since_maintenance": 450,
            "oil_quality_index": 45.0,
        }
        res = PredictionEngine.predict_failure_probability(features)
        self.assertIn(res["risk_tier"], ["HIGH", "CRITICAL"])
        self.assertGreater(res["failure_probability"], 0.65)
        self.assertGreater(len(res["feature_contributions"]), 0)

    def test_feature_contributions_structure(self):
        features = {
            "temperature_c": 95.0,
            "vibration_mms": 3.5,
            "load_pct": 95.0,
            "age_years": 15.0,
            "previous_failures": 2,
            "days_since_maintenance": 300,
            "oil_quality_index": 70.0,
        }
        res = PredictionEngine.predict_failure_probability(features)
        for contrib in res["feature_contributions"]:
            self.assertIn("feature", contrib)
            self.assertIn("value", contrib)
            self.assertIn("importance_score", contrib)
            self.assertIn("direction", contrib)


if __name__ == "__main__":
    unittest.main()
