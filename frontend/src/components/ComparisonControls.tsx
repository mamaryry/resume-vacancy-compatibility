import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Slider,
  FormControl,
  InputLabel,
  Select,
  SelectChangeEvent,
  MenuItem,
  Chip,
  Stack,
  Divider,
  Alert,
} from '@mui/material';
import {
  FilterList as FilterIcon,
  Sort as SortIcon,
  Add as AddIcon,
  Remove as RemoveIcon,
  RestartAlt as ResetIcon,
  Save as SaveIcon,
  Share as ShareIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';

/**
 * Интерфейс настроек фильтров
 */
interface ComparisonFilters {
  min_match_percentage: number;
  max_match_percentage: number;
}

/**
 * Интерфейс настроек сортировки
 */
interface ComparisonSort {
  field: 'created_at' | 'match_percentage' | 'name' | 'updated_at';
  order: 'asc' | 'desc';
}

/**
 * Интерфейс отдельного совпадения навыка
 */
interface SkillMatch {
  skill: string;
  matched: boolean;
  highlight: 'green' | 'red';
}

/**
 * Результат сравнения отдельного резюме
 */
interface ResumeComparisonResult {
  resume_id: string;
  match_percentage: number;
  matched_skills: SkillMatch[];
  missing_skills: SkillMatch[];
  experience_verification?: Array<{
    skill: string;
    total_months: number;
    required_months: number;
    meets_requirement: boolean;
  }>;
  overall_match: boolean;
}

/**
 * Интерфейс данных сравнения
 */
interface ComparisonData {
  vacancy_id: string;
  comparisons: ResumeComparisonResult[];
  all_unique_skills: string[];
}

/**
 * Свойства компонента ComparisonControls
 */
interface ComparisonControlsProps {
  /** Массив ID резюме, которые сейчас сравниваются */
  resumeIds: string[];
  /** Callback при изменении ID резюме */
  onResumeIdsChange?: (resumeIds: string[]) => void;
  /** Callback при изменении фильтров */
  onFiltersChange?: (filters: ComparisonFilters) => void;
  /** Callback при изменении настроек сортировки */
  onSortChange?: (sort: ComparisonSort) => void;
  /** Callback при нажатии кнопки сохранения */
  onSave?: () => void;
  /** Callback при нажатии кнопки поделиться */
  onShare?: () => void;
  /** Callback при нажатии кнопки экспорта */
  onExport?: () => void;
  /** Данные сравнения для экспорта */
  comparisonData?: ComparisonData | null;
  /** Initial filter values */
  initialFilters?: ComparisonFilters;
  /** Initial sort values */
  initialSort?: ComparisonSort;
  /** Maximum number of resumes allowed */
  maxResumes?: number;
  /** Minimum number of resumes required */
  minResumes?: number;
  /** Show save/share buttons */
  showSaveActions?: boolean;
  /** Show export button */
  showExport?: boolean;
  /** Disabled state */
  disabled?: boolean;
}

/**
 * Компонент ComparisonControls
 *
 * Обеспечивает элементы управления для сравнения резюме:
 * - Добавление/удаление резюме из сравнения
 * - Фильтрация по диапазону процента совпадения
 * - Сортировка по различным полям и порядкам
 * - Экспорт данных сравнения в Excel (формат CSV)
 * - Сохранение и совместное использование представлений сравнения
 * - Сброс к значениям по умолчанию
 *
 * @example
 * ```tsx
 * <ComparisonControls
 *   resumeIds={['resume-1', 'resume-2']}
 *   onResumeIdsChange={(ids) => console.log('ID резюме:', ids)}
 *   onFiltersChange={(filters) => console.log('Фильтры:', filters)}
 *   onSortChange={(sort) => console.log('Сортировка:', sort)}
 *   comparisonData={comparisonData}
 *   onExport={() => console.log('Экспорт нажат')}
 * />
 * ```
 */
const ComparisonControls: React.FC<ComparisonControlsProps> = ({
  resumeIds,
  onResumeIdsChange,
  onFiltersChange,
  onSortChange,
  onSave,
  onShare,
  onExport,
  comparisonData,
  initialFilters = { min_match_percentage: 0, max_match_percentage: 100 },
  initialSort = { field: 'match_percentage', order: 'desc' },
  maxResumes = 5,
  minResumes = 2,
  showSaveActions = true,
  showExport = true,
  disabled = false,
}) => {
  const [filters, setFilters] = useState<ComparisonFilters>(initialFilters);
  const [sort, setSort] = useState<ComparisonSort>(initialSort);
  const [newResumeId, setNewResumeId] = useState('');

  /**
   * Обработать изменение фильтра
   */
  const handleFilterChange = useCallback(
    (field: keyof ComparisonFilters, value: number) => {
      const newFilters = { ...filters, [field]: value };

      // Убедиться, что минимум не превышает максимум
      if (field === 'min_match_percentage' && value > newFilters.max_match_percentage) {
        newFilters.max_match_percentage = value;
      } else if (field === 'max_match_percentage' && value < newFilters.min_match_percentage) {
        newFilters.min_match_percentage = value;
      }

      setFilters(newFilters);
      onFiltersChange?.(newFilters);
    },
    [filters, onFiltersChange]
  );

  /**
   * Обработать изменение поля сортировки
   */
  const handleSortFieldChange = useCallback(
    (event: SelectChangeEvent<ComparisonSort['field']>) => {
      const field = event.target.value as ComparisonSort['field'];
      const newSort = { ...sort, field };
      setSort(newSort);
      onSortChange?.(newSort);
    },
    [sort, onSortChange]
  );

  /**
   * Обработать изменение порядка сортировки
   */
  const handleSortOrderChange = useCallback(
    (event: SelectChangeEvent<ComparisonSort['order']>) => {
      const order = event.target.value as ComparisonSort['order'];
      const newSort = { ...sort, order };
      setSort(newSort);
      onSortChange?.(newSort);
    },
    [sort, onSortChange]
  );

  /**
   * Обработать добавление резюме
   */
  const handleAddResume = useCallback(() => {
    if (!newResumeId.trim()) {
      return;
    }

    if (resumeIds.length >= maxResumes) {
      return;
    }

    if (resumeIds.includes(newResumeId.trim())) {
      return;
    }

    const updatedIds = [...resumeIds, newResumeId.trim()];
    onResumeIdsChange?.(updatedIds);
    setNewResumeId('');
  }, [newResumeId, resumeIds, maxResumes, onResumeIdsChange]);

  /**
   * Обработать удаление резюме
   */
  const handleRemoveResume = useCallback(
    (resumeId: string) => {
      const updatedIds = resumeIds.filter((id) => id !== resumeId);
      onResumeIdsChange?.(updatedIds);
    },
    [resumeIds, onResumeIdsChange]
  );

  /**
   * Обработать сброс элементов управления
   */
  const handleReset = useCallback(() => {
    const defaultFilters: ComparisonFilters = {
      min_match_percentage: 0,
      max_match_percentage: 100,
    };
    const defaultSort: ComparisonSort = {
      field: 'match_percentage',
      order: 'desc',
    };

    setFilters(defaultFilters);
    setSort(defaultSort);
    setNewResumeId('');

    onFiltersChange?.(defaultFilters);
    onSortChange?.(defaultSort);
  }, [onFiltersChange, onSortChange]);

  /**
   * Обработать сохранение сравнения
   */
  const handleSave = useCallback(() => {
    onSave?.();
  }, [onSave]);

  /**
   * Обработать общий доступ к сравнению
   */
  const handleShare = useCallback(() => {
    onShare?.();
  }, [onShare]);

  /**
   * Обработать экспорт в Excel (формат CSV)
   */
  const handleExport = useCallback(() => {
    // Если предоставлен пользовательский обработчик экспорта, использовать его
    if (onExport) {
      onExport();
      return;
    }

    // Реализация экспорта по умолчанию с использованием данных сравнения
    if (!comparisonData || !comparisonData.comparisons || comparisonData.comparisons.length === 0) {
      return;
    }

    try {
      // Создать содержимое CSV
      const csvRows: string[] = [];

      // Добавить заголовок с метаданными
      csvRows.push(`Resume Comparison Report,Vacancy ID,${comparisonData.vacancy_id}`);
      csvRows.push(`Generated,${new Date().toLocaleString()}`);
      csvRows.push('');

      // Добавить сводный раздел
      csvRows.push('СВОДКА');
      csvRows.push('Ранг,ID резюме,% совпадения,Найденные навыки,Отсутствующие навыки,Общее совпадение');

      const sortedComparisons = [...comparisonData.comparisons].sort(
        (a, b) => b.match_percentage - a.match_percentage
      );

      sortedComparisons.forEach((comparison, index) => {
        const matchedSkills = comparison.matched_skills.map((s) => s.skill).join('; ');
        const missingSkills = comparison.missing_skills.map((s) => s.skill).join('; ');
        csvRows.push(
          `${index + 1},"${comparison.resume_id}",${comparison.match_percentage.toFixed(1)}%,"${matchedSkills}","${missingSkills}","${comparison.overall_match ? 'Да' : 'Нет'}"`
        );
      });

      csvRows.push('');

      // Добавить матрицу навыков
      csvRows.push('МАТРИЦА НАВЫКОВ');
      const headerRow = ['Навык', ...sortedComparisons.map((c) => `"${c.resume_id} (${c.match_percentage.toFixed(0)}%)"`)];
      csvRows.push(headerRow.join(','));

      comparisonData.all_unique_skills.forEach((skill) => {
        const row = [`"${skill}"`];
        sortedComparisons.forEach((comparison) => {
          const hasSkill = comparison.matched_skills.some((s) => s.skill === skill);
          row.push(hasSkill ? '✓' : '✗');
        });
        csvRows.push(row.join(','));
      });

      csvRows.push('');

      // Добавить подтверждение опыта, если доступно
      const hasExperienceData = sortedComparisons.some(
        (c) => c.experience_verification && c.experience_verification.length > 0
      );

      if (hasExperienceData) {
        csvRows.push('ПОДТВЕРЖДЕНИЕ ОПЫТА');
        csvRows.push('ID резюме,Навык,Требуемые месяцы,Всего месяцев,Соответствует требованиям');

        sortedComparisons.forEach((comparison) => {
          if (comparison.experience_verification && comparison.experience_verification.length > 0) {
            comparison.experience_verification.forEach((exp) => {
              csvRows.push(
                `"${comparison.resume_id}","${exp.skill}",${exp.required_months},${exp.total_months},"${exp.meets_requirement ? 'Да' : 'Нет'}"`
              );
            });
          }
        });
      }

      // Создать blob и скачать
      const csvContent = csvRows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);

      link.setAttribute('href', url);
      link.setAttribute(
        'download',
        `resume-comparison-${comparisonData.vacancy_id}-${new Date().getTime()}.csv`
      );
      link.style.visibility = 'hidden';

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      // Тихая обработка ошибок экспорта
      // В продакшене можно показать всплывающее уведомление
    }
  }, [comparisonData, onExport]);

  /**
   * Обработать нажатие клавиши в поле ввода ID резюме
   */
  const handleKeyPress = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === 'Enter') {
        handleAddResume();
      }
    },
    [handleAddResume]
  );

  // Обновить состояние при изменении props
  useEffect(() => {
    if (initialFilters) {
      setFilters(initialFilters);
    }
  }, [initialFilters]);

  useEffect(() => {
    if (initialSort) {
      setSort(initialSort);
    }
  }, [initialSort]);

  const isValidRange = resumeIds.length >= minResumes && resumeIds.length <= maxResumes;
  const canAddMore = resumeIds.length < maxResumes;

  return (
    <Stack spacing={2}>
      {/* Раздел управления резюме */}
      <Paper elevation={1} sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <FilterIcon sx={{ mr: 1, fontSize: 24, color: 'primary.main' }} />
          <Typography variant="h6" fontWeight={600}>
            Resume Selection
          </Typography>
        </Box>
        <Divider sx={{ mb: 2 }} />

        {/* Информация о количестве резюме */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Selected Resumes: <strong>{resumeIds.length}</strong> / {maxResumes} (minimum {minResumes})
          </Typography>
          {!isValidRange && (
            <Alert severity="warning" sx={{ mt: 1 }}>
              {resumeIds.length < minResumes
                ? `At least ${minResumes} resume${minResumes > 1 ? 's are' : ' is'} required for comparison`
                : `Maximum ${maxResumes} resumes can be compared at once`}
            </Alert>
          )}
        </Box>

        {/* Список резюме */}
        {resumeIds.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Current Resumes:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {resumeIds.map((resumeId) => (
                <Chip
                  key={resumeId}
                  label={resumeId}
                  size="medium"
                  onDelete={!disabled ? () => handleRemoveResume(resumeId) : undefined}
                  color="primary"
                  variant="outlined"
                />
              ))}
            </Box>
          </Box>
        )}

        {/* Поле ввода для добавления резюме */}
        {!disabled && canAddMore && (
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <TextField
              fullWidth
              size="small"
              label="Добавить ID резюме"
              value={newResumeId}
              onChange={(e) => setNewResumeId(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Введите ID резюме..."
              disabled={disabled}
            />
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleAddResume}
              disabled={!newResumeId.trim() || disabled}
            >
              Добавить
            </Button>
          </Box>
        )}
      </Paper>

      {/* Раздел фильтров */}
      <Paper elevation={1} sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <FilterIcon sx={{ mr: 1, fontSize: 24, color: 'primary.main' }} />
          <Typography variant="h6" fontWeight={600}>
            Filters
          </Typography>
        </Box>
        <Divider sx={{ mb: 2 }} />

        {/* Диапазон процента совпадения */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Match Percentage Range: {filters.min_match_percentage}% - {filters.max_match_percentage}%
          </Typography>
          <Box sx={{ px: 1 }}>
            <Slider
              value={[filters.min_match_percentage, filters.max_match_percentage]}
              onChange={(_event, newValue) => {
                const value = newValue as number[];
                if (value[0] !== undefined) handleFilterChange('min_match_percentage', value[0]);
                if (value[1] !== undefined) handleFilterChange('max_match_percentage', value[1]);
              }}
              valueLabelDisplay="auto"
              valueLabelFormat={(value) => `${value}%`}
              min={0}
              max={100}
              step={5}
              marks={[
                { value: 0, label: '0%' },
                { value: 25, label: '25%' },
                { value: 50, label: '50%' },
                { value: 75, label: '75%' },
                { value: 100, label: '100%' },
              ]}
              disabled={disabled}
              sx={{
                '& .MuiSlider-thumb': {
                  '&:hover, &.Mui-focusVisible': {
                    boxShadow: '0 0 0 8px rgba(25, 118, 210, 0.16)',
                  },
                },
              }}
            />
          </Box>
        </Box>
      </Paper>

      {/* Раздел сортировки */}
      <Paper elevation={1} sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <SortIcon sx={{ mr: 1, fontSize: 24, color: 'primary.main' }} />
          <Typography variant="h6" fontWeight={600}>
            Sorting
          </Typography>
        </Box>
        <Divider sx={{ mb: 2 }} />

        <Stack spacing={2} direction={{ xs: 'column', md: 'row' }}>
          {/* Поле сортировки */}
          <FormControl fullWidth size="small" disabled={disabled}>
            <InputLabel>Sort By</InputLabel>
            <Select
              value={sort.field}
              onChange={handleSortFieldChange}
              label="Sort By"
            >
              <MenuItem value="match_percentage">Match Percentage</MenuItem>
              <MenuItem value="created_at">Date Created</MenuItem>
              <MenuItem value="updated_at">Last Updated</MenuItem>
              <MenuItem value="name">Name</MenuItem>
            </Select>
          </FormControl>

          {/* Порядок сортировки */}
          <FormControl fullWidth size="small" disabled={disabled}>
            <InputLabel>Order</InputLabel>
            <Select
              value={sort.order}
              onChange={handleSortOrderChange}
              label="Order"
            >
              <MenuItem value="desc">Descending</MenuItem>
              <MenuItem value="asc">Ascending</MenuItem>
            </Select>
          </FormControl>
        </Stack>

        {/* Индикатор активной сортировки */}
        <Box sx={{ mt: 2 }}>
          <Chip
            label={`Sorted by ${sort.field.replace('_', ' ')} (${sort.order})`}
            size="small"
            color="primary"
            variant="outlined"
          />
        </Box>
      </Paper>

      {/* Раздел действий */}
      <Paper elevation={1} sx={{ p: 3 }}>
        <Stack spacing={2} direction={{ xs: 'column', md: 'row' }}>
          {/* Кнопка сброса */}
          <Button
            fullWidth
            variant="outlined"
            startIcon={<ResetIcon />}
            onClick={handleReset}
            disabled={disabled}
          >
            Reset All
          </Button>

          {/* Кнопка экспорта */}
          {showExport && (
            <Button
              fullWidth
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={handleExport}
              disabled={disabled || !isValidRange || (!comparisonData && !onExport)}
              color="info"
            >
              Export to Excel
            </Button>
          )}

          {/* Кнопка сохранения */}
          {showSaveActions && onSave && (
            <Button
              fullWidth
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSave}
              disabled={disabled || !isValidRange}
              color="primary"
            >
              Save Comparison
            </Button>
          )}

          {/* Кнопка общего доступа */}
          {showSaveActions && onShare && (
            <Button
              fullWidth
              variant="contained"
              startIcon={<ShareIcon />}
              onClick={handleShare}
              disabled={disabled || !isValidRange}
              color="secondary"
            >
              Share
            </Button>
          )}
        </Stack>
      </Paper>

      {/* Информационное предупреждение */}
      <Alert severity="info" variant="outlined">
        <Typography variant="body2">
          <strong>Tip:</strong> Select {minResumes}-{maxResumes} resumes to compare side-by-side. Use filters
          to narrow down results and sorting to rank candidates.
        </Typography>
      </Alert>
    </Stack>
  );
};

export default ComparisonControls;
