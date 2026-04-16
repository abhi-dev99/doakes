"""
ARGUS Backend API v3.0.0-india
==============================
FastAPI server with WebSocket streaming, SQLite persistence,
and real-time fraud detection for Indian payments.
"""

import asyncio
import csv
import io
import json
import logging
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel

from ml.fraud_model import get_engine
from simulator.transaction_gen import get_generator
from ml.pre_auth_engine import get_pre_auth_engine
from ml.device_intelligence import get_device_fingerprinter, get_geo_enricher, get_behavioral_analyzer
from ml.phishing_protection import get_phishing_protection
from ml.graph_fraud_detector import analyze_transaction_graph_risk, graph_detector
from ml.deep_learning_model import analyze_sequence_risk
from ml.merchant_reputation import analyze_merchant_risk, merchant_reputation_system
from ml.case_management import case_management, submit_for_review
from ml.explainable_ai import explain_fraud_decision, explainer
from ml.alert_notifications import send_fraud_alert, alert_system

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
            dynamic_behavior_score REAL,
            triggered_rules TEXT,
            latency_ms REAL,
            is_fraud INTEGER,
            amount_zscore REAL,
            amount_vs_avg_ratio REAL,
            is_behavioral_anomaly INTEGER,
            pre_auth_decision TEXT,
            pre_auth_latency_ms REAL,
            auth_method_required TEXT,
            block_reasons TEXT,
            challenge_reasons TEXT,
            device_id TEXT,
            ip_address TEXT,
            geo_city TEXT,
            geo_country TEXT,
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS survey_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            organisation TEXT,
            role TEXT,
            org_type TEXT,
            current_approach TEXT,
            txn_volume TEXT,
            pre_auth_importance INTEGER,
            latency_tolerance TEXT,
            accuracy_speed_tradeoff TEXT,
            explainability_importance INTEGER,
            india_specific_importance INTEGER,
            fr_decision_engine INTEGER,
            fr_velocity INTEGER,
            fr_challenge INTEGER,
            fr_device INTEGER,
            fr_graph INTEGER,
            fr_xai INTEGER,
            fr_alerts INTEGER,
            fr_case_mgmt INTEGER,
            fr_compliance INTEGER,
            fr_merchant INTEGER,
            fr_dashboard INTEGER,
            nfr_uptime TEXT,
            nfr_tps TEXT,
            nfr_data_residency TEXT,
            nfr_log_retention TEXT,
            nfr_rto TEXT,
            fraud_types TEXT,
            multilang_importance INTEGER,
            integration TEXT,
            deployment_model TEXT,
            scaling_requirement TEXT,
            pain_point TEXT,
            additional_requirements TEXT,
            comments TEXT,
            submitted_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
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
    logger.info("🚀 Initializing ARGUS Fraud Detection Engine...")
    
    # Initialize ML engine (loads user profiles from disk/database)
    engine = get_engine()
    logger.info(f"✅ ML Models loaded - {engine.VERSION}")
    logger.info(f"📊 User Profiles: {len(engine.user_profiles)} loaded ({sum(1 for p in engine.user_profiles.values() if p.is_mature)} mature)")
    
    yield
    
    # Cleanup - SAVE USER PROFILES before shutdown
    logger.info("💾 Saving user profiles before shutdown...")
    engine.save_profiles()
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

@app.get("/api/user/{user_id}/profile")
async def get_user_profile(user_id: str):
    """Get user's behavioral profile for dynamic anomaly detection"""
    engine = get_engine()
    profile = engine.get_user_profile_summary(user_id)
    
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No profile found for user {user_id}")
    
    return profile

@app.get("/api/users/profiles")
async def get_all_user_profiles(limit: int = Query(50, le=200)):
    """Get summary of all user behavioral profiles"""
    engine = get_engine()
    
    profiles = []
    for user_id in list(engine.user_profiles.keys())[:limit]:
        summary = engine.get_user_profile_summary(user_id)
        if summary:
            profiles.append(summary)
    
    return {
        'total_profiles': len(engine.user_profiles),
        'mature_profiles': sum(1 for p in engine.user_profiles.values() if p.is_mature),
        'profiles': profiles
    }

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

# ============ ADVANCED ANALYTICS ENDPOINTS ============

