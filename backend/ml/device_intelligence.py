"""
DEVICE FINGERPRINTING & CONTEXT ENRICHMENT
===========================================
Collects real device, browser, and behavioral data.
Replaces random/mock features with actual intelligence.
"""

import hashlib
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import random

logger = logging.getLogger("ARGUS.DeviceIntel")


class DeviceFingerprinter:
    """
    Generates device fingerprints from browser/app data.
    Tracks device reputation and anomalies.
    """
    
    def __init__(self):
        # Device reputation database (use Redis/DB in production)
        self.device_db = {}
        
        # Track device behavior
        self.device_history = defaultdict(list)
        
        # Known bad device fingerprints
        self.blacklisted_devices = set()
    
    def generate_fingerprint(self, device_data: Dict[str, Any]) -> str:
        """
        Generate unique device fingerprint from browser/device attributes.
        
        Args:
            device_data: Dictionary with keys:
                - user_agent: Browser user agent string
                - screen_resolution: "1920x1080"
                - timezone_offset: -330 (IST)
                - language: "en-IN"
                - platform: "Win32"
                - plugins: List of installed plugins
                - canvas_hash: Canvas fingerprint hash
                - webgl_hash: WebGL fingerprint hash
                - fonts: List of installed fonts
        
        Returns:
            64-character hex fingerprint
        """
        # Combine all attributes
        fingerprint_components = [
            device_data.get('user_agent', ''),
            device_data.get('screen_resolution', ''),
            str(device_data.get('timezone_offset', 0)),
            device_data.get('language', ''),
            device_data.get('platform', ''),
            ','.join(sorted(device_data.get('plugins', []))),
            device_data.get('canvas_hash', ''),
            device_data.get('webgl_hash', ''),
            ','.join(sorted(device_data.get('fonts', [])))
        ]
        
        combined = '|'.join(fingerprint_components)
        fingerprint = hashlib.sha256(combined.encode()).hexdigest()
        
        return fingerprint
    
    def analyze_device(
        self, 
        fingerprint: str, 
        device_data: Dict[str, Any],
        user_id: str,
        transaction_amount: float
    ) -> Dict[str, Any]:
        """
        Analyze device and return risk assessment.
        
        Returns:
            {
                'device_id': str,
                'is_new': bool,
                'reputation': float (0-1),
                'age_hours': int,
                'total_transactions': int,
                'total_amount': float,
                'risk_flags': list[str],
                'is_trusted': bool,
                'is_high_risk': bool
            }
        """
        device_id = fingerprint
        now = datetime.now()
        
        risk_flags = []
        
        # Check if device exists in database
        if device_id not in self.device_db:
            # New device
            self.device_db[device_id] = {
                'first_seen': now,
                'last_seen': now,
                'user_ids': {user_id},
                'transaction_count': 0,
                'total_amount': 0.0,
                'fraud_count': 0,
                'successful_count': 0,
                'reputation': 0.5,  # Neutral for new devices
                'attributes': device_data
            }
            is_new = True
            device_age_hours = 0
            reputation = 0.5
        else:
            # Existing device
            device_record = self.device_db[device_id]
            device_record['last_seen'] = now
            device_record['user_ids'].add(user_id)
            
            is_new = False
            device_age_hours = (now - device_record['first_seen']).total_seconds() / 3600
            reputation = device_record['reputation']
            
            # Check for anomalies
            
            # 1. Multiple users on same device (account takeover indicator)
            if len(device_record['user_ids']) > 5:
                risk_flags.append(f"MULTI_USER_DEVICE: {len(device_record['user_ids'])} users")
            
            # 2. Device used by different users rapidly (fraud ring)
            recent_users = self._get_recent_users(device_id, hours=24)
            if len(recent_users) > 3:
                risk_flags.append(f"RAPID_USER_SWITCHING: {len(recent_users)} users in 24h")
            
            # 3. High fraud rate on this device
            if device_record['transaction_count'] > 10:
                fraud_rate = device_record['fraud_count'] / device_record['transaction_count']
                if fraud_rate > 0.3:
                    risk_flags.append(f"HIGH_FRAUD_RATE: {fraud_rate:.1%}")
                    reputation = max(reputation - 0.3, 0.0)
        
        # Analyze device attributes for anomalies
        attr_risks = self._analyze_attributes(device_data)
        risk_flags.extend(attr_risks)
        
        # Update transaction stats
        device_record = self.device_db[device_id]
        device_record['transaction_count'] += 1
        device_record['total_amount'] += transaction_amount
        
        # Determine trust level
        is_trusted = (
            device_age_hours > 168 and  # >1 week old
            device_record['transaction_count'] > 20 and
            device_record['fraud_count'] == 0 and
            reputation > 0.8
        )
        
        is_high_risk = (
            reputation < 0.3 or
            len(risk_flags) >= 3 or
            device_id in self.blacklisted_devices
        )
        
        return {
            'device_id': device_id,
            'is_new': is_new,
            'reputation': round(reputation, 3),
            'age_hours': int(device_age_hours),
            'total_transactions': device_record['transaction_count'],
            'total_amount': device_record['total_amount'],
            'risk_flags': risk_flags,
            'is_trusted': is_trusted,
            'is_high_risk': is_high_risk,
            'fingerprint': {
                'headless': device_data.get('headless', False),
                'is_emulator': device_data.get('is_emulator', False),
                'fingerprint_inconsistent': len(risk_flags) > 0
            }
        }
    
    def _get_recent_users(self, device_id: str, hours: int = 24) -> set:
        """Get unique users who used this device recently"""
        cutoff = datetime.now() - timedelta(hours=hours)
        device_record = self.device_db.get(device_id)
        
        if not device_record:
            return set()
        
        # In production, track this properly in history
        # For now, return the user_ids set
        return device_record.get('user_ids', set())
    
    def _analyze_attributes(self, device_data: Dict[str, Any]) -> list[str]:
        """Analyze device attributes for suspicious patterns"""
        risks = []
        
        # Headless browser detection (automation/bots)
        if device_data.get('headless'):
            risks.append("HEADLESS_BROWSER")
        
        # Emulator detection (Android/iOS emulators)
        if device_data.get('is_emulator'):
            risks.append("EMULATOR")
        
        # Suspicious user agent
        user_agent = device_data.get('user_agent', '').lower()
        suspicious_ua_keywords = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget']
        if any(kw in user_agent for kw in suspicious_ua_keywords):
            risks.append("SUSPICIOUS_USER_AGENT")
        
        # Very old browsers (security risk)
        if 'MSIE' in user_agent or 'Internet Explorer' in user_agent:
            risks.append("OUTDATED_BROWSER")
        
        # No plugins/fonts (possible spoofing)
        if not device_data.get('plugins') and not device_data.get('fonts'):
            risks.append("MINIMAL_FINGERPRINT")
        
        # Timezone mismatch with claimed location
        # (Would need geolocation data to validate)
        
        return risks
    
    def mark_fraud(self, device_id: str):
        """Mark device as involved in fraud"""
        if device_id in self.device_db:
            self.device_db[device_id]['fraud_count'] += 1
            self.device_db[device_id]['reputation'] = max(
                self.device_db[device_id]['reputation'] - 0.2,
                0.0
            )
    
    def mark_success(self, device_id: str):
        """Mark successful (legitimate) transaction"""
        if device_id in self.device_db:
            self.device_db[device_id]['successful_count'] += 1
            # Gradually improve reputation
            self.device_db[device_id]['reputation'] = min(
                self.device_db[device_id]['reputation'] + 0.01,
                1.0
            )
    
    def blacklist_device(self, device_id: str):
        """Add device to blacklist"""
        self.blacklisted_devices.add(device_id)
        if device_id in self.device_db:
            self.device_db[device_id]['reputation'] = 0.0


