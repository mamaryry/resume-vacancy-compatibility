import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useLanguageContext } from '@/contexts/LanguageContext';
import { formatNumber } from '@/utils/localeFormatters';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Alert,
  AlertTitle,
  Stack,
  Divider,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  CircularProgress,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  CheckCircle as CheckIcon,
  Cancel as CrossIcon,
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import CandidateMatchVisualization from '@components/CandidateMatchVisualization';

/**
 * Интерфейс ошибки/проблемы из backend-анализа
 */
interface AnalysisError {
  type: string;
  severity: 'critical' | 'warning' | 'info';
  message: string;
  recommendation?: string;
  category?: string;
}

/**
 * Интерфейс грамматической ошибки
 */
interface GrammarError {
  type: string;
  severity: 'error' | 'warning';
  message: string;
  context: string;
  suggestions: string[];
  position: {
    start: number;
    end: number;
  };
}

/**
 * Интерфейс совпадения навыка для подсветки
 */
interface SkillMatch {
  skill: string;
  matched: boolean;
  highlight: 'green' | 'red';
}

/**
 * Структура данных результата анализа
 */
interface AnalysisResult {
  id: string;
  filename: string;
  status: string;
  raw_text: string;
  errors: AnalysisError[];
  grammar_errors?: GrammarError[];
  keywords?: string[];
  technical_skills?: string[];
  total_experience_months?: number;
  matched_skills?: SkillMatch[];
  missing_skills?: SkillMatch[];
  match_percentage?: number;
  best_match?: {
    vacancy_id: string;
    vacancy_title: string;
    match_percentage: number;
    matched_skills: string[];
    missing_skills: string[];
    salary_min?: number;
    salary_max?: number;
    location?: string;
  };
  processing_time?: number;
}

/**
 * Свойства компонента AnalysisResults
 */
interface AnalysisResultsProps {
  /** ID резюме из параметра URL */
  resumeId: string;
  /** URL-адрес конечной точки API для получения результатов анализа */
  apiUrl?: string;
}

/**
 * Компонент AnalysisResults
 *
 * Отображает полные результаты анализа резюме, включая:
 * - Обнаружение ошибок с значками критичности (критично, предупреждение, информация)
 * - Грамматические и орфографические проблемы с предложениями
 * - Извлеченные ключевые слова и технические навыки
 * - Сводку об опыте
 * - Подсветку навыков (зеленый - совпавшие, красный - отсутствующие)
 * - Рекомендации к действию
 *
 * @example
 * ```tsx
 * <AnalysisResults resumeId="test-id" />
 * ```
 */
