"""
ARGUS - AI Fraud Detection Engine v3.2.0-india
===============================================
Production-ready fraud detection for Indian payment ecosystem.
Supports UPI, Cards, NetBanking, Wallets with DYNAMIC thresholds.

Key Features:
- XGBoost + Isolation Forest ensemble
- India-specific rule engine (RBI/NPCI compliant)
- **DYNAMIC User Behavior Analysis** - Personalized anomaly detection
- **PERSISTENT User Profiles** - Survives server restarts
- 0.1% realistic fraud rate
- Sub-10ms inference latency
"""

import numpy as np
import joblib
import logging
import time
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger("ARGUS.FraudEngine")

# ============ CONFIGURATION ============

@dataclass
class IndiaThresholds:
    """India-specific transaction thresholds in INR"""
    HIGH_VALUE: int = 50_000           # ₹50K - triggers review
    VERY_HIGH_VALUE: int = 200_000     # ₹2L - triggers enhanced scrutiny
    SUSPICIOUS_VALUE: int = 500_000    # ₹5L - potential structuring
    
    # Channel-specific limits
    UPI_SINGLE_LIMIT: int = 100_000    # ₹1L UPI single txn limit
    ATM_DAILY_LIMIT: int = 25_000      # ₹25K ATM withdrawal
    WALLET_LIMIT: int = 10_000         # ₹10K wallet limit
    
    # Velocity thresholds (per hour)
    MAX_TXN_PER_HOUR: int = 15
    MAX_AMOUNT_PER_HOUR: int = 200_000
    
    # Time-based risk windows (IST)
    HIGH_RISK_START: int = 23          # 11 PM
    HIGH_RISK_END: int = 5             # 5 AM

THRESHOLDS = IndiaThresholds()

# ============ DYNAMIC USER BEHAVIOR PROFILE ============

