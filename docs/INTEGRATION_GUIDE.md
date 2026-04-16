# 🔌 ARGUS Integration Guide

How to integrate ARGUS with real-world UPI apps, banking systems, or payment gateways.

---

## 1️⃣ Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PAYMENT FLOW WITH ARGUS                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Customer          UPI App/Bank           ARGUS API          Payment       │
│      │                  │                      │              Network       │
│      │                  │                      │              (NPCI)        │
│      │  1. Pay ₹5000    │                      │                │           │
│      │ ───────────────► │                      │                │           │
│      │                  │  2. /api/analyze     │                │           │
│      │                  │ ────────────────────►│                │           │
│      │                  │                      │                │           │
│      │                  │  3. {risk: LOW,      │                │           │
│      │                  │      allow: true}    │                │           │
│      │                  │ ◄────────────────────│                │           │
│      │                  │                      │                │           │
│      │                  │  4. Process Payment  │                │           │
│      │                  │ ──────────────────────────────────────►           │
│      │                  │                      │                │           │
│      │  5. Success ✓    │                      │                │           │
│      │ ◄─────────────── │                      │                │           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ Integration Methods

### **Method A: REST API Integration (Most Common)**

The payment app calls ARGUS before processing each transaction:

```python
# In your UPI app's payment service
import httpx

ARGUS_API = "https://argus.yourbank.com/api"

async def process_payment(transaction):
    # Step 1: Call ARGUS for risk assessment
    risk_response = await httpx.post(
        f"{ARGUS_API}/analyze",
        json={
            "transaction_id": transaction.id,
            "user_id": transaction.sender_upi,
            "amount": transaction.amount,
            "channel": "upi",
            "merchant_category": transaction.merchant_category,
            "city": transaction.location.city,
            "state": transaction.location.state,
            "device_id": transaction.device_fingerprint,
            "is_new_device": transaction.is_first_time_device,
            "is_new_location": transaction.is_new_city
        },
        timeout=0.05  # 50ms timeout (ARGUS responds in <10ms)
    )
    
    result = risk_response.json()
    
    # Step 2: Act on ARGUS recommendation
    if result["recommendation"] == "BLOCK":
        return PaymentResponse(
            status="DECLINED",
            reason=result["triggered_rules"][0],
            risk_score=result["risk_score"]
        )
    
    elif result["recommendation"] == "CHALLENGE":
        # Require additional authentication
        return PaymentResponse(
            status="PENDING_AUTH",
            auth_required="OTP",  # or biometric
            reason="Additional verification required"
        )
    
    else:  # APPROVE
        # Proceed with NPCI/payment network
        return await npci_gateway.process(transaction)
```

---

### **Method B: SDK Integration**

For tighter integration, embed ARGUS as a Python package:

```python
# Install: pip install argus-fraud-detection

from argus import FraudDetectionEngine

# Initialize once at app startup
fraud_engine = FraudDetectionEngine(
    model_path="/models/argus_v3.2",
    config={
        "market": "india",
        "channels": ["upi", "imps", "neft"],
        "latency_budget_ms": 10
    }
)

# In your payment handler
async def handle_upi_payment(request: UPIPaymentRequest):
    # Direct in-process call (fastest - ~2ms)
    risk_result = fraud_engine.analyze_transaction({
        "user_id": request.payer_vpa,
        "amount": request.amount,
        "channel": "upi",
        "merchant_category": request.mcc,
        "device_id": request.device_fingerprint,
        ...
    })
    
    if risk_result["risk_level"] == "CRITICAL":
        raise PaymentBlockedException(risk_result["triggered_rules"])
    
    # Continue with payment...
```

---

### **Method C: Kafka/Event Stream Integration**

For high-volume systems (millions of TPS), use async event streaming:

```python
# Producer (Payment App)
from kafka import KafkaProducer

producer = KafkaProducer(bootstrap_servers='kafka:9092')

async def submit_for_fraud_check(transaction):
    # Send to Kafka topic
    producer.send(
        'transactions.pending',
        key=transaction.id.encode(),
        value=json.dumps(transaction.to_dict()).encode()
    )
    
    # Wait for response on response topic
    response = await wait_for_response(
        topic='transactions.scored',
        key=transaction.id,
        timeout_ms=100
    )
    
    return response
```

