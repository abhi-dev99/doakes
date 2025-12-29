"""
Case Management and Analyst Review System
Queue management, fraud labeling, and model retraining pipeline
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from enum import Enum
import json
import sqlite3

logger = logging.getLogger("ARGUS.CaseManagement")


class CaseStatus(Enum):
    """Case review status"""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FRAUD_CONFIRMED = "fraud_confirmed"
    FALSE_POSITIVE = "false_positive"
    ESCALATED = "escalated"


class CasePriority(Enum):
    """Case priority levels"""
    CRITICAL = "critical"  # Blocked transactions, high amounts
    HIGH = "high"  # Challenged transactions
    MEDIUM = "medium"  # Flagged for review
    LOW = "low"  # Routine audits


class CaseManagementSystem:
    """Comprehensive case management and analyst workflow"""
    
    def __init__(self, db_path: str = "argus_data.db"):
        self.db_path = db_path
        self.case_queue = defaultdict(list)  # priority -> list of cases
        self.analyst_assignments = {}  # analyst_id -> list of case_ids
        self.feedback_data = []  # Feedback for model retraining
        
        self._initialize_database()
    
    def _initialize_database(self):
        """Create case management tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Cases table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fraud_cases (
                    case_id TEXT PRIMARY KEY,
                    transaction_id TEXT,
                    user_id TEXT,
                    amount REAL,
                    risk_score REAL,
                    block_reasons TEXT,
                    created_at TEXT,
                    status TEXT,
                    priority TEXT,
                    assigned_analyst TEXT,
                    reviewed_at TEXT,
                    review_notes TEXT,
                    final_decision TEXT,
                    true_label TEXT,
                    feedback_submitted INTEGER DEFAULT 0
                )
            """)
            
            # Analyst actions log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyst_actions (
                    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT,
                    analyst_id TEXT,
                    action_type TEXT,
                    timestamp TEXT,
                    notes TEXT,
                    FOREIGN KEY (case_id) REFERENCES fraud_cases(case_id)
                )
            """)
            
            # Model feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_feedback (
                    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT,
                    predicted_risk REAL,
                    true_label INTEGER,
                    features TEXT,
                    timestamp TEXT,
                    used_for_training INTEGER DEFAULT 0
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("Case management database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize case management DB: {e}")
    
    def create_case(self, transaction_data: Dict, priority: str = "medium") -> str:
        """Create a new fraud case for review"""
        case_id = f"CASE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{transaction_data.get('transaction_id', 'UNKNOWN')[:8]}"
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO fraud_cases (
                    case_id, transaction_id, user_id, amount, risk_score,
                    block_reasons, created_at, status, priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case_id,
                transaction_data.get('transaction_id'),
                transaction_data.get('user_id'),
                transaction_data.get('amount'),
                transaction_data.get('risk_score', 0),
                json.dumps(transaction_data.get('block_reasons', [])),
                datetime.now().isoformat(),
                CaseStatus.PENDING.value,
                priority
            ))
            
            conn.commit()
            conn.close()
            
            # Add to in-memory queue
            self.case_queue[priority].append({
                'case_id': case_id,
                'transaction_data': transaction_data,
                'created_at': datetime.now()
            })
            
            logger.info(f"Created case {case_id} with priority {priority}")
            return case_id
            
        except Exception as e:
            logger.error(f"Failed to create case: {e}")
            return None
    
    def assign_case(self, case_id: str, analyst_id: str) -> bool:
        """Assign a case to an analyst"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE fraud_cases 
                SET assigned_analyst = ?, status = ?
                WHERE case_id = ?
            """, (analyst_id, CaseStatus.UNDER_REVIEW.value, case_id))
            
            # Log action
            cursor.execute("""
                INSERT INTO analyst_actions (case_id, analyst_id, action_type, timestamp)
                VALUES (?, ?, ?, ?)
            """, (case_id, analyst_id, 'ASSIGNED', datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            # Update in-memory tracking
            if analyst_id not in self.analyst_assignments:
                self.analyst_assignments[analyst_id] = []
            self.analyst_assignments[analyst_id].append(case_id)
            
            logger.info(f"Assigned case {case_id} to analyst {analyst_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign case: {e}")
            return False
    
    def review_case(self, case_id: str, analyst_id: str, decision: str, 
                   notes: str = "", true_label: str = None) -> bool:
        """Submit case review decision"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update case
            cursor.execute("""
                UPDATE fraud_cases 
                SET status = ?, reviewed_at = ?, review_notes = ?, 
                    final_decision = ?, true_label = ?
                WHERE case_id = ?
            """, (
                decision, 
                datetime.now().isoformat(), 
                notes, 
                decision, 
                true_label,
                case_id
            ))
            
            # Log action
            cursor.execute("""
                INSERT INTO analyst_actions (case_id, analyst_id, action_type, timestamp, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (case_id, analyst_id, 'REVIEWED', datetime.now().isoformat(), notes))
            
            # If fraud confirmed/rejected, add to feedback
            if true_label:
                cursor.execute("""
                    SELECT transaction_id, risk_score FROM fraud_cases WHERE case_id = ?
                """, (case_id,))
                result = cursor.fetchone()
                
                if result:
                    transaction_id, risk_score = result
                    true_label_binary = 1 if true_label == 'fraud' else 0
                    
                    cursor.execute("""
                        INSERT INTO model_feedback (transaction_id, predicted_risk, true_label, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (transaction_id, risk_score, true_label_binary, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Case {case_id} reviewed by {analyst_id}: {decision}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to review case: {e}")
            return False
    
    def get_pending_cases(self, priority: str = None, limit: int = 50) -> List[Dict]:
        """Get pending cases for review"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if priority:
                cursor.execute("""
                    SELECT * FROM fraud_cases 
                    WHERE status = ? AND priority = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (CaseStatus.PENDING.value, priority, limit))
            else:
                cursor.execute("""
                    SELECT * FROM fraud_cases 
                    WHERE status = ?
                    ORDER BY 
                        CASE priority 
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                        END,
                        created_at DESC
                    LIMIT ?
                """, (CaseStatus.PENDING.value, limit))
            
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to get pending cases: {e}")
            return []
    
    def get_analyst_workload(self, analyst_id: str) -> Dict:
        """Get analyst's current workload"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Active cases
            cursor.execute("""
                SELECT COUNT(*) FROM fraud_cases 
                WHERE assigned_analyst = ? AND status IN (?, ?)
            """, (analyst_id, CaseStatus.PENDING.value, CaseStatus.UNDER_REVIEW.value))
            active_count = cursor.fetchone()[0]
            
            # Completed today
            today = datetime.now().date().isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM fraud_cases 
                WHERE assigned_analyst = ? AND DATE(reviewed_at) = ?
            """, (analyst_id, today))
            completed_today = cursor.fetchone()[0]
            
            # Total completed
            cursor.execute("""
                SELECT COUNT(*) FROM fraud_cases 
                WHERE assigned_analyst = ? AND status NOT IN (?, ?)
            """, (analyst_id, CaseStatus.PENDING.value, CaseStatus.UNDER_REVIEW.value))
            total_completed = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'analyst_id': analyst_id,
                'active_cases': active_count,
                'completed_today': completed_today,
                'total_completed': total_completed
            }
            
        except Exception as e:
            logger.error(f"Failed to get analyst workload: {e}")
            return {}
    
    def get_feedback_for_training(self, limit: int = 1000) -> List[Dict]:
        """Get labeled feedback data for model retraining"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM model_feedback 
                WHERE used_for_training = 0
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Mark as used
            if results:
                feedback_ids = [r['feedback_id'] for r in results]
                placeholders = ','.join(['?'] * len(feedback_ids))
                cursor.execute(f"""
                    UPDATE model_feedback 
                    SET used_for_training = 1
                    WHERE feedback_id IN ({placeholders})
                """, feedback_ids)
                conn.commit()
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to get feedback data: {e}")
            return []
    
    def get_queue_statistics(self) -> Dict:
        """Get overall queue statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            # Cases by status
            cursor.execute("""
                SELECT status, COUNT(*) FROM fraud_cases GROUP BY status
            """)
            stats['by_status'] = dict(cursor.fetchall())
            
            # Cases by priority
            cursor.execute("""
                SELECT priority, COUNT(*) FROM fraud_cases 
                WHERE status = ?
                GROUP BY priority
            """, (CaseStatus.PENDING.value,))
            stats['pending_by_priority'] = dict(cursor.fetchall())
            
            # Average review time
            cursor.execute("""
                SELECT AVG(
                    JULIANDAY(reviewed_at) - JULIANDAY(created_at)
                ) * 24 as avg_hours
                FROM fraud_cases 
                WHERE reviewed_at IS NOT NULL
            """)
            result = cursor.fetchone()
            stats['avg_review_time_hours'] = result[0] if result[0] else 0
            
            # Fraud confirmation rate
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN true_label = 'fraud' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) 
                FROM fraud_cases 
                WHERE true_label IS NOT NULL
            """)
            result = cursor.fetchone()
            stats['fraud_confirmation_rate'] = result[0] if result[0] else 0
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue statistics: {e}")
            return {}
    
    def escalate_case(self, case_id: str, reason: str) -> bool:
        """Escalate a case to senior analyst"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE fraud_cases 
                SET status = ?, priority = ?, review_notes = ?
                WHERE case_id = ?
            """, (CaseStatus.ESCALATED.value, CasePriority.CRITICAL.value, reason, case_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Case {case_id} escalated: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to escalate case: {e}")
            return False


# Global instance
case_management = CaseManagementSystem()


def submit_for_review(transaction_data: Dict, priority: str = "medium") -> str:
    """Wrapper to submit transaction for analyst review"""
    return case_management.create_case(transaction_data, priority)


def get_review_queue(limit: int = 50) -> List[Dict]:
    """Get pending review queue"""
    return case_management.get_pending_cases(limit=limit)
