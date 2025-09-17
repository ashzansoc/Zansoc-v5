import axios from 'axios';
import { Node, ClusterConfig, ActiveCluster, FilterState } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth tokens if needed
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const nodeService = {
  async getNodes(filters?: FilterState): Promise<Node[]> {
    const response = await apiClient.get('/nodes', { params: filters });
    return response.data;
  },

  async getNodeStatus(nodeId: string): Promise<Node> {
    const response = await apiClient.get(`/nodes/${nodeId}/status`);
    return response.data;
  },
};

export const clusterService = {
  async createCluster(config: ClusterConfig): Promise<ActiveCluster> {
    const response = await apiClient.post('/clusters', config);
    return response.data;
  },

  async getCluster(clusterId: string): Promise<ActiveCluster> {
    const response = await apiClient.get(`/clusters/${clusterId}`);
    return response.data;
  },

  async getClusters(): Promise<ActiveCluster[]> {
    const response = await apiClient.get('/clusters');
    return response.data;
  },

  async performClusterAction(clusterId: string, action: string): Promise<any> {
    const response = await apiClient.post(`/clusters/${clusterId}/actions`, { action });
    return response.data;
  },
};

export default apiClient;