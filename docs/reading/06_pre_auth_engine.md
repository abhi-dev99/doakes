# Documentation: `pre_auth_engine.py`

## 1. Purpose
This module is the first line of defense in the ARGUS architecture. It implements a **Pre-Authorization Engine**. Unlike post-transaction batch analysis, this code runs *before* the transaction is authorized by the banking switch. Its goal is to make instantaneous (<20ms) decisions to `ALLOW`, `CHALLENGE` (trigger OTP/3DS/Biometrics), or `BLOCK` a transaction outright.

## 2. Key Parameters & Constants

| Constant | Value | Description |
| :--- | :--- | :--- |
| `BLOCK_THRESHOLD` | 0.85 (85% Risk) | Any transaction hitting this total risk score is instantly rejected. |
| `CHALLENGE_THRESHOLD` | 0.60 (60% Risk) | Triggers step-up authentication. >=0.75 triggers `BIOMETRIC`, >=0.65 triggers `3DS`, else `OTP`. |
| `VelocityTracker.limits` | `1min`: 5 txns / ₹50K. `5min`: 15 txns / ₹1.5L. | In-memory limits for velocity attacks. If a user exceeds 5 txns in 60 seconds, they are blocked. |

## 3. Core Logic / Workflow (`check_pre_authorization`)

When a transaction hits the API, the engine executes 5 sequential heuristic checks *before* calling the heavy ML models:

1.  **Blacklist Check**: Instant rejection if the `user_id`, `device_id`, or `ip_address` matches known bad actors.
2.  **Velocity Tracking (`VelocityTracker`)**: Checks the rate of transactions across 1m, 5m, 1h, and 24h windows. Crucially, it also checks **Cross-Entity Velocity** (e.g., if >3 unique users are logging in from the same `device_id` in a short window, it flags it as an Account Takeover).
3.  **Impossible Travel (`GeoAnalyzer`)**: Calculates Haversine distance between the user's last known location and current IP location. If the speed required to cover the distance exceeds 900 km/h (commercial flight speed), it blocks for impossible travel. It also flags VPN/Tor usage.
4.  **Device Analysis (`DeviceAnalyzer`)**: Detects headless browsers (bot automation) or device emulators via fingerprint anomalies.
5.  **Merchant Risk (`MerchantRiskScorer`)**: Hardcoded risk scores for categories like Crypto or Gambling, combined with simulated merchant chargeback rates.

**Risk Aggregation**:
It calculates a weighted sum of these heuristic risks:
`Velocity (30%) + Geo (25%) + Device (20%) + Merchant (15%) + Amount (10%) = Total Risk`

## 4. Assumptions & Limitations
*   **Limitation (State Management)**: Currently, `VelocityTracker`, `GeoAnalyzer`, and `MerchantRiskScorer` store state in python dictionaries (in-memory). In a multi-worker production environment (like Uvicorn with 4+ workers), this state would not be shared. The roadmap assumes swapping these dictionaries for a centralized Redis cluster.
*   **Assumption**: Relies on accurate incoming context (`user_context`, `device_context`, `geo_context`). If the upstream gateway fails to provide IP addresses, the GeoAnalyzer degrades gracefully but loses efficacy.

## 5. Role in Architecture
This engine is called directly by `main.py` (the FastAPI entrypoint) upon receiving a `/api/v1/transaction/pre-auth` request. If this engine returns `BLOCK`, the request is terminated immediately, entirely bypassing the ML models in `fraud_model.py` to save compute resources.
