# Documentation: `alert_notifications.py`

## 1. Purpose
The `AlertNotificationSystem` handles the outbound communication of the ARGUS platform. When the core ensemble flags a transaction with a high risk score or blocks it entirely, this module determines *who* to notify and *how* to notify them (Email, SMS, Slack).

## 2. Alert Tiering System
The module categorizes alerts into three distinct priorities based on the severity of the threat and the decision made by the Pre-Auth engine:

### A. CRITICAL (Threshold > 90% or Graph/Phishing)
*   **Triggers**: Highly confident ML predictions (>90%), detection of Mule Accounts via NetworkX, or Phishing/Session Hijacking detected by the cybersecurity module.
*   **Action**: Blasts an alert across ALL channels instantly (Email, SMS, and Slack).

### B. HIGH (Threshold > 75% or Hard Block)
*   **Triggers**: The Pre-Auth Engine issued a hard `BLOCK` (e.g., velocity violation), or the transaction amount is extremely large (>₹100,000) combined with medium risk.
*   **Action**: Notifies via Email and Slack. Skips SMS to prevent alert fatigue.

### C. MEDIUM (Threshold > 60% or Soft Challenge)
*   **Triggers**: The Pre-Auth Engine issued a `CHALLENGE` (requiring OTP/Biometrics), or a new device was used.
*   **Action**: Logs quietly to a dedicated Slack channel for asynchronous review.

## 3. Implementation Details
*   **Payload Formatting**: The module dynamically crafts the notification payload based on the destination. For example, SMS alerts are strictly capped at 160 characters, while Slack alerts use Block Kit formatting with color-coded borders (Red for Critical, Orange for High).
*   **Simulation vs Production**: Currently, the `send_alert()` method is in **Simulation Mode**. It logs the formatted payloads to the console instead of making actual Twilio or SendGrid API calls. This is to avoid API costs during the hackathon/viva.
*   **In-Memory State**: Uses `collections.deque` with a `maxlen=1000` to store recent alerts. This powers the "Recent Alerts" widget on the frontend dashboard without needing constant DB queries.

## 4. Role in Architecture
Sits at the very end of the inference pipeline in `main.py`. Once a transaction is processed and the `explainable_ai` module has generated the human-readable headline, this module packages that data and distributes it to the ops team.
