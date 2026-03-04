import React from 'react';
import { Box, Container } from '@mui/material';
import { useParams } from 'react-router-dom';
import JobComparison from '@components/JobComparison';

/**
 * Компонент страницы сравнения
 *
 * Отображает комплексный анализ сравнения вакансий между резюме и вакансией,
 * показывая совпавшие/отсутствующие навыки, процент совпадения и подтверждение опыта.
 */
const ComparePage: React.FC = () => {
  const { resumeId, vacancyId } = useParams<{ resumeId: string; vacancyId: string }>();

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box>
        <JobComparison resumeId={resumeId || ''} vacancyId={vacancyId || ''} />
      </Box>
    </Container>
  );
};

export default ComparePage;
