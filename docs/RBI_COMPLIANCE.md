# 🏛️ RBI Compliance in ARGUS

ARGUS implements compliance with **RBI's Digital Payment Security Controls (2021)** and **NPCI UPI Guidelines**. This document details exactly what regulatory requirements are met and how they are implemented in code.

---

## 1️⃣ Transaction Limits (RBI/NPCI Mandated)

These are hard-coded in `backend/ml/fraud_model.py`:

```python
@dataclass
class IndiaThresholds:
    # Channel-specific limits (RBI/NPCI mandated)
    UPI_SINGLE_LIMIT: int = 100_000    # ₹1 Lakh UPI limit
    ATM_DAILY_LIMIT: int = 25_000      # ₹25K ATM withdrawal
    WALLET_LIMIT: int = 10_000         # ₹10K wallet limit
```

| Rule | RBI/NPCI Guideline | ARGUS Implementation |
|------|-------------------|---------------------|
| **UPI Limit** | Max ₹1 lakh per transaction (NPCI) | Flags transactions > ₹1,00,000 |
| **ATM Limit** | Max ₹25,000 per withdrawal | Flags ATM > ₹25,000 |
| **Wallet Limit** | Max ₹10,000 for PPIs (RBI) | Flags wallet > ₹10,000 |

**Code enforcement:**
```python
# R3: Channel limit violations
if channel == 'upi' and amount > THRESHOLDS.UPI_SINGLE_LIMIT:
    rules_triggered.append(f"UPI_LIMIT_EXCEEDED: ₹{amount:,.0f}")
    score += 0.5  # High risk
```

---

## 2️⃣ Velocity Controls (Anti-Money Laundering)

RBI requires monitoring of **rapid successive transactions** for AML compliance:

```python
# Velocity thresholds (per hour)
MAX_TXN_PER_HOUR: int = 15
MAX_AMOUNT_PER_HOUR: int = 200_000  # ₹2 lakh/hour
```

| Rule | Purpose | ARGUS Implementation |
|------|---------|---------------------|
| **15 txn/hour limit** | Prevents automated fraud/money laundering | Flags when exceeded |
| **₹2L/hour limit** | Prevents rapid fund extraction | Flags when exceeded |
| **Daily limit tracking** | Monitors cumulative daily spending | Per-user daily totals |

---

## 3️⃣ Time-Based Risk (RBI Fraud Guidelines)

RBI mandates **enhanced monitoring during high-risk hours**:

```python
# Time-based risk windows (IST)
HIGH_RISK_START: int = 23  # 11 PM
HIGH_RISK_END: int = 5     # 5 AM
```

