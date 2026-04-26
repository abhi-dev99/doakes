# Documentation: `merchant_reputation.py`

## 1. Purpose
This module manages the **Merchant Risk Scoring and Reputation System**. While user behavior tracks the *sender* of funds, this module tracks the *receiver*. It maintains a reputation score (0-100) for every merchant on the network based on their industry category, chargeback history, and historical fraud associations.

## 2. Key Components & Parameters

### Category Risk Baselines (`CATEGORY_RISK_SCORES`)
Certain industries carry inherently higher fraud risks. The system hardcodes these baselines (out of 100):
*   `crypto`: 85
*   `gambling`: 80
*   `forex`: 75
*   `dating`: 70
*   ...
*   `groceries`: 20
*   `utilities`: 10

### Reputation Score Math
Every merchant starts with a neutral score of 50. The score is dynamically updated (`_update_reputation`) based on 5 factors:
1.  **Chargeback Ratio**: >2% reduces score by 30 points. >1% reduces by 20. <0.5% adds 10 points.
2.  **Fraud Reports**: Absolute count of user-reported fraud associated with this merchant ID.
3.  **Volume & Age**: Established merchants (>1000 txns) get a +15 point trust bonus.
4.  **Category Baseline**: The score is pulled down heavily if they operate in a high-risk category like crypto.
5.  **Recent Fraud Pattern**: If >10% of the last 50 transactions were flagged, the score drops by 25 points.

## 3. Core Logic / Workflow
1.  **`record_transaction()`**: Called every time a transaction occurs. Updates total volume and updates the reputation score.
2.  **`calculate_merchant_risk()`**: Called during the `PreAuthEngine` execution. It calculates the live risk of a specific transaction hitting a specific merchant.
    *   If a user is buying ₹500 of groceries, the risk is negligible.
    *   If a user is buying ₹500 of crypto from a merchant with a 40/100 reputation score, the risk score spikes.
3.  **Penalty Mechanics**: If a merchant's reputation drops below 30/100, the system automatically appends "Poor merchant reputation" to the transaction risk factors, drastically increasing the likelihood of the Pre-Auth engine blocking the payment.

## 4. Assumptions & Limitations
*   **Limitation (State)**: Uses in-memory dictionaries (`merchant_database`, `chargeback_history`). In production, this requires a persistent database (PostgreSQL/Redis) to survive restarts and share state across API nodes.
*   **Assumption**: Assumes the presence of a robust backend mechanism to actually feed chargeback data (`record_chargeback()`) and user fraud reports (`record_fraud_report()`) into the system asynchronously. If this feedback loop is broken, the reputation scores will stagnate.

## 5. Role in Architecture
Instantiated as a global `merchant_reputation_system`. It is queried heavily by the `PreAuthEngine` to make sub-20ms decisions on whether the destination of the funds is a known scammer or a high-risk entity.
