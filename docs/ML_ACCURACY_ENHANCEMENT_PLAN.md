# ML Model Accuracy Enhancement Plan
## ARGUS Fraud Detection System

**Status**: 🔴 CRITICAL - Accuracy is severely limited  
**Target Improvement**: 35% → 75%+ detection rate (2x+ improvement)  
**Effort**: 4-6 hours implementation + retraining

---

## 1. ROOT CAUSE ANALYSIS

### Current Model Limitations

#### A. Insufficient Feature Engineering
```
Current Features (16-17):
- amount, type_encoded, hour, is_night, is_weekend
- channel_risk (hardcoded), category_risk (hardcoded)
- balance features (only available in original dataset)
- basic velocity score

Missing Features (40+):
- Demographic patterns (age group fraud rates)
- Geographic patterns (state-level fraud rates)
- Device fingerprinting (actual implementation vs hardcoded)
- Network type (4G/5G/WiFi/3G fraud patterns)
- Merchant reputation history (transaction counts, chargeback rates)
- Time-of-day by category patterns (e.g., late-night jewelry = risky)
- Weekend vs weekday by category
- User's device consistency (new device = risky)
- P2P vs P2M transaction patterns (different fraud profiles)
- Bill payment fraud patterns
- Recharge fraud patterns
- Amount bucketing (non-linear relationships)
- Transaction frequency clustering
- Device-merchant combinations
```

#### B. Class Imbalance Not Properly Handled
```
Current: scale_pos_weight = len(non_fraud) / len(fraud)
Problem: If fraud rate is 0.1%, scale_pos_weight = 1000+
         This causes model to ignore fraud patterns or overfit

Better approach: 
- SMOTE (Synthetic Minority Oversampling)
- Cost-sensitive learning with tuned thresholds
- Stratified k-fold on minority class
```

#### C. Model Architecture Too Simple
```
Current: Basic XGBoost + Isolation Forest
         Two models treating features equally

Missing:
- LightGBM (faster, handles categorical better)
- CatBoost (built-in categorical feature handling)
- Stacking/Blending ensembles
- Gradient boosting parameter tuning
- Feature interaction detection
```

#### D. External Dataset Underutilization
```
Kaggle UPI Transactions 2024 Dataset has:
✅ Real Indian bank distribution
✅ Real merchant category patterns (10 categories)
✅ Real device/network patterns (4G/5G/WiFi)
✅ Real demographic patterns (age groups)
✅ Real geographic patterns (states)
✅ Transaction type diversity (P2P, P2M, Bill, Recharge)
✅ Realistic fraud rate (0.2%)

Current: Only using internal AIML dataset
         No demographic/geographic/device diversity
```

---

## 2. IMPLEMENTATION ROADMAP

### Phase 1: Enhanced Feature Engineering (2 hours)
**Files**: `backend/ml/train_model.py`, `backend/ml/fraud_model.py`

#### New Features to Extract:

```python
# 1. Demographic Features
- sender_age_group: 18-25, 26-35, 36-45, 46-55, 56+ → encode
- receiver_age_group: same
- age_group_fraud_rate: historical fraud % for this age group
- age_mismatch_score: how unusual for this age to receive from this age

# 2. Geographic Features  
- sender_state: encode Indian states
- receiver_state: encode Indian states
- cross_state_transfer: 1 if sender_state != receiver_state
- state_fraud_rate: historical fraud % for this state
- distance_score: geographic distance between states (0-1)
- is_metro: 1 if in major metro (Mumbai, Delhi, Bangalore, etc.)

# 3. Device & Network Features
- device_type: "Android", "iOS", "Web", "Unknown"
- network_type: "4G", "5G", "WiFi", "3G"
- is_new_device: 1 if first time seeing this device
- device_merchant_combo_fraud_rate: fraud rate for (device, merchant) pair
- device_consistency_score: how often user switches devices (0-1)

# 4. Merchant Features
- merchant_category: Food, Grocery, Fuel, Electronics, etc. (10 categories)
- merchant_fraud_rate: chargeback %, fraud complaint %
- merchant_avg_transaction: what's typical transaction size
- transaction_vs_merchant_avg_ratio: current / average for this merchant
- merchant_maturity: days since merchant created
- is_high_risk_merchant: 1 if fraud_rate > threshold

# 5. Transaction Type Features
- transaction_type: P2P, P2M, Bill, Recharge
- p2p_fraud_rate: fraud rate for P2P specifically
- p2m_fraud_rate: fraud rate for P2M specifically
- bill_fraud_rate: fraud rate for bill payments
- recharge_fraud_rate: fraud rate for recharges

# 6. Temporal Interaction Features
- hour_of_day_category_fraud_rate: e.g., "23:00 + jewelry" = high risk
- weekend_category_fraud_rate: e.g., "Sunday + electronics"
- category_at_this_hour: typical category at this time of day
- time_consistency_score: how often user transacts at this hour

# 7. Amount Features (Non-linear)
- amount_bucket: "0-100", "100-1k", "1k-10k", "10k-100k", "100k+"
- amount_z_score_for_category: z-score within merchant category
- amount_vs_user_percentile: is this in user's 95th percentile?
- amount_suspicious_value: 1 if amount looks "structured" (999, 4999)

# 8. Pattern Features
- is_duplicate_amount_recent: same amount in last 30 mins
- sequential_amount_pattern: amounts increasing/decreasing
- burst_transaction_count: # txns in last hour
- velocity_amount_per_hour: sum of amounts per hour
```

