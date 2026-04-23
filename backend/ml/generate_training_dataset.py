"""
ARGUS Training Dataset Generator v4.0
Generates 750K labeled Indian payment transactions with 12 fraud archetypes.
"""
import random, uuid, math, json, csv, sys, os
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from dataset_config import (
    INDIAN_CITIES, CITY_WEIGHTS, CHANNELS, CHANNEL_NAMES, CHANNEL_WEIGHTS,
    CATEGORY_AMOUNTS, CHANNEL_RISK, CATEGORY_RISK, REGULATORY_LIMITS,
    HOUR_WEIGHTS_NORMAL, HOUR_WEIGHTS_FRAUD, ATM_COMMON_AMOUNTS,
    ATM_AMOUNT_WEIGHTS, STRUCTURING_AMOUNTS, MULE_ROUND_AMOUNTS,
    is_valid_channel_category,
)

# ============ AMOUNT GENERATOR ============

def generate_amount(channel: str, category: str) -> float:
    min_a, max_a = CATEGORY_AMOUNTS.get(category, (100, 10000))
    ch = CHANNELS.get(channel, CHANNELS['upi'])
    min_a = max(min_a, ch['min'])
    max_a = min(max_a, ch['max'])

    if channel == 'atm':
        amt = random.choices(ATM_COMMON_AMOUNTS, weights=ATM_AMOUNT_WEIGHTS)[0]
        return float(min(amt, max_a))

    # Log-normal skewed toward lower amounts (realistic Indian distribution)
    median = (min_a + max_a) / 3.5
    sigma = 0.7
    amt = np.random.lognormal(mean=math.log(max(median, 1)), sigma=sigma)
    amt = np.clip(amt, min_a, max_a)

    # Round to realistic denominations
    if amt < 50:
        amt = round(amt)
    elif amt < 500:
        amt = round(amt / 5) * 5
    elif amt < 5000:
        amt = round(amt / 10) * 10
    elif amt < 50000:
        amt = round(amt / 50) * 50
    else:
        amt = round(amt / 100) * 100
    return float(amt)


# ============ USER POOL ============

def create_user_pool(n=2000):
    users = []
    for i in range(n):
        city = random.choices(INDIAN_CITIES, weights=CITY_WEIGHTS)[0]
        pref_channel = random.choices(CHANNEL_NAMES, weights=CHANNEL_WEIGHTS)[0]
        users.append({
            'user_id': f"USR{i:06d}",
            'home_city': city['name'], 'home_state': city['state'],
            'tier': city['tier'],
            'preferred_channel': pref_channel,
            'avg_monthly_spend': random.choice([5000,10000,15000,25000,40000,60000,80000]),
            'account_age_days': random.randint(30, 1200),
        })
    return users

def create_device_pool(n=800):
    devices = []
    for i in range(n):
        devices.append({
            'device_id': f"DEV{i:08d}",
            'device_type': random.choices(['android','ios','web'], weights=[0.72,0.20,0.08])[0],
            'age_days': random.randint(5, 800),
        })
    return devices


# ============ NORMAL TRANSACTION ============

def generate_normal_txn(user, device_pool, base_time):
    channel = random.choices(CHANNEL_NAMES, weights=CHANNEL_WEIGHTS)[0]
    ch_cfg = CHANNELS[channel]
    category = random.choice(ch_cfg['categories'])
    amount = generate_amount(channel, category)

    # Location: 82% home city
    if random.random() < 0.82:
        city = next((c for c in INDIAN_CITIES if c['name'] == user['home_city']), INDIAN_CITIES[0])
    else:
        city = random.choices(INDIAN_CITIES, weights=CITY_WEIGHTS)[0]

    device = random.choice(device_pool)
    is_new_device = random.random() < 0.04
    is_new_loc = city['name'] != user['home_city']

    # Distance calculation
    if is_new_loc:
        home = next((c for c in INDIAN_CITIES if c['name'] == user['home_city']), INDIAN_CITIES[0])
        dist = math.sqrt((city['lat']-home['lat'])**2 + (city['lon']-home['lon'])**2) * 111
    else:
        dist = random.uniform(0, 8)

    hour = random.choices(range(24), weights=HOUR_WEIGHTS_NORMAL)[0]
    day_offset = random.randint(0, 89)  # 90-day window
    ts = base_time - timedelta(days=day_offset, hours=random.randint(0,23)-hour, minutes=random.randint(0,59))
    ts = ts.replace(hour=hour, minute=random.randint(0,59), second=random.randint(0,59))

    return {
        'transaction_id': str(uuid.uuid4()),
        'user_id': user['user_id'],
        'merchant_id': f"MER{random.randint(100000,999999)}",
        'amount': amount,
        'channel': channel,
        'merchant_category': category,
        'transaction_type': 'debit',
        'city': city['name'],
        'state': city['state'],
        'country': 'IN',
        'timestamp': ts.isoformat(),
        'device_id': device['device_id'] if not is_new_device else f"DEV_NEW_{uuid.uuid4().hex[:6]}",
        'device_type': device['device_type'],
        'device_age_hours': device['age_days'] * 24 if not is_new_device else random.uniform(48, 5000),
        'is_new_device': is_new_device,
        'is_new_location': is_new_loc,
        'location_distance_km': round(dist, 1),
        'merchant_risk_score': round(random.uniform(0.02, 0.25), 3),
        'account_age_days': user['account_age_days'],
        'is_fraud': 0,
        'fraud_type': 'none',
    }


