# ARGUS Backend Documentation: Master Index

Welcome to the comprehensive internal documentation for **Project ARGUS: Advanced Real-time Guard & User Security for Digital Payments**. This directory contains highly detailed, file-by-file breakdowns of the entire backend architecture.

## How to Read This Documentation (Chronological Sequence)
To truly understand the system "under the hood," it is highly recommended to read the file documentation in the following chronological order. This maps exactly to the lifecycle of data flowing through the system: from generation, to training, to real-time inference, and finally post-processing.

### 1. Data Generation & Training (The Foundation)
Understand how the system learns and what data it expects.
1. `01_dataset_config.md`
2. `02_generate_training_dataset.md`
3. `03_data_preparation.md`
4. `04_feature_engineering_v2.md`
5. `05_train_model_v4.md`

### 2. Core Decision Engine (The Brain)
Understand the actual models and the <20ms latency pre-authorization engine.
6. `06_pre_auth_engine.md`
7. `07_feature_extractor.md`
8. `08_fraud_model.md`

### 3. Specialized Intelligence Modules (The Experts)
Understand the specialized heuristics and deep-learning sub-modules that feed into the main ensemble.
9. `09_device_intelligence.md`
10. `10_merchant_reputation.md`
11. `11_upi_fraud_patterns.md`
12. `12_graph_fraud_detector.md`
13. `13_deep_learning_model.md`
14. `14_phishing_protection.md`

### 4. API, Post-Processing & Simulation (The Operations)
Understand how the system communicates, simulates traffic, and alerts users.
15. `15_transaction_gen.md` (Simulator)
16. `16_main.md` (FastAPI Server)
17. `17_explainable_ai.md`
18. `18_case_management.md`
19. `19_alert_notifications.md`
20. `20_test_v4.md`
21. `21_visualize_fraud_graph.md`

### 5. Frontend, Visualization & Market Validation
Understand the user interface and the business validation strategy.
22. `22_frontend.md` (React Dashboard)
23. `23_survey_form.md` (Market Validation Simulation)
24. `24_project_root.md`
25. `25_ml_architecture_deepdive.md` (Detailed ML Architecture Breakdown)
26. `26_project_contributions.md` (Team Roles & Contribution Guide)

---

## The Technology Stack (Detailed)

### Backend & Core Infrastructure
* **Python 3.11+**: The core language for backend logic and ML models. Chosen for its extensive data science ecosystem.
* **FastAPI**: A modern, fast web framework for building APIs. Used here because of its asynchronous I/O capabilities, crucial for maintaining the <20ms latency requirement during high-throughput transaction streams.
* **SQLite (Local Store)**: Used for `argus_data.db`. It stores the pre-authorization audit trails, case management queues, and persistent settings. (Note: User behavioral profiles are stored directly in `user_profiles.json` for rapid memory-mapped access).
* **WebSockets**: Used in `main.py` to stream live simulated transactions and alert notifications directly to the React frontend in real-time.

### Machine Learning & Data Science (The Ensemble)
* **XGBoost**: Extreme Gradient Boosting. The primary supervised learning classifier (30% weight). Excellent at finding non-linear relationships in structured tabular transaction data.
* **LightGBM**: Light Gradient Boosting Machine (25% weight). Highly efficient at handling large-scale categorical features (like merchant categories or device IDs).
* **Scikit-Learn (Isolation Forest)**: Used for unsupervised anomaly detection (15% weight). It isolates anomalous "zero-day" fraud patterns that haven't been seen in the training data.
* **PyTorch (LSTM)**: Long Short-Term Memory neural networks. Used in `deep_learning_model.py` for Temporal Sequence Analysis to detect multi-stage fraud attempts over time.
* **NetworkX**: A Python package for the creation, manipulation, and study of complex networks. Used in `graph_fraud_detector.py` for mule account and fraud ring (A → B → C → A) detection using community detection algorithms.
* **Pandas & NumPy**: Core libraries for data manipulation, feature extraction, and high-speed array operations.

### Frontend
* **React 18 & Vite**: Component-based UI library paired with a blazing-fast build tool.
* **Tailwind CSS**: Utility-first CSS framework used for styling the high-fidelity dashboard.
* **Recharts**: Composable charting library built on React components. Used for the real-time transaction telemetry graphs.
* **Vis-Network**: Used to render the interactive, physics-based NetworkX graph of fraud rings on the frontend.

---

## Explainable AI (XAI) Strategy: Clarifying the "AI Layer"
**Is there an AI layer?** 
Yes, absolutely. The system is heavily reliant on an AI layer comprising XGBoost, LightGBM, Isolation Forest, and LSTM neural networks. 

**How is Explainable AI (SHAP) implemented?**
True SHAP (SHapley Additive exPlanations) is computationally heavy. Running a full `shap.TreeExplainer` on every single transaction in real-time would completely violate the strict <20ms execution window required for a pre-authorization engine. 

Therefore, ARGUS employs a **Heuristic XAI Translation Layer** (`explainable_ai.py`). 
* **The Trade-off**: Instead of calculating dynamic Shapley values on the fly, the system pre-extracts the global feature importance weights from the trained XGBoost/LightGBM models (e.g., Amount = 25%, Merchant Risk = 20%, Velocity = 15%). 
* **The Implementation**: During inference, if a transaction is flagged, `explainable_ai.py` looks at the raw feature values (e.g., amount = 50,000, distance = 500km) and maps them against these pre-calculated AI weights and hardcoded rule triggers to generate a human-readable explanation (e.g., *"[BLOCKED] High transaction amount: ₹50,000 at Unusual time: 3:00"*). 

This approach provides regulatory compliance and transparency without sacrificing millisecond performance.

---

## Project Limitations (For Viva Defense)
Be prepared to acknowledge these limitations if asked. Acknowledging limitations demonstrates a mature engineering mindset.

1. **Reliance on Synthetic Data**: Because real banking datasets are heavily guarded by NDA and PII regulations, the models are trained on highly engineered synthetic data (`generate_training_dataset.py`) based on Kaggle/PaySim paradigms. While structurally accurate to Indian parameters, it lacks the true chaotic variance of actual bank traffic.
2. **The "Cold Start" Problem**: The Dynamic Behavioral Analysis (15% ensemble weight) relies on comparing a transaction to a user's 30-day rolling profile. New users with <10 transactions ("building" maturity) will default to global averages, making them slightly more vulnerable to false positives/negatives until their profile matures.
3. **SQLite Concurrency**: The backend uses SQLite. While perfectly fine for a prototype/demo, SQLite locks the entire database during write operations. In a production environment with 5,000+ Transactions Per Second (TPS), this would instantly bottleneck. The architecture is designed so that a production deployment would simply swap SQLite for a high-concurrency DB like PostgreSQL and Redis for velocity tracking (as outlined in the Roadmap).
