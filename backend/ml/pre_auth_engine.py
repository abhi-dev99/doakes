"""
PRE-AUTHORIZATION FRAUD PREVENTION ENGINE v1.0
==============================================
PREVENTS fraud BEFORE payment is processed.
Decision flow: BLOCK → CHALLENGE → ALLOW

This is the critical difference from post-transaction analysis:
- Runs BEFORE payment authorization
- Can block/reject suspicious payments
- Can trigger step-up authentication (OTP, biometric)
- Sub-10ms decision latency required
"""

import time
import logging
from typing import Dict, Any, Literal
from dataclasses import dataclass
from datetime import datetime
import hashlib

logger = logging.getLogger("ARGUS.PreAuth")

# Decision types
Decision = Literal["ALLOW", "CHALLENGE", "BLOCK"]

@dataclass
class PreAuthResult:
    """Result of pre-authorization check"""
    decision: Decision
    risk_score: float
    risk_level: str
    latency_ms: float
    
    # Reasons for decision
    block_reasons: list[str]
    challenge_reasons: list[str]
    
    # Required authentication step if CHALLENGE
    auth_method: str | None = None  # 'OTP', '3DS', 'BIOMETRIC'
    
    # Monitoring data
    rules_triggered: list[str] = None
    velocity_violations: list[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'decision': self.decision,
            'risk_score': round(self.risk_score, 4),
            'risk_level': self.risk_level,
            'latency_ms': round(self.latency_ms, 2),
            'block_reasons': self.block_reasons,
            'challenge_reasons': self.challenge_reasons,
            'auth_method': self.auth_method,
            'rules_triggered': self.rules_triggered or [],
            'velocity_violations': self.velocity_violations or []
        }


