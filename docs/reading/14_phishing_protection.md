# Documentation: `phishing_protection.py`

## 1. Purpose
This module is the **Cybersecurity Layer** of the fraud detection system. It protects against attacks where the *victim's account is compromised*, rather than attacks where the victim is socially engineered into sending money. It detects Session Hijacking, CSRF (Cross-Site Request Forgery), and Man-in-the-Browser attacks.

## 2. Core Checks & Scenarios (`check_unauthorized_transaction`)

The engine runs 6 sequential security checks on the HTTP context of the transaction:

### 1. Session Hijacking (`_check_session_hijacking`)
Tracks stateful session data. If a transaction arrives on a known `user_id` but the IP address has suddenly changed to a different country, or the `User-Agent` string has swapped (e.g., from Chrome/Windows to Safari/iOS) mid-session, it flags a hijacked session.

### 2. Suspicious Referrer (`_check_suspicious_referrer`)
Analyzes the `HTTP Referer` header.
*   **Phishing Links**: Flags transactions originating from URL shorteners (`bit.ly`, `tinyurl`) or free, high-abuse TLDs (`.tk`, `.ml`).
*   **Typosquatting**: Looks for fake banking domains containing keywords like `secure`, `login`, or `update` (e.g., `paytm-secure.tk`).

### 3. Automated API Abuse (`_check_user_interaction`)
Relies on frontend telemetry (if provided). If a transaction API call is made with 0 mouse movements, 0 keyboard inputs, and <3 seconds of time spent on the page, it strongly indicates a Python script or bot made the API call, not a human using the frontend React app.

### 4. CSRF Attack (`_check_csrf`)
Validates the presence of a matching CSRF token in the request headers to ensure a malicious third-party site didn't force the user's browser to execute the payment API.

### 5. Fake Payment Page (`_check_origin_mismatch`)
Verifies that the `Origin` header matches the strict whitelist of expected bank domains.

### 6. Temporal Anomaly (`_check_temporal_anomaly`)
Flags if a transaction occurs immediately (< 30 seconds) after the creation of a session, indicating automated credential stuffing and immediate draining of funds.

## 3. Decision Matrix
Based on the checks above, it calculates a `risk_score`:
*   **>= 0.60**: Flags the transaction as `is_unauthorized=True` and sets `requires_verification=True` (triggering an immediate OTP challenge).
*   **>= 0.80**: Flags the transaction as `should_block=True` (instantly terminating the request).

## 4. Assumptions & Limitations
*   **Limitation (Telemetry Dependency)**: Checks #3 and #6 absolutely require the frontend application to capture DOM telemetry (mouse events, focus events, session duration) and bundle it into an `http_context` payload attached to the transaction API request.
*   **Assumption**: Assumes attackers are not spoofing headers. Advanced attackers can easily spoof `Referer`, `Origin`, and `User-Agent` in automated scripts, making these checks less effective against sophisticated adversaries.

## 5. Role in Architecture
Operates alongside the `PreAuthEngine`. If this module flags a high risk of cyber-compromise, the transaction is rejected for security reasons, regardless of whether the transaction amount looks normal to the ML models.
