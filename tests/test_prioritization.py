import unittest
from backend.services.prioritization_engine import PrioritizationEngine


class MockAsset:
    def __init__(self, id, tag, name, sub, prob, risk, days_maint, faults, health):
        self.id = id
        self.asset_tag = tag
        self.name = name
        self.substation = sub
        self.failure_probability = prob
        self.current_risk_score = risk
        self.days_since_maintenance = days_maint
        self.previous_failure_count = faults
        self.health_status = health


class TestPrioritizationEngine(unittest.TestCase):
    def test_priority_ranking_order(self):
        # Asset 1: Critical high risk
        a1 = MockAsset(1, "FL-042", "Unit 42", "Sub A", 0.88, 88.0, 410, 3, "CRITICAL")
        # Asset 2: Moderate
        a2 = MockAsset(2, "FL-010", "Unit 10", "Sub B", 0.40, 42.0, 150, 0, "MODERATE")
        # Asset 3: Healthy
        a3 = MockAsset(3, "FL-002", "Unit 2", "Sub C", 0.12, 14.0, 30, 0, "HEALTHY")

        data = [
            (a2, {"temperature_c": 64.0, "is_anomaly": False}, 0),
            (a3, {"temperature_c": 50.0, "is_anomaly": False}, 0),
            (a1, {"temperature_c": 98.0, "is_anomaly": True, "anomaly_details": "Thermal Runaway"}, 2),
        ]

        ranked = PrioritizationEngine.rank_assets(data)

        self.assertEqual(len(ranked), 3)
        self.assertEqual(ranked[0]["asset_tag"], "FL-042")
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertEqual(ranked[0]["urgency"], "IMMEDIATE")
        self.assertGreater(ranked[0]["priority_score"], ranked[1]["priority_score"])
        self.assertEqual(ranked[2]["asset_tag"], "FL-002")


if __name__ == "__main__":
    unittest.main()
