# Documentation: `data_preparation.py`

## 1. Purpose
This script automates the downloading, normalization, and integration of external, open-source fraud datasets (PaySim and Kaggle UPI 2024). It serves as the fallback/supplementary data pipeline if the synthetic generator (`generate_training_dataset.py`) is not used, combining them into a unified training dataset.

## 2. Key Parameters & Constants

| Parameter | Value / Source | Description |
| :--- | :--- | :--- |
| `PAYSIM_URL` | `ealaxi/paysim1` (Kaggle) | A massive (4.8M+ rows) synthetic dataset of mobile money transactions based on African telemetry. Highly diverse but lacks Indian context. |
| `KAGGLE_UPI_DATASET` | `skullagos5246/upi...` | A smaller dataset (~1M rows) specifically mapping to Indian UPI transactions from 2024. Provides the necessary regional context. |
| `COMBINED_DATASET` | `combined_fraud_training_data.csv` | The final output file containing the merged and normalized data. |
| `Sampling Strategy` | 70% PaySim / 30% Kaggle UPI | The script samples 70% of its data from PaySim (for robust pattern diversity) and 30% from the UPI dataset (to ground the model in Indian realities). |

## 3. Core Logic / Workflow

### Step 1: Kaggle Authentication (`setup_kaggle_credentials`)
*   Checks if `~/.kaggle/kaggle.json` exists. Fails gracefully with instructions if missing.

### Step 2: Download Automation (`download_paysim`, `download_kaggle_upi`)
*   Uses the `subprocess` module to run the Kaggle CLI (`kaggle datasets download`).
*   Extracts the massive ZIP files into `backend/ml/data/`.

### Step 3: Schema Normalization (`normalize_paysim`, `normalize_kaggle_upi`)
*   **The Problem**: PaySim uses columns like `nameOrig` and `oldbalanceOrig`, while Kaggle UPI uses `amount (INR)`.
*   **The Fix**: Both dataframes are rigorously mapped to the ARGUS standard schema: `['transaction_type', 'amount', 'timestamp', 'is_fraud', 'merchant_category', 'device_type', 'state']`.
*   Missing fields (like `device_type` in PaySim) are imputed with default values (e.g., `'Unknown'`).

### Step 4: Dataset Integration (`combine_datasets`)
*   Shuffles both dataframes.
*   Extracts 70% of PaySim and 30% of Kaggle.
*   Concatenates them into a single pandas DataFrame.

### Step 5: Metadata Generation
*   Writes a companion `.json` file containing the total transaction count, global fraud rate, and source breakdowns for audit purposes.

## 4. Assumptions & Limitations
*   **Limitation**: Relies heavily on the Kaggle CLI and an active internet connection. If Kaggle changes its API or takes down the dataset, the pipeline breaks.
*   **Assumption**: The script assumes that missing data (like `device_type` in PaySim) can be safely defaulted without heavily skewing the machine learning model's understanding of those specific features.

## 5. Role in Architecture
This is a utility script used *only during the initial ML training phase*. It is completely decoupled from the real-time inference engine (`main.py` / `fraud_model.py`).
