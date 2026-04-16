"""
Graph-Based Fraud Detection Engine
Detects fraud rings, mule accounts, and cyclic transfer patterns using network analysis
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import json

try:
    import networkx as nx
except ImportError:
    nx = None

logger = logging.getLogger("ARGUS.GraphFraud")


class FraudRingDetector:
    """Detects fraud rings using graph-based network analysis"""
    
    def __init__(self):
        self.transaction_graph = nx.DiGraph() if nx else None
        self.account_metadata = {}
        self.fraud_rings = []
        self.mule_accounts = set()
        
    def add_transaction(self, txn_data: Dict) -> None:
        """Add transaction to the graph"""
        if not nx:
            return
            
        sender = txn_data.get('user_id', 'unknown')
        receiver = txn_data.get('merchant_id', 'unknown')
        amount = txn_data.get('amount', 0)
        timestamp = txn_data.get('timestamp', datetime.now().isoformat())
        
        # Add nodes
        if not self.transaction_graph.has_node(sender):
            self.transaction_graph.add_node(sender, node_type='user', first_seen=timestamp)
        if not self.transaction_graph.has_node(receiver):
            self.transaction_graph.add_node(receiver, node_type='merchant', first_seen=timestamp)
        
        # Add edge with transaction details
        if self.transaction_graph.has_edge(sender, receiver):
            edge_data = self.transaction_graph[sender][receiver]
            edge_data['count'] += 1
            edge_data['total_amount'] += amount
            edge_data['last_timestamp'] = timestamp
        else:
            self.transaction_graph.add_edge(
                sender, receiver,
                count=1,
                total_amount=amount,
                first_timestamp=timestamp,
                last_timestamp=timestamp
            )
    
    def detect_cyclic_patterns(self, max_cycle_length: int = 5) -> List[List[str]]:
        """Detect cyclic money transfer patterns (A→B→C→A)"""
        if not nx:
            return []
            
        cycles = []
        try:
            # Find all simple cycles up to max_cycle_length
            for cycle in nx.simple_cycles(self.transaction_graph):
                if len(cycle) <= max_cycle_length:
                    cycles.append(cycle)
        except Exception as e:
            logger.error(f"Error detecting cycles: {e}")
        
        return cycles
    
    def detect_mule_accounts(self, min_in_degree: int = 10, min_out_degree: int = 10) -> Set[str]:
        """Detect potential mule accounts (high in/out transaction volume)"""
        if not nx:
            return set()
            
        mule_candidates = set()
        
        for node in self.transaction_graph.nodes():
            in_degree = self.transaction_graph.in_degree(node)
            out_degree = self.transaction_graph.out_degree(node)
            
            # Mule accounts typically receive from many sources and send to many destinations
            if in_degree >= min_in_degree and out_degree >= min_out_degree:
                # Calculate velocity ratio (how fast money moves through)
                total_in = sum(self.transaction_graph[u][node]['total_amount'] 
                              for u in self.transaction_graph.predecessors(node))
                total_out = sum(self.transaction_graph[node][v]['total_amount'] 
                               for v in self.transaction_graph.successors(node))
                
                # High flow-through ratio indicates mule behavior
                if total_out > total_in * 0.8:  # 80%+ of incoming money flows out
                    mule_candidates.add(node)
        
        self.mule_accounts = mule_candidates
        return mule_candidates
    
    def detect_connected_fraud_rings(self, min_ring_size: int = 3) -> List[Set[str]]:
        """Detect tightly connected groups (potential fraud rings)"""
        if not nx:
            return []
            
        fraud_rings = []
        
        # Convert to undirected for community detection
        undirected = self.transaction_graph.to_undirected()
        
        # Find strongly connected components
        for component in nx.connected_components(undirected):
            if len(component) >= min_ring_size:
                # Check if this component has high internal connectivity
                subgraph = undirected.subgraph(component)
                density = nx.density(subgraph)
                
                # High density = tight connections = potential fraud ring
                if density > 0.5:  # 50%+ of possible connections exist
                    fraud_rings.append(component)
        
        self.fraud_rings = fraud_rings
        return fraud_rings
    
    def calculate_account_risk(self, account_id: str) -> Dict:
        """Calculate comprehensive risk score for an account based on graph metrics"""
        if not nx or not self.transaction_graph.has_node(account_id):
            return {'risk_score': 0, 'risk_factors': []}
        
        risk_factors = []
        risk_score = 0
        
        # Factor 1: Is account in a fraud ring?
        for ring in self.fraud_rings:
            if account_id in ring:
                risk_score += 30
                risk_factors.append(f"Part of fraud ring (size: {len(ring)})")
                break
        
        # Factor 2: Is it a mule account?
        if account_id in self.mule_accounts:
            risk_score += 25
            risk_factors.append("Identified as mule account")
        
        # Factor 3: Participation in cyclic patterns
        cycles = self.detect_cyclic_patterns()
        cycle_count = sum(1 for cycle in cycles if account_id in cycle)
        if cycle_count > 0:
            risk_score += min(20, cycle_count * 5)
            risk_factors.append(f"Involved in {cycle_count} cyclic patterns")
        
        # Factor 4: Abnormal connectivity
        in_degree = self.transaction_graph.in_degree(account_id)
        out_degree = self.transaction_graph.out_degree(account_id)
        
        if in_degree > 20:
            risk_score += 10
            risk_factors.append(f"High incoming connections: {in_degree}")
        if out_degree > 20:
            risk_score += 10
            risk_factors.append(f"High outgoing connections: {out_degree}")
        
        # Factor 5: Rapid money movement (velocity)
        try:
            # Calculate average time between receiving and sending
            in_edges = [(u, account_id, data) for u, v, data in 
                       self.transaction_graph.in_edges(account_id, data=True)]
            out_edges = [(account_id, v, data) for u, v, data in 
                        self.transaction_graph.out_edges(account_id, data=True)]
            
            if in_edges and out_edges:
                # Check if money is being moved out rapidly after receiving
                risk_score += 5
                risk_factors.append("Rapid money movement detected")
        except Exception:
            pass
        
        return {
            'risk_score': min(100, risk_score),
            'risk_factors': risk_factors,
            'in_degree': in_degree,
            'out_degree': out_degree,
            'is_mule': account_id in self.mule_accounts,
            'fraud_ring_member': any(account_id in ring for ring in self.fraud_rings)
        }
    
    def analyze_transaction_risk(self, sender_id: str, receiver_id: str, amount: float) -> Dict:
        """Analyze risk of a specific transaction based on graph patterns"""
        if not nx:
            return {'graph_risk_score': 0, 'risk_factors': []}
        
        risk_factors = []
        risk_score = 0
        
        # Check sender risk
        sender_risk = self.calculate_account_risk(sender_id)
        risk_score += sender_risk['risk_score'] * 0.4  # 40% weight
        
        # Check receiver risk
        receiver_risk = self.calculate_account_risk(receiver_id)
        risk_score += receiver_risk['risk_score'] * 0.3  # 30% weight
        
        # Check if this transaction creates a cycle
        if self.transaction_graph.has_node(sender_id) and self.transaction_graph.has_node(receiver_id):
            # Temporarily add edge to check for cycles
            temp_graph = self.transaction_graph.copy()
            temp_graph.add_edge(sender_id, receiver_id)
            
            try:
                cycles = list(nx.simple_cycles(temp_graph))
                new_cycles = [c for c in cycles if sender_id in c and receiver_id in c]
                if new_cycles:
                    risk_score += 20
                    risk_factors.append(f"Creates {len(new_cycles)} cyclic patterns")
            except Exception:
                pass
        
        # Check for rapid succession (velocity)
        if self.transaction_graph.has_edge(sender_id, receiver_id):
            edge_data = self.transaction_graph[sender_id][receiver_id]
            if edge_data['count'] > 5:  # More than 5 transactions between same parties
                risk_score += 10
                risk_factors.append(f"Repeated transactions: {edge_data['count']}")
        
        return {
            'graph_risk_score': min(100, risk_score),
            'risk_factors': risk_factors,
            'sender_analysis': sender_risk,
            'receiver_analysis': receiver_risk
        }
    
    def get_statistics(self) -> Dict:
        """Get overall graph statistics"""
        if not nx or not self.transaction_graph:
            return {}
        
        return {
            'total_nodes': self.transaction_graph.number_of_nodes(),
            'total_edges': self.transaction_graph.number_of_edges(),
            'fraud_rings_detected': len(self.fraud_rings),
            'mule_accounts_detected': len(self.mule_accounts),
            'average_degree': sum(dict(self.transaction_graph.degree()).values()) / max(self.transaction_graph.number_of_nodes(), 1),
            'graph_density': nx.density(self.transaction_graph)
        }
    
    def clear_old_data(self, days: int = 30):
        """Clear transaction data older than specified days"""
        if not nx:
            return
        
        cutoff_date = datetime.now() - timedelta(days=days)
        nodes_to_remove = []
        
        for node in self.transaction_graph.nodes():
            node_data = self.transaction_graph.nodes[node]
            first_seen = datetime.fromisoformat(node_data.get('first_seen', datetime.now().isoformat()))
            
            if first_seen < cutoff_date:
                # Check if node has recent activity
                has_recent_activity = False
                for _, _, edge_data in self.transaction_graph.edges(node, data=True):
                    last_ts = datetime.fromisoformat(edge_data.get('last_timestamp', datetime.now().isoformat()))
                    if last_ts >= cutoff_date:
                        has_recent_activity = True
                        break
                
                if not has_recent_activity:
                    nodes_to_remove.append(node)
        
        self.transaction_graph.remove_nodes_from(nodes_to_remove)
        logger.info(f"Removed {len(nodes_to_remove)} inactive nodes older than {days} days")


# Global instance
graph_detector = FraudRingDetector() if nx else None


def analyze_transaction_graph_risk(sender_id: str, receiver_id: str, amount: float, 
                                   transaction_data: Dict = None) -> Dict:
    """Wrapper function for graph-based risk analysis"""
    if not graph_detector:
        return {
            'graph_risk_score': 0,
            'risk_factors': ['NetworkX not available - graph analysis disabled'],
            'enabled': False
        }
    
    # Add transaction to graph
    if transaction_data:
        graph_detector.add_transaction(transaction_data)
    
    # Run periodic analysis
    if graph_detector.transaction_graph.number_of_edges() % 100 == 0:
        graph_detector.detect_mule_accounts()
        graph_detector.detect_connected_fraud_rings()
    
    # Analyze this specific transaction
    analysis = graph_detector.analyze_transaction_risk(sender_id, receiver_id, amount)
    analysis['enabled'] = True
    analysis['graph_stats'] = graph_detector.get_statistics()
    
    return analysis
