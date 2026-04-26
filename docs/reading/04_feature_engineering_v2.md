# Documentation: `feature_engineering_v2.py`

## 1. Purpose
This module is responsible for transforming raw transaction data into a rich, 40+ feature matrix. It uses historical baselines (demographic, geographic, device) and complex temporal combinations to feed highly discriminative signals into the XGBoost and LightGBM models.

## 2. Key Parameters & Constants (Baselines)
These dictionaries act as global "risk priors" (baseline probabilities of fraud) before the ML model even runs:

| Dictionary | Example Values | Reasoning |
| :--- | :--- | :--- |
| `MERCHANT_FRAUD_RATES` | `gambling`: 0.150, `jewellery`: 0.035, `grocery`: 0.003 | Hardcoded risk baselines indicating that buying crypto or gambling is inherently 50x riskier than buying groceries. |
| `STATE_FRAUD_RATES` | `DL` (Delhi): 0.018, `KL` (Kerala): 0.006 | Maps to historical cybercrime rates in India. Delhi and NCR regions historically exhibit higher digital fraud origination. |
| `DEVICE_FRAUD_RATES` | `Web`: 0.015, `iOS`: 0.005 | Web transactions are historically more vulnerable to scripted bot attacks compared to sandboxed mobile OS environments. |

## 3. Core Logic / Workflow (`EnhancedFeatureEngineer`)

The `engineer_features(df)` pipeline systematically adds features across 8 categories:

### 1. Temporal Features
*   Breaks down `timestamp` into `hour`, `day_of_week`, `is_weekend`, `is_night`, `is_suspicious_hour` (10 PM to 6 AM).

### 2. Demographic & Geographic Features
*   Maps `age_group` to the `AGE_FRAUD_RATES`.
*   Calculates `age_mismatch_score` (if a 60-year-old is suddenly sending money to an 18-year-old, the score spikes).
*   Calculates `is_cross_state` (if sender is in MH and receiver is in DL).

### 3. Device & Merchant Features
*   Flags `is_new_device`.
*   Flags `suspicious_device_network` (e.g., using 'Web' on 'WiFi' for a high-risk transaction).
*   Categorizes merchants into `is_high_risk_category` (Jewellery/Crypto) vs `is_low_risk_category` (Utilities).

### 4. Amount & Pattern Features
*   Buckets amounts into categories (`very_small` to `very_large`).
*   Calculates `amount_percentile` against the user's history.
*   Flags `is_suspicious_amount` (e.g., ₹99,999 - structuring just below ₹1L PAN card limits).
*   Calculates velocity metrics: `velocity_txn_per_hour` and `burst_txn_count_10min`.

### 5. Risky Combinations (Heuristic Cross-features)
*   **`late_night_jewelry`**: Night + Jewellery.
*   **`cross_state_high_risk`**: Cross state + High Risk Merchant.
*   **`web_wifi_jewelry`**: Web + Public WiFi + Jewellery.

## 4. Assumptions & Limitations
*   **Assumption**: The baseline fraud rates (`MERCHANT_FRAUD_RATES`, etc.) are static. In a true enterprise system, these would be dynamically updated via a nightly batch job calculating a rolling 90-day average from actual chargeback data.
*   **Limitation**: Pattern features like `velocity_txn_per_hour` are computationally expensive to calculate across a massive Pandas DataFrame using `groupby()`. This is fine for offline training but cannot be used during real-time inference (which is why `fraud_model.py` uses lightweight rolling caches instead).

## 5. Role in Architecture
This file is the **bridge between raw data and ML training**. It takes the output of `generate_training_dataset.py` (or `data_preparation.py`) and passes the 40+ engineered columns directly to `train_model_v4.py`.
