import math
import numpy as np
from typing import Dict, Any, Tuple, List

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class PredictionEngine:
    """
    Machine Learning Failure Probability Engine for Electrical Transformers.
    Estimates 30-day failure probability (0-100%) using an interpretable model.
    Includes feature contribution analysis and honest prototype disclaimer.
    """
    MODEL_NAME = "Calibrated Industrial Logistic Classifier (Prototype)"
    DISCLAIMER = (
        "This prototype uses simulated/historical demonstration data. "
        "Real deployment requires validated utility data, calibrated models and domain-specific validation."
    )

    FEATURE_NAMES = [
        "temperature_c",
        "vibration_mms",
        "load_pct",
        "age_years",
        "previous_failures",
        "days_since_maintenance",
        "oil_quality_index",
    ]

    _model = None
    _scaler = None

    @classmethod
    def _initialize_model(cls):
        """Initializes and trains the model on synthetic transformer degradation data."""
        if cls._model is not None:
            return

        # Synthetic demonstration dataset reflecting transformer physics
        np.random.seed(42)
        n_samples = 800

        # Features: [temp, vib, load, age, prev_fails, days_maint, oil_quality]
        temp = np.random.normal(65.0, 15.0, n_samples).clip(35.0, 115.0)
        vib = np.random.normal(2.0, 1.0, n_samples).clip(0.5, 6.5)
        load = np.random.normal(70.0, 20.0, n_samples).clip(20.0, 125.0)
        age = np.random.uniform(1.0, 30.0, n_samples)
        prev_fails = np.random.poisson(0.8, n_samples).clip(0, 5)
        days_maint = np.random.uniform(30.0, 500.0, n_samples)
        oil_quality = (100.0 - (age * 1.2) - (temp * 0.2) + np.random.normal(0, 5, n_samples)).clip(30.0, 99.0)

        X = np.column_stack([temp, vib, load, age, prev_fails, days_maint, oil_quality])

        # Underlying physical log-odds function for failure
        z = (
            -5.5
            + 0.055 * (temp - 60.0)
            + 0.75 * (vib - 1.8)
            + 0.040 * (load - 65.0)
            + 0.060 * (age - 8.0)
            + 0.65 * prev_fails
            + 0.004 * (days_maint - 150.0)
            - 0.035 * (oil_quality - 85.0)
        )
        prob = 1.0 / (1.0 + np.exp(-z))
        y = (prob > 0.45).astype(int)

        if HAS_SKLEARN:
            cls._scaler = StandardScaler()
            X_scaled = cls._scaler.fit_transform(X)
            cls._model = LogisticRegression(C=1.0, solver="lbfgs")
            cls._model.fit(X_scaled, y)
        else:
            cls._model = "fallback"

    @classmethod
    def predict_failure_probability(cls, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Estimates failure probability (0.0 to 1.0) and decomposes prediction into feature contributions.
        """
        cls._initialize_model()

        temp = float(features.get("temperature_c", 65.0))
        vib = float(features.get("vibration_mms", 1.8))
        load = float(features.get("load_pct", 68.0))
        age = float(features.get("age_years", 6.0))
        prev_fails = float(features.get("previous_failures", 0.0))
        days_maint = float(features.get("days_since_maintenance", 120.0))
        oil_qual = float(features.get("oil_quality_index", 90.0))

        raw_vector = np.array([[temp, vib, load, age, prev_fails, days_maint, oil_qual]])

        if HAS_SKLEARN and cls._model != "fallback" and cls._scaler is not None:
            scaled_vector = cls._scaler.transform(raw_vector)
            prob = float(cls._model.predict_proba(scaled_vector)[0][1])
            coeffs = cls._model.coef_[0]
            feature_impacts = scaled_vector[0] * coeffs
        else:
            # Analytical sigmoid fallback
            z = (
                -5.5
                + 0.055 * (temp - 60.0)
                + 0.75 * (vib - 1.8)
                + 0.040 * (load - 65.0)
                + 0.060 * (age - 8.0)
                + 0.65 * prev_fails
                + 0.004 * (days_maint - 150.0)
                - 0.035 * (oil_qual - 85.0)
            )
            prob = float(1.0 / (1.0 + math.exp(-z)))
            feature_impacts = [
                0.055 * (temp - 60.0),
                0.75 * (vib - 1.8),
                0.040 * (load - 65.0),
                0.060 * (age - 8.0),
                0.65 * prev_fails,
                0.004 * (days_maint - 150.0),
                -0.035 * (oil_qual - 85.0),
            ]

        # Clamp bounds
        prob = max(0.01, min(0.99, prob))
        prob_pct = round(prob * 100.0, 1)

        # Classify probability tier
        if prob_pct >= 81.0:
            risk_tier = "CRITICAL"
        elif prob_pct >= 61.0:
            risk_tier = "HIGH"
        elif prob_pct >= 31.0:
            risk_tier = "MODERATE"
        else:
            risk_tier = "LOW"

        # Construct explainable feature importance table
        contributions = []
        labels = [
            "Winding Temperature",
            "Mechanical Vibration",
            "Operational Load",
            "Asset Service Age",
            "Historical Failure Recurrence",
            "Maintenance Interval Gap",
            "Dielectric Oil Quality",
        ]
        values = [
            f"{temp:.1f}°C",
            f"{vib:.2f} mm/s",
            f"{load:.1f}%",
            f"{age:.1f} yrs",
            f"{int(prev_fails)} faults",
            f"{int(days_maint)} days",
            f"{oil_qual:.1f}/100",
        ]

        for lbl, val, imp in zip(labels, values, feature_impacts):
            direction = "RISK_INCREASE" if imp > 0.05 else ("RISK_DECREASE" if imp < -0.05 else "NEUTRAL")
            contributions.append({
                "feature": lbl,
                "value": val,
                "importance_score": round(float(imp), 3),
                "direction": direction,
            })

        # Sort by absolute impact descending
        contributions.sort(key=lambda x: abs(x["importance_score"]), reverse=True)

        return {
            "failure_probability": round(prob, 3),
            "failure_probability_pct": prob_pct,
            "risk_tier": risk_tier,
            "feature_contributions": contributions,
            "model_name": cls.MODEL_NAME,
            "disclaimer": cls.DISCLAIMER,
        }
