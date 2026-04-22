"""
Explainable AI Module
Provides human-readable explanations for fraud detection decisions
"""

import logging
from typing import Dict, List, Tuple
import numpy as np
from datetime import datetime

logger = logging.getLogger("ARGUS.ExplainableAI")


class FraudExplainer:
    """Generates human-readable explanations for fraud decisions"""
    
    # Feature importance weights (from XGBoost model)
    FEATURE_WEIGHTS = {
        'amount': 0.25,
        'merchant_risk': 0.20,
        'device_reputation': 0.15,
        'velocity': 0.15,
        'geolocation': 0.10,
        'time_of_day': 0.08,
        'user_behavior': 0.07
    }
    
    def __init__(self):
        self.decision_templates = {
            'BLOCK': "🚫 **Transaction BLOCKED** - {primary_reason}",
            'CHALLENGE': "⚠️ **Authentication Required** - {primary_reason}",
            'ALLOW': "✅ **Transaction Approved** - Low risk detected"
        }
    
    def explain_decision(self, transaction: Dict, analysis: Dict) -> Dict:
        """Generate comprehensive explanation for fraud decision"""
        
        # Extract key factors
        factors = self._extract_risk_factors(transaction, analysis)
        
        # Rank by importance
        ranked_factors = sorted(factors, key=lambda x: x['score'], reverse=True)
        
        # Get primary reason
        primary_reason = ranked_factors[0]['reason'] if ranked_factors else "Unknown"
        
        # Get decision
        decision = analysis.get('pre_auth', {}).get('decision', 'ALLOW')
        
        # Build explanation
        explanation = {
            'decision': decision,
            'headline': self.decision_templates[decision].format(primary_reason=primary_reason),
            'primary_reason': primary_reason,
            'contributing_factors': [f['reason'] for f in ranked_factors[1:4]],
            'risk_breakdown': self._build_risk_breakdown(factors),
            'confidence': self._calculate_confidence(analysis),
            'recommendation': self._get_recommendation(decision, analysis)
        }
        
        return explanation
    
    def _extract_risk_factors(self, transaction: Dict, analysis: Dict) -> List[Dict]:
        """Extract and score all risk factors"""
        factors = []
        
        # Amount-based risk
        amount = transaction.get('amount', 0)
        if amount > 50000:
            factors.append({
                'reason': f"High transaction amount: {self._format_inr(amount)}",
                'score': min(100, (amount / 100000) * 50),
                'category': 'amount'
            })
        
        # Merchant risk
        merchant_risk = analysis.get('merchant_risk', {})
        if merchant_risk.get('merchant_risk_score', 0) > 60:
            factors.append({
                'reason': f"High-risk merchant (reputation: {merchant_risk.get('merchant_reputation', 0)}/100)",
                'score': merchant_risk.get('merchant_risk_score', 0),
                'category': 'merchant'
            })
        
        # Device risk
        device = analysis.get('device', {})
        if device.get('is_new'):
            factors.append({
                'reason': "New/unrecognized device",
                'score': 40,
                'category': 'device'
            })
        if device.get('reputation', 100) < 50:
            factors.append({
                'reason': f"Low device reputation ({device.get('reputation', 0)}/100)",
                'score': 100 - device.get('reputation', 100),
                'category': 'device'
            })
        
        # Velocity violations
        pre_auth = analysis.get('pre_auth', {})
        velocity_violations = pre_auth.get('velocity_violations', [])
        if velocity_violations:
            factors.append({
                'reason': f"Velocity limit exceeded: {velocity_violations[0]}",
                'score': 70,
                'category': 'velocity'
            })
        
        # Geolocation risk
        geo = analysis.get('geo', {})
        if geo.get('is_vpn') or geo.get('is_proxy'):
            factors.append({
                'reason': "VPN/Proxy detected - hiding location",
                'score': 60,
                'category': 'geolocation'
            })
        
        # Time anomaly
        ts_value = transaction.get('timestamp')
        hour = datetime.now().hour
        if isinstance(ts_value, datetime):
            hour = ts_value.hour
        elif isinstance(ts_value, str) and ts_value:
            try:
                # Support ISO timestamps with optional Z suffix.
                parsed = datetime.fromisoformat(ts_value.replace('Z', '+00:00'))
                hour = parsed.hour
            except ValueError:
                # Keep fallback current hour when timestamp format is non-ISO.
                pass
        if 22 <= hour or hour <= 5:
            factors.append({
                'reason': f"Unusual time: {hour}:00 (night transaction)",
                'score': 30,
                'category': 'time'
            })
        
        # Graph fraud indicators
        graph_fraud = analysis.get('graph_fraud', {})
        if graph_fraud.get('sender_analysis', {}).get('is_mule'):
            factors.append({
                'reason': "Account identified as potential mule account",
                'score': 90,
                'category': 'graph'
            })
        
        # Sequence risk
        sequence_risk = analysis.get('sequence_risk', {})
        if sequence_risk.get('sequence_risk_score', 0) > 70:
            factors.append({
                'reason': f"Abnormal transaction pattern detected by AI",
                'score': sequence_risk.get('sequence_risk_score', 0),
                'category': 'pattern'
            })
        
        # Phishing
        if transaction.get('phishing_detected'):
            factors.append({
                'reason': f"Phishing attack detected: {transaction.get('attack_type', 'Unknown')}",
                'score': 100,
                'category': 'phishing'
            })
        
        return factors
    
    def _build_risk_breakdown(self, factors: List[Dict]) -> Dict:
        """Build category-wise risk breakdown"""
        breakdown = {}
        
        for factor in factors:
            category = factor['category']
            if category not in breakdown:
                breakdown[category] = {
                    'score': 0,
                    'count': 0,
                    'reasons': []
                }
            breakdown[category]['score'] = max(breakdown[category]['score'], factor['score'])
            breakdown[category]['count'] += 1
            breakdown[category]['reasons'].append(factor['reason'])
        
        return breakdown
    
    def _calculate_confidence(self, analysis: Dict) -> float:
        """Calculate confidence in the decision (0-100)"""
        risk_score = analysis.get('risk_score', 0)
        risk_percent = risk_score * 100 if risk_score <= 1 else risk_score
        
        # High confidence for extreme scores
        if risk_percent > 85 or risk_percent < 15:
            return 95.0
        elif risk_percent > 70 or risk_percent < 30:
            return 85.0
        else:
            return 70.0
    
    def _get_recommendation(self, decision: str, analysis: Dict) -> str:
        """Get actionable recommendation"""
        if decision == 'BLOCK':
            return "Transaction blocked to prevent potential fraud. Customer should be contacted for verification."
        elif decision == 'CHALLENGE':
            auth_method = analysis.get('pre_auth', {}).get('auth_method', 'OTP')
            return f"Require {auth_method} authentication before proceeding with payment."
        else:
            return "Transaction appears legitimate. Process normally with standard monitoring."
    
    def _format_inr(self, amount: float) -> str:
        """Format amount in Indian currency"""
        if amount >= 10000000:
            return f"₹{amount/10000000:.2f} Crore"
        elif amount >= 100000:
            return f"₹{amount/100000:.2f} Lakh"
        else:
            return f"₹{amount:,.0f}"
    
    def generate_pdf_report(self, transaction: Dict, explanation: Dict) -> str:
        """Generate formatted text report (PDF generation would require reportlab)"""
        report = f"""
═══════════════════════════════════════════════════════════════
                    FRAUD ANALYSIS REPORT
═══════════════════════════════════════════════════════════════

Transaction ID: {transaction.get('transaction_id', 'N/A')}
Amount: {self._format_inr(transaction.get('amount', 0))}
Date/Time: {transaction.get('timestamp', 'N/A')}
User: {transaction.get('user_id', 'N/A')}
Merchant: {transaction.get('merchant_id', 'N/A')}

───────────────────────────────────────────────────────────────
DECISION: {explanation['decision']}
───────────────────────────────────────────────────────────────

{explanation['headline']}

PRIMARY REASON:
• {explanation['primary_reason']}

CONTRIBUTING FACTORS:
"""
        for i, factor in enumerate(explanation['contributing_factors'], 1):
            report += f"{i}. {factor}\n"
        
        report += f"""
CONFIDENCE LEVEL: {explanation['confidence']:.1f}%

RECOMMENDATION:
{explanation['recommendation']}

───────────────────────────────────────────────────────────────
RISK BREAKDOWN BY CATEGORY
───────────────────────────────────────────────────────────────
"""
        
        for category, data in explanation['risk_breakdown'].items():
            report += f"\n{category.upper()}: {data['score']:.0f}% risk\n"
            for reason in data['reasons']:
                report += f"  • {reason}\n"
        
        report += "\n═══════════════════════════════════════════════════════════════\n"
        
        return report


# Global instance
explainer = FraudExplainer()


def explain_fraud_decision(transaction: Dict, analysis: Dict) -> Dict:
    """Wrapper function for explainability"""
    return explainer.explain_decision(transaction, analysis)
