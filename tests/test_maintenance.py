import unittest
from datetime import date
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from backend.models import User, TransformerAsset, MaintenanceTask, MaintenanceRecord


class TestMaintenanceWorkflow(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

            self.admin = User(username="admin_user", email="admin@test.com", role="ADMIN")
            self.admin.set_password("pass123")
            self.tech = User(username="tech_user", email="tech@test.com", role="TECHNICIAN")
            self.tech.set_password("pass123")
            db.session.add_all([self.admin, self.tech])
            db.session.commit()
            self.admin_id = self.admin.id
            self.tech_id = self.tech.id

            self.asset = TransformerAsset(
                asset_tag="FL-042",
                name="Primary Unit",
                substation="Substation A",
                location="Loc 1",
                installation_date=date(2019, 1, 1),
                manufacturer="Siemens",
                model_number="T-500",
                rated_capacity_kva=500.0,
            )
            db.session.add(self.asset)
            db.session.commit()
            self.asset_id = self.asset.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_create_maintenance_task(self):
        headers = {"X-User-Id": str(self.tech_id)}
        res = self.client.post("/api/maintenance/tasks", headers=headers, json={
            "asset_id": self.asset_id,
            "title": "Perform DGA and Oil Degassing",
            "priority": "HIGH",
            "notes": "Dissolved gas analysis revealed trace acetylene."
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn("TASK-", data["task"]["task_code"])
        self.assertEqual(data["task"]["status"], "DETECTED")

    def test_7_stage_workflow_progression(self):
        headers_tech = {"X-User-Id": str(self.tech_id)}
        headers_admin = {"X-User-Id": str(self.admin_id)}

        # 1. Create task
        res = self.client.post("/api/maintenance/tasks", headers=headers_tech, json={
            "asset_id": self.asset_id,
            "title": "Bushing Renewal",
            "priority": "CRITICAL"
        })
        task_id = res.get_json()["task"]["id"]

        # 2. Advance to RISK_ASSESSED
        res = self.client.put(f"/api/maintenance/tasks/{task_id}/status", headers=headers_tech, json={
            "status": "RISK_ASSESSED"
        })
        self.assertEqual(res.get_json()["task"]["status"], "RISK_ASSESSED")

        # 3. Advance to INSPECTION_REQUIRED
        res = self.client.put(f"/api/maintenance/tasks/{task_id}/status", headers=headers_tech, json={
            "status": "INSPECTION_REQUIRED"
        })
        self.assertEqual(res.get_json()["task"]["status"], "INSPECTION_REQUIRED")

        # 4. Advance to ASSIGNED
        res = self.client.put(f"/api/maintenance/tasks/{task_id}/status", headers=headers_tech, json={
            "status": "ASSIGNED"
        })
        self.assertEqual(res.get_json()["task"]["status"], "ASSIGNED")

        # 5. Advance to IN_PROGRESS
        res = self.client.put(f"/api/maintenance/tasks/{task_id}/status", headers=headers_tech, json={
            "status": "IN_PROGRESS"
        })
        self.assertEqual(res.get_json()["task"]["status"], "IN_PROGRESS")

        # 6. Advance to RESOLVED
        res = self.client.put(f"/api/maintenance/tasks/{task_id}/status", headers=headers_tech, json={
            "status": "RESOLVED",
            "resolution_notes": "Bushing replaced, oil filled and pressure tested."
        })
        self.assertEqual(res.get_json()["task"]["status"], "RESOLVED")

        # 7. Advance to VERIFIED (Admin only)
        res_tech_fail = self.client.put(f"/api/maintenance/tasks/{task_id}/status", headers=headers_tech, json={
            "status": "VERIFIED"
        })
        self.assertEqual(res_tech_fail.status_code, 403)

        res_admin_pass = self.client.put(f"/api/maintenance/tasks/{task_id}/status", headers=headers_admin, json={
            "status": "VERIFIED"
        })
        self.assertEqual(res_admin_pass.status_code, 200)
        self.assertEqual(res_admin_pass.get_json()["task"]["status"], "VERIFIED")

        # Ensure completed record was created in MaintenanceRecord
        with self.app.app_context():
            records = MaintenanceRecord.query.filter_by(asset_id=self.asset_id).all()
            self.assertGreaterEqual(len(records), 1)


if __name__ == "__main__":
    unittest.main()
