import pandas as pd
import networkx as nx
from pyvis.network import Network
import random
import os

print("Loading dataset...")
data_path = "../dataset/argus_training_data.csv"
if not os.path.exists(data_path):
    # Try the short one if the main one is too big or missing
    data_path = "../dataset/argus_training_data_short.csv"

# Load a chunk to find a good cluster
chunk_iter = pd.read_csv(data_path, chunksize=500000)
df = next(chunk_iter)

print("Filtering for fraud transactions...")
fraud_df = df[df['is_fraud'] == 1]

# Find a device or merchant with multiple fraud transactions
# Let's look for devices used by multiple users for fraud, or merchants targeted by multiple users
fraud_devices = fraud_df.groupby('device_id')['user_id'].nunique().sort_values(ascending=False)
fraud_merchants = fraud_df.groupby('merchant_id')['user_id'].nunique().sort_values(ascending=False)

# Get the top device or merchant
top_device = fraud_devices.index[0] if len(fraud_devices) > 0 else None
top_merchant = fraud_merchants.index[0] if len(fraud_merchants) > 0 else None

print(f"Top Fraud Device: {top_device} (used by {fraud_devices.iloc[0]} users)")
print(f"Top Fraud Merchant: {top_merchant} (targeted by {fraud_merchants.iloc[0]} users)")

# Pick a few top devices and merchants to form a nice network
target_devices = fraud_devices.head(3).index.tolist()
target_merchants = fraud_merchants.head(3).index.tolist()

# Filter original dataframe for any transactions involving these devices or merchants
cluster_df = df[(df['device_id'].isin(target_devices)) | (df['merchant_id'].isin(target_merchants))]

print(f"Extracted {len(cluster_df)} transactions for the cluster network.")

# Build the Graph
G = nx.Graph()

for _, row in cluster_df.iterrows():
    user = row['user_id']
    merchant = row['merchant_id']
    device = row['device_id']
    is_fraud = row['is_fraud']
    
    # Add Nodes
    G.add_node(user, group='user', title=f"User: {user}", color='#3498db', size=15)
    G.add_node(merchant, group='merchant', title=f"Merchant: {merchant}\nRisk: {row['merchant_risk_score']}", color='#2ecc71', size=20)
    G.add_node(device, group='device', title=f"Device: {device}", color='#9b59b6', size=15)
    
    # Add Edges
    edge_color = '#e74c3c' if is_fraud else '#bdc3c7'
    edge_width = 3 if is_fraud else 1
    
    # User -> Merchant
    if G.has_edge(user, merchant):
        # If edge exists, maybe it was fraud this time, update color if fraud
        if is_fraud:
            G[user][merchant]['color'] = edge_color
            G[user][merchant]['width'] = edge_width
    else:
        G.add_edge(user, merchant, color=edge_color, width=edge_width, title=f"Txn: {row['transaction_id']}")
        
    # User -> Device
    if not G.has_edge(user, device):
        G.add_edge(user, device, color='#95a5a6', width=1, dash=True)


print(f"Graph created with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")

# Use Pyvis to visualize
net = Network(height='750px', width='100%', bgcolor='#222222', font_color='white')
net.from_nx(G)

# Tweak physics for better layout
net.set_options("""
var options = {
  "physics": {
    "forceAtlas2Based": {
      "gravitationalConstant": -50,
      "centralGravity": 0.01,
      "springLength": 100,
      "springConstant": 0.08
    },
    "minVelocity": 0.75,
    "solver": "forceAtlas2Based"
  }
}
""")

output_file = "fraud_network.html"
net.write_html(output_file)
print(f"Graph saved to {output_file}")
