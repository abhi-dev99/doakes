"""
ARGUS Model Training Script
Trains on the AIML Dataset (6.3M transactions)
Uses stratified sampling for efficiency
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve
from xgboost import XGBClassifier
from sklearn.ensemble import IsolationForest
import joblib
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)
DATASET_PATH = BASE_DIR.parent.parent / "AIML Dataset.csv"

def load_and_preprocess(sample_size=500000):
    """Load dataset with stratified sampling for efficiency"""
    print(f"Loading dataset from {DATASET_PATH}...")
    
    # Read in chunks for memory efficiency
    chunks = []
    fraud_samples = []
    non_fraud_samples = []
    
    for chunk in pd.read_csv(DATASET_PATH, chunksize=500000):
        fraud = chunk[chunk['isFraud'] == 1]
        non_fraud = chunk[chunk['isFraud'] == 0]
        fraud_samples.append(fraud)
        non_fraud_samples.append(non_fraud)
    
    all_fraud = pd.concat(fraud_samples)
    all_non_fraud = pd.concat(non_fraud_samples)
    
    print(f"Total fraud cases: {len(all_fraud)}")
    print(f"Total non-fraud cases: {len(all_non_fraud)}")
    
    # Take all fraud cases + stratified sample of non-fraud
    # Use 1:10 ratio for balanced training (fraud:non-fraud)
    n_non_fraud = min(len(all_fraud) * 10, len(all_non_fraud), sample_size)
    non_fraud_sample = all_non_fraud.sample(n=n_non_fraud, random_state=42)
    
    df = pd.concat([all_fraud, non_fraud_sample]).sample(frac=1, random_state=42)
    print(f"Training set size: {len(df)}")
    print(f"Fraud ratio in training: {df['isFraud'].mean():.2%}")
    
    return df

def engineer_features(df):
    """Create fraud detection features"""
    df = df.copy()
    
    # Transaction type encoding
    type_encoder = LabelEncoder()
    df['type_encoded'] = type_encoder.fit_transform(df['type'])
    
    # Balance-based features
    df['balance_change_orig'] = df['newbalanceOrig'] - df['oldbalanceOrg']
    df['balance_change_dest'] = df['newbalanceDest'] - df['oldbalanceDest']
    
    # Ratio features (with safe division)
    df['amount_to_balance_ratio'] = np.where(
        df['oldbalanceOrg'] > 0,
        df['amount'] / df['oldbalanceOrg'],
        df['amount'] / 1  # If balance is 0, use amount as ratio
    )
    
    # Transaction drains account?
    df['drains_account'] = (df['newbalanceOrig'] == 0) & (df['oldbalanceOrg'] > 0)
    df['drains_account'] = df['drains_account'].astype(int)
    
    # Large transaction flag
    df['is_large_txn'] = (df['amount'] > df['amount'].quantile(0.95)).astype(int)
    
    # Suspicious patterns
    df['zero_dest_balance'] = (df['oldbalanceDest'] == 0).astype(int)
    df['full_amount_transfer'] = (abs(df['balance_change_orig'] + df['amount']) < 1).astype(int)
    
    # Amount buckets (log scale)
    df['amount_log'] = np.log1p(df['amount'])
    
    # Hour of day (from step - assuming step is hour)
    df['hour'] = df['step'] % 24
    df['is_night'] = ((df['hour'] >= 22) | (df['hour'] <= 5)).astype(int)
    
    # Type-specific risk
    high_risk_types = ['TRANSFER', 'CASH_OUT']
    df['is_high_risk_type'] = df['type'].isin(high_risk_types).astype(int)
    
    return df, type_encoder

def train_models(df, type_encoder):
    """Train XGBoost and Isolation Forest models"""
    
    feature_cols = [
        'type_encoded', 'amount', 'amount_log',
        'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest',
        'balance_change_orig', 'balance_change_dest',
        'amount_to_balance_ratio', 'drains_account', 'is_large_txn',
        'zero_dest_balance', 'full_amount_transfer',
        'hour', 'is_night', 'is_high_risk_type'
    ]
    
    X = df[feature_cols]
    y = df['isFraud']
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print("\n" + "="*50)
    print("Training XGBoost Classifier...")
    print("="*50)
    
    # XGBoost with class weights for imbalanced data
    scale_pos_weight = len(y_train[y_train==0]) / len(y_train[y_train==1])
    
    xgb_model = XGBClassifier(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        eval_metric='auc',
        random_state=42,
        n_jobs=-1
    )
    
    xgb_model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        verbose=True
    )
    
    # Evaluate XGBoost
    y_pred_proba = xgb_model.predict_proba(X_test_scaled)[:, 1]
    y_pred = (y_pred_proba > 0.5).astype(int)
    
    print("\nXGBoost Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Legit', 'Fraud']))
    print(f"ROC-AUC Score: {roc_auc_score(y_test, y_pred_proba):.4f}")
    
    # Find optimal threshold for high recall
    precision, recall, thresholds = precision_recall_curve(y_test, y_pred_proba)
    # Target 90% recall
    idx = np.argmin(np.abs(recall - 0.90))
    optimal_threshold = thresholds[idx] if idx < len(thresholds) else 0.5
    print(f"Optimal threshold for 90% recall: {optimal_threshold:.4f}")
    
    # Feature importance
    feature_importance = dict(zip(feature_cols, xgb_model.feature_importances_))
    print("\nTop 10 Feature Importances:")
    for feat, imp in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {feat}: {imp:.4f}")
    
    print("\n" + "="*50)
    print("Training Isolation Forest for Anomaly Detection...")
    print("="*50)
    
    # Train only on legitimate transactions for anomaly detection
    X_legit = X_train_scaled[y_train == 0]
    
    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=0.001,  # Expected fraud rate
        random_state=42,
        n_jobs=-1
    )
    iso_forest.fit(X_legit)
    
    # Save models
    print("\n" + "="*50)
    print("Saving models...")
    print("="*50)
    
    joblib.dump(xgb_model, MODELS_DIR / "xgb_model.joblib")
    joblib.dump(iso_forest, MODELS_DIR / "isolation_forest.joblib")
    joblib.dump(scaler, MODELS_DIR / "scaler.joblib")
    joblib.dump(type_encoder, MODELS_DIR / "type_encoder.joblib")
    joblib.dump(feature_cols, MODELS_DIR / "feature_cols.joblib")
    joblib.dump(optimal_threshold, MODELS_DIR / "optimal_threshold.joblib")
    joblib.dump(feature_importance, MODELS_DIR / "feature_importance.joblib")
    
    # Save model metadata
    metadata = {
        'version': '3.1.0-trained',
        'dataset_size': len(df),
        'fraud_ratio': float(df['isFraud'].mean()),
        'roc_auc': float(roc_auc_score(y_test, y_pred_proba)),
        'optimal_threshold': float(optimal_threshold),
        'feature_cols': feature_cols,
        'training_date': pd.Timestamp.now().isoformat()
    }
    joblib.dump(metadata, MODELS_DIR / "metadata.joblib")
    
    print(f"\nModels saved to {MODELS_DIR}")
    print(f"Model version: {metadata['version']}")
    print(f"ROC-AUC: {metadata['roc_auc']:.4f}")
    
    return xgb_model, iso_forest, scaler, feature_importance

if __name__ == "__main__":
    print("="*60)
    print("ARGUS Fraud Detection Model Training")
    print("="*60)
    
    # Load and preprocess
    df = load_and_preprocess(sample_size=100000)  # Use 100k for faster training
    
    # Feature engineering
    df, type_encoder = engineer_features(df)
    
    # Train models
    train_models(df, type_encoder)
    
    print("\n✅ Training complete!")