# ============ 12 FRAUD ARCHETYPES ============

FRAUD_ARCHETYPES = {
    'account_takeover':    0.20,
    'stolen_card':         0.15,
    'upi_collect_scam':    0.15,
    'digital_arrest':      0.10,
    'sim_swap':            0.10,
    'mule_account':        0.08,
    'velocity_attack':     0.07,
    'unusual_amount':      0.05,
    'qr_tampering':        0.03,
    'structuring':         0.03,
    'night_drain':         0.02,
    'cross_state_anomaly': 0.02,
}

def generate_fraud_txn(user, device_pool, base_time, fraud_type=None):
    if fraud_type is None:
        fraud_type = random.choices(
            list(FRAUD_ARCHETYPES.keys()),
            weights=list(FRAUD_ARCHETYPES.values())
        )[0]

    hour = random.choices(range(24), weights=HOUR_WEIGHTS_FRAUD)[0]
    day_offset = random.randint(0, 89)
    ts = base_time - timedelta(days=day_offset)
    ts = ts.replace(hour=hour, minute=random.randint(0,59), second=random.randint(0,59))

    # Pick a different city from user's home
    other_cities = [c for c in INDIAN_CITIES if c['name'] != user['home_city']]
    far_city = random.choice(other_cities)
    home = next((c for c in INDIAN_CITIES if c['name'] == user['home_city']), INDIAN_CITIES[0])
    dist = math.sqrt((far_city['lat']-home['lat'])**2 + (far_city['lon']-home['lon'])**2) * 111

    base = {
        'transaction_id': str(uuid.uuid4()),
        'user_id': user['user_id'],
        'merchant_id': f"MER{random.randint(100000,999999)}",
        'transaction_type': 'debit',
        'country': 'IN',
        'timestamp': ts.isoformat(),
        'account_age_days': user['account_age_days'],
        'is_fraud': 1,
        'fraud_type': fraud_type,
    }

    if fraud_type == 'account_takeover':
        ch = random.choice(['card_online', 'netbanking', 'upi'])
        cat = random.choice(CHANNELS[ch]['categories'])
        amt = generate_amount(ch, cat) * random.uniform(3, 8)
        amt = min(amt, CHANNELS[ch]['max'])
        base.update({
            'amount': round(amt, 2), 'channel': ch, 'merchant_category': cat,
            'city': far_city['name'], 'state': far_city['state'],
            'device_id': f"FRAUD_{uuid.uuid4().hex[:8]}",
            'device_type': random.choice(['android','web']),
            'device_age_hours': random.uniform(0, 12),
            'is_new_device': True, 'is_new_location': True,
            'location_distance_km': round(dist, 1),
            'merchant_risk_score': round(random.uniform(0.4, 0.85), 3),
        })

    elif fraud_type == 'stolen_card':
        ch = random.choice(['pos', 'card_online'])
        hi_cats = [c for c in CHANNELS[ch]['categories'] if c in ['Electronics','Electronics Online','Jewellery','E-commerce']]
        cat = random.choice(hi_cats or CHANNELS[ch]['categories'])
        base.update({
            'amount': round(random.uniform(15000, CHANNELS[ch]['max']*0.8), 2),
            'channel': ch, 'merchant_category': cat,
            'city': far_city['name'], 'state': far_city['state'],
            'device_id': f"FRAUD_{uuid.uuid4().hex[:8]}",
            'device_type': 'android',
            'device_age_hours': random.uniform(0, 36),
            'is_new_device': True, 'is_new_location': random.random() < 0.7,
            'location_distance_km': round(dist * random.uniform(0.3, 1), 1),
            'merchant_risk_score': round(random.uniform(0.5, 0.9), 3),
        })

    elif fraud_type == 'upi_collect_scam':
        base.update({
            'amount': round(random.uniform(5000, 95000), 2),
            'channel': 'upi', 'merchant_category': 'P2P Transfer',
            'city': home['name'], 'state': home['state'],
            'device_id': random.choice(device_pool)['device_id'],
            'device_type': random.choice(['android','ios']),
            'device_age_hours': random.uniform(200, 5000),
            'is_new_device': False, 'is_new_location': False,
            'location_distance_km': 0,
            'merchant_risk_score': round(random.uniform(0.6, 0.95), 3),
        })

    elif fraud_type == 'digital_arrest':
        base.update({
            'amount': round(random.choices([50000,100000,200000,300000,500000], weights=[0.3,0.3,0.2,0.1,0.1])[0] * random.uniform(0.8,1.2), 2),
            'channel': random.choice(['upi','netbanking']),
            'merchant_category': 'P2P Transfer',
            'city': home['name'], 'state': home['state'],
            'device_id': random.choice(device_pool)['device_id'],
            'device_type': random.choice(['android','ios']),
            'device_age_hours': random.uniform(500, 8000),
            'is_new_device': False, 'is_new_location': False,
            'location_distance_km': 0,
            'merchant_risk_score': round(random.uniform(0.3, 0.7), 3),
        })

    elif fraud_type == 'sim_swap':
        ch = random.choice(['upi', 'netbanking'])
        base.update({
            'amount': round(random.uniform(25000, CHANNELS[ch]['max']*0.9), 2),
            'channel': ch, 'merchant_category': random.choice(['P2P Transfer','Large Transfer']),
            'city': far_city['name'], 'state': far_city['state'],
            'device_id': f"FRAUD_{uuid.uuid4().hex[:8]}",
            'device_type': 'android',
            'device_age_hours': random.uniform(0, 2),  # Brand new device
            'is_new_device': True, 'is_new_location': True,
            'location_distance_km': round(dist, 1),
            'merchant_risk_score': round(random.uniform(0.4, 0.8), 3),
        })

    elif fraud_type == 'mule_account':
        amt = random.choice(MULE_ROUND_AMOUNTS)
        ch = random.choice(['upi', 'netbanking'])
        base.update({
            'amount': float(amt), 'channel': ch,
            'merchant_category': random.choice(['P2P Transfer','Large Transfer']),
            'city': home['name'], 'state': home['state'],
            'device_id': random.choice(device_pool)['device_id'],
            'device_type': 'android',
            'device_age_hours': random.uniform(24, 500),
            'is_new_device': False, 'is_new_location': False,
            'location_distance_km': 0,
            'merchant_risk_score': round(random.uniform(0.3, 0.6), 3),
            'account_age_days': random.randint(5, 45),  # New account
        })

    elif fraud_type == 'velocity_attack':
        ch = random.choice(['upi', 'card_online'])
        cat = random.choice(CHANNELS[ch]['categories'])
        base.update({
            'amount': round(generate_amount(ch, cat) * random.uniform(1.5, 3), 2),
            'channel': ch, 'merchant_category': cat,
            'city': random.choices(INDIAN_CITIES, weights=CITY_WEIGHTS)[0]['name'],
            'state': random.choices(INDIAN_CITIES, weights=CITY_WEIGHTS)[0]['state'],
            'device_id': random.choice(device_pool)['device_id'],
            'device_type': random.choice(['android','ios','web']),
            'device_age_hours': random.uniform(24, 1000),
            'is_new_device': random.random() < 0.3,
            'is_new_location': random.random() < 0.4,
            'location_distance_km': round(random.uniform(0, 500), 1),
            'merchant_risk_score': round(random.uniform(0.3, 0.65), 3),
        })

    elif fraud_type == 'unusual_amount':
        ch = random.choices(CHANNEL_NAMES, weights=CHANNEL_WEIGHTS)[0]
        cat = random.choice(CHANNELS[ch]['categories'])
        base.update({
            'amount': round(CHANNELS[ch]['max'] * random.uniform(0.6, 0.95), 2),
            'channel': ch, 'merchant_category': cat,
            'city': home['name'], 'state': home['state'],
            'device_id': random.choice(device_pool)['device_id'],
            'device_type': random.choice(['android','ios']),
            'device_age_hours': random.uniform(200, 5000),
            'is_new_device': False, 'is_new_location': False,
            'location_distance_km': 0,
            'merchant_risk_score': round(random.uniform(0.3, 0.6), 3),
        })

    elif fraud_type == 'qr_tampering':
        base.update({
            'amount': round(random.uniform(2000, 30000), 2),
            'channel': 'upi', 'merchant_category': random.choice(['Local Shop','Retail Store','Restaurant']),
            'city': random.choices(INDIAN_CITIES, weights=CITY_WEIGHTS)[0]['name'],
            'state': random.choices(INDIAN_CITIES, weights=CITY_WEIGHTS)[0]['state'],
            'device_id': random.choice(device_pool)['device_id'],
            'device_type': random.choice(['android','ios']),
            'device_age_hours': random.uniform(100, 3000),
            'is_new_device': False, 'is_new_location': random.random() < 0.5,
            'location_distance_km': round(random.uniform(0, 200), 1),
            'merchant_risk_score': round(random.uniform(0.6, 0.95), 3),
        })

    elif fraud_type == 'structuring':
        amt = random.choice(STRUCTURING_AMOUNTS)
        base.update({
            'amount': float(amt), 'channel': 'netbanking',
            'merchant_category': random.choice(['Large Transfer','Investment','Business Payment']),
            'city': home['name'], 'state': home['state'],
            'device_id': random.choice(device_pool)['device_id'],
            'device_type': random.choice(['android','web']),
            'device_age_hours': random.uniform(500, 5000),
            'is_new_device': False, 'is_new_location': False,
            'location_distance_km': 0,
            'merchant_risk_score': round(random.uniform(0.2, 0.5), 3),
        })

    elif fraud_type == 'night_drain':
        ch = random.choice(['upi', 'netbanking'])
        ts2 = ts.replace(hour=random.choice([1,2,3,4]))
        base['timestamp'] = ts2.isoformat()
        base.update({
            'amount': round(random.uniform(10000, 90000), 2),
            'channel': ch, 'merchant_category': 'P2P Transfer',
            'city': home['name'], 'state': home['state'],
            'device_id': f"FRAUD_{uuid.uuid4().hex[:8]}",
            'device_type': 'android',
            'device_age_hours': random.uniform(0, 24),
            'is_new_device': True, 'is_new_location': False,
            'location_distance_km': 0,
            'merchant_risk_score': round(random.uniform(0.4, 0.8), 3),
        })

    elif fraud_type == 'cross_state_anomaly':
        ch = random.choice(['upi', 'card_online', 'pos'])
        cat = random.choice(CHANNELS[ch]['categories'])
        base.update({
            'amount': round(generate_amount(ch, cat) * random.uniform(2, 5), 2),
            'channel': ch, 'merchant_category': cat,
            'city': far_city['name'], 'state': far_city['state'],
            'device_id': random.choice(device_pool)['device_id'],
            'device_type': random.choice(['android','ios']),
            'device_age_hours': random.uniform(100, 3000),
            'is_new_device': False, 'is_new_location': True,
            'location_distance_km': round(dist, 1),
            'merchant_risk_score': round(random.uniform(0.3, 0.6), 3),
        })

    # Ensure all fields present
    for key in ['city','state','device_id','device_type','device_age_hours',
                'is_new_device','is_new_location','location_distance_km','merchant_risk_score']:
        if key not in base:
            base[key] = {'city':home['name'],'state':home['state'],
                         'device_id':f"DEV_{uuid.uuid4().hex[:6]}",
                         'device_type':'android','device_age_hours':100.0,
                         'is_new_device':True,'is_new_location':True,
                         'location_distance_km':500.0,'merchant_risk_score':0.5}.get(key)
    return base


