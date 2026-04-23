"""
ARGUS Model Training v4.0
==========================
Trains XGBoost + LightGBM + IsolationForest ensemble on argus_training_data.csv.
Generates all evaluation plots. Uses Intel optimizations where available.

Usage:
    python train_model_v4.py
"""
import pandas as pd
import numpy as np
import joblib, json, time, sys, warnings
from pathlib import Path
from datetime import datetime

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, roc_auc_score, roc_curve,
    precision_recall_curve, confusion_matrix,
    f1_score, precision_score, recall_score, average_precision_score,
)
from sklearn.ensemble import IsolationForest
from sklearn.calibration import calibration_curve

warnings.filterwarnings('ignore')

# Try Intel accelerations
try:
    from sklearnex import patch_sklearn
    patch_sklearn()
    print("[INTEL] scikit-learn-intelex acceleration ENABLED")
except ImportError:
    print("[INFO] Install scikit-learn-intelex for Intel GPU/CPU acceleration")

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

try:
    from imblearn.over_sampling import SMOTE
    HAS_SMOTE = True
except ImportError:
    HAS_SMOTE = False
    print("[WARN] imblearn not installed, will use class_weight instead of SMOTE")

# Paths
BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "training_results"
DATASET_PATH = BASE_DIR.parent.parent / "dataset" / "argus_training_data.csv"
MODELS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Import feature extractor
sys.path.insert(0, str(BASE_DIR))
from feature_extractor import extract_features, FEATURE_NAMES, NUM_FEATURES


def load_and_extract_features():
    """Load dataset and extract 34 features for every row."""
    print(f"\n{'='*65}")
    print("  LOADING DATASET & EXTRACTING FEATURES")
    print(f"{'='*65}")

    df = pd.read_csv(DATASET_PATH)
    print(f"  Loaded {len(df):,} transactions from {DATASET_PATH.name}")
    print(f"  Fraud: {df.is_fraud.sum():,} ({df.is_fraud.mean()*100:.2f}%)")

    print(f"\n  Extracting {NUM_FEATURES} features per transaction...")
    t0 = time.time()

    features = np.zeros((len(df), NUM_FEATURES), dtype=np.float64)
    for i, (_, row) in enumerate(df.iterrows()):
        txn = row.to_dict()
        features[i] = extract_features(txn)
        if (i + 1) % 100000 == 0:
            print(f"    {i+1:,}/{len(df):,} ({(i+1)/len(df)*100:.0f}%)", end='\r')

    elapsed = time.time() - t0
    print(f"    {len(df):,}/{len(df):,} DONE in {elapsed:.1f}s ({len(df)/elapsed:.0f} txn/s)")

    y = df['is_fraud'].values
    fraud_types = df['fraud_type'].values
    channels = df['channel'].values

    return features, y, fraud_types, channels, df


def split_data(X, y, channels):
    """70/15/15 stratified split."""
    print(f"\n{'='*65}")
    print("  SPLITTING DATA (70/15/15 stratified)")
    print(f"{'='*65}")

    # First split: 70% train, 30% temp
    X_train, X_temp, y_train, y_temp, ch_train, ch_temp = train_test_split(
        X, y, channels, test_size=0.30, stratify=y, random_state=42
    )
    # Second split: temp → 50/50 = 15%/15% of total
    X_val, X_test, y_val, y_test, ch_val, ch_test = train_test_split(
        X_temp, y_temp, ch_temp, test_size=0.50, stratify=y_temp, random_state=42
    )

    for name, yy in [('Train', y_train), ('Validation', y_val), ('Test', y_test)]:
        print(f"  {name:12s}: {len(yy):>8,} ({yy.sum():,} fraud, {yy.mean()*100:.2f}%)")

    return X_train, X_val, X_test, y_train, y_val, y_test, ch_test


