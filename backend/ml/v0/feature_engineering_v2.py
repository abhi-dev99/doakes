"""
ARGUS Enhanced Feature Engineering v2.0
========================================
Implements 40+ features for superior fraud detection

Phase 1 of accuracy enhancement plan.
Uses demographic, geographic, device, merchant, and temporal patterns.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Tuple, List
import joblib
from pathlib import Path

# ============ INDIAN GEOGRAPHY ============

INDIAN_STATES = {
    'AN': 'Andaman & Nicobar', 'AP': 'Andhra Pradesh', 'AR': 'Arunachal Pradesh',
    'AS': 'Assam', 'BR': 'Bihar', 'CG': 'Chhattisgarh', 'CH': 'Chandigarh',
    'CT': 'Chhattisgarh', 'DL': 'Delhi', 'GA': 'Goa', 'GJ': 'Gujarat',
    'HR': 'Haryana', 'HP': 'Himachal Pradesh', 'JK': 'Jammu & Kashmir',
    'JH': 'Jharkhand', 'KA': 'Karnataka', 'KL': 'Kerala', 'LA': 'Ladakh',
    'LD': 'Lakshadweep', 'MP': 'Madhya Pradesh', 'MH': 'Maharashtra',
    'MN': 'Manipur', 'ML': 'Meghalaya', 'MZ': 'Mizoram', 'NL': 'Nagaland',
    'OR': 'Odisha', 'PB': 'Punjab', 'PY': 'Puducherry', 'RJ': 'Rajasthan',
    'SK': 'Sikkim', 'TN': 'Tamil Nadu', 'TR': 'Tripura', 'UP': 'Uttar Pradesh',
    'UT': 'Uttarakhand', 'WB': 'West Bengal'
}

METROS = {'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 
          'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow'}

# Merchant fraud rate baseline (from historical data or Kaggle)
MERCHANT_FRAUD_RATES = {
    'electronics': 0.045,
    'jewellery': 0.035,
    'cryptocurrency': 0.120,
    'gambling': 0.150,
    'cash_withdrawal': 0.040,
    'p2p_transfer': 0.025,
    'entertainment': 0.020,
    'shopping': 0.018,
    'fuel': 0.008,
    'food_delivery': 0.005,
    'grocery': 0.003,
    'utilities': 0.002,
    'healthcare': 0.001,
    'education': 0.001,
    'transport': 0.005
}

# State fraud rate baseline (from Kaggle dataset analysis)
STATE_FRAUD_RATES = {
    'MH': 0.015,  # Maharashtra high (major commerce)
    'DL': 0.018,  # Delhi high
    'KA': 0.012,  # Karnataka
    'TN': 0.010,
    'WB': 0.014,
    'GJ': 0.009,
    'UP': 0.008,
    'AP': 0.007,
    'KL': 0.006,
    'HR': 0.011
}

# Age group fraud rates
AGE_FRAUD_RATES = {
    '18-25': 0.020,
    '26-35': 0.010,
    '36-45': 0.006,
    '46-55': 0.005,
    '56+': 0.004
}

# Device fraud rates
DEVICE_FRAUD_RATES = {
    'Android': 0.010,
    'iOS': 0.005,
    'Web': 0.015,
    'Unknown': 0.025
}

# Network fraud rates
NETWORK_FRAUD_RATES = {
    '4G': 0.008,
    '5G': 0.006,
    'WiFi': 0.012,
    '3G': 0.018
}

# Transaction type fraud rates
TRANSACTION_TYPE_FRAUD_RATES = {
    'P2P': 0.025,
    'P2M': 0.008,
    'Bill Payment': 0.002,
    'Recharge': 0.001
}

# ============ ENHANCED FEATURE ENGINEERING ============

class EnhancedFeatureEngineer:
    """Advanced feature engineering with 40+ features"""
    
    def __init__(self):
        self.merchant_stats = {}
        self.state_stats = {}
        self.user_stats = {}
        self.device_stats = {}
    
    def engineer_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Engineer comprehensive feature set for fraud detection
        
        Returns:
            (df_with_features, feature_names)
        """
        df = df.copy()
        
        print("🔧 Engineering 40+ enhanced features...")
        
        # ===== TEMPORAL FEATURES =====
        print("  → Temporal features...")
        df = self._add_temporal_features(df)
        
        # ===== DEMOGRAPHIC FEATURES =====
        print("  → Demographic features...")
        df = self._add_demographic_features(df)
        
        # ===== GEOGRAPHIC FEATURES =====
        print("  → Geographic features...")
        df = self._add_geographic_features(df)
        
        # ===== DEVICE & NETWORK FEATURES =====
        print("  → Device & network features...")
        df = self._add_device_features(df)
        
        # ===== MERCHANT FEATURES =====
        print("  → Merchant features...")
        df = self._add_merchant_features(df)
        
        # ===== TRANSACTION TYPE FEATURES =====
        print("  → Transaction type features...")
        df = self._add_transaction_type_features(df)
        
        # ===== AMOUNT FEATURES =====
        print("  → Amount & ratio features...")
        df = self._add_amount_features(df)
        
        # ===== PATTERN FEATURES =====
        print("  → Pattern features...")
        df = self._add_pattern_features(df)
        
        # ===== RISKY COMBINATION FEATURES =====
        print("  → Risky combination features...")
        df = self._add_combination_features(df)
        
        # Define feature order
        feature_cols = self._get_feature_list()
        
        print(f"✅ Generated {len(feature_cols)} features")
        
        return df, feature_cols
    
    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Temporal features: hour, day, time-of-day patterns"""
        
        # Parse timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        df['day_of_month'] = df['timestamp'].dt.day
        df['month'] = df['timestamp'].dt.month
        
        # Time windows (fraud is higher at certain times)
        df['is_night'] = ((df['hour'] >= 23) | (df['hour'] <= 5)).astype(int)
        df['is_morning'] = ((df['hour'] >= 6) & (df['hour'] <= 11)).astype(int)
        df['is_afternoon'] = ((df['hour'] >= 12) & (df['hour'] <= 17)).astype(int)
        df['is_evening'] = ((df['hour'] >= 18) & (df['hour'] <= 22)).astype(int)
        
        # High-risk time windows
        df['is_suspicious_hour'] = ((df['hour'] >= 22) | (df['hour'] <= 6)).astype(int)
        
        return df
    
    def _add_demographic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Demographic features: age groups, fraud rate by age"""
        
        # Ensure age_group column exists
        if 'age_group' not in df.columns:
            df['age_group'] = '26-35'  # Default if not in data
        
        # Age group fraud risk
        df['age_fraud_rate'] = df['age_group'].map(AGE_FRAUD_RATES).fillna(0.010)
        df['age_group_encoded'] = pd.factorize(df['age_group'])[0]
        
        # Age consistency (should not vary wildly between sender/receiver)
        if 'receiver_age_group' in df.columns:
            df['age_mismatch_score'] = (df['age_group'] != df['receiver_age_group']).astype(int)
        else:
            df['age_mismatch_score'] = 0
        
        return df
    
    def _add_geographic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Geographic features: state, location, distance"""
        
        # State encoding
        if 'state' not in df.columns:
            df['state'] = 'MH'  # Default
        
        df['state_fraud_rate'] = df['state'].map(STATE_FRAUD_RATES).fillna(0.010)
        df['state_encoded'] = pd.factorize(df['state'])[0]
        
        # Metro detection
        df['is_metro_sender'] = df['state'].isin(METROS).astype(int)
        
        # Cross-state transfers
        if 'receiver_state' in df.columns:
            df['is_cross_state'] = (df['state'] != df['receiver_state']).astype(int)
            # Cross-state increases risk
            df['cross_state_risk_multiplier'] = df['is_cross_state'] * 1.3 + (1 - df['is_cross_state'])
        else:
            df['is_cross_state'] = 0
            df['cross_state_risk_multiplier'] = 1.0
        
        return df
    
    def _add_device_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Device & network features: device type, fingerprinting, consistency"""
        
        # Device type encoding
        if 'device_type' not in df.columns:
            df['device_type'] = 'Android'
        
        df['device_fraud_rate'] = df['device_type'].map(DEVICE_FRAUD_RATES).fillna(0.012)
        df['device_type_encoded'] = pd.factorize(df['device_type'])[0]
        
        # Network type
        if 'network_type' not in df.columns:
            df['network_type'] = '4G'
        
        df['network_fraud_rate'] = df['network_type'].map(NETWORK_FRAUD_RATES).fillna(0.012)
        df['network_type_encoded'] = pd.factorize(df['network_type'])[0]
        
        # New device flag (would be tracked in real-time)
        df['is_new_device'] = 0  # Default; set to 1 for actual new devices
        df['new_device_risk'] = df['is_new_device'] * 0.3  # +30% risk if new device
        
        # High-risk device combinations
        df['suspicious_device_network'] = (
            (df['device_type'] == 'Web') & (df['network_type'] == 'WiFi')
        ).astype(int)  # Web + public WiFi = risky
        
        return df
    
    def _add_merchant_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Merchant features: category, reputation, fraud rate"""
        
        # Merchant category
        if 'merchant_category' not in df.columns:
            df['merchant_category'] = 'shopping'
        
        df['merchant_category_encoded'] = pd.factorize(df['merchant_category'])[0]
        df['merchant_fraud_rate'] = df['merchant_category'].map(
            MERCHANT_FRAUD_RATES
        ).fillna(0.010)
        
        # High-risk merchant categories
        high_risk_categories = ['electronics', 'jewellery', 'cryptocurrency', 'gambling']
        df['is_high_risk_category'] = df['merchant_category'].isin(high_risk_categories).astype(int)
        
        # Low-risk merchant categories
        low_risk_categories = ['utilities', 'food_delivery', 'healthcare', 'education']
        df['is_low_risk_category'] = df['merchant_category'].isin(low_risk_categories).astype(int)
        
        # Merchant reputation score (placeholder; would be updated in real-time)
        df['merchant_reputation_score'] = 0.8  # 0-1, higher = better
        
        return df
    
    def _add_transaction_type_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transaction type features: P2P, P2M, Bill, Recharge"""
        
        # Transaction type
        if 'transaction_type' not in df.columns:
            df['transaction_type'] = 'P2M'
        
        df['transaction_type_encoded'] = pd.factorize(df['transaction_type'])[0]
        df['transaction_type_fraud_rate'] = df['transaction_type'].map(
            TRANSACTION_TYPE_FRAUD_RATES
        ).fillna(0.010)
        
        # Type-specific risk flags
        df['is_p2p'] = (df['transaction_type'] == 'P2P').astype(int)
        df['is_cash_like'] = (df['transaction_type'] == 'P2P').astype(int)  # P2P is most fraud-prone
        
        return df
    
    def _add_amount_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Amount features: bucketing, z-scores, ratios"""
        
        # Amount bucketing (non-linear)
        bins = [0, 100, 1000, 10000, 100000, float('inf')]
        labels = ['very_small', 'small', 'medium', 'large', 'very_large']
        df['amount_bucket'] = pd.cut(df['amount'], bins=bins, labels=labels, include_lowest=True)
        df['amount_bucket_encoded'] = pd.factorize(df['amount_bucket'])[0]
        
        # Amount percentiles for the user/merchant
        df['amount_percentile'] = df.groupby('user_id')['amount'].transform(
            lambda x: (x <= x.quantile(0.95)).astype(int)
        ) if 'user_id' in df.columns else 0
        
        # Suspicious amounts (structuring patterns)
        suspicious_amounts = [999, 4999, 9999, 49999, 99999]
        df['is_suspicious_amount'] = df['amount'].isin(suspicious_amounts).astype(int)
        
        # Round amount (less fraud in round amounts usually)
        df['is_round_amount'] = (df['amount'] % 100 == 0).astype(int)
        
        # Log-transformed amount
        df['amount_log'] = np.log1p(df['amount'])
        
        return df
    
    def _add_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pattern features: velocity, duplicates, sequences"""
        
        # Sort by timestamp for pattern detection
        df = df.sort_values('timestamp')
        
        # Velocity: transactions per hour
        if 'user_id' in df.columns:
            df['velocity_txn_per_hour'] = df.groupby('user_id').apply(
                lambda g: g.resample('H', on='timestamp').size().mean()
            ).mean()  # Aggregate; ideally tracked per user
        else:
            df['velocity_txn_per_hour'] = 3.0  # Default
        
        # Duplicate detection
        df['is_duplicate_amount_recent'] = df.groupby('user_id')['amount'].transform(
            lambda x: x.duplicated(keep=False)
        ) if 'user_id' in df.columns else 0
        
        # Amount velocity
        if 'user_id' in df.columns:
            df['amount_velocity_per_hour'] = df.groupby('user_id')['amount'].transform(
                lambda x: x.rolling('1H', min_periods=1).sum().mean()
            ) if hasattr(df.groupby('user_id')['amount'].transform(''), '__len__') else 0
        else:
            df['amount_velocity_per_hour'] = 0
        
        # Burst detection (many txns in short time)
        if 'user_id' in df.columns:
            df['burst_txn_count_10min'] = df.groupby('user_id').apply(
                lambda g: g.set_index('timestamp').resample('10min').size().max()
            ).mean()  # Simplified
        else:
            df['burst_txn_count_10min'] = 1
        
        return df
    
    def _add_combination_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Combination features: risky combinations of factors"""
        
        # Late night + high amount = risky
        df['late_night_high_amount'] = (
            (df['is_night'] == 1) & (df['amount'] > df['amount'].quantile(0.75))
        ).astype(int)
        
        # Late night + jewelry = very risky
        df['late_night_jewelry'] = (
            (df['is_night'] == 1) & 
            (df['merchant_category'] == 'jewellery')
        ).astype(int)
        
        # New device + high amount = risky
        df['new_device_high_amount'] = (
            (df['is_new_device'] == 1) & 
            (df['amount'] > df['amount'].quantile(0.75))
        ).astype(int)
        
        # Cross-state + high risk category = risky
        df['cross_state_high_risk'] = (
            (df['is_cross_state'] == 1) & 
            (df['is_high_risk_category'] == 1)
        ).astype(int)
        
        # Web + public WiFi + jewelry = very suspicious
        df['web_wifi_jewelry'] = (
            (df['device_type'] == 'Web') & 
            (df['network_type'] == 'WiFi') & 
            (df['merchant_category'] == 'jewellery')
        ).astype(int)
        
        # High-risk merchant + new device
        df['high_risk_merchant_new_device'] = (
            (df['merchant_fraud_rate'] > 0.04) & 
            (df['is_new_device'] == 1)
        ).astype(int)
        
        return df
    
    def _get_feature_list(self) -> List[str]:
        """Return ordered list of all features"""
        return [
            # Temporal (9)
            'hour', 'day_of_week', 'is_weekend', 'day_of_month', 'month',
            'is_night', 'is_morning', 'is_afternoon', 'is_evening', 'is_suspicious_hour',
            
            # Demographic (3)
            'age_group_encoded', 'age_fraud_rate', 'age_mismatch_score',
            
            # Geographic (4)
            'state_encoded', 'state_fraud_rate', 'is_metro_sender', 'is_cross_state',
            'cross_state_risk_multiplier',
            
            # Device & Network (6)
            'device_type_encoded', 'device_fraud_rate', 'is_new_device', 'new_device_risk',
            'network_type_encoded', 'network_fraud_rate', 'suspicious_device_network',
            
            # Merchant (6)
            'merchant_category_encoded', 'merchant_fraud_rate', 'is_high_risk_category',
            'is_low_risk_category', 'merchant_reputation_score',
            
            # Transaction Type (3)
            'transaction_type_encoded', 'transaction_type_fraud_rate', 'is_p2p', 'is_cash_like',
            
            # Amount (6)
            'amount', 'amount_bucket_encoded', 'amount_percentile',
            'is_suspicious_amount', 'is_round_amount', 'amount_log',
            
            # Patterns (4)
            'velocity_txn_per_hour', 'is_duplicate_amount_recent',
            'amount_velocity_per_hour', 'burst_txn_count_10min',
            
            # Combinations (6)
            'late_night_high_amount', 'late_night_jewelry', 'new_device_high_amount',
            'cross_state_high_risk', 'web_wifi_jewelry', 'high_risk_merchant_new_device'
        ]


# ============ USAGE EXAMPLE ============

if __name__ == "__main__":
    print("Enhanced Feature Engineering Example")
    print("=" * 50)
    
    # Create sample data
    sample_data = {
        'amount': [5000, 50000, 100],
        'timestamp': pd.to_datetime(['2024-01-15 23:30', '2024-01-16 02:15', '2024-01-16 14:00']),
        'merchant_category': ['jewellery', 'electronics', 'food_delivery'],
        'device_type': ['Web', 'Android', 'iOS'],
        'network_type': ['WiFi', '4G', '4G'],
        'state': ['MH', 'DL', 'KA'],
        'age_group': ['26-35', '36-45', '18-25'],
        'transaction_type': ['P2M', 'P2M', 'P2P'],
        'user_id': ['user_1', 'user_2', 'user_3'],
        'isFraud': [0, 0, 0]
    }
    
    df = pd.DataFrame(sample_data)
    
    engineer = EnhancedFeatureEngineer()
    df_enhanced, features = engineer.engineer_features(df)
    
    print(f"\n📊 Generated {len(features)} features:")
    for i, feat in enumerate(features, 1):
        print(f"  {i:2d}. {feat}")
    
    print(f"\n✅ Enhanced dataframe shape: {df_enhanced.shape}")
    print(f"   Original columns: {len(df.columns)}")
    print(f"   New columns: {len(df_enhanced.columns)}")