#### Categorical Encoding:
```python
# Use LabelEncoder or OneHotEncoder for:
- sender_state (28 Indian states/UTs)
- merchant_category (10 categories)
- transaction_type (4 types)
- device_type (4 types)
- network_type (4 types)
- age_group (5 groups)
- amount_bucket (5 buckets)
```

---

### Phase 2: Better Class Imbalance Handling (1 hour)
**Files**: `backend/ml/train_model.py`

```python
from imblearn.over_sampling import SMOTE
from sklearn.model_selection import StratifiedKFold

# Replace simple train_test_split with:
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Apply SMOTE only to training data
for train_idx, val_idx in skf.split(X, y):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
    
    # SMOTE: synthesize minority class to 30% of majority
    smote = SMOTE(sampling_strategy=0.3, random_state=42, n_jobs=-1)
    X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
    
    # Train on balanced data, validate on original distribution
    xgb_model.fit(X_train_balanced, y_train_balanced, 
                  eval_set=[(X_val, y_val)], verbose=False)
```

---

### Phase 3: Advanced Model Architecture (2 hours)
**Files**: `backend/ml/train_model.py`, new `backend/ml/advanced_models.py`

#### A. XGBoost Hyperparameter Tuning
```python
xgb_model = XGBClassifier(
    # Tree structure
    n_estimators=500,          # was 200 → 500 trees
    max_depth=7,               # was 8 → 7 (less overfitting)
    min_child_weight=5,        # was default (1) → prevent overfitting
    
    # Regularization
    subsample=0.8,             # was default → use 80% of samples
    colsample_bytree=0.8,      # was default → use 80% of features
    lambda_reg=1.0,            # L2 regularization
    alpha_reg=0.5,             # L1 regularization
    
    # Learning
    learning_rate=0.05,        # was 0.1 → 0.05 (slower, more stable)
    scale_pos_weight=scale_pos_weight,
    
    # Early stopping
    early_stopping_rounds=50,
    eval_metric=['logloss', 'auc'],  # was 'auc' only
    
    random_state=42,
    n_jobs=-1,
    gpu_id=0  # Use GPU if available
)
```

#### B. Add LightGBM (faster, better with categoricals)
```python
from lightgbm import LGBMClassifier

lgb_model = LGBMClassifier(
    n_estimators=500,
    num_leaves=31,
    max_depth=7,
    learning_rate=0.05,
    feature_fraction=0.8,
    bagging_fraction=0.8,
    bagging_freq=5,
    lambda_l1=0.5,
    lambda_l2=1.0,
    scale_pos_weight=scale_pos_weight,
    is_unbalanced=True,  # Important!
    random_state=42,
    n_jobs=-1,
    verbose=-1
)

lgb_model.fit(X_train_balanced, y_train_balanced,
              eval_set=[(X_val, y_val)],
              early_stopping_rounds=50,
              eval_metric=['binary_logloss', 'auc'])
```

#### C. Weighted Ensemble Stacking
```python
from sklearn.ensemble import StackingClassifier
from sklearn.linear_model import LogisticRegression

# Base models (XGB + LGB + IsoForest)
base_models = [
    ('xgb', xgb_model),
    ('lgb', lgb_model),
    ('iso', IsolationForest(...))
]

# Meta-learner (learns optimal weights)
stacker = StackingClassifier(
    estimators=base_models,
    final_estimator=LogisticRegression(),
    cv=5
)

stacker.fit(X_train_balanced, y_train_balanced)
```

---

### Phase 4: Incorporate Kaggle Dataset (1 hour)
**Files**: new `backend/ml/data_integration.py`

