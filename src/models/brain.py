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
