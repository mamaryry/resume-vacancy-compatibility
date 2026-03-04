import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress,
  IconButton,
  Alert,
  AlertTitle,
  Stack,
  Divider,
  Grid,
  Card,
  CardContent,
  Chip,
  FormControlLabel,
  Switch,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Close as CloseIcon,
  Save as SaveIcon,
  FolderOpen as OpenIcon,
  ArrowUpward as UpIcon,
  ArrowDownward as DownIcon,
  ChevronRight as RightIcon,
  Remove as RemoveIcon,
  Description as ReportIcon,
} from '@mui/icons-material';

/**
 * Определение доступной метрики
 */
interface AvailableMetric {
  id: string;
  name: string;
  description: string;
  category: 'pipeline' | 'performance' | 'sourcing' | 'skills';
}

/**
 * Выбранная метрика в отчете
 */
interface SelectedMetric {
  id: string;
  name: string;
  description: string;
  category: string;
}

/**
 * Данные конфигурации отчета
 */
interface ReportData {
  metrics: string[];
  filters: Record<string, string | boolean | number>;
}

/**
 * Отчет из бэкенда
 */
interface Report {
  id: string;
  organization_id: string;
  name: string;
  description?: string;
  created_by?: string;
  metrics: string[];
  filters: Record<string, string | boolean | number>;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Ответ списка из бэкенда
 */
interface ReportListResponse {
  organization_id?: string;
  reports: Report[];
  total_count: number;
}

/**
 * Данные формы для создания/редактирования отчетов
 */
interface ReportFormData {
  name: string;
  description: string;
  is_public: boolean;
}

/**
 * Свойства компонента ReportBuilder
 */
interface ReportBuilderProps {
  /** ID организации для отчетов */
  organizationId?: string;
  /** URL API конечной точки для отчетов */
  apiUrl?: string;
  /** Обратный вызов при создании/обновлении отчета */
  onReportChange?: (report: Report) => void;
}

/**
 * Компонент ReportBuilder
 *
 * Предоставляет интерфейс перетаскивания для создания пользовательских аналитических отчетов.
 * Функции включают:
 * - Просмотр и выбор доступных метрик
 * - Перетаскивание для изменения порядка выбранных метрик
 * - Сохранение и загрузку пользовательских отчетов
 * - Редактирование и удаление существующих отчетов
 * - Предварительный просмотр конфигурации отчета в реальном времени
 *
 * @example
 * ```tsx
 * <ReportBuilder organizationId="org123" />
 * ```
 */
const ReportBuilder: React.FC<ReportBuilderProps> = ({
  organizationId = 'default-org',
  apiUrl = 'http://localhost:8000/api/reports',
  onReportChange,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedMetrics, setSelectedMetrics] = useState<SelectedMetric[]>([]);
  const [availableMetrics] = useState<AvailableMetric[]>([
    {
      id: 'time_to_hire',
      name: 'Time to Hire',
      description: 'Average, median, and distribution of hiring time',
      category: 'pipeline',
    },
    {
      id: 'resumes_processed',
      name: 'Resumes Processed',
      description: 'Total resumes processed and processing rate',
      category: 'pipeline',
    },
    {
      id: 'match_rates',
      name: 'Match Rates',
      description: 'Overall and confidence-based match statistics',
      category: 'performance',
    },
    {
      id: 'funnel_data',
      name: 'Funnel Visualization',
      description: 'Candidate progression through pipeline stages',
      category: 'pipeline',
    },
    {
      id: 'skill_demand',
      name: 'Skill Demand',
      description: 'Most requested skills and trending technologies',
      category: 'skills',
    },
    {
      id: 'source_tracking',
      name: 'Source Tracking',
      description: 'Vacancy and hire distribution by source',
      category: 'sourcing',
    },
    {
      id: 'recruiter_performance',
      name: 'Recruiter Performance',
      description: 'Individual recruiter metrics and comparisons',
      category: 'performance',
    },
    {
      id: 'interviews_scheduled',
      name: 'Interviews Scheduled',
      description: 'Interview scheduling statistics and trends',
      category: 'pipeline',
    },
    {
      id: 'offers_extended',
      name: 'Offers Extended',
      description: 'Offer statistics and acceptance rates',
      category: 'pipeline',
    },
    {
      id: 'offers_accepted',
      name: 'Offers Accepted',
      description: 'Accepted offers and time to acceptance',
      category: 'pipeline',
    },
  ]);

  // Состояния диалогов
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [reportToDelete, setReportToDelete] = useState<Report | null>(null);
  const [editingReport, setEditingReport] = useState<Report | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Состояние формы
  const [formData, setFormData] = useState<ReportFormData>({
    name: '',
    description: '',
    is_public: false,
  });

  // Состояние перетаскивания
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  /**
   * Получение сохраненных отчетов из бэкенда
   */
  const fetchReports = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/?organization_id=${organizationId}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch reports: ${response.statusText}`);
      }

      const result: ReportListResponse = await response.json();
      setReports(result.reports || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load reports';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [organizationId]);

  /**
   * Добавление метрики в список выбранных
   */
  const handleAddMetric = (metric: AvailableMetric) => {
    if (selectedMetrics.find((m) => m.id === metric.id)) {
      return; // Уже выбрано
    }
    setSelectedMetrics([
      ...selectedMetrics,
      {
        id: metric.id,
        name: metric.name,
        description: metric.description,
        category: metric.category,
      },
    ]);
  };

  /**
   * Удаление метрики из списка выбранных
   */
  const handleRemoveMetric = (metricId: string) => {
    setSelectedMetrics(selectedMetrics.filter((m) => m.id !== metricId));
  };

  /**
   * Перемещение метрики вверх в списке выбранных
   */
  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const newMetrics = [...selectedMetrics];
    const temp = newMetrics[index];
    newMetrics[index] = newMetrics[index - 1]!;
    newMetrics[index - 1] = temp!;
    setSelectedMetrics(newMetrics);
  };

  /**
   * Перемещение метрики вниз в списке выбранных
   */
  const handleMoveDown = (index: number) => {
    if (index === selectedMetrics.length - 1) return;
    const newMetrics = [...selectedMetrics];
    const temp = newMetrics[index];
    newMetrics[index] = newMetrics[index + 1]!;
    newMetrics[index + 1] = temp!;
    setSelectedMetrics(newMetrics);
  };

  /**
   * Обработчик начала перетаскивания
   */
  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  /**
   * Обработчик перетаскивания над элементом
   */
  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;

    const newMetrics = [...selectedMetrics];
    const draggedItem = newMetrics[draggedIndex];
    if (!draggedItem) return;
    newMetrics.splice(draggedIndex, 1);
    newMetrics.splice(index, 0, draggedItem);
    setSelectedMetrics(newMetrics);
    setDraggedIndex(index);
  };

  /**
   * Обработчик окончания перетаскивания
   */
  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  /**
   * Открытие диалога сохранения
   */
  const handleSaveClick = () => {
    if (selectedMetrics.length === 0) {
      setError('Please select at least one metric before saving');
      return;
    }
    setEditingReport(null);
    setFormData({
      name: '',
      description: '',
      is_public: false,
    });
    setSaveDialogOpen(true);
    setError(null);
  };

  /**
   * Открытие диалога загрузки
   */
  const handleLoadClick = () => {
    setLoadDialogOpen(true);
  };

  /**
   * Загрузка отчета
   */
  const handleLoadReport = (report: Report) => {
    const loadedMetrics = report.metrics
      .map((metricId) => availableMetrics.find((m) => m.id === metricId))
      .filter((m): m is AvailableMetric => m !== undefined)
      .map((m) => ({
        id: m.id,
        name: m.name,
        description: m.description,
        category: m.category,
      }));

    setSelectedMetrics(loadedMetrics);
    setLoadDialogOpen(false);
    setEditingReport(report);
  };

  /**
   * Открытие диалога редактирования для текущего отчета
   */
  const handleEditClick = () => {
    if (!editingReport) {
      setError('No report loaded to edit');
      return;
    }
    setFormData({
      name: editingReport.name,
      description: editingReport.description || '',
      is_public: editingReport.is_public,
    });
    setSaveDialogOpen(true);
  };

  /**
   * Открытие диалога подтверждения удаления
   */
  const handleDeleteClick = () => {
    if (!editingReport) {
      setError('No report loaded to delete');
      return;
    }
    setReportToDelete(editingReport);
    setDeleteDialogOpen(true);
  };

  /**
   * Подтверждение удаления
   */
  const handleDeleteConfirm = async () => {
    if (!reportToDelete) return;

    setSubmitting(true);
    try {
      const response = await fetch(`${apiUrl}/${reportToDelete.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`Failed to delete report: ${response.statusText}`);
      }

