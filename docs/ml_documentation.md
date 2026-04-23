# ARGUS Machine Learning Architecture & Methodology (Enterprise Edition)

This document provides an exhaustive, highly detailed architectural breakdown of the machine learning pipeline that powers Project ARGUS. This covers our entire methodology from raw data ingestion to synthetic datasets, complex feature engineering, sequence modeling, and the multi-layered neural/ensemble inference architecture.

---

## 1. Dataset Methodology & Authenticity Validation

### Why Synthetic Data? (The PaySim Foundation)
Training a state-of-the-art fraud detection system requires millions of transactions with a known, labeled ground-truth of what is and isn't fraud. Real-world banking datasets are strictly confidential, heavily anonymized, and virtually impossible to acquire at the scale needed due to stringent privacy regulations (e.g., GDPR, India's DPDP Act, RBI data localization mandates).
- **The Base Dataset**: We utilize **PaySim**, a highly regarded financial simulator designed for Mobile Money. It uses agent-based modeling to simulate transaction graphs based on a sample extracted from one month of financial logs from a mobile money service implemented in an African country. This provides the mathematical underpinning for legitimate macro-economic transfer patterns.
- **Indian Market Localization**: We dynamically augment the base PaySim distributions with parameters tuned to the **Indian UPI (Unified Payments Interface) ecosystem**. We inject localized merchant categories, Tier 1/2/3 city mappings, and specific channel variances (e.g., high-frequency small-value transactions typical of Paytm/PhonePe).
- **Authenticity Validation**: To ensure the synthetic data behaves like real-world data, we cross-reference feature distributions against publicly available NPCI (National Payments Corporation of India) metrics. For instance, the system validates that P2M (Person-to-Merchant) transaction velocity mirrors daytime retail hours, while large P2P (Person-to-Person) transfers have a higher likelihood of triggering anomaly flags during off-hours (2 AM - 5 AM).

---

## 2. Feature Engineering (The V2 Architecture)

The raw transaction data (Amount, Channel, Merchant, Time) is completely insufficient for modern ML models to catch sophisticated fraud. ARGUS transforms this raw data into a highly dense vector space utilizing **50 engineered features** spread across 9 specific domains, managed by `feature_engineering_v2.py`.

### A. Temporal Features (10 Features)
Fraudsters operate in specific time windows. These features map temporal anomalies:
1. `hour`: The exact hour of the transaction (0-23).
2. `day_of_week`: Day index (0=Monday, 6=Sunday).
3. `is_weekend`: Binary flag for weekend transactions (Sat/Sun).
4. `day_of_month`: Date of the month (1-31).
5. `month`: Month of the year.
6. `is_night`: Binary flag (23:00 - 05:00). High risk for account takeovers.
7. `is_morning`: Binary flag (06:00 - 11:00).
8. `is_afternoon`: Binary flag (12:00 - 17:00).
9. `is_evening`: Binary flag (18:00 - 22:00).
10. `is_suspicious_hour`: Binary flag covering specifically high-fraud windows (22:00 - 06:00).

### B. Demographic Features (3 Features)
11. `age_group_encoded`: Numerical encoding of user age brackets.
12. `age_fraud_rate`: Historical probability of fraud mapped to the user's age demographic.
13. `age_mismatch_score`: Binary flag (1 if sender and receiver age groups differ wildly in a suspicious manner).

### C. Geographic Features (5 Features)
14. `state_encoded`: Numerical encoding of the Indian state.
15. `state_fraud_rate`: Baseline historical fraud rate for the origin state (e.g., certain cyber-hubs have naturally higher baseline rates).
16. `is_metro_sender`: Binary flag (1 if origin is a major metro like Mumbai, Bangalore, Delhi).
17. `is_cross_state`: Binary flag (1 if sender and receiver states differ).
18. `cross_state_risk_multiplier`: A non-linear multiplier applied when large sums cross state borders rapidly.