class PreAuthEngine:
    """
    Real-time fraud prevention engine that runs BEFORE payment authorization.
    Makes instant BLOCK/CHALLENGE/ALLOW decisions.
    """
    
    # Decision thresholds
    BLOCK_THRESHOLD = 0.85      # Risk >= 85% → BLOCK
    CHALLENGE_THRESHOLD = 0.60  # Risk >= 60% → CHALLENGE
    # Risk < 60% → ALLOW
    
    def __init__(self):
        self.velocity_tracker = VelocityTracker()
        self.device_analyzer = DeviceAnalyzer()
        self.geo_analyzer = GeoAnalyzer()
        self.merchant_scorer = MerchantRiskScorer()
        
        logger.info("PreAuthEngine initialized - BLOCKING mode active")
    
    def check_pre_authorization(
        self, 
        transaction: Dict[str, Any],
        user_context: Dict[str, Any],
        device_context: Dict[str, Any],
        geo_context: Dict[str, Any]
    ) -> PreAuthResult:
        """
        Main pre-authorization check - runs BEFORE payment.
        
        Args:
            transaction: Payment details (amount, channel, merchant, etc.)
            user_context: User history (user_id, account_age, trusted_status)
            device_context: Device fingerprint (device_id, browser, os, etc.)
            geo_context: Location data (ip, country, city, lat/lon)
        
        Returns:
            PreAuthResult with ALLOW/CHALLENGE/BLOCK decision
        """
        start_time = time.time()
        
        block_reasons = []
        challenge_reasons = []
        rules_triggered = []
        velocity_violations = []
        
        # Extract key fields
        amount = transaction.get('amount', 0)
        user_id = user_context.get('user_id')
        device_id = device_context.get('device_id')
        ip_address = geo_context.get('ip_address')
        
        # ===== HARD BLOCKS (Instant rejection) =====
        
        # 1. Blacklisted entities
        if self._is_blacklisted(user_id, device_id, ip_address):
            block_reasons.append("BLACKLISTED_ENTITY")
            return PreAuthResult(
                decision="BLOCK",
                risk_score=1.0,
                risk_level="CRITICAL",
                latency_ms=(time.time() - start_time) * 1000,
                block_reasons=block_reasons,
                challenge_reasons=[],
                rules_triggered=["BLACKLIST_HIT"]
            )
        
        # 2. Velocity violations (real-time counters)
        velocity_result = self.velocity_tracker.check_velocity(
            user_id=user_id,
            device_id=device_id,
            ip_address=ip_address,
            amount=amount,
            channel=transaction.get('channel')
        )
        
        if velocity_result['is_violation']:
            velocity_violations = velocity_result['violations']
            block_reasons.extend(velocity_result['block_reasons'])
            challenge_reasons.extend(velocity_result['challenge_reasons'])
        
        # 3. Impossible travel detection
        geo_risk = self.geo_analyzer.analyze_location(
            user_id=user_id,
            current_ip=ip_address,
            current_lat=geo_context.get('latitude'),
            current_lon=geo_context.get('longitude'),
            timestamp=datetime.now()
        )
        
        if geo_risk['impossible_travel']:
            block_reasons.append(f"IMPOSSIBLE_TRAVEL: {geo_risk['distance_km']}km in {geo_risk['time_mins']}min")
            rules_triggered.append("IMPOSSIBLE_TRAVEL")
        
        if geo_risk['is_vpn'] or geo_risk['is_proxy']:
            challenge_reasons.append("VPN_OR_PROXY_DETECTED")
            rules_triggered.append("ANONYMIZER_DETECTED")
        
        # 4. Device risk scoring
        device_risk = self.device_analyzer.score_device(
            device_id=device_id,
            device_fingerprint=device_context.get('fingerprint'),
            is_new_device=device_context.get('is_new', False),
            device_reputation=device_context.get('reputation', 0.5)
        )
        
        if device_risk['is_high_risk']:
            challenge_reasons.extend(device_risk['risk_factors'])
        
        # 5. Merchant risk scoring
        merchant_risk = self.merchant_scorer.score_merchant(
            merchant_id=transaction.get('merchant_id'),
            merchant_category=transaction.get('merchant_category'),
            amount=amount
        )
        
        if merchant_risk['is_high_risk']:
            challenge_reasons.append(f"HIGH_RISK_MERCHANT: {merchant_risk['risk_reason']}")
        
        # ===== CALCULATE AGGREGATE RISK SCORE =====
        
        risk_components = {
            'velocity': velocity_result.get('risk_score', 0.0) * 0.30,
            'geo': geo_risk.get('risk_score', 0.0) * 0.25,
            'device': device_risk.get('risk_score', 0.0) * 0.20,
            'merchant': merchant_risk.get('risk_score', 0.0) * 0.15,
            'amount': self._calculate_amount_risk(amount) * 0.10
        }
        
        total_risk_score = sum(risk_components.values())
        
        # Risk level classification
        if total_risk_score >= 0.85:
            risk_level = "CRITICAL"
        elif total_risk_score >= 0.70:
            risk_level = "HIGH"
        elif total_risk_score >= 0.50:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # ===== MAKE DECISION =====
        
        latency_ms = (time.time() - start_time) * 1000
        
        # BLOCK decision
        if block_reasons or total_risk_score >= self.BLOCK_THRESHOLD:
            if not block_reasons:
                block_reasons.append(f"HIGH_RISK_SCORE: {total_risk_score:.2%}")
            
            logger.warning(
                f"[BLOCK] Pre-auth | User: {user_id} | Amount: \u20b9{amount:,.0f} | "
                f"Risk: {total_risk_score:.2%} | Reasons: {', '.join(block_reasons)}"
            )
            
            return PreAuthResult(
                decision="BLOCK",
                risk_score=total_risk_score,
                risk_level=risk_level,
                latency_ms=latency_ms,
                block_reasons=block_reasons,
                challenge_reasons=[],
                rules_triggered=rules_triggered,
                velocity_violations=velocity_violations
            )
        
        # CHALLENGE decision
        if challenge_reasons or total_risk_score >= self.CHALLENGE_THRESHOLD:
            if not challenge_reasons:
                challenge_reasons.append(f"ELEVATED_RISK: {total_risk_score:.2%}")
            
            # Determine authentication method based on risk level
            if total_risk_score >= 0.75:
                auth_method = "BIOMETRIC"  # Highest security
            elif total_risk_score >= 0.65:
                auth_method = "3DS"  # 3D Secure
            else:
                auth_method = "OTP"  # Basic OTP
            
            logger.info(
                f"[CHALLENGE] Pre-auth | User: {user_id} | Amount: \u20b9{amount:,.0f} | "
                f"Risk: {total_risk_score:.2%} | Auth: {auth_method}"
            )
            
            return PreAuthResult(
                decision="CHALLENGE",
                risk_score=total_risk_score,
                risk_level=risk_level,
                latency_ms=latency_ms,
                block_reasons=[],
                challenge_reasons=challenge_reasons,
                auth_method=auth_method,
                rules_triggered=rules_triggered,
                velocity_violations=velocity_violations
            )
        
        # ALLOW decision
        logger.info(
            f"[ALLOW] Pre-auth | User: {user_id} | Amount: \u20b9{amount:,.0f} | "
            f"Risk: {total_risk_score:.2%}"
        )
        
        return PreAuthResult(
            decision="ALLOW",
            risk_score=total_risk_score,
            risk_level=risk_level,
            latency_ms=latency_ms,
            block_reasons=[],
            challenge_reasons=[],
            rules_triggered=rules_triggered,
            velocity_violations=velocity_violations
        )
    
    def _is_blacklisted(self, user_id: str, device_id: str, ip_address: str) -> bool:
        """Check if user/device/IP is blacklisted"""
        # TODO: Integrate with blacklist database (Redis/DB)
        # For now, maintain in-memory blacklist
        blacklisted_users = set()
        blacklisted_devices = set()
        blacklisted_ips = set()
        
        return (
            user_id in blacklisted_users or
            device_id in blacklisted_devices or
            ip_address in blacklisted_ips
        )
    
    def _calculate_amount_risk(self, amount: float) -> float:
        """Calculate risk score based on amount (structuring detection)"""
        # Structuring detection: amounts just below reporting thresholds
        suspicious_ranges = [
            (49000, 50000),   # Just below ₹50K
            (99000, 100000),  # Just below ₹1L
            (190000, 200000), # Just below ₹2L
        ]
        
        for lower, upper in suspicious_ranges:
            if lower <= amount <= upper:
                return 0.7  # High risk - possible structuring
        
        # Very high amounts
        if amount >= 500000:
            return 0.6
        elif amount >= 200000:
            return 0.4
        elif amount >= 50000:
            return 0.2
        else:
            return 0.05


