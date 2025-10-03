from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
import shap

FEATURES = ["age","sex_male","dx_chf","los_days","prior_admits","meds_count","hr_rest","spo2_min","steps_sum","sleep_eff"]

@dataclass
class ReadmissionModel:
    model: LogisticRegression = None
    auc: float = None
    explainer: shap.Explainer = None

    def train_synthetic(self, n: int = 2000, seed: int = 0):
        rng = np.random.default_rng(seed)
        df = pd.DataFrame({
            "age": rng.integers(40, 90, n),
            "sex_male": rng.integers(0, 2, n),
            "dx_chf": rng.integers(0, 2, n),
            "los_days": rng.integers(1, 11, n),
            "prior_admits": rng.integers(0, 5, n),
            "meds_count": rng.integers(1, 12, n),
            "hr_rest": rng.normal(78, 10, n),
            "spo2_min": rng.normal(94, 2.5, n),
            "steps_sum": rng.integers(0, 8000, n),
            "sleep_eff": rng.normal(0.85, 0.07, n).clip(0.5, 0.98),
        })
        # synthetic ground truth: higher risk with high age, CHF, long LOS, low SpO2, low steps
        z = (
            0.02*(df["age"]-65) +
            0.7*df["dx_chf"] +
            0.1*(df["los_days"]-4) +
            0.4*(df["prior_admits"]) +
            0.03*(df["meds_count"]) +
            0.03*(df["hr_rest"]-78) +
            -0.2*(df["spo2_min"]-94) +
            -0.00008*(df["steps_sum"]-3000) +
            -0.8*(df["sleep_eff"]-0.85)
        )
        p = 1 / (1 + np.exp(-z))
        y = (p > 0.5).astype(int)

        X_train, X_test, y_train, y_test = train_test_split(df[FEATURES], y, test_size=0.2, random_state=seed)
        model = LogisticRegression(max_iter=200)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:,1]
        auc = roc_auc_score(y_test, proba)

        self.model = model
        self.auc = float(auc)
        self.explainer = shap.LinearExplainer(model, X_train, feature_names=FEATURES)

    def predict_with_explain(self, features: Dict) -> Tuple[float, pd.DataFrame]:
        X = np.array([[features[k] for k in FEATURES]], dtype=float)
        proba = float(self.model.predict_proba(X)[0,1])
        shap_values = self.explainer(X).values[0]
        df = pd.DataFrame({
            "feature": FEATURES,
            "value": [features[k] for k in FEATURES],
            "shap": shap_values,
        })
        df["abs_shap"] = df["shap"].abs()
        return proba, df
