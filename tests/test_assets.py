import unittest
from datetime import date
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from backend.models import User, TransformerAsset


class TestAssetRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

            # Seed Admin and Viewer
            self.admin = User(username="admin_test", email="admin@test.com", role="ADMIN")
            self.admin.set_password("pass123")
            self.viewer = User(username="viewer_test", email="viewer@test.com", role="VIEWER")
            self.viewer.set_password("pass123")
            db.session.add_all([self.admin, self.viewer])
            db.session.commit()
            self.admin_id = self.admin.id
            self.viewer_id = self.viewer.id

            # Seed test assets
            self.asset1 = TransformerAsset(
                asset_tag="FL-042",
                name="Primary Heavy Feeder",
                substation="Metro Substation",
                location="Sector 1",
                installation_date=date(2018, 1, 1),
                manufacturer="Siemens",
                model_number="Troniq T-500",
                rated_capacity_kva=1250.0,
                current_status="MAINTENANCE_REQUIRED",
                health_status="CRITICAL",
                current_risk_score=87.0,
                failure_probability=0.87,
                previous_failure_count=3
            )
            self.asset2 = TransformerAsset(
                asset_tag="FL-005",
                name="Secondary Distribution Unit",
                substation="Metro Substation",
                location="Sector 2",
                installation_date=date(2022, 1, 1),
                manufacturer="ABB",
                model_number="TrafoStar",
                rated_capacity_kva=500.0,
                current_status="OPERATIONAL",
                health_status="HEALTHY",
                current_risk_score=15.0,
                failure_probability=0.12,
                previous_failure_count=0
            )
            db.session.add_all([self.asset1, self.asset2])
            db.session.commit()
            self.asset1_id = self.asset1.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_list_assets(self):
        res = self.client.get("/api/assets")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["assets"]), 2)
        self.assertEqual(data["pagination"]["total"], 2)

    def test_filter_assets_by_health(self):
        res = self.client.get("/api/assets?health=CRITICAL")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["assets"]), 1)
        self.assertEqual(data["assets"][0]["asset_tag"], "FL-042")

    def test_search_assets(self):
        res = self.client.get("/api/assets?search=042")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["assets"]), 1)
        self.assertEqual(data["assets"][0]["asset_tag"], "FL-042")

    def test_get_single_asset_profile(self):
        res = self.client.get(f"/api/assets/{self.asset1_id}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["asset"]["asset_tag"], "FL-042")
        self.assertIn("risk_analysis", data)
        self.assertIn("ml_prediction", data)
        self.assertGreater(len(data["risk_analysis"]["factors"]), 0)

    def test_create_asset_admin(self):
        headers = {"X-User-Id": str(self.admin_id)}
        res = self.client.post("/api/assets", headers=headers, json={
            "asset_tag": "FL-100",
            "name": "New Industrial Substation Transformer",
            "substation": "East Bay Substation",
            "location": "Berth 12",
            "manufacturer": "Schneider",
            "model_number=" : "Minera",
            "model_number": "Minera",
            "rated_capacity_kva": 1000.0,
            "installation_date": "2024-05-10"
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["asset"]["asset_tag"], "FL-100")

    def test_create_asset_forbidden_for_viewer(self):
        headers = {"X-User-Id": str(self.viewer_id)}
        res = self.client.post("/api/assets", headers=headers, json={
            "asset_tag": "FL-101",
            "name": "Unauthorized Transformer",
            "substation": "Sub 1",
            "location": "Loc 1",
            "manufacturer": "GE",
            "model_number": "GE-1",
            "rated_capacity_kva": 500.0,
        })
        self.assertEqual(res.status_code, 403)

    def test_update_asset(self):
        headers = {"X-User-Id": str(self.admin_id)}
        res = self.client.put(f"/api/assets/{self.asset1_id}", headers=headers, json={
            "name": "Updated Transformer Name",
            "current_status": "UNDER_MAINTENANCE"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["asset"]["name"], "Updated Transformer Name")
        self.assertEqual(data["asset"]["current_status"], "UNDER_MAINTENANCE")

    def test_delete_asset(self):
        headers = {"X-User-Id": str(self.admin_id)}
        res = self.client.delete(f"/api/assets/{self.asset1_id}", headers=headers)
        self.assertEqual(res.status_code, 200)
        get_res = self.client.get(f"/api/assets/{self.asset1_id}")
        self.assertEqual(get_res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
