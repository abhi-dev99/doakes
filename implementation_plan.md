# Project ARGUS: Full Platform Overhaul

This plan addresses every issue raised — from the Isolation Forest scoring bug and broken filters, to a complete redesign of every view (Dashboard, Alerts, Profiles, Settings), branding, and the addition of fraud ring detection.

---

## Proposed Changes

### Phase 1: Critical ML Scoring Bug — Isolation Forest Always 100%

#### [MODIFY] [fraud_model.py](file:///d:/hackathob/fraud-detection-system/backend/ml/fraud_model.py)

**Root Cause:** Line 925 normalizes the Isolation Forest raw score with `(raw_score + 0.5) / 0.5`. For normal transactions, `score_samples()` returns values near 0 (which after negation gives ~0), but the formula `(0 + 0.5) / 0.5 = 1.0` — **every normal transaction maps to 100%**. The normalization formula is inverted.

**Fix:** Replace with proper normalization: `np.clip(raw_score, 0, 1)` using the standard sklearn convention where higher `decision_function` scores = more anomalous (after negation). The correct approach:
```python
raw_score = self.isolation_forest.decision_function(scaled)[0]
# decision_function: negative = anomaly, positive = normal
# Invert so that 1.0 = highly anomalous, 0.0 = normal
normalized = np.clip(-raw_score / 0.5, 0, 1)
```

This will finally give XGBoost and LightGBM room to express their scores rather than IsoForest dominating at 100%.

---

### Phase 2: Emoji Purge + Branding

#### [MODIFY] [main.py](file:///d:/hackathob/fraud-detection-system/backend/main.py)
- Remove ALL emoji characters (🚀, ✅, 📊, 💾, ▶️, ⏹️, 👋, 🟢, etc.) from every `logger.info()` / `logger.warning()` call.

#### [MODIFY] [fraud_model.py](file:///d:/hackathob/fraud-detection-system/backend/ml/fraud_model.py)
- Remove ALL emoji characters from logger calls.

#### [MODIFY] [Appv2.jsx](file:///d:/hackathob/fraud-detection-system/frontend/src/Appv2.jsx)
- **"Argus Secure" → "Project ARGUS"** in the sidebar header.
- Remove the `<Shield>` icon from the sidebar logo area. Replace with a clean text-only logotype.
- **Reduce sidebar width:** `w-64` → `w-56` (open), `w-20` → `w-16` (collapsed).

---

### Phase 3: Live Traffic Filters — Actually Working

#### [MODIFY] [Appv2.jsx](file:///d:/hackathob/fraud-detection-system/frontend/src/Appv2.jsx)

**Root Cause:** The `filteredTransactions` logic works, but the transaction list render at line 737 uses `transactions` instead of `filteredTransactions`. The filter buttons correctly mutate state, but the displayed list ignores them.

**Fix:** Change `transactions.slice(0, 100).map(...)` → `filteredTransactions.slice(0, 100).map(...)`.

---

### Phase 4: Transaction Inspector — Fill Empty Space

#### [MODIFY] [Appv2.jsx](file:///d:/hackathob/fraud-detection-system/frontend/src/Appv2.jsx)

Below the Z-Score and Risk Score in the Anomaly Vectors card, add:
- **Account Age** — derived from `user_profile.profile_age_days` (already available in backend).
- **Profile Maturity** — `mature` vs `building` (already sent in `behavior_analysis.profile_maturity`).
- **Transaction History Count** — `behavior_analysis.transactions_analyzed`.
- **User Avg Transaction** — `behavior_analysis.user_avg_amount`.

This requires the backend to pass these fields through the WebSocket (which it already does via `behavior_analysis`).

---

### Phase 5: Alerts Tab — Only HIGH/CRITICAL + Admin Actions

#### [MODIFY] [main.py](file:///d:/hackathob/fraud-detection-system/backend/main.py)

- Modify `get_recent_alerts()` to only return alerts where `risk_level IN ('HIGH', 'CRITICAL')`.
- Add a `user_id` and `triggered_rules` column to alerts table for richer context.
- Update `_save_transaction` to include triggered_rules in alert creation.

#### [MODIFY] [Appv2.jsx](file:///d:/hackathob/fraud-detection-system/frontend/src/Appv2.jsx)

Complete redesign of the Alerts view:
- **Filter tabs:** All / Pending / Confirmed / Dismissed.
- Each alert card shows: Transaction ID (clickable → opens inspector), User ID (clickable → profiles), Amount, Channel, Triggered Rules summary.
- **Admin action buttons:** "Confirm Fraud" (red), "Dismiss" (gray), "Escalate" (orange).
- Clicking actions calls `api.updateAlert()` and removes the card from the pending list with animation.
- Show a count badge on the Alerts sidebar icon for pending alerts.

---

### Phase 6: Profiles Tab — Real Data, Clickable, Useful

#### [MODIFY] [Appv2.jsx](file:///d:/hackathob/fraud-detection-system/frontend/src/Appv2.jsx)