**Why?** Most frauds occur at night when:
- Victims are asleep (can't notice)
- Bank customer service is unavailable
- Fraudsters have more time before detection

```python
# R5: Night time transactions
if (hour >= 23 or hour < 5):
    if amount > night_threshold:
        rules_triggered.append(f"NIGHT_HIGH_VALUE: {hour}:00 IST")
        score += 0.25
```

---

## 4️⃣ Device & Location Monitoring (RBI Digital Security 2021)

RBI requires **device binding** and **location tracking**:

| Requirement | RBI Guideline | ARGUS Implementation |
|-------------|---------------|---------------------|
| **New Device Detection** | "Alert on new device registration" | `is_new_device` flag |
| **Location Change** | "Monitor unusual location patterns" | `is_new_location` flag |
| **Combined Risk** | "Block new device + new location" | Score += 0.35 |

```python
# R7: New location + new device (account takeover pattern)
if txn.get('is_new_device') and txn.get('is_new_location'):
    rules_triggered.append("NEW_DEVICE_AND_LOCATION")
    score += 0.35  # Account takeover likely
```

---

## 5️⃣ UPI-Specific Fraud Detection (NPCI Guidelines)

Implemented in `backend/ml/upi_fraud_patterns.py`:

| RBI/NPCI Category | Fraud Type | Detection Method |
|-------------------|------------|------------------|
| **Category 1** | Digital Arrest Scams | Govt keyword detection in merchant/notes |
| **Category 2** | SIM Swap Attacks | New device + high value + location change |
| **Category 3** | Mule Accounts | Money-in-money-out pattern detection |
| **Category 4** | QR Code Fraud | Suspicious QR payment patterns |
| **Category 5** | UPI ID Phishing | Regex patterns for fake UPI IDs |

```python
class UPIFraudDetector:
    """
    Detects India-specific fraud patterns:
    1. Digital Arrest Scams
    2. SIM Swap Attacks  
    3. Mule Account Chains
    4. Merchant Impersonation
    5. QR Code Fraud
    6. UPI ID Phishing
    """
```

---

## 6️⃣ Explainable AI (RBI Audit Requirement)

**RBI Requirement:** "Banks must be able to explain WHY a transaction was blocked to customers and regulators"

Implemented in `backend/ml/explainable_ai.py`:

```python
explanation = {
    'decision': 'BLOCK',
    'headline': "🚫 Transaction BLOCKED - High transaction amount",
    'primary_reason': "₹75,000 exceeds user's typical ₹2,500",
    'contributing_factors': [
        "New device detected",
        "Night time transaction (2 AM)",
        "High-risk merchant category"
    ],
    'risk_breakdown': {...},
    'confidence': 0.87
}
```

| RBI Requirement | ARGUS Feature |
|-----------------|---------------|
| Audit trail | Every decision logged with reasons |
| Customer explanation | Human-readable `headline` and `primary_reason` |
| Regulatory reporting | `triggered_rules` list for compliance reports |

---

## 7️⃣ High-Risk Merchant Categories (RBI KYC Guidelines)

RBI mandates **enhanced due diligence** for certain merchant categories:

```python
# R8: High-risk categories
high_risk_categories = ['cryptocurrency', 'gambling', 'forex', 'jewellery']
if any(cat in category for cat in high_risk_categories):
    rules_triggered.append(f"HIGH_RISK_CATEGORY: {category}")
    score += 0.2
```

| Category | Risk Level | Reason |
|----------|------------|--------|
| Cryptocurrency | High | Unregulated, money laundering risk |
| Gambling | High | FEMA violations, addiction |
| Forex | High | Capital control violations |
| Jewellery | Medium-High | Common for money laundering |

---

## 8️⃣ Structuring Detection (PMLA Compliance)

**Prevention of Money Laundering Act** requires detecting **structuring** (breaking large amounts into smaller ones):

```python
# R9: Round amount (potential structuring)
if amount >= structuring_threshold and amount % 10000 == 0:
    rules_triggered.append(f"ROUND_AMOUNT: ₹{amount:,.0f}")
    score += 0.1
```

Pattern detected: Multiple ₹10,000, ₹25,000, ₹50,000 transactions = potential structuring

---

## 📋 Compliance Summary Table

| RBI/NPCI Requirement | ARGUS Feature | File |
|---------------------|---------------|------|
| UPI ₹1L limit | `UPI_SINGLE_LIMIT` | fraud_model.py |
| ATM ₹25K limit | `ATM_DAILY_LIMIT` | fraud_model.py |
| Wallet ₹10K limit | `WALLET_LIMIT` | fraud_model.py |
| Velocity monitoring | `MAX_TXN_PER_HOUR` | fraud_model.py |
| Night transaction flagging | `HIGH_RISK_START/END` | fraud_model.py |
| Device binding | `is_new_device` detection | fraud_model.py |
| Location monitoring | `is_new_location` detection | fraud_model.py |
| Digital arrest scam | `detect_digital_arrest_scam()` | upi_fraud_patterns.py |
| SIM swap detection | `detect_sim_swap_attack()` | upi_fraud_patterns.py |
| Mule account detection | `detect_mule_account()` | upi_fraud_patterns.py |
| Explainable decisions | `FraudExplainer` class | explainable_ai.py |
| Audit trails | `triggered_rules` in every response | fraud_model.py |
| Structuring detection | Round amount + velocity rules | fraud_model.py |

---

## 🎯 Key RBI Guidelines Referenced

1. **RBI Digital Payment Security Controls (2021)** - Device binding, location monitoring
2. **RBI Master Direction on Fraud Classification (2016)** - Fraud categorization
3. **NPCI UPI Procedural Guidelines** - Transaction limits, dispute resolution
4. **PMLA 2002** - Anti-money laundering, structuring detection
5. **RBI KYC Master Direction** - High-risk merchant categories

---

## 📚 References

- [RBI Digital Payment Security Controls](https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12032)
- [NPCI UPI Product Statistics](https://www.npci.org.in/what-we-do/upi/product-statistics)
- [RBI Annual Report - Fraud Statistics](https://rbi.org.in/Scripts/AnnualReportPublications.aspx)
- [Prevention of Money Laundering Act, 2002](https://legislative.gov.in/sites/default/files/A2003-15.pdf)
