# Assignment 9 — Risk Identification & Mitigation Strategies
### Project: ARGUS — AI-Powered Fraud Detection System

---

## 1. Risk Management Framework

**Risk Score = Probability (P) × Impact (I)**

| Scale | Probability | Impact |
|---|---|---|
| 1 | Very Low (<10%) | Negligible |
| 2 | Low (10–30%) | Minor |
| 3 | Medium (30–50%) | Moderate |
| 4 | High (50–70%) | Major |
| 5 | Very High (>70%) | Catastrophic |

- **Low Risk:** Score 1–5  
- **Medium Risk:** Score 6–14  
- **High Risk:** Score 15–25  

**Risk Owner:** Project Team Lead  
**Review Frequency:** Weekly during development, bi-weekly during testing

---

## 2. Risk Register — All Identified Risks

### Category 1: Technical Risks

| Risk ID | Description | P | I | Score | Level |
|---|---|---|---|---|---|
| R01 | ML model accuracy too low for demo (<75% recall) | 4 | 5 | **20** | 🔴 HIGH |
| R02 | FastAPI backend crashes under simulation load | 3 | 5 | **15** | 🔴 HIGH |
| R03 | WebSocket connection drops during live demo | 3 | 4 | **12** | 🟡 MEDIUM |
| R04 | Graph fraud detection too slow (>500ms) | 3 | 4 | **12** | 🟡 MEDIUM |
| R05 | SQLite DB corruption under concurrent writes | 2 | 5 | **10** | 🟡 MEDIUM |
| R06 | Deep learning (LSTM) inference latency too high | 3 | 3 | **9** | 🟡 MEDIUM |
| R07 | React dashboard renders incorrectly on demo device | 2 | 3 | **6** | 🟡 MEDIUM |

### Category 2: Data & ML Risks

| Risk ID | Description | P | I | Score | Level |
|---|---|---|---|---|---|
| R08 | Kaggle dataset download fails (API/network) | 4 | 4 | **16** | 🔴 HIGH |
| R09 | Training data class imbalance causes biased model | 4 | 5 | **20** | 🔴 HIGH |
| R10 | Feature mismatch between training and inference | 3 | 5 | **15** | 🔴 HIGH |
| R11 | Model overfitting on training data | 3 | 4 | **12** | 🟡 MEDIUM |
| R12 | SMOTE oversampling creates unrealistic patterns | 2 | 3 | **6** | 🟢 LOW |

### Category 3: Project / Schedule Risks

| Risk ID | Description | P | I | Score | Level |
|---|---|---|---|---|---|
| R13 | Model retraining exceeds 90 min or OOM crash | 4 | 3 | **12** | 🟡 MEDIUM |
| R14 | Integration failure across 7 ML modules | 3 | 5 | **15** | 🔴 HIGH |
| R15 | Team member unavailability before deadline | 2 | 4 | **8** | 🟡 MEDIUM |
| R16 | Scope creep — adding unrequested features | 3 | 3 | **9** | 🟡 MEDIUM |

### Category 4: Security Risks

| Risk ID | Description | P | I | Score | Level |
|---|---|---|---|---|---|
| R17 | Sensitive data exposed via unprotected API endpoints | 2 | 5 | **10** | 🟡 MEDIUM |
| R18 | ML model inversion attack during demo | 1 | 4 | **4** | 🟢 LOW |

### Category 5: External / Environment Risks

| Risk ID | Description | P | I | Score | Level |
|---|---|---|---|---|---|
| R19 | Demo laptop failure at hackathon venue | 2 | 5 | **10** | 🟡 MEDIUM |
| R20 | No internet at venue — external API calls fail | 3 | 4 | **12** | 🟡 MEDIUM |

---

## 3. Risk Matrix (5×5)

```
PROBABILITY ↑

Very High(5) │  5  │  10  │  15  │  20  │  25  │
High (4)     │  4  │   8  │  12  │  16  │  20  │
             │     │      │R06   │ R08  │R01,R09│
Medium (3)   │  3  │   6  │   9  │  12  │  15  │
             │     │R07   │R16   │R03,R04│R02,R10,R14│
Low (2)      │  2  │   4  │   6  │   8  │  10  │
             │     │ R18  │ R12  │ R15  │R05,R17,R19│
Very Low (1) │  1  │   2  │   3  │   4  │   5  │
             └─────┴──────┴──────┴──────┴──────┘
               1      2      3      4      5
             IMPACT (Negligible → Catastrophic) →
```

---

## 4. Top Risk Mitigation Strategies

---

### R01 — ML Model Accuracy Insufficient
**Score: 20 | 🔴 HIGH**

**Description:** Current XGBoost model (trained on small internal dataset with 16-17 features) has ROC-AUC ~0.65-0.72 and recall ~35%, far below the SoW target of ≥0.88 AUC.

**Root Cause:** Insufficient training data, no SMOTE, too few engineered features.

**Mitigation Strategies:**

| Strategy | Actions |
|---|---|
| Avoid | Run `run_complete_training.py` on the 6-7M combined PaySim + Kaggle UPI dataset |
| Reduce | Apply SMOTE, add LightGBM to ensemble, optimize threshold on F1 not accuracy |
| Accept | Frame demo with "prototype" language if accuracy still below target |

**Contingency:** Pre-record a demo video with good metrics as backup.

---