**Root cause of "INSUFFICIENT MODEL DATA":** The frontend checks `p.models` but the backend returns profile data under `p.statistics` (see `get_user_profile_summary` at line 1117). The key mismatch means the conditional always falls through to the "Insufficient" state.

**Fix:**
- Map the backend's `statistics` field correctly.
- Show real data: avg amount, std dev, max amount, p95, txn count, profile age, maturity status.
- Add a **risk heatmap indicator** per profile based on their recent transaction deviation.
- Make each profile card clickable to expand into a detailed view showing transaction history stats and behavioral thresholds.
- Add a **search bar** to find users by ID.

---

### Phase 7: Dashboard — Outlier-Driven Command Center

#### [MODIFY] [Appv2.jsx](file:///d:/hackathob/fraud-detection-system/frontend/src/Appv2.jsx)

Complete redesign. The dashboard must answer: *"What needs my attention RIGHT NOW?"*

**New Layout:**
1. **Top Row: 4 KPI Cards** — Fraud Rate (with threshold indicator), Blocked Count (24h), Active Escalations (pending review), Avg Pipeline Latency (real, from stats).
2. **Middle Row (2 columns):**
   - **Left: Scoring Formula Explainer** — A visual breakdown of how the v4.0 ensemble score is calculated: `Score = XGB(30%) + LGB(25%) + IF(15%) + Rules(15%) + Dynamic(15%)`. Each component shown with its weight and a brief description. This is static educational content that adds value.
   - **Right: Risk Distribution** — Pie/donut chart showing LOW/MEDIUM/HIGH/CRITICAL distribution from `stats.risk_distribution`.
3. **Bottom Row:**
   - **Recent High-Risk Outliers** — Table of the 5 most recent HIGH/CRITICAL transactions. Each row is clickable to open the inspector. Shows: Txn ID, User, Amount, Score, Triggered Rules count.
   - **Volume Chart** — The existing kinetics chart, but using real latency from stats.

---

### Phase 8: Settings Tab — Real, Functional Configuration

#### [MODIFY] [Appv2.jsx](file:///d:/hackathob/fraud-detection-system/frontend/src/Appv2.jsx)

Replace the current placeholder settings with real, categorized sections:

1. **Engine Configuration:**
   - Ensemble weights (XGB/LGB/IF/Rules/Dynamic) — sliders, read-only display of current weights.
   - Risk thresholds: CRITICAL (0.55), HIGH (0.35), MEDIUM (0.18) — displayed, not editable yet.
   - Optimal threshold from training: displayed.

2. **Active Model Registry:**
   - Show the 4 actual models: XGBoost v4.0, LightGBM v4.0, Isolation Forest v4.0, Dynamic Behavior Engine.
   - Status: Loaded / Not loaded.
   - Feature count: 34.

3. **India Regulatory Limits (RBI/NPCI):**
   - UPI Single Txn Limit: ₹1,00,000
   - ATM Daily Limit: ₹25,000
   - Wallet Limit: ₹10,000
   - High Value Threshold: ₹50,000
   - Suspicious Value Threshold: ₹5,00,000

4. **User Behavior Engine:**
   - Active profiles count (from stats).
   - Mature profiles count.
   - Maturity threshold: 10 txns.
   - Z-Score anomaly threshold: 3.0σ.
   - Amount ratio threshold: 5.0x.

5. **System Info:**
   - Engine version: 4.0.0-india
   - Database path
   - Profile persistence: Enabled

---

### Phase 9: Fraud Ring Detection on Dashboard

#### [MODIFY] [Appv2.jsx](file:///d:/hackathob/fraud-detection-system/frontend/src/Appv2.jsx)
#### [MODIFY] [api.js](file:///d:/hackathob/fraud-detection-system/frontend/src/api.js)

The backend already has `GET /api/analytics/graph-stats` which returns fraud rings, mule accounts, and cyclic patterns (via `graph_fraud_detector.py`).

**Frontend integration:**
- Add a `getGraphStats()` method to `api.js`.
- On the Dashboard, add a **"Fraud Ring Intelligence"** card showing:
  - Number of detected rings
  - Number of mule accounts
  - Number of cyclic patterns
  - List of top rings with member counts
- If no data available (graph module not loaded), show a graceful "Graph analysis inactive" state.

---

## Verification Plan

### Automated Tests
1. Start backend, confirm no emoji in CLI output.
2. Start stream, open inspector, verify IsoForest scores are < 100% for normal transactions.
3. Click filter buttons, verify transaction list actually filters.
4. Check Alerts tab shows only HIGH/CRITICAL.
5. Check Profiles tab shows real statistics, not "INSUFFICIENT MODEL DATA".
6. Verify sidebar says "Project ARGUS" with no shield icon.

### Browser Verification
- Open dashboard and confirm outlier-driven layout with scoring formula.
- Open a transaction and verify Entity Context shows account age / profile maturity.
- Click a User ID in inspector → navigates to Profiles.
- Confirm Admin action buttons work on Alerts tab.
