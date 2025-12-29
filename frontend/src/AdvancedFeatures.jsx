// Advanced Features Display Panel Component
// Shows graph fraud detection, deep learning, merchant risk, and case management

import { Shield, Network, Brain, Store, FileText, AlertOctagon } from 'lucide-react';

export const AdvancedFeaturesPanel = ({ transaction }) => {
  if (!transaction) return null;
  
  const { graph_fraud, sequence_risk, merchant_risk, pre_auth } = transaction;
  
  return (
    <div className="mt-3 space-y-2">
      {/* Graph Fraud Detection */}
      {graph_fraud && graph_fraud.enabled && (
        <div className="glass-card p-2 border-l-2 border-purple-500">
          <div className="flex items-center gap-2 mb-1">
            <Network className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-xs font-semibold text-purple-400">Graph Analysis</span>
            <span className={`ml-auto text-xs font-mono px-2 py-0.5 rounded-full ${
              graph_fraud.graph_risk_score >= 70 ? 'bg-red-500/20 text-red-400' :
              graph_fraud.graph_risk_score >= 40 ? 'bg-amber-500/20 text-amber-400' :
              'bg-emerald-500/20 text-emerald-400'
            }`}>
              {graph_fraud.graph_risk_score?.toFixed(0)}%
            </span>
          </div>
          {graph_fraud.risk_factors && graph_fraud.risk_factors.length > 0 && (
            <div className="text-xs text-gray-400 space-y-0.5 pl-5">
              {graph_fraud.risk_factors.slice(0, 2).map((factor, i) => (
                <div key={i}>• {factor}</div>
              ))}
            </div>
          )}
          {graph_fraud.sender_analysis?.is_mule && (
            <div className="text-xs text-red-400 font-semibold pl-5 mt-1">
              ⚠️ Mule Account Detected
            </div>
          )}
        </div>
      )}
      
      {/* Sequence Risk (Deep Learning) */}
      {sequence_risk && sequence_risk.sequence_length > 0 && (
        <div className="glass-card p-2 border-l-2 border-cyan-500">
          <div className="flex items-center gap-2 mb-1">
            <Brain className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-xs font-semibold text-cyan-400">
              {sequence_risk.model_type || 'ML'} Sequence
            </span>
            <span className="text-xs text-gray-500">({sequence_risk.sequence_length} txns)</span>
            <span className={`ml-auto text-xs font-mono px-2 py-0.5 rounded-full ${
              sequence_risk.sequence_risk_score >= 70 ? 'bg-red-500/20 text-red-400' :
              sequence_risk.sequence_risk_score >= 40 ? 'bg-amber-500/20 text-amber-400' :
              'bg-emerald-500/20 text-emerald-400'
            }`}>
              {sequence_risk.sequence_risk_score?.toFixed(0)}%
            </span>
          </div>
          {sequence_risk.risk_factors && sequence_risk.risk_factors.length > 0 && (
            <div className="text-xs text-gray-400 pl-5">
              {sequence_risk.risk_factors[0]}
            </div>
          )}
        </div>
      )}
      
      {/* Merchant Reputation */}
      {merchant_risk && (
        <div className="glass-card p-2 border-l-2 border-amber-500">
          <div className="flex items-center gap-2 mb-1">
            <Store className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-xs font-semibold text-amber-400">Merchant Risk</span>
            <span className="text-xs text-gray-500">
              Rep: {merchant_risk.merchant_reputation || 50}/100
            </span>
            <span className={`ml-auto text-xs font-mono px-2 py-0.5 rounded-full ${
              merchant_risk.merchant_risk_score >= 70 ? 'bg-red-500/20 text-red-400' :
              merchant_risk.merchant_risk_score >= 40 ? 'bg-amber-500/20 text-amber-400' :
              'bg-emerald-500/20 text-emerald-400'
            }`}>
              {merchant_risk.merchant_risk_score?.toFixed(0)}%
            </span>
          </div>
          {merchant_risk.risk_factors && merchant_risk.risk_factors.length > 0 && (
            <div className="text-xs text-gray-400 pl-5">
              {merchant_risk.risk_factors[0]}
            </div>
          )}
          {merchant_risk.chargeback_ratio > 0.01 && (
            <div className="text-xs text-red-400 pl-5 mt-1">
              Chargeback: {(merchant_risk.chargeback_ratio * 100).toFixed(2)}%
            </div>
          )}
        </div>
      )}
      
      {/* Pre-Auth Decision */}
      {pre_auth && (
        <div className={`glass-card p-2 border-l-2 ${
          pre_auth.decision === 'BLOCK' ? 'border-red-500' :
          pre_auth.decision === 'CHALLENGE' ? 'border-amber-500' :
          'border-emerald-500'
        }`}>
          <div className="flex items-center gap-2">
            <Shield className={`w-3.5 h-3.5 ${
              pre_auth.decision === 'BLOCK' ? 'text-red-400' :
              pre_auth.decision === 'CHALLENGE' ? 'text-amber-400' :
              'text-emerald-400'
            }`} />
            <span className={`text-xs font-semibold ${
              pre_auth.decision === 'BLOCK' ? 'text-red-400' :
              pre_auth.decision === 'CHALLENGE' ? 'text-amber-400' :
              'text-emerald-400'
            }`}>
              {pre_auth.decision}
            </span>
            {pre_auth.decision === 'CHALLENGE' && pre_auth.auth_method && (
              <span className="text-xs text-gray-500">
                → {pre_auth.auth_method}
              </span>
            )}
            <span className="ml-auto text-xs text-gray-500">
              {pre_auth.latency_ms?.toFixed(1)}ms
            </span>
          </div>
          {pre_auth.block_reasons && pre_auth.block_reasons.length > 0 && (
            <div className="text-xs text-red-400 pl-5 mt-1">
              {pre_auth.block_reasons[0]}
            </div>
          )}
          {pre_auth.challenge_reasons && pre_auth.challenge_reasons.length > 0 && (
            <div className="text-xs text-amber-400 pl-5 mt-1">
              {pre_auth.challenge_reasons[0]}
            </div>
          )}
        </div>
      )}
      
      {/* Phishing Attack Detected */}
      {transaction.phishing_detected && (
        <div className="glass-card p-2 border-l-2 border-rose-500 bg-rose-500/5">
          <div className="flex items-center gap-2">
            <AlertOctagon className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-xs font-semibold text-rose-400">
              PHISHING ATTACK
            </span>
            <span className="text-xs text-gray-500">{transaction.attack_type}</span>
          </div>
          {transaction.phishing_indicators && transaction.phishing_indicators.length > 0 && (
            <div className="text-xs text-rose-300 pl-5 mt-1">
              {transaction.phishing_indicators[0]}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Stats Panel for Advanced Features
export const AdvancedStatsPanel = () => {
  const [stats, setStats] = React.useState({
    graph: null,
    merchants: null,
    cases: null
  });
  
  React.useEffect(() => {
    const fetchStats = async () => {
      try {
        const [graphRes, merchantsRes, casesRes] = await Promise.all([
          fetch('/api/analytics/graph-stats'),
          fetch('/api/analytics/high-risk-merchants?threshold=70'),
          fetch('/api/cases/stats')
        ]);
        
        setStats({
          graph: await graphRes.json(),
          merchants: await merchantsRes.json(),
          cases: await casesRes.json()
        });
      } catch (err) {
        console.error('Failed to fetch advanced stats:', err);
      }
    };
    
    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Update every 30s
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Graph Detection Stats */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Network className="w-5 h-5 text-purple-400" />
          <h3 className="text-sm font-semibold">Fraud Rings</h3>
        </div>
        {stats.graph && stats.graph.statistics && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Detected Rings</span>
              <span className="font-mono text-purple-400">
                {stats.graph.fraud_rings?.length || 0}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Mule Accounts</span>
              <span className="font-mono text-amber-400">
                {stats.graph.mule_accounts?.length || 0}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Cyclic Patterns</span>
              <span className="font-mono text-red-400">
                {stats.graph.cyclic_patterns || 0}
              </span>
            </div>
          </div>
        )}
      </div>
      
      {/* High-Risk Merchants */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Store className="w-5 h-5 text-amber-400" />
          <h3 className="text-sm font-semibold">Risk Merchants</h3>
        </div>
        {stats.merchants && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">High-Risk</span>
              <span className="font-mono text-red-400">
                {stats.merchants.count || 0}
              </span>
            </div>
            {stats.merchants.merchants?.slice(0, 2).map((m, i) => (
              <div key={i} className="text-xs text-gray-500 truncate">
                {m.merchant_name}: {m.risk_score}%
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Case Queue */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <FileText className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-semibold">Review Queue</h3>
        </div>
        {stats.cases && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Pending</span>
              <span className="font-mono text-cyan-400">
                {stats.cases.pending_by_priority ? 
                  Object.values(stats.cases.pending_by_priority).reduce((a, b) => a + b, 0) : 0}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Fraud Rate</span>
              <span className="font-mono text-red-400">
                {stats.cases.fraud_confirmation_rate?.toFixed(1) || 0}%
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Avg Review</span>
              <span className="font-mono text-gray-400">
                {stats.cases.avg_review_time_hours?.toFixed(1) || 0}h
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
