"""
ARGUS Backend API v3.0.0-india
==============================
FastAPI server with WebSocket streaming, SQLite persistence,
and real-time fraud detection for Indian payments.
"""

import asyncio
import json
import logging
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ml.fraud_model import get_engine
from simulator.transaction_gen import get_generator

# ============ LOGGING ============

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ARGUS.API")

# ============ DATABASE ============

DB_PATH = Path(__file__).parent / "argus_data.db"

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE,
            user_id TEXT,
            amount REAL,
            channel TEXT,
            merchant_category TEXT,
            city TEXT,
            state TEXT,
            timestamp TEXT,
            risk_score REAL,
            risk_level TEXT,
            recommendation TEXT,
            xgboost_score REAL,
            anomaly_score REAL,
            rule_score REAL,
            triggered_rules TEXT,
            latency_ms REAL,
            is_fraud INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT,
            risk_level TEXT,
            amount REAL,
            channel TEXT,
            status TEXT DEFAULT 'pending',
            timestamp TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_txn_timestamp ON transactions(timestamp)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_txn_risk ON transactions(risk_level)
    ''')
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============ MODELS ============

class TransactionRequest(BaseModel):
    transaction_id: Optional[str] = None
    user_id: str
    amount: float
    channel: str
    merchant_category: str
    city: Optional[str] = "Mumbai"
    state: Optional[str] = "MH"
    timestamp: Optional[str] = None
    device_id: Optional[str] = None
    is_new_device: Optional[bool] = False
    is_new_location: Optional[bool] = False

class AlertAction(BaseModel):
    status: str  # 'confirmed', 'dismissed'

# ============ CONNECTION MANAGER ============

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# ============ SIMULATION STATE ============

class SimulationState:
    def __init__(self):
        self.active = False
        self.task: Optional[asyncio.Task] = None
        self.txn_per_second = 3
        self.total_generated = 0

simulation = SimulationState()

# ============ APP LIFECYCLE ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    init_db()
    logger.info("🚀 Initializing ARGUS Fraud Detection Engine v3.0.0-india...")
    
    # Initialize ML engine
    engine = get_engine()
    logger.info(f"✅ ML Models loaded - {engine.VERSION}")
    
    yield
    
    # Cleanup
    if simulation.active:
        simulation.active = False
        if simulation.task:
            simulation.task.cancel()
    logger.info("👋 ARGUS shutdown complete")

# ============ FASTAPI APP ============

app = FastAPI(
    title="ARGUS Fraud Detection API",
    description="Real-time AI fraud detection for Indian payments",
    version="3.0.0-india",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ STATS HELPERS ============

def get_stats() -> Dict[str, Any]:
    """Get current statistics from database"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM transactions")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE recommendation = 'BLOCK'")
    blocked = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE recommendation IN ('FLAG', 'REVIEW')")
    flagged = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE recommendation = 'APPROVE'")
    approved = cursor.fetchone()[0]
    
    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions")
    volume = cursor.fetchone()[0]
    
    cursor.execute("SELECT COALESCE(AVG(risk_score), 0) FROM transactions")
    avg_risk = cursor.fetchone()[0]
    
    cursor.execute("SELECT COALESCE(AVG(latency_ms), 5) FROM transactions")
    avg_latency = cursor.fetchone()[0]
    
    # Risk distribution
    cursor.execute("""
        SELECT risk_level, COUNT(*) 
        FROM transactions 
        GROUP BY risk_level
    """)
    risk_dist = dict(cursor.fetchall())
    
    conn.close()
    
    return {
        'total_transactions': total,
        'total_blocked': blocked,
        'total_flagged': flagged,
        'total_approved': approved,
        'total_volume': volume,
        'fraud_rate': (blocked / total * 100) if total > 0 else 0,
        'avg_risk_score': avg_risk,
        'avg_latency_ms': avg_latency,
        'risk_distribution': {
            'LOW': risk_dist.get('LOW', 0),
            'MEDIUM': risk_dist.get('MEDIUM', 0),
            'HIGH': risk_dist.get('HIGH', 0),
            'CRITICAL': risk_dist.get('CRITICAL', 0)
        }
    }

def get_recent_transactions(limit: int = 50) -> List[Dict]:
    """Get recent transactions"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT transaction_id, user_id, amount, channel, merchant_category,
               city, state, timestamp, risk_score, risk_level, recommendation,
               xgboost_score, anomaly_score, rule_score, triggered_rules, latency_ms
        FROM transactions
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    transactions = []
    for row in rows:
        txn = dict(row)
        txn['model_scores'] = {
            'xgboost': row['xgboost_score'],
            'anomaly_detection': row['anomaly_score'],
            'rule_engine': row['rule_score']
        }
        txn['triggered_rules'] = json.loads(row['triggered_rules'] or '[]')
        transactions.append(txn)
    
    return transactions

def get_recent_alerts(limit: int = 20) -> List[Dict]:
    """Get recent alerts"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, transaction_id, risk_level, amount, channel, status, timestamp
        FROM alerts
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

# ============ API ROUTES ============

@app.get("/")
async def root():
    return {
        "name": "ARGUS Fraud Detection API",
        "version": "3.0.0-india",
        "status": "operational",
        "market": "India",
        "channels": ["UPI", "POS", "CARD_ONLINE", "NETBANKING", "WALLET", "ATM"]
    }

@app.get("/api/stats")
async def api_stats():
    """Get current statistics"""
    return get_stats()

@app.get("/api/transactions")
async def api_transactions(
    limit: int = Query(50, le=200),
    risk_level: Optional[str] = None,
    channel: Optional[str] = None
):
    """Get recent transactions with optional filters"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT transaction_id, user_id, amount, channel, merchant_category,
               city, state, timestamp, risk_score, risk_level, recommendation,
               xgboost_score, anomaly_score, rule_score, triggered_rules, latency_ms
        FROM transactions WHERE 1=1
    """
    params = []
    
    if risk_level:
        query += " AND risk_level = ?"
        params.append(risk_level)
    if channel:
        query += " AND channel = ?"
        params.append(channel)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Transform to include model_scores object and parse triggered_rules
    transactions = []
    for row in rows:
        txn = dict(row)
        txn['model_scores'] = {
            'xgboost': row['xgboost_score'],
            'anomaly_detection': row['anomaly_score'],
            'rule_engine': row['rule_score']
        }
        txn['triggered_rules'] = json.loads(row['triggered_rules'] or '[]')
        transactions.append(txn)
    
    return transactions

@app.post("/api/analyze")
async def analyze_transaction(txn: TransactionRequest):
    """Analyze a single transaction"""
    engine = get_engine()
    
    txn_data = txn.dict()
    txn_data['transaction_id'] = txn_data.get('transaction_id') or str(uuid.uuid4())
    txn_data['timestamp'] = txn_data.get('timestamp') or datetime.now().isoformat()
    
    result = engine.analyze_transaction(txn_data)
    
    # Save to database
    _save_transaction(txn_data, result)
    
    # Broadcast if high risk
    if result['risk_level'] in ['HIGH', 'CRITICAL']:
        await manager.broadcast({
            'type': 'alert',
            'data': {
                'id': uuid.uuid4().hex[:8],
                'transaction_id': txn_data['transaction_id'],
                'risk_level': result['risk_level'],
                'amount': txn_data['amount'],
                'channel': txn_data['channel'],
                'status': 'pending',
                'timestamp': txn_data['timestamp']
            }
        })
    
    return {**txn_data, **result}

@app.get("/api/model/stats")
async def model_stats():
    """Get ML model statistics"""
    engine = get_engine()
    return engine.get_model_stats()

@app.get("/api/alerts")
async def api_alerts(limit: int = Query(20, le=100)):
    """Get recent alerts"""
    return get_recent_alerts(limit)

@app.put("/api/alerts/{alert_id}")
async def update_alert(alert_id: int, action: AlertAction):
    """Update alert status"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE alerts SET status = ? WHERE id = ?",
        (action.status, alert_id)
    )
    conn.commit()
    conn.close()
    
    return {"status": "updated", "alert_id": alert_id}

# ============ SIMULATION ENDPOINTS ============

@app.post("/api/simulation/start")
async def start_simulation(rate: int = Query(3, ge=1, le=20)):
    """Start transaction simulation"""
    if simulation.active:
        return {"status": "already_running"}
    
    simulation.active = True
    simulation.txn_per_second = rate
    simulation.task = asyncio.create_task(_run_simulation())
    
    logger.info(f"▶️ Simulation started at {rate} txn/sec")
    return {"status": "started", "rate": rate}

@app.post("/api/simulation/stop")
async def stop_simulation():
    """Stop transaction simulation"""
    simulation.active = False
    if simulation.task:
        simulation.task.cancel()
    
    logger.info("⏹️ Simulation stopped")
    return {"status": "stopped", "total_generated": simulation.total_generated}

@app.get("/api/simulation/status")
async def simulation_status():
    """Get simulation status"""
    return {
        "active": simulation.active,
        "rate": simulation.txn_per_second,
        "total_generated": simulation.total_generated
    }

# ============ EXPORT/IMPORT ============

@app.get("/api/export")
async def export_data(format: str = Query("csv")):
    """Export transactions as CSV"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT transaction_id, user_id, amount, channel, merchant_category,
               city, state, timestamp, risk_score, risk_level, recommendation
        FROM transactions
        ORDER BY created_at DESC
        LIMIT 1000
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    # Generate CSV
    import io
    output = io.StringIO()
    
    headers = ['transaction_id', 'user_id', 'amount', 'channel', 'merchant_category',
               'city', 'state', 'timestamp', 'risk_score', 'risk_level', 'recommendation']
    output.write(','.join(headers) + '\n')
    
    for row in rows:
        output.write(','.join(str(v) for v in row) + '\n')
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=argus_transactions.csv"}
    )

@app.delete("/api/data")
async def clear_data():
    """Clear all data (for testing)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM alerts")
    conn.commit()
    conn.close()
    
    simulation.total_generated = 0
    
    return {"status": "cleared"}

# ============ WEBSOCKET ============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        # Send initial data
        await websocket.send_json({
            'type': 'init',
            'data': {
                'stats': get_stats(),
                'recent_transactions': get_recent_transactions(30),
                'recent_alerts': get_recent_alerts(10)
            }
        })
        
        while True:
            # Keep connection alive, handle incoming messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # Handle ping/pong
                if data == 'ping':
                    await websocket.send_text('pong')
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({'type': 'heartbeat'})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# ============ SIMULATION TASK ============

async def _run_simulation():
    """Background task to generate transactions"""
    generator = get_generator()
    engine = get_engine()
    
    while simulation.active:
        try:
            # Generate transaction
            txn = generator.generate_transaction()
            
            # Analyze
            result = engine.analyze_transaction(txn)
            
            # Merge result into transaction
            txn_with_result = {**txn, **result}
            
            # Save to database
            _save_transaction(txn, result)
            
            # Broadcast to clients
            await manager.broadcast({
                'type': 'transaction',
                'data': txn_with_result
            })
            
            # Create alert for high risk
            if result['risk_level'] in ['HIGH', 'CRITICAL']:
                alert = _create_alert(txn, result)
                await manager.broadcast({
                    'type': 'alert',
                    'data': alert
                })
            
            # Update stats periodically
            simulation.total_generated += 1
            if simulation.total_generated % 10 == 0:
                await manager.broadcast({
                    'type': 'stats',
                    'data': get_stats()
                })
            
            # Rate limiting
            await asyncio.sleep(1.0 / simulation.txn_per_second)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Simulation error: {e}")
            await asyncio.sleep(1)

def _save_transaction(txn: Dict, result: Dict):
    """Save transaction to database"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO transactions (
                transaction_id, user_id, amount, channel, merchant_category,
                city, state, timestamp, risk_score, risk_level, recommendation,
                xgboost_score, anomaly_score, rule_score, triggered_rules, latency_ms, is_fraud
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            txn.get('transaction_id'),
            txn.get('user_id'),
            txn.get('amount'),
            txn.get('channel'),
            txn.get('merchant_category'),
            txn.get('city'),
            txn.get('state'),
            txn.get('timestamp'),
            result.get('risk_score'),
            result.get('risk_level'),
            result.get('recommendation'),
            result['model_scores'].get('xgboost'),
            result['model_scores'].get('anomaly_detection'),
            result['model_scores'].get('rule_engine'),
            json.dumps(result.get('triggered_rules', [])),
            result.get('latency_ms'),
            1 if txn.get('is_fraud') else 0
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"DB save error: {e}")
    finally:
        conn.close()

def _create_alert(txn: Dict, result: Dict) -> Dict:
    """Create and save alert"""
    alert = {
        'id': None,
        'transaction_id': txn.get('transaction_id'),
        'risk_level': result.get('risk_level'),
        'amount': txn.get('amount'),
        'channel': txn.get('channel'),
        'status': 'pending',
        'timestamp': txn.get('timestamp')
    }
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO alerts (transaction_id, risk_level, amount, channel, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            alert['transaction_id'],
            alert['risk_level'],
            alert['amount'],
            alert['channel'],
            alert['status'],
            alert['timestamp']
        ))
        conn.commit()
        alert['id'] = cursor.lastrowid
    except Exception as e:
        logger.error(f"Alert save error: {e}")
    finally:
        conn.close()
    
    return alert

# ============ RUN ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
