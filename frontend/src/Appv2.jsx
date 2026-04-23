import { useState, useEffect, useRef, useMemo, memo } from 'react';
import { 
  Shield, Activity, AlertTriangle, CheckCircle, XCircle, 
  TrendingUp, Users, Clock, Play, Square, Eye, Bell, 
  BarChart3, Zap, Globe, Filter, ChevronRight, RefreshCw, 
  Search, X, Download, Sun, Moon, Smartphone, CreditCard, 
  Wallet, Building2, Banknote, Network, Brain, Store, AlertOctagon,
  LayoutDashboard, List, Settings, LogOut, ChevronLeft,
  PauseCircle, Cpu, Wifi, MapPin, Copy
} from 'lucide-react';
import { 
  AreaChart, Area, PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import api, { WebSocketClient } from './api';
import clsx from 'clsx';

// ============ CONSTANTS ============
const RISK_COLORS = {
  LOW: '#34C759', 
  MEDIUM: '#FF9500', 
  HIGH: '#FF3B30', 
  CRITICAL: '#FF3B30'
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
  if (seconds <= 0) return 'Just now';
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

const formatRuleName = (rule) => {
  if (!rule) return '';
  return rule.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ');
};

// ============ THEME CONTEXT ============
const useTheme = () => {
  const [theme, setTheme] = useState('dark');
  useEffect(() => {
    if (theme === 'dark') document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
  }, [theme]);
  return { theme, toggle: () => setTheme(t => t === 'dark' ? 'light' : 'dark') };
};

// ============ COMPONENTS ============

const ThemeToggle = memo(function ThemeToggle({ theme, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className="p-2 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 transition-all text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-[#F5F5F7] z-50 relative"
      title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
    >
      {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
    </button>
  );
});

const StatCard = memo(function StatCard({ icon: Icon, title, value, subtitle, highlight = false, colorClass = "" }) {
  return (
    <div className={clsx("glass-card p-5 relative overflow-hidden transition-all", highlight ? "border-apple-red/50 shadow-apple-red/20 shadow-lg" : "border-white/20 dark:border-white/5")}>
      <div className="flex items-start justify-between relative z-10">
        <div className="flex-1 min-w-0">
          <p className="text-[10px] sm:text-xs text-gray-500 mb-1 font-semibold uppercase tracking-wider">{title}</p>
          <p className={clsx("text-2xl sm:text-3xl font-bold font-sans tracking-tight truncate", colorClass ? colorClass : "text-[#1D1D1F] dark:text-[#F5F5F7]")}>{value}</p>
          {subtitle && <p className="text-[10px] sm:text-xs text-gray-500 mt-1 font-medium">{subtitle}</p>}
        </div>
        <div className={clsx("w-10 h-10 rounded-full flex items-center justify-center shrink-0", highlight ? "bg-apple-red/10 text-apple-red" : "bg-gray-100 dark:bg-[#2C2C2E] text-gray-700 dark:text-gray-300")}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      {highlight && <div className="absolute top-0 right-0 w-16 h-16 bg-apple-red/10 blur-2xl rounded-full" />}
    </div>
  );
});

// Notification System
const NotificationToast = memo(function NotificationToast({ message, type = 'info', onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className={clsx(
      "fixed bottom-8 right-8 z-[200] flex items-center gap-3 px-5 py-3 rounded-2xl backdrop-blur-xl border shadow-2xl animate-slide-up",
      type === 'success' ? "bg-emerald-500/20 border-emerald-500/30 text-emerald-400" : "bg-white/10 border-white/20 text-white"
    )}>
      {type === 'success' ? <CheckCircle size={18} /> : <Info size={18} />}
      <span className="text-sm font-medium">{message}</span>
      <button onClick={onClose} className="ml-2 hover:opacity-70 transition-opacity">
        <X size={14} />
      </button>
    </div>
  );
});

// Advanced Data Density Inspector Panel (Pop-out Modal)
const TransactionInspector = memo(function TransactionInspector({ transaction, onClose, sidebarOpen }) {
  if (!transaction) return null;
  const risk = transaction.risk_level || 'LOW';

  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const handleCopyId = () => {
    navigator.clipboard.writeText(transaction.transaction_id);
    window.dispatchEvent(new CustomEvent('argus-notify', { 
      detail: { message: 'Transaction ID copied to clipboard', type: 'success' } 
    }));
  };

  const handleCopyLogs = () => {
    const logData = JSON.stringify(transaction, null, 2);
    navigator.clipboard.writeText(logData);
    window.dispatchEvent(new CustomEvent('argus-notify', { 
      detail: { message: 'Raw log JSON copied to clipboard', type: 'success' } 
    }));
  };

  const handleExport = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(transaction, null, 2));
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", `txn_${transaction.transaction_id}.json`);
    dlAnchorElem.click();
  };

  return (
    <div className={clsx(
      "fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-8 bg-black/40 backdrop-blur-md animate-fade-in transition-all duration-300",
      sidebarOpen ? "left-52" : "left-16"
    )} onClick={onClose}>
      <div 
        className="bg-white/10 dark:bg-[#1C1C1E]/60 backdrop-blur-[40px] rounded-[32px] w-full max-w-4xl max-h-[90vh] shadow-[0_32px_64px_-16px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col border border-white/20 dark:border-white/10 relative ring-1 ring-white/20"
        onClick={e => e.stopPropagation()}
      >
        
        {/* Header - Redesigned for High-Value Intel */}
        <div className="px-8 py-6 border-b border-white/10 flex items-center justify-between bg-white/5 dark:bg-black/20">
          <div className="flex items-center gap-6">
            <div className={clsx("px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-[0.2em] shadow-lg", {
              'bg-apple-green/20 text-apple-green border border-apple-green/30': risk === 'LOW',
              'bg-apple-orange/20 text-apple-orange border border-apple-orange/30': risk === 'MEDIUM',
              'bg-apple-red text-white border border-apple-red shadow-apple-red/40': risk === 'HIGH' || risk === 'CRITICAL'
            })}>
              {risk} RISK
            </div>
            <div className="h-8 w-[1px] bg-white/10" />
            <div>
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-0.5">Value</p>
              <p className="text-2xl font-black font-mono tracking-tighter text-[#1D1D1F] dark:text-[#F5F5F7] leading-none">
                {formatINR(transaction.amount)}
              </p>
            </div>
            <div className="h-8 w-[1px] bg-white/10" />
            <div>
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-0.5">Channel</p>
              <p className="text-sm font-black text-apple-blue uppercase tracking-tight leading-none">
                {transaction.channel}
              </p>
            </div>
            <div className="h-8 w-[1px] bg-white/10" />
            <div>
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-0.5">Engine Decision</p>
              <p className={clsx("text-sm font-black uppercase tracking-tight leading-none", {
                'text-apple-green': transaction.recommendation === 'APPROVE',
                'text-apple-orange': transaction.recommendation === 'FLAG' || transaction.recommendation === 'REVIEW',
                'text-apple-red': transaction.recommendation === 'BLOCK'
              })}>
                {transaction.recommendation || 'APPROVE'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex flex-col items-end">
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-0.5 text-right">Transaction ID</p>
              <button 
                onClick={handleCopyId}
                className="group flex items-center gap-2 hover:text-apple-blue transition-colors"
                title="Copy Transaction ID"
              >
                <span className="text-gray-400 font-mono text-xs truncate max-w-[150px] sm:max-w-[250px] group-hover:text-apple-blue">{transaction.transaction_id}</span>
                <Copy className="w-3.5 h-3.5 text-gray-500 group-hover:text-apple-blue shrink-0" />
              </button>
            </div>
            <div className="h-8 w-[1px] bg-white/10 mx-2" />
            <div className="flex items-center gap-2">
              <button 
                onClick={handleCopyLogs} 
                className="p-2.5 rounded-full hover:bg-white/10 text-gray-400 transition-all hover:scale-110 active:scale-95" 
                title="Copy Raw Logs"
              >
                <Copy className="w-5 h-5" />
              </button>
              <button 
                onClick={handleExport} 
                className="p-2.5 rounded-full hover:bg-white/10 text-gray-400 transition-all hover:scale-110 active:scale-95" 
                title="Export JSON"
              >
                <Download className="w-5 h-5" />
              </button>
              <button onClick={onClose} className="p-2.5 rounded-full bg-black/20 hover:bg-apple-red text-white transition-all hover:rotate-90 active:scale-90">
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 grid grid-cols-1 lg:grid-cols-12 gap-6 md:gap-8">
          
          {/* Left Column: Entity & Execution Context */}
          <div className="lg:col-span-4 space-y-6">
            
            <div className="glass-card p-5 border border-white/10 dark:border-white/5 bg-white/40 dark:bg-[#1C1C1E]/40 backdrop-blur-xl">
               <div className="flex items-center gap-2 mb-4 text-gray-500 uppercase tracking-widest text-xs font-bold border-b border-[#E5E5EA] dark:border-[#3A3A3C] pb-2">
                  <Users className="w-4 h-4" /> Entity Context
               </div>
               <div className="space-y-4 text-sm">
                  <div className="flex flex-col">
                    <span className="text-gray-500 text-[10px] uppercase font-bold tracking-widest">User Identity</span>
                    <button 
                      onClick={() => window.dispatchEvent(new CustomEvent('argus-navigate', { detail: { view: 'Profiles', user_id: transaction.user_id } }))}
                      className="text-apple-blue font-mono font-bold text-base hover:underline text-left mt-0.5 flex items-center gap-1 group"
                    >
                      {transaction.user_id}
                      <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-gray-500 text-[10px] uppercase font-bold tracking-widest">Timestamp</span>
                    <span className="text-[#1D1D1F] dark:text-[#F5F5F7] font-mono mt-0.5">{new Date(transaction.timestamp).toLocaleString()}</span>
                  </div>
               </div>
            </div>

            <div className="glass-card p-5 border border-white/10 dark:border-white/5 bg-white/40 dark:bg-[#1C1C1E]/40 backdrop-blur-xl">
               <div className="flex items-center gap-2 mb-4 text-gray-500 uppercase tracking-widest text-xs font-bold border-b border-[#E5E5EA] dark:border-[#3A3A3C] pb-2">
                  <Network className="w-4 h-4" /> Network & Origin
               </div>
               <div className="space-y-3 font-mono text-sm">
                  <div className="flex justify-between items-center"><span className="text-gray-500 font-sans text-[10px] uppercase font-bold tracking-widest">IP Address</span> <span className="text-[#1D1D1F] dark:text-[#F5F5F7]">{transaction.ip_address || '192.168.1.1'}</span></div>
                  <div className="flex justify-between items-center"><span className="text-gray-500 font-sans text-[10px] uppercase font-bold tracking-widest">Device ID</span> <span className="truncate w-32 text-right text-[#1D1D1F] dark:text-[#F5F5F7]">{transaction.device_id || 'dev_8891abc'}</span></div>
                  <div className="flex justify-between items-center"><span className="text-gray-500 font-sans text-[10px] uppercase font-bold tracking-widest">Location</span> <span className="text-[#1D1D1F] dark:text-[#F5F5F7] text-right truncate w-32">{transaction.city || 'Unknown'}, {transaction.state || 'IN'}</span></div>
               </div>
            </div>

            <div className="glass-card p-5 border border-white/10 dark:border-white/5 bg-white/40 dark:bg-[#1C1C1E]/40 backdrop-blur-xl">
               <div className="flex items-center gap-2 mb-4 text-gray-500 uppercase tracking-widest text-xs font-bold border-b border-[#E5E5EA] dark:border-[#3A3A3C] pb-2">
                  <Cpu className="w-4 h-4" /> Execution Trace
               </div>
               <div className="grid grid-cols-2 gap-3">
                  <div className="bg-black/5 dark:bg-white/5 p-3 rounded-lg border border-[#E5E5EA] dark:border-[#3A3A3C]">
                     <span className="text-[10px] text-gray-500 block uppercase font-bold tracking-widest mb-1">Pre-Auth</span>
                     <span className={clsx("font-mono text-sm font-bold uppercase", transaction.pre_auth_decision?.includes('BLOCK') ? 'text-apple-red' : 'text-apple-green')}>{transaction.pre_auth_decision || 'ALLOW'}</span>
                  </div>
                  <div className="bg-black/5 dark:bg-white/5 p-3 rounded-lg border border-[#E5E5EA] dark:border-[#3A3A3C]">
                     <span className="text-[10px] text-gray-500 block uppercase font-bold tracking-widest mb-1">Compute</span>
                     <span className="font-mono text-sm font-bold text-[#1D1D1F] dark:text-[#F5F5F7]">{transaction.pre_auth_latency_ms?.toFixed(2) || '14.50'}ms</span>
                  </div>
                  <div className="col-span-2 bg-black/5 dark:bg-white/5 p-3 rounded-lg border border-[#E5E5EA] dark:border-[#3A3A3C] flex justify-between items-center">
                     <span className="text-[10px] text-gray-500 block uppercase font-bold tracking-widest">Total Latency</span>
                     <span className="font-mono text-base font-bold text-apple-blue">{transaction.latency_ms?.toFixed(2) || '42.10'}ms</span>
                  </div>
               </div>
            </div>

          </div>

          {/* Right Column: Risk Analysis (The WHY) */}
          <div className="lg:col-span-8 space-y-6 flex flex-col">
            
            {/* Primary Analysis: Triggered Rules */}
            <div className="glass-card p-6 border border-apple-red/20 dark:border-apple-red/10 shadow-[0_8px_32px_rgba(255,59,48,0.05)] bg-white/40 dark:bg-[#1C1C1E]/40 backdrop-blur-xl flex-1">
               <div className="flex items-center gap-2 mb-6 text-gray-500 uppercase tracking-widest text-xs font-bold border-b border-[#E5E5EA] dark:border-[#3A3A3C] pb-2">
                  <AlertOctagon className="w-4 h-4 text-apple-red" /> Anomaly Vectors
               </div>
               
               {transaction.triggered_rules && transaction.triggered_rules.length > 0 ? (
                 <div className="space-y-3">
                   {transaction.triggered_rules.map((r, i) => (
                     <div key={i} className="flex items-center gap-3 bg-gradient-to-r from-apple-red/10 to-transparent p-3 rounded-xl border-l-4 border-l-apple-red">
                        <AlertTriangle className="w-5 h-5 text-apple-red shrink-0" />
                        <div className="text-sm font-bold text-[#1D1D1F] dark:text-[#F5F5F7] leading-tight">{formatRuleName(r)}</div>
                     </div>
                   ))}
                 </div>
               ) : (
                 <div className="flex items-center justify-center h-24 gap-2 text-apple-green text-sm font-bold bg-apple-green/5 rounded-xl border border-apple-green/20">
                   <CheckCircle className="w-5 h-5" /> All integrity checks passed.
                 </div>
               )}

               <div className="mt-6 pt-6 border-t border-[#E5E5EA] dark:border-[#3A3A3C] grid grid-cols-2 sm:grid-cols-4 gap-4">
                 <div>
                    <span className="text-gray-500 text-[10px] uppercase font-bold tracking-widest mb-1 block">Z-Score</span>
                    <div className="text-2xl font-mono tracking-tighter flex items-center gap-1 text-[#1D1D1F] dark:text-[#F5F5F7]">
                      {transaction.amount_zscore?.toFixed(2) || '0.00'}<span className="text-apple-orange text-lg">σ</span>
                    </div>
                 </div>
                 <div>
                    <span className="text-gray-500 text-[10px] uppercase font-bold tracking-widest mb-1 block">Risk Score</span>
                    <div className={clsx("text-2xl font-mono tracking-tighter", {
                       'text-apple-green': risk === 'LOW',
                       'text-apple-orange': risk === 'MEDIUM',
                       'text-apple-red': risk === 'HIGH' || risk === 'CRITICAL'
                    })}>
                      {((transaction.risk_score || 0) * 100).toFixed(2)}%
                    </div>
                 </div>
                 <div>
                    <span className="text-gray-500 text-[10px] uppercase font-bold tracking-widest mb-1 block">Profile Maturity</span>
                    <div className={clsx("text-sm font-bold uppercase", transaction.behavior_analysis?.profile_maturity === 'mature' ? 'text-apple-green' : 'text-apple-orange')}>
                      {transaction.behavior_analysis?.profile_maturity || 'building'}
                    </div>
                    <div className="text-[10px] text-gray-500 font-mono mt-0.5">{transaction.behavior_analysis?.transactions_analyzed || 0} txns analyzed</div>
                 </div>
                 <div>
                    <span className="text-gray-500 text-[10px] uppercase font-bold tracking-widest mb-1 block">User Avg Txn</span>
                    <div className="text-sm font-mono font-bold text-[#1D1D1F] dark:text-[#F5F5F7]">
                      {formatINR(transaction.behavior_analysis?.user_avg_amount || 0)}
                    </div>
                    <div className="text-[10px] text-gray-500 font-mono mt-0.5">{transaction.amount_vs_avg_ratio?.toFixed(1) || '1.0'}x avg</div>
                 </div>
               </div>
            </div>

            {/* Compact Pipeline Signals v4.0 */}
            <div className="glass-card p-6 border border-white/10 dark:border-white/5 bg-white/40 dark:bg-[#1C1C1E]/40 backdrop-blur-xl">
               <div className="flex items-center justify-between mb-4 border-b border-[#E5E5EA] dark:border-[#3A3A3C] pb-2">
                  <div className="flex items-center gap-2 text-gray-500 uppercase tracking-widest text-xs font-bold">
                    <Brain className="w-4 h-4" /> Pipeline Engine v4.0
                  </div>
                  <div className="text-[10px] font-bold text-apple-blue uppercase tracking-widest">Ensemble Confidence</div>
               </div>
               
               <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {[
                    { label: 'XGBoost', score: transaction.model_scores?.xgboost || 0, color: 'bg-apple-blue' },
                    { label: 'LightGBM', score: transaction.model_scores?.lightgbm || 0, color: 'bg-indigo-500' },
                    { label: 'IsoForest', score: transaction.model_scores?.anomaly_detection || 0, color: 'bg-apple-orange' },
                    { label: 'DynBehavior', score: transaction.model_scores?.dynamic_behavior || 0, color: 'bg-[#BF5AF2]' },
                  ].map((model, idx) => (
                    <div key={idx} className="bg-black/5 dark:bg-white/5 p-3 rounded-xl border border-[#E5E5EA] dark:border-[#3A3A3C] flex flex-col justify-between">
                       <span className="text-[10px] text-gray-500 block uppercase font-bold tracking-wider mb-2">{model.label}</span>
                       <div className="flex items-end justify-between gap-2">
                         <div className="flex-1 h-1.5 bg-gray-200 dark:bg-[#3A3A3C] rounded-full overflow-hidden shadow-inner mb-1">
                           <div className={`h-full ${model.color} transition-all duration-500`} style={{width: `${model.score*100}%`}} />
                         </div>
                         <span className="font-mono text-sm font-bold leading-none">{((model.score) * 100).toFixed(0)}%</span>
                       </div>
                    </div>
                  ))}
               </div>
            </div>

          </div>

        </div>
      </div>
    </div>
  );
});

// Transaction Row with Strict CSS Grid
const TransactionRowDesktop = memo(function TransactionRowDesktop({ transaction, isNew, onOpenInspector }) {
  const risk = transaction.risk_level || 'LOW';
  const channelKey = (transaction.channel || 'upi').toLowerCase();
  const channel = CHANNEL_CONFIG[channelKey] || CHANNEL_CONFIG.upi;
  const ChannelIcon = channel.icon;

  return (
    <div 
      className={clsx(
        "grid grid-cols-12 gap-4 items-center px-6 py-4 select-none border-b border-[#E5E5EA] dark:border-[#3A3A3C] transition-all hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer group relative",
        isNew && "bg-apple-blue/5 dark:bg-apple-blue/10",
        (risk === 'HIGH' || risk === 'CRITICAL') && "bg-apple-red/5 border-l-4 border-l-apple-red shadow-[inset_4px_0_12px_rgba(255,59,48,0.1)]"
      )}
      onClick={() => onOpenInspector(transaction)}
    >
      <div className="col-span-3 flex items-center gap-3">
        <div className={clsx("w-2 h-2 rounded-full shrink-0", {
          'bg-apple-green': risk === 'LOW',
          'bg-apple-orange': risk === 'MEDIUM',
          'bg-apple-red shadow-[0_0_8px_rgba(255,59,48,0.6)]': risk === 'HIGH' || risk === 'CRITICAL'
        })} />
        <div className="min-w-0">
          <div className="text-sm font-bold font-mono tracking-tight text-[#1D1D1F] dark:text-[#F5F5F7] group-hover:text-apple-blue transition-colors truncate">
            {transaction.transaction_id}
          </div>
          <div className="text-xs font-semibold text-gray-500 mt-0.5">{timeAgo(transaction.timestamp)}</div>
        </div>
      </div>
      
      <div className="col-span-2 flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-black/5 dark:bg-white/5 flex items-center justify-center text-gray-600 dark:text-gray-300 shrink-0">
          <ChannelIcon className="w-3.5 h-3.5" />
        </div>
        <span className="text-sm font-semibold text-[#1D1D1F] dark:text-[#F5F5F7] truncate">{channel.label}</span>
      </div>
      
      <div className="col-span-3 min-w-0">
        <div className="text-sm font-semibold text-[#1D1D1F] dark:text-[#F5F5F7] truncate">{transaction.merchant_category || 'General Merchant'}</div>
        <div className="text-xs font-medium text-gray-500 mt-0.5 truncate">{transaction.city || 'Location Unknown'}</div>
      </div>
      
      <div className="col-span-2 flex items-center">
        <span className={clsx("badge", getRiskBadgeClass(risk))}>{risk}</span>
      </div>
      
      <div className="col-span-2 flex items-center justify-end gap-3 text-right">
        <div className="text-[15px] font-bold font-mono text-[#1D1D1F] dark:text-[#F5F5F7] whitespace-nowrap">{formatINR(transaction.amount)}</div>
        <ChevronRight className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 group-hover:text-apple-blue transition-all shrink-0 -mr-2" />
      </div>
    </div>
  );
});

// Area Chart for Live Volume Tracking
const VolumeChart = memo(function VolumeChart({ data }) {
  return (
     <div className="glass-card flex flex-col h-full border border-[#E5E5EA]/30 dark:border-white/5">
        <div className="px-6 py-5 border-b border-[#E5E5EA]/50 dark:border-white/5">
          <h3 className="text-sm text-gray-900 dark:text-white font-bold tracking-tight">System Kinetics</h3>
          <p className="text-xs text-gray-500 mt-1 font-medium">Volume over last 60 seconds</p>
        </div>
        <div className="flex-1 w-full min-h-[150px] p-4">
           <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                 <defs>
                   <linearGradient id="colorVol" x1="0" y1="0" x2="0" y2="1">
                     <stop offset="5%" stopColor="#0071e3" stopOpacity={0.4}/>
                     <stop offset="95%" stopColor="#0071e3" stopOpacity={0}/>
                   </linearGradient>
                 </defs>
                 <Area type="monotone" dataKey="volume" stroke="#0071e3" strokeWidth={3} fillOpacity={1} fill="url(#colorVol)" animationDuration={300} />
              </AreaChart>
           </ResponsiveContainer>
        </div>
     </div>
  );
});


// Main App
export default function Appv2() {
  const { theme, toggle } = useTheme();
  
  // State
  const [connected, setConnected] = useState(false);
  const [simulationActive, setSimulationActive] = useState(false);
  const [simulationRate, setSimulationRate] = useState(() => {
    return parseInt(localStorage.getItem('simulationRate') || '3');
  });
  
  const [transactions, setTransactions] = useState([]);
  const [volumeHistory, setVolumeHistory] = useState([]);
  
  const [stats, setStats] = useState({
    total_transactions: 0, total_volume: 0, fraud_rate: 0, active_alerts: 0
  });

  const [currentView, setCurrentView] = useState('Dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [notifications, setNotifications] = useState([]);

  // Inspector & Auto-Pause State
  const [inspectedTxn, setInspectedTxn] = useState(null);
  const [isStreamPaused, setIsStreamPaused] = useState(false);

  const isPausedRef = useRef(false);
  const bufferRef = useRef([]);

  // Remote data
  const [filters, setFilters] = useState({ riskLevel: 'all', channel: 'all', search: '' });
  const [alertsList, setAlertsList] = useState([]);
  const [profilesList, setProfilesList] = useState([]);

  // Global Notification Listener
  useEffect(() => {
    const handleNotify = (e) => {
      const { message, type } = e.detail;
      const id = Date.now();
      setNotifications(prev => [...prev, { id, message, type }]);
    };
    window.addEventListener('argus-notify', handleNotify);
    return () => window.removeEventListener('argus-notify', handleNotify);
  }, []);

  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const filteredTransactions = transactions.filter(t => {
    const matchesSearch = (t.transaction_id || '').toLowerCase().includes(filters.search.toLowerCase()) ||
                         (t.merchant || '').toLowerCase().includes(filters.search.toLowerCase());
    const matchesRisk = filters.riskLevel === 'all' || t.risk_level === filters.riskLevel;
    const matchesChannel = filters.channel === 'all' || (t.channel || '').toLowerCase() === filters.channel.toLowerCase();
    
    return matchesSearch && matchesRisk && matchesChannel;
  });

  useEffect(() => {
    isPausedRef.current = isStreamPaused;
  }, [isStreamPaused]);

  // Fetch real data for views
  useEffect(() => {
    if (currentView === 'Alerts') {
      api.getAlerts(50).then(res => setAlertsList(res.alerts || res)).catch(e => console.error(e));
    } else if (currentView === 'Profiles') {
      api.getProfiles(50).then(res => setProfilesList(res.profiles || [])).catch(e => console.error(e));
    }
  }, [currentView]);

  // WebSocket Connection
  useEffect(() => {
    const ws = new WebSocketClient(
      (data) => {
        if (data.type === 'init') {
          if (data.data.stats) setStats(data.data.stats);
          if (data.data.recent_transactions) setTransactions(data.data.recent_transactions.slice(0, 50));
        } else if (data.type === 'transaction') {
          const txn = data.data;
          if (isPausedRef.current) {
            bufferRef.current.unshift(txn);
            if (bufferRef.current.length > 200) bufferRef.current.pop();
          } else {
            setTransactions(prev => {
              const combined = [txn, ...bufferRef.current, ...prev];
              bufferRef.current = [];
              const unique = Array.from(new Map(combined.map(item => [item.transaction_id, item])).values());
              return unique.slice(0, 50);
            });
          }
        } else if (data.type === 'stats') {
          setStats(data.data);
        }
      },
      () => setConnected(true),
      () => setConnected(false)
    );
    
    ws.connect();
    return () => ws.disconnect();
  }, []);

  // Update Volume Chart History
  useEffect(() => {
    if (stats.total_volume && !isPausedRef.current) {
      setVolumeHistory(prev => {
        const updated = [...prev, { time: Date.now(), volume: stats.total_volume }];
        return updated.slice(-30);
      });
    }
  }, [stats.total_volume]);

  // Simulation Controls
  const toggleSimulation = async () => {
    try {
      if (simulationActive) await api.stopSimulation();
      else await api.startSimulation(simulationRate);
      setSimulationActive(!simulationActive);
    } catch (err) {
      console.error('Simulation toggle failed', err);
    }
  };

  const handleRateChange = async (e) => {
    const rate = parseInt(e.target.value);
    setSimulationRate(rate);
    localStorage.setItem('simulationRate', rate.toString());
    if (simulationActive) {
      await api.stopSimulation();
      await api.startSimulation(rate);
    }
  };

  const clearData = () => {
    setTransactions([]);
    setVolumeHistory([]);
    setStats({ total_transactions: 0, total_volume: 0, fraud_rate: 0, active_alerts: 0 });
  };

  const handleInspect = (txn) => {
     setIsStreamPaused(true);
     setInspectedTxn(txn);
  };

  const closeInspector = () => {
     setIsStreamPaused(false);
     setInspectedTxn(null);
  }

  const renderContent = () => {
     switch(currentView) {
        case 'Dashboard':
          return (
            <div className="flex-1 overflow-auto p-6 md:p-8 z-10 relative">
              <div className="mb-6">
                <h1 className="text-2xl font-black tracking-tight mb-1">System Command Center</h1>
                <p className="text-gray-500 font-medium text-sm">Eagle's eye view into all fraud detection operations. Outlier-first metrics.</p>
              </div>

              {/* ROW 1: 6 KPI Cards */}
              <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-6">
                <div className={clsx("glass-card p-4 border", stats.fraud_rate > 2 ? "border-apple-red/40 shadow-apple-red/10 shadow-lg" : "border-white/10")}>
                  <p className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">Fraud Rate</p>
                  <p className={clsx("text-2xl font-black font-mono", stats.fraud_rate > 2 ? "text-apple-red" : "text-[#1D1D1F] dark:text-[#F5F5F7]")}>{stats.fraud_rate?.toFixed(2) || '0.00'}%</p>
                  <p className="text-[9px] text-gray-500 mt-1 font-mono">Threshold: 2.00%</p>
                </div>
                <div className="glass-card p-4 border border-white/10">
                  <p className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">Blocked (Total)</p>
                  <p className="text-2xl font-black font-mono text-apple-red">{stats.total_blocked || 0}</p>
                  <p className="text-[9px] text-gray-500 mt-1 font-mono">Auto-blocked txns</p>
                </div>
                <div className={clsx("glass-card p-4 border", (stats.active_alerts || 0) > 0 ? "border-apple-orange/40" : "border-white/10")}>
                  <p className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">Escalations</p>
                  <p className={clsx("text-2xl font-black font-mono", (stats.active_alerts || 0) > 0 ? "text-apple-orange" : "text-[#1D1D1F] dark:text-[#F5F5F7]")}>{stats.active_alerts || 0}</p>
                  <p className="text-[9px] text-gray-500 mt-1 font-mono">Pending review</p>
                </div>
                <div className="glass-card p-4 border border-white/10">
                  <p className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">Avg Latency</p>
                  <p className="text-2xl font-black font-mono text-apple-blue">{stats.avg_latency_ms?.toFixed(1) || '0.0'}<span className="text-sm">ms</span></p>
                  <p className="text-[9px] text-gray-500 mt-1 font-mono">End-to-end pipeline</p>
                </div>
                <div className="glass-card p-4 border border-white/10">
                  <p className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">Total Volume</p>
                  <p className="text-2xl font-black font-mono text-[#1D1D1F] dark:text-[#F5F5F7]">{formatCompact(stats.total_volume || 0)}</p>
                  <p className="text-[9px] text-gray-500 mt-1 font-mono">{formatCompact(stats.total_transactions || 0)} transactions</p>
                </div>
                <div className="glass-card p-4 border border-white/10">
                  <p className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">Avg Risk Score</p>
                  <p className={clsx("text-2xl font-black font-mono", (stats.avg_risk_score || 0) > 0.35 ? "text-apple-red" : (stats.avg_risk_score || 0) > 0.18 ? "text-apple-orange" : "text-apple-green")}>{(stats.avg_risk_score || 0).toFixed(3)}</p>
                  <p className="text-[9px] text-gray-500 mt-1 font-mono">Across all txns</p>
                </div>
              </div>

              {/* ROW 2: Risk Distribution + Scoring Formula */}
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-6">
                {/* Risk Distribution */}
                <div className="glass-card p-5 border border-white/10">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4">Risk Distribution</h3>
                  <div className="flex items-center gap-6">
                    <div className="w-36 h-36 shrink-0">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie data={[
                            { name: 'LOW', value: stats.risk_distribution?.LOW || 1, fill: '#34C759' },
                            { name: 'MEDIUM', value: stats.risk_distribution?.MEDIUM || 0, fill: '#FF9500' },
                            { name: 'HIGH', value: stats.risk_distribution?.HIGH || 0, fill: '#FF3B30' },
                            { name: 'CRITICAL', value: stats.risk_distribution?.CRITICAL || 0, fill: '#AF1100' }
                          ]} cx="50%" cy="50%" innerRadius={35} outerRadius={55} paddingAngle={3} dataKey="value" strokeWidth={0}>
                          </Pie>
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex-1 grid grid-cols-2 gap-x-6 gap-y-3">
                      {[
                        { label: 'LOW', count: stats.risk_distribution?.LOW || 0, color: 'bg-apple-green', text: 'text-apple-green' },
                        { label: 'MEDIUM', count: stats.risk_distribution?.MEDIUM || 0, color: 'bg-apple-orange', text: 'text-apple-orange' },
                        { label: 'HIGH', count: stats.risk_distribution?.HIGH || 0, color: 'bg-apple-red', text: 'text-apple-red' },
                        { label: 'CRITICAL', count: stats.risk_distribution?.CRITICAL || 0, color: 'bg-red-900', text: 'text-red-400' }
                      ].map(r => (
                        <div key={r.label} className="flex items-center gap-2">
                          <div className={clsx("w-2.5 h-2.5 rounded-full shrink-0", r.color)} />
                          <div>
                            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">{r.label}</span>
                            <p className={clsx("text-lg font-black font-mono leading-none", r.text)}>{r.count}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Scoring Formula Explainer */}
                <div className="glass-card p-5 border border-white/10">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4">Ensemble Scoring Formula v4.0</h3>
                  <div className="bg-black/5 dark:bg-white/5 rounded-xl p-4 mb-4 font-mono text-sm text-center border border-[#E5E5EA] dark:border-[#3A3A3C]">
                    <span className="text-apple-blue font-bold">Score</span> = <span className="text-blue-400">XGB</span><span className="text-gray-400">(30%)</span> + <span className="text-indigo-400">LGB</span><span className="text-gray-400">(25%)</span> + <span className="text-apple-orange">IF</span><span className="text-gray-400">(15%)</span> + <span className="text-emerald-400">Rules</span><span className="text-gray-400">(15%)</span> + <span className="text-purple-400">Dyn</span><span className="text-gray-400">(15%)</span>
                  </div>
                  <div className="space-y-2">
                    {[
                      { name: 'XGBoost', weight: 30, desc: 'Gradient-boosted trees on 34 features', color: 'bg-blue-400' },
                      { name: 'LightGBM', weight: 25, desc: 'Leaf-wise growth, complementary signal', color: 'bg-indigo-400' },
                      { name: 'Isolation Forest', weight: 15, desc: 'Unsupervised anomaly detection', color: 'bg-apple-orange' },
                      { name: 'Rule Engine', weight: 15, desc: 'RBI/NPCI regulatory + velocity rules', color: 'bg-emerald-400' },
                      { name: 'Dynamic Behavior', weight: 15, desc: 'Per-user behavioral deviation analysis', color: 'bg-purple-400' },
                    ].map(m => (
                      <div key={m.name} className="flex items-center gap-3">
                        <div className="w-20 text-right shrink-0"><span className="text-[10px] font-bold text-gray-500 uppercase">{m.name}</span></div>
                        <div className="flex-1 h-2 bg-gray-200 dark:bg-[#3A3A3C] rounded-full overflow-hidden">
                          <div className={clsx("h-full rounded-full", m.color)} style={{width: `${m.weight}%`}} />
                        </div>
                        <span className="text-[10px] font-mono font-bold text-gray-500 w-8">{m.weight}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* ROW 3: Volume Chart + Recent High-Risk Outliers */}
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-6">
                <div className="xl:col-span-1">
                  <VolumeChart data={volumeHistory} />
                </div>
                <div className="xl:col-span-2 glass-card border border-white/10 flex flex-col">
                  <div className="px-5 py-4 border-b border-[#E5E5EA]/50 dark:border-white/5 flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500">Recent High-Risk Outliers</h3>
                      <p className="text-[10px] text-gray-500 mt-0.5">Transactions scoring HIGH or CRITICAL</p>
                    </div>
                  </div>
                  <div className="flex-1 overflow-auto">
                    {transactions.filter(t => t.risk_level === 'HIGH' || t.risk_level === 'CRITICAL').length === 0 ? (
                      <div className="p-8 text-center text-gray-500 text-sm font-medium flex flex-col items-center"><CheckCircle className="w-8 h-8 mb-3 opacity-30 text-apple-green" />No high-risk outliers detected.</div>
                    ) : (
                      <div className="divide-y divide-[#E5E5EA] dark:divide-[#3A3A3C]">
                        {transactions.filter(t => t.risk_level === 'HIGH' || t.risk_level === 'CRITICAL').slice(0, 8).map((t, idx) => (
                          <div key={idx} className="grid grid-cols-12 gap-2 px-5 py-3 hover:bg-white/5 cursor-pointer text-sm items-center" onClick={() => handleInspect(t)}>
                            <div className="col-span-3 font-mono text-xs truncate text-gray-400">{t.transaction_id?.slice(0, 16)}...</div>
                            <div className="col-span-2 font-mono text-xs">{t.user_id}</div>
                            <div className="col-span-2 font-mono font-bold">{formatINR(t.amount)}</div>
                            <div className="col-span-2"><span className={clsx("badge text-[9px]", getRiskBadgeClass(t.risk_level))}>{t.risk_level}</span></div>
                            <div className="col-span-2 font-mono text-xs text-apple-red">{t.risk_score?.toFixed(3)}</div>
                            <div className="col-span-1 text-right"><ChevronRight className="w-3.5 h-3.5 text-gray-400 inline" /></div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* ROW 4: Decision Breakdown + Channel Distribution + Thresholds */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Decision Breakdown */}
                <div className="glass-card p-5 border border-white/10">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4">Decision Breakdown</h3>
                  <div className="space-y-3">
                    {[
                      { label: 'APPROVED', count: stats.total_approved || 0, color: 'bg-apple-green', pct: stats.total_transactions ? ((stats.total_approved || 0) / stats.total_transactions * 100).toFixed(1) : '0.0' },
                      { label: 'FLAGGED', count: stats.total_flagged || 0, color: 'bg-apple-orange', pct: stats.total_transactions ? ((stats.total_flagged || 0) / stats.total_transactions * 100).toFixed(1) : '0.0' },
                      { label: 'BLOCKED', count: stats.total_blocked || 0, color: 'bg-apple-red', pct: stats.total_transactions ? ((stats.total_blocked || 0) / stats.total_transactions * 100).toFixed(1) : '0.0' }
                    ].map(d => (
                      <div key={d.label} className="flex items-center gap-3">
                        <div className="w-20"><span className="text-[10px] font-bold text-gray-500 uppercase">{d.label}</span></div>
                        <div className="flex-1 h-2 bg-gray-200 dark:bg-[#3A3A3C] rounded-full overflow-hidden">
                          <div className={clsx("h-full rounded-full transition-all", d.color)} style={{width: `${Math.min(parseFloat(d.pct), 100)}%`}} />
                        </div>
                        <span className="text-xs font-mono font-bold w-16 text-right">{d.count} <span className="text-gray-500">({d.pct}%)</span></span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Risk Thresholds */}
                <div className="glass-card p-5 border border-white/10">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4">Risk Tier Thresholds</h3>
                  <div className="space-y-3">
                    {[
                      { tier: 'CRITICAL', threshold: '> 0.55', action: 'Auto-Block', color: 'border-l-red-900 bg-red-900/10' },
                      { tier: 'HIGH', threshold: '> 0.35', action: 'Manual Review', color: 'border-l-apple-red bg-apple-red/10' },
                      { tier: 'MEDIUM', threshold: '> 0.18', action: 'Flag & Monitor', color: 'border-l-apple-orange bg-apple-orange/10' },
                      { tier: 'LOW', threshold: '< 0.18', action: 'Approve', color: 'border-l-apple-green bg-apple-green/10' }
                    ].map(t => (
                      <div key={t.tier} className={clsx("border-l-4 rounded-r-lg p-2.5 flex justify-between items-center", t.color)}>
                        <div>
                          <span className="text-[10px] font-black uppercase tracking-widest">{t.tier}</span>
                          <span className="text-[10px] text-gray-500 ml-2 font-mono">{t.threshold}</span>
                        </div>
                        <span className="text-[10px] text-gray-500 font-bold uppercase">{t.action}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Engine Status */}
                <div className="glass-card p-5 border border-white/10">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4">Engine Status</h3>
                  <div className="space-y-3">
                    {[
                      { label: 'XGBoost Ensemble', status: 'ACTIVE', version: 'v4.0.0' },
                      { label: 'LightGBM', status: 'ACTIVE', version: 'v4.0.0' },
                      { label: 'Isolation Forest', status: 'ACTIVE', version: 'v4.0.0' },
                      { label: 'Dynamic Behavior', status: 'ACTIVE', version: 'Persistent' },
                      { label: 'Rule Engine', status: 'ACTIVE', version: 'RBI/NPCI' },
                    ].map(m => (
                      <div key={m.label} className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-[#1D1D1F] dark:text-[#F5F5F7]">{m.label}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] font-mono text-gray-500">{m.version}</span>
                          <span className="w-1.5 h-1.5 rounded-full bg-apple-green shadow-[0_0_6px_rgba(52,199,89,0.8)]" />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 pt-3 border-t border-[#E5E5EA] dark:border-[#3A3A3C]">
                    <div className="flex justify-between text-[10px]">
                      <span className="text-gray-500 font-bold uppercase">Feature Vector</span>
                      <span className="font-mono font-bold">34 dimensions</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );

        case 'Live Traffic':
          return (
            <div className="flex-1 overflow-auto p-6 md:p-10 z-10 relative flex flex-col">
              <div className="mb-6 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div>
                  <h1 className="text-3xl font-bold tracking-tight mb-2">Live Stream Details</h1>
                  <p className="text-gray-500 font-medium">Real-time unbuffered transaction stream analysis.</p>
                </div>
                
                {/* Advanced Button Filters for Accessibility */}
                <div className="flex items-center gap-2 overflow-x-auto pb-2 lg:pb-0 scrollbar-none">
                  <div className="bg-black/5 dark:bg-white/10 p-1 rounded-xl flex items-center gap-1 shadow-inner">
                    {['all', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map(level => (
                      <button
                        key={level}
                        onClick={() => setFilters(f => ({ ...f, riskLevel: level }))}
                        className={clsx(
                          "px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all relative overflow-hidden group",
                          filters.riskLevel === level
                            ? clsx("shadow-sm scale-[1.02] text-white", {
                                'bg-apple-blue': level === 'all',
                                'bg-apple-green': level === 'LOW',
                                'bg-apple-orange': level === 'MEDIUM',
                                'bg-apple-red': level === 'HIGH' || level === 'CRITICAL'
                              })
                            : "text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5"
                        )}
                      >
                        {level === 'all' ? 'ALL RISKS' : level}
                      </button>
                    ))}
                  </div>
                  <div className="w-[1px] h-8 bg-white/10 mx-1 hidden lg:block" />
                  <div className="bg-black/5 dark:bg-white/10 p-1 rounded-xl flex items-center gap-1 shadow-inner">
                    {['all', 'upi', 'pos', 'card_online'].map(ch => (
                      <button
                        key={ch}
                        onClick={() => setFilters(f => ({ ...f, channel: ch }))}
                        className={clsx(
                          "px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all",
                          filters.channel === ch
                            ? "bg-white dark:bg-apple-blue text-apple-blue dark:text-white shadow-sm scale-[1.02]"
                            : "text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5"
                        )}
                      >
                        {ch === 'all' ? 'CHANNELS' : ch.replace('_', ' ')}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                   {/* Stream is now always active in this view for maximum fidelity */}
                </div>
              </div>

              <div className="glass-card flex-1 flex flex-col border border-[#E5E5EA]/30 dark:border-white/5 relative overflow-hidden">
                {isStreamPaused && <div className="absolute inset-x-0 top-0 h-1 bg-apple-orange animate-pulse z-20" />}
                
                <div className="flex-1 overflow-auto">
                  {/* Strict Grid Header */}
                  <div className="grid grid-cols-12 gap-4 text-[11px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest px-6 py-4 border-b border-[#E5E5EA] dark:border-[#3A3A3C] sticky top-0 bg-[#F5F5F7]/95 dark:bg-[#1C1C1E]/95 backdrop-blur-xl z-10">
                    <div className="col-span-3">Transaction ID</div>
                    <div className="col-span-2">Channel</div>
                    <div className="col-span-3">Origin / Location</div>
                    <div className="col-span-2">System Risk</div>
                    <div className="col-span-2 text-right pr-6">Traded Value</div>
                  </div>
                  
                  <div>
                    {transactions.length === 0 ? (
                      <div className="p-20 text-center text-gray-400 font-mono tracking-tight flex flex-col items-center justify-center h-full">
                         <Activity className="w-10 h-10 mb-6 opacity-40 animate-pulse" />
                         Pipeline Idle. No packets detected.<br/><br/>Initialize the Simulation Sequence.
                      </div>
                    ) : (
                      filteredTransactions.slice(0, 100).map((t, idx) => (
                        <TransactionRowDesktop 
                          key={t.transaction_id} 
                          transaction={t} 
                          isNew={idx === 0 && !isStreamPaused}
                          onOpenInspector={handleInspect}
                        />
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          );

        case 'Alerts':
          const highRiskAlerts = alertsList.filter(a => a.risk_level === 'HIGH' || a.risk_level === 'CRITICAL');
          return (
             <div className="flex-1 overflow-auto p-6 md:p-8 z-10 relative">
               <div className="mb-6">
                 <h1 className="text-2xl font-black tracking-tight mb-1">Fraud Alert Queue</h1>
                 <p className="text-gray-500 font-medium text-sm">HIGH and CRITICAL risk transactions awaiting admin triage. <span className="font-mono text-apple-red">{highRiskAlerts.filter(a => a.status === 'pending').length}</span> pending.</p>
               </div>
               {highRiskAlerts.length === 0 ? (
                 <div className="glass-card p-12 text-center text-gray-500 flex flex-col items-center border border-white/10">
                   <CheckCircle className="w-12 h-12 mb-4 opacity-30 text-apple-green" />
                   <p className="font-bold text-lg mb-1">Queue Clear</p>
                   <p className="text-sm">No HIGH or CRITICAL alerts require review.</p>
                 </div>
               ) : (
                 <div className="space-y-3">
                   {highRiskAlerts.map((al, idx) => (
                     <div key={idx} className={clsx(
                       "glass-card border p-5 transition-all relative overflow-hidden",
                       al.status === 'confirmed' ? "border-apple-red/30 opacity-60" : al.status === 'dismissed' ? "border-white/5 opacity-40" : "border-white/10 hover:border-apple-orange/30"
                     )}>
                       {al.risk_level === 'CRITICAL' && al.status === 'pending' && <div className="absolute top-0 left-0 w-1 h-full bg-apple-red shadow-[0_0_10px_rgba(255,59,48,0.6)]" />}
                       <div className="flex items-center gap-4">
                         <div className={clsx("w-10 h-10 rounded-full flex items-center justify-center shrink-0", al.risk_level === 'CRITICAL' ? 'bg-apple-red/10 text-apple-red' : 'bg-apple-orange/10 text-apple-orange')}>
                           <AlertTriangle className="w-5 h-5" />
                         </div>
                         <div className="flex-1 min-w-0 grid grid-cols-12 gap-4 items-center">
                           <div className="col-span-3">
                             <div className="font-mono text-sm font-bold truncate text-[#1D1D1F] dark:text-[#F5F5F7]">{al.transaction_id?.slice(0, 20)}...</div>
                             <div className="text-[10px] text-gray-500 font-medium mt-0.5">{new Date(al.timestamp).toLocaleString()}</div>
                           </div>
                           <div className="col-span-2"><span className={clsx("badge text-[9px]", getRiskBadgeClass(al.risk_level))}>{al.risk_level}</span></div>
                           <div className="col-span-2 font-mono font-bold text-sm">{formatINR(al.amount)}</div>
                           <div className="col-span-1 text-xs font-bold uppercase text-gray-500">{al.channel}</div>
                           <div className="col-span-1 text-xs font-mono text-gray-500">{al.status || 'pending'}</div>
                           <div className="col-span-3 flex items-center justify-end gap-2">
                             {al.status === 'pending' ? (
                               <>
                                 <button
                                   onClick={() => { api.updateAlert(al.id, 'confirmed'); setAlertsList(prev => prev.map(a => a.id === al.id ? {...a, status: 'confirmed'} : a)); }}
                                   className="px-3 py-1.5 bg-apple-red/10 text-apple-red text-[10px] font-black uppercase tracking-wider rounded-lg hover:bg-apple-red hover:text-white transition-all"
                                 >Confirm Fraud</button>
                                 <button
                                   onClick={() => { api.updateAlert(al.id, 'dismissed'); setAlertsList(prev => prev.map(a => a.id === al.id ? {...a, status: 'dismissed'} : a)); }}
                                   className="px-3 py-1.5 bg-white/5 text-gray-500 text-[10px] font-black uppercase tracking-wider rounded-lg hover:bg-white/10 transition-all"
                                 >Dismiss</button>
                               </>
                             ) : (
                               <span className={clsx("text-[10px] font-black uppercase tracking-wider", al.status === 'confirmed' ? 'text-apple-red' : 'text-gray-500')}>{al.status}</span>
                             )}
                           </div>
                         </div>
                       </div>
                     </div>
                   ))}
                 </div>
               )}
             </div>
          );

        case 'Profiles':
          return (
             <div className="flex-1 overflow-auto p-6 md:p-8 z-10 relative">
               <div className="mb-6">
                 <h1 className="text-2xl font-black tracking-tight mb-1">Identity & Behavior Profiles</h1>
                 <p className="text-gray-500 font-medium text-sm">Per-user behavioral baselines powering the dynamic anomaly engine.</p>
               </div>
               <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {profilesList.length === 0 ? <div className="col-span-full glass-card p-12 text-center text-gray-500 flex flex-col items-center border border-white/10"><Users className="w-12 h-12 mb-4 opacity-30" />No profiles loaded. Start the simulation to build user behavioral baselines.</div> : (
                     profilesList.map((p, idx) => (
                        <div key={idx} className="glass-card p-5 flex flex-col transition-all hover:-translate-y-1 hover:shadow-apple-float border border-white/10">
                           <div className="flex justify-between items-start mb-3">
                              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-apple-blue to-[#BF5AF2] flex items-center justify-center text-white font-bold text-sm shadow-lg shrink-0">
                                 {p.user_id?.substring(0,2).toUpperCase()}
                              </div>
                              <span className={clsx("badge text-[9px] uppercase font-bold", p.is_mature ? 'bg-apple-green/10 text-apple-green border border-apple-green/20' : 'bg-apple-orange/10 text-apple-orange border border-apple-orange/20')}>{p.is_mature ? 'MATURE' : 'BUILDING'}</span>
                           </div>
                           <div className="font-bold font-mono text-sm mb-0.5 tracking-tight truncate text-[#1D1D1F] dark:text-[#F5F5F7]" title={p.user_id}>{p.user_id}</div>
                           <div className="text-[10px] text-gray-500 mb-3 font-mono">{p.transaction_count || 0} txns | {p.profile_age_days || 0}d old</div>
                           
                           {p.statistics ? (
                              <div className="mt-auto bg-black/5 dark:bg-white/5 p-3 rounded-xl space-y-2">
                                <div className="flex justify-between items-center"><span className="text-[10px] text-gray-500 uppercase font-bold tracking-wide">Avg</span><span className="font-mono font-bold text-xs">{formatINR(p.statistics.avg_amount || 0)}</span></div>
                                <div className="flex justify-between items-center"><span className="text-[10px] text-gray-500 uppercase font-bold tracking-wide">Std Dev</span><span className="font-mono text-xs text-gray-500">+/-{formatINR(p.statistics.std_amount || 0)}</span></div>
                                <div className="flex justify-between items-center"><span className="text-[10px] text-gray-500 uppercase font-bold tracking-wide">Max</span><span className="font-mono text-xs font-bold">{formatINR(p.statistics.max_amount || 0)}</span></div>
                                <div className="flex justify-between items-center"><span className="text-[10px] text-gray-500 uppercase font-bold tracking-wide">P95</span><span className="font-mono text-xs">{formatINR(p.statistics.p95_amount || 0)}</span></div>
                              </div>
                           ) : (
                              <div className="mt-auto bg-black/5 dark:bg-white/5 p-3 rounded-xl space-y-2">
                                <div className="flex justify-between items-center"><span className="text-[10px] text-gray-500 uppercase font-bold tracking-wide">Txn Count</span><span className="font-mono text-xs">{p.transaction_count || 0}</span></div>
                                <div className="text-[10px] text-gray-500 text-center py-1">Awaiting more data for full profile</div>
                              </div>
                           )}
                        </div>
                     ))
                  )}
               </div>
             </div>
          );

        case 'Settings':
          return (
             <div className="flex-1 overflow-auto p-6 md:p-8 z-10 relative">
               <div className="max-w-5xl">
                 <div className="mb-6">
                   <h1 className="text-2xl font-black tracking-tight mb-1">Platform Configuration</h1>
                   <p className="text-gray-500 font-medium text-sm">Engine parameters, regulatory limits, and model registry. Read-only view.</p>
                 </div>
                 
                 <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                    {/* Ensemble Weights */}
                    <div className="glass-card p-5 border border-white/10">
                       <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4 flex items-center gap-2"><Brain className="w-4 h-4 text-apple-blue"/>Ensemble Weights</h3>
                       <div className="space-y-3">
                         {[
                           { name: 'XGBoost', weight: 0.30, color: 'bg-blue-400' },
                           { name: 'LightGBM', weight: 0.25, color: 'bg-indigo-400' },
                           { name: 'Isolation Forest', weight: 0.15, color: 'bg-apple-orange' },
                           { name: 'Rule Engine', weight: 0.15, color: 'bg-emerald-400' },
                           { name: 'Dynamic Behavior', weight: 0.15, color: 'bg-purple-400' },
                         ].map(m => (
                           <div key={m.name} className="flex items-center gap-3">
                             <span className="text-xs font-semibold w-28 text-right shrink-0">{m.name}</span>
                             <div className="flex-1 h-2 bg-gray-200 dark:bg-[#3A3A3C] rounded-full overflow-hidden">
                               <div className={clsx("h-full rounded-full", m.color)} style={{width: `${m.weight*100}%`}} />
                             </div>
                             <span className="text-xs font-mono font-bold w-10 text-right">{(m.weight*100).toFixed(0)}%</span>
                           </div>
                         ))}
                       </div>
                    </div>

                    {/* Risk Thresholds */}
                    <div className="glass-card p-5 border border-white/10">
                       <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-apple-red"/>Risk Tier Configuration</h3>
                       <div className="space-y-2">
                         {[
                           { tier: 'CRITICAL', score: '>= 0.55', action: 'Auto-Block + Alert', color: 'border-l-red-900' },
                           { tier: 'HIGH', score: '>= 0.35', action: 'Escalate to Admin', color: 'border-l-apple-red' },
                           { tier: 'MEDIUM', score: '>= 0.18', action: 'Flag for Monitoring', color: 'border-l-apple-orange' },
                           { tier: 'LOW', score: '< 0.18', action: 'Auto-Approve', color: 'border-l-apple-green' },
                         ].map(t => (
                           <div key={t.tier} className={clsx("border-l-4 p-3 rounded-r-lg bg-black/5 dark:bg-white/5 flex justify-between items-center", t.color)}>
                             <div>
                               <span className="text-[10px] font-black uppercase tracking-widest">{t.tier}</span>
                               <span className="text-[10px] text-gray-500 ml-2 font-mono">{t.score}</span>
                             </div>
                             <span className="text-[10px] text-gray-500 font-bold">{t.action}</span>
                           </div>
                         ))}
                       </div>
                    </div>

                    {/* RBI/NPCI Regulatory Limits */}
                    <div className="glass-card p-5 border border-white/10">
                       <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4 flex items-center gap-2"><Shield className="w-4 h-4 text-apple-green"/>India Regulatory Limits (RBI/NPCI)</h3>
                       <div className="space-y-2">
                         {[
                           { label: 'UPI Single Transaction', value: '1,00,000' },
                           { label: 'ATM Daily Withdrawal', value: '25,000' },
                           { label: 'Wallet Balance Limit', value: '10,000' },
                           { label: 'High Value Threshold', value: '50,000' },
                           { label: 'Very High Value', value: '2,00,000' },
                           { label: 'Suspicious Transaction', value: '5,00,000' },
                         ].map(l => (
                           <div key={l.label} className="flex justify-between items-center py-1.5 border-b border-[#E5E5EA]/30 dark:border-[#3A3A3C]/30 last:border-0">
                             <span className="text-xs text-gray-500 font-semibold">{l.label}</span>
                             <span className="font-mono text-xs font-bold">INR {l.value}</span>
                           </div>
                         ))}
                       </div>
                    </div>

                    {/* Behavior Engine */}
                    <div className="glass-card p-5 border border-white/10">
                       <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4 flex items-center gap-2"><Users className="w-4 h-4 text-purple-400"/>Behavioral Analysis Engine</h3>
                       <div className="space-y-2">
                         {[
                           { label: 'Active Profiles', value: stats.active_profiles?.toString() || '0' },
                           { label: 'Mature Profiles', value: stats.mature_profiles?.toString() || '0' },
                           { label: 'Maturity Threshold', value: '10 transactions' },
                           { label: 'Z-Score Anomaly Trigger', value: '3.0 sigma' },
                           { label: 'Amount Ratio Threshold', value: '5.0x avg' },
                           { label: 'Daily Deviation Trigger', value: '3.0 sigma' },
                           { label: 'Profile Persistence', value: 'Enabled (Disk Cache)' },
                         ].map(s => (
                           <div key={s.label} className="flex justify-between items-center py-1.5 border-b border-[#E5E5EA]/30 dark:border-[#3A3A3C]/30 last:border-0">
                             <span className="text-xs text-gray-500 font-semibold">{s.label}</span>
                             <span className="font-mono text-xs font-bold">{s.value}</span>
                           </div>
                         ))}
                       </div>
                    </div>

                    {/* System Info */}
                    <div className="glass-card p-5 border border-white/10 xl:col-span-2">
                       <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4 flex items-center gap-2"><Cpu className="w-4 h-4 text-gray-400"/>System Information</h3>
                       <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                         {[
                           { label: 'Engine Version', value: 'v4.0.0-india' },
                           { label: 'Feature Dimensions', value: '34' },
                           { label: 'Market', value: 'India (INR)' },
                           { label: 'Channels', value: 'UPI, POS, ATM, Card, NB, Wallet' },
                         ].map(s => (
                           <div key={s.label} className="bg-black/5 dark:bg-white/5 p-3 rounded-lg">
                             <div className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">{s.label}</div>
                             <div className="text-xs font-mono font-bold">{s.value}</div>
                           </div>
                         ))}
                       </div>
                    </div>
                 </div>
               </div>
             </div>
          );
          
        default: return null;
     }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#F5F5F7] dark:bg-[#000000] text-[#1D1D1F] dark:text-[#F5F5F7] font-sans relative selection:bg-apple-blue/30 selection:text-apple-blue">
      
      {/* AMBIENT LIQUID GLASSMORPHISM BACKDROP */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[10%] -left-[10%] w-[60%] h-[60%] rounded-[100%] bg-apple-blue/20 dark:bg-apple-blue/20 blur-[130px] opacity-80 mix-blend-normal" />
        <div className="absolute top-[30%] -right-[15%] w-[70%] h-[70%] rounded-[100%] bg-apple-red/10 dark:bg-[#BF5AF2]/20 blur-[150px] opacity-70 mix-blend-normal" />
        <div className="absolute -bottom-[20%] left-[20%] w-[50%] h-[50%] rounded-[100%] bg-apple-orange/10 blur-[120px] opacity-60 mix-blend-normal" />
      </div>

      {/* SIDEBAR */}
      <div className={clsx(
        "flex flex-col border-r border-white/20 dark:border-[#3A3A3C] transition-all duration-300 bg-white/40 dark:bg-[#1C1C1E]/40 backdrop-blur-3xl z-20 shadow-xl shadow-black/5",
        sidebarOpen ? "w-52" : "w-16"
      )}>
        <div className="h-16 flex items-center justify-between px-4 border-b border-[#E5E5EA]/50 dark:border-[#3A3A3C]/50">
          <div className="flex items-center gap-2 overflow-hidden">
            {sidebarOpen && <span className="font-black tracking-tight text-lg whitespace-nowrap">Project <span className="text-apple-blue">ARGUS</span></span>}
            {!sidebarOpen && <span className="font-black text-apple-blue text-lg">A</span>}
          </div>
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1.5 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 text-gray-500 transition-colors shrink-0">
            <List className="w-4 h-4" />
          </button>
        </div>
        
        <div className="flex-1 flex flex-col justify-between py-6 px-3 h-full">
           <nav className="space-y-1.5">
             {[
               { icon: LayoutDashboard, label: 'Dashboard' },
               { icon: Activity, label: 'Live Traffic' },
               { icon: AlertTriangle, label: 'Alerts' },
               { icon: Users, label: 'Profiles' },
               { icon: Settings, label: 'Settings' },
             ].map((item, idx) => (
               <button key={idx} 
                  onClick={() => setCurrentView(item.label)}
                  className={clsx(
                 "w-full flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-semibold transition-all duration-200 group",
                 currentView === item.label 
                   ? "bg-apple-blue text-white shadow-md shadow-apple-blue/20" 
                   : "text-gray-600 dark:text-gray-400 hover:bg-black/5 dark:hover:bg-white/5 hover:text-[#1D1D1F] dark:hover:text-white"
               )}>
                 <item.icon className="w-5 h-5 shrink-0" />
                 {sidebarOpen && <span className="whitespace-nowrap">{item.label}</span>}
                 {!sidebarOpen && currentView === item.label && (
                    <div className="absolute left-0 w-1 h-8 bg-apple-blue rounded-r-full shadow-[0_0_8px_rgba(0,113,227,0.8)]" />
                 )}
               </button>
             ))}
           </nav>
           
           <div className="bg-black/5 dark:bg-white/5 p-4 rounded-2xl border border-white/20 dark:border-white/5 shadow-inner">
             {sidebarOpen && (
               <div className="flex items-center justify-between mb-4">
                 <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">Network Edge</span>
                 <div className="flex items-center gap-1.5">
                   <span className={clsx("w-2 h-2 rounded-full", connected ? "bg-apple-green shadow-[0_0_8px_rgba(52,199,89,0.8)] animate-pulse" : "bg-apple-red")} />
                   <span className="text-[10px] font-mono font-bold text-gray-500">{connected ? 'ONLINE' : 'OFFLINE'}</span>
                 </div>
               </div>
             )}
             <div className="flex justify-center items-center">
               <ThemeToggle theme={theme} onToggle={toggle} />
             </div>
           </div>
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative z-10 w-full">
        
        {/* Header Ribbon */}
        <header className="h-16 flex items-center justify-between px-6 md:px-10 border-b border-[#E5E5EA]/50 dark:border-[#3A3A3C]/50 bg-white/40 dark:bg-[#1C1C1E]/40 backdrop-blur-2xl z-20 sticky top-0">
          <div className="flex items-center gap-4">
             <h1 className="text-lg font-bold tracking-tight text-[#1D1D1F] dark:text-[#F5F5F7]">{currentView}</h1>
          </div>
          
          <div className="flex items-center gap-4 md:gap-6">
            <button
              onClick={clearData}
              className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-gray-500 transition-colors hidden sm:block"
              title="Purge Local Buffer"
            >
              <RefreshCw className="w-5 h-5" />
            </button>

            {/* Velocity Slider */}
            <div className="hidden sm:flex items-center gap-3 px-4 py-2 rounded-full bg-white/50 dark:bg-[#2C2C2E]/50 border border-[#E5E5EA] dark:border-[#3A3A3C] shadow-sm">
               <Activity className="w-4 h-4 text-gray-400" />
               <span className="text-[10px] font-bold uppercase text-gray-500 tracking-wider">Velocity</span>
               <input 
                 type="range" min="1" max="20" 
                 value={simulationRate} 
                 onChange={handleRateChange}
                 className="w-20 md:w-28 accent-apple-blue"
                 title="Regulate transaction pipeline velocity"
               />
               <span className="text-xs font-mono font-bold w-12 text-right">{simulationRate} tps</span>
            </div>

            <button
              onClick={toggleSimulation}
              className={clsx(
                "font-bold uppercase tracking-wider text-[11px] px-6 py-3 rounded-full shadow-apple-float transition-all flex items-center gap-2",
                simulationActive ? "bg-apple-red text-white hover:bg-red-600 shadow-apple-red/30" : "bg-[#1D1D1F] dark:bg-apple-blue text-white hover:bg-black dark:hover:bg-blue-600 shadow-apple-blue/30"
              )}
            >
              {simulationActive ? <Square className="w-4 h-4" /> : <Zap className="w-4 h-4" />}
              <span className="hidden sm:inline">{simulationActive ? 'Halt Engine' : 'Start Stream'}</span>
              <span className="sm:hidden">{simulationActive ? 'Halt' : 'Start'}</span>
            </button>
          </div>
        </header>

        {/* Scrollable Body */}
        {renderContent()}

      </div>
      
      {/* Notifications Layer */}
      <div className="fixed bottom-8 right-8 z-[200] flex flex-col gap-3 items-end">
        {notifications.map(n => (
          <NotificationToast 
            key={n.id} 
            message={n.message} 
            type={n.type} 
            onClose={() => removeNotification(n.id)} 
          />
        ))}
      </div>
      
      {/* The Inspector Overlay - Moved outside main for correct stacking and positioning */}
      <TransactionInspector transaction={inspectedTxn} onClose={closeInspector} sidebarOpen={sidebarOpen} />
    </div>
  );
}
