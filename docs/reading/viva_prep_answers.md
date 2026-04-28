# ARGUS Viva Preparation: Deep Dive Answers

This document contains detailed answers to your most complex investigatory questions to ensure you are fully prepared to defend the architecture and decisions of the ARGUS project during your viva.

---

## 1. Have we actually implemented the Fraud Ring Detection (Networks)?
**Yes, but with prototype constraints.** 

If you look at `backend/ml/graph_fraud_detector.py`, the core algorithms *are* fully implemented. We are using the `networkx` library to build a Directed Graph (`nx.DiGraph`) in real-time. 
*   It successfully runs `nx.simple_cycles()` to detect A → B → C → A money laundering loops.
*   It analyzes `in_degree` and `out_degree` flow ratios to flag Mule Accounts.
*   It uses `nx.connected_components()` to find tightly knit fraud rings.

**The Catch (For the Viva):** 
Our implementation is entirely **in-memory**. Every time a transaction happens, it adds a node/edge to the RAM of the Python server. 
*   *Why we did this:* It is the only way to build a functional graph prototype in a weekend without forcing the judges/evaluators to install and configure a heavy external database.
*   *The Limitation:* If the server crashes, the graph is lost. Furthermore, `networkx` cannot handle millions of nodes in RAM. In a true enterprise environment, this exact logic would be ported to **Neo4j** (a dedicated Graph Database) using Cypher queries.

---

## 2. How the ML Models Work (Step-by-Step)

When a transaction enters the ML layer, here is exactly what happens mathematically:

1.  **XGBoost (The Heavy Lifter - 30% Weight)**: 
    *   *How it works:* It builds hundreds of "decision trees." It builds the first tree, sees where it made mistakes (residuals), and then builds the second tree *specifically* to fix the errors of the first tree. It repeats this 500 times (`n_estimators=500`).
    *   *Step-by-step:* It takes the 34 features (amount, distance, device age, etc.) and drops them down these 500 trees. The final leaf it lands in gives a probability score (0.0 to 1.0).
2.  **LightGBM (The Speedster - 25% Weight)**:
    *   *How it works:* Similar to XGBoost, but instead of growing trees level-by-level, it grows them "leaf-wise." It looks for the single leaf that will reduce the error the most and splits that one.
    *   *Step-by-step:* It processes categorical features incredibly fast, acting as a "second opinion" to XGBoost. If XGBoost says 80% fraud and LightGBM says 90%, the ensemble averages them based on their weights.
3.  **Isolation Forest (The Zero-Day Catcher - 15% Weight)**:
    *   *How it works:* It does NOT know what fraud looks like. It was trained exclusively on *normal* transactions. It draws random lines through the data space. 
    *   *Step-by-step:* Normal transactions are clustered tightly together in the center. A weird, brand-new fraud tactic will be far away from the center. Because it's far away, it takes very few random lines to "isolate" it. If it gets isolated quickly, the model flags it as an anomaly.
4.  **Dynamic Behavior Baseline (The Personal Touch - 15% Weight)**:
    *   *How it works:* Not ML, but statistics. It looks at the user's last 100 transactions and calculates their personal Average and Standard Deviation.
    *   *Step-by-step:* It calculates a **Z-Score**: `(Current Amount - Average Amount) / Standard Deviation`. If the Z-Score is > 3, it means this transaction is 3 standard deviations larger than this specific user's normal behavior, driving the risk score up.

---

## 3. What do the Database Files Do?

You will notice two main storage mechanisms in the backend:

1.  **`argus_data.db` (SQLite)**: 
    *   *What it is:* A standard relational database file. 
    *   *What it holds:* The `transactions` table. This is the **Immutable Ledger**. Every single transaction, along with its final risk score, the exact latency it took to process, and the block reason, is written here. It also holds the `fraud_cases` and `model_feedback` tables for the human analysts. 
    *   *Why:* Because banks require absolute auditability for compliance. If a user complains their card was blocked, the bank queries this DB to prove exactly why the AI blocked it.