### D. Device & Network Features (7 Features)
19. `device_type_encoded`: Encoding of device OS (Android, iOS, Web).
20. `device_fraud_rate`: Baseline risk for the given device OS.
21. `is_new_device`: Binary flag (1 if the device fingerprint hasn't been seen for this user).
22. `new_device_risk`: A calculated coefficient applying extra weight if `is_new_device` is True.
23. `network_type_encoded`: Encoding of network (4G, 5G, WiFi, 3G).
24. `network_fraud_rate`: Baseline risk for the network type.
25. `suspicious_device_network`: Binary flag (1 if Web + Public WiFi).

### E. Merchant Features (5 Features)
26. `merchant_category_encoded`: Numerical encoding of category.
27. `merchant_fraud_rate`: Baseline risk mapping (e.g., `cryptocurrency` = 0.120, `grocery` = 0.003).
28. `is_high_risk_category`: Binary flag (1 for electronics, jewellery, gambling, crypto).
29. `is_low_risk_category`: Binary flag (1 for utilities, groceries, healthcare).
30. `merchant_reputation_score`: A dynamic 0-1 score representing the merchant's historical safety.

### F. Transaction Type Features (4 Features)
31. `transaction_type_encoded`: Encoding for P2P, P2M, Bill, Recharge.
32. `transaction_type_fraud_rate`: Baseline historical risk.
33. `is_p2p`: Binary flag (Person-to-Person transfers have statistically higher fraud rates).
34. `is_cash_like`: Binary flag for highly liquid transfers that are hard to reverse.

### G. Amount Features (6 Features)
35. `amount`: The raw transaction amount.
36. `amount_bucket_encoded`: Non-linear bucket ('very_small' to 'very_large').
37. `amount_percentile`: Where this amount ranks historically for the specific user/merchant.
38. `is_suspicious_amount`: Binary flag (1 for structuring amounts like 49,999 to bypass 50,000 pan-card limits).
39. `is_round_amount`: Binary flag (1 if divisible by 100). Fraudsters usually type round numbers.
40. `amount_log`: `log(1 + amount)` to normalize the exponential distribution of money.

### H. Velocity & Pattern Features (4 Features)
41. `velocity_txn_per_hour`: Moving average of transactions per hour.
42. `is_duplicate_amount_recent`: Binary flag (1 if the exact same amount was transferred recently).
43. `amount_velocity_per_hour`: Rolling 1-hour sum of capital transferred.
44. `burst_txn_count_10min`: Peak transactions occurring in a 10-minute window.

### I. Risky Combination Matrices (6 Features)
These are engineered cross-features that find complex overlaps before passing to the ML model:
45. `late_night_high_amount`: Night + Amount > 75th percentile.
46. `late_night_jewelry`: Night + Jewellery Merchant.
47. `new_device_high_amount`: New Device + Amount > 75th percentile.
48. `cross_state_high_risk`: Cross-State transfer + High-Risk Merchant.
49. `web_wifi_jewelry`: Web + Public WiFi + Jewellery.
50. `high_risk_merchant_new_device`: Merchant Fraud Rate > 4% + New Device.

---

## 3. The ML Pipeline: 4-Tier Ensemble + Deep Sequence Models

ARGUS doesn't rely on one model; it employs a multi-tiered architecture that combines supervised learning, unsupervised learning, graph theory, and sequence modeling.

### Tier 1: Supervised Ensembles (XGBoost & LightGBM)
These models are trained on historical data to recognize complex "structural" fraud patterns across the entire user base.
- **XGBoost (Primary Engine)**
  - *Parameters*: `max_depth=6`, `learning_rate=0.1`, `subsample=0.8`, `n_estimators=200`
  - *Methodology*: Excels at non-linear boundary detection. It leverages the engineered cross-features to map boundaries.
- **LightGBM (Secondary Engine)**
  - *Parameters*: `num_leaves=31`, `learning_rate=0.05`, `feature_fraction=0.9`
  - *Methodology*: Uses histogram-based binning to compute significantly faster. It acts as a secondary validator, ensuring we don't miss patterns XGBoost might under-weight, particularly for sparse categorical features like State or Device encoding.

### Tier 2: Unsupervised Outlier Detection (Isolation Forest)
- *Parameters*: `n_estimators=100`, `contamination='auto'`
- *Methodology*: This model is completely unsupervised—it doesn't look at labels. It isolates anomalies by seeing how quickly a data point can be separated from the rest of the dataset. Normal transactions require many splits; anomalies require very few. This is our primary defense against **Zero-Day Fraud** (new attack vectors that our supervised models have never seen before).

### Tier 3: Graph Fraud Detection (Network Analysis)
Powered by `NetworkX` in `graph_fraud_detector.py`, this engine models users and merchants as nodes in a massive directed graph.
- **Mule Account Detection**: Analyzes `in_degree` vs `out_degree`. If an account receives capital from 15 distinct sources and immediately transfers >80% of it to 10 other sources (high flow-through velocity), it is flagged as a Money Mule.
- **Cyclic Patterns**: Uses simple cycle algorithms to find A → B → C → A transfer loops (classic money laundering behavior).
- **Fraud Rings**: Uses community detection to find strongly connected subgraphs (density > 0.5), grouping suspicious clusters of users who heavily transact with one another.

### Tier 4: Deep Learning Sequence Analysis
Powered by PyTorch in `deep_learning_model.py`, this engine looks at *time-series sequences* rather than isolated transactions.
- **LSTM (Long Short-Term Memory)**: Analyzes sequences of the last 10 transactions. It looks for "ramp-up" behavior (e.g., small tests followed by massive liquidation).
- **Transformer (Attention-Based)**: Uses positional encoding and multi-head attention to find non-sequential but highly correlated anomalies (e.g., matching a high-value withdrawal to an unusual login location from 3 days prior).

---

## 4. Final Risk Scoring & Architecture Decision Logic

### The Pre-Auth Environment Protection (Phishing/Bots)
Before ANY machine learning model processes a transaction, it passes through the `PreAuthEngine`.
- **Methodology**: It evaluates the *client-side execution environment*.
- **Triggers**: It looks for Bot Signatures (e.g., `No Mouse Movement`, `Instant Submit < 1000ms`, `No Keyboard Input`) or known phishing domains.
- **Outcome**: If a bot is detected, it throws a **CRITICAL BLOCK** with a risk score of 1.0 (100%), and effectively bypasses the ML ensemble. **This is why small value transactions (e.g., ₹840) are blocked with 0% ML confidence—fraudsters test stolen credentials with small amounts using scripts, and catching the script is more important than analyzing the transaction amount.**

### The Ensemble Weighting Methodology
If the transaction clears Pre-Auth, it is handed to the ML Pipeline. The final risk score is a carefully tuned weighted sum:
- `Final Score = (XGB * 0.30) + (LGB * 0.25) + (IsoForest * 0.15) + (DynBehavior * 0.15) + (Rules/Graph * 0.15)`

**Why we arrived at these weights:**
1. Supervised models (XGB/LGB, combined 55%) receive the highest weight because they are historically proven on vast datasets with explicit labels.
2. Unsupervised (IsoForest) and User-specific (DynBehavior) act as heavy modifiers (15% each) to push borderline transactions over the threshold.
3. If DynBehavior flags a transaction as a massive anomaly (e.g., a massive spike in a single user's profile), it can independently trigger a high-risk flag even if the supervised models deem the absolute amount to be structurally normal.

---

## 5. Persistence & Operational Data (SQLite / argus_data.db)

The `argus_data.db` file serves as the core state-management layer for the platform.

### A. Role in the System
- **Persistence Layer**: It acts as the system's "memory," storing every processed transaction, alert, and analyst action across sessions.
- **Audit Trail**: Every decision made by the ML ensemble is recorded with a full scoring breakdown (XGB, LGB, IsoForest scores) and execution latency.
- **Operational Workflow**: Stores real-time alert statuses (`pending`, `dismissed`, `confirmed`) to power the Triage dashboard.

### B. Table Schema & Data Points
- **Transactions Table**: Stores 30+ columns of data including raw transaction details, behavioral Z-Scores, and the final multi-model confidence scores.
- **Alerts Table**: Tracks high-risk events requiring administrative review.
- **Survey & Feedback**: Captures model performance feedback and analyst actions to facilitate future reinforcement learning (RLHF) loops.

### C. Analytics Foundation
The Dashboard's real-time and historical charts are powered by high-speed SQL aggregations over the `transactions` table, providing the "Eagle's Eye" metrics (Fraud Rate, Volume, Latency) that administrators rely on for system monitoring.
