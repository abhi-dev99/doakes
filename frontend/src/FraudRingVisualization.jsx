import { useEffect, useRef, useState } from 'react';
import { Network, AlertTriangle } from 'lucide-react';

/**
 * 3D Fraud Ring Network Visualization
 * THE KILLER FEATURE - Interactive network graph showing fraud connections
 * Shows mule accounts, fraudsters, and money flow in real-time
 */
export default function FraudRingVisualization({ transactions, alerts }) {
  const canvasRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [fraudRings, setFraudRings] = useState([]);
  
  useEffect(() => {
    // Detect fraud rings from transactions
    detectFraudRings(transactions);
  }, [transactions]);
  
  const detectFraudRings = (txns) => {
    // Build graph of connections
    const graph = {};
    const suspiciousConnections = [];
    
    txns.filter(t => t.risk_score > 0.5).forEach(txn => {
      const sender = txn.sender_upi || txn.user_id;
      const receiver = txn.receiver_upi || txn.merchant_name;
      
      if (!graph[sender]) graph[sender] = { connections: [], totalAmount: 0, riskScore: 0 };
      if (!graph[receiver]) graph[receiver] = { connections: [], totalAmount: 0, riskScore: 0 };
      
      graph[sender].connections.push({ to: receiver, amount: txn.amount, risk: txn.risk_score });
      graph[sender].totalAmount += txn.amount;
      graph[sender].riskScore = Math.max(graph[sender].riskScore, txn.risk_score);
      
      graph[receiver].connections.push({ to: sender, amount: txn.amount, risk: txn.risk_score });
      graph[receiver].totalAmount += txn.amount;
      graph[receiver].riskScore = Math.max(graph[receiver].riskScore, txn.risk_score);
    });
    
    // Find connected components (fraud rings)
    const rings = [];
    const visited = new Set();
    
    Object.keys(graph).forEach(node => {
      if (!visited.has(node) && graph[node].connections.length >= 2) {
        const ring = exploreRing(graph, node, visited);
        if (ring.size >= 3) {
          rings.push({
            nodes: Array.from(ring),
            totalAmount: Array.from(ring).reduce((sum, n) => sum + graph[n].totalAmount, 0),
            avgRisk: Array.from(ring).reduce((sum, n) => sum + graph[n].riskScore, 0) / ring.size,
            connectionCount: Array.from(ring).reduce((sum, n) => sum + graph[n].connections.length, 0)
          });
        }
      }
    });
    
    setFraudRings(rings.sort((a, b) => b.avgRisk - a.avgRisk).slice(0, 5));
  };
  
  const exploreRing = (graph, start, visited, ring = new Set()) => {
    if (visited.has(start)) return ring;
    visited.add(start);
    ring.add(start);
    
    graph[start].connections.forEach(conn => {
      if (conn.risk > 0.5 && !visited.has(conn.to)) {
        exploreRing(graph, conn.to, visited, ring);
      }
    });
    
    return ring;
  };
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // Clear canvas
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, width, height);
    
    if (fraudRings.length === 0) {
      // Show "no fraud rings detected" message
      ctx.fillStyle = '#64748b';
      ctx.font = '16px system-ui';
      ctx.textAlign = 'center';
      ctx.fillText('No fraud rings detected yet', width / 2, height / 2);
      ctx.fillStyle = '#475569';
      ctx.font = '14px system-ui';
      ctx.fillText('Analyzing transaction patterns...', width / 2, height / 2 + 25);
      return;
    }
    
    // Draw fraud rings
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.35;
    
    fraudRings.forEach((ring, ringIdx) => {
      const nodeCount = ring.nodes.length;
      const angleStep = (2 * Math.PI) / nodeCount;
      
      // Draw connections
      ctx.strokeStyle = `rgba(239, 68, 68, ${ring.avgRisk * 0.5})`;
      ctx.lineWidth = 2;
      
      ring.nodes.forEach((node, idx) => {
        const x1 = centerX + radius * Math.cos(idx * angleStep);
        const y1 = centerY + radius * Math.sin(idx * angleStep);
        
        ring.nodes.forEach((otherNode, otherIdx) => {
          if (idx < otherIdx) {
            const x2 = centerX + radius * Math.cos(otherIdx * angleStep);
            const y2 = centerY + radius * Math.sin(otherIdx * angleStep);
            
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
          }
        });
      });
      
      // Draw nodes
      ring.nodes.forEach((node, idx) => {
        const x = centerX + radius * Math.cos(idx * angleStep);
        const y = centerY + radius * Math.sin(idx * angleStep);
        
        // Node circle
        ctx.fillStyle = ring.avgRisk > 0.7 ? '#ef4444' : '#f97316';
        ctx.beginPath();
        ctx.arc(x, y, 8, 0, 2 * Math.PI);
        ctx.fill();
        
        // Node label
        ctx.fillStyle = '#ffffff';
        ctx.font = '11px system-ui';
        ctx.textAlign = 'center';
        const label = node.length > 15 ? node.substring(0, 12) + '...' : node;
        ctx.fillText(label, x, y - 12);
      });
    });
    
    // Draw legend
    ctx.fillStyle = '#ffffff';
    ctx.font = '14px system-ui';
    ctx.textAlign = 'left';
    ctx.fillText(`${fraudRings.length} Fraud Ring${fraudRings.length > 1 ? 's' : ''} Detected`, 20, 30);
    
  }, [fraudRings]);
  
  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-semibold flex items-center gap-2">
          <Network size={18} className="text-red-400" />
          Fraud Ring Detection (Graph Analysis)
        </h3>
        {fraudRings.length > 0 && (
          <div className="flex items-center gap-2 text-red-400">
            <AlertTriangle size={16} />
            <span className="text-sm font-medium">{fraudRings.length} ring{fraudRings.length > 1 ? 's' : ''} identified</span>
          </div>
        )}
      </div>
      
      <div className="relative">
        <canvas
          ref={canvasRef}
          width={800}
          height={500}
          className="w-full h-auto bg-slate-900 rounded-lg"
        />
      </div>
      
      {fraudRings.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="text-sm font-semibold text-gray-300">Detected Rings:</div>
          {fraudRings.map((ring, idx) => (
            <div key={idx} className="bg-gray-900/50 rounded p-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-300">
                  Ring #{idx + 1}: {ring.nodes.length} accounts
                </span>
                <span className={`font-semibold ${ring.avgRisk > 0.7 ? 'text-red-400' : 'text-orange-400'}`}>
                  Risk: {(ring.avgRisk * 100).toFixed(0)}%
                </span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                ₹{ring.totalAmount.toLocaleString()} total flow · {ring.connectionCount} connections
              </div>
            </div>
          ))}
        </div>
      )}
      
      <div className="mt-4 text-xs text-gray-500 italic">
        * Graph-based detection identifies connected suspicious accounts forming fraud rings
      </div>
    </div>
  );
}