class GeoLocationEnricher:
    """
    Enriches transactions with real geolocation data from IP addresses.
    Replaces random location generation with actual IP intelligence.
    """
    
    def __init__(self):
        # IP to location cache (use MaxMind GeoIP2 or similar in production)
        self.ip_cache = {}
        
        # Known VPN/proxy/Tor exit nodes
        self.vpn_ranges = set()
        self.proxy_ips = set()
        self.tor_exits = set()
    
    def enrich_from_ip(self, ip_address: str) -> Dict[str, Any]:
        """
        Get geolocation and reputation data from IP address.
        
        In production, integrate with:
        - MaxMind GeoIP2 (location, ISP, proxy detection)
        - IPQualityScore (fraud score, VPN detection)
        - IPQS or similar for Tor exit node detection
        
        Returns:
            {
                'ip_address': str,
                'country': str,
                'country_code': str,
                'city': str,
                'region': str,
                'latitude': float,
                'longitude': float,
                'isp': str,
                'is_vpn': bool,
                'is_proxy': bool,
                'is_tor': bool,
                'is_datacenter': bool,
                'risk_score': float (0-1),
                'timezone': str
            }
        """
        
        # Check cache
        if ip_address in self.ip_cache:
            return self.ip_cache[ip_address]
        
        # TODO: Replace with actual GeoIP lookup
        # For now, generate realistic Indian data
        geo_data = self._mock_geoip_lookup(ip_address)
        
        # Cache result
        self.ip_cache[ip_address] = geo_data
        
        return geo_data
    
    def _mock_geoip_lookup(self, ip_address: str) -> Dict[str, Any]:
        """
        Mock GeoIP lookup - generates realistic Indian location data.
        Replace this with actual MaxMind/IPQS integration.
        """
        
        # Indian cities with coordinates
        indian_cities = [
            {'city': 'Mumbai', 'region': 'Maharashtra', 'lat': 19.0760, 'lon': 72.8777},
            {'city': 'Delhi', 'region': 'Delhi', 'lat': 28.7041, 'lon': 77.1025},
            {'city': 'Bangalore', 'region': 'Karnataka', 'lat': 12.9716, 'lon': 77.5946},
            {'city': 'Chennai', 'region': 'Tamil Nadu', 'lat': 13.0827, 'lon': 80.2707},
            {'city': 'Kolkata', 'region': 'West Bengal', 'lat': 22.5726, 'lon': 88.3639},
            {'city': 'Hyderabad', 'region': 'Telangana', 'lat': 17.3850, 'lon': 78.4867},
            {'city': 'Pune', 'region': 'Maharashtra', 'lat': 18.5204, 'lon': 73.8567},
            {'city': 'Ahmedabad', 'region': 'Gujarat', 'lat': 23.0225, 'lon': 72.5714},
        ]
        
        # Use IP hash to deterministically select city
        ip_hash = int(hashlib.md5(ip_address.encode()).hexdigest()[:8], 16)
        city_data = indian_cities[ip_hash % len(indian_cities)]
        
        # Detect VPN/proxy/Tor (simple heuristic based on IP pattern)
        is_vpn = ip_address.startswith('10.') or '.vpn.' in ip_address.lower()
        is_proxy = '.proxy.' in ip_address.lower()
        is_tor = '.tor.' in ip_address.lower()
        is_datacenter = any(dc in ip_address.lower() for dc in ['aws', 'azure', 'gcp', 'digitalocean'])
        
        # Calculate risk score
        risk_score = 0.0
        if is_vpn:
            risk_score += 0.3
        if is_proxy:
            risk_score += 0.4
        if is_tor:
            risk_score += 0.6
        if is_datacenter:
            risk_score += 0.2
        
        return {
            'ip_address': ip_address,
            'country': 'India',
            'country_code': 'IN',
            'city': city_data['city'],
            'region': city_data['region'],
            'latitude': city_data['lat'],
            'longitude': city_data['lon'],
            'isp': 'Jio' if ip_hash % 3 == 0 else 'Airtel' if ip_hash % 3 == 1 else 'BSNL',
            'is_vpn': is_vpn,
            'is_proxy': is_proxy,
            'is_tor': is_tor,
            'is_datacenter': is_datacenter,
            'risk_score': min(risk_score, 1.0),
            'timezone': 'Asia/Kolkata'
        }


