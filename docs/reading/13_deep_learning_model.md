# Documentation: `deep_learning_model.py`

## 1. Purpose
This module introduces **Sequential Deep Learning** (LSTM and Transformers) to analyze the *time-series behavior* of a user's transactions. While XGBoost treats every transaction as an isolated row, this module treats a user's transaction history as a temporal sequence (like a sentence of words) to detect complex escalation patterns.

## 2. Key Architecture

### A. Model Variants
The module provides two PyTorch architectures:
1.  `TransactionLSTM`: A Long Short-Term Memory network. Excellent at remembering long-term historical context.
2.  `TransactionTransformer`: An Attention-based Transformer (similar architecture to LLMs). Excellent at finding complex relationships between distant transactions in a sequence.

### B. Sequence Encoding
Instead of the standard 34 tabular features, it encodes a sequence of transactions into a sequence of 16-dimensional vectors (`input_size=16`).
Features include normalized amounts, log amounts, cyclical time, and one-hot encoded payment channels/categories.

## 3. Core Logic / Workflow (`SequenceAnalyzer`)
1.  **State Management**: It maintains a `deque(maxlen=10)` for each `user_id`. Every new transaction pushes the oldest one out.
2.  **Inference (`predict_sequence_risk`)**:
    *   It extracts the 16 features for the new transaction and appends it to the user's deque.
    *   It pads the sequence with zeros if the user has fewer than 10 transactions.
    *   It converts the sequence to a PyTorch Tensor (`batch=1, seq_len=10, input=16`) and runs a forward pass through the model.
    *   The model outputs a sigmoid probability (0.0 to 1.0) which is scaled to a risk score of 0-100.

### Fallback Mechanism
If PyTorch is not installed (`TORCH_AVAILABLE = False`), the module degrades gracefully to a rule-based sequence analyzer. It mathematically checks for:
*   Rapid Amount Escalation (recent avg > historical avg * 2)
*   Velocity Increases (< 60s between transactions)
*   Erratic amount variances

## 4. Assumptions & Limitations
*   **Limitation (Compute)**: Running a PyTorch Transformer forward pass synchronously in a Python API thread adds considerable latency (10-50ms) and requires high CPU/GPU usage. It is currently disabled/bypassed in the standard `fraud_model.py` ensemble to maintain the sub-20ms SLA.
*   **Limitation (State)**: Keeping a `deque` of histories in Python RAM is not scalable across multiple worker nodes.

## 5. Role in Architecture
Currently serves as an experimental/advanced feature module. In a full production deployment, this model would run *asynchronously* (post-authorization) as a batch job to flag accounts for manual review, rather than blocking transactions in real-time.