def train_models(X_train, X_val, y_train, y_val):
    """Train XGBoost + LightGBM + IsolationForest."""
    print(f"\n{'='*65}")
    print("  SCALING & BALANCING")
    print(f"{'='*65}")

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)

    # SMOTE on training set only
    if HAS_SMOTE:
        print("  Applying SMOTE (5% -> 30%)...")
        smote = SMOTE(sampling_strategy=0.30, random_state=42)
        X_train_bal, y_train_bal = smote.fit_resample(X_train_s, y_train)
        print(f"  After SMOTE: {len(y_train_bal):,} ({(y_train_bal==1).sum():,} fraud, {(y_train_bal==1).mean()*100:.1f}%)")
    else:
        X_train_bal, y_train_bal = X_train_s, y_train

    spw = (y_train_bal == 0).sum() / max((y_train_bal == 1).sum(), 1)

    # ===== XGBoost =====
    print(f"\n{'='*65}")
    print("  TRAINING XGBOOST (500 estimators)")
    print(f"{'='*65}")

    xgb = XGBClassifier(
        n_estimators=500, max_depth=8, min_child_weight=5,
        subsample=0.8, colsample_bytree=0.8,
        reg_lambda=1.0, reg_alpha=0.5,
        learning_rate=0.05, scale_pos_weight=spw,
        eval_metric='aucpr', random_state=42, n_jobs=-1, verbosity=0,
    )
    t0 = time.time()
    xgb.fit(X_train_bal, y_train_bal, eval_set=[(X_val_s, y_val)], verbose=False)
    xgb_time = time.time() - t0

    y_xgb_val = xgb.predict_proba(X_val_s)[:, 1]
    xgb_auc = roc_auc_score(y_val, y_xgb_val)
    xgb_ap = average_precision_score(y_val, y_xgb_val)
    print(f"  ROC-AUC: {xgb_auc:.4f} | AP: {xgb_ap:.4f} | Time: {xgb_time:.1f}s")

    # ===== LightGBM =====
    print(f"\n{'='*65}")
    print("  TRAINING LIGHTGBM (500 estimators)")
    print(f"{'='*65}")

    lgb = LGBMClassifier(
        n_estimators=500, num_leaves=63, max_depth=8,
        learning_rate=0.05, feature_fraction=0.8, bagging_fraction=0.8,
        bagging_freq=5, lambda_l1=0.5, lambda_l2=1.0,
        scale_pos_weight=spw,
        random_state=42, n_jobs=-1, verbose=-1,
    )
    t0 = time.time()
    lgb.fit(
        X_train_bal, y_train_bal,
        eval_set=[(X_val_s, y_val)],
        callbacks=[],
    )
    lgb_time = time.time() - t0

    y_lgb_val = lgb.predict_proba(X_val_s)[:, 1]
    lgb_auc = roc_auc_score(y_val, y_lgb_val)
    lgb_ap = average_precision_score(y_val, y_lgb_val)
    print(f"  ROC-AUC: {lgb_auc:.4f} | AP: {lgb_ap:.4f} | Time: {lgb_time:.1f}s")

    # ===== Isolation Forest =====
    print(f"\n{'='*65}")
    print("  TRAINING ISOLATION FOREST (legit-only)")
    print(f"{'='*65}")

    X_legit = X_train_bal[y_train_bal == 0]
    iso = IsolationForest(n_estimators=200, contamination=0.05, random_state=42, n_jobs=-1)
    t0 = time.time()
    iso.fit(X_legit)
    iso_time = time.time() - t0

    iso_raw = -iso.decision_function(X_val_s)
    y_iso_val = (iso_raw - iso_raw.min()) / (iso_raw.max() - iso_raw.min() + 1e-10)
    iso_auc = roc_auc_score(y_val, y_iso_val)
    print(f"  ROC-AUC: {iso_auc:.4f} | Time: {iso_time:.1f}s")

    return xgb, lgb, iso, scaler, {
        'xgb_auc': xgb_auc, 'lgb_auc': lgb_auc, 'iso_auc': iso_auc,
        'xgb_ap': xgb_ap, 'lgb_ap': lgb_ap,
        'xgb_time': xgb_time, 'lgb_time': lgb_time, 'iso_time': iso_time,
    }


def find_optimal_threshold(y_true, y_scores):
    """Find threshold that maximizes F1 on validation set."""
    prec, rec, thresholds = precision_recall_curve(y_true, y_scores)
    f1s = 2 * (prec * rec) / (prec + rec + 1e-10)
    idx = np.argmax(f1s)
    return float(thresholds[idx]) if idx < len(thresholds) else 0.5


def ensemble_predict(xgb, lgb, iso, scaler, X):
    """Weighted ensemble: XGB 40% + LGB 35% + IF 25%"""
    X_s = scaler.transform(X)
    y_xgb = xgb.predict_proba(X_s)[:, 1]
    y_lgb = lgb.predict_proba(X_s)[:, 1]
    iso_raw = -iso.decision_function(X_s)
    y_iso = (iso_raw - iso_raw.min()) / (iso_raw.max() - iso_raw.min() + 1e-10)
    return 0.40 * y_xgb + 0.35 * y_lgb + 0.25 * y_iso


