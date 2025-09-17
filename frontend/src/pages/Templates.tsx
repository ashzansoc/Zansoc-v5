import React, { useState } from 'react';
import {
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Box,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import {
  Add as AddIcon,
  MoreVert as MoreVertIcon,
  Computer as ComputerIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Launch as LaunchIcon,
} from '@mui/icons-material';

interface ClusterTemplate {
  id: string;
  name: string;
  description: string;
  nodeCount: number;
  estimatedCost: number;
  tags: string[];
  createdAt: Date;
}

// Mock data for demonstration
const mockTemplates: ClusterTemplate[] = [
  {
    id: 'template-001',
    name: 'ML Training Setup',
    description: 'Standard configuration for machine learning training workloads',
    nodeCount: 4,
    estimatedCost: 0.25,
    tags: ['ml', 'training', 'gpu'],
    createdAt: new Date('2024-01-10'),
  },
  {
    id: 'template-002',
    name: 'Inference Cluster',
    description: 'Lightweight setup for model inference and serving',
    nodeCount: 2,
    estimatedCost: 0.10,
    tags: ['inference', 'serving'],
    createdAt: new Date('2024-01-08'),
  },
];

const Templates: React.FC = () => {
  const [templates, setTemplates] = useState<ClusterTemplate[]>(mockTemplates);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newTemplate, setNewTemplate] = useState({
    name: '',
    description: '',
  });

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, templateId: string) => {
    setAnchorEl(event.currentTarget);
    setSelectedTemplate(templateId);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedTemplate(null);
  };

  const handleCreateTemplate = () => {
    // In a real app, this would save to the backend
    const template: ClusterTemplate = {
      id: `template-${Date.now()}`,
      name: newTemplate.name,
      description: newTemplate.description,
      nodeCount: 0,
      estimatedCost: 0,
      tags: [],
      createdAt: new Date(),
    };

    setTemplates([...templates, template]);
    setCreateDialogOpen(false);
    setNewTemplate({ name: '', description: '' });
  };

  const TemplateCard: React.FC<{ template: ClusterTemplate }> = ({ template }) => (
    <Card elevation={2}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Box>
            <Typography variant="h6" gutterBottom>
              {template.name}
            </Typography>
            <Typography variant="body2" color="textSecondary" paragraph>
              {template.description}
            </Typography>
          </Box>
          <IconButton
            size="small"
            onClick={(e) => handleMenuClick(e, template.id)}
          >
            <MoreVertIcon />
          </IconButton>
        </Box>

        <Grid container spacing={2} mb={2}>
          <Grid item xs={6}>
            <Box display="flex" alignItems="center" gap={1}>
              <ComputerIcon fontSize="small" color="action" />
              <Typography variant="body2">{template.nodeCount} nodes</Typography>
            </Box>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="body2" color="textSecondary">
              Est. ${template.estimatedCost.toFixed(2)}/hr
            </Typography>
          </Grid>
        </Grid>

        <Box display="flex" flexWrap="wrap" gap={1} mb={2}>
          {template.tags.map((tag) => (
            <Box
              key={tag}
              sx={{
                px: 1,
                py: 0.5,
                backgroundColor: 'primary.light',
                color: 'primary.contrastText',
                borderRadius: 1,
                fontSize: '0.75rem',
              }}
            >
              {tag}
            </Box>
          ))}
        </Box>

        <Typography variant="caption" color="textSecondary" display="block" mb={2}>
          Created {template.createdAt.toLocaleDateString()}
        </Typography>

        <Button
          variant="contained"
          size="small"
          startIcon={<LaunchIcon />}
          fullWidth
        >
          Use Template
        </Button>
      </CardContent>
    </Card>
  );

  return (
    <Container maxWidth="lg">
      <Box mb={4} display="flex" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Cluster Templates
          </Typography>
          <Typography variant="body1" color="textSecondary">
            Save and reuse cluster configurations for quick deployment
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Template
        </Button>
      </Box>

      {templates.length === 0 ? (
        <Card elevation={1}>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="textSecondary" gutterBottom>
              No Templates Yet
            </Typography>
            <Typography variant="body2" color="textSecondary" mb={3}>
              Create your first cluster template to save time on future deployments.
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
            >
              Create Template
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {templates.map((template) => (
            <Grid item xs={12} md={6} lg={4} key={template.id}>
              <TemplateCard template={template} />
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
          <EditIcon sx={{ mr: 1 }} fontSize="small" />
          Edit Template
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <LaunchIcon sx={{ mr: 1 }} fontSize="small" />
          Use Template
        </MenuItem>
        <MenuItem onClick={handleMenuClose} sx={{ color: 'error.main' }}>
          <DeleteIcon sx={{ mr: 1 }} fontSize="small" />
          Delete Template
        </MenuItem>
      </Menu>

      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Template</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Template Name"
            fullWidth
            variant="outlined"
            value={newTemplate.name}
            onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            value={newTemplate.description}
            onChange={(e) => setNewTemplate({ ...newTemplate, description: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateTemplate}
            variant="contained"
            disabled={!newTemplate.name.trim()}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Te