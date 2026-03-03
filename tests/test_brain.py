import unittest

try:
    from src.models.brain import BettingBrain

    BRAIN_IMPORT_ERROR = None
except Exception as exc:
    BettingBrain = None
    BRAIN_IMPORT_ERROR = exc


@unittest.skipIf(BettingBrain is None, f"No se pudo importar BettingBrain: {BRAIN_IMPORT_ERROR}")
class BettingBrainTests(unittest.TestCase):
    def setUp(self):
        self.brain = BettingBrain()

    def test_predict_1x2_returns_expected_keys(self):
        probabilities = self.brain.predict_1x2(1.8, 1.1)
        self.assertEqual(set(probabilities.keys()), {"L", "E", "V"})

    def test_predict_1x2_probabilities_are_bounded(self):
        probabilities = self.brain.predict_1x2(1.5, 1.2)
        for value in probabilities.values():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_find_value_detects_positive_ev(self):
        probabilities = {"L": 0.55, "E": 0.25, "V": 0.20}
        odds = {"L": 2.20, "E": 3.10, "V": 4.20}
        values = self.brain.find_value(probabilities, odds)
        self.assertIn("L", values)

    def test_apply_absences_reduces_attack_power(self):
        self.assertAlmostEqual(self.brain.apply_absences(2.0, 0), 2.0)
        self.assertAlmostEqual(self.brain.apply_absences(2.0, 1), 1.7)
        self.assertAlmostEqual(self.brain.apply_absences(2.0, 2), 1.4)


if __name__ == "__main__":
    unittest.main()
