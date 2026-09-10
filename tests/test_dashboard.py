import unittest
from datetime import date
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from backend.models import TransformerAsset, Alert, MaintenanceTask


class TestDashboardRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

            a1 = TransformerAsset(
                asset_tag="FL-042",
                name="Unit 42",
                substation="Substation A",
                location="Loc 1",
                installation_date=date(2018, 1, 1),
                manufacturer="Siemens",
                model_number="T-500",
                rated_capacity_kva=1000.0,
                health_status="CRITICAL",
                current_risk_score=88.0,
                failure_probability=0.88
            )
            a2 = TransformerAsset(
                asset_tag="FL-001",
                name="Unit 1",
                substation="Substation B",
                location="Loc 2",
                installation_date=date(2023, 1, 1),
                manufacturer="ABB",
                model_number="Pro-X",
                rated_capacity_kva=500.0,
                health_status="HEALTHY",
                current_risk_score=12.0,
                failure_probability=0.10
            )
            db.session.add_all([a1, a2])
            db.session.commit()

            # Seed task and alert
            task = MaintenanceTask(
                task_code="TASK-2026-001",
                asset_id=a1.id,
                title="Critical Thermal Overhaul",
                priority="CRITICAL",
                status="DETECTED"
            )
            alert = Alert(
                asset_id=a1.id,
                severity="CRITICAL",
                alert_type="TEMPERATURE_ANOMALY",
                title="Critical Heat Spike",
                message="Winding at 104°C",
                status="ACTIVE"
            )
            db.session.add_all([task, alert])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_dashboard_stats(self):
        res = self.client.get("/api/dashboard/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        m = data["metrics"]
        self.assertEqual(m["total_assets"], 2)
        self.assertEqual(m["critical"], 1)
        self.assertEqual(m["healthy"], 1)
        self.assertEqual(m["open_maintenance_tasks"], 1)
        self.assertEqual(m["active_alerts"], 1)
        self.assertEqual(len(data["risk_distribution"]), 4)

    def test_dashboard_priority_queue(self):
        res = self.client.get("/api/dashboard/priority")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("priority_assets", data)
        self.assertEqual(len(data["priority_assets"]), 2)
        # First asset must be the critical unit
        self.assertEqual(data["priority_assets"][0]["asset_tag"], "FL-042")
        self.assertEqual(data["priority_assets"][0]["rank"], 1)


if __name__ == "__main__":
    unittest.main()
