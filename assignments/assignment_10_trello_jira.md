# Assignment 10 — Hands-on with Project Management Tools
## Trello & JIRA — ARGUS Fraud Detection System

---

## Overview

| Tool | Best For | Format |
|---|---|---|
| **Trello** | Visual Kanban, quick setup, small teams | Cards on lists (columns) |
| **JIRA** | Sprint planning, story points, velocity tracking | Backlog + Sprints (Scrum) |

---

---

# PART A: TRELLO

## What is Trello?

Trello is a **Kanban board** tool where tasks are represented as **cards** inside **lists** (columns). Cards move left to right as work progresses.

### Key Concepts
- **Board** — The project (one board per project)
- **List** — A status column (To Do, In Progress, Done, etc.)
- **Card** — A task
- **Checklist** — Sub-tasks inside a card
- **Label** — Color-coded category tags
- **Member** — Team member assigned to a card

---

## ARGUS Trello Board

**Board Name:** ARGUS — AI Fraud Detection  
**Workspace:** Team / College Name

---

### Board Layout — 5 Lists

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   BACKLOG    │  │    TO DO     │  │ IN PROGRESS  │  │    REVIEW    │  │     DONE     │
│              │  │  (This Week) │  │  (Active)    │  │  (Testing)   │  │  (Complete)  │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

---

### Label Legend

| Color | Category |
|---|---|
| 🔴 Red | ML / Backend |
| 🔵 Blue | Frontend / UI |
| 🟡 Yellow | Documentation |
| 🟢 Green | Done |
| 🟠 Orange | Infrastructure / DevOps |

---

### BACKLOG List

| Card | Label | Due | Notes |
|---|---|---|---|
| Federated Learning Integration | 🔴 ML | Future | Post-prototype scope |
| Mobile SDK Development | 🔵 UI | Future | Future release |
| Redis Velocity Caching | 🟠 Infra | Future | Replace in-memory counters |
| Blockchain Audit Trail | 🔴 ML | Future | Regulatory enhancement |
| Real-time Model Online Learning | 🔴 ML | Future | Post-MVP |

---

### TO DO List (Current Sprint)

| Card | Label | Due | Assigned | Checklist Items |
|---|---|---|---|---|
| Download Kaggle UPI Dataset | 🔴 ML | Day 1 | Dev A | ☐ Setup API key ☐ Run download ☐ Verify file size |
| Run Combined Model Training | 🔴 ML | Day 2 | Dev A | ☐ Run script ☐ Verify 8 model files ☐ Check accuracy |
| Build Settings Panel | 🔵 UI | Day 2 | Dev B | ☐ Threshold sliders ☐ Engine toggles ☐ Wire to API |
| Analyze Survey Data | 🟡 Docs | Day 2 | Dev B | ☐ Open CSV ☐ Compute stats ☐ Add to pitch |
| Format Rule Strings (Human-readable) | 🔵 UI | Day 3 | Dev B | ☐ Map all RULE_CODES to readable text |
| Record Backup Demo Video | 🟡 Docs | Day 3 | Both | ☐ Run demo ☐ Record screen ☐ Export MP4 |

---

### IN PROGRESS List

| Card | Label | Progress | Notes |
|---|---|---|---|
| Integrate Combined ML Models | 🔴 ML | 50% | Waiting for training to complete |
| Rehearse Pitch (8 min) | 🟡 Docs | 30% | Pitch guide ready |

---

### REVIEW List

| Card | Who Reviews | Status |
|---|---|---|
| Backend stress test (100 txns) | Dev A reviews Dev B's integration | In Testing |
| Dashboard cross-browser check | Both | Chrome + Edge verified |

---

### DONE List

| Card | Completed |
|---|---|
| SoW — Statement of Work | Week 2 |
| System Architecture Design | Week 3 |
| DFD (Level 0, 1, 2) | Week 4 |
| Class Diagram + State Diagram | Week 4 |
| FastAPI Backend Setup | Week 5 |
| SQLite DB Integration | Week 5 |
| REST API + WebSocket | Week 6 |
| Data Prep & Feature Engineering | Week 7 |
| XGBoost + Isolation Forest Training | Week 7 |
| Ensemble Model + Threshold | Week 8 |
| Pre-Authorization Engine | Week 7 |
| Device Intelligence Module | Week 7 |
| Graph Fraud Ring Detector | Week 8 |
| Phishing Protection (6-layer) | Week 8 |
| Explainable AI (SHAP) | Week 9 |
| Alert & Notification System | Week 9 |
| Case Management Module | Week 9 |
| React Dashboard (core) | Week 9 |
| Fraud Ring Visualization | Week 9 |
| Performance Metrics Panel | Week 9 |
| Pitch Guide | Week 10 |

