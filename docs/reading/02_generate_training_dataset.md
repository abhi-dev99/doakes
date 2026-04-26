# Documentation: `generate_training_dataset.py`

## 1. Purpose
This script is the engine for generating the 750,000-row synthetic training dataset (`argus_training_data.csv`). It simulates normal Indian payment behavior and specifically injects 12 distinct, highly engineered "fraud archetypes" to train the machine learning models.

## 2. Key Parameters & Constants

| Parameter | Value | Description |
| :--- | :--- | :--- |
| `total` | 750,000 | The total number of transactions generated. |
| `fraud_rate` | 0.05 (5%) | The baseline percentage of transactions that are fraudulent (approx 37,500 rows). This is intentionally higher than real-world fraud rates (<0.1%) to ensure the ML models have enough positive samples to learn from without severe class imbalance. |
| `seed` | 42 | Ensures the generated dataset is identical every time the script is run (reproducibility). |
| `users` pool | 2,000 | Number of simulated distinct users. |
| `devices` pool| 800 | Number of simulated distinct devices. |

## 3. Core Logic / Workflow

### Step 1: Base Generation
The script uses `numpy` to generate log-normal distributions for transaction amounts. This creates a realistic "long tail" curve where most transactions are small (₹10-₹500), but a few are massive (₹1L+). It snaps these amounts to realistic human denominations (e.g., rounding ₹123.45 to ₹120 or ₹125).

### Step 2: Normal Transaction Generation (`generate_normal_txn`)
*   Picks a random user, channel, and category based on weights in `dataset_config.py`.
*   Assigns a location. 82% of the time, the transaction occurs in the user's `home_city`.
*   Calculates distance using Euclidean geometry (`math.sqrt`) between cities.
*   Assigns time using the `HOUR_WEIGHTS_NORMAL` distribution (peaks in the evening).

### Step 3: Fraud Injection (`generate_fraud_txn`)
This is the most critical part of the script. It explicitly models 12 fraud archetypes:
1.  **Account Takeover (20%)**: Large amounts on a new device, far from the home city.
2.  **Stolen Card (15%)**: High-risk categories (Jewellery, Electronics) on POS/Online, new device.
3.  **UPI Collect Scam (15%)**: Standard amounts on UPI, but high merchant risk score.
4.  **Digital Arrest (10%)**: Massive UPI/Netbanking transfers (₹50k-₹5L) to "P2P" with very old account ages (simulating older victims).
5.  **Sim Swap (10%)**: Very large transfers, brand new device (`device_age_hours < 2`), cross-state.
6.  **Mule Account (8%)**: Exact round amounts (₹10k, ₹50k), new account age (<45 days).
7.  **Velocity Attack (7%)**: Highly accelerated frequency of transactions.
8.  **Unusual Amount (5%)**: Transactions just below channel limits.
9.  **QR Tampering (3%)**: Local shops/retail with high merchant risk and new locations.
10. **Structuring (3%)**: Exact amounts just below the ₹10L reporting threshold (e.g., ₹9.9L, ₹9.5L) to evade FIU-IND triggers.
11. **Night Drain (2%)**: Back-to-back P2P transfers between 1 AM and 4 AM.
12. **Cross-State Anomaly (2%)**: Physical POS/ATM transactions occurring hundreds of miles from the user's last known location.

### Step 4: CSV Export
Iterates and writes 750K rows to `dataset/argus_training_data.csv`.

## 4. Assumptions & Limitations
*   **Limitation**: The distance calculation uses a simplified Euclidean multiplier (`* 111` km per degree) rather than the precise Haversine formula, which is acceptable for synthetic data but not perfectly geodetic.
*   **Assumption**: The `is_new_device` flag is randomly assigned a 4% probability for normal transactions, assuming occasional phone upgrades or secondary devices.

## 5. Role in Architecture
This file is run offline (prior to system deployment). The output CSV is consumed by `data_preparation.py` and `feature_engineering_v2.py` to eventually train the XGBoost and LightGBM models in `train_model_v4.py`.
