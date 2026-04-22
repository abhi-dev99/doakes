# Assignment 8 — Software Cost Estimation
## Function Point Analysis (FPA) + Use Case Points (UCP)
### Project: ARGUS — AI-Powered Fraud Detection System

---

## Part A: Function Point Analysis (FPA)

### Background

Function Point Analysis (FPA) was developed by Allan J. Albrecht at IBM in 1979 and standardized by IFPUG in 1984. It measures software size based on **what the system does** (functionality), not how it's built. It is technology-independent — applicable to any language or platform.

---

### Step 1: Identify the Five Function Types

#### 1. External Inputs (EI) — Weights: Simple=3, Average=4, High=6

| # | External Input | Complexity | Weight |
|---|---|---|---|
| 1 | Submit Transaction for Fraud Check | High | 6 |
| 2 | Start/Stop Simulation | Simple | 3 |
| 3 | Update Risk Threshold Settings | Average | 4 |
| 4 | Update Alert Configuration | Average | 4 |
| 5 | Analyst Case Action (Dismiss/Confirm) | Simple | 3 |
| 6 | Device Fingerprint Data | High | 6 |
| 7 | IP Geolocation Data Input | Average | 4 |
| 8 | Merchant Data Registration | Average | 4 |
| | **Total EI** | | **34** |

#### 2. External Outputs (EO) — Weights: Simple=4, Average=5, High=7

| # | External Output | Complexity | Weight |
|---|---|---|---|
| 1 | Fraud Decision (BLOCK/CHALLENGE/ALLOW) | High | 7 |
| 2 | XAI Explanation Report | High | 7 |
| 3 | Real-time Alert (Email/SMS/Slack) | High | 7 |
| 4 | Transaction Analytics Report | Average | 5 |
| 5 | Fraud Ring Detection Report | High | 7 |
| 6 | Performance Metrics Dashboard | Average | 5 |
| 7 | Regulatory Compliance Report | Average | 5 |
| 8 | Case Management Export | Average | 5 |
| | **Total EO** | | **48** |

#### 3. External Inquiries (EQ) — Weights: Simple=3, Average=4, High=6

| # | External Inquiry | Complexity | Weight |
|---|---|---|---|
| 1 | Get Transaction by ID | Simple | 3 |
| 2 | Get Recent Transactions List | Average | 4 |
| 3 | Get System Statistics | Average | 4 |
| 4 | Get Alerts Feed | Simple | 3 |
| 5 | Get Graph Analytics (fraud rings) | High | 6 |
| 6 | Get Merchant Reputation Data | Average | 4 |
| 7 | Get Performance Metrics | Average | 4 |
| 8 | Get Case Queue for Analyst | Simple | 3 |
| 9 | Get Explainability for Transaction | High | 6 |
| | **Total EQ** | | **37** |

#### 4. Internal Logical Files (ILF) — Weights: Simple=7, Average=10, High=15

| # | Internal Logical File | Complexity | Weight |
|---|---|---|---|
| 1 | Transactions Table (SQLite) | High | 15 |
| 2 | User Behavioral Profiles (JSON) | High | 15 |
| 3 | Fraud Alerts Table | Average | 10 |
| 4 | Case Management Records | Average | 10 |
| 5 | Device Reputation Registry | Average | 10 |
| 6 | Merchant Reputation Table | Simple | 7 |
| 7 | Graph Nodes/Edges (fraud network) | High | 15 |
| 8 | ML Model Files (joblib artifacts) | Simple | 7 |
| | **Total ILF** | | **89** |

#### 5. External Interface Files (EIF) — Weights: Simple=5, Average=7, High=10

| # | External Interface File | Complexity | Weight |
|---|---|---|---|
| 1 | IP Geolocation Database | Average | 7 |
| 2 | Kaggle UPI Dataset (training data) | Average | 7 |
| 3 | PaySim Dataset (training data) | Average | 7 |
| 4 | RBI Regulatory Rules Reference | Simple | 5 |
| 5 | Email/SMS/Slack Webhook APIs | Simple | 5 |
| | **Total EIF** | | **31** |

---

### Step 2: Unadjusted Function Points (UFP)

| Type | Count | Weighted Total |
|---|---|---|
| External Inputs (EI) | 8 | 34 |
| External Outputs (EO) | 8 | 48 |
| External Inquiries (EQ) | 9 | 37 |
| Internal Logical Files (ILF) | 8 | 89 |
| External Interface Files (EIF) | 5 | 31 |
| **UFP Total** | **38** | **239** |

---

### Step 3: Value Adjustment Factor (VAF)

Each of the 14 General System Characteristics (GSC) rated **0–5**:

| # | General System Characteristic | Rating |
|---|---|---|
| 1 | Data Communications | 5 |
| 2 | Distributed Data Processing | 2 |
| 3 | Performance | 5 |
| 4 | Heavily Used Configuration | 3 |
| 5 | Transaction Rate | 5 |
| 6 | Online Data Entry | 4 |
| 7 | End-User Efficiency | 3 |
| 8 | Online Update | 5 |
| 9 | Complex Processing | 5 |
| 10 | Reusability | 3 |
| 11 | Installation Ease | 2 |
| 12 | Operational Ease | 3 |
| 13 | Multiple Sites | 1 |
| 14 | Facilitate Change | 3 |
| **TDI** | | **49** |

**VAF = 0.65 + (0.01 × TDI) = 0.65 + 0.49 = 1.14**

---

### Step 4: Adjusted Function Points (AFP)

**AFP = UFP × VAF = 239 × 1.14 = 272.5 ≈ 273 Function Points**

