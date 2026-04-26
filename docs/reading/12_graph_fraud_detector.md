# Documentation: `graph_fraud_detector.py`

## 1. Purpose
This module introduces **Network/Graph Analysis** to the ARGUS platform. While traditional ML models look at transactions in isolation (or relative to a single user's history), this module views the entire payment ecosystem as a massive graph of interconnected nodes (Users and Merchants). Its primary goal is to identify macro-level structures like Fraud Rings and Cyclic Money Flows.

## 2. Key Technology
It utilizes `networkx`, a powerful Python graph library, to maintain an in-memory `DiGraph` (Directed Graph).
*   **Nodes**: Users and Merchants.
*   **Edges**: Transactions flowing from a Sender to a Receiver. Edge weights include transaction counts and total volume.

## 3. Core Graph Analytics

### A. Cyclic Pattern Detection (`detect_cyclic_patterns`)
Uses `nx.simple_cycles` to find paths where money moves from A → B → C → A. This is a classic indicator of layered money laundering or artificial volume generation (wash trading). It restricts searches to cycles of length 5 or less for performance.

### B. Mule Account Detection (`detect_mule_accounts`)
Mule accounts are the hubs of illicit money movement. The system looks for nodes with high `in_degree` (receiving from many people) AND high `out_degree` (sending to many people). It then checks the flow ratio—if >80% of the money entering the node immediately leaves the node to multiple destinations, it is tagged as a Mule.

### C. Fraud Ring Detection (`detect_connected_fraud_rings`)
Converts the directed graph to an undirected graph to find tight communities. It identifies "Strongly Connected Components" of 3 or more users. If the network density of that component is >50% (meaning everyone is transacting with almost everyone else in the group), it flags the entire cluster as a Fraud Ring.

## 4. Risk Scoring (`calculate_account_risk`)
When a new transaction hits the engine, it asks the graph: *"What is the network reputation of the Sender and Receiver?"*
*   +30 points if the account is in a known Fraud Ring.
*   +25 points if the account is a known Mule.
*   +5 points per cyclic pattern the account is involved in.
*   +20 points if *this specific transaction* creates a brand new cycle.

## 5. Assumptions & Limitations
*   **Limitation (Memory & Scale)**: `networkx` stores the graph entirely in RAM. While fine for thousands of nodes, storing millions of Indian UPI users in Python RAM will result in an Out Of Memory (OOM) crash.
*   **Limitation (Performance)**: Cycle detection (`simple_cycles`) is an NP-hard problem. Running it synchronously on every transaction is impossible for a low-latency system. Therefore, the engine only runs the heavy ring/mule detection every 100 transactions in the background.
*   **Production Roadmap**: A true enterprise deployment would migrate this logic to a dedicated graph database like Neo4j or Amazon Neptune, querying using Cypher.

## 6. Role in Architecture
Provides an experimental, high-level structural view of fraud. Its outputs are available for the case management dashboard to visualize the spread of illicit funds.
