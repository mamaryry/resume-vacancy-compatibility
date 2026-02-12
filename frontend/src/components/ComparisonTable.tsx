import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  Stack,
  Button,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Cancel as CrossIcon,
  Refresh as RefreshIcon,
  Person as PersonIcon,
} from '@mui/icons-material';

/**
 * Интерфейс отдельного совпадения навыка
 */
interface SkillMatch {
  skill: string;
  matched: boolean;
  highlight: 'green' | 'red';
}

/**
 * Интерфейс подтверждения опыта
 */
interface ExperienceVerification {
  skill: string;
  total_months: number;
  required_months: number;
  meets_requirement: boolean;
  projects: Array<{
    company: string;
    position: string;
    start_date: string;
    end_date: string | null;
    months: number;
  }>;
}

/**
 * Результат сравнения отдельного резюме
 */
interface ResumeComparisonResult {
  resume_id: string;
  match_percentage: number;
  matched_skills: SkillMatch[];
  missing_skills: SkillMatch[];
  experience_verification?: ExperienceVerification[];
  overall_match: boolean;
}

/**
 * Структура данных таблицы сравнения из backend
 */
interface ComparisonTableData {
  vacancy_id: string;
  comparisons: ResumeComparisonResult[];
  all_unique_skills: string[];
  processing_time?: number;
}

/**
 * Свойства компонента ComparisonTable
 */
interface ComparisonTableProps {
  /** Массив ID резюме для сравнения */
  resumeIds: string[];
  /** ID вакансии для сравнения */
  vacancyId: string;
  /** URL-адрес конечной точки API для получения результатов сравнения */
  apiUrl?: string;
}

/**
 * Компонент ComparisonTable
 *
 * Отображает сравнение нескольких резюме (2-5) в табличном формате:
 * - Процент совпадения для каждого резюме
 * - Матрица навыков, показывающая, какие кандидаты обладают какими навыками
 * - Визуальная подсветка (зеленый=есть навык, красный=отсутствует)
 * - Сводки подтверждения опыта
 * - Ранжирование по проценту совпадения
 *
 * @example
 * ```tsx
 * <ComparisonTable
 *   resumeIds={['resume-1', 'resume-2', 'resume-3']}
 *   vacancyId="vacancy-123"
 * />
 * ```
 */