const AnalysisResults: React.FC<AnalysisResultsProps> = ({
  resumeId,
  apiUrl = '/api/resumes',
}) => {
  const { t } = useTranslation();
  const { language } = useLanguageContext();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalysisResult | null>(null);

  /**
   * Получить результаты анализа из backend
   */
  const fetchAnalysis = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/${resumeId}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch analysis: ${response.statusText}`);
      }

      const result: AnalysisResult = await response.json();
      setData(result);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : t('results.error.failedToLoad');
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (resumeId) {
      fetchAnalysis();
    }
  }, [resumeId]);

  /**
   * Получить цвет и значок критичности для отображения ошибки
   */
  const getSeverityConfig = (severity: string) => {
    switch (severity) {
      case 'critical':
      case 'error':
        return {
          color: 'error' as const,
          icon: <ErrorIcon />,
          label: t('results.errors.severity.critical'),
        };
      case 'warning':
        return {
          color: 'warning' as const,
          icon: <WarningIcon />,
          label: t('results.errors.severity.warning'),
        };
      case 'info':
      default:
        return {
          color: 'info' as const,
          icon: <InfoIcon />,
          label: t('results.errors.severity.info'),
        };
    }
  };

  /**
   * Форматировать месяцы опыта в читаемую строку с правильным склонением
   */
  const formatExperience = (months?: number): string => {
    if (!months) return t('results.experience.notSpecified');

    const years = Math.floor(months / 12);
    const remainingMonths = months % 12;

    if (years === 0) {
      return t('results.experience.month', { count: remainingMonths });
    }
    if (remainingMonths === 0) {
      return t('results.experience.year', { count: years });
    }
    return t('results.experience.format', {
      years: t('results.experience.year', { count: years }),
      months: t('results.experience.month', { count: remainingMonths })
    });
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
          {t('results.loading.title')}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {t('results.loading.subtitle')}
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
          <Button color="inherit" onClick={fetchAnalysis} startIcon={<RefreshIcon />}>
            {t('results.error.retry')}
          </Button>
        }
      >
        <AlertTitle>{t('results.error.title')}</AlertTitle>
        {error}
      </Alert>
    );
  }

  /**
   * Отобразить состояние отсутствия данных
   */
  if (!data) {
    return (
      <Alert severity="info">
        <AlertTitle>{t('results.noData.title')}</AlertTitle>
        <span dangerouslySetInnerHTML={{ __html: t('results.noData.message', { id: resumeId }) }} />
      </Alert>
    );
  }

  const { errors, grammar_errors, keywords, technical_skills, total_experience_months, matched_skills, missing_skills, match_percentage, raw_text, filename, best_match } = data;

  // Подсчитать ошибки по критичности (с проверками безопасности)
  const criticalCount = (errors || []).filter((e) => e.severity === 'critical').length;
  const warningCount = (errors || []).filter((e) => e.severity === 'warning').length;
  const infoCount = (errors || []).filter((e) => e.severity === 'info').length;
  const grammarErrorCount = (grammar_errors || []).filter((e) => e.severity === 'error').length;

  return (
    <Stack spacing={3}>
      {/* Раздел заголовка */}
      <Paper elevation={2} sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" fontWeight={600}>
            {t('results.title')}
          </Typography>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchAnalysis} size="small">
            {t('results.refresh')}
          </Button>
        </Box>

        {/* Сводная статистика */}
        <Grid container spacing={2}>
          <Grid item xs={6} sm={3}>
            <Card variant="outlined" sx={{ borderColor: 'error.main' }}>
              <CardContent sx={{ textAlign: 'center', py: 1 }}>
                <Typography variant="h4" color="error.main" fontWeight={700}>
                  {criticalCount}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t('results.stats.critical')}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card variant="outlined" sx={{ borderColor: 'warning.main' }}>
              <CardContent sx={{ textAlign: 'center', py: 1 }}>
                <Typography variant="h4" color="warning.main" fontWeight={700}>
                  {warningCount}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t('results.stats.warnings')}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card variant="outlined" sx={{ borderColor: 'info.main' }}>
              <CardContent sx={{ textAlign: 'center', py: 1 }}>
                <Typography variant="h4" color="info.main" fontWeight={700}>
                  {infoCount}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t('results.stats.info')}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card variant="outlined" sx={{ borderColor: grammarErrorCount > 0 ? 'error.main' : 'success.main' }}>
              <CardContent sx={{ textAlign: 'center', py: 1 }}>
                <Typography variant="h4" color={grammarErrorCount > 0 ? 'error.main' : 'success.main'} fontWeight={700}>
                  {grammarErrorCount}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t('results.stats.grammarIssues')}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Paper>

      {/* Баннер лучшего совпадения */}
      {best_match && (
        <Paper
          elevation={3}
          sx={{
            p: 3,
            background: (theme) =>
              `linear-gradient(135deg, ${theme.palette.primary.main}15 0%, ${theme.palette.primary.main}05 100%)`,
            borderLeft: 6,
            borderColor: 'primary.main',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
            <Box sx={{ flex: 1, minWidth: 250 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Лучшее совпадение
              </Typography>
              <Typography variant="h5" fontWeight={600} color="primary.main">
                {best_match.match_percentage}% совпадение
              </Typography>
              <Typography variant="h6" sx={{ mt: 1 }}>
                {best_match.vacancy_title}
              </Typography>
              {best_match.location && (
                <Typography variant="body2" color="text.secondary">
                  📍 {best_match.location}
                </Typography>
              )}
            </Box>

            <Box sx={{ flex: 1, minWidth: 200 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Найденные навыки
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {best_match.matched_skills.slice(0, 8).map((skill) => (
                  <Chip
                    key={skill}
                    label={skill}
                    size="small"
                    color="success"
                    sx={{ fontSize: '0.75rem' }}
                  />
                ))}
                {best_match.matched_skills.length > 8 && (
                  <Chip
                    label={`+${best_match.matched_skills.length - 8}`}
                    size="small"
                    variant="outlined"
                  />
                )}
              </Box>
            </Box>

            <Box sx={{ textAlign: 'center' }}>
              <Button
                variant="contained"
                size="large"
                href={`/compare/${resumeId}/${best_match.vacancy_id}`}
                sx={{ minWidth: 180 }}
              >
                Подробнее
              </Button>
            </Box>
          </Box>
        </Paper>
      )}

      {/* Раздел текста резюме */}
      {raw_text && (
        <Paper elevation={1} sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" fontWeight={600}>
              Содержимое резюме: {filename}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {raw_text.length} символов
            </Typography>
          </Box>
          <Divider sx={{ mb: 2 }} />
          <Box
            sx={{
              bgcolor: 'grey.50',
              p: 2,
              borderRadius: 1,
              maxHeight: 500,
              overflow: 'auto',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {raw_text}
          </Box>
        </Paper>
      )}

      {/* Визуализация совпадения кандидата */}
      {technical_skills && technical_skills.length > 0 && (
        <CandidateMatchVisualization resumeId={resumeId} skills={technical_skills} />
      )}

      {/* Раздел ошибок и проблем */}
      {errors.length > 0 && (
        <Paper elevation={1} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight={600}>
            {t('results.detectedIssues')}
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Stack spacing={2}>
            {(errors || []).map((errorItem, index) => {
              const config = getSeverityConfig(errorItem.severity);
              return (
                <Alert key={index} severity={config.color} icon={config.icon}>
                  <AlertTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Chip label={config.label} size="small" color={config.color} variant="filled" />
                    <Typography variant="subtitle2" component="span" fontWeight={600}>
                      {errorItem.type}
                    </Typography>
                  </AlertTitle>
                  <Typography variant="body2" paragraph>
                    {errorItem.message}
                  </Typography>
                  {errorItem.recommendation && (
                    <Typography variant="body2" color="text.secondary">
                      <strong>{t('results.issues.recommendation')}</strong> {errorItem.recommendation}
                    </Typography>
                  )}
                </Alert>
              );
            })}
          </Stack>
        </Paper>
      )}

      {/* Раздел грамматики и орфографии */}
      {grammar_errors && grammar_errors.length > 0 && (
        <Paper elevation={1} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight={600}>
            {t('results.grammar.title')}
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="body1" fontWeight={500}>
                {t('results.grammar.viewIssues', { count: (grammar_errors || []).length })}
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <List>
                {(grammar_errors || []).map((error, index) => {
                  const config = getSeverityConfig(error.severity);
                  return (
                    <ListItem key={index} alignItems="flex-start" sx={{ px: 0 }}>
                      <ListItemIcon>{config.icon}</ListItemIcon>
                      <ListItemText
                        primary={
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Typography variant="subtitle2" component="span">
                              {error.type}
                            </Typography>
                            <Chip label={config.label} size="small" color={config.color} variant="outlined" />
                          </Stack>
                        }
                        secondary={
                          <Stack spacing={1} mt={0.5}>
                            <Typography variant="body2" component="div">
                              {error.message}
                            </Typography>
                            <Typography
                              variant="caption"
                              sx={{
                                fontFamily: 'monospace',
                                bgcolor: 'action.hover',
                                px: 1,
                                py: 0.5,
                                borderRadius: 0.5,
                                display: 'inline-block',
                              }}
                            >
                              "{error.context}"
                            </Typography>
                            {error.suggestions && error.suggestions.length > 0 && (
                              <Typography variant="body2" color="primary.main">
                                <strong>{t('results.grammar.suggestion')}</strong> {error.suggestions.join(` ${t('common.or')} `)}
                              </Typography>
                            )}
                          </Stack>
                        }
                      />
                    </ListItem>
                  );
                })}
              </List>
            </AccordionDetails>
          </Accordion>
        </Paper>
      )}

      {/* Раздел извлеченной информации */}
      {(keywords && keywords.length > 0) || (technical_skills && technical_skills.length > 0) ? (
        <Paper elevation={1} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight={600}>
            {t('results.extractedInfo')}
          </Typography>
          <Divider sx={{ mb: 2 }} />

          {/* Общий опыт */}
          {total_experience_months !== undefined && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                {t('results.experience.title')}
              </Typography>
              <Typography variant="h5" color="primary.main" fontWeight={600}>
                {formatExperience(total_experience_months)}
              </Typography>
            </Box>
          )}

          {/* Ключевые слова */}
          {keywords && keywords.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                {t('results.keywords.title')}
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {keywords.slice(0, 20).map((keyword, index) => (
                  <Chip key={index} label={keyword} size="small" variant="outlined" />
                ))}
              </Box>
            </Box>
          )}

          {/* Технические навыки */}
          {technical_skills && technical_skills.length > 0 && (
            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                {t('results.skills.title')}
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {(technical_skills || []).map((skill, index) => (
                  <Chip key={index} label={skill} size="small" color="primary" variant="filled" />
                ))}
              </Box>
            </Box>
          )}
        </Paper>
      ) : null}

      {/* Раздел сопоставления навыков (если доступно) */}
      {(matched_skills && matched_skills.length > 0) || (missing_skills && missing_skills.length > 0) ? (
        <Paper elevation={1} sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" fontWeight={600}>
              {t('results.skillMatching')}
            </Typography>
            {match_percentage !== undefined && (
              <Chip
                label={t('results.skills.matchPercentage', { percentage: formatNumber(match_percentage, language) })}
                color={match_percentage >= 70 ? 'success' : match_percentage >= 40 ? 'warning' : 'error'}
                sx={{ fontWeight: 600 }}
              />
            )}
          </Box>
          <Divider sx={{ mb: 2 }} />

          {/* Совпавшие навыки - Зеленый */}
          {matched_skills && matched_skills.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" color="success.main" gutterBottom fontWeight={600}>
                <CheckIcon fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
                {t('results.skills.matched', { count: matched_skills.length })}
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {matched_skills.map((item, index) => (
                  <Chip
                    key={index}
                    label={item.skill}
                    size="small"
                    sx={{
                      bgcolor: 'success.main',
                      color: 'success.contrastText',
                      '&:hover': {
                        bgcolor: 'success.dark',
                      },
                    }}
                  />
                ))}
              </Box>
            </Box>
          )}

          {/* Отсутствующие навыки - Красный */}
          {missing_skills && missing_skills.length > 0 && (
            <Box>
              <Typography variant="subtitle2" color="error.main" gutterBottom fontWeight={600}>
                <CrossIcon fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
                {t('results.skills.missing', { count: missing_skills.length })}
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {missing_skills.map((item, index) => (
                  <Chip
                    key={index}
                    label={item.skill}
                    size="small"
                    sx={{
                      bgcolor: 'error.main',
                      color: 'error.contrastText',
                      '&:hover': {
                        bgcolor: 'error.dark',
                      },
                    }}
                  />
                ))}
              </Box>
            </Box>
          )}
        </Paper>
      ) : null}

      {/* Сообщение об отсутствии проблем */}
      {errors.length === 0 && (!grammar_errors || grammar_errors.length === 0) && (
        <Paper elevation={1} sx={{ p: 4, textAlign: 'center' }}>
          <CheckIcon sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
          <Typography variant="h6" color="success.main" gutterBottom fontWeight={600}>
            {t('results.allClear.title')}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {t('results.allClear.message')}
          </Typography>
        </Paper>
      )}
    </Stack>
  );
};

export default AnalysisResults;
