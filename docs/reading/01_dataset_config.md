# Documentation: `dataset_config.py`

## 1. Purpose
This file serves as the master configuration dictionary for generating synthetic, yet highly realistic, Indian transaction data. It hardcodes all the foundational constants, weights, and regulatory limits calibrated to 2024 NPCI data and RBI guidelines.

## 2. Key Parameters & Constants

| Constant | Description | Key Values & Reasoning |
| :--- | :--- | :--- |
| `INDIAN_CITIES` | List of 30 major Indian cities grouped by Tier (1, 2, 3). | **Tier 1 (59% weight)**: Mumbai (15%), Delhi (12%), Bangalore (10%). Reflects the heavy concentration of digital payments in metros. Includes accurate latitude/longitude for geospatial velocity calculations. |
| `CHANNELS` | Payment channels and their allowed categories. | **UPI (55%)**: ₹1 to ₹1L. **POS (15%)**: ₹20 to ₹5L. **Card Online (12%)**: ₹49 to ₹2L. **Netbanking (8%)**: ₹500 to ₹10L. Captures the dominance of UPI for micro/small payments and Netbanking for large transfers. |
| `CATEGORY_AMOUNTS` | Min/Max transaction values per merchant category. | E.g., `Tea/Snacks`: ₹5-150. `Property`: ₹50,000-₹10L. Calibrated to realistic Indian spending habits. |
| `CHANNEL_RISK` / `CATEGORY_RISK` | Inherent risk weights for specific channels and categories. | `Card Online` (0.32) is riskier than `UPI` (0.12). `Jewellery` (0.45) and `Cryptocurrency` (implied high) are highest risk; `Tea/Snacks` (0.01) is lowest. |
| `REGULATORY_LIMITS` | Hard limits defined by RBI/NPCI. | `upi_single`: ₹100k. `str_threshold`: ₹10L (FIU-IND Suspicious Transaction Report). `upi_new_user_24h`: ₹5k (NPCI mandate). Used by the `pre_auth_engine.py` for immediate blocking. |
| `HOUR_WEIGHTS` | Probability distribution of transactions across 24 hours. | `NORMAL`: Peaks at 18-23 (evening). `FRAUD`: Peaks at 0-5 AM (dead night). This is crucial for temporal anomaly detection. |

## 3. Core Logic / Workflow
This file contains very little executable logic. The only function is:
*   **`is_valid_channel_category(channel, category)`**: A helper function that ensures transactions make logical sense (e.g., preventing a "Cash Withdrawal" on the "UPI" channel, which is impossible).

## 4. Assumptions & Limitations
*   **Assumption**: The weight distributions (e.g., 55% UPI) are static representations of 2024 data. In reality, these shift daily.
*   **Limitation**: Only 30 cities are defined. Transactions outside these 30 cities are not natively simulated, meaning the geospatial logic is slightly constrained to urban/semi-urban hubs.

## 5. Role in Architecture
This file is the **foundation of the simulation layer**. It is imported exclusively by `generate_training_dataset.py` (to build the 750K training rows) and `simulator/transaction_gen.py` (to generate the real-time live traffic stream).
