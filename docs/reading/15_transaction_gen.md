# Documentation: `transaction_gen.py`

## 1. Purpose
The `TransactionGenerator` module acts as the lifeblood of the ARGUS platform during demonstrations, testing, and the viva. Because we cannot connect to a live Indian banking switch (like NPCI) for real data, this module synthesizes a mathematically realistic, endless stream of transactions to feed the Live Traffic dashboard.

## 2. Key Logic & Configuration

### A. Geography & User Pools
It maintains a hardcoded list of Indian Tier 1, 2, and 3 cities with realistic population/transaction weights (e.g., Mumbai 15%, Delhi 12%, Patna 2%). It initializes a static pool of 1,000 synthetic users and 500 synthetic devices. 

### B. Payment Channels (`CHANNELS`)
It strictly defines constraints for 6 payment channels to mimic reality:
*   **UPI** (55% weight): P2P, Groceries. Range: ₹1 - ₹100,000.
*   **POS** (15% weight): Retail stores. Range: ₹50 - ₹50,000.
*   **CARD_ONLINE** (12% weight): E-commerce. Range: ₹100 - ₹200,000.
*   **NETBANKING** (8% weight): High value EMI/Investments. Range: ₹500 - ₹1,000,000.
*   **WALLET** (5% weight): Gaming, Cab. Range: ₹1 - ₹10,000.
*   **ATM** (5% weight): *Exclusively* Cash Withdrawals. Must be in multiples of ₹100.

### C. Distribution Curves
Normal transactions use a **log-normal distribution** to generate amounts, skewing the vast majority of transactions toward lower values (₹100-₹500) while allowing occasional large values, perfectly mimicking real-world spending habits.

## 3. Fraud Generation (`_generate_fraud_transaction`)
It injects fraud at a default rate of 0.1%. When triggered, it selects from 5 distinct fraud archetypes:
1.  **Account Takeover**: Forces a completely new device ID, a new location thousands of km away from the user's home city, and multiplies the normal amount by 2x-5x. Often occurs at odd hours (2 AM).
2.  **Stolen Card**: Triggers high-value POS or E-commerce transactions consecutively.
3.  **Unusual Amount**: Pushes a transaction to the absolute upper limit of the channel.

## 4. Assumptions & Limitations
*   **Limitation (Scale)**: The user pool is limited to 1,000 users. While fine for a 100 TPS demo, analyzing graph fraud over long periods will result in unnaturally dense connections because the population is too small.
*   **Assumption**: Assumes a flat 0.1% fraud rate. In reality, fraud rates spike during holidays or massive data breaches.

## 5. Role in Architecture
Instantiated in `main.py`. The FastAPI WebSocket endpoint calls `generate_transaction()` continuously inside an `asyncio.sleep` loop, broadcasting the result to the ML Engine and the React frontend.
