# Documentation: `upi_fraud_patterns.py`

## 1. Purpose
This module contains the `UPIFraudDetector`, a highly specialized heuristic engine designed specifically for the Indian payment ecosystem. While standard ML models detect generic mathematical anomalies, this module codifies the exact *narratives* and *archetypes* of known Indian scams based on RBI reports.

## 2. Key Fraud Archetypes Detected

### A. Digital Arrest Scams
Victims are coerced into transferring money to "safe accounts" by fraudsters impersonating law enforcement.
*   **Trigger**: High-value transfer > ₹50K to an `individual` account, combined with keywords like `police`, `cbi`, `ed`, `customs`, or `narcotics` found in the merchant name or transaction notes.

### B. SIM Swap Attacks
Fraudsters duplicate a user's SIM to intercept OTPs.
*   **Trigger**: A transaction from a completely new `device_id` AND a new geographic state/location, occurring rapidly, often during unusual night hours (2 AM - 6 AM).

### C. Mule Account Networks
Accounts used solely to receive illicit funds and bounce them to a secondary layer.
*   **Trigger**: An account < 30 days old receiving rapid transfers from multiple unique senders and immediately draining the funds out to multiple receivers. It specifically looks for a `avg_debit / avg_credit` ratio of ~1.0 (money-in-money-out) and round-number structuring (₹10K, ₹50K).

### D. QR Code / Phishing Scams
"Scan this to receive money" scams.
*   **Trigger**: A high-value QR payment to an `individual` with suspicious terms like `cashback`, `reward`, or `kyc` in the name.
*   **UPI ID Matching**: It cross-references the prefix of the UPI ID (e.g., `sunil123@okaxis`) with the registered merchant name. A total mismatch is flagged.

## 3. Core Logic / Workflow
The `analyze_transaction()` method acts as a router. It runs the transaction payload through all 5 independent detector functions simultaneously.
If any detector returns `True`, it flags `is_upi_fraud=True`, aggregates the reasons, and automatically assigns the official RBI Classification string (e.g., "Account Takeover Fraud", "Social Engineering").

## 4. Assumptions & Limitations
*   **Limitation (Regex Dependency)**: The Digital Arrest and QR Code detectors rely heavily on parsing string notes and merchant names. Fraudsters can evade this by using misspelled words or leaving notes blank.
*   **Assumption**: Assumes the `user_history` payload passed into the Mule Account detector contains accurate chronological ledgers.

## 5. Role in Architecture
This is a booster module. It is called by `fraud_model.py` *after* the ML ensemble executes. If this module finds a specific UPI pattern, it artificially boosts the final risk score by +0.10 to ensure the transaction triggers a block/challenge, overriding the ML model if the ML model missed the narrative context.