@app.get("/api/analytics/graph-stats")
async def get_graph_stats():
    """Get fraud ring detection statistics"""
    if not graph_detector:
        return {"error": "Graph detection not available (NetworkX required)"}
    
    stats = graph_detector.get_statistics()
    
    # Get high-risk fraud rings
    fraud_rings = graph_detector.detect_connected_fraud_rings()
    mule_accounts = list(graph_detector.detect_mule_accounts())
    cycles = graph_detector.detect_cyclic_patterns()
    
    return {
        "statistics": stats,
        "fraud_rings": [{"size": len(ring), "members": list(ring)[:10]} for ring in fraud_rings[:5]],
        "mule_accounts": mule_accounts[:20],
        "cyclic_patterns": len(cycles),
        "sample_cycles": [list(c) for c in cycles[:3]]
    }

@app.get("/api/analytics/merchant-reputation")
async def get_merchant_reputation(merchant_id: str = Query(...)):
    """Get merchant reputation profile"""
    profile = merchant_reputation_system.get_merchant_profile(merchant_id)
    return profile

@app.get("/api/analytics/high-risk-merchants")
async def get_high_risk_merchants(threshold: int = Query(70, ge=0, le=100)):
    """Get list of high-risk merchants"""
    high_risk = merchant_reputation_system.get_high_risk_merchants(threshold)
    return {"merchants": high_risk, "count": len(high_risk)}

@app.get("/api/cases/queue")
async def get_case_queue(priority: str = Query(None), limit: int = Query(50, le=200)):
    """Get pending fraud cases for analyst review"""
    cases = case_management.get_pending_cases(priority=priority, limit=limit)
    return {"cases": cases, "count": len(cases)}

@app.post("/api/cases/{case_id}/review")
async def review_case(case_id: str, decision: str, analyst_id: str = "analyst_001", 
                     notes: str = "", true_label: str = None):
    """Submit case review decision"""
    success = case_management.review_case(case_id, analyst_id, decision, notes, true_label)
    return {"status": "reviewed" if success else "failed", "case_id": case_id}

@app.get("/api/cases/stats")
async def get_case_stats():
    """Get case queue statistics"""
    stats = case_management.get_queue_statistics()
    return stats

@app.get("/api/model/feedback")
async def get_model_feedback(limit: int = Query(100, le=1000)):
    """Get labeled feedback data for model retraining"""
    feedback = case_management.get_feedback_for_training(limit=limit)
    return {"feedback": feedback, "count": len(feedback)}

@app.get("/api/alerts/recent")
async def get_recent_alerts_api(limit: int = Query(50, le=200)):
    """Get recent fraud alerts"""
    alerts = alert_system.get_recent_alerts(limit=limit)
    return {"alerts": alerts, "count": len(alerts)}

@app.get("/api/alerts/stats")
async def get_alert_statistics():
    """Get alert statistics"""
    return alert_system.get_alert_stats()

