/**
 * WebSocket Manager - Real-time Data Updates
 * Handles WebSocket connections for live cost tracking, alerts, and updates
 */

class WebSocketManager {
    constructor(options = {}) {
        this.url = options.url || this.getWebSocketURL();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.listeners = {};
        this.connected = false;
        this.shouldReconnect = true;
        this.messageQueue = [];
    }

    /**
     * Get WebSocket URL based on current environment
     */
    getWebSocketURL() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws/realtime`;
    }

    /**
     * Connect to WebSocket server
     */
    connect(apiKey) {
        if (this.ws && this.connected) {
            console.log('WebSocket already connected');
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(this.url);

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.connected = true;
                    this.reconnectAttempts = 0;

                    // Authenticate with API key
                    this.send({
                        type: 'auth',
                        token: apiKey
                    });

                    // Send any queued messages
                    while (this.messageQueue.length > 0) {
                        const message = this.messageQueue.shift();
                        this.ws.send(JSON.stringify(message));
                    }

                    this.emit('connected');
                    resolve();
                };

                this.ws.onmessage = (event) => {
                    this.handleMessage(JSON.parse(event.data));
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.emit('error', error);
                    reject(error);
                };

                this.ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    this.connected = false;
                    this.emit('disconnected');
                    
                    if (this.shouldReconnect) {
                        this.attemptReconnect();
                    }
                };
            } catch (error) {
                console.error('Failed to create WebSocket:', error);
                reject(error);
            }
        });
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(message) {
        const { type, data, id } = message;

        switch (type) {
            case 'cost_update':
                this.emit('cost_update', data);
                break;

            case 'alert':
                this.emit('alert', data);
                break;

            case 'anomaly_detected':
                this.emit('anomaly', data);
                break;

            case 'budget_warning':
                this.emit('budget_warning', data);
                break;

            case 'real_time_metrics':
                this.emit('metrics_update', data);
                break;

            case 'team_activity':
                this.emit('activity_update', data);
                break;

            case 'pong':
                this.emit('pong', data);
                break;

            default:
                console.warn('Unknown message type:', type);
        }
    }

    /**
     * Send message through WebSocket
     */
    send(message) {
        if (!this.connected) {
            this.messageQueue.push(message);
            return;
        }

        try {
            this.ws.send(JSON.stringify(message));
        } catch (error) {
            console.error('Failed to send WebSocket message:', error);
            this.messageQueue.push(message);
        }
    }

    /**
     * Subscribe to cost updates for specific team
     */
    subscribeToCosts(teamId) {
        this.send({
            type: 'subscribe',
            channel: 'costs',
            filters: { team_id: teamId }
        });
    }

    /**
     * Subscribe to alerts
     */
    subscribeToAlerts() {
        this.send({
            type: 'subscribe',
            channel: 'alerts'
        });
    }

    /**
     * Subscribe to anomalies
     */
    subscribeToAnomalies() {
        this.send({
            type: 'subscribe',
            channel: 'anomalies'
        });
    }

    /**
     * Subscribe to budget warnings
     */
    subscribeToBudgets() {
        this.send({
            type: 'subscribe',
            channel: 'budgets'
        });
    }

    /**
     * Get real-time metrics
     */
    requestMetrics() {
        this.send({
            type: 'request',
            channel: 'metrics',
            id: `metrics_${Date.now()}`
        });
    }

    /**
     * Unsubscribe from channel
     */
    unsubscribe(channel) {
        this.send({
            type: 'unsubscribe',
            channel: channel
        });
    }

    /**
     * Ping server to keep connection alive
     */
    ping() {
        this.send({
            type: 'ping',
            timestamp: Date.now()
        });
    }

    /**
     * Register event listener
     */
    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }

    /**
     * Remove event listener
     */
    off(event, callback) {
        if (!this.listeners[event]) return;
        this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }

    /**
     * Emit event to listeners
     */
    emit(event, data) {
        if (!this.listeners[event]) return;
        this.listeners[event].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`Error in ${event} listener:`, error);
            }
        });
    }

    /**
     * Attempt to reconnect with exponential backoff
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.emit('reconnect_failed');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => {
            const apiKey = localStorage.getItem('substacker_api_key');
            if (apiKey) {
                this.connect(apiKey).catch(error => {
                    console.error('Reconnection failed:', error);
                });
            }
        }, delay);
    }

    /**
     * Disconnect WebSocket
     */
    disconnect() {
        this.shouldReconnect = false;
        if (this.ws) {
            this.ws.close();
        }
        this.connected = false;
    }

    /**
     * Check if WebSocket is connected
     */
    isConnected() {
        return this.connected && this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

// Create global WebSocket manager instance
window.wsManager = new WebSocketManager();

// Auto-connect if API key exists
document.addEventListener('DOMContentLoaded', () => {
    const apiKey = localStorage.getItem('substacker_api_key');
    if (apiKey) {
        window.wsManager.connect(apiKey).catch(error => {
            console.error('Failed to connect WebSocket:', error);
        });

        // Keep connection alive with ping every 30 seconds
        setInterval(() => {
            if (window.wsManager.isConnected()) {
                window.wsManager.ping();
            }
        }, 30000);
    }
});