      // Оптимистичное обновление
      setReports(reports.filter((r) => r.id !== reportToDelete.id));
      setEditingReport(null);
      setSelectedMetrics([]);
      setDeleteDialogOpen(false);
      setReportToDelete(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete report';
      setError(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  /**
   * Отправка формы (создание или обновление)
   */
  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);

    try {
      const reportData: ReportData = {
        metrics: selectedMetrics.map((m) => m.id),
        filters: {},
      };

      if (editingReport) {
        // Обновление существующего отчета
        const response = await fetch(`${apiUrl}/${editingReport.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: formData.name,
            description: formData.description || null,
            metrics: reportData.metrics,
            filters: reportData.filters,
            is_public: formData.is_public,
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to update report: ${response.statusText}`);
        }

        const updated: Report = await response.json();
        setReports(reports.map((r) => (r.id === updated.id ? updated : r)));
        setEditingReport(updated);

        if (onReportChange) {
          onReportChange(updated);
        }
      } else {
        // Создание нового отчета
        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: formData.name,
            description: formData.description || null,
            organization_id: organizationId,
            created_by: 'current-user',
            metrics: reportData.metrics,
            filters: reportData.filters,
            is_public: formData.is_public,
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to create report: ${response.statusText}`);
        }

        const created: Report = await response.json();
        setReports([...reports, created]);
        setEditingReport(created);

        if (onReportChange) {
          onReportChange(created);
        }
      }

      setSaveDialogOpen(false);
      setFormData({
        name: '',
        description: '',
        is_public: false,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save report';
      setError(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  /**
   * Получение цвета категории
   */
  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'pipeline':
        return 'primary' as const;
      case 'performance':
        return 'success' as const;
      case 'sourcing':
        return 'info' as const;
      case 'skills':
        return 'warning' as const;
      default:
        return 'default' as const;
    }
  };

  /**
   * Отображение состояния загрузки
   */
  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          py: 8,
        }}
      >
        <CircularProgress size={60} sx={{ mb: 3 }} />
        <Typography variant="h6" color="text.secondary">
          Loading Report Builder...
        </Typography>
      </Box>
    );
  }

  /**
   * Отображение состояния ошибки
   */
  if (error && reports.length === 0) {
    return (
      <Alert
        severity="error"
        action={
          <Button color="inherit" onClick={fetchReports} startIcon={<RefreshIcon />}>
            Retry
          </Button>
        }
      >
        <AlertTitle>Error Loading Reports</AlertTitle>
        {error}
      </Alert>
    );
  }

  return (
    <Stack spacing={3}>
      {/* Секция заголовка */}
      <Paper elevation={2} sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <ReportIcon color="primary" sx={{ fontSize: 32 }} />
            <Typography variant="h5" fontWeight={600}>
              Custom Report Builder
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchReports} size="small">
              Refresh
            </Button>
          </Box>
        </Box>

        <Typography variant="body2" color="text.secondary" paragraph>
          Build custom reports by selecting and ordering metrics. Drag metrics to reorder them in your report.
        </Typography>

        {/* Кнопки действий */}
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSaveClick}
            disabled={selectedMetrics.length === 0}
          >
            Save Report
          </Button>
          <Button variant="outlined" startIcon={<OpenIcon />} onClick={handleLoadClick}>
            Load Report
          </Button>
          {editingReport && (
            <>
              <Button variant="outlined" startIcon={<EditIcon />} onClick={handleEditClick}>
                Edit Report
              </Button>
              <Button
                variant="outlined"
                color="error"
                startIcon={<DeleteIcon />}
                onClick={handleDeleteClick}
              >
                Delete Report
              </Button>
            </>
          )}
        </Box>

        {editingReport && (
          <Alert severity="info" sx={{ mt: 2 }}>
            <AlertTitle>Current Report: {editingReport.name}</AlertTitle>
            {editingReport.description || 'No description'}
          </Alert>
        )}
      </Paper>

      {/* Предупреждение об ошибке */}
      {error && selectedMetrics.length > 0 && (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Выбор метрик */}
      <Grid container spacing={3}>
        {/* Доступные метрики */}
        <Grid item xs={12} md={6}>
          <Paper elevation={1} sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom fontWeight={600}>
              Available Metrics
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
              Click to add metrics to your report
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Stack spacing={1}>
              {availableMetrics.map((metric) => {
                const isSelected = selectedMetrics.find((m) => m.id === metric.id);
                return (
                  <Card
                    key={metric.id}
                    variant="outlined"
                    sx={{
                      cursor: isSelected ? 'default' : 'pointer',
                      opacity: isSelected ? 0.5 : 1,
                      '&:hover': !isSelected ? { boxShadow: 3 } : {},
                      transition: 'all 0.2s',
                    }}
                    onClick={() => !isSelected && handleAddMetric(metric)}
                  >
                    <CardContent sx={{ py: 1.5, px: 2, '&:last-child': { pb: 1.5 } }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Box sx={{ flex: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                            <Typography variant="subtitle2" fontWeight={600}>
                              {metric.name}
                            </Typography>
                            <Chip
                              label={metric.category}
                              size="small"
                              color={getCategoryColor(metric.category)}
                              variant="filled"
                              sx={{ height: 20, fontSize: '0.7rem', '& .MuiChip-label': { px: 0.5 } }}
                            />
                          </Box>
                          <Typography variant="caption" color="text.secondary">
                            {metric.description}
                          </Typography>
                        </Box>
                        {!isSelected && <RightIcon color="action" fontSize="small" />}
                        {isSelected && (
                          <Chip label="Added" size="small" color="success" variant="filled" />
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                );
              })}
            </Stack>
          </Paper>
        </Grid>

        {/* Выбранные метрики */}
        <Grid item xs={12} md={6}>
          <Paper elevation={1} sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom fontWeight={600}>
              Selected Metrics ({selectedMetrics.length})
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
              Drag to reorder or use arrows to move up/down
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Stack spacing={1}>
              {selectedMetrics.length === 0 ? (
                <Box sx={{ py: 4, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    No metrics selected. Click on available metrics to add them to your report.
                  </Typography>
                </Box>
              ) : (
                selectedMetrics.map((metric, index) => (
                  <Card
                    key={metric.id}
                    variant="outlined"
                    draggable
                    onDragStart={() => handleDragStart(index)}
                    onDragOver={(e) => handleDragOver(e, index)}
                    onDragEnd={handleDragEnd}
                    sx={{
                      cursor: 'grab',
                      border: draggedIndex === index ? '2px solid primary.main' : undefined,
                      '&:active': { cursor: 'grabbing' },
                      '&:hover': { boxShadow: 2 },
                      transition: 'all 0.2s',
                    }}
                  >
                    <CardContent sx={{ py: 1.5, px: 2, '&:last-child': { pb: 1.5 } }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
                          <Typography
                            variant="body2"
                            fontWeight={600}
                            sx={{ minWidth: 24, textAlign: 'center', color: 'text.secondary' }}
                          >
                            {index + 1}.
                          </Typography>
                          <Box sx={{ flex: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                              <Typography variant="subtitle2" fontWeight={600}>
                                {metric.name}
                              </Typography>
                              <Chip
                                label={metric.category}
                                size="small"
                                color={getCategoryColor(metric.category)}
                                variant="filled"
                                sx={{ height: 20, fontSize: '0.7rem', '& .MuiChip-label': { px: 0.5 } }}
                              />
                            </Box>
                            <Typography variant="caption" color="text.secondary">
                              {metric.description}
                            </Typography>
                          </Box>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <IconButton
                            size="small"
                            onClick={() => handleMoveUp(index)}
                            disabled={index === 0}
                            title="Move up"
                          >
                            <UpIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleMoveDown(index)}
                            disabled={index === selectedMetrics.length - 1}
                            title="Move down"
                          >
                            <DownIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleRemoveMetric(metric.id)}
                            color="error"
                            title="Remove"
                          >
                            <RemoveIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                ))
              )}
            </Stack>
          </Paper>
        </Grid>
      </Grid>

      {/* Диалог сохранения/редактирования */}
      <Dialog
        open={saveDialogOpen}
        onClose={() => !submitting && setSaveDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">
              {editingReport ? 'Edit Report' : 'Save New Report'}
            </Typography>
            <IconButton
              onClick={() => setSaveDialogOpen(false)}
              disabled={submitting}
              size="small"
            >
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <TextField
              label="Report Name"
              fullWidth
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Monthly Hiring Report"
              disabled={submitting}
            />

            <TextField
              label="Description (Optional)"
              fullWidth
              multiline
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Brief description of this report..."
              disabled={submitting}
            />

            <FormControlLabel
              control={
                <Switch
                  checked={formData.is_public}
                  onChange={(e) => setFormData({ ...formData, is_public: e.target.checked })}
                  disabled={submitting}
                />
              }
              label="Make this report visible to all organization members"
            />

            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Selected Metrics ({selectedMetrics.length}):
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {selectedMetrics.map((metric) => (
                  <Chip
                    key={metric.id}
                    label={metric.name}
                    size="small"
                    color={getCategoryColor(metric.category)}
                    variant="filled"
                  />
                ))}
              </Box>
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveDialogOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            disabled={submitting || !formData.name}
            startIcon={submitting ? <CircularProgress size={16} /> : <SaveIcon />}
          >
            {submitting ? 'Saving...' : editingReport ? 'Update' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Диалог загрузки отчета */}
      <Dialog
        open={loadDialogOpen}
        onClose={() => setLoadDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Load Saved Report</Typography>
            <IconButton onClick={() => setLoadDialogOpen(false)} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          {reports.length === 0 ? (
            <Box sx={{ py: 4, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                No saved reports found. Create your first report to get started.
              </Typography>
            </Box>
          ) : (
            <Stack spacing={2} sx={{ mt: 1 }}>
              {reports.map((report) => (
                <Card
                  key={report.id}
                  variant="outlined"
                  sx={{
                    cursor: 'pointer',
                    '&:hover': { boxShadow: 3, borderColor: 'primary.main' },
                    transition: 'all 0.2s',
                  }}
                  onClick={() => handleLoadReport(report)}
                >
                  <CardContent sx={{ py: 2, px: 2, '&:last-child': { pb: 2 } }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Box sx={{ flex: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Typography variant="subtitle1" fontWeight={600}>
                            {report.name}
                          </Typography>
                          {report.is_public && (
                            <Chip label="Public" size="small" color="primary" variant="filled" />
                          )}
                        </Box>
                        {report.description && (
                          <Typography variant="body2" color="text.secondary" paragraph>
                            {report.description}
                          </Typography>
                        )}
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {report.metrics.slice(0, 5).map((metricId) => {
                            const metric = availableMetrics.find((m) => m.id === metricId);
                            return metric ? (
                              <Chip
                                key={metricId}
                                label={metric.name}
                                size="small"
                                variant="outlined"
                                sx={{ fontSize: '0.75rem', height: 24 }}
                              />
                            ) : null;
                          })}
                          {report.metrics.length > 5 && (
                            <Chip
                              label={`+${report.metrics.length - 5} more`}
                              size="small"
                              variant="outlined"
                              sx={{ fontSize: '0.75rem', height: 24 }}
                            />
                          )}
                        </Box>
                      </Box>
                      <OpenIcon color="action" />
                    </Box>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                      Created: {new Date(report.created_at).toLocaleDateString()}
                    </Typography>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLoadDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Диалог подтверждения удаления */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography variant="body1">
            Are you sure you want to delete the report <strong>"{reportToDelete?.name}"</strong>?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            variant="contained"
            color="error"
            disabled={submitting}
            startIcon={submitting ? <CircularProgress size={16} /> : <DeleteIcon />}
          >
            {submitting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
};

export default ReportBuilder;
