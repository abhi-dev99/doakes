# Documentation: `main.py`

## 1. Purpose
This is the **Entry Point** of the ARGUS Backend. It is a FastAPI server that orchestrates all the individual ML models, databases, simulators, and REST/WebSocket endpoints. It ties the entire project together, acting as the bridge between the React frontend and the Python ML backend.

## 2. Core Architecture

### A. FastAPI Application
FastAPI was chosen specifically for its asynchronous I/O capabilities. Fraud detection requires processing thousands of requests per second while waiting for various DB/Cache lookups. Asynchronous endpoints ensure the server doesn't block while waiting.

### B. Database (SQLite)
On startup, it initializes `argus_data.db`. It maintains a `transactions` table that acts as the immutable ledger/audit trail for every decision the engine makes.
*   **Production Note**: As mentioned in the limitations, SQLite is a file-based lock system. `main.py` is structured so that swapping this out for PostgreSQL/SQLAlchemy in production would be trivial.

### C. The WebSocket Stream (`/ws`)
This is the most critical endpoint for the live dashboard.
1.  The React app connects to `ws://localhost:8000/ws`.
2.  An infinite `while True:` loop begins.
3.  Every X milliseconds (based on the `tps` parameter), it generates a synthetic transaction.
4.  It passes this transaction to `analyze_transaction()` in the `fraud_model.py` ensemble.
5.  It saves the result to SQLite.
6.  It broadcasts the enriched JSON payload back to the React app.

### D. REST API Endpoints
*   `POST /api/analyze`: The synchronous endpoint for integrating ARGUS into a real banking switch. You pass a JSON payload, it returns an ALLOW/BLOCK decision in <20ms.
*   `GET /api/config` & `POST /api/config`: Endpoints to get and update the dynamic ML weights (e.g., boosting XGBoost from 30% to 40%) or rule thresholds without restarting the server.
*   `GET /api/stats`: Serves the aggregated data (Total Volume, Block Rate, Fraud Ring count) for the top-level dashboard.

## 3. Assumptions & Limitations
*   **Limitation (Statefulness)**: The WebSocket connection holds state. If the server restarts or scales to multiple Uvicorn workers, WebSocket clients might lose sync or receive duplicate streams unless backed by a Pub/Sub system like Redis.
*   **Assumption**: The API assumes the incoming JSON payloads are perfectly formed. It uses Pydantic for basic validation but lacks deep data sanitization (which would be required in production to prevent injection attacks).

## 4. Role in Architecture
`main.py` *is* the application server. It is executed via `uvicorn backend.main:app` to start the entire system.
