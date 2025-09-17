import React, { useState } from 'react';
import {
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Box,
  Chip,
  Button,
  LinearProgress,
  IconButton,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  MoreVert as MoreVertIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';
import { ActiveCluster } from '../types';

// Mock data for demonstration
const mockClusters: ActiveCluster[] = [
  {
    id: 'cluster-001',
    name: 'ML Training Cluster',
    status: 'running',
    nodes: [
      { nodeId: 'rpi-001', role: 'master', status: 'online' },
      { nodeId: 'rpi-002', role: 'worker', status: 'online' },
      { nodeId: 'laptop-001', role: 'worker', status: 'online' },
    ],
    metrics: {
      cpuUsage: 75,
      memoryUsage: 60,
      networkTraffic: 45,
      uptime: 3600, // 1 hour in seconds
    },
    cost: {
      current: 2.45,
      projected: 5.20,
    },
    connectionInfo: {
      rayDashboardUrl: 'http://localhost:8265',
      apiEndpoint: 'http://cluster-001.zansoc.local:10001',
      credentials: {
        username: 'admin',
        password: 'secure123',
      },
    },
  },
  {
    id: 'cluster-002',
    name: 'Inference Cluster',
    status: 'paused',
    nodes: [
      { nodeId: 'rpi-003', role: 'master', status: 'online' },
      { nodeId: 'rpi-004', role: 'worker', status: 'online' },
    ],
    metrics: {
      cpuUsage: 0,
      memoryUsage: 20,
      networkTraffic: 0,
      uptime: 7200, // 2 hours
    },
    cost: {
      current: 1.20,
      projected: 2.40,
    },
    connectionInfo: {
      rayDashboardUrl: 'http://localhost:8266',
      apiEndpoint: 'http://cluster-002.zansoc.local:10002',
      credentials: {
        username: 'admin',
        password: 'secure456',
      },
    },
  },
];

const ActiveClusters: React.FC = () => {
  const [clusters, setClusters] = useState<ActiveCluster[]>(mockClusters);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedCluster, setSelectedCluster] = useState<string | null>(null);

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, clusterId: string) => {
    setAnchorEl(event.currentTarget);
    setSelectedCluster(clusterId);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedCluster(null);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'success';
      case 'paused': return 'warning';
      case 'error': return 'error';
      case 'initializing': return 'info';
      default: return 'default';
    }
  };

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const ClusterCard: React.FC<{ cluster: ActiveCluster }> = ({ cluster }) => (
    <Card elevation={2}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Box>
            <Typography variant="h6" gutterBottom>
              {cluster.name}
            </Typography>
            <Chip 
              label={cluster.status} 
              color={getStatusColor(cluster.status) as any}
              size="small"
            />
          </Box>
          <IconButton 
            size="small"
            onClick={(e) => handleMenuClick(e, cluster.id)}
          >
            <MoreVertIcon />
          </IconButton>
        </Box>

        <Grid container spacing={2} mb={2}>
          <Grid item xs={6}>
            <Typography variant="body2" color="textSecondary">Nodes</Typography>
            <Typography variant="body1">{cluster.nodes.length}</Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="body2" color="textSecondary">Uptime</Typography>
            <Typography variant="body1">{formatUptime(cluster.metrics.uptime)}</Typography>
          </Grid>
        </Grid>

        <Box mb={2}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="body2" color="textSecondary">CPU Usage</Typography>
            <Typography variant="body2">{cluster.metrics.cpuUsage}%</Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={cluster.metrics.cpuUsage} 
            sx={{ height: 6, borderRadius: 3 }}
          />
        </Box>

        <Box mb={2}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="body2" color="textSecondary">Memory Usage</Typography>
            <Typography variant="body2">{cluster.metrics.memoryUsage}%</Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={cluster.metrics.memoryUsage} 
            sx={{ height: 6, borderRadius: 3 }}
            color="secondary"
          />
        </Box>

        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="body2" color="textSecondary">
            Current Cost: ${cluster.cost.current.toFixed(2)}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Projected: ${cluster.cost.projected.toFixed(2)}
          </Typography>
        </Box>

        <Box display="flex" gap={1}>
          {cluster.status === 'running' && (
            <Button
              size="small"
              startIcon={<PauseIcon />}
              variant="outlined"
            >
              Pause
            </Button>
          )}
          {cluster.status === 'paused' && (
            <Button
              size="small"
              startIcon={<PlayIcon />}
              variant="contained"
            >
              Resume
            </Button>
          )}
          <Button
            size="small"
            startIcon={<OpenInNewIcon />}
            variant="outlined"
            onClick={() => window.open(cluster.connectionInfo.rayDashboardUrl, '_blank')}
          >
            Dashboard
          </Button>
        </Box>
      </CardContent>
    </Card>
  );

  return (
    <Container maxWidth="lg">
      <Box mb={4}>
        <Typography variant="h4" component="h1" gutterBottom>
          Active Clusters
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Monitor and manage your running compute clusters
        </Typography>
      </Box>

      {clusters.length === 0 ? (
        <Card elevation={1}>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="textSecondary" gutterBottom>
              No Active Clusters
            </Typography>
            <Typography variant="body2" color="textSecondary" mb={3}>
              You don't have any running clusters. Start by browsing available nodes.
            </Typography>
            <Button variant="contained" href="/nodes">
              Browse Nodes
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {clusters.map((cluster) => (
            <Grid item xs={12} md={6} lg={4} key={cluster.id}>
              <ClusterCard cluster={cluster} />
            </Grid>
          ))}
        </Grid>
      )}

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleMenuClose}>
          <PlayIcon sx={{ mr: 1 }} fontSize="small" />
          Scale Up
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <PauseIcon sx={{ mr: 1 }} fontSize="small" />
          Scale Down
        </MenuItem>
        <MenuItem onClick={handleMenuClose} sx={{ color: 'error.main' }}>
          <StopIcon sx={{ mr: 1 }} fontSize="small" />
          Terminate
        </MenuItem>
      </Menu>
    </Container>
  );
};

export default ActiveClusters;