import unittest
from datetime import date
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from backend.models import User, TransformerAsset, IncidentReport, Alert


class TestReportsAndAlerts(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

            self.user = User(username="field_tech", email="tech@test.com", role="TECHNICIAN")
            self.user.set_password("pass123")
            db.session.add(self.user)
            db.session.commit()
            self.user_id = self.user.id

            self.asset = TransformerAsset(
                asset_tag="FL-042",
                name="Test Unit",
                substation="Metro Substation",
                location="Loc 1",
                installation_date=date(2019, 1, 1),
                manufacturer="Siemens",
                model_number="T-500",
                rated_capacity_kva=500.0,
                current_risk_score=40.0
            )
            db.session.add(self.asset)
            db.session.commit()
            self.asset_id = self.asset.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_submit_report_and_risk_escalation(self):
        headers = {"X-User-Id": str(self.user_id)}
        res = self.client.post("/api/reports", headers=headers, json={
            "asset_id": self.asset_id,
            "category": "VIBRATION",
            "severity": "CRITICAL",
            "title": "Severe mechanical harmonics detected",
            "description": "Core bolts rattling violently during peak morning shift."
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()

        # Risk score must be calculated and updated
        self.assertGreater(data["updated_risk_score"], 20.0)
        # Critical report generates alert
        self.assertGreaterEqual(len(data["alerts_triggered"]), 1)

    def test_alerts_lifecycle(self):
        headers = {"X-User-Id": str(self.user_id)}
        with self.app.app_context():
            alert = Alert(
                asset_id=self.asset_id,
                severity="CRITICAL",
                alert_type="TEMPERATURE_ANOMALY",
                title="Thermal Runaway Alert",
                message="Winding temperature exceeded 100°C.",
                status="ACTIVE"
            )
            db.session.add(alert)
            db.session.commit()
            alert_id = alert.id

        # 1. Check alert is in active list
        res = self.client.get("/api/alerts?status=ACTIVE")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()["alerts"]), 1)

        # 2. Acknowledge alert
        res_ack = self.client.put(f"/api/alerts/{alert_id}/acknowledge", headers=headers)
        self.assertEqual(res_ack.status_code, 200)
        self.assertEqual(res_ack.get_json()["alert"]["status"], "ACKNOWLEDGED")

        # 3. Resolve alert
        res_res = self.client.put(f"/api/alerts/{alert_id}/resolve", headers=headers)
        self.assertEqual(res_res.status_code, 200)
        self.assertEqual(res_res.get_json()["alert"]["status"], "RESOLVED")


if __name__ == "__main__":
    unittest.main()