2.  **`user_profiles.json` (File-based NoSQL Mock)**:
    *   *What it is:* A fast, flat JSON file holding user state.
    *   *What it holds:* The rolling history of amounts and timestamps for every user. 
    *   *Why:* The Dynamic Behavior model needs to instantly know a user's average spend over the last 30 days. Running a `SELECT AVG(amount) FROM transactions WHERE user_id = X` in SQLite takes too long (adding 10-20ms of latency). Keeping this in JSON allows the server to load it directly into ultra-fast RAM dictionaries, mimicking how Redis works in the real world.

---

## 4. The Tech Stack: Choices & Rejected Alternatives

| Technology | What it Does | Rejected Alternative | Why We Rejected It |
| :--- | :--- | :--- | :--- |
| **FastAPI** | Python Web Server. Handles incoming API requests and routes them to the ML models. | **Flask / Django** | Flask is synchronous and blocks when busy. Django is too heavy and slow. FastAPI uses `asyncio`, crucial for handling thousands of requests concurrently under 20ms. |
| **React + Vite** | The Frontend Dashboard UI. | **Angular / Plain HTML** | Angular is too complex for a rapid dashboard. Plain HTML/JS cannot handle the state management required for high-speed live WebSocket data streams. |
| **WebSockets** | Keeps a persistent connection open to push live transactions to the UI instantly. | **REST Polling** | Having the frontend ask the backend "Any new transactions?" every 1 second overloads the server and introduces massive latency. |
| **Tailwind CSS** | Styles the frontend using utility classes (e.g., `text-red-500`). | **Bootstrap** | Bootstrap looks generic and dated. Tailwind allowed us to build the premium "glassmorphism" Apple-like aesthetic required for a modern enterprise tool. |

---

## 5. The "No Budget / No Constraints" Ideal Tech Stack

If an interviewer asks you, "How would you scale this to handle 10,000 transactions per second globally?", here is the perfect architect answer:

1.  **Event Ingestion**: **Apache Kafka**. API gateways would dump raw payloads into Kafka. Kafka handles the immense throughput and guarantees no dropped transactions.
2.  **Core Server**: **Golang (Go)** or **Rust**. Python is too slow for the API layer at scale. Go provides microsecond latency.
3.  **ML Serving Layer**: **NVIDIA Triton Inference Server**. We would convert our XGBoost models to `ONNX` format and run them on GPUs/Triton. This bypasses Python's Global Interpreter Lock (GIL) completely.
4.  **In-Memory State (Velocity/Behavior)**: **Redis Cluster**. `user_profiles.json` would be replaced by Redis, allowing hundreds of API servers to read/write user behavioral baselines in sub-millisecond times.
5.  **Graph Database**: **Neo4j**. `networkx` would be completely replaced. Neo4j can traverse billions of nodes in milliseconds to find massive, global money-laundering rings.
6.  **Cold Storage / Audit**: **Snowflake** or **PostgreSQL**. SQLite is replaced by distributed relational databases for the immutable ledger.

---

## 6. Are there ONLY 3 Limitations?

No, `00_index.md` only highlights the top 3 easiest to digest for a general audience. If pushed by a highly technical examiner, you can list these additional systemic limitations:

1.  **Statefulness & Horizontal Scaling**: Because the `UserBehaviorProfile`s and `networkx` graphs are stored in local server RAM, you cannot easily spin up 5 copies of the FastAPI server behind a load balancer. Server A wouldn't know the graph data stored on Server B. (Fix: Centralize state in Redis/Neo4j).
2.  **Rule Engine Rigidity**: Currently, rules (like "block above ₹50,000") are hardcoded in Python dictionaries (`dataset_config.py`). In a real bank, analysts need a UI to change these rules dynamically without touching code. (Fix: Implement a Business Rules Management System like Drools).
3.  **Concept Drift Mitigation**: The ML models are statically trained `.joblib` files. They suffer from "Concept Drift" (scammers changing tactics over time). We implemented the `model_feedback` table, but the actual *retraining* of the model is currently a manual offline script execution. (Fix: MLOps pipeline using Airflow for automated continuous retraining).
