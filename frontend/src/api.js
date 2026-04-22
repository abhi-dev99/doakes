/**
 * ARGUS API Client
 * Handles REST API calls and WebSocket connection
 */

const API_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

// ============ REST API ============

const api = {
  baseUrl: API_BASE,
  
  async getStats() {
    const res = await fetch(`${API_BASE}/api/stats`);
    if (!res.ok) throw new Error('Failed to fetch stats');
    return res.json();
  },
  
  async getTransactions(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/api/transactions?${query}`);
    if (!res.ok) throw new Error('Failed to fetch transactions');
    return res.json();
  },
  
  async analyzeTransaction(txn) {
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(txn)
    });
    if (!res.ok) throw new Error('Failed to analyze transaction');
    return res.json();
  },
  
  async getModelStats() {
    const res = await fetch(`${API_BASE}/api/model/stats`);
    if (!res.ok) throw new Error('Failed to fetch model stats');
    return res.json();
  },
  
  async getAlerts(limit = 20) {
    const res = await fetch(`${API_BASE}/api/alerts?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch alerts');
    return res.json();
  },
  
  async getProfiles(limit = 50) {
    const res = await fetch(`${API_BASE}/api/users/profiles?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch profiles');
    return res.json();
  },
  
  async updateAlert(alertId, status) {
    const res = await fetch(`${API_BASE}/api/alerts/${alertId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    if (!res.ok) throw new Error('Failed to update alert');
    return res.json();
  },
  
  async startSimulation(rate = 3) {
    const res = await fetch(`${API_BASE}/api/simulation/start?rate=${rate}`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to start simulation');
    return res.json();
  },
  
  async stopSimulation() {
    const res = await fetch(`${API_BASE}/api/simulation/stop`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to stop simulation');
    return res.json();
  },
  
  async getSimulationStatus() {
    const res = await fetch(`${API_BASE}/api/simulation/status`);
    if (!res.ok) throw new Error('Failed to get simulation status');
    return res.json();
  },
  
  async exportData() {
    const res = await fetch(`${API_BASE}/api/export`);
    if (!res.ok) throw new Error('Failed to export data');
    return res.blob();
  },
  
  async clearData() {
    const res = await fetch(`${API_BASE}/api/data`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to clear data');
    return res.json();
  }
};

// ============ WEBSOCKET WITH THROTTLING ============

export class WebSocketClient {
  constructor(onMessage, onConnect, onDisconnect) {
    this.ws = null;
    this.url = WS_URL;
    this.onMessage = onMessage;
    this.onConnect = onConnect;
    this.onDisconnect = onDisconnect;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1000;
    this.pingInterval = null;
    
    // Throttling for performance - batch updates
    this.messageQueue = [];
    this.throttleMs = 150;
    this.throttleTimer = null;
  }
  
  connect() {
    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('[WS] Connected');
        this.reconnectAttempts = 0;
        this.onConnect?.();
        this.startPing();
      };
      
      this.ws.onmessage = (event) => {
        try {
          if (event.data === 'pong') return;
          const data = JSON.parse(event.data);
          if (data.type === 'heartbeat') return;
          
          if (data.type === 'transaction') {
            this.messageQueue.push(data);
            this.scheduleProcessing();
          } else {
            this.onMessage?.(data);
          }
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };
      
      this.ws.onclose = () => {
        console.log('[WS] Disconnected');
        this.stopPing();
        this.onDisconnect?.();
        this.attemptReconnect();
      };
      
      this.ws.onerror = (error) => {
        console.error('[WS] Error:', error);
      };
      
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      this.attemptReconnect();
    }
  }
  
  scheduleProcessing() {
    if (!this.throttleTimer) {
      this.throttleTimer = setTimeout(() => {
        this.processQueue();
      }, this.throttleMs);
    }
  }
  
  processQueue() {
    this.throttleTimer = null;
    if (this.messageQueue.length > 0) {
      const queued = [...this.messageQueue];
      this.messageQueue = [];
      queued.forEach((message) => this.onMessage?.(message));
    }
  }
  
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WS] Max reconnection attempts reached');
      return;
    }
    
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
    console.log(`[WS] Reconnecting in ${delay}ms`);
    setTimeout(() => this.connect(), delay);
  }
  
  startPing() {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 25000);
  }
  
  stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
  
  disconnect() {
    this.stopPing();
    if (this.throttleTimer) {
      clearTimeout(this.throttleTimer);
      this.throttleTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
  
  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }
}

export default api;
