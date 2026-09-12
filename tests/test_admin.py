import unittest
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from backend.models import TransformerAsset, Alert


class TestAdminRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_db_status_endpoint(self):
        res = self.client.get("/api/admin/db-status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "online")
        self.assertIn("table_counts", data)
        self.assertIn("transformer_assets", data["table_counts"])

    def test_clean_demo_records_unauthorized(self):
        res = self.client.post("/api/admin/clean-demo-records")
        self.assertEqual(res.status_code, 401)

    def test_clean_demo_records_authorized(self):
        # Insert a sample asset
        from datetime import date
        asset = TransformerAsset(
            asset_tag="TEST-999",
            name="Sample Transformer",
            substation="Substation A",
            location="Zone 1",
            installation_date=date.today(),
            manufacturer="ABB",
            model_number="M-100",
            rated_capacity_kva=500.0,
            primary_voltage_kv=11.0,
            secondary_voltage_kv=0.415
        )
        db.session.add(asset)
        db.session.commit()
        self.assertEqual(TransformerAsset.query.count(), 1)

        # Clean demo records
        res = self.client.post("/api/admin/clean-demo-records?token=faultlens-prod-clean-2026")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["is_clean_production"])
        self.assertEqual(data["remaining_counts"]["transformer_assets"], 0)
        self.assertEqual(TransformerAsset.query.count(), 0)


if __name__ == "__main__":
    unittest.main()
