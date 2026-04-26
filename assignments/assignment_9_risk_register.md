# Assignment 9 — Risk Management and Mitigation
### Project: ARGUS — AI-Powered Fraud Detection System

---

## 1. Risk Identification & Categories
As per software project management principles, the risks associated with the ARGUS system are classified into the following core categories:

### 1.1 Technical Risks
Affect the quality and performance of the software system (technology, design, implementation).
* **R01: ML Ensemble Inference Latency:** Running XGBoost, LightGBM, and Isolation Forest sequentially might exceed the <500ms transaction processing target.
* **R02: WebSocket Connection Drops:** The live simulation dashboard depends entirely on WebSocket stability; drops lead to a frozen UI.
* **R03: SQLite Database Locking:** High-throughput concurrent writes from the simulation loop may cause database locking or corruption.

### 1.2 Project Risks
Affect the project schedule, cost, resources, and timeline.
* **R04: Module Integration Failure:** Combining the Pre-Auth Engine, ML Ensemble, and UI into a cohesive pipeline might exceed the scheduled integration time.
* **R05: Local Hardware Constraints:** Training the ML models (especially with SMOTE upsampling on large datasets) might crash local machines due to Out-Of-Memory (OOM) errors.

### 1.3 Business Risks
Affect the business success of the software project.
* **R06: Low Fraud Recall (False Negatives):** If the ML models miss complex fraud rings, the system loses its primary business value, leading to rejection by financial institutions.
* **R07: High False Positives:** Flagging too many legitimate transactions will cause alert fatigue for analysts and poor user experience.

### 1.4 Known Risks
Identified in advance during project planning.
* **R08: Class Imbalance in Training Data:** Financial transaction datasets inherently possess extreme class imbalance.
* **R09: External API Dependency:** The system relies on IP geolocation APIs for the Geo-Check module, requiring active internet.

### 1.5 Predictable Risks
Expected from previous projects or historical data.
* **R10: Scope Creep:** Adding unrequested features (like complex reporting dashboards) may delay the core real-time detection deliverables.

---

## 2. Risk Projection and Components
Each risk is evaluated based on its Probability, Impact Level (Negligible, Marginal, Critical, Catastrophic), Impact Component (Performance, Support, Cost, Schedule), and overall Priority.

| Risk ID | Risk Description | Component | Probability | Impact Level | Priority |
|---|---|---|---|---|---|
| R06 | Low Fraud Recall (False Negatives) | Performance | 0.40 | Catastrophic | 1 |
| R01 | ML Ensemble Inference Latency | Performance | 0.60 | Critical | 2 |
| R08 | Class Imbalance in Training Data | Performance | 0.80 | Critical | 3 |
| R04 | Module Integration Failure | Schedule | 0.50 | Critical | 4 |
| R02 | WebSocket Connection Drops | Support | 0.40 | Marginal | 5 |
| R03 | SQLite Database Locking | Performance | 0.30 | Critical | 6 |
| R05 | Local Hardware Constraints | Schedule | 0.50 | Marginal | 7 |
| R07 | High False Positives | Support | 0.60 | Marginal | 8 |
| R09 | External API Dependency | Performance | 0.30 | Marginal | 9 |
| R10 | Scope Creep | Cost/Schedule | 0.40 | Negligible | 10 |

---

## 3. Risk Refinement
Breaking down a complex risk into smaller, manageable risks for better planning.

**Refining R01: ML Ensemble Inference Latency**
* Sub-Risk 1: Feature extraction (e.g., calculating velocity profiles from the database) takes too long.
* Sub-Risk 2: LightGBM and XGBoost models running sequentially block the main thread in FastAPI.
* Sub-Risk 3: Graph Risk Check traversing too many nodes for dense fraud rings.

---

## 4. Risk Mitigation, Monitoring, and Management (RMMM)

This section details the strategy (Avoid, Reduce, Transfer, Accept) for the highest priority risks using a proactive risk management approach.

### R06: Low Fraud Recall (Catastrophic)
* **Strategy:** Reduce
* **Mitigation:** Implement an Ensemble approach combining XGBoost, LightGBM, and Isolation Forest. Do not rely on a single model. Tune the decision threshold based on the F1-score rather than raw accuracy. Include anomaly vectors for interpretability.
* **Monitoring:** Continuously track the Confusion Matrix during validation phases. 
* **Management:** If recall drops below target, trigger a model retraining phase with adjusted class weights.

### R01: ML Ensemble Inference Latency (Critical)
* **Strategy:** Reduce
* **Mitigation:** Utilize FastAPI's `BackgroundTasks` for asynchronous scoring where immediate blocking is not strictly required. Cache user behavior profiles in memory to avoid repeated database reads. 
* **Monitoring:** Log response times for the transaction endpoint and alert if the average exceeds acceptable limits.
* **Management:** If latency is unacceptable during the demo, temporarily disable the heavy Graph Risk Check and rely solely on the LightGBM/XGBoost models.

### R08: Class Imbalance in Training Data (Critical)
* **Strategy:** Avoid
* **Mitigation:** Apply SMOTE (Synthetic Minority Over-sampling Technique) during the data preprocessing pipeline. Use `scale_pos_weight` in XGBoost and LightGBM to heavily penalize false negatives.
* **Monitoring:** Review the class distribution of the training batches before finalizing models.
* **Management:** Ensure validation is performed on a strictly un-sampled, real-world distribution to get an accurate representation of performance.

### R04: Module Integration Failure (Critical)
* **Strategy:** Avoid
* **Mitigation:** Define strict JSON schemas and Pydantic models for the data contracts between the Pre-Auth Engine, ML Engine, and Frontend UI.
* **Monitoring:** Conduct end-to-end integration tests using the automated transaction simulator.
* **Management:** If a module fails integration, stub its response (e.g., return a default score of 0 or empty anomaly vector) so the rest of the pipeline can continue functioning.

### R09: External API Dependency (Marginal)
* **Strategy:** Accept
* **Mitigation:** Wrap the IP Geolocation API call in a `try/except` block with a short timeout.
* **Monitoring:** Monitor API failure rates in the terminal logs.
* **Management:** If the hackathon venue lacks internet or the API is down, automatically fallback to returning "Unknown Location" without crashing the transaction pipeline.
