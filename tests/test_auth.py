import unittest
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from backend.models import User, TransformerAsset


class TestAppInitialization(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_app_created(self):
        self.assertIsNotNone(self.app)
        self.assertTrue(self.app.config["TESTING"])

    def test_landing_page_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"FAULTLENS", response.data)


class TestAuthRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            # Seed an admin user
            admin = User(username="admin_user", email="admin@test.internal", role="ADMIN")
            admin.set_password("pass123")
            db.session.add(admin)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_user_registration(self):
        res = self.client.post("/api/auth/register", json={
            "username": "tech1",
            "email": "tech1@test.internal",
            "password": "techpassword",
            "role": "TECHNICIAN",
            "full_name": "Tech Operator"
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["user"]["username"], "tech1")
        self.assertEqual(data["user"]["role"], "TECHNICIAN")

    def test_duplicate_registration_fails(self):
        res = self.client.post("/api/auth/register", json={
            "username": "admin_user",
            "email": "different@test.internal",
            "password": "somepassword"
        })
        self.assertEqual(res.status_code, 409)

    def test_login_success(self):
        res = self.client.post("/api/auth/login", json={
            "username": "admin_user",
            "password": "pass123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["user"]["username"], "admin_user")

    def test_login_bad_password(self):
        res = self.client.post("/api/auth/login", json={
            "username": "admin_user",
            "password": "wrongpassword"
        })
        self.assertEqual(res.status_code, 401)

    def test_me_endpoint_unauthenticated(self):
        res = self.client.get("/api/auth/me")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["authenticated"])

    def test_logout(self):
        self.client.post("/api/auth/login", json={"username": "admin_user", "password": "pass123"})
        res = self.client.post("/api/auth/logout")
        self.assertEqual(res.status_code, 200)
        me_res = self.client.get("/api/auth/me")
        self.assertFalse(me_res.get_json()["authenticated"])


if __name__ == "__main__":
    unittest.main()
