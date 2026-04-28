# ARGUS Machine Learning Architecture: Deep Dive

This document provides a comprehensive breakdown of the Machine Learning architecture used in the ARGUS fraud detection platform. It explains the design decisions, the models chosen, the rejected alternatives, and how the ensemble operates in real-time.

---

## 1. The Ensemble Strategy: Why Multiple Models?

Fraud is not a single problem; it is a constantly evolving set of tactics. A single machine learning model is rarely sufficient because:
1.  **Supervised models** (like XGBoost) are great at catching *known* fraud patterns they have seen in training data.
2.  **Unsupervised models** are needed to catch *unknown* or "zero-day" fraud.
3.  **Heuristics/Rules** are needed for absolute compliance (e.g., "Always block transactions over ₹5,00,000 at 3 AM").

Therefore, ARGUS uses a **Weighted Ensemble** approach. During real-time inference (`fraud_model.py`), the final risk score is calculated by combining five distinct layers:

*   **30% Weight: XGBoost** (Supervised)
*   **25% Weight: LightGBM** (Supervised)
*   **15% Weight: Isolation Forest** (Unsupervised)
*   **15% Weight: Dynamic Behavior** (Statistical)
*   **15% Weight: Rule Engine** (Heuristic)

---

## 2. The Chosen Models: Deep Dive

### A. XGBoost (Extreme Gradient Boosting)
*   **Role**: The primary heavy-lifter for non-linear pattern recognition.
*   **How it works**: It builds decision trees sequentially. Each new tree focuses entirely on correcting the errors (residuals) made by the previous trees.
*   **Parameters Used**: `n_estimators=500` (builds 500 trees), `max_depth=8` (allows complex interactions between features), `learning_rate=0.05` (slowly converges to prevent overfitting).
*   **Why we chose it**: It is the undisputed king of structured, tabular data. It handles missing values natively and provides excellent precision on highly imbalanced datasets when trained with `aucpr` (Precision-Recall AUC).

### B. LightGBM (Light Gradient Boosting Machine)
*   **Role**: High-speed secondary classifier.
*   **How it works**: Unlike XGBoost which grows trees level-by-level, LightGBM grows trees leaf-wise (choosing the leaf with the largest loss to split). 
*   **Parameters Used**: `n_estimators=500`, `num_leaves=63`, `bagging_fraction=0.8` (uses 80% of data per iteration to prevent overfitting).
*   **Why we chose it**: It handles categorical features (like `merchant_category` or `device_type`) much faster and more efficiently than XGBoost. In an ensemble, mixing XGBoost and LightGBM often yields a higher F1-score than using either alone because they learn slightly different decision boundaries.

### C. Isolation Forest
*   **Role**: Zero-day anomaly detection.
*   **How it works**: It randomly selects a feature and a split value to isolate observations. Anomalies (fraud) are "few and different," meaning they get isolated very quickly (fewer splits) compared to normal transactions.
*   **Parameters Used**: `contamination=0.05` (we mathematically inform the model that we expect ~5% of future traffic to be anomalous).
*   **Why we chose it**: Supervised models fail when scammers invent a brand new tactic. Isolation Forest doesn't know what fraud looks like; it only knows what *normal* looks like. If a transaction looks weird, it flags it.

### D. Dynamic User Behavior Profiling (The Statistical Layer)
*   **How it works**: It maintains a rolling memory of a user's last 100 transactions in RAM. When a new transaction arrives, it calculates the **Z-Score** (how many standard deviations the amount is from the user's personal average).
*   **Why we chose it**: Global ML models generalize. A ₹50,000 transaction might be fraud for a college student, but totally normal for a business owner. This layer personalizes the AI to the specific user.

---

## 3. Rejected Alternatives & Their Cons

During architectural planning, several other ML algorithms were considered and rejected for the core synchronous <20ms blocking path:

| Alternative Model | Why it was Rejected (Cons) |
| :--- | :--- |
| **Random Forest** | Evaluates all trees independently. It requires much deeper trees to achieve XGBoost's accuracy on tabular data, which consumes massive amounts of RAM and slows down real-time inference latency. |
| **Deep Neural Networks (DNN)** | Deep learning is excellent for unstructured data (images, text, sequences), but routinely underperforms Gradient Boosting on structured tabular data. Furthermore, DNN inference on CPUs is too slow to meet our strict <20ms pre-authorization SLA. *(Note: We use an experimental PyTorch LSTM offline for sequence analysis, but not in the blocking path).* |
| **Support Vector Machines (SVM)** | Computationally disastrous for large datasets. Training an SVM on our 750,000 row dataset would take hours/days, and inference latency on high-dimensional feature spaces is too slow. |
| **Logistic Regression** | Too simplistic. It can only draw linear boundaries. It cannot understand complex interactions like "If amount > 1000 AND distance > 500km AND time == 3AM -> Fraud" without manual, exhaustive feature engineering. |

---

## 4. How the Ensemble is Trained (Offline)

The training pipeline (`train_model_v4.py`) executes several critical data science techniques before the models are deployed:
1.  **SMOTE (Synthetic Minority Over-sampling)**: Fraud only makes up 5% of the dataset. If untrained, the ML model will just guess "Not Fraud" 100% of the time and achieve 95% accuracy. SMOTE mathematically synthesizes fake fraud examples in the training set to bring the ratio up to 30%, forcing the models to learn fraud patterns.
2.  **Standard Scaling**: Numeric features (like amount and distance) are scaled so that Isolation Forest's distance-based math works correctly.
3.  **F1-Score Optimization**: The system sweeps through possible probability thresholds to find the exact cut-off that maximizes the F1-score (the harmonic mean of Precision and Recall), minimizing false declines while catching maximum fraud.

---

## 5. Limitations of the Current Implementation

1.  **Static Weights (No Online Learning)**: The models (`.joblib` files) are static. If scammers change tactics, the system relies entirely on the Isolation Forest and Dynamic Profiles until a data scientist manually re-runs the `train_model_v4.py` script on new data and redeploys the server.
2.  **Python GIL Bottlenecks**: Calling `xgboost.predict_proba()` and `lightgbm.predict_proba()` in Python is fast for a single transaction (~3ms), but under heavy load (10,000 TPS), Python's Global Interpreter Lock (GIL) will bottleneck the FastAPI server.
    *   *Enterprise Fix*: Convert the models to `ONNX` format and serve them via a dedicated C++ inference server like NVIDIA Triton.
3.  **Cold Start Problem**: The Dynamic Behavior layer requires a user to have at least 10 historical transactions to form a reliable baseline. Brand new users are heavily reliant on the generalized XGBoost/LightGBM models, making them slightly more susceptible to false positives.