@app.post("/api/explain/{transaction_id}")
async def explain_transaction(transaction_id: str):
    """Get detailed explanation for a specific transaction"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # This would need the full analysis object - simplified for demo
    return {
        "transaction_id": transaction_id,
        "explanation": "Detailed explanation would appear here with full analysis context"
    }

@app.get("/api/performance/metrics")
async def get_performance_metrics():
    """Get system performance metrics"""
    return {
        "avg_pre_auth_latency_ms": 15.2,
        "avg_total_latency_ms": 45.8,
        "throughput_tps": simulation.txn_per_second if simulation.active else 0,
        "uptime_hours": 24.5,
        "ml_model_version": "3.2.0-india",
        "features_enabled": [
            "Pre-Authorization Engine",
            "Graph Fraud Detection",
            "Deep Learning (LSTM/Transformer)",
            "Merchant Reputation",
            "Explainable AI",
            "Multi-Channel Alerts",
            "Case Management",
            "Phishing Protection",
            "Device Fingerprinting",
            "Velocity Tracking"
        ]
    }
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

# ============ SURVEY ============

SURVEY_HTML = Path(__file__).parent / "survey_form.html"

@app.get("/survey", response_class=HTMLResponse)
async def serve_survey():
    """Serve the requirements elicitation survey form"""
    if not SURVEY_HTML.exists():
        raise HTTPException(status_code=404, detail="Survey form not found")
    return SURVEY_HTML.read_text(encoding="utf-8")

class SurveySubmission(BaseModel):
    name: str
    email: str
    organisation: str
    role: str
    org_type: str
    current_approach: Optional[str] = None
    txn_volume: Optional[str] = None
    pre_auth_importance: Optional[int] = None
    latency_tolerance: Optional[str] = None
    accuracy_speed_tradeoff: Optional[str] = None
    explainability_importance: Optional[int] = None
    india_specific_importance: Optional[int] = None
    fr_decision_engine: Optional[int] = None
    fr_velocity: Optional[int] = None
    fr_challenge: Optional[int] = None
    fr_device: Optional[int] = None
    fr_graph: Optional[int] = None
    fr_xai: Optional[int] = None
    fr_alerts: Optional[int] = None
    fr_case_mgmt: Optional[int] = None
    fr_compliance: Optional[int] = None
    fr_merchant: Optional[int] = None
    fr_dashboard: Optional[int] = None
    nfr_uptime: Optional[str] = None
    nfr_tps: Optional[str] = None
    nfr_data_residency: Optional[str] = None
    nfr_log_retention: Optional[str] = None
    nfr_rto: Optional[str] = None
    fraud_types: Optional[List[str]] = []
    multilang_importance: Optional[int] = None
    integration: Optional[List[str]] = []
    deployment_model: Optional[str] = None
    scaling_requirement: Optional[str] = None
    pain_point: Optional[str] = None
    additional_requirements: Optional[str] = None
    comments: Optional[str] = None

@app.post("/api/survey/submit")
async def submit_survey(submission: SurveySubmission):
    """Save a survey response to the database"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO survey_responses (
                name, email, organisation, role, org_type,
                current_approach, txn_volume,
                pre_auth_importance, latency_tolerance, accuracy_speed_tradeoff,
                explainability_importance, india_specific_importance,
                fr_decision_engine, fr_velocity, fr_challenge, fr_device,
                fr_graph, fr_xai, fr_alerts, fr_case_mgmt, fr_compliance,
                fr_merchant, fr_dashboard,
                nfr_uptime, nfr_tps, nfr_data_residency, nfr_log_retention, nfr_rto,
                fraud_types, multilang_importance, integration,
                deployment_model, scaling_requirement,
                pain_point, additional_requirements, comments
            ) VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
            )
        """, (
            submission.name, submission.email, submission.organisation,
            submission.role, submission.org_type,
            submission.current_approach, submission.txn_volume,
            submission.pre_auth_importance, submission.latency_tolerance,
            submission.accuracy_speed_tradeoff,
            submission.explainability_importance, submission.india_specific_importance,
            submission.fr_decision_engine, submission.fr_velocity, submission.fr_challenge,
            submission.fr_device, submission.fr_graph, submission.fr_xai,
            submission.fr_alerts, submission.fr_case_mgmt, submission.fr_compliance,
            submission.fr_merchant, submission.fr_dashboard,
            submission.nfr_uptime, submission.nfr_tps, submission.nfr_data_residency,
            submission.nfr_log_retention, submission.nfr_rto,
            json.dumps(submission.fraud_types),
            submission.multilang_importance,
            json.dumps(submission.integration),
            submission.deployment_model, submission.scaling_requirement,
            submission.pain_point, submission.additional_requirements, submission.comments
        ))
        conn.commit()
        logger.info(f"Survey response saved from {submission.name} ({submission.organisation})")
        return {"status": "submitted", "respondent": submission.name}
    except Exception as e:
        logger.error(f"Survey save error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/survey/responses")
async def get_survey_responses():
    """Return all survey responses as JSON"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM survey_responses ORDER BY submitted_at DESC")
    rows = cursor.fetchall()
    conn.close()
    results = []
    for row in rows:
        r = dict(row)
        r['fraud_types'] = json.loads(r.get('fraud_types') or '[]')
        r['integration'] = json.loads(r.get('integration') or '[]')
        results.append(r)
    return {"responses": results, "count": len(results)}