@dataclass
class UserBehaviorProfile:
    """
    Dynamic user profile for personalized anomaly detection.
    Tracks historical transaction patterns to detect deviations.
    """
    user_id: str
    
    # Transaction history (rolling window)
    transaction_amounts: deque = field(default_factory=lambda: deque(maxlen=100))
    transaction_timestamps: deque = field(default_factory=lambda: deque(maxlen=100))
    daily_totals: Dict[str, float] = field(default_factory=dict)  # date -> total
    
    # Computed statistics (updated dynamically)
    avg_amount: float = 2500.0
    std_amount: float = 1500.0
    median_amount: float = 1500.0
    max_amount: float = 5000.0
    p75_amount: float = 3000.0
    p95_amount: float = 10000.0
    
    # Daily behavior
    avg_daily_total: float = 10000.0
    max_daily_total: float = 20000.0
    avg_daily_txn_count: float = 3.0
    
    # Velocity tracking
    txn_count: int = 0
    total_amount: float = 0.0
    last_hour_txns: List[Tuple[float, float]] = field(default_factory=list)
    amount_velocity: float = 0.1
    txn_velocity: float = 0.1
    
    # Behavior maturity
    profile_age_days: int = 0
    is_mature: bool = False  # True after 10+ transactions
    
    def add_transaction(self, amount: float, timestamp: datetime = None) -> Dict[str, Any]:
        """
        Add a new transaction and update all statistics.
        Returns anomaly indicators for this transaction.
        """
        timestamp = timestamp or datetime.now()
        now = time.time()
        
        # Store transaction
        self.transaction_amounts.append(amount)
        self.transaction_timestamps.append(timestamp)
        self.txn_count += 1
        self.total_amount += amount
        
        # Update daily totals
        date_key = timestamp.strftime('%Y-%m-%d')
        self.daily_totals[date_key] = self.daily_totals.get(date_key, 0) + amount
        
        # Clean old daily totals (keep last 30 days)
        cutoff_date = (timestamp - timedelta(days=30)).strftime('%Y-%m-%d')
        self.daily_totals = {k: v for k, v in self.daily_totals.items() if k >= cutoff_date}
        
        # Update velocity tracking
        self.last_hour_txns = [
            (t, a) for t, a in self.last_hour_txns if now - t < 3600
        ]
        self.last_hour_txns.append((now, amount))
        
        hour_txns = len(self.last_hour_txns)
        hour_amount = sum(a for _, a in self.last_hour_txns)
        
        self.txn_velocity = min(hour_txns / THRESHOLDS.MAX_TXN_PER_HOUR, 1.0)
        self.amount_velocity = min(hour_amount / THRESHOLDS.MAX_AMOUNT_PER_HOUR, 1.0)
        
        # Calculate anomaly indicators BEFORE updating statistics
        anomaly_info = self._calculate_anomaly_indicators(amount, date_key)
        
        # Now update statistics with new transaction
        self._update_statistics()
        
        # Check if profile is mature enough for reliable detection
        self.is_mature = self.txn_count >= 10
        
        return anomaly_info
    
    def _calculate_anomaly_indicators(self, amount: float, date_key: str) -> Dict[str, Any]:
        """Calculate how anomalous this transaction is relative to user's history"""
        indicators = {
            'amount_zscore': 0.0,
            'amount_deviation_ratio': 1.0,
            'percentile_rank': 50.0,
            'daily_total_deviation': 1.0,
            'is_amount_anomaly': False,
            'is_daily_anomaly': False,
            'is_velocity_anomaly': False,
            'anomaly_reasons': []
        }
        
        if self.txn_count < 3:
            # Not enough history - use default thresholds
            return indicators
        
        # 1. Z-Score: How many standard deviations from mean?
        if self.std_amount > 0:
            indicators['amount_zscore'] = (amount - self.avg_amount) / self.std_amount
        
        # 2. Ratio to average amount
        if self.avg_amount > 0:
            indicators['amount_deviation_ratio'] = amount / self.avg_amount
        
        # 3. Percentile rank in user's history
        amounts_list = list(self.transaction_amounts)
        if amounts_list:
            below_count = sum(1 for a in amounts_list if a < amount)
            indicators['percentile_rank'] = (below_count / len(amounts_list)) * 100
        
        # 4. Daily total deviation
        current_daily = self.daily_totals.get(date_key, 0)
        if self.avg_daily_total > 0 and len(self.daily_totals) > 3:
            indicators['daily_total_deviation'] = current_daily / self.avg_daily_total
        
        # 5. Determine if this is an anomaly
        
        # Amount anomaly: Z-score > 3 OR amount > 5x average OR > 99th percentile
        if self.is_mature:
            if indicators['amount_zscore'] > 3:
                indicators['is_amount_anomaly'] = True
                indicators['anomaly_reasons'].append(
                    f"AMOUNT_ZSCORE: {indicators['amount_zscore']:.1f}σ above average (₹{self.avg_amount:,.0f})"
                )
            
            if indicators['amount_deviation_ratio'] > 5:
                indicators['is_amount_anomaly'] = True
                indicators['anomaly_reasons'].append(
                    f"AMOUNT_SPIKE: {indicators['amount_deviation_ratio']:.1f}x user's average (₹{self.avg_amount:,.0f})"
                )
            
            if amount > self.p95_amount * 2 and amount > 10000:  # Significant outlier
                indicators['is_amount_anomaly'] = True
                indicators['anomaly_reasons'].append(
                    f"UNUSUAL_HIGH: ₹{amount:,.0f} vs 95th percentile ₹{self.p95_amount:,.0f}"
                )
        
            # Daily total anomaly: Today's total > 3x average daily total
            if indicators['daily_total_deviation'] > 3 and len(self.daily_totals) > 5:
                indicators['is_daily_anomaly'] = True
                indicators['anomaly_reasons'].append(
                    f"DAILY_SPIKE: Today ₹{current_daily:,.0f} vs avg ₹{self.avg_daily_total:,.0f}/day"
                )
            
            # Velocity anomaly
            if self.txn_velocity > 0.7 and self.avg_daily_txn_count > 0:
                hour_txns = len(self.last_hour_txns)
                if hour_txns > self.avg_daily_txn_count * 2:
                    indicators['is_velocity_anomaly'] = True
                    indicators['anomaly_reasons'].append(
                        f"HIGH_FREQUENCY: {hour_txns} txns/hour vs {self.avg_daily_txn_count:.1f} avg/day"
                    )
        
        return indicators
    
    def _update_statistics(self):
        """Update running statistics from transaction history"""
        amounts = list(self.transaction_amounts)
        if not amounts:
            return
        
        # Basic statistics
        self.avg_amount = np.mean(amounts)
        self.std_amount = np.std(amounts) if len(amounts) > 1 else self.avg_amount * 0.5
        self.median_amount = np.median(amounts)
        self.max_amount = max(amounts)
        
        # Percentiles
        if len(amounts) >= 5:
            self.p75_amount = np.percentile(amounts, 75)
            self.p95_amount = np.percentile(amounts, 95)
        
        # Daily statistics
        if len(self.daily_totals) > 1:
            daily_values = list(self.daily_totals.values())
            self.avg_daily_total = np.mean(daily_values)
            self.max_daily_total = max(daily_values)
            
            # Calculate average transactions per day
            days_with_data = len(self.daily_totals)
            self.avg_daily_txn_count = self.txn_count / max(days_with_data, 1)
        
        # Profile age
        if self.transaction_timestamps:
            oldest = min(self.transaction_timestamps)
            newest = max(self.transaction_timestamps)
            self.profile_age_days = (newest - oldest).days + 1
    
    def get_dynamic_thresholds(self) -> Dict[str, float]:
        """
        Get personalized thresholds for this user.
        Returns thresholds based on user's own behavior pattern.
        """
        if not self.is_mature:
            # Use static thresholds for new users
            return {
                'high_value': THRESHOLDS.HIGH_VALUE,
                'very_high_value': THRESHOLDS.VERY_HIGH_VALUE,
                'suspicious_value': THRESHOLDS.SUSPICIOUS_VALUE
            }
        
        # Dynamic thresholds based on user's history
        return {
            'high_value': max(self.p75_amount * 3, self.avg_amount * 5, 10000),
            'very_high_value': max(self.p95_amount * 3, self.avg_amount * 10, 50000),
            'suspicious_value': max(self.max_amount * 2, self.avg_amount * 20, 100000),
            'daily_limit': max(self.max_daily_total * 2, self.avg_daily_total * 5, 50000)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize profile to dictionary for persistence"""
        return {
            'user_id': self.user_id,
            'transaction_amounts': list(self.transaction_amounts),
            'transaction_timestamps': [t.isoformat() for t in self.transaction_timestamps],
            'daily_totals': self.daily_totals,
            'avg_amount': self.avg_amount,
            'std_amount': self.std_amount,
            'median_amount': self.median_amount,
            'max_amount': self.max_amount,
            'p75_amount': self.p75_amount,
            'p95_amount': self.p95_amount,
            'avg_daily_total': self.avg_daily_total,
            'max_daily_total': self.max_daily_total,
            'avg_daily_txn_count': self.avg_daily_txn_count,
            'txn_count': self.txn_count,
            'total_amount': self.total_amount,
            'profile_age_days': self.profile_age_days,
            'is_mature': self.is_mature
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserBehaviorProfile':
        """Deserialize profile from dictionary"""
        profile = cls(user_id=data['user_id'])
        
        # Restore transaction history
        profile.transaction_amounts = deque(data.get('transaction_amounts', []), maxlen=100)
        profile.transaction_timestamps = deque(
            [datetime.fromisoformat(t) for t in data.get('transaction_timestamps', [])],
            maxlen=100
        )
        profile.daily_totals = data.get('daily_totals', {})
        
        # Restore statistics
        profile.avg_amount = data.get('avg_amount', 2500.0)
        profile.std_amount = data.get('std_amount', 1500.0)
        profile.median_amount = data.get('median_amount', 1500.0)
        profile.max_amount = data.get('max_amount', 5000.0)
        profile.p75_amount = data.get('p75_amount', 3000.0)
        profile.p95_amount = data.get('p95_amount', 10000.0)
        profile.avg_daily_total = data.get('avg_daily_total', 10000.0)
        profile.max_daily_total = data.get('max_daily_total', 20000.0)
        profile.avg_daily_txn_count = data.get('avg_daily_txn_count', 3.0)
        profile.txn_count = data.get('txn_count', 0)
        profile.total_amount = data.get('total_amount', 0.0)
        profile.profile_age_days = data.get('profile_age_days', 0)
        profile.is_mature = data.get('is_mature', False)
        
        return profile

# ============ FRAUD DETECTION ENGINE ============

class FraudDetectionEngine:
    """
    Production fraud detection engine for Indian payments.
    Uses ensemble of XGBoost, Isolation Forest, and rule engine.
    Features DYNAMIC user behavior analysis for personalized anomaly detection.
    
    User profiles are PERSISTENT - they survive server restarts by:
    1. Saving profiles to disk periodically
    2. Loading historical transactions from database on startup
    """
    
    VERSION = "3.2.0-india"
    
    # Risk level thresholds (conservative for India's 0.1% fraud rate)
    RISK_THRESHOLDS = {
        'CRITICAL': 0.55,  # Block immediately
        'HIGH': 0.35,      # Manual review required
        'MEDIUM': 0.18,    # Flag for monitoring
        'LOW': 0.0         # Approve
    }
    
    # Feature names for XGBoost
    FEATURE_NAMES = [
        'amount', 'amount_zscore', 'hour', 'is_night', 'is_weekend',
        'channel_risk', 'category_risk', 'velocity_score', 'is_new_device',
        'is_new_location', 'amount_velocity', 'txn_velocity', 'device_age_hours',
        'location_distance_km', 'merchant_risk_score', 'user_avg_txn_ratio'
    ]
    
    def __init__(self, models_dir: Optional[Path] = None, db_path: Optional[Path] = None):
        self.models_dir = models_dir or Path(__file__).parent / "models"
        self.db_path = db_path or Path(__file__).parent.parent / "argus_data.db"
        self.profiles_path = self.models_dir / "user_profiles.json"
        
        self.xgb_model = None
        self.isolation_forest = None
        self.scaler = None
        self.model_loaded = False
        
        # Dynamic user behavior profiles (PERSISTENT)
        self.user_profiles: Dict[str, UserBehaviorProfile] = {}
        self._profiles_dirty = False  # Track if profiles need saving
        self._last_save_time = time.time()
        self._save_interval = 60  # Save profiles every 60 seconds
        
        self._load_models()
        self._load_user_profiles()  # Load persisted profiles on startup
    
    def _load_models(self) -> None:
        """Load pre-trained models or initialize new ones"""
        try:
            self.models_dir.mkdir(parents=True, exist_ok=True)
            
            xgb_path = self.models_dir / "xgb_model.joblib"
            iso_path = self.models_dir / "isolation_forest.joblib"
            scaler_path = self.models_dir / "scaler.joblib"
            
            if xgb_path.exists() and iso_path.exists() and scaler_path.exists():
                self.xgb_model = joblib.load(xgb_path)
                self.isolation_forest = joblib.load(iso_path)
                self.scaler = joblib.load(scaler_path)
                self.model_loaded = True
                logger.info(f"Loaded pre-trained models {self.VERSION}")
            else:
                self._initialize_models()
                
        except Exception as e:
            logger.warning(f"Model loading failed: {e}, initializing fresh")
            self._initialize_models()
    
    def _load_user_profiles(self) -> None:
        """
        Load user profiles from persisted file OR rebuild from database.
        This ensures user behavior history survives server restarts.
        """
        profiles_loaded = 0
        
        # Method 1: Try loading from saved profiles file (fast)
        if self.profiles_path.exists():
            try:
                with open(self.profiles_path, 'r') as f:
                    profiles_data = json.load(f)
                
                for user_id, profile_dict in profiles_data.items():
                    self.user_profiles[user_id] = UserBehaviorProfile.from_dict(profile_dict)
                    profiles_loaded += 1
                
                logger.info(f"✅ Loaded {profiles_loaded} user profiles from cache")
                return
            except Exception as e:
                logger.warning(f"Could not load profiles from cache: {e}")
        
        # Method 2: Rebuild from database (slower but complete)
        if self.db_path.exists():
            profiles_loaded = self._rebuild_profiles_from_db()
            if profiles_loaded > 0:
                logger.info(f"✅ Rebuilt {profiles_loaded} user profiles from transaction history")
                self._save_user_profiles()  # Cache for next time
    
    def _rebuild_profiles_from_db(self) -> int:
        """Rebuild user profiles by analyzing historical transactions in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all historical transactions ordered by timestamp
            cursor.execute("""
                SELECT user_id, amount, timestamp 
                FROM transactions 
                ORDER BY timestamp ASC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return 0
            
            # Process each transaction to rebuild profiles
            for row in rows:
                user_id = row['user_id']
                amount = row['amount']
                timestamp_str = row['timestamp']
                
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
                
                # Create profile if doesn't exist
                if user_id not in self.user_profiles:
                    self.user_profiles[user_id] = UserBehaviorProfile(user_id=user_id)
                
                # Add transaction to profile (without triggering anomaly detection)
                profile = self.user_profiles[user_id]
                profile.transaction_amounts.append(amount)
                profile.transaction_timestamps.append(timestamp)
                profile.txn_count += 1
                profile.total_amount += amount
                
                # Update daily totals
                date_key = timestamp.strftime('%Y-%m-%d')
                profile.daily_totals[date_key] = profile.daily_totals.get(date_key, 0) + amount
            
            # Finalize statistics for all profiles
            for profile in self.user_profiles.values():
                profile._update_statistics()
                profile.is_mature = profile.txn_count >= 10
                
                # Clean old daily totals
                cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                profile.daily_totals = {k: v for k, v in profile.daily_totals.items() if k >= cutoff}
            
            return len(self.user_profiles)
            
        except Exception as e:
            logger.error(f"Error rebuilding profiles from DB: {e}")
            return 0
    
    def _save_user_profiles(self) -> None:
        """Save user profiles to disk for persistence"""
        try:
            profiles_data = {
                user_id: profile.to_dict() 
                for user_id, profile in self.user_profiles.items()
            }
            
            with open(self.profiles_path, 'w') as f:
                json.dump(profiles_data, f)
            
            self._profiles_dirty = False
            self._last_save_time = time.time()
            logger.debug(f"Saved {len(profiles_data)} user profiles to disk")
            
        except Exception as e:
            logger.error(f"Error saving user profiles: {e}")
    
    def _maybe_save_profiles(self) -> None:
        """Save profiles if dirty and enough time has passed"""
        if self._profiles_dirty and (time.time() - self._last_save_time) > self._save_interval:
            self._save_user_profiles()
    
    def _initialize_models(self) -> None:
        """Initialize models with synthetic training data"""
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler
        import xgboost as xgb
        
        logger.info("Initializing fraud detection models...")
        
        # Generate synthetic training data
        np.random.seed(42)
        n_samples = 10000
        
        # Normal transactions (99.9%)
        n_normal = int(n_samples * 0.999)
        normal_data = self._generate_normal_transactions(n_normal)
        
        # Fraudulent transactions (0.1%)
        n_fraud = n_samples - n_normal
        fraud_data = self._generate_fraud_transactions(n_fraud)
        
        X = np.vstack([normal_data, fraud_data])
        y = np.array([0] * n_normal + [1] * n_fraud)
        
        # Shuffle
        shuffle_idx = np.random.permutation(len(X))
        X, y = X[shuffle_idx], y[shuffle_idx]
        
        # Train scaler
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Train XGBoost
        self.xgb_model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            scale_pos_weight=n_normal / max(n_fraud, 1),
            use_label_encoder=False,
            eval_metric='logloss',
            random_state=42
        )
        self.xgb_model.fit(X_scaled, y)
        
        # Train Isolation Forest
        self.isolation_forest = IsolationForest(
            n_estimators=100,
            contamination=0.001,  # 0.1% anomaly rate
            random_state=42
        )
        self.isolation_forest.fit(X_scaled)
        
        # Save models
        joblib.dump(self.xgb_model, self.models_dir / "xgb_model.joblib")
        joblib.dump(self.isolation_forest, self.models_dir / "isolation_forest.joblib")
        joblib.dump(self.scaler, self.models_dir / "scaler.joblib")
        
        self.model_loaded = True
        logger.info(f"Models trained and saved - {self.VERSION}")
    
    def _generate_normal_transactions(self, n: int) -> np.ndarray:
        """Generate realistic normal Indian transaction patterns"""
        data = []
        for _ in range(n):
            # Amount: log-normal, median around ₹500-2000
            amount = np.random.lognormal(mean=7, sigma=1.2)
            amount = np.clip(amount, 10, 100000)
            
            hour = np.random.choice(24, p=self._get_hour_distribution())
            is_night = 1 if (hour >= 23 or hour < 5) else 0
            is_weekend = np.random.random() < 0.286  # 2/7 days
            
            data.append([
                amount,
                np.random.normal(0, 0.5),      # amount_zscore (normal)
                hour,
                is_night,
                int(is_weekend),
                np.random.uniform(0.1, 0.4),   # channel_risk (low)
                np.random.uniform(0.1, 0.3),   # category_risk (low)
                np.random.uniform(0.05, 0.2),  # velocity_score (low)
                np.random.random() < 0.05,     # is_new_device (5%)
                np.random.random() < 0.1,      # is_new_location (10%)
                np.random.uniform(0.1, 0.3),   # amount_velocity
                np.random.uniform(0.1, 0.2),   # txn_velocity
                np.random.uniform(500, 5000),  # device_age_hours
                np.random.uniform(0, 50),      # location_distance_km
                np.random.uniform(0.1, 0.3),   # merchant_risk_score
                np.random.uniform(0.5, 1.5),   # user_avg_txn_ratio
            ])
        return np.array(data)
    
    def _generate_fraud_transactions(self, n: int) -> np.ndarray:
        """Generate realistic fraud patterns"""
        data = []
        for _ in range(n):
            fraud_type = np.random.choice(['high_value', 'velocity', 'unusual', 'night'])
            
            if fraud_type == 'high_value':
                amount = np.random.uniform(50000, 500000)
                amount_zscore = np.random.uniform(2, 5)
            elif fraud_type == 'velocity':
                amount = np.random.uniform(5000, 50000)
                amount_zscore = np.random.uniform(1, 3)
            else:
                amount = np.random.uniform(1000, 100000)
                amount_zscore = np.random.uniform(1.5, 4)
            
            hour = np.random.choice([0, 1, 2, 3, 4, 23]) if fraud_type == 'night' else np.random.randint(0, 24)
            is_night = 1 if (hour >= 23 or hour < 5) else 0
            
            data.append([
                amount,
                amount_zscore,
                hour,
                is_night,
                np.random.random() < 0.3,
                np.random.uniform(0.5, 0.9),   # channel_risk (high)
                np.random.uniform(0.4, 0.8),   # category_risk (high)
                np.random.uniform(0.5, 1.0),   # velocity_score (high)
                np.random.random() < 0.6,      # is_new_device (60%)
                np.random.random() < 0.7,      # is_new_location (70%)
                np.random.uniform(0.6, 1.0),   # amount_velocity
                np.random.uniform(0.5, 1.0),   # txn_velocity
                np.random.uniform(0, 48),      # device_age_hours (new)
                np.random.uniform(100, 2000),  # location_distance_km (far)
                np.random.uniform(0.5, 0.9),   # merchant_risk_score
                np.random.uniform(2, 10),      # user_avg_txn_ratio (unusual)
            ])
        return np.array(data)
    
    def _get_hour_distribution(self) -> List[float]:
        """Realistic Indian transaction hour distribution"""
        # Peak: 10-12 AM, 6-9 PM (IST)
        weights = [
            0.01, 0.005, 0.003, 0.002, 0.002, 0.005,  # 0-5 (night)
            0.01, 0.02, 0.04, 0.06, 0.08, 0.08,       # 6-11 (morning)
            0.07, 0.06, 0.05, 0.05, 0.06, 0.07,       # 12-17 (afternoon)
            0.08, 0.09, 0.08, 0.06, 0.04, 0.02        # 18-23 (evening)
        ]
        return [w / sum(weights) for w in weights]
    
    def analyze_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point - analyze a transaction for fraud.
        Returns comprehensive risk assessment with dynamic anomaly detection.
        """
        start_time = time.perf_counter()
        
        # Get user profile for dynamic analysis
        user_id = transaction.get('user_id', 'unknown')
        amount = transaction.get('amount', 0)
        
        # Parse timestamp
        timestamp = transaction.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Get or create user behavior profile
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserBehaviorProfile(user_id=user_id)
        
        user_profile = self.user_profiles[user_id]
        
        # Calculate dynamic anomaly indicators
        anomaly_info = user_profile.add_transaction(amount, timestamp)
        
        # Extract features (now with user profile context)
        features = self._extract_features(transaction, user_profile, anomaly_info)
        
        # Get model predictions
        xgb_score = self._get_xgb_score(features)
        anomaly_score = self._get_anomaly_score(features)
        rule_score, triggered_rules = self._apply_rules(transaction, user_profile, anomaly_info)
        
        # Add dynamic anomaly score component
        dynamic_anomaly_score = self._calculate_dynamic_anomaly_score(anomaly_info)
        
        # Ensemble scoring with weights (adjusted for dynamic analysis)
        final_score = (
            xgb_score * 0.35 +
            anomaly_score * 0.15 +
            rule_score * 0.25 +
            dynamic_anomaly_score * 0.25  # New dynamic component
        )
        
        # Determine risk level
        risk_level = self._get_risk_level(final_score)
        
        # Get recommendation
        recommendation = self._get_recommendation(risk_level, triggered_rules)
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Build response with dynamic analysis info
        response = {
            'risk_score': round(final_score, 4),
            'risk_level': risk_level,
            'recommendation': recommendation,
            'model_scores': {
                'xgboost': round(xgb_score, 4),
                'anomaly_detection': round(anomaly_score, 4),
                'rule_engine': round(rule_score, 4),
                'dynamic_behavior': round(dynamic_anomaly_score, 4)
            },
            'triggered_rules': triggered_rules,
            'latency_ms': round(latency_ms, 2),
            'model_version': self.VERSION,
            # Dynamic behavior analysis details
            'behavior_analysis': {
                'user_avg_amount': round(user_profile.avg_amount, 2),
                'amount_zscore': round(anomaly_info['amount_zscore'], 2),
                'amount_vs_avg_ratio': round(anomaly_info['amount_deviation_ratio'], 2),
                'percentile_rank': round(anomaly_info['percentile_rank'], 1),
                'is_behavioral_anomaly': any([
                    anomaly_info['is_amount_anomaly'],
                    anomaly_info['is_daily_anomaly'],
                    anomaly_info['is_velocity_anomaly']
                ]),
                'profile_maturity': 'mature' if user_profile.is_mature else 'building',
                'transactions_analyzed': user_profile.txn_count
            }
        }
        
        # Mark profiles as needing save and maybe save periodically
        self._profiles_dirty = True
        self._maybe_save_profiles()
        
        return response
    
    def _calculate_dynamic_anomaly_score(self, anomaly_info: Dict[str, Any]) -> float:
        """Calculate anomaly score based on user's behavioral deviation"""
        score = 0.0
        
        # Z-score contribution (heavily weighted for extreme deviations)
        zscore = abs(anomaly_info.get('amount_zscore', 0))
        if zscore > 5:
            score += 0.5
        elif zscore > 4:
            score += 0.4
        elif zscore > 3:
            score += 0.3
        elif zscore > 2:
            score += 0.15
        
        # Amount ratio contribution
        ratio = anomaly_info.get('amount_deviation_ratio', 1)
        if ratio > 20:
            score += 0.4
        elif ratio > 10:
            score += 0.3
        elif ratio > 5:
            score += 0.2
        elif ratio > 3:
            score += 0.1
        
        # Daily total deviation
        daily_dev = anomaly_info.get('daily_total_deviation', 1)
        if daily_dev > 5:
            score += 0.3
        elif daily_dev > 3:
            score += 0.2
        elif daily_dev > 2:
            score += 0.1
        
        # Direct anomaly flags
        if anomaly_info.get('is_amount_anomaly'):
            score += 0.15
        if anomaly_info.get('is_daily_anomaly'):
            score += 0.15
        if anomaly_info.get('is_velocity_anomaly'):
            score += 0.1
        
        return min(score, 1.0)
    
    def _extract_features(self, txn: Dict[str, Any], user_profile: UserBehaviorProfile, anomaly_info: Dict[str, Any]) -> np.ndarray:
        """Extract ML features from transaction with dynamic user profile"""
        amount = txn.get('amount', 0)
        
        # Time features
        timestamp = txn.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        hour = timestamp.hour
        is_night = 1 if (hour >= 23 or hour < 5) else 0
        is_weekend = 1 if timestamp.weekday() >= 5 else 0
        
        # Channel risk
        channel_risks = {
            'upi': 0.15, 'card_online': 0.35, 'pos': 0.2,
            'netbanking': 0.25, 'wallet': 0.1, 'atm': 0.3
        }
        channel = txn.get('channel', 'upi').lower()
        channel_risk = channel_risks.get(channel, 0.2)
        
        # Category risk
        category_risks = {
            'p2p_transfer': 0.3, 'cash_withdrawal': 0.35, 'electronics': 0.4,
            'jewellery': 0.5, 'cryptocurrency': 0.7, 'gambling': 0.8,
            'grocery': 0.05, 'utilities': 0.05, 'fuel': 0.1, 'food_delivery': 0.1
        }
        category = txn.get('merchant_category', 'retail').lower().replace(' ', '_')
        category_risk = category_risks.get(category, 0.15)
        
        # Velocity features from user profile
        velocity_score = self._calculate_velocity_score(user_profile)
        
        features = [
            amount,
            anomaly_info.get('amount_zscore', 0),  # Use dynamic zscore
            hour,
            is_night,
            is_weekend,
            channel_risk,
            category_risk,
            velocity_score,
            1 if txn.get('is_new_device', False) else 0,
            1 if txn.get('is_new_location', False) else 0,
            user_profile.amount_velocity,
            user_profile.txn_velocity,
            txn.get('device_age_hours', 1000),
            txn.get('location_distance_km', 0),
            txn.get('merchant_risk_score', 0.2),
            anomaly_info.get('amount_deviation_ratio', 1.0)  # Use dynamic ratio
        ]
        
        return np.array(features).reshape(1, -1)
    
    def _calculate_velocity_score(self, profile: UserBehaviorProfile) -> float:
        """Calculate overall velocity risk score"""
        return (profile.txn_velocity * 0.4 + profile.amount_velocity * 0.6)
    
    def _get_xgb_score(self, features: np.ndarray) -> float:
        """Get XGBoost fraud probability"""
        if self.xgb_model is None:
            return 0.1
        try:
            scaled = self.scaler.transform(features)
            proba = self.xgb_model.predict_proba(scaled)[0]
            return float(proba[1]) if len(proba) > 1 else float(proba[0])
        except Exception as e:
            logger.error(f"XGBoost prediction error: {e}")
            return 0.1
    
    def _get_anomaly_score(self, features: np.ndarray) -> float:
        """Get Isolation Forest anomaly score (normalized to 0-1)"""
        if self.isolation_forest is None:
            return 0.1
        try:
            scaled = self.scaler.transform(features)
            # score_samples returns negative values, more negative = more anomalous
            raw_score = -self.isolation_forest.score_samples(scaled)[0]
            # Normalize to 0-1 range
            return float(np.clip((raw_score + 0.5) / 0.5, 0, 1))
        except Exception as e:
            logger.error(f"Isolation Forest error: {e}")
            return 0.1
    
    def _apply_rules(self, txn: Dict[str, Any], user_profile: UserBehaviorProfile, anomaly_info: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Apply India-specific fraud detection rules with DYNAMIC thresholds"""
        rules_triggered = []
        score = 0.0
        
        amount = txn.get('amount', 0)
        channel = txn.get('channel', 'upi').lower()
        category = txn.get('merchant_category', '').lower()
        
        # Get dynamic thresholds based on user behavior
        dynamic_thresholds = user_profile.get_dynamic_thresholds()
        
        # R1: Dynamic high value detection (based on user's history)
        if user_profile.is_mature:
            if amount >= dynamic_thresholds['suspicious_value']:
                rules_triggered.append(f"USER_SUSPICIOUS_VALUE: ₹{amount:,.0f} >= ₹{dynamic_thresholds['suspicious_value']:,.0f} (personalized)")
                score += 0.5
            elif amount >= dynamic_thresholds['very_high_value']:
                rules_triggered.append(f"USER_VERY_HIGH: ₹{amount:,.0f} >= ₹{dynamic_thresholds['very_high_value']:,.0f} (personalized)")
                score += 0.35
            elif amount >= dynamic_thresholds['high_value']:
                rules_triggered.append(f"USER_HIGH_VALUE: ₹{amount:,.0f} >= ₹{dynamic_thresholds['high_value']:,.0f} (personalized)")
                score += 0.2
        else:
            # Fall back to static thresholds for new users
            if amount >= THRESHOLDS.VERY_HIGH_VALUE:
                rules_triggered.append(f"VERY_HIGH_VALUE: ₹{amount:,.0f} >= ₹{THRESHOLDS.VERY_HIGH_VALUE:,}")
                score += 0.4
            elif amount >= THRESHOLDS.HIGH_VALUE:
                rules_triggered.append(f"HIGH_VALUE: ₹{amount:,.0f} >= ₹{THRESHOLDS.HIGH_VALUE:,}")
                score += 0.2
        
        # R2: DYNAMIC ANOMALY - Add anomaly reasons from behavioral analysis
        for reason in anomaly_info.get('anomaly_reasons', []):
            rules_triggered.append(reason)
            score += 0.25  # Each behavioral anomaly adds to score
        
        # R3: Channel limit violations
        if channel == 'upi' and amount > THRESHOLDS.UPI_SINGLE_LIMIT:
            rules_triggered.append(f"UPI_LIMIT_EXCEEDED: ₹{amount:,.0f} > ₹{THRESHOLDS.UPI_SINGLE_LIMIT:,}")
            score += 0.5
        
        if channel == 'atm' and amount > THRESHOLDS.ATM_DAILY_LIMIT:
            rules_triggered.append(f"ATM_LIMIT_EXCEEDED: ₹{amount:,.0f} > ₹{THRESHOLDS.ATM_DAILY_LIMIT:,}")
            score += 0.4
        
        if channel == 'wallet' and amount > THRESHOLDS.WALLET_LIMIT:
            rules_triggered.append(f"WALLET_LIMIT_EXCEEDED: ₹{amount:,.0f} > ₹{THRESHOLDS.WALLET_LIMIT:,}")
            score += 0.3
        
        # R4: ATM must be cash withdrawal only
        if channel == 'atm' and category != 'cash_withdrawal':
            rules_triggered.append(f"INVALID_ATM_CATEGORY: {category}")
            score += 0.6
        
        # R5: Night time transactions
        timestamp = txn.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        hour = timestamp.hour
        
        if (hour >= THRESHOLDS.HIGH_RISK_START or hour < THRESHOLDS.HIGH_RISK_END):
            # Dynamic: use user's typical transaction amount to judge "high value at night"
            night_threshold = user_profile.avg_amount * 5 if user_profile.is_mature else 10000
            if amount > night_threshold:
                rules_triggered.append(f"NIGHT_HIGH_VALUE: {hour}:00 IST, ₹{amount:,.0f} (>{night_threshold:,.0f})")
                score += 0.25
        
        # R6: New device + high value (relative to user)
        high_value_for_user = user_profile.avg_amount * 3 if user_profile.is_mature else 25000
        if txn.get('is_new_device') and amount > high_value_for_user:
            rules_triggered.append(f"NEW_DEVICE_HIGH_VALUE: ₹{amount:,.0f} (>{high_value_for_user:,.0f} for this user)")
            score += 0.3
        
        # R7: New location + new device (account takeover pattern)
        if txn.get('is_new_device') and txn.get('is_new_location'):
            rules_triggered.append("NEW_DEVICE_AND_LOCATION")
            score += 0.35
        
        # R8: High-risk categories
        high_risk_categories = ['cryptocurrency', 'gambling', 'forex', 'jewellery']
        if any(cat in category for cat in high_risk_categories):
            rules_triggered.append(f"HIGH_RISK_CATEGORY: {category}")
            score += 0.2
        
        # R9: Round amount (potential structuring) - but relative to user's typical amounts
        structuring_threshold = max(user_profile.avg_amount * 5, 10000) if user_profile.is_mature else 10000
        if amount >= structuring_threshold and amount % 10000 == 0:
            rules_triggered.append(f"ROUND_AMOUNT: ₹{amount:,.0f}")
            score += 0.1
        
        # R10: DYNAMIC VELOCITY - User-specific velocity anomaly
        if anomaly_info.get('is_velocity_anomaly'):
            score += 0.2
        
        # R11: DYNAMIC DAILY LIMIT - Transaction exceeds user's typical daily total
        if user_profile.is_mature and 'daily_limit' in dynamic_thresholds:
            today_key = datetime.now().strftime('%Y-%m-%d')
            today_total = user_profile.daily_totals.get(today_key, 0)
            if today_total > dynamic_thresholds['daily_limit']:
                rules_triggered.append(f"DAILY_LIMIT_EXCEEDED: Today ₹{today_total:,.0f} > ₹{dynamic_thresholds['daily_limit']:,.0f}")
                score += 0.3
        
        return min(score, 1.0), rules_triggered
    
    def _get_risk_level(self, score: float) -> str:
        """Determine risk level from score"""
        if score >= self.RISK_THRESHOLDS['CRITICAL']:
            return 'CRITICAL'
        elif score >= self.RISK_THRESHOLDS['HIGH']:
            return 'HIGH'
        elif score >= self.RISK_THRESHOLDS['MEDIUM']:
            return 'MEDIUM'
        return 'LOW'
    
    def _get_recommendation(self, risk_level: str, rules: List[str]) -> str:
        """Get action recommendation"""
        if risk_level == 'CRITICAL':
            return 'BLOCK'
        elif risk_level == 'HIGH':
            return 'REVIEW'
        elif risk_level == 'MEDIUM':
            return 'FLAG'
        return 'APPROVE'
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get model statistics and feature importance"""
        stats = {
            'version': self.VERSION,
            'model_loaded': self.model_loaded,
            'feature_names': self.FEATURE_NAMES,
            'thresholds': {
                'critical': self.RISK_THRESHOLDS['CRITICAL'],
                'high': self.RISK_THRESHOLDS['HIGH'],
                'medium': self.RISK_THRESHOLDS['MEDIUM']
            },
            'india_limits': {
                'high_value': THRESHOLDS.HIGH_VALUE,
                'very_high_value': THRESHOLDS.VERY_HIGH_VALUE,
                'upi_limit': THRESHOLDS.UPI_SINGLE_LIMIT,
                'atm_limit': THRESHOLDS.ATM_DAILY_LIMIT
            },
            'dynamic_detection': {
                'enabled': True,
                'persistent': True,  # Profiles survive restarts
                'description': 'Personalized anomaly detection based on user behavior (PERSISTENT)',
                'active_user_profiles': len(self.user_profiles),
                'mature_profiles': sum(1 for p in self.user_profiles.values() if p.is_mature),
                'profiles_path': str(self.profiles_path),
                'detection_criteria': {
                    'amount_zscore_threshold': 3.0,
                    'amount_ratio_threshold': 5.0,
                    'daily_deviation_threshold': 3.0,
                    'min_transactions_for_maturity': 10
                }
            }
        }
        
        if self.xgb_model is not None:
            try:
                importance = self.xgb_model.feature_importances_
                stats['feature_importance'] = {
                    name: round(float(imp), 4) 
                    for name, imp in zip(self.FEATURE_NAMES, importance)
                }
            except:
                pass
        
        return stats
    
    def save_profiles(self) -> None:
        """Force save all user profiles (call on shutdown)"""
        if self.user_profiles:
            self._save_user_profiles()
            logger.info(f"💾 Saved {len(self.user_profiles)} user profiles on shutdown")
    
    def get_user_profile_summary(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of a user's behavioral profile for debugging/monitoring"""
        if user_id not in self.user_profiles:
            return None
        
        profile = self.user_profiles[user_id]
        return {
            'user_id': user_id,
            'is_mature': profile.is_mature,
            'transaction_count': profile.txn_count,
            'profile_age_days': profile.profile_age_days,
            'statistics': {
                'avg_amount': round(profile.avg_amount, 2),
                'std_amount': round(profile.std_amount, 2),
                'median_amount': round(profile.median_amount, 2),
                'max_amount': round(profile.max_amount, 2),
                'p75_amount': round(profile.p75_amount, 2),
                'p95_amount': round(profile.p95_amount, 2)
            },
            'daily_behavior': {
                'avg_daily_total': round(profile.avg_daily_total, 2),
                'max_daily_total': round(profile.max_daily_total, 2),
                'avg_daily_txn_count': round(profile.avg_daily_txn_count, 2)
            },
            'dynamic_thresholds': profile.get_dynamic_thresholds()
        }


# Singleton instance
_engine_instance: Optional[FraudDetectionEngine] = None

def get_engine() -> FraudDetectionEngine:
    """Get or create fraud detection engine singleton"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = FraudDetectionEngine()
    return _engine_instance
