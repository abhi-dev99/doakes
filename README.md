# ARGUS - AI Fraud Detection System 🛡️

Real-time fraud detection system for Indian payments powered by ML.

![ARGUS Dashboard](https://img.shields.io/badge/Version-3.0.0--india-cyan)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![React](https://img.shields.io/badge/React-18-61dafb)

## Features

### 🤖 ML Engine
- **XGBoost** - Primary fraud classifier
- **Isolation Forest** - Anomaly detection
- **Rule Engine** - RBI/NPCI compliant rules
- **Ensemble Scoring** - Weighted combination for accuracy

### 🇮🇳 India-Specific
- **UPI** - P2P transfers, QR payments (₹1 - ₹1L)
- **POS** - Card swipes at physical stores (₹50 - ₹50K)
- **Card Online** - E-commerce (₹100 - ₹2L)
- **NetBanking** - High value transfers, EMI (₹500 - ₹10L)
- **Wallet** - Small digital payments (₹1 - ₹10K)
- **ATM** - Cash withdrawals ONLY (₹100 - ₹25K, multiples of ₹100)

### 📊 Dashboard
- Real-time transaction streaming via WebSocket
- Dark/Light theme toggle
- Session vs Overall statistics
- Risk distribution charts
- Channel breakdown
- Alert management

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm

### Installation

```bash
# Clone
git clone <repo>
cd fraud-detection-system

# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Get statistics |
| GET | `/api/transactions` | List transactions |
| POST | `/api/analyze` | Analyze single transaction |
| GET | `/api/model/stats` | ML model info |
| POST | `/api/simulation/start` | Start simulation |
| POST | `/api/simulation/stop` | Stop simulation |
| WS | `/ws` | WebSocket stream |

## Transaction Logic

| Channel | Category | Amount Range |
|---------|----------|--------------|
| UPI | P2P, Grocery, Restaurant, Fuel, Bills | ₹1 - ₹1,00,000 |
| ATM | Cash Withdrawal ONLY | ₹100 - ₹25,000 |
| POS | Retail, Supermarket, Electronics | ₹50 - ₹50,000 |
| Card Online | E-commerce, Travel, Subscriptions | ₹100 - ₹2,00,000 |
| NetBanking | EMI, Insurance, Tax, Property | ₹500 - ₹10,00,000 |
| Wallet | Recharge, Food, Cab, Gaming | ₹1 - ₹10,000 |

## Risk Thresholds

- **CRITICAL** (≥55%): Block immediately
- **HIGH** (≥35%): Manual review required
- **MEDIUM** (≥18%): Flag for monitoring
- **LOW** (<18%): Approve

## Tech Stack

**Backend:**
- FastAPI
- SQLite
- XGBoost
- scikit-learn
- WebSockets

**Frontend:**
- React 18
- Vite
- Tailwind CSS
- Recharts
- Lucide Icons

## License

MIT
