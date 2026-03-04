import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  Chip,
  Stack,
  CircularProgress,
  Alert,
  Button,
  Divider,
  LinearProgress,
} from '@mui/material';
import {
  Work as WorkIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  Star as StarIcon,
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';

interface MatchResult {
  vacancy_id: string;
  vacancy_title: string;
  match_percentage: number;
  matched_skills: string[];
  missing_skills: string[];
  additional_matched: string[];
  salary_min?: number;
  salary_max?: number;
  location?: string;
  work_format?: string;
  industry?: string;
}

interface AllVacanciesMatchResponse {
  resume_id: string;
  total_vacancies: number;
  matches: MatchResult[];
  best_match: MatchResult | null;
  processing_time_ms: number;
}

interface VacancyMatchResultsProps {
  resumeId: string;
}

const StyledCard = styled(Card)(({ theme }) => ({
  marginBottom: theme.spacing(2),
  transition: 'transform 0.2s, box-shadow 0.2s',
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: theme.shadows[4],
  },
}));

const MatchPercentageBar = styled(LinearProgress)<{ value: number }>(
  ({ theme, value }) => ({
    height: 10,
    borderRadius: 5,
    backgroundColor: theme.palette.grey[200],
    '& .MuiLinearProgress-bar': {
      backgroundColor:
        value >= 80
          ? theme.palette.success.main
          : value >= 50
          ? theme.palette.warning.main
          : theme.palette.error.main,
    },
  })
);

