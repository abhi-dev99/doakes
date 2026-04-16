"""
Deep Learning Fraud Detection Model
LSTM/Transformer-based sequence analysis for temporal fraud patterns
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import deque
import json

logger = logging.getLogger("ARGUS.DeepLearning")

# Optional imports
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - Deep learning features disabled")


class TransactionLSTM(nn.Module if TORCH_AVAILABLE else object):
    """LSTM model for sequential transaction analysis"""
    
    def __init__(self, input_size: int = 20, hidden_size: int = 64, num_layers: int = 2):
        if not TORCH_AVAILABLE:
            return
            
        super(TransactionLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.3)
        self.fc1 = nn.Linear(hidden_size, 32)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(32, 1)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        # x shape: (batch, sequence_length, input_size)
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # Take the last output
        last_output = lstm_out[:, -1, :]
        
        # Feed through fully connected layers
        out = self.fc1(last_output)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.sigmoid(out)
        
        return out


class TransactionTransformer(nn.Module if TORCH_AVAILABLE else object):
    """Transformer model for attention-based transaction analysis"""
    
    def __init__(self, input_size: int = 20, d_model: int = 64, nhead: int = 4, 
                 num_layers: int = 2, dim_feedforward: int = 128):
        if not TORCH_AVAILABLE:
            return
            
        super(TransactionTransformer, self).__init__()
        
        self.input_projection = nn.Linear(input_size, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=0.1,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.fc = nn.Linear(d_model, 1)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        # x shape: (batch, sequence_length, input_size)
        x = self.input_projection(x)
        x = self.pos_encoder(x)
        
        transformer_out = self.transformer(x)
        
        # Global average pooling
        pooled = torch.mean(transformer_out, dim=1)
        
        out = self.fc(pooled)
        out = self.sigmoid(out)
        
        return out


class PositionalEncoding(nn.Module if TORCH_AVAILABLE else object):
    """Positional encoding for transformer"""
    
    def __init__(self, d_model: int, max_len: int = 100):
        if not TORCH_AVAILABLE:
            return
            
        super(PositionalEncoding, self).__init__()
        
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-np.log(10000.0) / d_model))
        
        pe = torch.zeros(1, max_len, d_model)
        pe[0, :, 0::2] = torch.sin(position * div_term)
        pe[0, :, 1::2] = torch.cos(position * div_term)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        # x shape: (batch, seq_len, d_model)
        return x + self.pe[:, :x.size(1), :]


class SequenceAnalyzer:
    """Analyzes transaction sequences using deep learning models"""
    
    def __init__(self, sequence_length: int = 10, use_transformer: bool = True):
        self.sequence_length = sequence_length
        self.user_sequences = {}  # user_id -> deque of transactions
        self.use_transformer = use_transformer
        
        if TORCH_AVAILABLE:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            
            if use_transformer:
                self.model = TransactionTransformer(input_size=20).to(self.device)
            else:
                self.model = TransactionLSTM(input_size=20).to(self.device)
            
            self.model.eval()  # Inference mode
            logger.info(f"Deep learning model initialized: {'Transformer' if use_transformer else 'LSTM'} on {self.device}")
        else:
            self.model = None
            logger.warning("PyTorch not available - using rule-based fallback")
    
    def extract_sequence_features(self, transaction: Dict) -> np.ndarray:
        """Extract features from a single transaction for sequence analysis"""
        features = []
        
        # Amount features
        features.append(float(transaction.get('amount', 0)) / 100000)  # Normalize
        features.append(np.log1p(float(transaction.get('amount', 0))))
        
        # Time features
        hour = datetime.now().hour
        features.append(hour / 24.0)
        features.append(1 if 22 <= hour or hour <= 6 else 0)  # Night transaction
        
        # Payment method one-hot (6 methods)
        methods = ['UPI', 'CARD', 'NETBANKING', 'WALLET', 'ATM', 'POS']
        method = transaction.get('payment_method', 'UPI')
        features.extend([1 if m == method else 0 for m in methods])
        
        # Category one-hot (6 categories)
        categories = ['shopping', 'food', 'bills', 'transfer', 'entertainment', 'other']
        category = transaction.get('merchant_category', 'shopping')
        features.extend([1 if c == category else 0 for c in categories])
        
        return np.array(features, dtype=np.float32)
    
    def add_transaction(self, user_id: str, transaction: Dict):
        """Add transaction to user's sequence"""
        if user_id not in self.user_sequences:
            self.user_sequences[user_id] = deque(maxlen=self.sequence_length)
        
        features = self.extract_sequence_features(transaction)
        self.user_sequences[user_id].append({
            'features': features,
            'timestamp': transaction.get('timestamp', datetime.now().isoformat()),
            'amount': transaction.get('amount', 0),
            'is_fraud': transaction.get('is_fraud', False)
        })
    
    def predict_sequence_risk(self, user_id: str) -> Dict:
        """Predict fraud risk based on user's transaction sequence"""
        if user_id not in self.user_sequences or len(self.user_sequences[user_id]) == 0:
            return {
                'sequence_risk_score': 0,
                'risk_factors': ['No transaction history'],
                'sequence_length': 0
            }
        
        sequence = list(self.user_sequences[user_id])
        
        # Rule-based fallback if PyTorch not available
        if not TORCH_AVAILABLE or self.model is None:
            return self._rule_based_sequence_analysis(sequence)
        
        # Deep learning prediction
        try:
            # Pad sequence if needed
            feature_list = [txn['features'] for txn in sequence]
            
            if len(feature_list) < self.sequence_length:
                # Pad with zeros
                padding = [np.zeros_like(feature_list[0]) for _ in range(self.sequence_length - len(feature_list))]
                feature_list = padding + feature_list
            
            # Convert to tensor
            sequence_tensor = torch.FloatTensor(np.array([feature_list])).to(self.device)
            
            with torch.no_grad():
                risk_prob = self.model(sequence_tensor).item()
            
            risk_score = risk_prob * 100
            risk_factors = self._analyze_sequence_patterns(sequence, risk_score)
            
            return {
                'sequence_risk_score': risk_score,
                'risk_factors': risk_factors,
                'sequence_length': len(sequence),
                'model_type': 'Transformer' if self.use_transformer else 'LSTM'
            }
            
        except Exception as e:
            logger.error(f"Deep learning prediction failed: {e}")
            return self._rule_based_sequence_analysis(sequence)
    
    def _rule_based_sequence_analysis(self, sequence: List[Dict]) -> Dict:
        """Fallback rule-based sequence analysis"""
        risk_score = 0
        risk_factors = []
        
        if len(sequence) < 2:
            return {
                'sequence_risk_score': 0,
                'risk_factors': ['Insufficient history'],
                'sequence_length': len(sequence),
                'model_type': 'Rule-based'
            }
        
        # Pattern 1: Rapid amount escalation
        amounts = [txn['amount'] for txn in sequence]
        if len(amounts) >= 3:
            recent_avg = np.mean(amounts[-3:])
            historical_avg = np.mean(amounts[:-3]) if len(amounts) > 3 else recent_avg
            
            if recent_avg > historical_avg * 2:
                risk_score += 20
                risk_factors.append(f"Amount escalation: {recent_avg/historical_avg:.1f}x increase")
        
        # Pattern 2: Velocity increase
        timestamps = [datetime.fromisoformat(txn['timestamp']) for txn in sequence]
        if len(timestamps) >= 5:
            recent_intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() 
                               for i in range(len(timestamps)-5, len(timestamps)-1)]
            avg_interval = np.mean(recent_intervals)
            
            if avg_interval < 60:  # Less than 1 minute between transactions
                risk_score += 25
                risk_factors.append(f"Rapid succession: {avg_interval:.0f}s avg interval")
        
        # Pattern 3: Unusual time pattern
        night_txns = sum(1 for txn in sequence[-5:] 
                        if 22 <= datetime.fromisoformat(txn['timestamp']).hour or 
                        datetime.fromisoformat(txn['timestamp']).hour <= 6)
        if night_txns >= 3:
            risk_score += 15
            risk_factors.append(f"{night_txns} night-time transactions")
        
        # Pattern 4: Amount variance
        if len(amounts) >= 5:
            std_dev = np.std(amounts[-5:])
            mean_amt = np.mean(amounts[-5:])
            if std_dev > mean_amt * 0.8:  # High variance
                risk_score += 10
                risk_factors.append("Erratic transaction amounts")
        
        return {
            'sequence_risk_score': min(100, risk_score),
            'risk_factors': risk_factors,
            'sequence_length': len(sequence),
            'model_type': 'Rule-based'
        }
    
    def _analyze_sequence_patterns(self, sequence: List[Dict], base_risk: float) -> List[str]:
        """Analyze specific patterns in the sequence"""
        patterns = []
        
        # Check for known fraud patterns
        amounts = [txn['amount'] for txn in sequence]
        
        # Pattern 1: Test transactions followed by large amount
        if len(amounts) >= 3:
            if amounts[-3] < 100 and amounts[-2] < 100 and amounts[-1] > 10000:
                patterns.append("Test transaction pattern detected")
        
        # Pattern 2: Round number clustering
        round_numbers = sum(1 for amt in amounts[-5:] if amt % 1000 == 0)
        if round_numbers >= 3:
            patterns.append("Multiple round-number transactions")
        
        # Pattern 3: Identical amounts
        if len(set(amounts[-5:])) <= 2:
            patterns.append("Repetitive transaction amounts")
        
        if not patterns:
            if base_risk > 70:
                patterns.append("High-risk sequence pattern detected by ML model")
            elif base_risk > 40:
                patterns.append("Moderate-risk sequence pattern")
            else:
                patterns.append("Normal transaction sequence")
        
        return patterns
    
    def get_user_behavior_profile(self, user_id: str) -> Dict:
        """Get comprehensive behavior profile for a user"""
        if user_id not in self.user_sequences:
            return {}
        
        sequence = list(self.user_sequences[user_id])
        
        amounts = [txn['amount'] for txn in sequence]
        timestamps = [datetime.fromisoformat(txn['timestamp']) for txn in sequence]
        
        return {
            'total_transactions': len(sequence),
            'avg_amount': np.mean(amounts) if amounts else 0,
            'std_amount': np.std(amounts) if amounts else 0,
            'max_amount': max(amounts) if amounts else 0,
            'min_amount': min(amounts) if amounts else 0,
            'night_transaction_ratio': sum(1 for ts in timestamps 
                                          if 22 <= ts.hour or ts.hour <= 6) / len(timestamps) if timestamps else 0,
            'avg_interval_seconds': np.mean([(timestamps[i+1] - timestamps[i]).total_seconds() 
                                            for i in range(len(timestamps)-1)]) if len(timestamps) > 1 else 0
        }


# Global instance
sequence_analyzer = SequenceAnalyzer(sequence_length=10, use_transformer=True)


def analyze_sequence_risk(user_id: str, transaction: Dict) -> Dict:
    """Wrapper function for sequence-based risk analysis"""
    # Add current transaction to sequence
    sequence_analyzer.add_transaction(user_id, transaction)
    
    # Get risk prediction
    analysis = sequence_analyzer.predict_sequence_risk(user_id)
    
    # Add behavior profile
    analysis['behavior_profile'] = sequence_analyzer.get_user_behavior_profile(user_id)
    
    return analysis