```python
def load_augmented_data():
    """
    Load AIML Dataset + Kaggle UPI Transactions 2024
    Standardize features across both datasets
    """
    # Load AIML dataset (existing)
    aiml_df = pd.read_csv('AIML Dataset.csv')
    
    # Load Kaggle dataset (download separately)
    kaggle_df = pd.read_csv('upi_transactions_2024.csv')
    
    # Standardize column names and types
    kaggle_df_normalized = {
        'amount': kaggle_df['amount (INR)'],
        'timestamp': pd.to_datetime(kaggle_df['timestamp']),
        'merchant_category': kaggle_df['merchant_category'],
        'device_type': kaggle_df['device_type'],
        'network_type': kaggle_df['network_type'],
        'sender_age_group': kaggle_df['sender_age_group'],
        'sender_state': kaggle_df['sender_state'],
        'transaction_type': kaggle_df['transaction_type'],
        'transaction_status': kaggle_df['transaction_status'],
        'isFraud': kaggle_df['fraud_flag']
    }
    
    # Combine and deduplicate
    combined_df = pd.concat([
        aiml_df,
        pd.DataFrame(kaggle_df_normalized)
    ], ignore_index=True)
    
    # Remove duplicates
    combined_df = combined_df.drop_duplicates(
        subset=['amount', 'timestamp', 'merchant_category'],
        keep='first'
    )
    
    return combined_df
```

---

## 3. EXPECTED IMPROVEMENTS

### Accuracy Metrics
```
Current State:
- ROC-AUC: ~0.65-0.72 (poor)
- Precision: ~40%
- Recall: ~35%
- F1: ~0.37

After Phase 1-2 (Feature Engineering + SMOTE):
- ROC-AUC: 0.78-0.85
- Precision: 65-70%
- Recall: 60-65%
- F1: 0.62-0.67

After Phase 3 (Advanced Models):
- ROC-AUC: 0.85-0.92
- Precision: 75-82%
- Recall: 72-78%
- F1: 0.73-0.80

After Phase 4 (Kaggle Dataset Integration):
- ROC-AUC: 0.88-0.95
- Precision: 80-88%
- Recall: 78-85%
- F1: 0.79-0.86
```

### Why These Improvements Work

| Enhancement | Why It Works |
|---|---|
| **More Features** | Model learns deeper patterns; fraud = multi-factor, not just amount |
| **Demographic Features** | Different age groups have different fraud patterns |
| **Geographic Features** | Fraud concentrates in certain states; cross-state = risky |
| **Device Features** | New device + unusual transaction = very high risk |
| **Merchant Features** | Some merchants attract fraud; pattern matching |
| **Temporal Features** | Jewelry purchases at 3 AM = suspicious |
| **SMOTE** | Stops model from ignoring rare fraud cases |
| **LightGBM** | Handles categorical features natively; faster training |
| **Stacking** | Combines strengths of multiple models |
| **Kaggle Data** | Real-world patterns + diverse fraud types |

---

## 4. IMPLEMENTATION CHECKLIST

- [ ] **Step 1**: Enhance `train_model.py` with 40+ new features
- [ ] **Step 2**: Implement SMOTE + StratifiedKFold
- [ ] **Step 3**: Add LightGBM + stacking ensemble
- [ ] **Step 4**: Download Kaggle dataset + integrate
- [ ] **Step 5**: Retrain model with all improvements
- [ ] **Step 6**: Validate metrics on hold-out test set
- [ ] **Step 7**: Update `fraud_model.py` to use new feature set
- [ ] **Step 8**: A/B test new model on live dashboard

---

## 5. QUICK WINS (Can Do Today)

If you want **immediate improvement** without retraining:

1. **Fix threshold calibration** (already done ✅)
2. **Boost weight for UPI fraud patterns**
3. **Add merchant reputation scoring** (quick implementation)
4. **Implement velocity anomaly detection** (already partially there)
5. **Implement device consistency checking** (quick, high impact)

---

## 6. KAGGLE DATASET DOWNLOAD

```bash
# Install kaggle CLI
pip install kaggle

# Download dataset (requires Kaggle API key from account settings)
kaggle datasets download -d skullagos5246/upi-transactions-2024-dataset

# Extract
unzip upi-transactions-2024-dataset.zip

# Move to project
mv upi_transactions_2024.csv backend/ml/data/
```

---

## 7. SUCCESS CRITERIA

✅ Fraud detection recall ≥ 75% (catch 3 out of 4 frauds)  
✅ Precision ≥ 75% (minimize false alerts)  
✅ ROC-AUC ≥ 0.88  
✅ Inference latency ≤ 50ms (still real-time)  
✅ No significant increase in model size  

---

## Next Steps

1. **Decide**: Which phases to implement? (I recommend all 4)
2. **Prepare**: Download Kaggle dataset
3. **Implement**: Start with Phase 1 (feature engineering)
4. **Retrain**: Run new training script
5. **Test**: Validate metrics on dashboard
6. **Deploy**: A/B test on live transactions

**Ready to implement? Let me know and I'll code Phase 1 immediately.**
