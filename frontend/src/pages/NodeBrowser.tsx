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
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Computer as ComputerIcon,
  Memory as MemoryIcon,
  Storage as StorageIcon,
  LocationOn as LocationIcon,
} from '@mui/icons-material';
import { Node, FilterState } from '../types';

// Mock data for demonstration
const mockNodes: Node[] = [
  {
    id: 'rpi-001',
    name: 'RaspberryPi Node 1',
    type: 'raspberry-pi',
    specs: { cpu: 'ARM Cortex-A72', cores: 4, ram: 8, storage: 64 },
    location: { region: 'US-West', city: 'San Francisco', coordinates: [37.7749, -122.4194] },
    status: 'online',
    pricing: { hourlyRate: 0.05, currency: 'USD' },
    availability: {},
  },
  {
    id: 'rpi-002',
    name: 'RaspberryPi Node 2',
    type: 'raspberry-pi',
    specs: { cpu: 'ARM Cortex-A72', cores: 4, ram: 8, storage: 32 },
    location: { region: 'US-East', city: 'New York', coordinates: [40.7128, -74.0060] },
    status: 'online',
    pricing: { hourlyRate: 0.05, currency: 'USD' },
    availability: {},
  },
  {
    id: 'laptop-001',
    name: 'Laptop Node 1',
    type: 'laptop',
    specs: { cpu: 'Intel i7-12700H', cores: 12, ram: 16, storage: 512 },
    location: { region: 'US-West', city: 'Seattle', coordinates: [47.6062, -122.3321] },
    status: 'online',
    pricing: { hourlyRate: 0.15, currency: 'USD' },
    availability: {},
  },
];

const NodeBrowser: React.FC = () => {
  const [nodes, setNodes] = useState<Node[]>(mockNodes);
  const [selectedNodes, setSelectedNodes] = useState<string[]>([]);
  const [filters, setFilters] = useState<FilterState>({});

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'success';
      case 'offline': return 'error';
      case 'busy': return 'warning';
      default: return 'default';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'raspberry-pi': return '🥧';
      case 'laptop': return '💻';
      case 'server': return '🖥️';
      default: return '💻';
    }
  };

  const handleNodeSelect = (nodeId: string) => {
    setSelectedNodes(prev => 
      prev.includes(nodeId) 
        ? prev.filter(id => id !== nodeId)
        : [...prev, nodeId]
    );
  };

  const totalCost = selectedNodes.reduce((sum, nodeId) => {
    const node = nodes.find(n => n.id === nodeId);
    return sum + (node?.pricing.hourlyRate || 0);
  }, 0);

  const NodeCard: React.FC<{ node: Node }> = ({ node }) => (
    <Card 
      elevation={selectedNodes.includes(node.id) ? 4 : 1}
      sx={{ 
        cursor: 'pointer',
        border: selectedNodes.includes(node.id) ? '2px solid #1976d2' : '1px solid #e0e0e0',
        '&:hover': { elevation: 3 }
      }}
      onClick={() => handleNodeSelect(node.id)}
    >
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="h6">
              {getTypeIcon(node.type)} {node.name}
            </Typography>
          </Box>
          <Chip 
            label={node.status} 
            color={getStatusColor(node.status) as any}
            size="small"
          />
        </Box>

        <Grid container spacing={2} mb={2}>
          <Grid item xs={6}>
            <Box display="flex" alignItems="center" gap={1}>
              <ComputerIcon fontSize="small" color="action" />
              <Typography variant="body2">{node.specs.cores} cores</Typography>
            </Box>
          </Grid>
          <Grid item xs={6}>
            <Box display="flex" alignItems="center" gap={1}>
              <MemoryIcon fontSize="small" color="action" />
              <Typography variant="body2">{node.specs.ram} GB RAM</Typography>
            </Box>
          </Grid>
          <Grid item xs={6}>
            <Box display="flex" alignItems="center" gap={1}>
              <StorageIcon fontSize="small" color="action" />
              <Typography variant="body2">{node.specs.storage} GB</Typography>
            </Box>
          </Grid>
          <Grid item xs={6}>
            <Box display="flex" alignItems="center" gap={1}>
              <LocationIcon fontSize="small" color="action" />
              <Typography variant="body2">{node.location.city}</Typography>
            </Box>
          </Grid>
        </Grid>

        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="body2" color="textSecondary">
            {node.specs.cpu}
          </Typography>
          <Typography variant="h6" color="primary">
            ${node.pricing.hourlyRate}/hr
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );

  return (
    <Container maxWidth="lg">
      <Box mb={4}>
        <Typography variant="h4" component="h1" gutterBottom>
          Browse Compute Nodes
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Select nodes to create your distributed compute cluster
        </Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <Card elevation={1}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Filters
              </Typography>
              
              <Box display="flex" flexDirection="column" gap={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>Node Type</InputLabel>
                  <Select
                    value={filters.nodeType?.[0] || ''}
                    label="Node Type"
                    onChange={(e) => setFilters({...filters, nodeType: e.target.value ? [e.target.value] : undefined})}
                  >
                    <MenuItem value="">All Types</MenuItem>
                    <MenuItem value="raspberry-pi">Raspberry Pi</MenuItem>
                    <MenuItem value="laptop">Laptop</MenuItem>
                    <MenuItem value="server">Server</MenuItem>
                  </Select>
                </FormControl>

                <FormControl fullWidth size="small">
                  <InputLabel>Region</InputLabel>
                  <Select
                    value={filters.region?.[0] || ''}
                    label="Region"
                    onChange={(e) => setFilters({...filters, region: e.target.value ? [e.target.value] : undefined})}
                  >
                    <MenuItem value="">All Regions</MenuItem>
                    <MenuItem value="US-West">US West</MenuItem>
                    <MenuItem value="US-East">US East</MenuItem>
                  </Select>
                </FormControl>

                <TextField
                  label="Min Cores"
                  type="number"
                  size="small"
                  value={filters.minCores || ''}
                  onChange={(e) => setFilters({...filters, minCores: e.target.value ? Number(e.target.value) : undefined})}
                />

                <TextField
                  label="Min RAM (GB)"
                  type="number"
                  size="small"
                  value={filters.minRam || ''}
                  onChange={(e) => setFilters({...filters, minRam: e.target.value ? Number(e.target.value) : undefined})}
                />
              </Box>
            </CardContent>
          </Card>

          {selectedNodes.length > 0 && (
            <Card elevation={2} sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Selected Nodes ({selectedNodes.length})
                </Typography>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  Estimated cost: ${totalCost.toFixed(2)}/hr
                </Typography>
                <Button 
                  variant="contained" 
                  fullWidth 
                  sx={{ mt: 2 }}
                  disabled={selectedNodes.length === 0}
                >
                  Configure Cluster
                </Button>
              </CardContent>
            </Card>
          )}
        </Grid>

        <Grid item xs={12} md={9}>
          <Grid container spacing={2}>
            {nodes.map((node) => (
              <Grid item xs={12} sm={6} lg={4} key={node.id}>
                <NodeCard node={node} />
              </Grid>
            ))}
          </Grid>
        </Grid>
      </Grid>
    </Container>
  );
};

export default NodeBrowser;