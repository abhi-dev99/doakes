"""
ARGUS ML Model Training - Dataset Download & Integration Script
================================================================

Automatically downloads:
1. PaySim Mobile Money (4.8M transactions - PRIMARY)
2. Kaggle UPI Transactions 2024 (1-2M transactions - SECONDARY)
3. Combines into unified training dataset

Then trains enhanced model with all improvements.

USAGE:
  python data_preparation.py --download
  python data_preparation.py --train
  python data_preparation.py --all
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import subprocess
import json
from datetime import datetime
import urllib.request
import zipfile
import shutil
from typing import Tuple, Dict

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

# Dataset configurations
PAYSIM_URL = "https://www.kaggle.com/datasets/ealaxi/paysim1"
PAYSIM_FILE = DATA_DIR / "PS_20174392719_1491204493457_log.csv"

KAGGLE_UPI_DATASET = "skullagos5246/upi-transactions-2024-dataset"
KAGGLE_UPI_FILE = DATA_DIR / "upi_transactions_2024.csv"

COMBINED_DATASET = DATA_DIR / "combined_fraud_training_data.csv"

# ============ KAGGLE AUTHENTICATION ============

def setup_kaggle_credentials():
    """
    Setup Kaggle API credentials
    
    Steps:
    1. Go to https://kaggle.com/settings/account
    2. Click 'Create New API Token'
    3. Save kaggle.json to ~/.kaggle/
    """
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_json = kaggle_dir / "kaggle.json"
    
    if not kaggle_json.exists():
        print("\n❌ Kaggle API credentials not found!")
        print("\n📋 Setup Instructions:")
        print("1. Go to: https://kaggle.com/settings/account")
        print("2. Click 'Create New API Token'")
        print("3. This downloads kaggle.json")
        print("4. Move it to: ~/.kaggle/kaggle.json")
        print("5. Run: chmod 600 ~/.kaggle/kaggle.json")
        print("\nThen re-run this script.")
        return False
    
    print("✅ Kaggle credentials found")
    return True


# ============ PAYSIM DOWNLOAD ============

def download_paysim():
    """Download PaySim dataset from Kaggle"""
    print("\n" + "="*60)
    print("DOWNLOADING PAYSIM DATASET")
    print("="*60)
    
    if PAYSIM_FILE.exists():
        print(f"✅ PaySim already exists: {PAYSIM_FILE}")
        return True
    
    print(f"\n📥 Downloading PaySim (440 MB)...")
    print(f"   Source: {PAYSIM_URL}")
    
    try:
        # Use kaggle CLI to download
        dataset_name = "ealaxi/paysim1"
        
        # Download dataset
        result = subprocess.run(
            ["kaggle", "datasets", "download", "-d", dataset_name, "-p", str(DATA_DIR)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )
        
        if result.returncode != 0:
            print(f"❌ Download failed: {result.stderr}")
            return False
        
        print("✅ PaySim downloaded successfully")
        
        # Unzip if needed
        zip_file = DATA_DIR / f"{dataset_name.split('/')[-1]}.zip"
        if zip_file.exists():
            print(f"📦 Extracting {zip_file}...")
            with zipfile.ZipFile(zip_file, 'r') as z:
                z.extractall(DATA_DIR)
            os.remove(zip_file)
            print("✅ Extraction complete")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Download timeout (>5 min). Try manual download from Kaggle.")
        return False
    except Exception as e:
        print(f"❌ Download error: {e}")
        return False


def download_kaggle_upi():
    """Download Kaggle UPI Transactions 2024"""
    print("\n" + "="*60)
    print("DOWNLOADING KAGGLE UPI TRANSACTIONS 2024")
    print("="*60)
    
    if KAGGLE_UPI_FILE.exists():
        print(f"✅ Kaggle UPI already exists: {KAGGLE_UPI_FILE}")
        return True
    
    print(f"\n📥 Downloading Kaggle UPI (29.81 MB)...")
    print(f"   Source: {KAGGLE_UPI_DATASET}")
    
    try:
        result = subprocess.run(
            ["kaggle", "datasets", "download", "-d", KAGGLE_UPI_DATASET, "-p", str(DATA_DIR)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            print(f"❌ Download failed: {result.stderr}")
            return False
        
        print("✅ Kaggle UPI downloaded successfully")
        
        # Unzip
        zip_file = DATA_DIR / f"{KAGGLE_UPI_DATASET.split('/')[-1]}.zip"
        if zip_file.exists():
            print(f"📦 Extracting {zip_file}...")
            with zipfile.ZipFile(zip_file, 'r') as z:
                z.extractall(DATA_DIR)
            os.remove(zip_file)
            print("✅ Extraction complete")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Download timeout. Try manual download from Kaggle.")
        return False
    except Exception as e:
        print(f"❌ Download error: {e}")
        return False


# ============ DATA INTEGRATION ============

def load_paysim() -> pd.DataFrame:
    """Load PaySim dataset"""
    print(f"\n📂 Loading PaySim from {PAYSIM_FILE}...")
    
    if not PAYSIM_FILE.exists():
        print(f"❌ File not found: {PAYSIM_FILE}")
        return None
    
    try:
        df = pd.read_csv(PAYSIM_FILE)
        print(f"✅ Loaded {len(df):,} transactions")
        print(f"   Fraud rate: {df['isFraud'].mean():.2%}")
        print(f"   Columns: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"❌ Error loading PaySim: {e}")
        return None


def load_kaggle_upi() -> pd.DataFrame:
    """Load Kaggle UPI dataset"""
    print(f"\n📂 Loading Kaggle UPI from {KAGGLE_UPI_FILE}...")
    
    if not KAGGLE_UPI_FILE.exists():
        print(f"❌ File not found: {KAGGLE_UPI_FILE}")
        return None
    
    try:
        df = pd.read_csv(KAGGLE_UPI_FILE)
        print(f"✅ Loaded {len(df):,} transactions")
        
        # Find fraud column (might be named differently)
        fraud_col = None
        for col in ['isFraud', 'fraud_flag', 'Fraud', 'fraud']:
            if col in df.columns:
                fraud_col = col
                break
        
        if fraud_col:
            print(f"   Fraud rate: {df[fraud_col].mean():.2%}")
        else:
            print(f"   ⚠️ Fraud column not found. Columns: {list(df.columns)[:10]}...")
        
        print(f"   Full columns: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"❌ Error loading Kaggle UPI: {e}")
        return None


def normalize_paysim(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize PaySim to standard schema"""
    print("\n🔧 Normalizing PaySim schema...")
    
    df = df.copy()
    
    # Rename columns to standard names
    df = df.rename(columns={
        'type': 'transaction_type',
        'amount': 'amount',
        'nameOrig': 'sender_id',
        'oldbalanceOrig': 'sender_balance_before',
        'newbalanceOrig': 'sender_balance_after',
        'nameDest': 'receiver_id',
        'oldbalanceDest': 'receiver_balance_before',
        'newbalanceDest': 'receiver_balance_after',
        'isFraud': 'is_fraud'
    })
    
    # Add PaySim source marker
    df['source_dataset'] = 'paysim'
    
    # Add missing columns with defaults for compatibility
    if 'timestamp' not in df.columns and 'step' in df.columns:
        df['timestamp'] = pd.to_datetime('2016-01-01') + pd.to_timedelta(df['step'], unit='H')
    
    if 'merchant_category' not in df.columns:
        # Infer from transaction type
        type_to_category = {
            'CASH_IN': 'cash_withdrawal',
            'CASH_OUT': 'cash_withdrawal',
            'PAYMENT': 'merchant_payment',
            'TRANSFER': 'p2p_transfer',
            'DEBIT': 'debit'
        }
        df['merchant_category'] = df.get('transaction_type', 'PAYMENT').map(
            type_to_category
        ).fillna('retail')
    
    if 'device_type' not in df.columns:
        df['device_type'] = 'Unknown'
    
    if 'state' not in df.columns:
        df['state'] = 'MH'  # Default to Maharashtra
    
    # Keep only relevant columns
    standard_cols = [
        'transaction_type', 'amount', 'sender_id', 'receiver_id',
        'timestamp', 'is_fraud', 'merchant_category', 'device_type', 'state',
        'source_dataset'
    ]
    
    for col in standard_cols:
        if col not in df.columns:
            if col == 'is_fraud':
                df[col] = 0
            elif col == 'timestamp':
                df[col] = datetime.now()
            else:
                df[col] = 'Unknown'
    
    df = df[standard_cols]
    
    print(f"✅ PaySim normalized: {len(df):,} transactions")
    return df