def generate_plots(y_test, y_scores, y_pred, xgb, lgb, iso, scaler, X_test,
                   y_val, X_val, channels_test, fraud_types_all, y_all):
    """Generate all 12 evaluation plots."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    print(f"\n{'='*65}")
    print("  GENERATING EVALUATION PLOTS")
    print(f"{'='*65}")

    # Consistent style
    plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'ggplot')

    X_test_s = scaler.transform(X_test)

    # 1. ROC Curve (per model + ensemble)
    print("  [1/10] ROC Curve...")
    fig, ax = plt.subplots(figsize=(8, 6))
    for name, scores in [
        ('XGBoost', xgb.predict_proba(X_test_s)[:, 1]),
        ('LightGBM', lgb.predict_proba(X_test_s)[:, 1]),
        ('Ensemble', y_scores),
    ]:
        fpr, tpr, _ = roc_curve(y_test, scores)
        auc = roc_auc_score(y_test, scores)
        ax.plot(fpr, tpr, label=f'{name} (AUC={auc:.4f})', linewidth=2)
    ax.plot([0,1],[0,1],'k--',alpha=0.3)
    ax.set_xlabel('False Positive Rate'); ax.set_ylabel('True Positive Rate')
    ax.set_title('ROC Curve — ARGUS Fraud Detection Ensemble')
    ax.legend(loc='lower right'); plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'roc_curve.png', dpi=150); plt.close()

    # 2. Precision-Recall Curve
    print("  [2/10] Precision-Recall Curve...")
    fig, ax = plt.subplots(figsize=(8, 6))
    for name, scores in [
        ('XGBoost', xgb.predict_proba(X_test_s)[:, 1]),
        ('LightGBM', lgb.predict_proba(X_test_s)[:, 1]),
        ('Ensemble', y_scores),
    ]:
        prec, rec, _ = precision_recall_curve(y_test, scores)
        ap = average_precision_score(y_test, scores)
        ax.plot(rec, prec, label=f'{name} (AP={ap:.4f})', linewidth=2)
    ax.set_xlabel('Recall'); ax.set_ylabel('Precision')
    ax.set_title('Precision-Recall Curve'); ax.legend(); plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'pr_curve.png', dpi=150); plt.close()

    # 3. Confusion Matrix
    print("  [3/10] Confusion Matrix...")
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, cmap='Blues')
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f'{cm[i,j]:,}', ha='center', va='center',
                    fontsize=14, color='white' if cm[i,j] > cm.max()/2 else 'black')
    ax.set_xticks([0,1]); ax.set_yticks([0,1])
    ax.set_xticklabels(['Legit','Fraud']); ax.set_yticklabels(['Legit','Fraud'])
    ax.set_xlabel('Predicted'); ax.set_ylabel('Actual')
    ax.set_title('Confusion Matrix'); plt.colorbar(im); plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'confusion_matrix.png', dpi=150); plt.close()

    # 4. Score Distribution
    print("  [4/10] Score Distribution...")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(y_scores[y_test==0], bins=50, alpha=0.6, label=f'Legit (n={int((y_test==0).sum()):,})', color='#2ecc71')
    ax.hist(y_scores[y_test==1], bins=50, alpha=0.6, label=f'Fraud (n={int((y_test==1).sum()):,})', color='#e74c3c')
    ax.axvline(x=find_optimal_threshold(y_test, y_scores), color='black', linestyle='--', label='Threshold')
    ax.set_xlabel('Ensemble Score'); ax.set_ylabel('Count')
    ax.set_title('Score Distribution: Fraud vs Legitimate'); ax.legend(); plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'score_distribution.png', dpi=150); plt.close()

    # 5. Feature Importance (combined XGB + LGB)
    print("  [5/10] Feature Importance...")
    xgb_imp = xgb.feature_importances_
    lgb_imp = lgb.feature_importances_ / (lgb.feature_importances_.sum() + 1e-10)
    xgb_imp_n = xgb_imp / (xgb_imp.sum() + 1e-10)
    combined = (xgb_imp_n + lgb_imp) / 2
    top_idx = np.argsort(combined)[-20:]
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(range(len(top_idx)), combined[top_idx], color='#3498db')
    ax.set_yticks(range(len(top_idx)))
    ax.set_yticklabels([FEATURE_NAMES[i] for i in top_idx])
    ax.set_xlabel('Importance'); ax.set_title('Top 20 Feature Importance (XGB+LGB)')
    plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'feature_importance.png', dpi=150); plt.close()

    # 6. Threshold Analysis
    print("  [6/10] Threshold Analysis...")
    prec, rec, thresholds = precision_recall_curve(y_test, y_scores)
    f1s = 2 * (prec[:-1] * rec[:-1]) / (prec[:-1] + rec[:-1] + 1e-10)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(thresholds, prec[:-1], label='Precision', linewidth=2)
    ax.plot(thresholds, rec[:-1], label='Recall', linewidth=2)
    ax.plot(thresholds, f1s, label='F1', linewidth=2, linestyle='--')
    opt = thresholds[np.argmax(f1s)]
    ax.axvline(x=opt, color='red', linestyle=':', label=f'Optimal={opt:.3f}')
    ax.set_xlabel('Threshold'); ax.set_ylabel('Score')
    ax.set_title('Threshold Analysis'); ax.legend(); plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'threshold_analysis.png', dpi=150); plt.close()

    # 7. Per-Channel Performance
    print("  [7/10] Per-Channel Performance...")
    ch_metrics = {}
    for ch in sorted(set(channels_test)):
        mask = channels_test == ch
        if mask.sum() > 0 and y_test[mask].sum() > 0:
            ch_f1 = f1_score(y_test[mask], y_pred[mask], zero_division=0)
            ch_rec = recall_score(y_test[mask], y_pred[mask], zero_division=0)
            ch_prec = precision_score(y_test[mask], y_pred[mask], zero_division=0)
            ch_metrics[ch] = {'f1': ch_f1, 'recall': ch_rec, 'precision': ch_prec}
    fig, ax = plt.subplots(figsize=(10, 5))
    chs = list(ch_metrics.keys())
    x = range(len(chs))
    w = 0.25
    ax.bar([i-w for i in x], [ch_metrics[c]['precision'] for c in chs], w, label='Precision', color='#3498db')
    ax.bar(x, [ch_metrics[c]['recall'] for c in chs], w, label='Recall', color='#e74c3c')
    ax.bar([i+w for i in x], [ch_metrics[c]['f1'] for c in chs], w, label='F1', color='#2ecc71')
    ax.set_xticks(x); ax.set_xticklabels(chs, rotation=30)
    ax.set_ylabel('Score'); ax.set_title('Per-Channel Performance'); ax.legend(); plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'per_channel_performance.png', dpi=150); plt.close()

    # 8. Calibration Curve
    print("  [8/10] Calibration Curve...")
    fig, ax = plt.subplots(figsize=(7, 6))
    prob_true, prob_pred = calibration_curve(y_test, y_scores, n_bins=10, strategy='uniform')
    ax.plot(prob_pred, prob_true, 'o-', label='Ensemble', linewidth=2)
    ax.plot([0,1],[0,1],'k--',alpha=0.3, label='Perfect')
    ax.set_xlabel('Mean Predicted Probability'); ax.set_ylabel('Fraction of Positives')
    ax.set_title('Calibration Curve'); ax.legend(); plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'calibration_curve.png', dpi=150); plt.close()

    # 9. Amount vs Score scatter
    print("  [9/10] Amount vs Score...")
    fig, ax = plt.subplots(figsize=(8, 5))
    sample_idx = np.random.RandomState(42).choice(len(y_test), min(5000, len(y_test)), replace=False)
    amounts_sample = X_test[sample_idx, 0]  # amount is feature 0
    scores_sample = y_scores[sample_idx]
    colors = ['#2ecc71' if y == 0 else '#e74c3c' for y in y_test[sample_idx]]
    ax.scatter(amounts_sample, scores_sample, c=colors, alpha=0.3, s=8)
    ax.set_xlabel('Amount (INR)'); ax.set_ylabel('Ensemble Score')
    ax.set_title('Amount vs Fraud Score (green=legit, red=fraud)'); plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'amount_vs_score.png', dpi=150); plt.close()

    # 10. Learning summary
    print("  [10/10] Summary card...")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.axis('off')
    metrics_text = f"""ARGUS v4.0 Training Summary
{'─'*40}
ROC-AUC:   {roc_auc_score(y_test, y_scores):.4f}
AP:        {average_precision_score(y_test, y_scores):.4f}
F1:        {f1_score(y_test, y_pred):.4f}
Precision: {precision_score(y_test, y_pred):.4f}
Recall:    {recall_score(y_test, y_pred):.4f}
{'─'*40}
Threshold: {opt:.4f}
Features:  {NUM_FEATURES}
Train set: {len(y_all) - len(y_test)*2:,}
Test set:  {len(y_test):,}
Date:      {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
    ax.text(0.1, 0.95, metrics_text, transform=ax.transAxes, fontsize=11,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='#ecf0f1', alpha=0.8))
    plt.tight_layout()
    fig.savefig(RESULTS_DIR / 'training_summary.png', dpi=150); plt.close()

    print(f"  All plots saved to {RESULTS_DIR}")
    return ch_metrics


