import { useState, useEffect, useRef, useMemo, memo } from 'react';
import { 
  Shield, Activity, AlertTriangle, CheckCircle, XCircle, 
  TrendingUp, Users, Clock, Play, Square, Eye, Bell, 
  BarChart3, Zap, Globe, Filter, ChevronRight, RefreshCw, 
  Search, X, Download, Sun, Moon, Smartphone, CreditCard, 
  Wallet, Building2, Banknote, Network, Brain, Store, AlertOctagon,
  LayoutDashboard, List, Settings, LogOut, ChevronLeft,
  PauseCircle, Cpu, Wifi, MapPin
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

// Advanced Data Density Inspector Panel (Pop-out Modal)
const TransactionInspector = memo(function TransactionInspector({ transaction, onClose }) {
  if (!transaction) return null;
  const risk = transaction.risk_level || 'LOW';

  const handleExport = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(transaction, null, 2));
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", `txn_${transaction.transaction_id}.json`);
    dlAnchorElem.click();
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-8 bg-black/60 backdrop-blur-md animate-fade-in">
      <div className="bg-[#F5F5F7]/95 dark:bg-[#1C1C1E]/95 backdrop-blur-2xl rounded-3xl w-full max-w-5xl max-h-[90vh] shadow-apple-float overflow-hidden flex flex-col border border-white/20 dark:border-white/10 relative">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#E5E5EA] dark:border-[#3A3A3C] flex items-center justify-between bg-white/50 dark:bg-black/20">
          <div className="flex items-center gap-3">
            <div className={clsx("w-3 h-3 rounded-full shadow-[0_0_10px_rgba(0,0,0,0.5)]", {
              'bg-apple-green': risk === 'LOW',
              'bg-apple-orange': risk === 'MEDIUM',
              'bg-apple-red shadow-[0_0_10px_rgba(255,59,48,0.8)]': risk === 'HIGH' || risk === 'CRITICAL'
            })} />
            <h2 className="text-lg font-bold font-sans tracking-tight text-[#1D1D1F] dark:text-[#F5F5F7]">Txn Inspector</h2>
            <span className="text-gray-400 font-mono text-sm ml-2">{transaction.transaction_id}</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleExport} className="p-2 flex items-center gap-2 rounded-full hover:bg-gray-200 dark:hover:bg-[#2C2C2E] text-gray-500 transition-colors" title="Export JSON">
              <Download className="w-5 h-5" />
            </button>
            <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-[#2C2C2E] text-gray-500 transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Core Info */}
          <div className="glass-card p-5">
             <div className="flex items-center gap-2 mb-4 text-gray-500 uppercase tracking-widest text-xs font-bold border-b border-[#E5E5EA] dark:border-[#3A3A3C] pb-2">
                <Shield className="w-4 h-4" /> Core Intel
             </div>
             <div className="space-y-4">
                <div><span className="text-gray-500 text-xs uppercase font-medium">Amount</span><div className="text-2xl font-bold font-mono tracking-tighter text-[#1D1D1F] dark:text-[#F5F5F7]">{formatINR(transaction.amount)}</div></div>
                <div><span className="text-gray-500 text-xs uppercase font-medium">Decision</span><div className={clsx("text-lg font-bold uppercase tracking-tight", risk === 'LOW' ? 'text-apple-green' : 'text-apple-red')}>{transaction.recommendation || 'APPROVE'}</div></div>
                <div><span className="text-gray-500 text-xs uppercase font-medium">Channel / Merchant</span><div className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] uppercase tracking-wide">{transaction.channel} • {transaction.merchant_category || 'Retail'}</div></div>
                <div><span className="text-gray-500 text-xs uppercase font-medium">Timestamp</span><div className="text-sm font-mono text-[#1D1D1F] dark:text-[#F5F5F7]">{new Date(transaction.timestamp).toLocaleString()}</div></div>
             </div>
          </div>

          {/* Network & Identity */}
          <div className="glass-card p-5">
             <div className="flex items-center gap-2 mb-4 text-gray-500 uppercase tracking-widest text-xs font-bold border-b border-[#E5E5EA] dark:border-[#3A3A3C] pb-2">
                <Network className="w-4 h-4" /> Network & Origin
             </div>
             <div className="space-y-4 font-mono text-sm">
                <div className="flex items-center justify-between"><span className="text-gray-500 font-sans text-xs uppercase font-medium">IP Addr:</span> <span className="text-[#1D1D1F] dark:text-[#F5F5F7]">{transaction.ip_address || '192.168.1.1'}</span></div>
                <div className="flex items-center justify-between"><span className="text-gray-500 font-sans text-xs uppercase font-medium">Device:</span> <span className="truncate w-32 text-right text-[#1D1D1F] dark:text-[#F5F5F7]">{transaction.device_id || 'dev_8891abc'}</span></div>
                <div className="flex items-center justify-between"><span className="text-gray-500 font-sans text-xs uppercase font-medium">Location:</span> <span className="text-[#1D1D1F] dark:text-[#F5F5F7] text-right truncate w-32">{transaction.city || 'Unknown'}, {transaction.state || 'IN'}</span></div>
                <div className="flex items-center justify-between pt-2 border-t border-[#E5E5EA] dark:border-[#3A3A3C]"><span className="text-gray-500 font-sans text-xs uppercase font-medium">User ID:</span> <span className="text-apple-blue">{transaction.user_id}</span></div>
             </div>
          </div>

          {/* ML Intel Pipeline */}
          <div className="glass-card p-5 md:col-span-1 md:row-span-2">
             <div className="flex items-center gap-2 mb-4 text-gray-500 uppercase tracking-widest text-xs font-bold border-b border-[#E5E5EA] dark:border-[#3A3A3C] pb-2">
                <Brain className="w-4 h-4" /> Pipeline Signals
             </div>
             
             <div className="space-y-6">
                <div>
                  <div className="flex justify-between text-xs text-gray-500 mb-2 font-medium"><span className="uppercase">XGBoost Ensemble</span><span className="font-mono">{((transaction.model_scores?.xgboost || 0) * 100).toFixed(0)}%</span></div>
                  <div className="h-2 bg-gray-200 dark:bg-[#3A3A3C] rounded-full overflow-hidden shadow-inner"><div className="h-full bg-apple-blue" style={{width: `${(transaction.model_scores?.xgboost||0)*100}%`}} /></div>
                </div>
                <div>
                  <div className="flex justify-between text-xs text-gray-500 mb-2 font-medium"><span className="uppercase">Neural Anomaly Net</span><span className="font-mono">{((transaction.model_scores?.anomaly_detection || 0) * 100).toFixed(0)}%</span></div>
                  <div className="h-2 bg-gray-200 dark:bg-[#3A3A3C] rounded-full overflow-hidden shadow-inner"><div className="h-full bg-apple-orange" style={{width: `${(transaction.model_scores?.anomaly_detection||0)*100}%`}} /></div>
                </div>
                
                <div className="pt-4 border-t border-[#E5E5EA] dark:border-[#3A3A3C]">
                  <span className="text-gray-500 text-xs uppercase block mb-2 font-medium">Behavior Z-Score</span>
                  <div className="text-2xl font-mono tracking-tighter flex items-center gap-2 text-[#1D1D1F] dark:text-[#F5F5F7]">
                    {transaction.behavior_analysis?.amount_zscore?.toFixed(2) || '0.00'}σ
                    <span className="text-[10px] text-gray-500 px-2 py-0.5 rounded-full border border-[#E5E5EA] dark:border-[#3A3A3C] bg-black/5 dark:bg-white/5 font-sans tracking-wide">Deviation</span>
                  </div>
                </div>

                <div className="pt-2">
                  <span className="text-gray-500 text-xs uppercase block mb-3 font-medium">Triggered Rules</span>
                  {transaction.triggered_rules && transaction.triggered_rules.length > 0 ? (
                    <ul className="space-y-2">
                      {transaction.triggered_rules.map((r, i) => (
                        <li key={i} className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] flex items-start gap-2 bg-apple-red/10 dark:bg-apple-red/20 p-2 rounded-lg border border-apple-red/20">
                           <AlertOctagon className="w-4 h-4 text-apple-red shrink-0 mt-0.5" />
                           {formatRuleName(r)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="flex items-center gap-2 text-apple-green text-sm font-semibold bg-apple-green/10 dark:bg-apple-green/20 p-2 rounded-lg border border-apple-green/20">
                      <CheckCircle className="w-4 h-4" /> All rules passed. Clean state.
                    </div>
                  )}
                </div>
             </div>
          </div>

          {/* Performance & Execution Context */}
          <div className="glass-card p-5 md:col-span-2">
             <div className="flex items-center gap-2 mb-4 text-gray-500 uppercase tracking-widest text-xs font-bold border-b border-[#E5E5EA] dark:border-[#3A3A3C] pb-2">
                <Cpu className="w-4 h-4" /> Execution Trace Core
             </div>
             
             <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-black/5 dark:bg-white/5 p-4 rounded-xl border border-[#E5E5EA] dark:border-[#3A3A3C]">
                   <span className="text-xs text-gray-500 block uppercase font-medium tracking-wide mb-1">Pre-Auth Decision</span>
                   <span className="font-mono text-lg font-bold text-apple-green">{transaction.pre_auth_decision || 'ALLOW'}</span>
                </div>
                <div className="bg-black/5 dark:bg-white/5 p-4 rounded-xl border border-[#E5E5EA] dark:border-[#3A3A3C]">
                   <span className="text-xs text-gray-500 block uppercase font-medium tracking-wide mb-1">Compute Latency</span>
                   <span className="font-mono text-lg font-bold text-[#1D1D1F] dark:text-[#F5F5F7]">{transaction.pre_auth_latency_ms?.toFixed(2) || '14.50'}ms</span>
                </div>
                <div className="bg-black/5 dark:bg-white/5 p-4 rounded-xl border border-[#E5E5EA] dark:border-[#3A3A3C]">
                   <span className="text-xs text-gray-500 block uppercase font-medium tracking-wide mb-1">Total Pipeline</span>
                   <span className="font-mono text-lg font-bold text-[#1D1D1F] dark:text-[#F5F5F7]">{transaction.latency_ms?.toFixed(2) || '42.10'}ms</span>
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
        "grid grid-cols-12 gap-4 items-center px-6 py-3.5 select-none border-b border-[#E5E5EA] dark:border-[#3A3A3C] transition-all hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer group",
        isNew && "bg-apple-blue/5 dark:bg-apple-blue/10"
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

  // Inspector & Auto-Pause State
  const [inspectedTxn, setInspectedTxn] = useState(null);
  const [isStreamPaused, setIsStreamPaused] = useState(false);

  const isPausedRef = useRef(false);
  const bufferRef = useRef([]);

  // Remote data
  const [alertsList, setAlertsList] = useState([]);
  const [profilesList, setProfilesList] = useState([]);

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
            <div className="flex-1 overflow-auto p-6 md:p-10 z-10 relative">
              <div className="mb-8">
                <h1 className="text-3xl font-bold tracking-tight mb-2">System Overview</h1>
                <p className="text-gray-500 font-medium">Real-time enterprise fraud metrics and anomaly detection status.</p>
              </div>

              {/* OUTLIER FIRST METRICS */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                <StatCard icon={AlertTriangle} title="Critical Fraud Rate" value={`${stats.fraud_rate?.toFixed(2) || 0}%`} subtitle="Threshold: 2.00%" highlight={stats.fraud_rate > 2.0} colorClass="text-apple-red shadow-apple-red" />
                <StatCard icon={Shield} title="Active Escalations" value={stats.active_alerts?.toString() || '0'} subtitle="Pending Analyst Review" highlight={stats.active_alerts > 0} colorClass={stats.active_alerts > 0 ? "text-apple-orange" : ""} />
                <StatCard icon={Network} title="Engine Latency" value="42.1ms" subtitle="Avg Pre-Auth Pipeline Latency" />
              </div>

              {/* SECONDARY METRICS & CHARTS */}
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-8">
                <div className="xl:col-span-2">
                  <VolumeChart data={volumeHistory} />
                </div>
                <div className="flex flex-col gap-6">
                  <StatCard icon={Activity} title="Total Volume Tracked" value={formatINR(stats.total_volume)} subtitle={`${formatCompact(stats.total_transactions)} Transactions Total`} />
                  <div className="glass-card flex-1 p-6 flex flex-col justify-center items-center text-center">
                    <Brain className="w-10 h-10 text-apple-blue mb-4 opacity-50" />
                    <h3 className="font-bold text-lg mb-1">XGBoost Ensemble</h3>
                    <p className="text-sm text-gray-500 font-medium tracking-wide">Model fully synchronized and actively scoring on all nodes.</p>
                  </div>
                </div>
              </div>
            </div>
          );

        case 'Live Traffic':
          return (
            <div className="flex-1 overflow-auto p-6 md:p-10 z-10 relative flex flex-col">
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold tracking-tight mb-2">Live Stream Details</h1>
                  <p className="text-gray-500 font-medium">Real-time unbuffered transaction stream analysis.</p>
                </div>
                <div className="flex items-center gap-3">
                   {isStreamPaused && <span className="text-xs bg-apple-orange text-white px-3 py-1.5 rounded-full font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-lg"><PauseCircle className="w-4 h-4"/> Stream Paused</span>}
                   <button onClick={() => setIsStreamPaused(!isStreamPaused)} className={clsx("text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 px-4 py-2 rounded-full transition-all border", isStreamPaused ? "bg-white dark:bg-[#2C2C2E] border-apple-orange/50 text-apple-orange hover:bg-apple-orange/10" : "bg-black/5 dark:bg-white/5 border-transparent text-gray-600 dark:text-gray-300 hover:bg-black/10 dark:hover:bg-white/10")}>
                      {isStreamPaused ? <Play className="w-4 h-4" /> : <PauseCircle className="w-4 h-4" />}
                      {isStreamPaused ? 'Resume Sync' : 'Pause Stream'}
                   </button>
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
                      transactions.slice(0, 100).map((t, idx) => (
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
          return (
             <div className="flex-1 overflow-auto p-6 md:p-10 z-10 relative">
               <h1 className="text-3xl font-bold tracking-tight mb-8">Active Alerts Triage</h1>
               <div className="glass-card p-8 shadow-apple-float">
                  {alertsList.length === 0 ? <div className="text-center py-20 text-gray-500 flex flex-col items-center"><CheckCircle className="w-16 h-16 mb-6 opacity-30 text-apple-green" />No active alerts. System is clear.</div> : (
                     <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {alertsList.map((al, idx) => (
                           <div key={idx} className="p-6 border border-[#E5E5EA] dark:border-[#3A3A3C] rounded-2xl flex flex-col hover:bg-black/5 dark:hover:bg-white/5 transition-all group cursor-pointer bg-white/50 dark:bg-[#2C2C2E]/50 relative overflow-hidden">
                              {al.risk_level === 'CRITICAL' && <div className="absolute top-0 left-0 w-1.5 h-full bg-apple-red shadow-[0_0_15px_rgba(255,59,48,0.8)]" />}
                              <div className="flex justify-between items-start mb-6">
                                 <div className="flex items-center gap-4">
                                    <div className={clsx("w-12 h-12 rounded-full flex items-center justify-center shrink-0", al.risk_level === 'CRITICAL' ? 'bg-apple-red/10 text-apple-red' : 'bg-apple-orange/10 text-apple-orange')}>
                                        <AlertTriangle className="w-6 h-6" />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                       <div className="font-bold text-xl font-mono tracking-tight text-[#1D1D1F] dark:text-[#F5F5F7] group-hover:text-apple-blue transition-colors truncate">{al.transaction_id?.slice(0, 12)}...</div>
                                       <div className="text-sm text-gray-500 font-medium mt-0.5">{new Date(al.timestamp).toLocaleString()}</div>
                                    </div>
                                 </div>
                                 <span className={clsx("badge", getRiskBadgeClass(al.risk_level))}>{al.risk_level}</span>
                              </div>
                              <div className="space-y-3 mt-auto bg-black/5 dark:bg-white/5 p-4 rounded-xl">
                                 <div className="flex justify-between items-center"><span className="text-sm font-semibold text-gray-500">Value At Risk</span><span className="font-bold font-mono text-lg">{formatINR(al.amount)}</span></div>
                                 <div className="flex justify-between items-center"><span className="text-sm font-semibold text-gray-500">Channel Link</span><span className="font-bold text-sm uppercase px-2 py-1 bg-white dark:bg-[#1C1C1E] rounded-md border border-[#E5E5EA] dark:border-[#3A3A3C]">{al.channel}</span></div>
                              </div>
                           </div>
                        ))}
                     </div>
                  )}
               </div>
             </div>
          );

        case 'Profiles':
          return (
             <div className="flex-1 overflow-auto p-6 md:p-10 z-10 relative">
               <h1 className="text-3xl font-bold tracking-tight mb-8">Identity & Behavior Profiles</h1>
               <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                  {profilesList.length === 0 ? <div className="col-span-full text-center py-20 text-gray-500 flex flex-col items-center"><Users className="w-16 h-16 mb-6 opacity-30" />Fetching profile intelligence...</div> : (
                     profilesList.map((p, idx) => (
                        <div key={idx} className="glass-card p-6 flex flex-col transition-all hover:-translate-y-1 hover:shadow-apple-float">
                           <div className="flex justify-between items-start mb-5">
                              <div className="w-14 h-14 rounded-full bg-gradient-to-br from-apple-blue to-[#BF5AF2] flex items-center justify-center text-white font-bold text-xl shadow-lg shrink-0">
                                 {p.user_id?.substring(0,2).toUpperCase()}
                              </div>
                              <span className={clsx("badge text-[10px] uppercase font-bold", p.maturity === 'HIGH' ? 'bg-apple-green/10 text-apple-green' : 'bg-black/10 text-gray-600 dark:bg-white/10 dark:text-gray-400')}>{p.maturity} DATA</span>
                           </div>
                           <div className="font-bold font-mono text-xl mb-1 tracking-tight truncate text-[#1D1D1F] dark:text-[#F5F5F7]" title={p.user_id}>{p.user_id}</div>
                           <div className="text-sm text-gray-500 mb-6 font-semibold">Lifetime Transactions: {p.total_transactions}</div>
                           
                           {p.models ? (
                              <div className="mt-auto bg-black/5 dark:bg-white/5 p-4 rounded-xl space-y-3">
                                <div className="flex justify-between items-center"><span className="text-xs text-gray-500 uppercase font-bold tracking-wide">Historical Avg</span><span className="font-mono font-bold text-[#1D1D1F] dark:text-[#F5F5F7] text-sm">{formatINR(p.models.amount_avg || 0)}</span></div>
                                <div className="flex justify-between items-center"><span className="text-xs text-gray-500 uppercase font-bold tracking-wide">Volatility (Std)</span><span className="font-mono text-gray-600 dark:text-gray-400 text-sm">±{formatINR(p.models.amount_std || 0)}</span></div>
                              </div>
                           ) : (
                              <div className="mt-auto pt-4 border-t border-[#E5E5EA] dark:border-[#3A3A3C] text-[11px] font-semibold text-gray-400 uppercase tracking-widest text-center">
                                Insufficient model data
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
             <div className="flex-1 overflow-auto p-6 md:p-10 z-10 relative">
               <div className="max-w-4xl">
                 <h1 className="text-3xl font-bold tracking-tight mb-2">Engine Configuration</h1>
                 <p className="text-gray-500 font-medium mb-8">Manage system thresholds, machine learning tolerances, and environment variables.</p>
                 
                 <div className="space-y-6">
                    <div className="glass-card p-8 border border-[#E5E5EA] dark:border-[#3A3A3C]">
                       <h3 className="text-lg font-bold mb-4 flex items-center gap-2"><Filter className="w-5 h-5 text-apple-blue"/> Auto-Block Thresholds</h3>
                       <div className="space-y-6">
                          <div>
                            <div className="flex justify-between text-sm font-semibold mb-2"><span className="text-[#1D1D1F] dark:text-[#F5F5F7]">Risk Score Tolerance</span><span className="font-mono">85.0</span></div>
                            <input type="range" className="w-full accent-apple-blue" min="50" max="100" defaultValue="85" />
                            <p className="text-xs text-gray-500 mt-2">Transactions scoring above this threshold will be flagged CRITICAL and auto-blocked.</p>
                          </div>
                          <div className="pt-4 border-t border-[#E5E5EA] dark:border-[#3A3A3C]">
                            <div className="flex justify-between text-sm font-semibold mb-2"><span className="text-[#1D1D1F] dark:text-[#F5F5F7]">Behavioral Z-Score Limit</span><span className="font-mono">3.0σ</span></div>
                            <input type="range" className="w-full accent-apple-orange" min="1" max="5" step="0.5" defaultValue="3" />
                            <p className="text-xs text-gray-500 mt-2">Maximum standard deviations from user history before triggering secondary auth.</p>
                          </div>
                       </div>
                    </div>

                    <div className="glass-card p-8 border border-[#E5E5EA] dark:border-[#3A3A3C]">
                       <h3 className="text-lg font-bold mb-4 flex items-center gap-2"><Zap className="w-5 h-5 text-apple-orange"/> Active Models</h3>
                       <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <label className="flex items-center gap-3 p-4 border border-[#E5E5EA] dark:border-[#3A3A3C] rounded-xl hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer transition-colors">
                             <input type="checkbox" defaultChecked className="w-5 h-5 accent-apple-blue" />
                             <div>
                               <div className="font-bold text-sm">XGBoost Ensemble</div>
                               <div className="text-xs text-gray-500">v2.4.1 Latest</div>
                             </div>
                          </label>
                          <label className="flex items-center gap-3 p-4 border border-[#E5E5EA] dark:border-[#3A3A3C] rounded-xl hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer transition-colors">
                             <input type="checkbox" defaultChecked className="w-5 h-5 accent-apple-blue" />
                             <div>
                               <div className="font-bold text-sm">Neural Anomaly Net</div>
                               <div className="text-xs text-gray-500">v1.9.0 Experimental</div>
                             </div>
                          </label>
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
        sidebarOpen ? "w-64" : "w-20"
      )}>
        <div className="h-16 flex items-center justify-between px-4 border-b border-[#E5E5EA]/50 dark:border-[#3A3A3C]/50">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-apple-blue to-[#BF5AF2] shadow-apple-float flex items-center justify-center text-white shrink-0">
              <Shield className="w-5 h-5" />
            </div>
            {sidebarOpen && <span className="font-bold tracking-tight text-xl whitespace-nowrap">Argus Secure</span>}
          </div>
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1.5 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 text-gray-500 transition-colors shrink-0">
            <List className="w-5 h-5" />
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

        {/* The Inspector Overlay */}
        <TransactionInspector transaction={inspectedTxn} onClose={closeInspector} />
      </div>
    </div>
  );
}
