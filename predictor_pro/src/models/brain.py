import numpy as np
from scipy.stats import poisson

class BettingBrain:
    def predict_1x2(self, h_xg, a_xg):
        max_g = 6
        matrix = np.outer(poisson.pmf(range(max_g), h_xg), poisson.pmf(range(max_g), a_xg))
        return {
            "L": float(np.sum(np.tril(matrix, -1))),
            "E": float(np.sum(np.diag(matrix))),
            "V": float(np.sum(np.triu(matrix, 1)))
        }

    def find_value(self, probs, odds):
        return {k: (probs[k] * odds[k]) - 1 for k in odds if (probs[k] * odds[k]) > 1.10}
# Modificación en brain.py
def apply_absences(self, original_xg, absence_level):
    """
    absence_level: 0 (Sin bajas), 1 (Baja clave: -15%), 2 (Crisis: -30%)
    """
    reduction = {0: 1.0, 1: 0.85, 2: 0.70}
    return original_xg * reduction.get(absence_level, 1.0)