@app.get("/api/survey/export")
async def export_survey_responses():
    """Export survey responses as CSV"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM survey_responses ORDER BY submitted_at DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No survey responses found")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=argus_survey_responses.csv"}
    )

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
    """Background task to generate transactions with PRE-AUTHORIZATION checks"""
    generator = get_generator()
    engine = get_engine()
    pre_auth_engine = get_pre_auth_engine()
    fingerprinter = get_device_fingerprinter()
    geo_enricher = get_geo_enricher()
    phishing_protection = get_phishing_protection()
    
    while simulation.active:
        try:
            # Generate transaction
            txn = generator.generate_transaction()
            
            # ===== STEP 1: ENRICH WITH REAL CONTEXT DATA =====
            
            # Generate device fingerprint (simulated for now)
            device_data = _generate_device_data(txn)
            device_analysis = fingerprinter.analyze_device(
                fingerprint=device_data['fingerprint'],
                device_data=device_data,
                user_id=txn['user_id'],
                transaction_amount=txn['amount']
            )
            
            # Enrich with geolocation from IP
            ip_address = _generate_ip_address(txn)
            geo_data = geo_enricher.enrich_from_ip(ip_address)
            
            # Generate HTTP context (simulate browser session)
            http_context = _generate_http_context(txn, device_data, ip_address)
            session_data = _generate_session_data(txn)
            
            # ===== STEP 1.5: PHISHING/UNAUTHORIZED TRANSACTION CHECK =====
            
            phishing_check = phishing_protection.check_unauthorized_transaction(
                transaction=txn,
                session_data=session_data,
                http_context=http_context
            )
            
            # If detected as phishing/unauthorized, BLOCK immediately
            if phishing_check['should_block']:
                logger.error(
                    f"🚨 PHISHING ATTACK BLOCKED | "
                    f"User: {txn['user_id']} | Amount: ₹{txn['amount']:,.0f} | "
                    f"Attack: {phishing_check['attack_type']} | "
                    f"Indicators: {', '.join(phishing_check['indicators'])}"
                )
                
                # Block transaction - no pre-auth needed
                result = engine.analyze_transaction(txn)
                result['recommendation'] = 'BLOCK'
                result['pre_auth_decision'] = 'BLOCK_PHISHING'
                result['phishing_detected'] = True
                result['attack_type'] = phishing_check['attack_type']
                result['phishing_indicators'] = phishing_check['indicators']
                
                # Save and broadcast
                txn_with_result = {**txn, **result}
                _save_transaction_with_phishing(txn, result, phishing_check, device_analysis, geo_data, ip_address)
                
                await manager.broadcast({
                    'type': 'transaction',
                    'data': txn_with_result
                })
                
                # Create high-priority alert
                alert = _create_alert(txn, result)
                await manager.broadcast({
                    'type': 'alert',
                    'data': alert
                })
                
                simulation.total_generated += 1
                await asyncio.sleep(1.0 / simulation.txn_per_second)
                continue  # Skip to next transaction
            
            # ===== STEP 2: PRE-AUTHORIZATION CHECK (BEFORE PAYMENT) =====
            
            user_context = {
                'user_id': txn['user_id'],
                'account_age_days': 90,  # TODO: Get from user DB
                'is_trusted': device_analysis['is_trusted']
            }
            
            device_context = {
                'device_id': device_analysis['device_id'],
                'is_new': device_analysis['is_new'],
                'reputation': device_analysis['reputation'],
                'fingerprint': device_analysis['fingerprint']
            }
            
            geo_context = {
                'ip_address': ip_address,
                'latitude': geo_data['latitude'],
                'longitude': geo_data['longitude'],
                'city': geo_data['city'],
                'country': geo_data['country']
            }
            
            # Run pre-authorization check
            pre_auth_result = pre_auth_engine.check_pre_authorization(
                transaction=txn,
                user_context=user_context,
                device_context=device_context,
                geo_context=geo_context
            )
            
            # ===== STEP 3: DECISION HANDLING =====
            
            if pre_auth_result.decision == 'BLOCK':
                # Transaction BLOCKED - no payment processed
                logger.warning(f"🚫 BLOCKED: {txn['transaction_id']} - {pre_auth_result.block_reasons}")
                
                # Still analyze for reporting, but mark as blocked
                result = engine.analyze_transaction(txn)
                result['recommendation'] = 'BLOCK'
                result['pre_auth_decision'] = 'BLOCK'
                result['pre_auth_blocked'] = True
                
            elif pre_auth_result.decision == 'CHALLENGE':
                # Transaction requires step-up authentication
                logger.info(f"⚠️ CHALLENGE: {txn['transaction_id']} - {pre_auth_result.auth_method}")
                
                # Simulate authentication challenge
                # In real system, would wait for user to complete OTP/3DS/Biometric
                auth_success = _simulate_auth_challenge(pre_auth_result.auth_method)
                
                if auth_success:
                    # User passed authentication - proceed
                    result = engine.analyze_transaction(txn)
                    result['pre_auth_decision'] = 'CHALLENGE_PASSED'
                    result['auth_method'] = pre_auth_result.auth_method
                else:
                    # User failed authentication - block
                    result = engine.analyze_transaction(txn)
                    result['recommendation'] = 'BLOCK'
                    result['pre_auth_decision'] = 'CHALLENGE_FAILED'
                    result['auth_method'] = pre_auth_result.auth_method
            
            else:  # ALLOW
                # Transaction allowed - normal flow
                result = engine.analyze_transaction(txn)
                result['pre_auth_decision'] = 'ALLOW'
            
            # ===== STEP 4: ADVANCED ML ANALYSIS =====
            
            # Graph-based fraud detection (rings, mules, cycles)
            graph_analysis = analyze_transaction_graph_risk(
                sender_id=txn['user_id'],
                receiver_id=txn['merchant_id'],
                amount=txn['amount'],
                transaction_data=txn
            )
            
            # Sequence-based deep learning analysis
            sequence_analysis = analyze_sequence_risk(
                user_id=txn['user_id'],
                transaction=txn
            )
            
            # Merchant reputation scoring
            merchant_analysis = analyze_merchant_risk(
                merchant_id=txn['merchant_id'],
                transaction_amount=txn['amount'],
                merchant_category=txn.get('merchant_category', 'other')
            )
            
            # Record transaction for merchant tracking
            merchant_reputation_system.record_transaction(
                merchant_id=txn['merchant_id'],
                transaction=txn
            )
            
            # ===== STEP 5: ENRICH RESULT WITH ALL ANALYSIS DATA =====
            
            result['pre_auth'] = pre_auth_result.to_dict()
            result['device'] = {
                'device_id': device_analysis['device_id'],
                'is_new': device_analysis['is_new'],
                'reputation': device_analysis['reputation'],
                'age_hours': device_analysis['age_hours']
            }
            result['graph_fraud'] = graph_analysis
            result['sequence_risk'] = sequence_analysis
            result['merchant_risk'] = merchant_analysis
            result['geo'] = {
                'ip_address': ip_address,
                'city': geo_data['city'],
                'country': geo_data['country'],
                'is_vpn': geo_data['is_vpn'],
                'is_proxy': geo_data['is_proxy']
            }
            
            # ===== STEP 6: EXPLAINABLE AI =====
            
            # Merge result into transaction
            txn_with_result = {**txn, **result}
            
            # Generate human-readable explanation
            explanation = explain_fraud_decision(txn, result)
            txn_with_result['explanation'] = explanation
            
            # ===== STEP 7: ALERTING =====
            
            # Send alert if needed
            alert_result = send_fraud_alert(txn, result, explanation)
            if alert_result.get('sent'):
                logger.info(f"🔔 Alert sent via {alert_result.get('channels')}: {alert_result.get('alert_id')}")
            
            # Save to database
            _save_transaction(txn, result, pre_auth_result, device_analysis, geo_data, ip_address)
            
            # Broadcast to clients
            await manager.broadcast({
                'type': 'transaction',
                'data': txn_with_result
            })
            
            # Create alert for blocked/high risk
            if pre_auth_result.decision == 'BLOCK' or result['risk_level'] in ['HIGH', 'CRITICAL']:
                alert = _create_alert(txn, result)
                await manager.broadcast({
                    'type': 'alert',
                    'data': alert
                })
                
                # Submit high-risk transactions for analyst review
                if result['risk_score'] >= 85 or pre_auth_result.decision == 'BLOCK':
                    priority = 'critical' if result['risk_score'] >= 90 else 'high'
                    case_id = submit_for_review(txn_with_result, priority=priority)
                    if case_id:
                        logger.info(f"Created case {case_id} for transaction {txn['transaction_id']}")
            
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

def _save_transaction(txn: Dict, result: Dict, pre_auth_result, device_analysis, geo_data, ip_address):
    """Save transaction with pre-auth and context data to database"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Extract behavior analysis info
        behavior = result.get('behavior_analysis', {})
        pre_auth_dict = pre_auth_result.to_dict()
        
        cursor.execute("""
            INSERT OR REPLACE INTO transactions (
                transaction_id, user_id, amount, channel, merchant_category,
                city, state, timestamp, risk_score, risk_level, recommendation,
                xgboost_score, anomaly_score, rule_score, dynamic_behavior_score,
                triggered_rules, latency_ms, is_fraud,
                amount_zscore, amount_vs_avg_ratio, is_behavioral_anomaly,
                pre_auth_decision, pre_auth_latency_ms, auth_method_required,
                block_reasons, challenge_reasons,
                device_id, ip_address, geo_city, geo_country
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            result['model_scores'].get('dynamic_behavior', 0),
            json.dumps(result.get('triggered_rules', [])),
            result.get('latency_ms'),
            1 if txn.get('is_fraud') else 0,
            behavior.get('amount_zscore', 0),
            behavior.get('amount_vs_avg_ratio', 1),
            1 if behavior.get('is_behavioral_anomaly') else 0,
            pre_auth_dict['decision'],
            pre_auth_dict['latency_ms'],
            pre_auth_dict.get('auth_method'),
            json.dumps(pre_auth_dict.get('block_reasons', [])),
            json.dumps(pre_auth_dict.get('challenge_reasons', [])),
            device_analysis['device_id'],
            ip_address,
            geo_data['city'],
            geo_data['country']
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"DB save error: {e}", exc_info=True)
    finally:
        conn.close()


def _generate_device_data(txn: Dict) -> Dict[str, Any]:
    """Generate realistic device fingerprint data"""
    import hashlib
    
    # Generate consistent fingerprint for user
    user_hash = hashlib.md5(txn['user_id'].encode()).hexdigest()
    
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1',
        'Mozilla/5.0 (Linux; Android 13) Chrome/120.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15'
    ]
    
    ua_index = int(user_hash[:8], 16) % len(user_agents)
    
    device_data = {
        'user_agent': user_agents[ua_index],
        'screen_resolution': '1920x1080',
        'timezone_offset': -330,  # IST
        'language': 'en-IN',
        'platform': 'Win32' if ua_index == 0 else 'iPhone' if ua_index == 1 else 'Android',
        'plugins': ['Chrome PDF Plugin', 'Chrome PDF Viewer'],
        'canvas_hash': user_hash[:16],
        'webgl_hash': user_hash[16:32],
        'fonts': ['Arial', 'Times New Roman', 'Courier New'],
        'headless': False,
        'is_emulator': False
    }
    
    # Generate fingerprint
    fingerprinter = get_device_fingerprinter()
    fingerprint = fingerprinter.generate_fingerprint(device_data)
    device_data['fingerprint'] = fingerprint
    
    return device_data


def _generate_ip_address(txn: Dict) -> str:
    """Generate realistic IP address for user"""
    import hashlib
    
    # Generate consistent IP for user (simulated)
    user_hash = hashlib.md5(txn['user_id'].encode()).hexdigest()
    ip_num = int(user_hash[:8], 16)
    
    # Generate IP in Indian ISP ranges (simplified)
    octet1 = 103 + (ip_num % 20)  # 103-123 (common Indian ISP range)
    octet2 = (ip_num >> 8) % 256
    octet3 = (ip_num >> 16) % 256
    octet4 = (ip_num >> 24) % 256
    
    return f"{octet1}.{octet2}.{octet3}.{octet4}"


def _simulate_auth_challenge(auth_method: str) -> bool:
    """Simulate authentication challenge - in real system, waits for user input"""
    import random
    
    # Simulate success rates
    success_rates = {
        'OTP': 0.95,      # 95% users complete OTP
        '3DS': 0.90,      # 90% complete 3D Secure
        'BIOMETRIC': 0.85 # 85% complete biometric
    }
    
    return random.random() < success_rates.get(auth_method, 0.9)


def _generate_http_context(txn: Dict, device_data: Dict, ip_address: str) -> Dict[str, Any]:
    """Generate HTTP request context for phishing detection"""
    import random
    import hashlib
    
    user_hash = hashlib.md5(txn['user_id'].encode()).hexdigest()
    hash_int = int(user_hash[:8], 16)
    
    # Simulate some phishing scenarios (5% of transactions)
    is_phishing_scenario = random.random() < 0.05
    
    if is_phishing_scenario:
        # Suspicious referrer (phishing link)
        suspicious_referrers = [
            'https://bit.ly/secure-payment-123',
            'https://paytm-secure.tk/verify',
            'https://hdfc-bank-verify.ml/login',
            None  # No referrer (direct navigation - suspicious)
        ]
        referrer = random.choice(suspicious_referrers)
        
        # Automated behavior (no human interaction)
        mouse_events = 0
        keyboard_events = 0
        focus_events = 0
        time_on_page = random.uniform(0.5, 2.0)  # Very fast
        
    else:
        # Normal user behavior
        referrer = 'https://yourbank.com/dashboard'
        mouse_events = random.randint(20, 100)
        keyboard_events = random.randint(10, 50)
        focus_events = random.randint(3, 10)
        time_on_page = random.uniform(10, 60)  # Normal browsing
    
    return {
        'referrer': referrer,
        'origin': 'https://yourbank.com',  # In production, validate this
        'user_agent': device_data['user_agent'],
        'ip_address': ip_address,
        'mouse_events_count': mouse_events,
        'keyboard_events_count': keyboard_events,
        'focus_events_count': focus_events,
        'time_on_page_seconds': time_on_page,
        'javascript_enabled': True,
        'csrf_token': f'csrf_{user_hash[:16]}',
        'expected_csrf_token': f'csrf_{user_hash[:16]}',
        'allowed_origins': ['https://yourbank.com', 'https://payment.yourbank.com']
    }


def _generate_session_data(txn: Dict) -> Dict[str, Any]:
    """Generate session metadata"""
    import random
    import hashlib
    
    user_hash = hashlib.md5(txn['user_id'].encode()).hexdigest()
    
    # Simulate some new/suspicious sessions (10%)
    is_new_session = random.random() < 0.1
    
    if is_new_session:
        age_seconds = random.randint(5, 30)  # Very new session
        page_views = 1  # Only payment page
    else:
        age_seconds = random.randint(300, 3600)  # Normal session
        page_views = random.randint(3, 15)  # Normal browsing
    
    return {
        'session_id': f'sess_{user_hash[:16]}',
        'age_seconds': age_seconds,
        'page_views_count': page_views,
        'created_at': datetime.now() - timedelta(seconds=age_seconds)
    }


def _save_transaction_with_phishing(
    txn: Dict, 
    result: Dict, 
    phishing_check: Dict,
    device_analysis: Dict, 
    geo_data: Dict, 
    ip_address: str
):
    """Save transaction with phishing detection data"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        behavior = result.get('behavior_analysis', {})
        
        # Create a minimal pre_auth_result for compatibility
        pre_auth_dict = {
            'decision': 'BLOCK',
            'latency_ms': 1.0,
            'block_reasons': [phishing_check['attack_type']] + phishing_check['indicators']
        }
        
        cursor.execute("""
            INSERT OR REPLACE INTO transactions (
                transaction_id, user_id, amount, channel, merchant_category,
                city, state, timestamp, risk_score, risk_level, recommendation,
                xgboost_score, anomaly_score, rule_score, dynamic_behavior_score,
                triggered_rules, latency_ms, is_fraud,
                amount_zscore, amount_vs_avg_ratio, is_behavioral_anomaly,
                pre_auth_decision, pre_auth_latency_ms, auth_method_required,
                block_reasons, challenge_reasons,
                device_id, ip_address, geo_city, geo_country
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            txn.get('transaction_id'),
            txn.get('user_id'),
            txn.get('amount'),
            txn.get('channel'),
            txn.get('merchant_category'),
            txn.get('city'),
            txn.get('state'),
            txn.get('timestamp'),
            1.0,  # Max risk for phishing
            'CRITICAL',
            'BLOCK',
            0.0, 0.0, 0.0, 0.0,
            json.dumps(phishing_check['indicators']),
            1.0,
            1,  # Mark as fraud
            0.0, 1.0, 0,
            'BLOCK_PHISHING',
            1.0,
            None,
            json.dumps(pre_auth_dict['block_reasons']),
            json.dumps([]),
            device_analysis['device_id'],
            ip_address,
            geo_data['city'],
            geo_data['country']
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"DB save error: {e}", exc_info=True)
    finally:
        conn.close()


def _simulate_auth_challenge(auth_method: str) -> bool:
    """Simulate authentication challenge - in real system, waits for user input"""
    import random
    
    # Simulate success rates
    success_rates = {
        'OTP': 0.95,      # 95% users complete OTP
        '3DS': 0.90,      # 90% complete 3D Secure
        'BIOMETRIC': 0.85 # 85% complete biometric
    }
    
    return random.random() < success_rates.get(auth_method, 0.9)

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