class VelocityTracker:
    """Real-time velocity tracking with multiple time windows"""
    
    def __init__(self):
        # In-memory counters (use Redis in production for distributed systems)
        from collections import defaultdict, deque
        
        self.user_txns = defaultdict(lambda: deque(maxlen=1000))
        self.device_txns = defaultdict(lambda: deque(maxlen=1000))
        self.ip_txns = defaultdict(lambda: deque(maxlen=1000))
        
        # Velocity limits
        self.limits = {
            '1min': {'txn_count': 5, 'amount': 50000},
            '5min': {'txn_count': 15, 'amount': 150000},
            '1hour': {'txn_count': 50, 'amount': 500000},
            '24hour': {'txn_count': 200, 'amount': 2000000}
        }
    
    def check_velocity(
        self, 
        user_id: str, 
        device_id: str, 
        ip_address: str, 
        amount: float,
        channel: str
    ) -> Dict[str, Any]:
        """Check velocity across multiple dimensions and time windows"""
        now = time.time()
        violations = []
        block_reasons = []
        challenge_reasons = []
        
        # Record transaction
        txn_record = {'timestamp': now, 'amount': amount, 'channel': channel}
        self.user_txns[user_id].append(txn_record)
        self.device_txns[device_id].append(txn_record)
        self.ip_txns[ip_address].append(txn_record)
        
        # Check each time window
        for window_name, window_limits in self.limits.items():
            window_seconds = self._window_to_seconds(window_name)
            cutoff_time = now - window_seconds
            
            # Count transactions in window
            user_window_txns = [t for t in self.user_txns[user_id] if t['timestamp'] >= cutoff_time]
            device_window_txns = [t for t in self.device_txns[device_id] if t['timestamp'] >= cutoff_time]
            ip_window_txns = [t for t in self.ip_txns[ip_address] if t['timestamp'] >= cutoff_time]
            
            # Transaction count violations
            if len(user_window_txns) > window_limits['txn_count']:
                violation = f"USER_VELOCITY_{window_name.upper()}: {len(user_window_txns)} txns (limit: {window_limits['txn_count']})"
                violations.append(violation)
                if window_name in ['1min', '5min']:
                    block_reasons.append(violation)
                else:
                    challenge_reasons.append(violation)
            
            # Amount velocity violations
            user_window_amount = sum(t['amount'] for t in user_window_txns)
            if user_window_amount > window_limits['amount']:
                violation = f"AMOUNT_VELOCITY_{window_name.upper()}: ₹{user_window_amount:,.0f} (limit: ₹{window_limits['amount']:,})"
                violations.append(violation)
                if window_name in ['1min', '5min']:
                    block_reasons.append(violation)
                else:
                    challenge_reasons.append(violation)
            
            # Cross-entity velocity (same device, different users - account takeover)
            unique_users_on_device = len(set(
                self._get_recent_users(device_id, cutoff_time)
            ))
            if unique_users_on_device > 3:
                block_reasons.append(f"MULTI_USER_DEVICE: {unique_users_on_device} users on device in {window_name}")
        
        # Calculate aggregate risk score
        risk_score = min(
            (len(violations) * 0.15) + (len(block_reasons) * 0.30),
            1.0
        )
        
        return {
            'is_violation': len(violations) > 0,
            'violations': violations,
            'block_reasons': block_reasons,
            'challenge_reasons': challenge_reasons,
            'risk_score': risk_score
        }
    
    def _window_to_seconds(self, window: str) -> int:
        """Convert window name to seconds"""
        mapping = {
            '1min': 60,
            '5min': 300,
            '1hour': 3600,
            '24hour': 86400
        }
        return mapping.get(window, 3600)
    
    def _get_recent_users(self, device_id: str, cutoff_time: float) -> list:
        """Get list of users who used this device recently (simulated)"""
        # TODO: Implement actual user tracking per device
        return []