### R09 — Class Imbalance in Training Data
**Score: 20 | 🔴 HIGH**

**Description:** Fraud transactions are only 0.12% of the dataset. A naive model predicts "legitimate" always — 99.88% accuracy, 0% fraud caught.

**Mitigation:**
1. Apply SMOTE (`sampling_strategy=0.3`) — upsample fraud to 30% of training set
2. Use `scale_pos_weight` in XGBoost
3. Optimize decision threshold on F1-score (not accuracy)
4. Use stratified 5-fold cross-validation

**Residual Risk:** Low (SMOTE + weighted loss adequately handles this)

---

### R08 — Kaggle Dataset Download Failure
**Score: 16 | 🔴 HIGH**

**Description:** Training requires downloading the 440MB PaySim dataset from Kaggle. Network issues or missing credentials block this.

**Mitigation:**
1. Manually download PaySim CSV from Kaggle browser before hackathon
2. Set up Kaggle API key: create `~/.kaggle/kaggle.json`
3. Download on fast internet, NOT on hackathon day
4. Keep raw CSV backed up on USB drive and cloud

---

### R02 — Backend Crashes Under Simulation Load
**Score: 15 | 🔴 HIGH**

**Description:** Simulation generates rapid transactions via WebSocket. Blocking ML inference can overwhelm the thread pool and crash FastAPI.

**Mitigation:**
1. Use `BackgroundTasks` in FastAPI for heavy ML inference
2. Add `asyncio.sleep(0.5)` delay between simulation transactions
3. Stress test with 5-minute simulation run before demo day
4. Wrap all ML calls in `try/except` — never let exceptions crash WebSocket

---

### R10 — Feature Mismatch: Training vs Inference
**Score: 15 | 🔴 HIGH**

**Description:** If `feature_cols.joblib` doesn't match features computed in `fraud_model.py` at inference time, predictions will fail silently or produce garbage.

**Mitigation:**
1. After retraining, smoke test: send 5 known transactions, verify reasonable scores
2. Load feature names from saved joblib, not hardcoded list
3. Add assertion: `assert set(inference_cols) == set(saved_feature_cols)`
4. Keep v1 models as fallback

---

### R14 — Module Integration Failure
**Score: 15 | 🔴 HIGH**

**Description:** All 7 ML modules (pre-auth, device, graph, phishing, merchant, XAI, case mgmt) must integrate cleanly in `main.py`. JSON key mismatches cause silent failures.

**Mitigation:**
1. Run `START_DEMO.bat`, generate 50 transactions, verify full JSON response
2. Validate response schema in `api.js` frontend layer
3. Use Pydantic models in FastAPI for strict request/response validation
4. Log all module outputs to file during integration testing

---

### R03 — WebSocket Drop During Demo
**Score: 12 | 🟡 MEDIUM**

**Mitigation:**
1. Reconnection logic is already in `api.js` — verify it works before demo
2. Fallback: use polling endpoint `/api/transactions` if WebSocket fails
3. Run demo from `localhost` — eliminates external network dependency

---

### R13 — Model Training Too Slow / Out of Memory
**Score: 12 | 🟡 MEDIUM**

**Mitigation:**
1. Reduce `n_estimators` to 200 (from 500) for faster training if needed
2. Use stratified sampling to train on 1M rows instead of 6M
3. Close all browsers and apps during training
4. Train at least 2 days before hackathon — NOT the night before

---

### R20 — No Internet at Venue
**Score: 12 | 🟡 MEDIUM**

**Description:** System uses IP geolocation API requiring internet. Alert channels (Slack/Email) also need connectivity.

**Mitigation:**
1. Ensure geolocation falls back gracefully: `return "Unknown City, IN"`
2. Disable live email/SMS alerts in demo mode — show in-dashboard alerts only
3. All core fraud detection (ML models, graph, rules) runs 100% offline

---

### R19 — Demo Laptop Failure at Venue
**Score: 10 | 🟡 MEDIUM**

**Mitigation:**
1. Pre-record 2–3 min demo video as absolute backup
2. Push final code to GitHub — runnable on any laptop
3. Bring charger + power bank
4. Test `START_DEMO.bat` successfully 3 times before leaving for venue

---

## 5. Risk Monitoring Plan

| Review Point | Who | Action |
|---|---|---|
| Daily during development | Team | Check training logs, test simulation, update risk register |
| 3 days before hackathon | Team Lead | Full end-to-end test, verify all mitigations applied |
| 1 day before | Full Team | Demo rehearsal, record backup video |
| Day of hackathon | All | Arrive 30 min early, run `START_DEMO.bat`, verify live |

---

## 6. Residual Risk Summary

| Risk | Initial Score | Residual Score | Status |
|---|---|---|---|
| R01: ML Accuracy | 20 | 8 | 🟡 Reduced |
| R09: Class Imbalance | 20 | 4 | 🟢 Resolved |
| R08: Dataset Download | 16 | 4 | 🟢 Resolved (manual download) |
| R02: Backend Crash | 15 | 6 | 🟡 Reduced |
| R10: Feature Mismatch | 15 | 4 | 🟢 Resolved |
| R14: Integration Failure | 15 | 6 | 🟡 Reduced |
| R19: Laptop Failure | 10 | 4 | 🟢 Resolved (backup video) |
| R20: No Internet | 12 | 4 | 🟢 Resolved (offline fallback) |