---

### Trello Power-Ups to Enable

1. **Calendar** — view cards with due dates on a calendar
2. **Card Aging** — older untouched cards fade to highlight stale work
3. **Checklist** — sub-tasks inside each card
4. **Labels** — color-coded categories as above
5. **Members** — assign team members to each card

---

### How to Set Up Trello (Steps)

1. Go to [trello.com](https://trello.com) → sign up (free)
2. Click **Create Board** → Name it "ARGUS Fraud Detection"
3. Create 5 lists: Backlog, To Do, In Progress, Review, Done
4. Add all cards listed above
5. Open each card → add checklist items → set due dates → assign members
6. Use Labels to color-code by category
7. As work progresses, drag cards from list to list

---

---

# PART B: JIRA

## What is JIRA?

JIRA is an enterprise-grade **Agile project management tool** used across the software industry. It supports:

- **Epics** — Large features (groups of stories)
- **Stories** — User-facing requirements ("As a user, I want...")
- **Tasks** — Technical sub-tasks under stories
- **Bugs** — Defects to fix
- **Sprints** — Fixed time-boxed iterations (1–2 weeks)
- **Story Points** — Relative effort estimates (Fibonacci: 1, 2, 3, 5, 8, 13...)

---

## ARGUS JIRA Project Setup

**Project Name:** ARGUS  
**Project Key:** ARG  
**Type:** Scrum  
**Sprint Length:** 2 weeks

---

## Epics

| Epic ID | Epic Name | Description |
|---|---|---|
| ARG-E1 | Requirements & Design | SoW, architecture, diagrams |
| ARG-E2 | Backend Core | FastAPI, REST API, DB, WebSocket |
| ARG-E3 | ML Pipeline | Data prep, training, ensemble |
| ARG-E4 | Advanced ML Modules | Pre-auth, device, graph, phishing, XAI |
| ARG-E5 | Frontend Dashboard | React app, charts, simulation |
| ARG-E6 | Integration & Testing | End-to-end testing, performance |
| ARG-E7 | Documentation & Demo | README, pitch, demo video |

---

## Product Backlog (Stories + Tasks)

### Epic ARG-E2: Backend Core

| ID | Type | Summary | Points | Priority |
|---|---|---|---|---|
| ARG-10 | Story | As a payment gateway, I want to POST a transaction and get BLOCK/CHALLENGE/ALLOW in <20ms | 8 | Highest |
| ARG-11 | Task | Setup FastAPI project with uvicorn | 2 | High |
| ARG-12 | Task | Create SQLite schema for transactions | 3 | High |
| ARG-13 | Task | Implement POST /api/transactions | 3 | High |
| ARG-14 | Task | Implement WebSocket /ws/transactions | 5 | High |
| ARG-15 | Story | As an analyst, I want GET /api/transactions with filters | 3 | Medium |

### Epic ARG-E3: ML Pipeline

| ID | Type | Summary | Points | Priority |
|---|---|---|---|---|
| ARG-20 | Story | As the system, I want fraud probability predicted within 10ms | 13 | Highest |
| ARG-21 | Task | Download and merge PaySim + Kaggle UPI datasets | 5 | Highest |
| ARG-22 | Task | Engineer 40+ features from combined dataset | 8 | Highest |
| ARG-23 | Task | Train XGBoost with SMOTE + early stopping | 8 | Highest |
| ARG-24 | Task | Train LightGBM model | 5 | High |
| ARG-25 | Task | Train Isolation Forest anomaly detector | 3 | High |
| ARG-26 | Task | Build weighted ensemble (XGB+LGB+IF) | 5 | High |
| ARG-27 | Task | Optimize F1 threshold and save all model files | 3 | High |

### Epic ARG-E4: Advanced ML Modules

| ID | Type | Summary | Points | Priority |
|---|---|---|---|---|
| ARG-30 | Story | As the system, I want to BLOCK transactions BEFORE payment is authorized | 13 | Highest |
| ARG-31 | Task | Implement velocity tracking (1min/5min/1hr/24hr) | 8 | Highest |
| ARG-32 | Task | Implement device fingerprinting + reputation | 5 | High |
| ARG-33 | Task | Implement graph fraud ring detection (NetworkX) | 8 | High |
| ARG-34 | Task | Implement 6-layer phishing detection | 5 | High |
| ARG-35 | Story | As an analyst, I want human-readable XAI explanations | 8 | High |
| ARG-36 | Task | Implement SHAP value computation | 5 | High |
| ARG-37 | Task | Generate rule-based explanation text | 3 | Medium |
| ARG-38 | Task | Implement multi-channel alert notifications | 5 | Medium |
| ARG-39 | Task | Implement case management workflow | 5 | Medium |

### Epic ARG-E5: Frontend

| ID | Type | Summary | Points | Priority |
|---|---|---|---|---|
| ARG-40 | Story | As an analyst, I want a real-time dashboard with live transaction feed | 13 | Highest |
| ARG-41 | Task | Setup React 18 + Vite project | 2 | High |
| ARG-42 | Task | Build header, stat cards, India banner | 3 | High |
| ARG-43 | Task | Build expandable transaction feed | 8 | High |
| ARG-44 | Task | Build risk distribution pie chart | 3 | Medium |
| ARG-45 | Task | Build fraud ring network visualization | 8 | Medium |
| ARG-46 | Story | As an analyst, I want to configure risk thresholds from the UI | 5 | Medium |
| ARG-47 | Task | Build Settings panel with sliders and engine toggles | 5 | Medium |

---

## Sprint Planning

### Sprint 1 — Foundation (Weeks 1–2)
**Sprint Goal:** SoW written, backend running, DB set up

| Issue | Points | Assignee |
|---|---|---|
| ARG-11 FastAPI Setup | 2 | Dev A |
| ARG-12 SQLite Schema | 3 | Dev A |
| ARG-13 REST Endpoint | 3 | Dev A |
| ARG-41 React/Vite Setup | 2 | Dev B |
| ARG-21 Dataset Download | 5 | Dev A |
| **Sprint Total** | **15** | |

---

### Sprint 2 — ML Core (Weeks 3–6)
**Sprint Goal:** ML models trained and integrated into backend API

| Issue | Points | Assignee |
|---|---|---|
| ARG-22 Feature Engineering | 8 | Dev A |
| ARG-23 XGBoost Training | 8 | Dev A |
| ARG-25 Isolation Forest | 3 | Dev A |
| ARG-26 Ensemble Model | 5 | Dev A |
| ARG-14 WebSocket | 5 | Dev B |
| ARG-42 Dashboard Header | 3 | Dev B |
| **Sprint Total** | **32** | |

---

### Sprint 3 — Advanced Modules + Full UI (Weeks 7–10)
**Sprint Goal:** All 7 ML modules active, full React dashboard live

| Issue | Points | Assignee |
|---|---|---|
| ARG-31 Velocity Tracking | 8 | Dev A |
| ARG-33 Graph Fraud | 8 | Dev A |
| ARG-35 XAI | 8 | Dev A |
| ARG-43 Transaction Feed | 8 | Dev B |
| ARG-45 Fraud Ring Viz | 8 | Dev B |
| ARG-47 Settings Panel | 5 | Dev B |
| **Sprint Total** | **45** | |

---

## JIRA Workflow States

```
Open  ──►  In Progress  ──►  Code Review  ──►  Testing  ──►  Done
                  ▲__________________________|
                  (fails review → back to In Progress)
```

---

## Progress Monitoring

### JIRA Reports

| Report | What It Shows |
|---|---|
| Sprint Burndown Chart | Remaining story points vs days left in sprint |
| Velocity Chart | Points completed per sprint (capacity trend) |
| Cumulative Flow | Issues in each state over time |
| Epic Progress | % complete per epic |

### Velocity Tracking

| Sprint | Planned | Completed | Velocity |
|---|---|---|---|
| Sprint 1 | 15 pts | 14 pts | 93% |
| Sprint 2 | 32 pts | 30 pts | 94% |
| Sprint 3 | 45 pts | 40 pts | 89% |
| **Average** | | | **~28 pts/sprint** |

---

## How to Set Up JIRA (Steps)

1. Go to [atlassian.com/software/jira](https://atlassian.com/software/jira) → Free plan
2. Create Project → Choose **Scrum** template
3. Set Project Name: ARGUS | Key: ARG
4. Go to **Backlog** → Create Epics (E1–E7 from the table above)
5. Create Stories and Tasks under each Epic
6. Set story points on each issue
7. **Create Sprint 1** → Drag 15 points of issues into it → Start Sprint
8. As work progresses: drag issues from **To Do → In Progress → Done**
9. Check the **Burndown Chart** daily
10. At end of sprint: Sprint Review → Retrospective → Plan Sprint 2

---

## Trello vs JIRA — When to Use Which

| Situation | Recommended |
|---|---|
| Small team, quick visual overview | **Trello** |
| Sprint planning with story points | **JIRA** |
| Tracking bugs with priority/severity | **JIRA** |
| Simple Kanban drag-and-drop | **Trello** |
| Reporting velocity to stakeholders | **JIRA** |
| Hackathon (fast moving, simple) | **Trello** |
| Corporate internship / industry project | **JIRA** |
