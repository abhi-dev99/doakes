# Documentation: `device_intelligence.py`

## 1. Purpose
This module forms a critical part of the "Specialized Intelligence" layer. It is designed to look beyond the financial numbers of a transaction and analyze *how* the transaction is being executed. It detects bots, account takeovers, VPN/Tor usage, and device spoofing.

## 2. Key Components

### A. `DeviceFingerprinter`
Generates a unique 64-character SHA-256 hash representing a user's device based on browser attributes (User-Agent, Screen Resolution, Timezone, Plugins, Canvas/WebGL hashes, and Fonts).
*   **Anomaly Detection**: It tracks how many unique users log in from a single fingerprint. If >5 users share a fingerprint, it flags a `MULTI_USER_DEVICE` anomaly (a strong indicator of a fraud ring or account takeover).
*   **Spoofing Detection**: It flags "Headless Browsers" (bots), Emulators, or missing fonts/plugins which indicate a script trying to evade detection.

### B. `GeoLocationEnricher`
Resolves an IP address to a physical location (City, Region, Lat/Lon) and an ISP.
*   **Heuristics**: Currently uses a deterministic mock based on MD5 hashing the IP to an Indian city. It checks for `.vpn.`, `.proxy.`, or `.tor.` in the IP string to flag anonymizers.
*   **Production Note**: This is a placeholder class designed to be swapped with MaxMind GeoIP2 or IPQualityScore API calls in a real production environment.

### C. `BehavioralBiometrics`
Analyzes *human* interaction patterns:
*   `typing_speed`: Detects bots (instant typing) or hijacked sessions (drastically different typing speeds).
*   `mouse_velocity`: Checks for zero movement (API-driven bot attacks).
*   `form_fill_time`: Flags instant form submissions.
*   `copy_paste_count`: Flags excessive copy-pasting (Credential Stuffing).

## 3. Core Logic / Workflow
These classes are instantiated as Singletons. When a pre-auth request arrives, the `PreAuthEngine` calls `score_device()` and `analyze_location()`. The outputs (risk scores and boolean flags like `is_vpn`) are then fed into the heuristic risk aggregation.

## 4. Assumptions & Limitations
*   **Limitation (State)**: Similar to the Pre-Auth engine, the device history and reputation scores are stored in Python dictionaries. This limits horizontal scaling and means device reputation is lost on server restart.
*   **Limitation (Data Collection)**: The `BehavioralBiometrics` class assumes that the frontend application (React/Next.js) is actively capturing DOM events (onKeyUp, onMouseMove) and bundling this telemetry into the API payload. If the frontend doesn't send it, this class gracefully defaults to 0 risk.

## 5. Role in Architecture
Provides the "Physical and Behavioral Context" to the Pre-Authorization engine. It answers the question: *"Is a real human holding a real phone making this transaction?"*