class DeviceAnalyzer:
    """Analyzes device fingerprints and reputation"""
    
    def score_device(
        self, 
        device_id: str, 
        device_fingerprint: Dict[str, Any],
        is_new_device: bool,
        device_reputation: float
    ) -> Dict[str, Any]:
        """Score device risk based on fingerprint and history"""
        
        risk_factors = []
        risk_score = 0.0
        
        # New device risk
        if is_new_device:
            risk_factors.append("NEW_DEVICE")
            risk_score += 0.3
        
        # Device reputation (0 = bad, 1 = good)
        if device_reputation < 0.3:
            risk_factors.append(f"LOW_DEVICE_REPUTATION: {device_reputation:.2f}")
            risk_score += 0.4
        elif device_reputation < 0.5:
            risk_factors.append(f"MODERATE_DEVICE_REPUTATION: {device_reputation:.2f}")
            risk_score += 0.2
        
        # Fingerprint anomalies
        if device_fingerprint:
            # Check for headless browsers (automation)
            if device_fingerprint.get('headless'):
                risk_factors.append("HEADLESS_BROWSER_DETECTED")
                risk_score += 0.6
            
            # Check for emulators
            if device_fingerprint.get('is_emulator'):
                risk_factors.append("EMULATOR_DETECTED")
                risk_score += 0.5
            
            # Check for tampered fingerprint
            if device_fingerprint.get('fingerprint_inconsistent'):
                risk_factors.append("FINGERPRINT_TAMPERING")
                risk_score += 0.4
        
        is_high_risk = risk_score >= 0.5
        
        return {
            'risk_score': min(risk_score, 1.0),
            'is_high_risk': is_high_risk,
            'risk_factors': risk_factors
        }


