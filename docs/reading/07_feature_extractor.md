# Documentation: `feature_extractor.py`

## 1. Purpose
This file is the **Unified Feature Extractor** (v4.0). Its singular purpose is to take a raw JSON transaction payload and convert it into a flat, 34-dimensional NumPy array of floats (`np.ndarray(34,)`).

**Crucially, this file is the "Single Source of Truth."** It is imported by both `train_model_v4.py` (during offline training) and `fraud_model.py` (during real-time inference) to ensure there is zero drift between how features are calculated during training vs production.

## 2. Key Structure & Groupings
The 34 features are strictly ordered and grouped into 7 analytical domains:

1.  **Core Transaction (4)**: `amount`, `amount_log`, `balance_delta_ratio`, `amount_to_channel_limit_ratio`.
2.  **Channel & Category (6)**: Ordinal encodings and base risk scores for the specific payment method and merchant type.
3.  **Temporal (6)**: `hour`, `is_night`, `is_weekend`, `is_salary_period` (days 1-7), `is_month_end` (days 25+), and an `hour_sin` cyclical transformation (since 23:00 and 01:00 are close in time but far in integer value).
4.  **Device & Location (6)**: `is_new_device`, `device_age_hours`, `location_distance_km`, and a composite `dev_loc_risk` heuristic.
5.  **Behavioral (6)**: Relies heavily on the dynamic user profile: `amount_zscore`, `amount_deviation_ratio`, `txn_velocity`.
6.  **Regulatory (4)**: Checks if amounts exceed `upi_single` limits, are near the ₹10L `str_threshold` (Suspicious Transaction Report), or trigger `cooling_period_risk` (high amounts on a new account <24hrs old).
7.  **Merchant (2)**: `merchant_risk_score`, `is_new_beneficiary`.

## 3. Core Logic / Workflow (`extract_features`)

The function `extract_features(txn, user_profile, anomaly_info)` takes the raw dict and performs O(1) transformations:

*   **Handling Missing Data**: Every feature calculation has a safe fallback. If the timestamp is missing/malformed, it falls back to `datetime.now()`. If a category is unknown, it defaults to a base risk. This prevents inference crashes.
*   **Vectorization**: It does not use heavy pandas operations. It uses pure Python/math logic to build the array instantly, which is why it achieves sub-millisecond extraction times.
*   **Batch Support**: `extract_features_batch()` is provided as a wrapper to process arrays of transactions simultaneously for the training pipeline.

## 4. Assumptions & Limitations
*   **Limitation**: `balance_delta_ratio` is hardcoded to 0.0 because real-time bank balance lookups are usually too slow for the <20ms auth window in real life. It remains as a placeholder for future internal ledger integration.
*   **Assumption (Cyclical Time)**: `hour_sin` is used, but `hour_cos` is omitted. Typically, both sine and cosine are needed to perfectly encode cyclical time, but tree-based models (XGB/LGB) can often infer the boundary sufficiently with just the sine transform plus the raw `hour` integer.

## 5. Role in Architecture
It acts as the strict data contract between the API payload and the ML model tensors. `fraud_model.py` calls this right before running `.predict()` on the XGBoost model.
