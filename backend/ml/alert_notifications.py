"""
Alert Notification System
Multi-channel alerting: Email, SMS, Slack, Webhook
"""

import logging
from datetime import datetime
from typing import Dict, List
import json
from collections import deque

logger = logging.getLogger("ARGUS.Alerts")


class AlertNotificationSystem:
    """Manages multi-channel fraud alerts"""
    
    def __init__(self):
        self.alert_queue = deque(maxlen=1000)
        self.sent_alerts = []
        self.alert_rules = self._initialize_rules()
    
    def _initialize_rules(self) -> Dict:
        """Define alerting rules"""
        return {
            'CRITICAL': {
                'channels': ['email', 'sms', 'slack'],
                'threshold': 90,
                'conditions': ['phishing_detected', 'mule_account', 'fraud_ring']
            },
            'HIGH': {
                'channels': ['email', 'slack'],
                'threshold': 75,
                'conditions': ['high_amount', 'velocity_violation', 'blocked_transaction']
            },
            'MEDIUM': {
                'channels': ['slack'],
                'threshold': 60,
                'conditions': ['challenged_transaction', 'new_device']
            }
        }
    
    def should_alert(self, transaction: Dict, analysis: Dict) -> tuple[bool, str]:
        """Determine if alert should be sent and at what level"""
        risk_score = analysis.get('risk_score', 0)
        
        # Critical alerts
        if (transaction.get('phishing_detected') or 
            analysis.get('graph_fraud', {}).get('sender_analysis', {}).get('is_mule') or
            risk_score >= 90):
            return True, 'CRITICAL'
        
        # High alerts
        if (analysis.get('pre_auth', {}).get('decision') == 'BLOCK' or
            transaction.get('amount', 0) > 100000 or
            risk_score >= 75):
            return True, 'HIGH'
        
        # Medium alerts
        if (analysis.get('pre_auth', {}).get('decision') == 'CHALLENGE' or
            analysis.get('device', {}).get('is_new') or
            risk_score >= 60):
            return True, 'MEDIUM'
        
        return False, 'LOW'
    
    def create_alert(self, transaction: Dict, analysis: Dict, explanation: Dict) -> Dict:
        """Create formatted alert"""
        should_send, level = self.should_alert(transaction, analysis)
        
        if not should_send:
            return None
        
        alert = {
            'alert_id': f"ALERT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{transaction.get('transaction_id', '')[:8]}",
            'level': level,
            'timestamp': datetime.now().isoformat(),
            'transaction_id': transaction.get('transaction_id'),
            'user_id': transaction.get('user_id'),
            'amount': transaction.get('amount'),
            'risk_score': analysis.get('risk_score'),
            'decision': analysis.get('pre_auth', {}).get('decision'),
            'headline': explanation.get('headline'),
            'primary_reason': explanation.get('primary_reason'),
            'channels': self.alert_rules[level]['channels']
        }
        
        self.alert_queue.append(alert)
        return alert
    
    def format_email(self, alert: Dict) -> str:
        """Format email notification"""
        return f"""
Subject: [{alert['level']}] Fraud Alert - Transaction {alert['transaction_id']}

ARGUS Fraud Detection Alert
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Alert Level: {alert['level']}
Transaction ID: {alert['transaction_id']}
Amount: ₹{alert['amount']:,.0f}
Risk Score: {alert['risk_score']:.1f}%
Decision: {alert['decision']}

{alert['headline']}

Primary Reason:
{alert['primary_reason']}

Action Required:
Please review this transaction immediately in the ARGUS dashboard.

View Details: http://localhost:3000/transaction/{alert['transaction_id']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated alert from ARGUS Fraud Detection System
"""
    
    def format_sms(self, alert: Dict) -> str:
        """Format SMS notification (160 chars max)"""
        return f"ARGUS {alert['level']}: ₹{alert['amount']:,.0f} txn blocked. Risk {alert['risk_score']:.0f}%. Review now."
    
    def format_slack(self, alert: Dict) -> Dict:
        """Format Slack webhook payload"""
        color_map = {
            'CRITICAL': '#FF0000',
            'HIGH': '#FF6B00',
            'MEDIUM': '#FFA500'
        }
        
        return {
            "attachments": [
                {
                    "color": color_map[alert['level']],
                    "title": f"{alert['level']} Fraud Alert",
                    "text": alert['headline'],
                    "fields": [
                        {
                            "title": "Transaction ID",
                            "value": alert['transaction_id'],
                            "short": True
                        },
                        {
                            "title": "Amount",
                            "value": f"₹{alert['amount']:,.0f}",
                            "short": True
                        },
                        {
                            "title": "Risk Score",
                            "value": f"{alert['risk_score']:.1f}%",
                            "short": True
                        },
                        {
                            "title": "Decision",
                            "value": alert['decision'],
                            "short": True
                        },
                        {
                            "title": "Reason",
                            "value": alert['primary_reason'],
                            "short": False
                        }
                    ],
                    "footer": "ARGUS Fraud Detection",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
    
    def send_alert(self, alert: Dict) -> Dict:
        """Simulate sending alert (in production, would actually send)"""
        if not alert:
            return {'sent': False}
        
        sent_channels = []
        
        for channel in alert['channels']:
            if channel == 'email':
                email_content = self.format_email(alert)
                logger.info(f"📧 [SIMULATED] Email sent: {email_content[:100]}...")
                sent_channels.append('email')
            
            elif channel == 'sms':
                sms_content = self.format_sms(alert)
                logger.info(f"📱 [SIMULATED] SMS sent: {sms_content}")
                sent_channels.append('sms')
            
            elif channel == 'slack':
                slack_payload = self.format_slack(alert)
                logger.info(f"💬 [SIMULATED] Slack webhook: {json.dumps(slack_payload, indent=2)[:200]}...")
                sent_channels.append('slack')
        
        self.sent_alerts.append({
            **alert,
            'sent_at': datetime.now().isoformat(),
            'sent_channels': sent_channels
        })
        
        return {
            'sent': True,
            'channels': sent_channels,
            'alert_id': alert['alert_id']
        }
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent alerts"""
        return list(self.alert_queue)[-limit:]
    
    def get_alert_stats(self) -> Dict:
        """Get alerting statistics"""
        if not self.sent_alerts:
            return {}
        
        return {
            'total_alerts': len(self.sent_alerts),
            'by_level': {
                'CRITICAL': sum(1 for a in self.sent_alerts if a['level'] == 'CRITICAL'),
                'HIGH': sum(1 for a in self.sent_alerts if a['level'] == 'HIGH'),
                'MEDIUM': sum(1 for a in self.sent_alerts if a['level'] == 'MEDIUM')
            },
            'by_channel': {
                'email': sum(1 for a in self.sent_alerts if 'email' in a.get('sent_channels', [])),
                'sms': sum(1 for a in self.sent_alerts if 'sms' in a.get('sent_channels', [])),
                'slack': sum(1 for a in self.sent_alerts if 'slack' in a.get('sent_channels', []))
            },
            'last_alert': self.sent_alerts[-1] if self.sent_alerts else None
        }


# Global instance
alert_system = AlertNotificationSystem()


def send_fraud_alert(transaction: Dict, analysis: Dict, explanation: Dict) -> Dict:
    """Wrapper to create and send alert"""
    alert = alert_system.create_alert(transaction, analysis, explanation)
    return alert_system.send_alert(alert)