# ============ MAIN GENERATOR ============

def generate_dataset(total=750000, fraud_rate=0.05, seed=42):
    """Generate the full dataset."""
    random.seed(seed)
    np.random.seed(seed)

    print(f"\n{'='*65}")
    print(f"  ARGUS TRAINING DATASET GENERATOR v4.0")
    print(f"  Generating {total:,} transactions ({fraud_rate*100:.1f}% fraud)")
    print(f"{'='*65}\n")

    users = create_user_pool(2000)
    devices = create_device_pool(800)
    base_time = datetime(2026, 4, 20, 12, 0, 0)
    n_fraud = int(total * fraud_rate)
    n_normal = total - n_fraud

    print(f"  Users: {len(users):,} | Devices: {len(devices):,}")
    print(f"  Normal: {n_normal:,} | Fraud: {n_fraud:,}\n")

    CSV_FIELDS = [
        'transaction_id','user_id','merchant_id','amount','channel',
        'merchant_category','transaction_type','city','state','country',
        'timestamp','device_id','device_type','device_age_hours',
        'is_new_device','is_new_location','location_distance_km',
        'merchant_risk_score','account_age_days','is_fraud','fraud_type',
    ]

    out_path = Path(__file__).parent.parent.parent / 'dataset' / 'argus_training_data.csv'
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fraud_counter = Counter()
    channel_counter = Counter()
    amount_stats = []

    print("  Generating transactions...")
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()

        # Generate fraud transactions
        for i in range(n_fraud):
            user = random.choice(users)
            txn = generate_fraud_txn(user, devices, base_time)
            writer.writerow({k: txn.get(k, '') for k in CSV_FIELDS})
            fraud_counter[txn['fraud_type']] += 1
            channel_counter[txn['channel']] += 1
            amount_stats.append(txn['amount'])
            if (i+1) % 5000 == 0:
                print(f"    Fraud: {i+1:,}/{n_fraud:,}", end='\r')

        print(f"    Fraud: {n_fraud:,}/{n_fraud:,} DONE")

        # Generate normal transactions
        for i in range(n_normal):
            user = random.choice(users)
            txn = generate_normal_txn(user, devices, base_time)
            writer.writerow({k: txn.get(k, '') for k in CSV_FIELDS})
            channel_counter[txn['channel']] += 1
            amount_stats.append(txn['amount'])
            if (i+1) % 50000 == 0:
                print(f"    Normal: {i+1:,}/{n_normal:,}", end='\r')

        print(f"    Normal: {n_normal:,}/{n_normal:,} DONE")

    amounts = np.array(amount_stats)
    file_mb = out_path.stat().st_size / (1024*1024)

    print(f"\n{'='*65}")
    print(f"  DATASET GENERATED SUCCESSFULLY")
    print(f"{'='*65}")
    print(f"  File: {out_path}")
    print(f"  Size: {file_mb:.1f} MB")
    print(f"  Total: {total:,} transactions")
    print(f"  Fraud: {n_fraud:,} ({n_fraud/total*100:.2f}%)")
    print(f"\n  Amount Distribution:")
    print(f"    Min:    Rs.{amounts.min():>12,.2f}")
    print(f"    Mean:   Rs.{amounts.mean():>12,.2f}")
    print(f"    Median: Rs.{np.median(amounts):>12,.2f}")
    print(f"    P95:    Rs.{np.percentile(amounts, 95):>12,.2f}")
    print(f"    Max:    Rs.{amounts.max():>12,.2f}")
    print(f"\n  Channel Distribution:")
    for ch, cnt in channel_counter.most_common():
        print(f"    {ch:15s}: {cnt:>8,} ({cnt/total*100:5.1f}%)")
    print(f"\n  Fraud Archetype Distribution:")
    for ft, cnt in fraud_counter.most_common():
        print(f"    {ft:25s}: {cnt:>6,} ({cnt/n_fraud*100:5.1f}%)")

    # Amount bracket analysis
    brackets = {
        'Micro (<=100)': sum(1 for a in amounts if a <= 100),
        'Small (101-1K)': sum(1 for a in amounts if 100 < a <= 1000),
        'Medium (1K-10K)': sum(1 for a in amounts if 1000 < a <= 10000),
        'Large (10K-1L)': sum(1 for a in amounts if 10000 < a <= 100000),
        'Very Large (>1L)': sum(1 for a in amounts if a > 100000),
    }
    print(f"\n  Amount Brackets:")
    for bracket, cnt in brackets.items():
        print(f"    {bracket:20s}: {cnt:>8,} ({cnt/total*100:5.1f}%)")

    print(f"\n{'='*65}\n")
    return str(out_path)


if __name__ == '__main__':
    generate_dataset()
