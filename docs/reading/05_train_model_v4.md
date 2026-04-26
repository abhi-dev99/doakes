# Documentation: `train_model_v4.py`

## 1. Purpose
This is the master training pipeline for ARGUS v4.0. It ingests the synthetic dataset (`argus_training_data.csv`), scales features, balances the classes, trains three distinct machine learning models (XGBoost, LightGBM, Isolation Forest), calculates optimal thresholds, and outputs 10 comprehensive evaluation plots alongside the final `.joblib` model weights.

## 2. Key Parameters & Architecture

### The Ensemble (v4.0 Architecture)
The final pre-authorization risk score is a weighted ensemble of three models:
*   **XGBoost (40% weight)**: Primary classifier. Excellent at finding non-linear patterns in tabular data.
*   **LightGBM (35% weight)**: Highly efficient classifier. Very good at handling categorical splits and runs faster than XGBoost on large datasets.
*   **Isolation Forest (25% weight)**: An *unsupervised* anomaly detector trained *only* on legitimate transactions. It looks for "zero-day" fraud patterns that don't match known fraud archetypes.

*(Note: The remaining 15% rule engine and 15% dynamic behavioral weights are applied in `fraud_model.py` during inference, not during this base training phase).*

### Hyperparameters
*   **XGBoost**: `n_estimators=500`, `max_depth=8`, `learning_rate=0.05`. Uses `aucpr` (Area Under Precision-Recall Curve) as the evaluation metric to heavily penalize false positives.
*   **LightGBM**: `n_estimators=500`, `num_leaves=63`, `max_depth=8`. Uses `bagging_fraction=0.8` to prevent overfitting.
*   **Isolation Forest**: `contamination=0.05` (assumes 5% of future data will be anomalies).

## 3. Core Logic / Workflow

### Step 1: Data Loading & Extraction (`load_and_extract_features`)
*   Loads 750K rows.
*   Iterates through every row, passing it to `feature_extractor.py` to convert raw JSON fields into a NumPy array of 34 numeric features. This is computationally heavy but ensures identical feature mappings between training and real-time inference.

### Step 2: Stratified Split (`split_data`)
*   Data is split 70% Train, 15% Validation, 15% Test.
*   **Stratification** ensures the 5% fraud rate is perfectly maintained across all three sets.

### Step 3: Scaling & Balancing (`train_models`)
*   **`StandardScaler`**: Normalizes all numerical features (crucial for Isolation Forest distance metrics).
*   **`SMOTE` (Synthetic Minority Over-sampling Technique)**: Because fraud is rare (5%), SMOTE mathematically generates synthetic fraud examples in the training set to bring the ratio up to 30%, forcing XGBoost/LightGBM to pay more attention to fraud signals.

### Step 4: Optimal Threshold Calculation (`find_optimal_threshold`)
*   The script uses the **Validation set** to find the exact classification threshold (0.0 to 1.0) that maximizes the **F1-Score**. This perfectly balances Precision (minimizing false customer declines) and Recall (catching maximum fraud).

### Step 5: Evaluation & Plotting (`generate_plots`)
*   Runs the trained models against the **Test set** (which it has never seen).
*   Generates 10 plots saved to `backend/ml/training_results/` including ROC curves, Precision-Recall curves, Confusion Matrices, and Feature Importance bar charts.

## 4. Assumptions & Limitations
*   **Limitation**: The model is trained statically. It does not natively support continuous online learning. To update the model, this entire script must be re-run on a fresh batch of data, causing downtime or requiring blue/green deployment.
*   **Assumption**: SMOTE assumes that new fraud instances will occur linearly between existing fraud instances in feature space. While effective, it cannot synthesize entirely new "zero-day" strategies (which is why Isolation Forest is included to compensate).

## 5. Role in Architecture
This is a core ML pipeline file, but it is executed **offline**. The outputs of this script (`xgb_model.joblib`, `lgb_model.joblib`, `scaler.joblib`) are directly loaded into RAM by `fraud_model.py` upon server startup for real-time inference.