```python
# Consumer (ARGUS Service)
from kafka import KafkaConsumer

consumer = KafkaConsumer('transactions.pending')
producer = KafkaProducer(bootstrap_servers='kafka:9092')

for message in consumer:
    transaction = json.loads(message.value)
    
    # Score transaction
    result = fraud_engine.analyze_transaction(transaction)
    
    # Send back result
    producer.send(
        'transactions.scored',
        key=message.key,
        value=json.dumps(result).encode()
    )
```

---

## 3️⃣ Integration Points in Payment Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                    WHERE ARGUS FITS IN UPI FLOW                        │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│  │  User    │    │  PSP     │    │  ARGUS   │    │  NPCI    │         │
│  │  (App)   │    │  Bank    │    │  Engine  │    │  Switch  │         │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘         │
│       │               │               │               │                │
│       │ 1. Initiate   │               │               │                │
│       │    Payment    │               │               │                │
│       │──────────────►│               │               │                │
│       │               │               │               │                │
│       │               │ 2. Pre-Auth   │               │                │
│       │               │    Check      │               │                │
│       │               │──────────────►│               │                │
│       │               │               │               │                │
│       │               │ 3. Risk Score │               │                │
│       │               │    + Decision │               │                │
│       │               │◄──────────────│               │                │
│       │               │               │               │                │
│       │               │ 4. If ALLOW,  │               │                │
│       │               │    Forward    │               │                │
│       │               │───────────────────────────────►                │
│       │               │               │               │                │
│       │               │ 5. Response   │               │                │
│       │               │◄───────────────────────────────                │
│       │               │               │               │                │
│       │ 6. Result     │               │               │                │
│       │◄──────────────│               │               │                │
│                                                                        │
│  ARGUS Decision Points:                                                │
│  ✓ PRE-AUTH (before NPCI) - Block fraudulent transactions             │
│  ✓ POST-AUTH (after NPCI) - Log for analysis, update profiles         │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4️⃣ API Contract for Integration

### Request Format
```json
POST /api/analyze
Content-Type: application/json

{
    "transaction_id": "TXN123456789",
    "user_id": "user@upi",
    "amount": 25000,
    "channel": "upi",
    "merchant_category": "electronics",
    "merchant_id": "MERCHANT123",
    "city": "Mumbai",
    "state": "MH",
    "timestamp": "2026-01-05T14:30:00+05:30",
    "device_id": "DEVICE_FINGERPRINT_HASH",
    "ip_address": "103.45.67.89",
    "is_new_device": false,
    "is_new_location": false
}
```

### Response Format
```json
{
    "risk_score": 0.23,
    "risk_level": "MEDIUM",
    "recommendation": "ALLOW",
    "model_scores": {
        "xgboost": 0.18,
        "anomaly_detection": 0.25,
        "rule_engine": 0.20,
        "dynamic_behavior": 0.35
    },
    "triggered_rules": [],
    "latency_ms": 4.2,
    "behavior_analysis": {
        "user_avg_amount": 5000,
        "amount_zscore": 1.2,
        "is_behavioral_anomaly": false,
        "profile_maturity": "mature"
    },
    "explanation": {
        "headline": "✅ Transaction Approved - Low risk detected",
        "primary_reason": "Transaction within normal patterns"
    }
}
```

---

## 5️⃣ Production Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                      LOAD BALANCER (AWS ALB)                    │   │
│   │                    argus-api.yourbank.com                       │   │
│   └───────────────────────────┬─────────────────────────────────────┘   │
│                               │                                         │
│           ┌───────────────────┼───────────────────┐                     │
│           │                   │                   │                     │
│           ▼                   ▼                   ▼                     │
│   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐            │
│   │  ARGUS Pod 1  │   │  ARGUS Pod 2  │   │  ARGUS Pod 3  │            │
│   │  (FastAPI)    │   │  (FastAPI)    │   │  (FastAPI)    │            │
│   │  + ML Models  │   │  + ML Models  │   │  + ML Models  │            │
│   └───────┬───────┘   └───────┬───────┘   └───────┬───────┘            │
│           │                   │                   │                     │
│           └───────────────────┼───────────────────┘                     │
│                               │                                         │
│                               ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                     REDIS CLUSTER                               │   │
│   │           (User profiles cache, rate limiting)                  │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                               │                                         │
│                               ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                   POSTGRESQL / TIMESCALEDB                      │   │
│   │           (Transaction logs, audit trails, analytics)           │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6️⃣ Code Changes for Production

### Current (Demo):
```python
# SQLite (single file)
DB_PATH = Path(__file__).parent / "argus_data.db"
```

