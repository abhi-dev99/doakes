"""
Merchant Risk Scoring and Reputation System
Real-time merchant reputation tracking with chargeback analysis
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import json

logger = logging.getLogger("ARGUS.MerchantRep")


class MerchantReputationSystem:
    """Comprehensive merchant reputation and risk scoring"""
    
    # Category risk scores (baseline risk by industry)
    CATEGORY_RISK_SCORES = {
        'crypto': 85,
        'gambling': 80,
        'forex': 75,
        'dating': 70,
        'gaming': 60,
        'travel': 50,
        'electronics': 45,
        'fashion': 40,
        'food': 25,
        'groceries': 20,
        'bills': 15,
        'utilities': 10,
        'healthcare': 10,
        'education': 10
    }
    
    # High-risk countries/regions
    HIGH_RISK_COUNTRIES = {
        'unknown': 50,
        'offshore': 70,
        'sanctioned': 95
    }
    
    def __init__(self):
        self.merchant_database = {}  # merchant_id -> reputation data
        self.chargeback_history = defaultdict(list)  # merchant_id -> list of chargebacks
        self.fraud_reports = defaultdict(int)  # merchant_id -> fraud report count
        self.transaction_history = defaultdict(list)  # merchant_id -> transactions
        
    def register_merchant(self, merchant_id: str, merchant_data: Dict):
        """Register or update merchant information"""
        if merchant_id not in self.merchant_database:
            self.merchant_database[merchant_id] = {
                'merchant_id': merchant_id,
                'name': merchant_data.get('name', 'Unknown'),
                'category': merchant_data.get('category', 'other'),
                'country': merchant_data.get('country', 'IN'),
                'registration_date': datetime.now().isoformat(),
                'total_transactions': 0,
                'total_volume': 0,
                'chargebacks': 0,
                'fraud_reports': 0,
                'reputation_score': 50  # Start neutral
            }
        
        # Update existing data
        self.merchant_database[merchant_id].update({
            k: v for k, v in merchant_data.items() 
            if k in ['name', 'category', 'country']
        })
    
    def record_transaction(self, merchant_id: str, transaction: Dict):
        """Record a transaction for a merchant"""
        if merchant_id not in self.merchant_database:
            self.register_merchant(merchant_id, {
                'category': transaction.get('merchant_category', 'other'),
                'name': transaction.get('merchant_name', merchant_id)
            })
        
        merchant = self.merchant_database[merchant_id]
        merchant['total_transactions'] += 1
        merchant['total_volume'] += transaction.get('amount', 0)
        merchant['last_transaction_date'] = datetime.now().isoformat()
        
        self.transaction_history[merchant_id].append({
            'amount': transaction.get('amount', 0),
            'timestamp': datetime.now().isoformat(),
            'user_id': transaction.get('user_id'),
            'fraud_flagged': transaction.get('is_fraud', False)
        })
        
        # Update reputation based on transaction
        self._update_reputation(merchant_id)
    
    def record_chargeback(self, merchant_id: str, transaction_id: str, amount: float):
        """Record a chargeback against a merchant"""
        self.chargeback_history[merchant_id].append({
            'transaction_id': transaction_id,
            'amount': amount,
            'timestamp': datetime.now().isoformat()
        })
        
        if merchant_id in self.merchant_database:
            self.merchant_database[merchant_id]['chargebacks'] += 1
            self._update_reputation(merchant_id)
    
    def record_fraud_report(self, merchant_id: str, details: Dict):
        """Record a fraud report against a merchant"""
        self.fraud_reports[merchant_id] += 1
        
        if merchant_id in self.merchant_database:
            self.merchant_database[merchant_id]['fraud_reports'] += 1
            self._update_reputation(merchant_id)
    
    def _update_reputation(self, merchant_id: str):
        """Recalculate merchant reputation score"""
        if merchant_id not in self.merchant_database:
            return
        
        merchant = self.merchant_database[merchant_id]
        score = 50  # Start neutral
        
        # Factor 1: Chargeback ratio
        total_txns = merchant.get('total_transactions', 1)
        chargeback_count = merchant.get('chargebacks', 0)
        chargeback_ratio = chargeback_count / total_txns
        
        if chargeback_ratio > 0.02:  # >2% chargeback rate
            score -= 30
        elif chargeback_ratio > 0.01:  # >1% chargeback rate
            score -= 20
        elif chargeback_ratio > 0.005:  # >0.5% chargeback rate
            score -= 10
        else:
            score += 10  # Good chargeback rate
        
        # Factor 2: Fraud reports
        fraud_count = merchant.get('fraud_reports', 0)
        if fraud_count > 10:
            score -= 30
        elif fraud_count > 5:
            score -= 20
        elif fraud_count > 0:
            score -= fraud_count * 3
        
        # Factor 3: Volume and age (established merchants get bonus)
        if total_txns > 1000:
            score += 15
        elif total_txns > 100:
            score += 10
        elif total_txns < 10:
            score -= 5  # New/unknown merchant
        
        # Factor 4: Category baseline risk
        category = merchant.get('category', 'other').lower()
        category_risk = self.CATEGORY_RISK_SCORES.get(category, 30)
        score -= (category_risk - 30) * 0.5  # Adjust by category risk
        
        # Factor 5: Recent fraud pattern
        recent_txns = [t for t in self.transaction_history[merchant_id][-50:]]
        if recent_txns:
            recent_fraud_rate = sum(1 for t in recent_txns if t.get('fraud_flagged', False)) / len(recent_txns)
            if recent_fraud_rate > 0.1:  # >10% fraud rate
                score -= 25
            elif recent_fraud_rate > 0.05:  # >5% fraud rate
                score -= 15
        
        # Clamp score between 0-100
        merchant['reputation_score'] = max(0, min(100, score))
        merchant['last_reputation_update'] = datetime.now().isoformat()
    
    def calculate_merchant_risk(self, merchant_id: str, transaction_amount: float) -> Dict:
        """Calculate comprehensive risk score for a merchant transaction"""
        risk_factors = []
        risk_score = 0
        
        # Check if merchant exists
        if merchant_id not in self.merchant_database:
            risk_score += 20
            risk_factors.append("Unknown merchant (no history)")
            
            # Create placeholder
            self.register_merchant(merchant_id, {'category': 'other'})
        
        merchant = self.merchant_database[merchant_id]
        
        # Factor 1: Reputation score (inverse - low reputation = high risk)
        reputation = merchant.get('reputation_score', 50)
        reputation_risk = (100 - reputation) * 0.4  # 40% weight
        risk_score += reputation_risk
        
        if reputation < 30:
            risk_factors.append(f"Poor merchant reputation ({reputation}/100)")
        elif reputation < 50:
            risk_factors.append(f"Below-average reputation ({reputation}/100)")
        
        # Factor 2: Chargeback ratio
        total_txns = merchant.get('total_transactions', 1)
        chargeback_count = merchant.get('chargebacks', 0)
        chargeback_ratio = chargeback_count / total_txns
        
        if chargeback_ratio > 0.02:
            risk_score += 25
            risk_factors.append(f"High chargeback rate ({chargeback_ratio*100:.1f}%)")
        elif chargeback_ratio > 0.01:
            risk_score += 15
            risk_factors.append(f"Elevated chargeback rate ({chargeback_ratio*100:.1f}%)")
        
        # Factor 3: Fraud reports
        fraud_count = merchant.get('fraud_reports', 0)
        if fraud_count > 5:
            risk_score += 20
            risk_factors.append(f"{fraud_count} fraud reports")
        
        # Factor 4: Category risk
        category = merchant.get('category', 'other').lower()
        category_risk = self.CATEGORY_RISK_SCORES.get(category, 30)
        
        if category_risk > 60:
            risk_score += 15
            risk_factors.append(f"High-risk category: {category}")
        elif category_risk > 40:
            risk_score += 5
            risk_factors.append(f"Moderate-risk category: {category}")
        
        # Factor 5: Transaction amount vs. average
        avg_amount = merchant.get('total_volume', 0) / max(total_txns, 1)
        if avg_amount > 0 and transaction_amount > avg_amount * 5:
            risk_score += 15
            risk_factors.append(f"Amount {transaction_amount/avg_amount:.1f}x higher than average")
        
        # Factor 6: New merchant (less than 10 transactions)
        if total_txns < 10:
            risk_score += 10
            risk_factors.append(f"New/untested merchant ({total_txns} txns)")
        
        # Factor 7: Recent fraud spike
        recent_txns = self.transaction_history[merchant_id][-20:]
        if len(recent_txns) >= 10:
            recent_fraud_count = sum(1 for t in recent_txns if t.get('fraud_flagged', False))
            if recent_fraud_count >= 5:
                risk_score += 20
                risk_factors.append(f"Recent fraud spike: {recent_fraud_count}/20 flagged")
        
        return {
            'merchant_risk_score': min(100, risk_score),
            'risk_factors': risk_factors,
            'merchant_reputation': reputation,
            'merchant_name': merchant.get('name', 'Unknown'),
            'merchant_category': category,
            'total_transactions': total_txns,
            'chargeback_ratio': chargeback_ratio,
            'fraud_reports': fraud_count
        }
    
    def get_merchant_profile(self, merchant_id: str) -> Dict:
        """Get complete merchant profile"""
        if merchant_id not in self.merchant_database:
            return {'error': 'Merchant not found'}
        
        merchant = self.merchant_database[merchant_id]
        
        # Calculate additional metrics
        total_txns = merchant.get('total_transactions', 0)
        chargebacks = len(self.chargeback_history[merchant_id])
        
        return {
            **merchant,
            'chargeback_ratio': chargebacks / max(total_txns, 1),
            'avg_transaction_amount': merchant.get('total_volume', 0) / max(total_txns, 1),
            'recent_transactions': len(self.transaction_history[merchant_id][-30:]),
            'category_risk_baseline': self.CATEGORY_RISK_SCORES.get(
                merchant.get('category', 'other').lower(), 30
            )
        }
    
    def get_high_risk_merchants(self, threshold: int = 70) -> List[Dict]:
        """Get list of high-risk merchants"""
        high_risk = []
        
        for merchant_id, data in self.merchant_database.items():
            risk_analysis = self.calculate_merchant_risk(merchant_id, 0)
            
            if risk_analysis['merchant_risk_score'] >= threshold:
                high_risk.append({
                    'merchant_id': merchant_id,
                    'merchant_name': data.get('name', 'Unknown'),
                    'risk_score': risk_analysis['merchant_risk_score'],
                    'reputation': data.get('reputation_score', 0),
                    'risk_factors': risk_analysis['risk_factors']
                })
        
        return sorted(high_risk, key=lambda x: x['risk_score'], reverse=True)
    
    def cleanup_old_transactions(self, days: int = 90):
        """Clean up transaction history older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for merchant_id in self.transaction_history:
            self.transaction_history[merchant_id] = [
                t for t in self.transaction_history[merchant_id]
                if datetime.fromisoformat(t['timestamp']) >= cutoff_date
            ]


# Global instance
merchant_reputation_system = MerchantReputationSystem()


def analyze_merchant_risk(merchant_id: str, transaction_amount: float, 
                         merchant_category: str = 'other') -> Dict:
    """Wrapper function for merchant risk analysis"""
    # Ensure merchant is registered
    if merchant_id not in merchant_reputation_system.merchant_database:
        merchant_reputation_system.register_merchant(merchant_id, {
            'category': merchant_category
        })
    
    # Get risk analysis
    return merchant_reputation_system.calculate_merchant_risk(merchant_id, transaction_amount)