const VacancyMatchResults: React.FC<VacancyMatchResultsProps> = ({ resumeId }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matchData, setMatchData] = useState<AllVacanciesMatchResponse | null>(null);

  const fetchMatches = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/vacancies/match-all?resume_id=${resumeId}`
      );

      if (!response.ok) {
        throw new Error('Не удалось получить совпадения');
      }

      const data: AllVacanciesMatchResponse = await response.json();
      setMatchData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить совпадения');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (resumeId) {
      fetchMatches();
    }
  }, [resumeId]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
      <CircularProgress />
      <Typography variant="body1" sx={{ ml: 2 }}>
        Анализ резюме со всеми вакансиями...
      </Typography>
    </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!matchData || matchData.total_vacancies === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <WorkIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Нет доступных вакансий для сопоставления
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Сначала создайте вакансию, чтобы увидеть результаты сопоставления
        </Typography>
        <Button
          variant="contained"
          color="primary"
          onClick={() => window.location.href = '/recruiter/vacancies/create'}
        >
          Создать вакансию
        </Button>
      </Box>
    );
  }

  const { best_match, matches } = matchData;

  return (
    <Box>
      {/* Best Match Banner */}
      {best_match && (
        <StyledCard
          sx={{
            mb: 3,
            background: (theme) =>
              `linear-gradient(135deg, ${theme.palette.primary.main}22 0%, ${theme.palette.primary.main}44 100%)`,
          }}
        >
          <CardContent>
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                mb: 2,
              }}
            >
              <StarIcon
                sx={{ fontSize: 32, color: 'primary.main' }}
              />
              <Box>
                <Typography variant="h5" fontWeight={600} color="primary.main">
                  Лучшее совпадение
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {best_match.match_percentage}% совпадение
                </Typography>
              </Box>
            </Box>

            <Typography variant="h4" gutterBottom>
              {best_match.vacancy_title}
            </Typography>

            <MatchPercentageBar
              variant="determinate"
              value={best_match.match_percentage}
              sx={{ mb: 2 }}
            />

            <Box
              sx={{
                display: 'flex',
                gap: 3,
                flexWrap: 'wrap',
              }}
            >
              {/* Matched Skills */}
              <Box sx={{ flex: 1, minWidth: 200 }}>
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                  sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                >
                  <CheckIcon color="success" fontSize="small" />
                  Найденные навыки ({best_match.matched_skills.length})
                </Typography>
                <Stack direction="row" spacing={0.5} flexWrap="wrap">
                  {best_match.matched_skills.map((skill) => (
                    <Chip
                      key={skill}
                      label={skill}
                      size="small"
                      color="success"
                      sx={{ fontSize: '0.75rem' }}
                    />
                  ))}
                </Stack>
              </Box>

              {/* Missing Skills */}
              <Box sx={{ flex: 1, minWidth: 200 }}>
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                  sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                >
                  <CancelIcon color="error" fontSize="small" />
                  Отсутствующие навыки ({best_match.missing_skills.length})
                </Typography>
                <Stack direction="row" spacing={0.5} flexWrap="wrap">
                  {best_match.missing_skills.map((skill) => (
                    <Chip
                      key={skill}
                      label={skill}
                      size="small"
                      color="error"
                      sx={{ fontSize: '0.75rem' }}
                    />
                  ))}
                </Stack>
              </Box>

              {/* Additional Skills */}
              {best_match.additional_matched &&
                best_match.additional_matched.length > 0 && (
                <Box sx={{ flex: 1, minWidth: 200 }}>
                  <Typography
                    variant="subtitle2"
                    color="text.secondary"
                    gutterBottom
                  >
                    ⭐ Бонусные навыки ({best_match.additional_matched.length})
                  </Typography>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap">
                    {best_match.additional_matched.map((skill) => (
                      <Chip
                        key={skill}
                        label={skill}
                        size="small"
                        color="secondary"
                        sx={{ fontSize: '0.75rem' }}
                      />
                    ))}
                  </Stack>
                </Box>
              )}
            </Box>

            {/* Job Details */}
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Детали вакансии
              </Typography>
              <List dense>
                {best_match.salary_min && (
                  <ListItem>
                    <ListItemText
                      primary={`Зарплата: $${best_match.salary_min?.toLocaleString()} - $${best_match.salary_max?.toLocaleString()}`}
                    />
                  </ListItem>
                )}
                {best_match.location && (
                  <ListItem>
                    <ListItemText
                      primary={`Местоположение: ${best_match.location}`}
                    />
                  </ListItem>
                )}
                {best_match.work_format && (
                  <ListItem>
                    <ListItemText
                      primary={`Формат работы: ${best_match.work_format}`}
                    />
                  </ListItem>
                )}
                {best_match.industry && (
                  <ListItem>
                    <ListItemText primary={`Индустрия: ${best_match.industry}`} />
                  </ListItem>
                )}
              </List>
            </Box>

            <Button
              variant="contained"
              color="primary"
              href={`/compare/${resumeId}/${best_match.vacancy_id}`}
              sx={{ mt: 2 }}
            >
              Подробное сравнение
            </Button>
          </CardContent>
        </StyledCard>
      )}

      {/* All Matches */}
      <Typography variant="h5" fontWeight={600} gutterBottom>
        Все совпадения вакансий ({matchData.total_vacancies})
      </Typography>

      <Stack spacing={2}>
        {matches.map((match, index) => (
          <Card
            key={match.vacancy_id}
            variant={index === 0 && best_match ? 'outlined' : 'elevation'}
            sx={{
              border: index === 0 && best_match ? 2 : 1,
              borderColor: index === 0 && best_match ? 'primary.main' : 'divider',
            }}
          >
            <CardContent>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  mb: 2,
                }}
              >
                <Box sx={{ flex: 1 }}>
                  <Typography variant="h6" fontWeight={600} gutterBottom>
                    {match.vacancy_title}
                  </Typography>
                  <MatchPercentageBar
                    variant="determinate"
                    value={match.match_percentage}
                    sx={{ mb: 1 }}
                  />
                </Box>
                <Typography
                  variant="h4"
                  fontWeight={700}
                  color={
                    match.match_percentage >= 80
                      ? 'success.main'
                      : match.match_percentage >= 50
                      ? 'warning.main'
                      : 'error.main'
                  }
                >
                  {match.match_percentage}%
                </Typography>
              </Box>

              <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
                <Box>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', mb: 0.5 }}
                  >
                    ✅ Найдено ({match.matched_skills.length})
                  </Typography>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap">
                    {match.matched_skills.slice(0, 10).map((skill) => (
                      <Chip
                        key={skill}
                        label={skill}
                        size="small"
                        color="success"
                      />
                    ))}
                    {match.matched_skills.length > 10 && (
                      <Chip
                        label={`+${match.matched_skills.length - 10}`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Stack>
                </Box>

                <Box>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', mb: 0.5 }}
                  >
                    ❌ Отсутствует ({match.missing_skills.length})
                  </Typography>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap">
                    {match.missing_skills.slice(0, 10).map((skill) => (
                      <Chip
                        key={skill}
                        label={skill}
                        size="small"
                        color="error"
                      />
                    ))}
                    {match.missing_skills.length > 10 && (
                      <Chip
                        label={`+${match.missing_skills.length - 10}`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Stack>
                </Box>
              </Stack>

              {match.additional_matched && match.additional_matched.length > 0 && (
                <>
                  <Divider sx={{ my: 1 }} />
                  <Typography variant="caption" color="text.secondary">
                    ⭐ Бонус: {match.additional_matched.join(', ')}
                  </Typography>
                </>
              )}

              {match.salary_min && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                  💰 ${match.salary_min?.toLocaleString()} - ${match.salary_max?.toLocaleString()}
                  {match.location && ` • ${match.location}`}
                </Typography>
              )}
            </CardContent>
          </Card>
        ))}
      </Stack>

      {/* Processing Time */}
      <Box sx={{ mt: 3, textAlign: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          Обработано за {matchData.processing_time_ms}мс
        </Typography>
      </Box>
    </Box>
  );
};

export default VacancyMatchResults;
