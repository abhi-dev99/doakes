# ARGUS: Backend Core Contribution Breakdown (4-Person Team)

Since the backend is the core of the project, this breakdown focuses exclusively on the Python Machine Learning, Data Science, and Infrastructure modules. It divides the technical responsibilities among four backend engineers.

---

## Person 1: Data Engineer (Synthetic Generation & Data Foundation)
**Primary Focus**: The "Data Source" and Schema definition.
*   **Core Modules**: `generate_training_dataset.py`, `data_preparation.py`, `dataset_config.py`.
*   **Key Responsibilities**:
    *   **Synthetic Logic**: Architected the 750,000-row simulation engine that generates realistic Indian payment patterns.
    *   **Domain Configuration**: Defined the `dataset_config` thresholds for Indian cities, merchant categories, and payment channel limits (UPI, ATM, Cards).
    *   **ETL Pipeline**: Built the cleaning and normalization scripts that ingest raw synthetic and Kaggle data into a unified ML-ready schema.
    *   **Scale Management**: Optimized CSV chunking and memory management to handle large-scale dataset extraction.

## Person 2: ML Scientist (Model Pipeline & Optimization)
**Primary Focus**: The "Predictive Intelligence" and Model performance.
*   **Core Modules**: `train_model_v4.py`, `feature_engineering_v2.py`, `deep_learning_model.py`.
*   **Key Responsibilities**:
    *   **Supervised Learning**: Implemented the **XGBoost and LightGBM** classifiers, focusing on non-linear pattern matching.
    *   **Class Imbalance**: Applied **SMOTE** (Synthetic Minority Over-sampling) to address the rare 5% fraud distribution in the training data.
    *   **Evaluation**: Developed the F1-Score threshold optimization logic and the comprehensive plotting suite (ROC, PR Curves, Feature Importance).
    *   **Temporal Sequences**: Built the experimental **PyTorch LSTM/Transformer** sequence models for analyzing account escalations over time.

## Person 3: Core Engine Developer (Real-time Inference & Graph Analysis)
**Primary Focus**: The "Execution Brain" and Network Topology.
*   **Core Modules**: `fraud_model.py`, `feature_extractor.py`, `graph_fraud_detector.py`.
*   **Key Responsibilities**:
    *   **Ensemble Orchestration**: Built the master `FraudDetectionEngine` that aggregates scores from ML models, rules, and behavioral baselines.
    *   **Feature Extraction**: Developed the sub-20ms live feature extractor that maps raw API payloads to the 34-feature ML vector.
    *   **Network Intelligence**: Architected the **Graph-based Ring Detector** using NetworkX to identify cyclic fund flows (A -> B -> C -> A) and mule clusters.
    *   **Behavioral Profiling**: Implemented the stateful **UserBehaviorProfile** system to track rolling Z-scores of user activity in RAM.

## Person 4: Infrastructure & Fraud Intelligence Engineer (API & India-Specific Logic)
**Primary Focus**: The "Connectivity" and Domain Heuristics.
*   **Core Modules**: `main.py`, `upi_fraud_patterns.py`, `pre_auth_engine.py`, `phishing_protection.py`, `alert_notifications.py`.
*   **Key Responsibilities**:
    *   **API Infrastructure**: Developed the **FastAPI and WebSocket server**, ensuring reliable streaming of transactions and alerts.
    *   **UPI Domain Logic**: Authored the heuristic detectors for India-specific threats like **Digital Arrest, SIM Swaps, and QR Code scams**.
    *   **Pre-Auth Engine**: Built the ultra-low-latency blocking logic for velocity violations and impossible travel heuristics.
    *   **Security Layer**: Implemented the **Phishing Protection** and device fingerprinting logic to audit HTTP context and session telemetry.
