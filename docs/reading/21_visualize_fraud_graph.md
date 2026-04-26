# Documentation: `visualize_fraud_graph.py`

## 1. Purpose
This is an offline, standalone utility script used to generate an interactive HTML visualization of complex fraud rings. While the main application uses `NetworkX` in memory for real-time detection, this script uses `PyVis` to export those networks into a format (`fraud_network.html`) that can be presented to stakeholders or investigators.

## 2. Core Logic

### A. Data Extraction
1.  The script reads the massive 750k row synthetic dataset (`argus_training_data.csv`) using Pandas chunking to avoid memory overflow.
2.  It filters exclusively for transactions marked as `is_fraud = 1`.
3.  It performs a `.groupby()` to identify the most heavily targeted `merchant_id`s and the most frequently used `device_id`s in fraudulent transactions.

### B. Graph Construction
Using `NetworkX`, it builds a tripartite graph connecting Users, Devices, and Merchants:
*   **Nodes**: 
    *   Users (Blue, Size 15)
    *   Merchants (Green, Size 20)
    *   Devices (Purple, Size 15)
*   **Edges**:
    *   Solid Line (User -> Merchant): Represents a financial transaction. Colored Red if fraudulent, Grey if legitimate.
    *   Dashed Line (User -> Device): Represents a login/session association.

### C. PyVis Rendering
The `NetworkX` graph is passed to `pyvis.network.Network`.
*   It configures a physics engine (`forceAtlas2Based`) to create a dynamic, gravity-based layout where highly connected nodes (like a device used by 50 different users for fraud) naturally clump together in the center.
*   The output is written to `fraud_network.html`.

## 3. Role in Architecture
This is a forensic/reporting tool. It is not part of the real-time $<20ms$ execution path. It is used to generate the visual evidence of "Fraud Rings" (e.g., multiple seemingly unrelated users all using the exact same Device ID to funnel money into the same Merchant ID), which is a key feature of the ARGUS platform.
