# Documentation: `test_v4.py`

## 1. Purpose
This is a lightweight integration testing script for the V4 `FraudDetectionEngine`. It allows developers to instantly verify that the machine learning models (XGBoost, LightGBM, Isolation Forest) and the rule engine are loading correctly and outputting logical scores without spinning up the entire FastAPI server.

## 2. Test Cases
The script defines a static list of hardcoded dictionaries representing diverse payment scenarios:
1.  **LEGIT (grocery)**: A standard, low-value UPI transaction at a home city. Expected score: Low.
2.  **LEGIT (micro tea)**: A very small ₹15 transaction at a tea stall. Expected score: Very Low.
3.  **FRAUD (account takeover)**: High value, new device, 1100km away from home, new location. Expected score: High (Critical).
4.  **FRAUD (structuring)**: An abnormally large NetBanking transfer (₹9,90,000) that looks like structuring/layering. Expected score: High.
5.  **FRAUD (SIM swap)**: A massive UPI P2P transfer from a brand-new device, 1800km away, matching SIM swap heuristics. Expected score: High.

## 3. Execution & Output
Running `python test_v4.py` initializes the `FraudDetectionEngine`. It passes each mock transaction through the ensemble.
The output to the console displays:
*   The overall `risk_score` (0.0 to 1.0) and `risk_level`.
*   The individual breakdown of the XGBoost, LightGBM, and Isolation Forest scores.
*   The execution `latency_ms` (to verify the <20ms SLA).
*   Any specific heuristic rules triggered (e.g., `['velocity_high', 'new_device']`).

## 4. Role in Architecture
Serves as the primary sanity check during development. Before committing changes to feature engineering or model weights, a developer runs this script to ensure the core logic hasn't regressed.
