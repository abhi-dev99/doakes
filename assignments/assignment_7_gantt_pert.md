# Assignment 7 — Software Project Plan: Gantt & PERT Charts
### Project: ARGUS — AI-Powered Fraud Detection System

---

## 1. Project Overview

**Project Name:** ARGUS (Advanced Real-time Guard & User Security)  
**Type:** AI/ML-based Pre-Authorization Fraud Detection  
**Duration:** 12 Weeks (Phase 1 / Prototype)  
**Team Size:** 2–3 members  
**Start Date:** Week 1 (January 2026)

---

## 2. Work Breakdown Structure (WBS)

| Phase | Description | Sub-Tasks |
|---|---|---|
| P1 | Requirements & Planning | SoW, stakeholder analysis, feature list |
| P2 | System Design | Architecture, DFD (L0/L1/L2), class & state diagram, DB schema |
| P3 | Backend Core | FastAPI setup, DB models, REST API, WebSocket |
| P4 | ML Pipeline | Feature engineering, XGBoost, Isolation Forest, ensemble |
| P5 | Advanced ML Modules | Pre-auth engine, device intelligence, graph fraud, phishing, XAI |
| P6 | Frontend Dashboard | React/Vite, dashboard views, WebSocket feed, charts |
| P7 | Integration & Testing | End-to-end integration, unit tests, simulation testing |
| P8 | Documentation & Demo | README, pitch guide, demo script, video |

---

## 3. Gantt Chart

```
WEEK:          1    2    3    4    5    6    7    8    9   10   11   12
               |----|----|----|----|----|----|----|----|----|----|----|----|

P1: Requirements
  SoW Writing  [====]
  Arch Design       [====]

P2: System Design
  DFD / UML             [====]
  DB Schema             [====]

P3: Backend Core
  FastAPI Setup               [====]
  REST API / WS                    [====]
  SQLite Integration              [====]

P4: ML Pipeline
  Data Prep & EDA               [====]
  Feature Engineering                [========]
  XGBoost Training                        [====]
  Isolation Forest                        [====]
  Ensemble + Threshold                         [====]

P5: Advanced Modules
  Pre-Auth Engine                     [====]
  Device Intelligence                      [====]
  Graph Fraud Detector                          [====]
  Phishing Protection                           [====]
  Explainable AI (XAI)                               [====]
  Alert & Case Mgmt                                  [====]

P6: Frontend
  React/Vite Setup                    [====]
  Dashboard UI                             [========]
  Charts & Simulation                               [====]

P7: Testing
  Integration Testing                                    [====]
  Performance Tuning                                     [====]
  Bug Fixes                                                   [====]

P8: Documentation
  README / SoW Final                                         [====]
  Pitch Guide / Demo                                              [====]
```

### Gantt Summary Table

| Task | Start | End | Duration | Dependencies |
|---|---|---|---|---|
| SoW Writing | W1 | W2 | 2 weeks | — |
| Architecture Design | W2 | W3 | 2 weeks | SoW |
| DFD / UML Diagrams | W3 | W4 | 2 weeks | Architecture |
| DB Schema Design | W3 | W4 | 1 week | Architecture |
| FastAPI Setup | W4 | W5 | 1 week | DB Schema |
| REST API + WebSocket | W5 | W6 | 2 weeks | FastAPI Setup |
| Data Prep & EDA | W4 | W5 | 1 week | DB Schema |
| Feature Engineering | W5 | W7 | 3 weeks | Data Prep |
| XGBoost Training | W6 | W7 | 2 weeks | Feature Eng. |
| Isolation Forest | W6 | W7 | 2 weeks | Feature Eng. |
| Ensemble + Threshold | W7 | W8 | 1 week | XGBoost + IF |
| Pre-Auth Engine | W5 | W7 | 2 weeks | REST API |
| Device Intelligence | W6 | W7 | 2 weeks | Pre-Auth |
| Graph Fraud Detector | W7 | W8 | 2 weeks | Pre-Auth |
| Phishing Protection | W7 | W8 | 2 weeks | Pre-Auth |
| Explainable AI | W8 | W9 | 2 weeks | All ML modules |
| Alert & Case Mgmt | W8 | W9 | 2 weeks | REST API |
| React/Vite Setup | W5 | W6 | 1 week | FastAPI |
| Dashboard UI | W6 | W8 | 3 weeks | React Setup |
| Charts & Simulation | W8 | W9 | 2 weeks | Dashboard UI |
| Integration Testing | W9 | W10 | 2 weeks | All above |
| Performance Tuning | W9 | W10 | 2 weeks | Integration |
| Bug Fixes | W10 | W11 | 1 week | Testing |
| README / SoW Final | W10 | W11 | 1 week | Testing |
| Pitch & Demo Prep | W11 | W12 | 2 weeks | All complete |

**Critical Path:** SoW → Architecture → DB Schema → FastAPI → Feature Engineering → ML Training → Ensemble → Explainable AI → Integration Testing → Demo

---

## 4. PERT Chart

### PERT Formula

- **O** = Optimistic time (best case)  
- **M** = Most Likely time  
- **P** = Pessimistic time (worst case)  
- **Expected Time: tₑ = (O + 4M + P) / 6**  
- **Variance: σ² = ((P − O) / 6)²**

---

### PERT Task Estimates (weeks)

