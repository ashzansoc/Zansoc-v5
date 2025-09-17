export interface Node {
  id: string;
  name: string;
  type: 'raspberry-pi' | 'laptop' | 'server';
  specs: {
    cpu: string;
    cores: number;
    ram: number; // GB
    storage: number; // GB
    gpu?: string;
  };
  location: {
    region: string;
    city: string;
    coordinates: [number, number];
  };
  status: 'online' | 'offline' | 'busy';
  pricing: {
    hourlyRate: number;
    currency: 'USD';
  };
  availability: {
    estimatedAvailable?: Date;
    maintenanceWindow?: TimeWindow;
  };
}

export interface TimeWindow {
  start: Date;
  end: Date;
}

export interface FilterState {
  nodeType?: string[];
  region?: string[];
  minCores?: number;
  maxCores?: number;
  minRam?: number;
  maxRam?: number;
  minPrice?: number;
  maxPrice?: number;
  status?: string[];
}

export interface ClusterConfig {
  name: string;
  description: string;
  masterNodeId: string;
  workerNodeIds: string[];
  runtime: {
    duration?: number; // hours
    autoShutdown: boolean;
    shutdownConditions: ShutdownCondition[];
  };
  tags: string[];
  estimatedCost: number;
}

export interface ShutdownCondition {
  type: 'idle_time' | 'max_cost' | 'scheduled_time';
  value: number | Date;
}

export interface ActiveCluster {
  id: string;
  name: string;
  status: 'initializing' | 'running' | 'paused' | 'error';
  nodes: ClusterNode[];
  metrics: {
    cpuUsage: number;
    memoryUsage: number;
    networkTraffic: number;
    uptime: number;
  };
  cost: {
    current: number;
    projected: number;
  };
  connectionInfo: {
    rayDashboardUrl: string;
    apiEndpoint: string;
    credentials: ClusterCredentials;
  };
}

export interface ClusterNode {
  nodeId: string;
  role: 'master' | 'worker';
  status: 'online' | 'offline' | 'error';
}

export interface ClusterCredentials {
  username: string;
  password: string;
  token?: string;
}

export type ClusterAction = 'scale_up' | 'scale_down' | 'pause' | 'resume' | 'terminate';