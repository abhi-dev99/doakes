# Documentation: `case_management.py`

## 1. Purpose
The `CaseManagementSystem` provides the human-in-the-loop workflow for the ARGUS platform. While the ML engine makes automated decisions, borderline transactions or manually flagged alerts must be reviewed by human fraud analysts. This module handles the queueing, assignment, and feedback loop for these reviews.

## 2. Core Architecture & Database

### A. Database Schema
It uses the central `argus_data.db` (SQLite) to maintain three specific tables:
1.  `fraud_cases`: The master list of all transactions sent for review. Contains priority, assigned analyst, and current status (`PENDING`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`).
2.  `analyst_actions`: An audit log of who touched a case and when.
3.  `model_feedback`: The most critical table for continuous ML learning. Stores the true labels provided by analysts.

### B. Core Workflows
*   **Queue Generation (`create_case`)**: When `fraud_model.py` generates a decision of `REVIEW` (usually because the risk score is between the `medium_risk` and `high_risk` thresholds), it calls this function to drop the transaction into the pending queue.
*   **Analyst Review (`review_case`)**: Analysts fetch cases via the API, review the data, and submit a decision. If they confirm it's fraud or flag it as a false positive, the `true_label` is updated.

## 3. The Continuous Learning Feedback Loop
The most advanced feature of this module is `get_feedback_for_training()`.
*   When analysts provide a `true_label`, it is saved to the `model_feedback` table.
*   Periodically, data science pipelines can query this endpoint to extract newly labeled data.
*   This ground-truth data is used to continually retrain the XGBoost and LightGBM models, reducing False Positives and adapting to model drift over time.

## 4. Assumptions & Limitations
*   **Limitation (Concurrency)**: As with the main engine, managing a live, multi-analyst case queue using SQLite will lead to database locking issues in a high-volume production environment.
*   **Assumption**: Assumes analysts actually review the cases. If the queue backs up, the feedback loop breaks.

## 5. Role in Architecture
Provides the operational backend for the "Case Review" section of the frontend dashboard, turning ARGUS from a simple prediction API into a fully operational fraud management platform.
