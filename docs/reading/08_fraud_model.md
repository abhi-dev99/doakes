# Documentation: `fraud_model.py`

## 1. Purpose
This is the core execution brain of the ARGUS platform during real-time inference. It is responsible for loading the pre-trained ML models into memory, maintaining stateful "Dynamic User Behavior Profiles," evaluating transactions against both ML models and Indian-specific rules, and outputting the final comprehensive Risk Score.

## 2. Key Architecture: The V4 Ensemble

The engine aggregates 5 distinct intelligence layers to calculate the final score:

1.  **XGBoost (30%)**: Loaded from `xgb_model.joblib`. Handles non-linear pattern matching.
2.  **LightGBM (25%)**: Loaded from `lgb_model.joblib`. Handles categorical feature splits rapidly.
3.  **Isolation Forest (15%)**: Loaded from `isolation_forest.joblib`. Unsupervised anomaly detection for zero-day fraud patterns.
4.  **Rule Engine (15%)**: Hardcoded heuristic logic checking against `IndiaThresholds`.
5.  **Dynamic Behavior (15%)**: Real-time evaluation of how the transaction deviates from the user's personal 30-day history.

## 3. Core Component: `UserBehaviorProfile`

This is a critical innovation to solve the "static threshold" problem. Instead of blocking every ₹50,000 transaction, the system learns if ₹50,000 is normal for a specific user.

*   **Stateful Tracking**: It maintains rolling memory (`deque(maxlen=100)`) of a user's recent `transaction_amounts` and `transaction_timestamps`.
*   **Dynamic Updating**: On every transaction, it recalculates the user's `avg_amount`, `std_amount`, and daily totals.
*   **Maturity**: A profile is considered `is_mature = False` until the user hits 10 transactions. Until then, the system relies more on global ML defaults than personalized behavioral deviations.
*   **Persistence**: Profiles are saved to `backend/ml/models/user_profiles.json` every 60 seconds (`_save_interval`). Upon server restart, if the JSON is missing, it runs `_rebuild_profiles_from_db()` to reconstruct the state from the SQLite `transactions` table.

## 4. Core Logic / Workflow (`analyze_transaction`)

1.  **Context Retrieval**: Gets or creates the `UserBehaviorProfile` for the `user_id`.
2.  **Behavioral Check**: Calls `add_transaction()` on the profile to get `anomaly_info` (Z-scores, percentile ranks).
3.  **Extraction**: Passes the raw dict, the profile, and the anomaly info to `extract_features()` (from `feature_extractor.py`) to generate the 34-feature array.
4.  **Inference execution**:
    *   `xgb.predict_proba()`
    *   `lgb.predict_proba()`
    *   `iso.decision_function()`
5.  **Rule Execution**: `_apply_rules()` checks for high value thresholds, weird hours, etc.
6.  **Ensemble Math**: Multiplies each score by its defined weight (30/25/15/15/15) to generate the `final_score`.
7.  **Sub-Module Execution**: Triggers the `UPIFraudDetector` (if available) to look specifically for UPI-scam archetypes. Boosts the final score if a positive hit occurs.
8.  **Output**: Maps the final score to a `risk_level` (LOW/MEDIUM/HIGH/CRITICAL) and returns a massive metadata payload for the frontend and XAI systems.

## 5. Assumptions & Limitations
*   **Limitation (Latency vs Scale)**: Calling `.predict_proba()` on XGBoost and LightGBM sequentially for a single row takes roughly 2-4ms. At 10,000 TPS, Python's GIL would heavily bottleneck this. In a true enterprise deployment, these models would be exported to ONNX format or served via NVIDIA Triton.
*   **Assumption (In-Memory State)**: Keeping `UserBehaviorProfile`s in a Python dictionary limits the application to a single node. A real deployment requires migrating this behavioral state to a Redis cluster (RedisTimeSeries) so multiple FastAPI worker nodes can read/write the profile simultaneously.

## 6. Role in Architecture
Instantiated as a singleton via `get_pre_auth_engine()` (Wait, this is an error in my thought, it's actually `fraud_model.py` instantiated as `get_fraud_engine()` in `main.py`). It is the final authority on transaction risk, providing the numbers that drive the XAI and case management pipelines.
