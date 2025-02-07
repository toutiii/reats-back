from django.test import TestCase
from rest_framework.test import APIClient


class HealthCheckTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_check(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.data)
        self.assertIn("database", response.data)
        self.assertEqual(response.data["status"], "ok")