---

### Step 5: Effort & Cost Estimation

| Metric | Value |
|---|---|
| Adjusted FP | 273 |
| Effort at 8 hrs/FP | **2,184 person-hours** |
| Effort at 10 hrs/FP | **2,730 person-hours** |
| Team Size | 2 developers |
| Duration | ~12 weeks = 480 hrs/person |
| Cost @ ₹500/hr blended rate | **₹10.9L – ₹13.7L** |
| Productivity | ~23 FP/person-month |

---
---

## Part B: Use Case Points (UCP)

### Background

Use Case Points (UCP) was proposed by Gustav Karner in 1993. It estimates effort from use cases and actors, then adjusts for technical and environmental complexity.

---

### Step 1: Actor Weighting (UAW)

| Actor | Type | Weight | Reason |
|---|---|---|---|
| Payment Gateway | System via API | Simple = 1 | REST JSON calls |
| Fraud Analyst | GUI User | Complex = 3 | Full dashboard |
| Simulator Engine | System via API | Simple = 1 | Automated calls |
| Alert Recipient | External System | Average = 2 | Receives notifications |
| Regulatory System | External via file | Average = 2 | Compliance reports |
| ML Training System | System via API | Average = 2 | Kaggle API download |

**UAW = 1 + 3 + 1 + 2 + 2 + 2 = 11**

---

### Step 2: Use Case Weighting (UUCW)

- **Simple** (≤ 3 transactions) = 5 pts  
- **Average** (4–7 transactions) = 10 pts  
- **Complex** (> 7 transactions) = 15 pts

| # | Use Case | Complexity | Weight |
|---|---|---|---|
| UC1 | Evaluate Transaction for Fraud | Complex | 15 |
| UC2 | Pre-Authorization Decision (BLOCK/CHALLENGE/ALLOW) | Complex | 15 |
| UC3 | Generate Explainable AI Report | Complex | 15 |
| UC4 | Detect Fraud Ring via Graph | Complex | 15 |
| UC5 | Send Multi-Channel Alert | Average | 10 |
| UC6 | Manage Case (Analyst Workflow) | Average | 10 |
| UC7 | Train ML Model | Complex | 15 |
| UC8 | Run Transaction Simulation | Average | 10 |
| UC9 | View Analytics Dashboard | Average | 10 |
| UC10 | Configure Risk Thresholds | Simple | 5 |
| UC11 | Device Fingerprint + Geolocation | Average | 10 |
| UC12 | Phishing Detection | Average | 10 |
| UC13 | Merchant Reputation Scoring | Simple | 5 |
| UC14 | View Performance Metrics | Simple | 5 |

**UUCW = 150**

**UUCP = UAW + UUCW = 11 + 150 = 161**

---

### Step 3: Technical Complexity Factor (TCF)

| # | Factor | Weight | Rating | Score |
|---|---|---|---|---|
| T1 | Distributed System | 2 | 1 | 2 |
| T2 | Response/Throughput | 1 | 5 | 5 |
| T3 | End-User Efficiency | 1 | 3 | 3 |
| T4 | Complex Internal Processing | 1 | 5 | 5 |
| T5 | Code Reusability | 1 | 3 | 3 |
| T6 | Easy to Install | 0.5 | 2 | 1 |
| T7 | Easy to Use | 0.5 | 3 | 1.5 |
| T8 | Portable | 2 | 2 | 4 |
| T9 | Easy to Change | 1 | 3 | 3 |
| T10 | Concurrent | 1 | 4 | 4 |
| T11 | Special Security | 1 | 5 | 5 |
| T12 | Direct 3rd Party Access | 1 | 3 | 3 |
| T13 | Special User Training | 1 | 2 | 2 |
| **Sum** | | | | **41.5** |

**TCF = 0.6 + (0.01 × 41.5) = 1.015 ≈ 1.02**

---

### Step 4: Environmental Factor (ECF)

| # | Factor | Weight | Rating | Score |
|---|---|---|---|---|
| E1 | Familiar with dev process | 1.5 | 3 | 4.5 |
| E2 | Application experience | 0.5 | 3 | 1.5 |
| E3 | OO experience | 1 | 4 | 4 |
| E4 | Lead analyst capability | 0.5 | 3 | 1.5 |
| E5 | Motivation | 1 | 4 | 4 |
| E6 | Stable requirements | 2 | 3 | 6 |
| E7 | Part-time workers | −1 | 2 | −2 |
| E8 | Difficult programming language | −1 | 1 | −1 |
| **Sum** | | | | **18.5** |

**ECF = 1.4 + (−0.03 × 18.5) = 1.4 − 0.555 = 0.845 ≈ 0.85**

---

### Step 5: Final Use Case Points

**UCP = UUCP × TCF × ECF = 161 × 1.02 × 0.85 = 139.6 ≈ 140**

---

### Step 6: Effort from UCP

**Industry standard: 20 person-hours/UCP**

| Metric | Value |
|---|---|
| Final UCP | 140 |
| Effort @ 20 hrs/UCP | **2,800 person-hours** |
| Team Size | 2 developers |

---

## Summary: Both Methods Compared

| Method | Size Metric | Effort Estimate |
|---|---|---|
| Function Point Analysis | 273 Adjusted FP | 2,184 – 2,730 hrs |
| Use Case Points | 140 UCP | 2,800 hrs |
| **Convergence** | | **~2,500 person-hours** |

> The ARGUS prototype scope covers ~30–40% of the full system, requiring approximately **800–1,000 person-hours** across the 12-week development sprint by a 2-person team.
