"""Quick integration test for v4 engine."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ml'))
os.chdir(os.path.join(os.path.dirname(__file__), 'ml'))
from fraud_model import FraudDetectionEngine

engine = FraudDetectionEngine()

tests = [
    ("LEGIT (grocery)", {'user_id':'U001','amount':450,'channel':'upi','merchant_category':'Grocery',
        'city':'Mumbai','state':'MH','is_new_device':False,'is_new_location':False,
        'device_age_hours':2000,'location_distance_km':2,'merchant_risk_score':0.05,'account_age_days':365}),
    ("LEGIT (micro tea)", {'user_id':'U004','amount':15,'channel':'upi','merchant_category':'Tea/Snacks',
        'city':'Bangalore','state':'KA','is_new_device':False,'is_new_location':False,
        'device_age_hours':5000,'location_distance_km':0,'merchant_risk_score':0.02,'account_age_days':800}),
    ("FRAUD (account takeover)", {'user_id':'U002','amount':85000,'channel':'card_online',
        'merchant_category':'Electronics Online','city':'Ranchi','state':'JH','is_new_device':True,
        'is_new_location':True,'device_age_hours':3,'location_distance_km':1100,
        'merchant_risk_score':0.75,'account_age_days':200}),
    ("FRAUD (structuring)", {'user_id':'U003','amount':990000,'channel':'netbanking',
        'merchant_category':'Large Transfer','city':'Delhi','state':'DL','is_new_device':False,
        'is_new_location':False,'device_age_hours':3000,'location_distance_km':0,
        'merchant_risk_score':0.35,'account_age_days':500}),
    ("FRAUD (SIM swap)", {'user_id':'U005','amount':75000,'channel':'upi',
        'merchant_category':'P2P Transfer','city':'Guwahati','state':'AS','is_new_device':True,
        'is_new_location':True,'device_age_hours':1,'location_distance_km':1800,
        'merchant_risk_score':0.6,'account_age_days':400}),
]

print(f"\nARGUS v{engine.VERSION} Integration Test")
print("=" * 65)

for label, txn in tests:
    r = engine.analyze_transaction(txn)
    scores = r['model_scores']
    print(f"\n  {label}")
    print(f"    Score: {r['risk_score']:.4f} | Level: {r['risk_level']}")
    print(f"    XGB={scores['xgboost']:.4f} LGB={scores['lightgbm']:.4f} IF={scores['anomaly_detection']:.4f}")
    print(f"    Latency: {r['latency_ms']:.2f}ms")
    if r['triggered_rules']:
        print(f"    Rules: {r['triggered_rules'][:3]}")

print("\n" + "=" * 65)
print("  PASS" if engine.model_loaded else "  FAIL - models not loaded")
