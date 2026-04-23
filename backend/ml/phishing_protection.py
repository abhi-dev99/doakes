"""
PHISHING & UNAUTHORIZED TRANSACTION PROTECTION
===============================================
Detects and prevents fraud from:
- Malicious links (phishing)
- Session hijacking
- Unauthorized transactions
- CSRF attacks
- Man-in-the-browser attacks
"""

import logging
import time
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger("ARGUS.PhishingProtection")


class PhishingProtectionEngine:
    """
    Detects unauthorized transactions from phishing/malicious links.
    
    Scenarios covered:
    1. User clicks malicious link → session stolen → money transferred
    2. Fake payment page (looks like bank) → captures credentials
    3. Man-in-the-browser attack → modifies transaction
    4. CSRF attack → unauthorized transaction from trusted session
    """
    
    def __init__(self):
        # Track user sessions
        self.user_sessions = defaultdict(dict)
        
        # Track suspicious referrers/origins
        self.suspicious_domains = {
            'bit.ly', 'tinyurl.com', 't.co',  # URL shorteners (used in phishing)
            'tk', 'ml', 'ga', 'cf',  # Free TLDs (common in phishing)
        }
        
        # Track user interaction timeline
        self.user_timeline = defaultdict(list)
    
    def check_unauthorized_transaction(
        self,
        transaction: Dict[str, Any],
        session_data: Dict[str, Any],
        http_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if transaction is unauthorized (phishing/session hijacking).
        
        Args:
            transaction: Payment details
            session_data: User session info
            http_context: HTTP headers, referrer, origin, etc.
        
        Returns:
            {
                'is_unauthorized': bool,
                'risk_score': float,
                'attack_type': str,
                'indicators': list[str],
                'should_block': bool
            }
        """
        indicators = []
        risk_score = 0.0
        attack_type = None
        
        user_id = transaction['user_id']
        amount = transaction['amount']
        
        # ===== CHECK 1: SESSION HIJACKING =====
        session_check = self._check_session_hijacking(user_id, session_data, http_context)
        if session_check['is_suspicious']:
            indicators.extend(session_check['indicators'])
            risk_score += session_check['risk_score']
            if not attack_type:
                attack_type = 'SESSION_HIJACKING'
        
        # ===== CHECK 2: SUSPICIOUS REFERRER =====
        referrer_check = self._check_suspicious_referrer(http_context.get('referrer'))
        if referrer_check['is_suspicious']:
            indicators.extend(referrer_check['indicators'])
            risk_score += 0.4
            if not attack_type:
                attack_type = 'PHISHING_LINK'
        
        # ===== CHECK 3: NO USER INTERACTION =====
        interaction_check = self._check_user_interaction(
            user_id, 
            transaction,
            http_context
        )
        if interaction_check['is_suspicious']:
            indicators.extend(interaction_check['indicators'])
            risk_score += interaction_check['risk_score']
            if not attack_type:
                attack_type = 'AUTOMATED_TRANSFER'
        
        # ===== CHECK 4: CSRF ATTACK =====
        csrf_check = self._check_csrf(http_context)
        if csrf_check['is_suspicious']:
            indicators.append('CSRF_TOKEN_MISSING_OR_INVALID')
            risk_score += 0.6
            attack_type = 'CSRF_ATTACK'
        
        # ===== CHECK 5: ORIGIN MISMATCH =====
        origin_check = self._check_origin_mismatch(http_context)
        if origin_check['is_suspicious']:
            indicators.extend(origin_check['indicators'])
            risk_score += 0.5
            if not attack_type:
                attack_type = 'FAKE_PAYMENT_PAGE'
        
        # ===== CHECK 6: TIME-BASED ANOMALY =====
        # Transaction immediately after external link click
        time_check = self._check_temporal_anomaly(user_id, session_data)
        if time_check['is_suspicious']:
            indicators.extend(time_check['indicators'])
            risk_score += 0.3
        
        # Decision
        is_unauthorized = risk_score >= 0.6
        should_block = risk_score >= 0.8
        
        if is_unauthorized:
            logger.warning(
                f"[ALERT] UNAUTHORIZED TRANSACTION DETECTED | "
                f"User: {user_id} | Amount: ₹{amount:,.0f} | "
                f"Attack: {attack_type} | Risk: {risk_score:.0%} | "
                f"Indicators: {', '.join(indicators)}"
            )
        
        return {
            'is_unauthorized': is_unauthorized,
            'risk_score': min(risk_score, 1.0),
            'attack_type': attack_type,
            'indicators': indicators,
            'should_block': should_block,
            'requires_verification': is_unauthorized and not should_block
        }
    
    def _check_session_hijacking(
        self, 
        user_id: str, 
        session_data: Dict[str, Any],
        http_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect if session was stolen/hijacked"""
        indicators = []
        risk_score = 0.0
        
        session_id = session_data.get('session_id')
        
        # Check if we have previous session data
        if user_id in self.user_sessions:
            prev_session = self.user_sessions[user_id]
            
            # 1. IP address suddenly changed
            prev_ip = prev_session.get('ip_address')
            current_ip = http_context.get('ip_address')
            
            if prev_ip and current_ip and prev_ip != current_ip:
                # Check if IPs are from different countries/cities
                if self._are_ips_far_apart(prev_ip, current_ip):
                    indicators.append(f'IP_CHANGED: {prev_ip} → {current_ip}')
                    risk_score += 0.5
            
            # 2. User agent changed (different browser/device)
            prev_ua = prev_session.get('user_agent')
            current_ua = http_context.get('user_agent')
            
            if prev_ua and current_ua and prev_ua != current_ua:
                indicators.append('USER_AGENT_CHANGED')
                risk_score += 0.4
            
            # 3. Session created very recently (< 2 minutes ago)
            session_age = session_data.get('age_seconds', 1000)
            if session_age < 120:
                indicators.append(f'NEW_SESSION: {session_age}s old')
                risk_score += 0.3
        
        # Update session tracking
        self.user_sessions[user_id] = {
            'session_id': session_id,
            'ip_address': http_context.get('ip_address'),
            'user_agent': http_context.get('user_agent'),
            'last_seen': datetime.now()
        }
        
        return {
            'is_suspicious': len(indicators) > 0,
            'risk_score': risk_score,
            'indicators': indicators
        }
    
    def _check_suspicious_referrer(self, referrer: Optional[str]) -> Dict[str, Any]:
        """Check if transaction came from suspicious/phishing link"""
        indicators = []
        
        if not referrer:
            # No referrer - could be direct navigation or hidden referrer
            indicators.append('NO_REFERRER')
            return {'is_suspicious': True, 'indicators': indicators}
        
        # Extract domain from referrer
        try:
            from urllib.parse import urlparse
            parsed = urlparse(referrer)
            domain = parsed.netloc.lower()
            
            # Check if from suspicious domain
            for suspicious in self.suspicious_domains:
                if suspicious in domain:
                    indicators.append(f'SUSPICIOUS_DOMAIN: {domain}')
                    return {'is_suspicious': True, 'indicators': indicators}
            
            # Check for URL shorteners (common in phishing)
            if any(shortener in domain for shortener in ['bit.ly', 'tinyurl', 't.co', 'goo.gl']):
                indicators.append(f'URL_SHORTENER: {domain}')
                return {'is_suspicious': True, 'indicators': indicators}
            
            # Check for typosquatting (fake bank domains)
            # Example: "paytm-secure.tk" instead of "paytm.com"
            suspicious_keywords = [
                'secure', 'login', 'verify', 'account', 'update',
                'bank-', '-bank', 'payment-', '-payment'
            ]
            if any(kw in domain for kw in suspicious_keywords):
                indicators.append(f'SUSPICIOUS_DOMAIN_KEYWORD: {domain}')
                return {'is_suspicious': True, 'indicators': indicators}
        
        except Exception as e:
            logger.error(f"Error parsing referrer: {e}")
        
        return {'is_suspicious': False, 'indicators': []}
    
    def _check_user_interaction(
        self,
        user_id: str,
        transaction: Dict[str, Any],
        http_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if real user initiated transaction (not automated)"""
        indicators = []
        risk_score = 0.0
        
        # 1. No mouse movement before transaction
        mouse_events = http_context.get('mouse_events_count', 0)
        if mouse_events == 0:
            indicators.append('NO_MOUSE_MOVEMENT')
            risk_score += 0.4
        
        # 2. No keyboard events (form filled by script, not human)
        keyboard_events = http_context.get('keyboard_events_count', 0)
        if keyboard_events == 0:
            indicators.append('NO_KEYBOARD_INPUT')
            risk_score += 0.4
        
        # 3. Form submitted too fast (< 3 seconds from page load)
        page_time = http_context.get('time_on_page_seconds', 10)
        if page_time < 3:
            indicators.append(f'INSTANT_SUBMIT: {page_time}s')
            risk_score += 0.5
        
        # 4. No focus events (user didn't click on input fields)
        focus_events = http_context.get('focus_events_count', 0)
        if focus_events == 0:
            indicators.append('NO_FIELD_FOCUS')
            risk_score += 0.3
        
        # 5. JavaScript disabled or blocked (suspicious for modern banking)
        js_enabled = http_context.get('javascript_enabled', True)
        if not js_enabled:
            indicators.append('JAVASCRIPT_DISABLED')
            risk_score += 0.2
        
        return {
            'is_suspicious': len(indicators) >= 2,
            'risk_score': risk_score,
            'indicators': indicators
        }
    
    def _check_csrf(self, http_context: Dict[str, Any]) -> Dict[str, Any]:
        """Check for CSRF (Cross-Site Request Forgery) attack"""
        # Check if CSRF token is present and valid
        csrf_token = http_context.get('csrf_token')
        expected_csrf = http_context.get('expected_csrf_token')
        
        if not csrf_token or csrf_token != expected_csrf:
            return {'is_suspicious': True}
        
        return {'is_suspicious': False}
    
    def _check_origin_mismatch(self, http_context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if request origin doesn't match expected domain"""
        indicators = []
        
        origin = http_context.get('origin', '')
        expected_origins = http_context.get('allowed_origins', [
            'https://yourbank.com',
            'https://payment.yourbank.com'
        ])
        
        if origin and origin not in expected_origins:
            indicators.append(f'ORIGIN_MISMATCH: {origin}')
            return {'is_suspicious': True, 'indicators': indicators}
        
        return {'is_suspicious': False, 'indicators': []}
    
    def _check_temporal_anomaly(
        self,
        user_id: str,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if transaction happened suspiciously fast after session start"""
        indicators = []
        
        session_age = session_data.get('age_seconds', 1000)
        
        # Transaction within 30 seconds of session creation (automated)
        if session_age < 30:
            indicators.append(f'IMMEDIATE_TRANSACTION: {session_age}s after login')
        
        # Check if user had any navigation/browsing before transaction
        page_views = session_data.get('page_views_count', 1)
        if page_views == 1:  # Only payment page, no browsing
            indicators.append('SINGLE_PAGE_SESSION')
        
        return {
            'is_suspicious': len(indicators) > 0,
            'indicators': indicators
        }
    
    def _are_ips_far_apart(self, ip1: str, ip2: str) -> bool:
        """Check if two IPs are from different locations"""
        # Simplified - in production, use GeoIP database
        # Different first octet = likely different network/country
        octet1_ip1 = int(ip1.split('.')[0])
        octet1_ip2 = int(ip2.split('.')[0])
        
        return abs(octet1_ip1 - octet1_ip2) > 10
    
    def add_user_action(self, user_id: str, action: str):
        """Track user actions to detect automation"""
        self.user_timeline[user_id].append({
            'action': action,
            'timestamp': datetime.now()
        })
        
        # Keep only last 100 actions
        if len(self.user_timeline[user_id]) > 100:
            self.user_timeline[user_id] = self.user_timeline[user_id][-100:]
    
    def verify_user_presence(
        self,
        user_id: str,
        challenge_type: str = 'OTP'
    ) -> Dict[str, Any]:
        """
        Send verification to confirm real user is present.
        Use when unauthorized transaction is suspected.
        
        Args:
            user_id: User to verify
            challenge_type: 'OTP', 'PUSH_NOTIFICATION', 'BIOMETRIC'
        
        Returns:
            Verification result
        """
        logger.info(
            f"[VERIFY] USER PRESENCE VERIFICATION | "
            f"User: {user_id} | Method: {challenge_type}"
        )
        
        # In production:
        # - Send SMS OTP
        # - Send push notification to mobile app
        # - Request biometric authentication
        
        return {
            'verification_sent': True,
            'method': challenge_type,
            'expires_in_seconds': 300  # 5 minutes
        }


# Singleton instance
_phishing_engine = None

def get_phishing_protection() -> PhishingProtectionEngine:
    """Get singleton PhishingProtectionEngine instance"""
    global _phishing_engine
    if _phishing_engine is None:
        _phishing_engine = PhishingProtectionEngine()
    return _phishing_engine
