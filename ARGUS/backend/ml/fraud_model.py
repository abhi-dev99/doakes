"""
ARGUS - AI Fraud Detection Engine v3.0 (India-focused)
=======================================================
Realistic fraud detection based on:
- RBI fraud statistics (0.05-0.1% fraud rate in digital payments)
- UPI/Card transaction patterns from NPCI data
- Research papers on fraud detection thresholds
- Indian payment ecosystem characteristics

References:
- RBI Annual Report 2023-24: Digital payment fraud statistics
- NPCI UPI Ecosystem Statistics 
- "Credit Card Fraud Detection" - Kaggle dataset patterns (European transactions)
- "Machine Learning for Fraud Detection" - IEEE papers on realistic thresholds
- Indian e-commerce transaction patterns (Razorpay, PayTM insights)

Key realistic assumptions for India:
- Average UPI transaction: ₹1,500-2,000
- Average card transaction: ₹3,000-5,000
- High-value threshold: ₹50,000+ (not ₹10,000)
- Fraud rate: 0.1% (not 5%)4
- Most fraud: Card-not-present, account takeover, social engineering
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
from xgboost import XGBClassifier
import joblib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
import json
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ARGUS.FraudEngine")


class VelocityTracker:
    """Track transaction velocity per user with time-decay"""
    
    def __init__(self):
        self.user_transactions: Dict[str, List[dict]] = defaultdict(list)
        
    def add_transaction(self, user_id: str, amount: float, merchant_id: str, timestamp: datetime):
        self.user_transactions[user_id].append({
            'amount': amount,
            'timestamp': timestamp,
            'merchant_id': merchant_id
        })
        
        # Keep only last 30 days, max 200 txns per user
        cutoff = timestamp - timedelta(days=30)
        self.user_transactions[user_id] = [
            t for t in self.user_transactions[user_id]
            if t['timestamp'] > cutoff
        ][-200:]
        
    def get_velocity_features(self, user_id: str, current_time: datetime) -> dict:
        txns = self.user_transactions.get(user_id, [])
        
        if not txns:
            return {
                'velocity_1h': 0, 'velocity_24h': 0, 'velocity_7d': 0,
                'amount_1h': 0, 'amount_24h': 0, 'avg_amount_7d': 0,
                'unique_merchants_7d': 0, 'time_since_last_txn': 9999,
                'is_new_user': 1
            }
        
        one_hour = current_time - timedelta(hours=1)
        one_day = current_time - timedelta(days=1)
        seven_days = current_time - timedelta(days=7)
        
        txns_1h = [t for t in txns if t['timestamp'] > one_hour]
        txns_24h = [t for t in txns if t['timestamp'] > one_day]
        txns_7d = [t for t in txns if t['timestamp'] > seven_days]
        
        amounts_7d = [t['amount'] for t in txns_7d] if txns_7d else [0]
        merchants_7d = set(t['merchant_id'] for t in txns_7d)
        
        last_txn_time = max(t['timestamp'] for t in txns)
        time_since_last = (current_time - last_txn_time).total_seconds() / 60
        
        return {
            'velocity_1h': len(txns_1h),
            'velocity_24h': len(txns_24h),
            'velocity_7d': len(txns_7d),
            'amount_1h': sum(t['amount'] for t in txns_1h),
            'amount_24h': sum(t['amount'] for t in txns_24h),
            'avg_amount_7d': np.mean(amounts_7d) if amounts_7d else 0,
            'std_amount_7d': np.std(amounts_7d) if len(amounts_7d) > 1 else 0,
            'unique_merchants_7d': len(merchants_7d),
            'time_since_last_txn': min(time_since_last, 9999),
            'is_new_user': 0
        }


class FraudDetectionEngineV2:
    """
    Production fraud detection for Indian payment ecosystem.
    
    Design philosophy:
    - LOW false positive rate (< 2% of legitimate transactions flagged)
    - High recall on actual fraud (catch > 80% of fraud)
    - Rules based on RBI guidelines and real fraud patterns
    - ML models as secondary signal, not primary
    """
    
    VERSION = "3.0.0-india"
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path or os.path.join(os.path.dirname(__file__), 'models')
        
        self.xgb_model: Optional[XGBClassifier] = None
        self.isolation_forest: Optional[IsolationForest] = None
        self.scaler = RobustScaler()
        self.scaler_fitted = False
        
        self.velocity_tracker = VelocityTracker()
        
        # Feature names for the model
        self.feature_names = [
            'amount', 'amount_log', 'hour_of_day', 'day_of_week', 'is_weekend',
            'is_late_night', 'merchant_category_risk', 'transaction_type_risk',
            'channel_risk', 'velocity_1h', 'velocity_24h', 
            'amount_deviation', 'is_round_amount', 'is_high_value',
            'time_since_last_txn', 'is_new_user'
        ]
        
        # Merchant category risk scores (based on RBI fraud data)
        self.merchant_risk = {
            'grocery': 0.05,
            'retail': 0.08,
            'restaurant': 0.06,
            'fuel': 0.05,
            'utilities': 0.03,
            'entertainment': 0.10,
            'travel': 0.12,         # Slightly higher but not crazy
            'healthcare': 0.05,
            'education': 0.04,
            'ecommerce': 0.18,
            'gaming': 0.30,
            'crypto': 0.45,
            'gambling': 0.55,
            'forex': 0.40,
            'investment': 0.35,
            'unknown': 0.20,
        }
        
        # Transaction type risk
        self.txn_type_risk = {
            'purchase': 0.08,
            'bill_payment': 0.05,
            'recharge': 0.10,
            'transfer': 0.15,
            'withdrawal': 0.18,
            'investment': 0.25,
            'refund': 0.12,
        }
        
        # Channel risk (based on RBI digital fraud stats)
        self.channel_risk = {
            'upi': 0.08,
            'pos': 0.05,
            'netbanking': 0.12,
            'card_online': 0.16,
            'wallet': 0.10,
            'atm': 0.14,
            'mobile_banking': 0.10,
        }
        
        # REALISTIC rules for Indian context (amounts in INR)
        self.rules = {
            'high_value_threshold': 50000,
            'very_high_value_threshold': 200000,
            'suspicious_round_amount': 10000,
            'max_txns_per_hour': 15,
            'max_txns_per_day': 50,
            'max_amount_per_hour': 100000,
            'max_amount_per_day': 500000,
            'late_night_start': 23,
            'late_night_end': 5,
            'new_user_high_amount': 25000,
            'rapid_succession_minutes': 2,
        }
        
        self.stats = {
            'total_predictions': 0,
            'blocked': 0,
            'flagged': 0,
            'approved': 0,
            'avg_latency_ms': 0
        }
        
        self.training_metrics = {}
        self._initialize_models()
    
    def _initialize_models(self):
        try:
            self.load_models()
            logger.info(f"Loaded pre-trained models v{self.VERSION}")
        except Exception as e:
            logger.warning(f"Training new models: {e}")
            self._train_models()
    
    def _generate_realistic_training_data(self, n_samples: int = 50000) -> pd.DataFrame:
        """Generate training data with REALISTIC distributions based on Indian payment patterns."""
        np.random.seed(42)
        
        # 99.9% legitimate, 0.1% fraud (realistic rate per RBI data)
        n_legit = int(n_samples * 0.999)
        n_fraud = n_samples - n_legit
        
        data = []
        
        # LEGITIMATE transactions
        for _ in range(n_legit):
            amount = np.random.lognormal(mean=7.3, sigma=1.0)
            amount = np.clip(amount, 10, 500000)
            
            hour_weights = [
                0.01, 0.005, 0.005, 0.005, 0.01, 0.02,
                0.03, 0.05, 0.07, 0.09, 0.10, 0.10,
                0.09, 0.08, 0.07, 0.06, 0.05, 0.05,
                0.06, 0.07, 0.08, 0.06, 0.04, 0.02
            ]
            hour = np.random.choice(24, p=np.array(hour_weights)/sum(hour_weights))
            
            categories = ['grocery', 'retail', 'ecommerce', 'restaurant', 'fuel', 
                         'utilities', 'entertainment', 'travel', 'healthcare']
            cat_weights = [0.20, 0.15, 0.25, 0.12, 0.08, 0.08, 0.05, 0.04, 0.03]
            category = np.random.choice(categories, p=cat_weights)
            
            channels = ['upi', 'card_online', 'pos', 'netbanking', 'wallet']
            chan_weights = [0.45, 0.20, 0.15, 0.12, 0.08]
            channel = np.random.choice(channels, p=chan_weights)
            
            data.append({
                'amount': amount,
                'amount_log': np.log1p(amount),
                'hour_of_day': hour,
                'day_of_week': np.random.randint(0, 7),
                'is_weekend': 1 if np.random.random() < 0.28 else 0,
                'is_late_night': 1 if hour < 5 or hour >= 23 else 0,
                'merchant_category_risk': self.merchant_risk.get(category, 0.1),
                'transaction_type_risk': np.random.choice([0.05, 0.08, 0.10, 0.15]),
                'channel_risk': self.channel_risk.get(channel, 0.1),
                'velocity_1h': np.random.poisson(0.5),
                'velocity_24h': np.random.poisson(3),
                'amount_deviation': np.random.normal(0, 0.5),
                'is_round_amount': 1 if amount >= 1000 and amount % 1000 == 0 and np.random.random() < 0.15 else 0,
                'is_high_value': 1 if amount > 50000 else 0,
                'time_since_last_txn': np.random.exponential(180),
                'is_new_user': 1 if np.random.random() < 0.05 else 0,
                'is_fraud': 0
            })
        
        # FRAUD transactions (based on actual fraud patterns)
        fraud_patterns = ['account_takeover', 'card_not_present', 'social_engineering', 'sim_swap', 'fake_merchant']
        
        for i in range(n_fraud):
            pattern = fraud_patterns[i % len(fraud_patterns)]
            
            if pattern == 'account_takeover':
                amount = np.random.uniform(20000, 200000)
                hour = np.random.choice([0, 1, 2, 3, 4, 23])
                velocity_1h = np.random.randint(3, 10)
                merchant_risk = 0.35
            elif pattern == 'card_not_present':
                amount = np.random.uniform(5000, 80000)
                hour = np.random.randint(0, 24)
                velocity_1h = np.random.randint(2, 6)
                merchant_risk = 0.25
            elif pattern == 'social_engineering':
                amount = np.random.uniform(10000, 100000)
                hour = np.random.randint(9, 21)
                velocity_1h = np.random.randint(1, 3)
                merchant_risk = 0.30
            elif pattern == 'sim_swap':
                amount = np.random.uniform(25000, 300000)
                hour = np.random.choice([0, 1, 2, 22, 23])
                velocity_1h = np.random.randint(5, 15)
                merchant_risk = 0.35
            else:
                amount = np.random.uniform(2000, 30000)
                hour = np.random.randint(10, 22)
                velocity_1h = np.random.randint(0, 3)
                merchant_risk = 0.28
            
            data.append({
                'amount': amount,
                'amount_log': np.log1p(amount),
                'hour_of_day': hour,
                'day_of_week': np.random.randint(0, 7),
                'is_weekend': 1 if np.random.random() < 0.35 else 0,
                'is_late_night': 1 if hour < 5 or hour >= 23 else 0,
                'merchant_category_risk': merchant_risk,
                'transaction_type_risk': np.random.choice([0.15, 0.20, 0.30]),
                'channel_risk': np.random.choice([0.15, 0.18, 0.20]),
                'velocity_1h': velocity_1h,
                'velocity_24h': velocity_1h + np.random.randint(0, 10),
                'amount_deviation': np.random.uniform(1.5, 4),
                'is_round_amount': 1 if np.random.random() < 0.4 else 0,
                'is_high_value': 1 if amount > 50000 else 0,
                'time_since_last_txn': np.random.uniform(0, 30),
                'is_new_user': 1 if np.random.random() < 0.3 else 0,
                'is_fraud': 1
            })
        
        df = pd.DataFrame(data)
        return df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    def _train_models(self):
        logger.info("Generating realistic training data...")
        data = self._generate_realistic_training_data(50000)
        
        feature_cols = [c for c in data.columns if c != 'is_fraud']
        X = data[feature_cols]
        y = data['is_fraud']
        
        logger.info(f"Fraud rate in training: {y.mean()*100:.3f}%")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        self.scaler.fit(X_train)
        self.scaler_fitted = True
        X_train_scaled = self.scaler.transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        logger.info("Training XGBoost...")
        self.xgb_model = XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=500,
            random_state=42,
            eval_metric='aucpr',
            reg_alpha=0.1,
            reg_lambda=1.0,
        )
        self.xgb_model.fit(X_train_scaled, y_train)
        
        logger.info("Training Isolation Forest...")
        self.isolation_forest = IsolationForest(
            n_estimators=100,
            contamination=0.001,
            random_state=42,
            max_features=0.8,
            n_jobs=-1
        )
        self.isolation_forest.fit(X_train_scaled)
        
        y_pred_proba = self.xgb_model.predict_proba(X_test_scaled)[:, 1]
        threshold = 0.3
        y_pred = (y_pred_proba >= threshold).astype(int)
        
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_pred_proba)
        
        self.training_metrics = {
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1_score': round(f1, 4),
            'auc_roc': round(auc, 4),
            'fraud_rate_percent': round(y.mean() * 100, 3),
            'threshold': threshold,
            'trained_at': datetime.now().isoformat()
        }
        
        logger.info(f"Metrics - Precision: {precision:.2%}, Recall: {recall:.2%}, F1: {f1:.2%}, AUC: {auc:.4f}")
        self.save_models()
    
    def extract_features(self, transaction: dict, user_id: str) -> np.ndarray:
        try:
            timestamp = transaction.get('timestamp')
            if isinstance(timestamp, str):
                now = datetime.fromisoformat(timestamp.replace('Z', '+00:00').split('+')[0])
            else:
                now = datetime.now()
        except:
            now = datetime.now()
        
        velocity = self.velocity_tracker.get_velocity_features(user_id, now)
        
        amount = float(transaction.get('amount', 0))
        hour = now.hour
        
        avg_amount = velocity.get('avg_amount_7d', amount)
        std_amount = velocity.get('std_amount_7d', avg_amount * 0.5)
        if std_amount > 0 and avg_amount > 0:
            amount_deviation = (amount - avg_amount) / max(std_amount, 1)
        else:
            amount_deviation = 0
        
        merchant_cat = transaction.get('merchant_category', 'unknown').lower()
        merchant_risk = self.merchant_risk.get(merchant_cat, 0.15)
        
        txn_type = transaction.get('transaction_type', 'purchase').lower()
        txn_risk = self.txn_type_risk.get(txn_type, 0.1)
        
        channel = transaction.get('channel', 'upi').lower()
        channel_risk = self.channel_risk.get(channel, 0.1)
        
        features = np.array([
            amount,
            np.log1p(amount),
            hour,
            now.weekday(),
            1 if now.weekday() >= 5 else 0,
            1 if hour < 5 or hour >= 23 else 0,
            merchant_risk,
            txn_risk,
            channel_risk,
            velocity['velocity_1h'],
            velocity['velocity_24h'],
            np.clip(amount_deviation, -5, 5),
            1 if amount >= 10000 and amount % 1000 == 0 else 0,
            1 if amount > 50000 else 0,
            np.clip(velocity['time_since_last_txn'], 0, 9999),
            velocity['is_new_user']
        ]).reshape(1, -1)
        
        return features
    
    def apply_rules(self, transaction: dict, velocity: dict, amount: float) -> Tuple[float, List[str]]:
        """Rule-based scoring with realistic Indian thresholds."""
        risk_score = 0.0
        triggered_rules = []
        
        try:
            timestamp = transaction.get('timestamp')
            if isinstance(timestamp, str):
                now = datetime.fromisoformat(timestamp.replace('Z', '+00:00').split('+')[0])
            else:
                now = datetime.now()
        except:
            now = datetime.now()
        
        hour = now.hour
        
        # Very high value (₹2L+)
        if amount > self.rules['very_high_value_threshold']:
            risk_score += 0.25
            triggered_rules.append(f"Very high value: ₹{amount:,.0f}")
        elif amount > self.rules['high_value_threshold']:
            risk_score += 0.08
            triggered_rules.append(f"High value: ₹{amount:,.0f}")
        
        # Late night + significant amount
        is_late_night = hour >= self.rules['late_night_start'] or hour < self.rules['late_night_end']
        if is_late_night and amount > 20000:
            risk_score += 0.12
            triggered_rules.append(f"Late night transaction ({hour}:00)")
        
        # High velocity
        if velocity['velocity_1h'] >= self.rules['max_txns_per_hour']:
            risk_score += 0.20
            triggered_rules.append(f"High velocity: {velocity['velocity_1h']} txns in 1hr")
        elif velocity['velocity_1h'] >= 8:
            risk_score += 0.08
        
        # Amount velocity
        if velocity['amount_1h'] + amount > self.rules['max_amount_per_hour']:
            risk_score += 0.18
            triggered_rules.append(f"Hourly amount limit: ₹{velocity['amount_1h'] + amount:,.0f}")
        
        # New user high value
        if velocity['is_new_user'] and amount > self.rules['new_user_high_amount']:
            risk_score += 0.15
            triggered_rules.append(f"New user high value: ₹{amount:,.0f}")
        
        # Rapid succession
        if velocity['time_since_last_txn'] < self.rules['rapid_succession_minutes']:
            if velocity['velocity_1h'] >= 3:
                risk_score += 0.15
                triggered_rules.append(f"Rapid transactions: {velocity['time_since_last_txn']:.1f}min gap")
        
        # High-risk category
        merchant_cat = transaction.get('merchant_category', 'unknown').lower()
        if merchant_cat in ['gambling', 'crypto', 'forex', 'investment']:
            if amount > 10000:
                risk_score += 0.18
                triggered_rules.append(f"High-risk category: {merchant_cat}")
            else:
                risk_score += 0.06
        
        return min(risk_score, 1.0), triggered_rules
    
    def predict(self, transaction: dict, user_id: str) -> dict:
        """Main prediction - conservative scoring, most transactions should be LOW risk."""
        import time
        start_time = time.time()
        
        try:
            timestamp = transaction.get('timestamp')
            if isinstance(timestamp, str):
                now = datetime.fromisoformat(timestamp.replace('Z', '+00:00').split('+')[0])
            else:
                now = datetime.now()
        except:
            now = datetime.now()
        
        velocity = self.velocity_tracker.get_velocity_features(user_id, now)
        amount = float(transaction.get('amount', 0))
        
        features = self.extract_features(transaction, user_id)
        
        if self.scaler_fitted:
            features_scaled = self.scaler.transform(features)
        else:
            features_scaled = features
        
        # ML scores
        xgb_proba = float(self.xgb_model.predict_proba(features_scaled)[0][1])
        
        anomaly_raw = self.isolation_forest.decision_function(features_scaled)[0]
        anomaly_score = float(max(0, min(1, 0.5 - anomaly_raw)))
        
        # Rules
        rule_score, triggered_rules = self.apply_rules(transaction, velocity, amount)
        
        # Conservative ensemble
        base_ml_score = 0.40 * xgb_proba + 0.25 * anomaly_score
        
        if triggered_rules:
            final_score = 0.35 * rule_score + 0.65 * base_ml_score
            if rule_score > 0.2 and xgb_proba > 0.3:
                final_score = min(final_score * 1.15, 1.0)
        else:
            final_score = 0.6 * base_ml_score  # Dampen ML-only signals
        
        # Conservative thresholds
        if final_score >= 0.55:
            risk_level = 'CRITICAL'
            recommendation = 'BLOCK'
        elif final_score >= 0.35:
            risk_level = 'HIGH'
            recommendation = 'REVIEW'
        elif final_score >= 0.18:
            risk_level = 'MEDIUM'
            recommendation = 'FLAG'
        else:
            risk_level = 'LOW'
            recommendation = 'APPROVE'
        
        # Update velocity
        self.velocity_tracker.add_transaction(
            user_id, amount,
            transaction.get('merchant_id', 'unknown'),
            now
        )
        
        # Stats
        self.stats['total_predictions'] += 1
        if recommendation == 'BLOCK':
            self.stats['blocked'] += 1
        elif recommendation in ['FLAG', 'REVIEW']:
            self.stats['flagged'] += 1
        else:
            self.stats['approved'] += 1
        
        latency_ms = (time.time() - start_time) * 1000
        self.stats['avg_latency_ms'] = self.stats['avg_latency_ms'] * 0.95 + latency_ms * 0.05
        
        return {
            'transaction_id': transaction.get('transaction_id', f"TXN-{uuid.uuid4().hex[:8].upper()}"),
            'risk_score': round(float(final_score), 4),
            'risk_level': risk_level,
            'recommendation': recommendation,
            'model_scores': {
                'xgboost': round(xgb_proba, 4),
                'anomaly_detection': round(anomaly_score, 4),
                'rule_engine': round(rule_score, 4)
            },
            'triggered_rules': triggered_rules,
            'features': {
                name: round(float(val), 4) 
                for name, val in zip(self.feature_names, features[0])
            },
            'velocity': {
                'txns_1h': velocity['velocity_1h'],
                'txns_24h': velocity['velocity_24h'],
                'amount_1h': round(velocity['amount_1h'], 2),
                'amount_24h': round(velocity['amount_24h'], 2)
            },
            'latency_ms': round(latency_ms, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    def batch_predict(self, transactions: List[dict], user_id: str = None) -> List[dict]:
        return [self.predict(txn, user_id or txn.get('user_id', 'unknown')) for txn in transactions]
    
    def save_models(self):
        os.makedirs(self.model_path, exist_ok=True)
        joblib.dump(self.xgb_model, os.path.join(self.model_path, 'xgb_model.joblib'))
        joblib.dump(self.isolation_forest, os.path.join(self.model_path, 'isolation_forest.joblib'))
        joblib.dump(self.scaler, os.path.join(self.model_path, 'scaler.joblib'))
        
        metadata = {
            'version': self.VERSION,
            'feature_names': self.feature_names,
            'training_metrics': self.training_metrics,
            'rules': self.rules,
            'saved_at': datetime.now().isoformat()
        }
        with open(os.path.join(self.model_path, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Models saved to {self.model_path}")
    
    def load_models(self):
        self.xgb_model = joblib.load(os.path.join(self.model_path, 'xgb_model.joblib'))
        self.isolation_forest = joblib.load(os.path.join(self.model_path, 'isolation_forest.joblib'))
        self.scaler = joblib.load(os.path.join(self.model_path, 'scaler.joblib'))
        self.scaler_fitted = True
        
        metadata_path = os.path.join(self.model_path, 'metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                self.training_metrics = metadata.get('training_metrics', {})
    
    def get_model_stats(self) -> dict:
        feature_importance = {}
        if self.xgb_model is not None:
            importance = self.xgb_model.feature_importances_
            feature_importance = dict(zip(
                self.feature_names,
                [round(float(x), 4) for x in importance]
            ))
        
        return {
            'version': self.VERSION,
            'feature_names': self.feature_names,
            'feature_importance': feature_importance,
            'training_metrics': self.training_metrics,
            'rules': self.rules,
            'runtime_stats': self.stats
        }
    
    def update_rule(self, rule_name: str, value: Any) -> bool:
        if rule_name in self.rules:
            self.rules[rule_name] = value
            return True
        return False
    
    def get_user_risk_profile(self, user_id: str) -> dict:
        velocity = self.velocity_tracker.get_velocity_features(user_id, datetime.now())
        return {
            'user_id': user_id,
            'velocity_1h': velocity['velocity_1h'],
            'velocity_24h': velocity['velocity_24h'],
            'velocity_7d': velocity['velocity_7d'],
            'is_new_user': velocity['is_new_user']
        }


_engine_instance: Optional[FraudDetectionEngineV2] = None

def get_fraud_engine() -> FraudDetectionEngineV2:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = FraudDetectionEngineV2()
    return _engine_instance

def reset_engine():
    global _engine_instance
    _engine_instance = None