| Task ID | Task Name | O | M | P | **tₑ** | σ² |
|---|---|---|---|---|---|---|
| T1 | SoW & Requirements | 1 | 2 | 3 | **2.0** | 0.11 |
| T2 | System Architecture | 1 | 2 | 4 | **2.2** | 0.25 |
| T3 | DFD + UML Diagrams | 1 | 1.5 | 3 | **1.7** | 0.11 |
| T4 | DB Schema | 0.5 | 1 | 2 | **1.1** | 0.06 |
| T5 | FastAPI Backend Setup | 0.5 | 1 | 2 | **1.1** | 0.06 |
| T6 | REST API + WebSocket | 1 | 2 | 4 | **2.2** | 0.25 |
| T7 | Data Prep & EDA | 1 | 1.5 | 3 | **1.7** | 0.11 |
| T8 | Feature Engineering | 2 | 3 | 5 | **3.2** | 0.25 |
| T9 | XGBoost Training | 1 | 2 | 4 | **2.2** | 0.25 |
| T10 | Isolation Forest | 0.5 | 1 | 2 | **1.1** | 0.06 |
| T11 | Ensemble Model | 0.5 | 1 | 2 | **1.1** | 0.06 |
| T12 | Pre-Auth Engine | 1 | 2 | 3 | **2.0** | 0.11 |
| T13 | Device Intelligence | 1 | 2 | 4 | **2.2** | 0.25 |
| T14 | Graph Fraud Detector | 1 | 2 | 4 | **2.2** | 0.25 |
| T15 | Phishing Protection | 1 | 1.5 | 3 | **1.7** | 0.11 |
| T16 | Explainable AI | 1 | 2 | 4 | **2.2** | 0.25 |
| T17 | Alert & Case Mgmt | 1 | 2 | 3 | **2.0** | 0.11 |
| T18 | React Dashboard | 1 | 2 | 4 | **2.2** | 0.25 |
| T19 | Charts & Simulation | 1 | 2 | 3 | **2.0** | 0.11 |
| T20 | Integration Testing | 1 | 2 | 4 | **2.2** | 0.25 |
| T21 | Performance Tuning | 0.5 | 1 | 2 | **1.1** | 0.06 |
| T22 | Documentation | 0.5 | 1 | 2 | **1.1** | 0.06 |
| T23 | Pitch & Demo Prep | 0.5 | 1 | 2 | **1.1** | 0.06 |

---

### PERT Network Diagram (Text Form)

```
(START)
   |
   T1: SoW (2.0w)
   |
   T2: Architecture (2.2w)
   |         \
   T3:DFD    T4: DB Schema (1.1w)
   (1.7w)    |           \
             T5:FastAPI   T7:Data Prep
             (1.1w)       (1.7w)
             |             |
             T6:API(2.2w)  T8:Feature Eng.(3.2w)
             |             |       \
             |          T9:XGB   T10:IF
             |          (2.2w)   (1.1w)
             |             \      /
             |           T11:Ensemble(1.1w)
             |                 |
          T12:Pre-Auth(2.0w)   T16:XAI(2.2w)
          /   \                     |
       T13   T14                    |
       T15   T17                    |
        \     |    T18:React(2.2w)  |
         \    |    T19:Charts(2.0w) |
          \   |         |           |
          T20: Integration Testing (2.2w)
               |
          T21: Perf Tuning (1.1w)
               |
          T22: Documentation (1.1w)
               |
          T23: Demo Prep (1.1w)
               |
            (END)
```

---

### Critical Path Calculation

**Critical Path:** T1 → T2 → T4 → T8 → T9 → T11 → T12 → T16 → T20 → T21 → T22 → T23

| Task | tₑ (weeks) | σ² |
|---|---|---|
| T1: SoW | 2.0 | 0.11 |
| T2: Architecture | 2.2 | 0.25 |
| T4: DB Schema | 1.1 | 0.06 |
| T8: Feature Engineering | 3.2 | 0.25 |
| T9: XGBoost Training | 2.2 | 0.25 |
| T11: Ensemble | 1.1 | 0.06 |
| T12: Pre-Auth Engine | 2.0 | 0.11 |
| T16: Explainable AI | 2.2 | 0.25 |
| T20: Integration Testing | 2.2 | 0.25 |
| T21: Performance Tuning | 1.1 | 0.06 |
| T22: Documentation | 1.1 | 0.06 |
| T23: Demo Prep | 1.1 | 0.06 |
| **TOTAL** | **21.5 weeks** | **1.77** |

**σ = √1.77 = 1.33 weeks**  
**95% confidence interval:** 21.5 ± (1.65 × 1.33) ≈ **19.3 – 23.7 weeks** (sequential tasks)  
**Actual wall-clock time with parallelism:** ~12 weeks

> Any delay in the critical path tasks directly delays the project completion date.

---

## 5. Milestones

| Milestone | Target Week | Description |
|---|---|---|
| M1: Design Complete | End of W4 | SoW, architecture, DFDs, DB schema finalized |
| M2: Backend Live | End of W6 | FastAPI running with REST API and WebSocket |
| M3: ML Models Trained | End of W8 | XGBoost + ensemble + all advanced modules working |
| M4: Frontend Complete | End of W9 | Full React dashboard with live simulation |
| M5: System Integrated | End of W10 | Full end-to-end system verified |
| M6: Demo Ready | End of W12 | Pitch, demo video, documentation complete |