def normalize_kaggle_upi(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Kaggle UPI to standard schema"""
    print("\n🔧 Normalizing Kaggle UPI schema...")
    
    df = df.copy()
    
    # Find fraud column
    fraud_col = None
    for col in ['isFraud', 'fraud_flag', 'Fraud', 'fraud']:
        if col in df.columns:
            fraud_col = col
            break
    
    if not fraud_col:
        print("⚠️ No fraud column found, assuming no fraud for all transactions")
        df['is_fraud'] = 0
    else:
        df['is_fraud'] = df[fraud_col]
    
    # Rename columns
    df = df.rename(columns={
        'transaction_type': 'transaction_type',
        'amount (INR)': 'amount',
        'amount': 'amount'
    })
    
    # Add source marker
    df['source_dataset'] = 'kaggle_upi'
    
    # Handle missing columns
    if 'timestamp' not in df.columns:
        df['timestamp'] = datetime.now()
    
    if 'merchant_category' not in df.columns:
        df['merchant_category'] = 'retail'
    
    if 'device_type' not in df.columns:
        df['device_type'] = 'Android'
    
    if 'state' not in df.columns:
        df['state'] = 'MH'
    
    standard_cols = [
        'transaction_type', 'amount', 'timestamp', 'is_fraud',
        'merchant_category', 'device_type', 'state', 'source_dataset'
    ]
    
    for col in standard_cols:
        if col not in df.columns:
            if col == 'is_fraud':
                df[col] = 0
            else:
                df[col] = 'Unknown'
    
    df = df[standard_cols]
    
    print(f"✅ Kaggle UPI normalized: {len(df):,} transactions")
    return df


def combine_datasets(paysim_df: pd.DataFrame, kaggle_df: pd.DataFrame) -> pd.DataFrame:
    """Combine PaySim and Kaggle UPI with optimal weighting"""
    print("\n" + "="*60)
    print("COMBINING DATASETS")
    print("="*60)
    
    print(f"\nPaySim: {len(paysim_df):,} transactions ({paysim_df['is_fraud'].mean():.2%} fraud)")
    print(f"Kaggle UPI: {len(kaggle_df):,} transactions ({kaggle_df['is_fraud'].mean():.2%} fraud)")
    
    # Strategy: 70% PaySim (more diverse) + 30% Kaggle UPI (India-specific)
    sample_paysim = paysim_df.sample(frac=0.7, random_state=42)
    sample_kaggle = kaggle_df.sample(frac=0.3, random_state=42)
    
    combined = pd.concat([sample_paysim, sample_kaggle], ignore_index=True)
    combined = combined.sample(frac=1, random_state=42)  # Shuffle
    
    print(f"\n✅ Combined dataset: {len(combined):,} transactions")
    print(f"   Fraud rate: {combined['is_fraud'].mean():.4%}")
    print(f"   PaySim contribution: {(sample_paysim['is_fraud'].sum() + sample_kaggle['is_fraud'].sum())/len(combined)*100:.0f}%")
    print(f"\n   Source breakdown:")
    print(f"      PaySim: {len(sample_paysim):,} ({len(sample_paysim)/len(combined)*100:.0f}%)")
    print(f"      Kaggle UPI: {len(sample_kaggle):,} ({len(sample_kaggle)/len(combined)*100:.0f}%)")
    
    return combined


def save_combined_dataset(df: pd.DataFrame):
    """Save combined dataset"""
    print(f"\n💾 Saving combined dataset to {COMBINED_DATASET}...")
    
    df.to_csv(COMBINED_DATASET, index=False)
    
    size_mb = COMBINED_DATASET.stat().st_size / (1024*1024)
    print(f"✅ Saved: {size_mb:.1f} MB")
    
    # Save metadata
    metadata = {
        'created': datetime.now().isoformat(),
        'total_transactions': len(df),
        'fraud_rate': float(df['is_fraud'].mean()),
        'fraud_count': int(df['is_fraud'].sum()),
        'non_fraud_count': int((df['is_fraud'] == 0).sum()),
        'sources': df['source_dataset'].value_counts().to_dict(),
        'columns': list(df.columns)
    }
    
    metadata_file = COMBINED_DATASET.with_suffix('.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Metadata saved: {metadata_file}")
    
    return metadata


# ============ MAIN PIPELINE ============

def main():
    """Main execution pipeline"""
    print("\n" + "="*60)
    print("ARGUS ML - DATA PREPARATION PIPELINE")
    print("="*60)
    print(f"Start time: {datetime.now()}")
    
    # Step 1: Check Kaggle credentials
    print("\n[1/5] Checking Kaggle credentials...")
    if not setup_kaggle_credentials():
        print("\n❌ Please setup Kaggle credentials and re-run.")
        return False
    
    # Step 2: Download PaySim
    print("\n[2/5] Processing PaySim dataset...")
    if not download_paysim():
        print("⚠️  PaySim download failed. Manual download required:")
        print("   https://www.kaggle.com/datasets/ealaxi/paysim1")
        print("   Save to: backend/ml/data/PS_20174392719_1491204493457_log.csv")
    
    # Step 3: Download Kaggle UPI
    print("\n[3/5] Processing Kaggle UPI dataset...")
    if not download_kaggle_upi():
        print("⚠️  Kaggle UPI download failed. Manual download required:")
        print("   https://www.kaggle.com/datasets/skullagos5246/upi-transactions-2024-dataset")
        print("   Save to: backend/ml/data/upi_transactions_2024.csv")
    
    # Step 4: Load and normalize
    print("\n[4/5] Loading and normalizing datasets...")
    paysim_df = load_paysim()
    kaggle_df = load_kaggle_upi()
    
    if paysim_df is None or kaggle_df is None:
        print("\n❌ Could not load one or both datasets. Check paths and try again.")
        return False
    
    # Normalize schemas
    paysim_normalized = normalize_paysim(paysim_df)
    kaggle_normalized = normalize_kaggle_upi(kaggle_df)
    
    # Step 5: Combine
    print("\n[5/5] Combining datasets...")
    combined_df = combine_datasets(paysim_normalized, kaggle_normalized)
    save_combined_dataset(combined_df)
    
    print("\n" + "="*60)
    print("✅ DATA PREPARATION COMPLETE")
    print("="*60)
    print(f"End time: {datetime.now()}")
    print(f"\nNext step: Train model with combined dataset")
    print(f"  python train_model_v3_combined.py")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download and prepare fraud detection datasets")
    parser.add_argument("--download", action="store_true", help="Download datasets only")
    parser.add_argument("--combine", action="store_true", help="Combine datasets only")
    parser.add_argument("--all", action="store_true", help="Download and combine (default)")
    
    args = parser.parse_args()
    
    # Default to --all if no args
    if not (args.download or args.combine or args.all):
        args.all = True
    
    success = main()
    sys.exit(0 if success else 1)
