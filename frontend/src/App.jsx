import { useState, useEffect, useCallback, useRef, useMemo, memo } from 'react';
import { 
  Shield, Activity, AlertTriangle, CheckCircle, XCircle, 
  TrendingUp, Users, Clock, Play, Square, Eye, Bell, 
  BarChart3, Zap, Globe, Filter, ChevronRight, RefreshCw, 
  Search, X, Download, Sun, Moon, Smartphone, CreditCard, 
  Wallet, Building2, Banknote, Network, Brain, Store, AlertOctagon
} from 'lucide-react';
import { 
  PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts';
import api, { WebSocketClient } from './api';
import clsx from 'clsx';

// ============ CONSTANTS ============

const RISK_COLORS = {
  LOW: '#10b981',
  MEDIUM: '#f59e0b', 
  HIGH: '#f97316',
  CRITICAL: '#ef4444'
};

const CHANNEL_CONFIG = {
  upi: { icon: Smartphone, color: 'purple', label: 'UPI' },
  pos: { icon: CreditCard, color: 'blue', label: 'POS' },
  card_online: { icon: CreditCard, color: 'indigo', label: 'Card Online' },
  netbanking: { icon: Building2, color: 'cyan', label: 'NetBanking' },
  wallet: { icon: Wallet, color: 'amber', label: 'Wallet' },
  atm: { icon: Banknote, color: 'emerald', label: 'ATM' }
};

// ============ UTILITIES ============

const formatINR = (amount) => {
  if (amount === undefined || amount === null) return '₹0';
  return new Intl.NumberFormat('en-IN', { 
    style: 'currency', 
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(amount);
};

const formatCompact = (num) => {
  if (num >= 10000000) return `${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000) return `${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num?.toString() || '0';
};

const timeAgo = (timestamp) => {
  if (!timestamp) return 'now';
  const seconds = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  return `${Math.floor(seconds / 86400)}d`;
};

const getRiskBadgeClass = (level) => ({
  LOW: 'badge-low',
  MEDIUM: 'badge-medium',
  HIGH: 'badge-high',
  CRITICAL: 'badge-critical'
}[level] || 'badge-low');

// ============ THEME CONTEXT ============

const useTheme = () => {
  const [dark, setDark] = useState(true);
  
  useEffect(() => {
    document.body.classList.toggle('light', !dark);
  }, [dark]);
  
  return { dark, toggle: () => setDark(d => !d) };
};

// ============ COMPONENTS ============

// Theme Toggle
const ThemeToggle = memo(function ThemeToggle({ dark, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className="p-2 rounded-lg glass-card hover:border-cyan-500/50 transition-all"
      title={dark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
    >
      {dark ? (
        <Sun className="w-4 h-4 text-amber-400" />
      ) : (
        <Moon className="w-4 h-4 text-indigo-500" />
      )}
    </button>
  );
});

// Stats Toggle
const StatsToggle = memo(function StatsToggle({ mode, onChange }) {
  return (
    <div className="flex items-center gap-1 glass-card p-1">
      {['session', 'overall'].map((m) => (
        <button
          key={m}
          onClick={() => onChange(m)}
          className={clsx(
            "px-3 py-1.5 rounded-md text-xs font-medium transition-all",
            mode === m 
              ? "bg-gradient-to-r from-cyan-500 to-teal-500 text-white shadow-lg shadow-cyan-500/30" 
              : "text-gray-400 hover:text-white dark:hover:text-white"
          )}
        >
          {m === 'session' ? 'This Session' : 'All Time'}
        </button>
      ))}
    </div>
  );
});

// Header
const Header = memo(function Header({ 
  connected, simulationActive, onToggleSimulation, onRefresh, 
  modelVersion, dark, onThemeToggle 
}) {
  return (
    <header className="glass sticky top-0 z-50 px-4 sm:px-6 py-3">
      <div className="flex items-center justify-between max-w-[1800px] mx-auto">
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Logo */}
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-teal-500 flex items-center justify-center shadow-lg shadow-cyan-500/30">
              <Eye className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
            </div>
            <div className="hidden sm:block">
              <h1 className="text-lg sm:text-xl font-bold gradient-text">ARGUS</h1>
              <p className="text-[10px] sm:text-xs text-gray-500">Fraud Detection • India</p>
            </div>
          </div>
          
          {/* Version Badge */}
          <div className="hidden md:flex items-center gap-2 px-2 py-1 rounded-full glass-card">
            <span className="text-[10px] sm:text-xs text-cyan-400 font-mono">{modelVersion || 'v3.0.0'}</span>
          </div>
          
          {/* Connection Status */}
          <div className={clsx(
            "flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] sm:text-xs font-medium",
            connected 
              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" 
              : "bg-red-500/15 text-red-400 border border-red-500/30"
          )}>
            <span className={clsx(
              "w-1.5 h-1.5 rounded-full",
              connected ? "bg-emerald-400 live-pulse" : "bg-red-400"
            )} />
            <span className="hidden sm:inline">{connected ? 'Live' : 'Offline'}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-2 sm:gap-3">
          {/* RBI Badge */}
          <div className="hidden lg:flex items-center gap-1.5 text-xs text-gray-500">
            <Globe className="w-3.5 h-3.5" />
            <span>RBI Compliant</span>
          </div>
          
          <ThemeToggle dark={dark} onToggle={onThemeToggle} />
          
          <button
            onClick={onRefresh}
            className="p-2 rounded-lg glass-card hover:border-cyan-500/50 transition-all"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4 text-gray-400" />
          </button>
          
          <button
            onClick={onToggleSimulation}
            className={clsx(
              "flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-lg font-medium transition-all text-sm",
              simulationActive ? "btn-danger" : "btn-primary"
            )}
          >
            {simulationActive ? (
              <><Square className="w-4 h-4" /><span className="hidden sm:inline">Stop</span></>
            ) : (
              <><Play className="w-4 h-4" /><span className="hidden sm:inline">Start</span></>
            )}
          </button>
        </div>
      </div>
    </header>
  );
});

// India Banner
const IndiaBanner = memo(function IndiaBanner({ stats }) {
  return (
    <div className="india-banner rounded-xl p-3 sm:p-4 mb-4">
      <div className="flex flex-wrap items-center justify-between gap-3 sm:gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-400 via-white to-green-500 flex items-center justify-center shadow-lg">
            <span className="text-lg">🇮🇳</span>
          </div>
          <div>
            <p className="font-semibold text-sm">Indian Payment Ecosystem</p>
            <p className="text-xs text-gray-500">UPI • Cards • NetBanking • Wallets • ATM</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4 sm:gap-6 text-xs">
          <div className="text-center">
            <p className="text-gray-500">Volume</p>
            <p className="font-mono font-semibold">{formatINR(stats.total_volume)}</p>
          </div>
          <div className="text-center hidden sm:block">
            <p className="text-gray-500">Avg Txn</p>
            <p className="font-mono font-semibold">
              {formatINR(stats.total_transactions > 0 ? stats.total_volume / stats.total_transactions : 0)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-gray-500">Block Rate</p>
            <p className={clsx(
              "font-mono font-semibold",
              stats.fraud_rate < 1 ? "text-emerald-400" : stats.fraud_rate < 5 ? "text-amber-400" : "text-red-400"
            )}>
              {stats.fraud_rate?.toFixed(2) || 0}%
            </p>
          </div>
          <div className="text-center px-2 py-1 bg-emerald-500/10 rounded-lg border border-emerald-500/30 hidden md:block">
            <p className="text-emerald-400 font-semibold text-[10px] sm:text-xs">✓ RBI</p>
          </div>
        </div>
      </div>
    </div>
  );
});

// Stat Card
const StatCard = memo(function StatCard({ icon: Icon, title, value, subtitle, color = 'cyan' }) {
  const colors = {
    cyan: 'from-cyan-500 to-teal-500 shadow-cyan-500/20',
    emerald: 'from-emerald-500 to-green-500 shadow-emerald-500/20',
    amber: 'from-amber-500 to-orange-500 shadow-amber-500/20',
    red: 'from-red-500 to-rose-500 shadow-red-500/20',
    blue: 'from-blue-500 to-indigo-500 shadow-blue-500/20'
  };
  
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between relative z-10">
        <div className="flex-1 min-w-0">
          <p className="text-[10px] sm:text-xs text-gray-500 mb-1 uppercase tracking-wide">{title}</p>
          <p className="text-lg sm:text-xl font-bold font-mono truncate">{value}</p>
          {subtitle && <p className="text-[10px] sm:text-xs text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
        <div className={clsx(
          "w-8 h-8 sm:w-9 sm:h-9 rounded-lg flex items-center justify-center bg-gradient-to-br shadow-lg shrink-0",
          colors[color]
        )}>
          <Icon className="w-4 h-4 text-white" />
        </div>
      </div>
    </div>
  );
});

// Transaction Row
const TransactionRow = memo(function TransactionRow({ transaction, isNew }) {
  const [expanded, setExpanded] = useState(false);
  const risk = transaction.risk_level || 'LOW';
  const channelKey = (transaction.channel || 'upi').toLowerCase();
  const channel = CHANNEL_CONFIG[channelKey] || CHANNEL_CONFIG.upi;
  const ChannelIcon = channel.icon;
  
  return (
    <div className={clsx(
      "table-row transition-all",
      isNew && "animate-slide-in bg-cyan-500/5"
    )}>
      <div 
        className="p-2.5 sm:p-3 flex items-center gap-2 sm:gap-3 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Risk Indicator */}
        <div className={clsx("risk-indicator h-10 shrink-0", risk.toLowerCase())} />
        
        {/* Channel */}
        <div className={clsx("channel-icon shrink-0", `channel-${channelKey}`)}>
          <ChannelIcon className="w-4 h-4" />
        </div>
        
        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs sm:text-sm truncate max-w-[100px] sm:max-w-none">
              {transaction.transaction_id?.slice(0, 8)}...
            </span>
            <span className={clsx("badge", getRiskBadgeClass(risk))}>{risk}</span>
          </div>
          <div className="flex items-center gap-2 text-[10px] sm:text-xs text-gray-500 mt-0.5">
            <span className="truncate max-w-[80px] sm:max-w-none">{transaction.merchant_category}</span>
            <span>•</span>
            <span className="uppercase">{channel.label}</span>
          </div>
        </div>
        
        {/* Amount */}
        <div className="text-right shrink-0">
          <div className="font-mono font-semibold text-xs sm:text-sm">{formatINR(transaction.amount)}</div>
          <div className="text-[10px] text-gray-500">{timeAgo(transaction.timestamp)}</div>
        </div>
        
        {/* Score */}
        <div className="w-12 sm:w-14 text-right shrink-0 hidden sm:block">
          <div className="font-mono text-sm font-medium" style={{ color: RISK_COLORS[risk] }}>
            {((transaction.risk_score || 0) * 100).toFixed(0)}%
          </div>
        </div>
        
        <ChevronRight className={clsx(
          "w-4 h-4 text-gray-600 transition-transform shrink-0",
          expanded && "rotate-90"
        )} />
      </div>
      
      {expanded && (
        <div className="px-3 pb-3 animate-fade-in">
          {/* Advanced Features Panel */}
          {(transaction.graph_fraud || transaction.sequence_risk || transaction.merchant_risk || transaction.pre_auth || transaction.phishing_detected) && (
            <div className="mb-3 space-y-2">
              {/* Graph Fraud Detection */}
              {transaction.graph_fraud && transaction.graph_fraud.enabled && (
                <div className="glass-card p-2 border-l-2 border-purple-500">
                  <div className="flex items-center gap-2 mb-1">
                    <Network className="w-3.5 h-3.5 text-purple-400" />
                    <span className="text-xs font-semibold text-purple-400">Graph Analysis</span>
                    <span className={`ml-auto text-xs font-mono px-2 py-0.5 rounded-full ${
                      transaction.graph_fraud.graph_risk_score >= 70 ? 'bg-red-500/20 text-red-400' :
                      transaction.graph_fraud.graph_risk_score >= 40 ? 'bg-amber-500/20 text-amber-400' :
                      'bg-emerald-500/20 text-emerald-400'
                    }`}>
                      {transaction.graph_fraud.graph_risk_score?.toFixed(0)}%
                    </span>
                  </div>
                  {transaction.graph_fraud.risk_factors && transaction.graph_fraud.risk_factors.length > 0 && (
                    <div className="text-xs text-gray-400 space-y-0.5 pl-5">
                      {transaction.graph_fraud.risk_factors.slice(0, 2).map((factor, i) => (
                        <div key={i}>• {factor}</div>
                      ))}
                    </div>
                  )}
                  {transaction.graph_fraud.sender_analysis?.is_mule && (
                    <div className="text-xs text-red-400 font-semibold pl-5 mt-1">
                      ⚠️ Mule Account Detected
                    </div>
                  )}
                </div>
              )}
              
              {/* Sequence Risk (Deep Learning) */}
              {transaction.sequence_risk && transaction.sequence_risk.sequence_length > 0 && (
                <div className="glass-card p-2 border-l-2 border-cyan-500">
                  <div className="flex items-center gap-2 mb-1">
                    <Brain className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="text-xs font-semibold text-cyan-400">
                      {transaction.sequence_risk.model_type || 'ML'} Sequence
                    </span>
                    <span className="text-xs text-gray-500">({transaction.sequence_risk.sequence_length} txns)</span>
                    <span className={`ml-auto text-xs font-mono px-2 py-0.5 rounded-full ${
                      transaction.sequence_risk.sequence_risk_score >= 70 ? 'bg-red-500/20 text-red-400' :
                      transaction.sequence_risk.sequence_risk_score >= 40 ? 'bg-amber-500/20 text-amber-400' :
                      'bg-emerald-500/20 text-emerald-400'
                    }`}>
                      {transaction.sequence_risk.sequence_risk_score?.toFixed(0)}%
                    </span>
                  </div>
                  {transaction.sequence_risk.risk_factors && transaction.sequence_risk.risk_factors.length > 0 && (
                    <div className="text-xs text-gray-400 pl-5">
                      {transaction.sequence_risk.risk_factors[0]}
                    </div>
                  )}
                </div>
              )}
              
              {/* Merchant Reputation */}
              {transaction.merchant_risk && (
                <div className="glass-card p-2 border-l-2 border-amber-500">
                  <div className="flex items-center gap-2 mb-1">
                    <Store className="w-3.5 h-3.5 text-amber-400" />
                    <span className="text-xs font-semibold text-amber-400">Merchant Risk</span>
                    <span className="text-xs text-gray-500">
                      Rep: {transaction.merchant_risk.merchant_reputation || 50}/100
                    </span>
                    <span className={`ml-auto text-xs font-mono px-2 py-0.5 rounded-full ${
                      transaction.merchant_risk.merchant_risk_score >= 70 ? 'bg-red-500/20 text-red-400' :
                      transaction.merchant_risk.merchant_risk_score >= 40 ? 'bg-amber-500/20 text-amber-400' :
                      'bg-emerald-500/20 text-emerald-400'
                    }`}>
                      {transaction.merchant_risk.merchant_risk_score?.toFixed(0)}%
                    </span>
                  </div>
                  {transaction.merchant_risk.risk_factors && transaction.merchant_risk.risk_factors.length > 0 && (
                    <div className="text-xs text-gray-400 pl-5">
                      {transaction.merchant_risk.risk_factors[0]}
                    </div>
                  )}
                  {transaction.merchant_risk.chargeback_ratio > 0.01 && (
                    <div className="text-xs text-red-400 pl-5 mt-1">
                      Chargeback: {(transaction.merchant_risk.chargeback_ratio * 100).toFixed(2)}%
                    </div>
                  )}
                </div>
              )}
              
              {/* Pre-Auth Decision */}
              {transaction.pre_auth && (
                <div className={`glass-card p-2 border-l-2 ${
                  transaction.pre_auth.decision === 'BLOCK' ? 'border-red-500' :
                  transaction.pre_auth.decision === 'CHALLENGE' ? 'border-amber-500' :
                  'border-emerald-500'
                }`}>
                  <div className="flex items-center gap-2">
                    <Shield className={`w-3.5 h-3.5 ${
                      transaction.pre_auth.decision === 'BLOCK' ? 'text-red-400' :
                      transaction.pre_auth.decision === 'CHALLENGE' ? 'text-amber-400' :
                      'text-emerald-400'
                    }`} />
                    <span className={`text-xs font-semibold ${
                      transaction.pre_auth.decision === 'BLOCK' ? 'text-red-400' :
                      transaction.pre_auth.decision === 'CHALLENGE' ? 'text-amber-400' :
                      'text-emerald-400'
                    }`}>
                      {transaction.pre_auth.decision}
                    </span>
                    {transaction.pre_auth.decision === 'CHALLENGE' && transaction.pre_auth.auth_method && (
                      <span className="text-xs text-gray-500">
                        → {transaction.pre_auth.auth_method}
                      </span>
                    )}
                    <span className="ml-auto text-xs text-gray-500">
                      {transaction.pre_auth.latency_ms?.toFixed(1)}ms
                    </span>
                  </div>
                  {transaction.pre_auth.block_reasons && transaction.pre_auth.block_reasons.length > 0 && (
                    <div className="text-xs text-red-400 pl-5 mt-1">
                      {transaction.pre_auth.block_reasons[0]}
                    </div>
                  )}
                  {transaction.pre_auth.challenge_reasons && transaction.pre_auth.challenge_reasons.length > 0 && (
                    <div className="text-xs text-amber-400 pl-5 mt-1">
                      {transaction.pre_auth.challenge_reasons[0]}
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
          )}
          
          <div className="glass-card p-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            {/* Scores */}
            <div>
              <p className="text-gray-500 mb-2 font-semibold uppercase tracking-wide text-[10px]">ML Scores</p>
              {['xgboost', 'anomaly_detection', 'rule_engine', 'dynamic_behavior'].map((key) => (
                <div key={key} className="flex justify-between items-center mb-1.5">
                  <span className="text-gray-400 capitalize text-[10px]">{key.replace(/_/g, ' ')}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-12 h-1.5 bg-argus-border rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-cyan-500 to-teal-500 rounded-full"
                        style={{ width: `${(transaction.model_scores?.[key] || 0) * 100}%` }}
                      />
                    </div>
                    <span className="font-mono w-8 text-right text-[10px]">
                      {((transaction.model_scores?.[key] || 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Behavior Analysis */}
            <div>
              <p className="text-gray-500 mb-2 font-semibold uppercase tracking-wide text-[10px]">
                Behavior Analysis
                {transaction.behavior_analysis?.is_behavioral_anomaly && (
                  <span className="ml-1 text-orange-400">⚠️</span>
                )}
              </p>
              <div className="space-y-1 text-gray-400">
                <p className="flex justify-between">
                  <span className="text-gray-500">User Avg:</span> 
                  <span className="font-mono">{formatINR(transaction.behavior_analysis?.user_avg_amount || 0)}</span>
                </p>
                <p className="flex justify-between">
                  <span className="text-gray-500">Z-Score:</span> 
                  <span className={clsx(
                    "font-mono",
                    Math.abs(transaction.behavior_analysis?.amount_zscore || 0) > 3 ? "text-red-400" :
                    Math.abs(transaction.behavior_analysis?.amount_zscore || 0) > 2 ? "text-orange-400" : ""
                  )}>
                    {(transaction.behavior_analysis?.amount_zscore || 0).toFixed(1)}σ
                  </span>
                </p>
                <p className="flex justify-between">
                  <span className="text-gray-500">vs Avg:</span> 
                  <span className={clsx(
                    "font-mono",
                    (transaction.behavior_analysis?.amount_vs_avg_ratio || 1) > 5 ? "text-red-400" :
                    (transaction.behavior_analysis?.amount_vs_avg_ratio || 1) > 3 ? "text-orange-400" : ""
                  )}>
                    {(transaction.behavior_analysis?.amount_vs_avg_ratio || 1).toFixed(1)}x
                  </span>
                </p>
                <p className="flex justify-between">
                  <span className="text-gray-500">Profile:</span> 
                  <span className={clsx(
                    "font-mono",
                    transaction.behavior_analysis?.profile_maturity === 'mature' ? "text-emerald-400" : "text-amber-400"
                  )}>
                    {transaction.behavior_analysis?.profile_maturity || 'new'} ({transaction.behavior_analysis?.transactions_analyzed || 0})
                  </span>
                </p>
              </div>
            </div>
            
            {/* Details */}
            <div>
              <p className="text-gray-500 mb-2 font-semibold uppercase tracking-wide text-[10px]">Details</p>
              <div className="space-y-1 text-gray-400">
                <p><span className="text-gray-500">City:</span> {transaction.city || 'Unknown'}</p>
                <p><span className="text-gray-500">Device:</span> {transaction.is_new_device ? '🆕 New' : '✓ Known'}</p>
                <p><span className="text-gray-500">Location:</span> {transaction.is_new_location ? '📍 New' : '✓ Home'}</p>
                <p><span className="text-gray-500">Latency:</span> {transaction.latency_ms?.toFixed(1) || '5'}ms</p>
              </div>
            </div>
            
            {/* Rules */}
            <div>
              <p className="text-gray-500 mb-2 font-semibold uppercase tracking-wide text-[10px]">
                Rules ({transaction.triggered_rules?.length || 0})
              </p>
              {transaction.triggered_rules?.length > 0 ? (
                <ul className="space-y-1">
                  {transaction.triggered_rules.slice(0, 5).map((rule, i) => (
                    <li key={i} className={clsx(
                      "flex items-start gap-1 text-[10px]",
                      rule.includes('AMOUNT_ZSCORE') || rule.includes('AMOUNT_SPIKE') || rule.includes('DAILY_SPIKE') 
                        ? "text-purple-400" 
                        : "text-orange-400/90"
                    )}>
                      <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5" />
                      <span className="truncate">{rule}</span>
                    </li>
                  ))}
                  {transaction.triggered_rules.length > 5 && (
                    <li className="text-gray-500 text-[10px]">
                      +{transaction.triggered_rules.length - 5} more...
                    </li>
                  )}
                </ul>
              ) : (
                <p className="text-emerald-400/70 flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" />
                  All checks passed
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}, (prev, next) => 
  prev.transaction.transaction_id === next.transaction.transaction_id && 
  prev.isNew === next.isNew
);

// Alert Card
const AlertCard = memo(function AlertCard({ alert, onAction }) {
  const [loading, setLoading] = useState(false);
  
  const handleAction = async (action) => {
    setLoading(true);
    await onAction(alert.id, action);
    setLoading(false);
  };
  
  return (
    <div className={clsx(
      "glass-card p-2.5 border-l-2 transition-all",
      alert.risk_level === 'CRITICAL' ? "border-red-500" : "border-orange-500"
    )}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <AlertTriangle className={clsx(
            "w-4 h-4 shrink-0",
            alert.risk_level === 'CRITICAL' ? "text-red-400" : "text-orange-400"
          )} />
          <div className="min-w-0">
            <p className="font-semibold text-xs">{alert.risk_level}</p>
            <p className="text-[10px] text-gray-500 truncate">
              {formatINR(alert.amount)} • {alert.transaction_id?.slice(0, 8)}
            </p>
          </div>
        </div>
        
        {alert.status === 'pending' ? (
          <div className="flex gap-1 shrink-0">
            <button
              onClick={() => handleAction('dismissed')}
              disabled={loading}
              className="p-1.5 rounded glass-card text-emerald-400 hover:bg-emerald-500/20 transition disabled:opacity-50"
            >
              <CheckCircle className="w-3 h-3" />
            </button>
            <button
              onClick={() => handleAction('confirmed')}
              disabled={loading}
              className="p-1.5 rounded glass-card text-red-400 hover:bg-red-500/20 transition disabled:opacity-50"
            >
              <XCircle className="w-3 h-3" />
            </button>
          </div>
        ) : (
          <span className={clsx(
            "badge text-[10px]",
            alert.status === 'dismissed' ? "badge-low" : "badge-critical"
          )}>
            {alert.status}
          </span>
        )}
      </div>
    </div>
  );
});

// Risk Distribution Chart
const RiskChart = memo(function RiskChart({ data }) {
  const chartData = useMemo(() => [
    { name: 'Low', value: data?.LOW || 0, fill: RISK_COLORS.LOW },
    { name: 'Medium', value: data?.MEDIUM || 0, fill: RISK_COLORS.MEDIUM },
    { name: 'High', value: data?.HIGH || 0, fill: RISK_COLORS.HIGH },
    { name: 'Critical', value: data?.CRITICAL || 0, fill: RISK_COLORS.CRITICAL }
  ], [data]);
  
  const total = chartData.reduce((s, i) => s + i.value, 0);
  
  return (
    <div className="glass-card p-4">
      <h3 className="text-xs font-semibold text-gray-500 mb-3 uppercase tracking-wide">Risk Distribution</h3>
      <div className="h-32">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={30}
              outerRadius={50}
              paddingAngle={3}
              dataKey="value"
            >
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="grid grid-cols-2 gap-2 mt-2">
        {chartData.map((item) => (
          <div key={item.name} className="flex items-center gap-1.5 text-xs">
            <div className="w-2 h-2 rounded-sm" style={{ background: item.fill }} />
            <span className="text-gray-500">{item.name}</span>
            <span className="font-mono ml-auto">
              {total > 0 ? ((item.value / total) * 100).toFixed(0) : 0}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
});

// Channel Distribution
const ChannelChart = memo(function ChannelChart({ transactions }) {
  const data = useMemo(() => {
    const counts = {};
    transactions.forEach(t => {
      const ch = (t.channel || 'upi').toLowerCase();
      counts[ch] = (counts[ch] || 0) + 1;
    });
    return Object.entries(counts)
      .map(([name, value]) => ({ 
        name: CHANNEL_CONFIG[name]?.label || name.toUpperCase(), 
        value,
        key: name
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 5);
  }, [transactions]);
  
  if (data.length === 0) return null;
  
  return (
    <div className="glass-card p-4">
      <h3 className="text-xs font-semibold text-gray-500 mb-3 uppercase tracking-wide">Payment Channels</h3>
      <div className="space-y-2">
        {data.map((item, i) => {
          const colors = ['#06b6d4', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444'];
          return (
            <div key={item.key}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-400">{item.name}</span>
                <span className="font-mono">{item.value}</span>
              </div>
              <div className="h-1.5 bg-argus-border rounded-full overflow-hidden">
                <div 
                  className="h-full rounded-full transition-all"
                  style={{ 
                    width: `${(item.value / (data[0]?.value || 1)) * 100}%`,
                    backgroundColor: colors[i]
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});

// Model Stats
const ModelStatsCard = memo(function ModelStatsCard({ stats }) {
  const features = useMemo(() => 
    Object.entries(stats?.feature_importance || {})
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5),
    [stats?.feature_importance]
  );
  
  const dynamicStats = stats?.dynamic_detection || {};
  
  return (
    <div className="glass-card p-4">
      <h3 className="text-xs font-semibold text-gray-500 mb-3 uppercase tracking-wide flex items-center gap-2">
        <BarChart3 className="w-3 h-3" />
        Model {stats?.version || 'v3.1.0'}
      </h3>
      
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="glass-card p-2 text-center">
          <p className="text-[10px] text-gray-500">User Profiles</p>
          <p className="font-mono text-sm text-cyan-400">{dynamicStats.active_user_profiles || 0}</p>
        </div>
        <div className="glass-card p-2 text-center">
          <p className="text-[10px] text-gray-500">Mature</p>
          <p className="font-mono text-sm text-emerald-400">{dynamicStats.mature_profiles || 0}</p>
        </div>
      </div>
      
      {dynamicStats.enabled && (
        <div className="mb-3 p-2 glass-card border-l-2 border-purple-500">
          <p className="text-[10px] text-purple-400 font-semibold">Dynamic Detection Active</p>
          <p className="text-[9px] text-gray-500 mt-0.5">
            Personalized thresholds based on user behavior
          </p>
        </div>
      )}
      
      {features.length > 0 && (
        <>
          <p className="text-[10px] text-gray-500 mb-2 uppercase">Top Features</p>
          <div className="space-y-1.5">
            {features.map(([name, value]) => (
              <div key={name}>
                <div className="flex justify-between text-[10px] mb-0.5">
                  <span className="text-gray-400 truncate">{name.replace(/_/g, ' ')}</span>
                  <span className="font-mono">{(value * 100).toFixed(0)}%</span>
                </div>
                <div className="h-1 bg-argus-border rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-cyan-500 to-teal-500 rounded-full"
                    style={{ width: `${Math.min(value * 200, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
});

// Filters
const Filters = memo(function Filters({ filters, onChange, onClear, onExport }) {
  return (
    <div className="glass-card p-3 mb-4">
      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
        <div className="flex items-center gap-2 text-gray-500">
          <Filter className="w-4 h-4" />
          <span className="text-xs font-medium hidden sm:inline">Filters</span>
        </div>
        
        <select
          value={filters.riskLevel}
          onChange={(e) => onChange({ ...filters, riskLevel: e.target.value })}
          className="input text-xs py-1.5"
        >
          <option value="all">All Risks</option>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="HIGH">High</option>
          <option value="CRITICAL">Critical</option>
        </select>
        
        <select
          value={filters.channel}
          onChange={(e) => onChange({ ...filters, channel: e.target.value })}
          className="input text-xs py-1.5"
        >
          <option value="all">All Channels</option>
          {Object.entries(CHANNEL_CONFIG).map(([key, cfg]) => (
            <option key={key} value={key}>{cfg.label}</option>
          ))}
        </select>
        
        <div className="relative flex-1 max-w-[200px]">
          <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => onChange({ ...filters, search: e.target.value })}
            className="input text-xs py-1.5 pl-7 w-full"
            placeholder="Search..."
          />
        </div>
        
        <div className="flex gap-1 ml-auto">
          <button 
            onClick={onClear} 
            className="p-1.5 rounded glass-card text-gray-400 hover:text-white transition"
            title="Clear"
          >
            <X className="w-3 h-3" />
          </button>
          <button 
            onClick={onExport} 
            className="p-1.5 rounded glass-card text-gray-400 hover:text-white transition"
            title="Export CSV"
          >
            <Download className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
});

// ============ MAIN APP ============

function App() {
  const theme = useTheme();
  const [connected, setConnected] = useState(false);
  const [simulationActive, setSimulationActive] = useState(false);
  const [statsMode, setStatsMode] = useState('session');
  
  const [sessionStats, setSessionStats] = useState({
    total_transactions: 0, total_blocked: 0, total_flagged: 0,
    total_approved: 0, total_volume: 0, fraud_rate: 0,
    avg_risk_score: 0, avg_latency_ms: 5,
    risk_distribution: { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 }
  });
  
  const [overallStats, setOverallStats] = useState({ ...sessionStats });
  const [transactions, setTransactions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [modelStats, setModelStats] = useState({});
  const [filters, setFilters] = useState({ riskLevel: 'all', channel: 'all', search: '' });
  
  const wsRef = useRef(null);
  const newTxnIds = useRef(new Set());
  
  const stats = statsMode === 'session' ? sessionStats : overallStats;
  
  // WebSocket
  useEffect(() => {
    const ws = new WebSocketClient(
      (data) => {
        switch (data.type) {
          case 'init':
            setOverallStats(data.data.stats || overallStats);
            setTransactions(data.data.recent_transactions || []);
            setAlerts(data.data.recent_alerts || []);
            break;
          case 'transaction':
            const txn = data.data;
            newTxnIds.current.add(txn.transaction_id);
            setTransactions(prev => [txn, ...prev.slice(0, 99)]);
            
            setSessionStats(prev => {
              const n = prev.total_transactions + 1;
              const risk = txn.risk_level || 'LOW';
              const rec = txn.recommendation;
              return {
                ...prev,
                total_transactions: n,
                total_blocked: prev.total_blocked + (rec === 'BLOCK' ? 1 : 0),
                total_flagged: prev.total_flagged + (rec === 'FLAG' || rec === 'REVIEW' ? 1 : 0),
                total_approved: prev.total_approved + (rec === 'APPROVE' ? 1 : 0),
                total_volume: prev.total_volume + (txn.amount || 0),
                fraud_rate: ((prev.total_blocked + (rec === 'BLOCK' ? 1 : 0)) / n) * 100,
                avg_risk_score: ((prev.avg_risk_score * (n-1)) + (txn.risk_score || 0)) / n,
                avg_latency_ms: ((prev.avg_latency_ms * (n-1)) + (txn.latency_ms || 5)) / n,
                risk_distribution: {
                  ...prev.risk_distribution,
                  [risk]: (prev.risk_distribution[risk] || 0) + 1
                }
              };
            });
            
            setTimeout(() => newTxnIds.current.delete(txn.transaction_id), 2000);
            break;
          case 'alert':
            setAlerts(prev => [data.data, ...prev.slice(0, 19)]);
            break;
          case 'stats':
            setOverallStats(prev => ({ ...prev, ...data.data }));
            break;
        }
      },
      () => setConnected(true),
      () => setConnected(false)
    );
    
    ws.connect();
    wsRef.current = ws;
    return () => ws.disconnect();
  }, []);
  
  // Load initial data
  const loadData = useCallback(async () => {
    try {
      const [statsRes, modelRes, simStatus] = await Promise.all([
        api.getStats(),
        api.getModelStats(),
        api.getSimulationStatus()
      ]);
      setOverallStats(prev => ({ ...prev, ...statsRes }));
      setModelStats(modelRes);
      setSimulationActive(simStatus.active);
    } catch (e) {
      console.error('Load error:', e);
    }
  }, []);
  
  useEffect(() => { loadData(); }, [loadData]);
  
  const handleToggleSimulation = async () => {
    try {
      if (simulationActive) {
        await api.stopSimulation();
        setSimulationActive(false);
      } else {
        setSessionStats({
          total_transactions: 0, total_blocked: 0, total_flagged: 0,
          total_approved: 0, total_volume: 0, fraud_rate: 0,
          avg_risk_score: 0, avg_latency_ms: 5,
          risk_distribution: { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 }
        });
        await api.startSimulation();
        setSimulationActive(true);
      }
    } catch (e) {
      console.error('Simulation error:', e);
    }
  };
  
  const handleAlertAction = async (id, action) => {
    try {
      await api.updateAlert(id, action);
      setAlerts(prev => prev.map(a => a.id === id ? { ...a, status: action } : a));
    } catch (e) {
      console.error('Alert error:', e);
    }
  };
  
  const handleExport = async () => {
    try {
      const blob = await api.exportData();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `argus_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Export error:', e);
    }
  };
  
  // Filter transactions
  const filteredTxns = useMemo(() => {
    return transactions.filter(t => {
      if (filters.riskLevel !== 'all' && t.risk_level !== filters.riskLevel) return false;
      if (filters.channel !== 'all' && t.channel?.toLowerCase() !== filters.channel) return false;
      if (filters.search) {
        const s = filters.search.toLowerCase();
        if (!t.transaction_id?.toLowerCase().includes(s) &&
            !t.user_id?.toLowerCase().includes(s) &&
            !t.merchant_category?.toLowerCase().includes(s) &&
            !t.city?.toLowerCase().includes(s)) return false;
      }
      return true;
    });
  }, [transactions, filters]);
  
  return (
    <div className="min-h-screen">
      <Header 
        connected={connected}
        simulationActive={simulationActive}
        onToggleSimulation={handleToggleSimulation}
        onRefresh={loadData}
        modelVersion={modelStats?.version}
        dark={theme.dark}
        onThemeToggle={theme.toggle}
      />
      
      <main className="p-3 sm:p-4 max-w-[1800px] mx-auto">
        <IndiaBanner stats={stats} />
        
        {/* Stats Header */}
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <h2 className="text-xs sm:text-sm font-semibold text-gray-500 uppercase tracking-wide">
            {statsMode === 'session' ? 'Session Stats' : 'Overall Stats'}
          </h2>
          <StatsToggle mode={statsMode} onChange={setStatsMode} />
        </div>
        
        {/* Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-3 mb-4">
          <StatCard icon={Activity} title="Transactions" value={formatCompact(stats.total_transactions)} color="cyan" />
          <StatCard icon={CheckCircle} title="Approved" value={formatCompact(stats.total_approved)} 
                    subtitle={`${stats.total_transactions > 0 ? ((stats.total_approved / stats.total_transactions) * 100).toFixed(0) : 0}%`} color="emerald" />
          <StatCard icon={AlertTriangle} title="Flagged" value={formatCompact(stats.total_flagged)} color="amber" />
          <StatCard icon={XCircle} title="Blocked" value={formatCompact(stats.total_blocked)}
                    subtitle={`${stats.fraud_rate?.toFixed(1) || 0}%`} color="red" />
          <StatCard icon={Shield} title="Avg Risk" value={`${((stats.avg_risk_score || 0) * 100).toFixed(0)}%`} color="blue" />
          <StatCard icon={Zap} title="Latency" value={`${(stats.avg_latency_ms || 5).toFixed(0)}ms`} subtitle="P50" color="cyan" />
        </div>
        
        <Filters 
          filters={filters}
          onChange={setFilters}
          onClear={() => setFilters({ riskLevel: 'all', channel: 'all', search: '' })}
          onExport={handleExport}
        />
        
        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 sm:gap-4">
          {/* Transactions */}
          <div className="lg:col-span-2">
            <div className="glass-card overflow-hidden">
              <div className="p-3 border-b border-argus-border/30 flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  Live Transactions
                  <span className="text-xs text-gray-500 font-normal">({filteredTxns.length})</span>
                </h3>
                {simulationActive && (
                  <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 live-pulse" />
                    Streaming
                  </span>
                )}
              </div>
              
              <div className="max-h-[500px] overflow-y-auto">
                {filteredTxns.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <Activity className="w-10 h-10 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">No transactions yet</p>
                    <p className="text-xs mt-1">Start simulation to see live data</p>
                  </div>
                ) : (
                  filteredTxns.slice(0, 50).map((txn) => (
                    <TransactionRow 
                      key={txn.transaction_id} 
                      transaction={txn}
                      isNew={newTxnIds.current.has(txn.transaction_id)}
                    />
                  ))
                )}
              </div>
            </div>
          </div>
          
          {/* Right Column */}
          <div className="space-y-3 sm:space-y-4">
            <RiskChart data={stats.risk_distribution} />
            <ChannelChart transactions={transactions} />
            
            {/* Alerts */}
            <div className="glass-card overflow-hidden">
              <div className="p-3 border-b border-argus-border/30 flex items-center justify-between">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex items-center gap-2">
                  <Bell className="w-3 h-3 text-orange-400" />
                  Alerts
                </h3>
                <span className="badge badge-high text-[10px]">
                  {alerts.filter(a => a.status === 'pending').length}
                </span>
              </div>
              
              <div className="p-2 space-y-2 max-h-[200px] overflow-y-auto">
                {alerts.length === 0 ? (
                  <div className="text-center text-gray-500 py-4">
                    <Shield className="w-6 h-6 mx-auto mb-1 opacity-30" />
                    <p className="text-xs">No alerts</p>
                  </div>
                ) : (
                  alerts.slice(0, 8).map((alert) => (
                    <AlertCard key={alert.id} alert={alert} onAction={handleAlertAction} />
                  ))
                )}
              </div>
            </div>
            
            <ModelStatsCard stats={modelStats} />
          </div>
        </div>
      </main>
      
      <footer className="glass mt-6 px-4 py-3 text-center text-xs text-gray-500 border-t border-cyan-500/10">
        <p className="gradient-text font-semibold">ARGUS v3.0.0-india</p>
        <p className="text-[10px] mt-0.5">Real-time AI Fraud Detection • XGBoost + Isolation Forest + Rule Engine</p>
      </footer>
    </div>
  );
}

export default App;
