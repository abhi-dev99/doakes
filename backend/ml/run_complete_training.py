#!/usr/bin/env python3
"""
ARGUS ML Training - Complete Automation Script
==============================================

One-command training with:
1. Kaggle dataset download (UPI 2024)
2. PaySim dataset download (4.8M transactions)
3. Data combination & normalization
4. Automatic model training (v3.1 combined)

USAGE:
  python run_complete_training.py

REQUIREMENTS:
  - Kaggle API credentials (~/.kaggle/kaggle.json)
  - Internet connection
  - ~8-16 GB RAM
  - 60-90 minutes

This is the COMPLETE SOLUTION - just run this one script!
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# Paths
BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / f"training_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

def log(message: str, also_print=True):
    """Log message to file and optionally print"""
    with open(LOG_FILE, 'a') as f:
        f.write(message + '\n')
    if also_print:
        print(message)

def run_command(cmd: list, description: str) -> bool:
    """Run command and handle output"""
    print(f"\n{'='*70}")
    print(f"🔧 {description}")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            timeout=3600  # 1 hour max
        )
        
        if result.returncode != 0:
            log(f"❌ FAILED: {description}", True)
            return False
        
        log(f"✅ SUCCESS: {description}", True)
        return True
        
    except subprocess.TimeoutExpired:
        log(f"❌ TIMEOUT: {description} (>1 hour)", True)
        return False
    except Exception as e:
        log(f"❌ ERROR in {description}: {e}", True)
        return False


def main():
    """Main orchestration"""
    log("="*70, True)
    log("ARGUS ML TRAINING - COMPLETE AUTOMATION", True)
    log("="*70, True)
    log(f"Start time: {datetime.now()}", True)
    log(f"Log file: {LOG_FILE}", True)
    
    steps = [
        (
            ["python", str(BASE_DIR / "data_preparation.py"), "--all"],
            "DATA PREPARATION (Download PaySim + Kaggle UPI + Combine)"
        ),
        (
            ["python", str(BASE_DIR / "train_model_v3_combined.py")],
            "MODEL TRAINING (XGB + LGB + ISO Ensemble)"
        ),
    ]
    
    results = []
    
    for cmd, description in steps:
        success = run_command(cmd, description)
        results.append((description, success))
        
        if not success:
            log(f"\n⚠️  Training pipeline stopped at: {description}", True)
            break
    
    # Summary
    log("\n" + "="*70, True)
    log("TRAINING PIPELINE SUMMARY", True)
    log("="*70, True)
    
    for description, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        log(f"{status}: {description}", True)
    
    all_success = all(success for _, success in results)
    
    if all_success:
        log(f"\n{'='*70}", True)
        log("🎉 COMPLETE TRAINING SUCCESSFUL!", True)
        log(f"{'='*70}", True)
        log(f"""
Models saved to: {BASE_DIR / 'models'}

New model files:
  - xgb_model_combined.joblib
  - lgb_model_combined.joblib
  - isolation_forest_combined.joblib
  - scaler_combined.joblib
  - feature_cols_combined.joblib
  - optimal_threshold_combined.joblib
  - feature_importance_combined.joblib
  - metadata_combined.joblib

Next Steps:
  1. Update fraud_model.py to use *_combined models
  2. Test on dashboard
  3. Monitor performance metrics
  4. Deploy to production

For details, see: {LOG_FILE}
""", True)
        return 0
    else:
        log(f"\n{'='*70}", True)
        log("❌ TRAINING FAILED - CHECK ERRORS ABOVE", True)
        log(f"{'='*70}", True)
        log(f"Log file: {LOG_FILE}", True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