const ComparisonTable: React.FC<ComparisonTableProps> = ({
  resumeIds,
  vacancyId,
  apiUrl = 'http://localhost:8000/api/comparisons',
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ComparisonTableData | null>(null);

  /**
   * Получить данные сравнения из backend
   */
  const fetchComparison = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/compare-multiple`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          vacancy_id: vacancyId,
          resume_ids: resumeIds,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch comparison: ${response.statusText}`);
      }

      const result: ComparisonTableData = await response.json();
      setData(result);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to load comparison data';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (resumeIds && resumeIds.length >= 2 && resumeIds.length <= 5 && vacancyId) {
      fetchComparison();
    } else if (resumeIds.length < 2) {
      setError('At least 2 resumes are required for comparison');
      setLoading(false);
    } else if (resumeIds.length > 5) {
      setError('Maximum 5 resumes can be compared at once');
      setLoading(false);
    }
  }, [resumeIds, vacancyId]);

  /**
   * Проверить, есть ли у резюме определенный навык
   */
  const hasSkill = (comparison: ResumeComparisonResult, skill: string): boolean => {
    return comparison.matched_skills.some((s) => s.skill === skill);
  };

  /**
   * Получить цвет и метку процента совпадения
   */
  const getMatchConfig = (percentage: number) => {
    if (percentage >= 70) {
      return {
        color: 'success' as const,
        label: 'Excellent',
        bgColor: 'success.main',
        textColor: 'success.contrastText',
      };
    }
    if (percentage >= 40) {
      return {
        color: 'warning' as const,
        label: 'Moderate',
        bgColor: 'warning.main',
        textColor: 'warning.contrastText',
      };
    }
    return {
      color: 'error' as const,
      label: 'Poor',
      bgColor: 'error.main',
      textColor: 'error.contrastText',
    };
  };

  /**
   * Отобразить состояние загрузки
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
          Comparing resumes...
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Analyzing {resumeIds.length} resumes against vacancy requirements
        </Typography>
      </Box>
    );
  }

  /**
   * Отобразить состояние ошибки
   */
  if (error) {
    return (
      <Alert
        severity="error"
        action={
          <Button color="inherit" onClick={fetchComparison} startIcon={<RefreshIcon />}>
            Retry
          </Button>
        }
      >
        <Typography variant="subtitle1" fontWeight={600}>
          Comparison Failed
        </Typography>
        <Typography variant="body2">{error}</Typography>
      </Alert>
    );
  }

  /**
   * Отобразить состояние отсутствия данных
   */
  if (!data || !data.comparisons || data.comparisons.length === 0) {
    return (
      <Alert severity="info">
        <Typography variant="subtitle1" fontWeight={600}>
          No Comparison Data
        </Typography>
        <Typography variant="body2">
          No comparison data found for the selected resumes and vacancy.
        </Typography>
      </Alert>
    );
  }

  // Сортировать сравнения по проценту совпадения (по убыванию)
  const sortedComparisons = [...data.comparisons].sort(
    (a, b) => b.match_percentage - a.match_percentage
  );

  return (
    <Stack spacing={3}>
      {/* Раздел заголовка */}
      <Paper elevation={2} sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box>
            <Typography variant="h5" fontWeight={600}>
              Resume Comparison Matrix
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Vacancy: <strong>{vacancyId}</strong> • Comparing <strong>{resumeIds.length}</strong> resumes
            </Typography>
          </Box>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchComparison} size="small">
            Refresh
          </Button>
        </Box>

        {/* Обзор ранжирования */}
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mt: 2 }}>
          {sortedComparisons.map((comparison, index) => {
            const matchConfig = getMatchConfig(comparison.match_percentage);
            return (
              <Box
                key={comparison.resume_id}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  bgcolor: `${matchConfig.color}.50`,
                  px: 2,
                  py: 1,
                  borderRadius: 2,
                  border: `1px solid ${matchConfig.color}.main`,
                }}
              >
                <Typography variant="h6" fontWeight={700} color={`${matchConfig.color}.main`}>
                  #{index + 1}
                </Typography>
                <Box>
                  <Typography variant="body2" fontWeight={600}>
                    {comparison.resume_id}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {comparison.match_percentage.toFixed(0)}% • {matchConfig.label}
                  </Typography>
                </Box>
              </Box>
            );
          })}
        </Box>
      </Paper>

      {/* Таблица сравнения навыков */}
      <Paper elevation={1} sx={{ p: 3 }}>
        <Typography variant="h6" fontWeight={600} gutterBottom>
          Skills Matrix
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Showing which candidates have the required skills for this vacancy
        </Typography>

        <TableContainer sx={{ maxHeight: 600, overflow: 'auto' }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell
                  sx={{
                    fontWeight: 700,
                    bgcolor: 'grey.100',
                    minWidth: 150,
                    position: 'sticky',
                    left: 0,
                    zIndex: 3,
                  }}
                >
                  Skill
                </TableCell>
                {sortedComparisons.map((comparison) => (
                  <TableCell
                    key={comparison.resume_id}
                    align="center"
                    sx={{
                      fontWeight: 700,
                      bgcolor: 'grey.100',
                      minWidth: 120,
                    }}
                  >
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <Typography variant="body2" fontWeight={600}>
                        {comparison.resume_id}
                      </Typography>
                      <Chip
                        label={`${comparison.match_percentage.toFixed(0)}%`}
                        size="small"
                        color={getMatchConfig(comparison.match_percentage).color}
                        sx={{ mt: 0.5, fontWeight: 700 }}
                      />
                    </Box>
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {data.all_unique_skills.map((skill) => (
                <TableRow
                  key={skill}
                  sx={{ '&:nth-of-type(odd)': { bgcolor: 'action.hover' } }}
                >
                  <TableCell
                    sx={{
                      fontWeight: 600,
                      position: 'sticky',
                      left: 0,
                      bgcolor: 'background.paper',
                      zIndex: 2,
                    }}
                  >
                    {skill}
                  </TableCell>
                  {sortedComparisons.map((comparison) => {
                    const skillMatch = hasSkill(comparison, skill);
                    return (
                      <TableCell key={`${comparison.resume_id}-${skill}`} align="center">
                        {skillMatch ? (
                          <CheckIcon color="success" sx={{ fontSize: 28 }} />
                        ) : (
                          <CrossIcon color="error" sx={{ fontSize: 28 }} />
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Сводка об опыте */}
      <Paper elevation={1} sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <PersonIcon sx={{ mr: 1, fontSize: 28, color: 'primary.main' }} />
          <Typography variant="h6" fontWeight={600}>
            Experience Summary
          </Typography>
        </Box>

        <Stack spacing={2}>
          {sortedComparisons.map((comparison) => {
            const matchConfig = getMatchConfig(comparison.match_percentage);
            return (
              <Box
                key={comparison.resume_id}
                sx={{
                  p: 2,
                  borderRadius: 2,
                  border: `1px solid ${matchConfig.color}.main`,
                  bgcolor: `${matchConfig.color}.50`,
                }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    {comparison.resume_id}
                  </Typography>
                  <Chip
                    label={`${comparison.match_percentage.toFixed(0)}% Совпадение`}
                    color={matchConfig.color}
                    size="small"
                    sx={{ fontWeight: 600 }}
                  />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Найденные навыки: <strong>{comparison.matched_skills.length}</strong> •
                  Отсутствующие навыки: <strong>{comparison.missing_skills.length}</strong>
                </Typography>
                {comparison.experience_verification && comparison.experience_verification.length > 0 && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Опыт подтверждён для {comparison.experience_verification.length} навыка
                      {comparison.experience_verification.length !== 1 ? 'ов' : ''}
                    </Typography>
                  </Box>
                )}
              </Box>
            );
          })}
        </Stack>
      </Paper>

      {/* Время обработки */}
      {data.processing_time && (
        <Typography variant="caption" color="text.secondary" align="center" display="block">
          Сравнение завершено за {data.processing_time.toFixed(2)} секунд
        </Typography>
      )}
    </Stack>
  );
};

export default ComparisonTable;
