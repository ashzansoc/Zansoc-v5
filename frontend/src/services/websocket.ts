import { io, Socket } from 'socket.io-client';
import { Node, ActiveCluster } from '../types';

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(): void {
    const wsUrl = process.env.REACT_APP_WS_URL || 'http://localhost:5000';
    
    this.socket = io(wsUrl, {
      transports: ['websocket'],
      autoConnect: true,
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      this.handleReconnect();
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.handleReconnect();
    });
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.socket?.connect();
      }, 2000 * this.reconnectAttempts);
    }
  }

  subscribeToNodeUpdates(callback: (nodes: Node[]) => void): void {
    if (!this.socket) return;
    
    this.socket.emit('subscribe_nodes');
    this.socket.on('node_status_changed', callback);
  }

  subscribeToClusterUpdates(clusterId: string, callback: (cluster: ActiveCluster) => void): void {
    if (!this.socket) return;
    
    this.socket.emit('subscribe_cluster', { cluster_id: clusterId });
    this.socket.on('cluster_metrics_updated', callback);
  }

  unsubscribeFromNodeUpdates(): void {
    if (!this.socket) return;
    this.socket.off('node_status_changed');
  }

  unsubscribeFromClusterUpdates(): void {
    if (!this.socket) return;
    this.socket.off('cluster_metrics_updated');
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }
}

export const wsService = new WebSocketService();
export default wsService;