def save_models(xgb, lgb, iso, scaler, threshold, metrics, ch_metrics):
    """Save all model artifacts."""
    print(f"\n{'='*65}")
    print("  SAVING MODELS")
    print(f"{'='*65}")

    joblib.dump(xgb, MODELS_DIR / "xgb_model.joblib")
    joblib.dump(lgb, MODELS_DIR / "lgb_model.joblib")
    joblib.dump(iso, MODELS_DIR / "isolation_forest.joblib")
    joblib.dump(scaler, MODELS_DIR / "scaler.joblib")
    joblib.dump(threshold, MODELS_DIR / "optimal_threshold.joblib")
    joblib.dump(FEATURE_NAMES, MODELS_DIR / "feature_names.joblib")

    metadata = {
        'version': '4.0.0-india',
        'training_date': datetime.now().isoformat(),
        'features': FEATURE_NAMES,
        'num_features': NUM_FEATURES,
        'optimal_threshold': threshold,
        'ensemble_weights': {'xgboost': 0.40, 'lightgbm': 0.35, 'isolation_forest': 0.25},
        'performance': metrics,
        'per_channel': ch_metrics,
    }
    with open(MODELS_DIR / "training_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"  Saved to {MODELS_DIR}")


def main():
    print(f"\n{'='*65}")
    print("  ARGUS FRAUD DETECTION MODEL TRAINING v4.0")
    print(f"{'='*65}")

    total_start = time.time()

    # Load & extract
    X, y, fraud_types, channels, df = load_and_extract_features()

    # Split
    X_train, X_val, X_test, y_train, y_val, y_test, ch_test = split_data(X, y, channels)

    # Train
    xgb, lgb, iso, scaler, train_metrics = train_models(X_train, X_val, y_train, y_val)

    # Ensemble on validation → find threshold
    print(f"\n{'='*65}")
    print("  FINDING OPTIMAL THRESHOLD (on validation set)")
    print(f"{'='*65}")

    y_val_scores = ensemble_predict(xgb, lgb, iso, scaler, X_val)
    threshold = find_optimal_threshold(y_val, y_val_scores)
    print(f"  Optimal threshold: {threshold:.4f}")

    # Evaluate on TEST set (never seen during training)
    print(f"\n{'='*65}")
    print("  FINAL EVALUATION (on held-out test set)")
    print(f"{'='*65}")

    y_test_scores = ensemble_predict(xgb, lgb, iso, scaler, X_test)
    y_test_pred = (y_test_scores > threshold).astype(int)

    test_auc = roc_auc_score(y_test, y_test_scores)
    test_ap = average_precision_score(y_test, y_test_scores)
    test_f1 = f1_score(y_test, y_test_pred)
    test_prec = precision_score(y_test, y_test_pred)
    test_rec = recall_score(y_test, y_test_pred)

    print(f"\n  Classification Report:")
    print(classification_report(y_test, y_test_pred, target_names=['Legit', 'Fraud']))

    cm = confusion_matrix(y_test, y_test_pred)
    print(f"  Confusion Matrix:")
    print(f"    TN: {cm[0,0]:>7,} | FP: {cm[0,1]:>6,}")
    print(f"    FN: {cm[1,0]:>7,} | TP: {cm[1,1]:>6,}")

    final_metrics = {
        **train_metrics,
        'test_roc_auc': test_auc, 'test_ap': test_ap,
        'test_f1': test_f1, 'test_precision': test_prec, 'test_recall': test_rec,
        'threshold': threshold,
    }

    print(f"\n  Summary:")
    print(f"    ROC-AUC:   {test_auc:.4f}")
    print(f"    AP:        {test_ap:.4f}")
    print(f"    F1:        {test_f1:.4f}")
    print(f"    Precision: {test_prec:.4f}")
    print(f"    Recall:    {test_rec:.4f}")

    # Generate all plots
    ch_metrics = generate_plots(
        y_test, y_test_scores, y_test_pred,
        xgb, lgb, iso, scaler, X_test, y_val, X_val, ch_test,
        fraud_types, y,
    )

    # Save
    save_models(xgb, lgb, iso, scaler, threshold, final_metrics, ch_metrics)

    total_time = (time.time() - total_start) / 60
    print(f"\n{'='*65}")
    print(f"  TRAINING COMPLETE — {total_time:.1f} minutes")
    print(f"{'='*65}")
    print(f"  Models:  {MODELS_DIR}")
    print(f"  Plots:   {RESULTS_DIR}")
    print(f"  Version: 4.0.0-india")
    print(f"{'='*65}\n")


if __name__ == '__main__':
    main()
