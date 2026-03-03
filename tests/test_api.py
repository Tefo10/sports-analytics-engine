import importlib.util
import unittest

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None
TESTCLIENT_INSTALLED = False
API_IMPORT_ERROR = None

if FASTAPI_INSTALLED:
    try:
        from fastapi.testclient import TestClient

        TESTCLIENT_INSTALLED = True
    except Exception as exc:
        API_IMPORT_ERROR = exc

if FASTAPI_INSTALLED and TESTCLIENT_INSTALLED:
    try:
        import api
    except Exception as exc:
        API_IMPORT_ERROR = exc


@unittest.skipUnless(FASTAPI_INSTALLED and TESTCLIENT_INSTALLED, "fastapi/testclient no disponible")
@unittest.skipIf(API_IMPORT_ERROR is not None, f"No se pudo importar API: {API_IMPORT_ERROR}")
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(api.app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_teams_endpoint(self):
        response = self.client.get("/teams")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreaterEqual(len(body), 20)
        self.assertIn("name", body[0])
        self.assertIn("atk", body[0])
        self.assertIn("def", body[0])

    def test_predict_endpoint_schema(self):
        payload = {
            "home_name": "Real Madrid",
            "away_name": "Barcelona",
            "home_attack_power": 2.1,
            "away_defense_weakness": 1.1,
            "odds": {"L": 2.1, "E": 3.3, "V": 3.8},
        }
        response = self.client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("probabilities", body)
        self.assertIn("value_found", body)


if __name__ == "__main__":
    unittest.main()