class GeoAnalyzer:
    """Geolocation and IP reputation analysis"""
    
    def __init__(self):
        # Store last known location per user
        self.user_locations = {}
    
    def analyze_location(
        self, 
        user_id: str, 
        current_ip: str,
        current_lat: float,
        current_lon: float,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Analyze location for impossible travel, VPN, high-risk countries"""
        
        risk_score = 0.0
        impossible_travel = False
        is_vpn = False
        is_proxy = False
        is_tor = False
        distance_km = 0
        time_mins = 0
        
        # Check IP reputation
        ip_risk = self._check_ip_reputation(current_ip)
        is_vpn = ip_risk.get('is_vpn', False)
        is_proxy = ip_risk.get('is_proxy', False)
        is_tor = ip_risk.get('is_tor', False)
        
        if is_vpn:
            risk_score += 0.3
        if is_proxy:
            risk_score += 0.4
        if is_tor:
            risk_score += 0.6
        
        # Impossible travel detection
        if user_id in self.user_locations:
            last_loc = self.user_locations[user_id]
            last_lat, last_lon = last_loc['lat'], last_loc['lon']
            last_time = last_loc['timestamp']
            
            # Calculate distance
            distance_km = self._haversine_distance(
                last_lat, last_lon, current_lat, current_lon
            )
            
            # Calculate time difference
            time_diff = (timestamp - last_time).total_seconds()
            time_mins = time_diff / 60
            
            # Check if travel is physically impossible
            # Max speed: 900 km/h (commercial flight)
            max_possible_distance = (time_diff / 3600) * 900
            
            if distance_km > max_possible_distance and distance_km > 100:
                impossible_travel = True
                risk_score += 0.8
        
        # Update location
        self.user_locations[user_id] = {
            'lat': current_lat,
            'lon': current_lon,
            'timestamp': timestamp,
            'ip': current_ip
        }
        
        return {
            'risk_score': min(risk_score, 1.0),
            'impossible_travel': impossible_travel,
            'is_vpn': is_vpn,
            'is_proxy': is_proxy,
            'is_tor': is_tor,
            'distance_km': distance_km,
            'time_mins': time_mins
        }
    
    def _check_ip_reputation(self, ip_address: str) -> Dict[str, Any]:
        """Check IP reputation (VPN, proxy, Tor detection)"""
        # TODO: Integrate with IP intelligence services (IPQualityScore, MaxMind, etc.)
        # For now, basic heuristics
        
        # Common VPN/proxy detection
        is_vpn = False
        is_proxy = False
        is_tor = False
        
        # Simple heuristic: check if IP is in known datacenter ranges
        # (Real implementation would use IP intelligence APIs)
        
        return {
            'is_vpn': is_vpn,
            'is_proxy': is_proxy,
            'is_tor': is_tor,
            'reputation_score': 0.7  # 0 = bad, 1 = good
        }
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in km"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth radius in km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c


class MerchantRiskScorer:
    """Scores merchant risk based on chargeback rates, fraud history, category"""
    
    def __init__(self):
        # Merchant reputation database (use real DB in production)
        self.merchant_db = {}
        
        # High-risk merchant categories
        self.high_risk_categories = {
            'cryptocurrency': 0.9,
            'gambling': 0.85,
            'forex_trading': 0.8,
            'electronics': 0.6,
            'jewellery': 0.7,
            'gift_cards': 0.75,
            'money_transfer': 0.65
        }
    
    def score_merchant(
        self, 
        merchant_id: str, 
        merchant_category: str,
        amount: float
    ) -> Dict[str, Any]:
        """Calculate merchant risk score"""
        
        risk_score = 0.0
        risk_reason = ""
        is_high_risk = False
        
        # Category-based risk
        category_key = merchant_category.lower().replace(' ', '_')
        category_risk = self.high_risk_categories.get(category_key, 0.1)
        risk_score += category_risk * 0.6
        
        # Check merchant reputation
        if merchant_id in self.merchant_db:
            merchant_data = self.merchant_db[merchant_id]
            
            # Chargeback rate
            chargeback_rate = merchant_data.get('chargeback_rate', 0.0)
            if chargeback_rate > 0.02:  # >2% chargebacks
                risk_score += 0.4
                risk_reason = f"HIGH_CHARGEBACK_RATE: {chargeback_rate:.1%}"
                is_high_risk = True
            
            # Fraud rate
            fraud_rate = merchant_data.get('fraud_rate', 0.0)
            if fraud_rate > 0.01:  # >1% fraud
                risk_score += 0.3
                risk_reason = f"HIGH_FRAUD_RATE: {fraud_rate:.1%}"
                is_high_risk = True
        
        # New merchant risk
        if merchant_id not in self.merchant_db:
            risk_score += 0.2
            risk_reason = "NEW_MERCHANT"
        
        # Category-based high risk
        if category_risk >= 0.6:
            is_high_risk = True
            risk_reason = f"HIGH_RISK_CATEGORY: {merchant_category}"
        
        return {
            'risk_score': min(risk_score, 1.0),
            'is_high_risk': is_high_risk,
            'risk_reason': risk_reason,
            'category_risk': category_risk
        }


# Singleton instance
_engine = None

def get_pre_auth_engine() -> PreAuthEngine:
    """Get singleton PreAuthEngine instance"""
    global _engine
    if _engine is None:
        _engine = PreAuthEngine()
    return _engine