### Production:
```python
# PostgreSQL with connection pooling
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")  # From secrets manager

pool = await asyncpg.create_pool(
    DATABASE_URL,
    min_size=10,
    max_size=100
)

# Redis for user profiles (faster than disk)
import redis
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"))

def get_user_profile(user_id: str) -> UserBehaviorProfile:
    # Check Redis first
    cached = redis_client.get(f"profile:{user_id}")
    if cached:
        return UserBehaviorProfile.from_json(cached)
    
    # Fall back to DB
    profile = db.fetch_profile(user_id)
    redis_client.setex(f"profile:{user_id}", 3600, profile.to_json())
    return profile
```

---

## 7️⃣ Integration Checklist

| Step | Task | Status |
|------|------|--------|
| 1 | Deploy ARGUS API behind load balancer | ⬜ |
| 2 | Set up PostgreSQL for transaction logs | ⬜ |
| 3 | Set up Redis for profile caching | ⬜ |
| 4 | Configure API authentication (JWT/API keys) | ⬜ |
| 5 | Add TLS/HTTPS encryption | ⬜ |
| 6 | Set up monitoring (Prometheus/Grafana) | ⬜ |
| 7 | Configure alerting (PagerDuty/Slack) | ⬜ |
| 8 | Integrate with payment app's pre-auth hook | ⬜ |
| 9 | Test with shadow traffic (log only, don't block) | ⬜ |
| 10 | Gradual rollout (1% → 10% → 100% traffic) | ⬜ |

---

## 8️⃣ Example: PhonePe/GPay Style Integration

```python
# Hypothetical PhonePe-style integration

class UPIPaymentService:
    def __init__(self):
        self.argus_client = ArgusClient(
            base_url="https://argus-internal.phonepe.com",
            api_key=os.getenv("ARGUS_API_KEY"),
            timeout_ms=50
        )
    
    async def send_money(self, request: SendMoneyRequest) -> PaymentResult:
        # 1. Build fraud check payload
        fraud_payload = {
            "user_id": request.sender_vpa,
            "amount": request.amount,
            "channel": "upi",
            "merchant_category": self._get_mcc(request.receiver_vpa),
            "device_id": request.device_fingerprint,
            "ip_address": request.client_ip,
            "city": request.location.city,
            "is_new_device": not self._is_known_device(request),
        }
        
        # 2. Call ARGUS (sub-10ms)
        try:
            risk = await self.argus_client.analyze(fraud_payload)
        except TimeoutError:
            # Fail-open: allow transaction if ARGUS is slow
            risk = {"recommendation": "ALLOW", "risk_level": "UNKNOWN"}
            self._alert_ops("ARGUS timeout")
        
        # 3. Apply decision
        if risk["recommendation"] == "BLOCK":
            # Log for compliance
            await self._log_blocked_transaction(request, risk)
            
            return PaymentResult(
                status=PaymentStatus.DECLINED,
                message="Transaction declined for security reasons",
                support_code=f"SEC-{risk['triggered_rules'][0][:10]}"
            )
        
        elif risk["recommendation"] == "CHALLENGE":
            # Trigger step-up authentication
            return PaymentResult(
                status=PaymentStatus.PENDING_VERIFICATION,
                verification_required=VerificationType.OTP,
                message="Please verify with OTP"
            )
        
        # 4. Proceed to NPCI
        npci_response = await self.npci_client.process_upi(request)
        
        # 5. Post-transaction: update ARGUS with outcome
        await self.argus_client.report_outcome(
            transaction_id=request.txn_id,
            final_status=npci_response.status,
            is_fraud=False  # Will be updated if customer reports fraud
        )
        
        return PaymentResult(
            status=PaymentStatus.SUCCESS,
            transaction_id=npci_response.rrn
        )
```

---

## 9️⃣ Security Considerations

| Concern | Solution |
|---------|----------|
| API Authentication | JWT tokens or API keys with rotation |
| Data in Transit | TLS 1.3 encryption |
| Data at Rest | AES-256 encryption for PII |
| Rate Limiting | Redis-based rate limiter (1000 req/sec per client) |
| DDoS Protection | AWS Shield / Cloudflare |
| Audit Logging | Immutable logs to S3/CloudWatch |

---

## 🔗 Related Documentation

- [RBI Compliance](./RBI_COMPLIANCE.md)
- [Future Roadmap](./FUTURE_SCOPE.md)
