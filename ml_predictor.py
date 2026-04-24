import numpy as np
from sklearn.linear_model import LinearRegression

class MLPredictor:
    def __init__(self):
        self.model = LinearRegression()
        self._trained = False
        self._t0 = None  # epoch seconds baseline

    def train(self, history):
        """
        Train on rows shaped like (time, process_id, used_mb).

        Uses time normalized to seconds since first sample to avoid huge epoch values.
        """
        if not history or len(history) < 2:
            self._trained = False
            return False

        times = np.array([int(h[0]) for h in history], dtype=np.int64)
        y = np.array([float(h[2]) for h in history], dtype=np.float64)

        self._t0 = int(times.min())
        X = (times - self._t0).astype(np.float64).reshape(-1, 1)

        self.model.fit(X, y)
        self._trained = True
        return True

    def predict(self, time):
        if not self._trained or self._t0 is None:
            raise RuntimeError("Model is not trained yet")

        x = np.array([[float(int(time) - int(self._t0))]], dtype=np.float64)
        return int(self.model.predict(x)[0])