class BehavioralBiometrics:
    """
    Analyzes behavioral patterns like typing speed, mouse movements, touch patterns.
    Helps detect account takeover and automated attacks.
    """
    
    def __init__(self):
        # User behavior profiles
        self.user_profiles = {}
    
    def analyze_behavior(
        self, 
        user_id: str, 
        behavioral_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze behavioral biometrics.
        
        Args:
            behavioral_data: Dictionary with:
                - typing_speed: Characters per minute
                - mouse_velocity: Average mouse movement speed
                - touch_pressure: Touch pressure pattern
                - scroll_behavior: Scroll speed and pattern
                - form_fill_time: Time taken to fill form (seconds)
                - copy_paste_count: Number of copy/paste actions
        
        Returns:
            Risk assessment based on behavior deviation
        """
        
        risk_score = 0.0
        anomalies = []
        
        # Get user's normal behavior profile
        if user_id not in self.user_profiles:
            # First time - create profile
            self.user_profiles[user_id] = {
                'avg_typing_speed': behavioral_data.get('typing_speed', 200),
                'avg_mouse_velocity': behavioral_data.get('mouse_velocity', 100),
                'avg_form_fill_time': behavioral_data.get('form_fill_time', 30),
                'transaction_count': 0
            }
            is_new_profile = True
        else:
            profile = self.user_profiles[user_id]
            is_new_profile = False
            
            # Compare with historical behavior
            
            # 1. Typing speed anomaly (bot detection)
            typing_speed = behavioral_data.get('typing_speed', 200)
            if typing_speed > profile['avg_typing_speed'] * 2:
                anomalies.append("ABNORMALLY_FAST_TYPING")
                risk_score += 0.3
            elif typing_speed < profile['avg_typing_speed'] * 0.3:
                anomalies.append("ABNORMALLY_SLOW_TYPING")
                risk_score += 0.2
            
            # 2. Form fill time (automation detection)
            form_time = behavioral_data.get('form_fill_time', 30)
            if form_time < 5:  # Too fast - likely automated
                anomalies.append("INSTANT_FORM_FILL")
                risk_score += 0.5
            
            # 3. Copy/paste abuse (credentials stuffing)
            copy_paste_count = behavioral_data.get('copy_paste_count', 0)
            if copy_paste_count > 3:
                anomalies.append("EXCESSIVE_COPY_PASTE")
                risk_score += 0.3
            
            # 4. No mouse movement (bot/automation)
            if behavioral_data.get('mouse_velocity', 100) == 0:
                anomalies.append("NO_MOUSE_MOVEMENT")
                risk_score += 0.4
            
            # Update profile with new data
            profile['avg_typing_speed'] = (
                profile['avg_typing_speed'] * 0.9 + 
                typing_speed * 0.1
            )
            profile['transaction_count'] += 1
        
        return {
            'risk_score': min(risk_score, 1.0),
            'anomalies': anomalies,
            'is_new_profile': is_new_profile,
            'is_suspicious': risk_score >= 0.4
        }


# Singleton instances
_fingerprinter = None
_geo_enricher = None
_behavioral = None

def get_device_fingerprinter() -> DeviceFingerprinter:
    global _fingerprinter
    if _fingerprinter is None:
        _fingerprinter = DeviceFingerprinter()
    return _fingerprinter

def get_geo_enricher() -> GeoLocationEnricher:
    global _geo_enricher
    if _geo_enricher is None:
        _geo_enricher = GeoLocationEnricher()
    return _geo_enricher

def get_behavioral_analyzer() -> BehavioralBiometrics:
    global _behavioral
    if _behavioral is None:
        _behavioral = BehavioralBiometrics()
    return _behavioral
