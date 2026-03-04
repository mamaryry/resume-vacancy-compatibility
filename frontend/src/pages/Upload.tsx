import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Typography, Box, Paper } from '@mui/material';
import ResumeUploader from '@components/ResumeUploader';

/**
 * Компонент страницы загрузки
 *
 * Обеспечивает интерфейс загрузки резюме с поддержкой перетаскивания.
 * Пользователи могут загружать резюме в формате PDF или DOCX для AI-анализа.
 *
 * При успешной загрузке перенаправляет на страницу результатов с ID резюме.
 */
const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();

  /**
   * Обработать успешную загрузку путем перехода на страницу результатов
   */
  const handleUploadComplete = (resumeId: string) => {
    navigate(`/results/${resumeId}`);
  };

  /**
   * Обработать ошибки загрузки (можно расширить с логированием ошибок/toast)
   */
  const handleUploadError = (error: string) => {
    // Ошибка отображается в компоненте ResumeUploader
    // Дополнительная обработка ошибок может быть добавлена здесь (например, toast-уведомления)
  };

  return (
    <Box>
      {/* Заголовок страницы */}
      <Typography variant="h4" component="h1" gutterBottom fontWeight={600}>
        {t('upload.title')}
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        {t('upload.subtitle')}
      </Typography>

      {/* Компонент загрузки */}
      <Paper elevation={1} sx={{ p: 4, mt: 3 }}>
        <ResumeUploader
          uploadUrl="http://localhost:8000/api/resumes/upload"
          onUploadComplete={handleUploadComplete}
          onUploadError={handleUploadError}
        />
      </Paper>

      {/* Дополнительные инструкции */}
      <Paper elevation={0} sx={{ p: 3, mt: 3, bgcolor: 'action.hover' }}>
        <Typography variant="h6" gutterBottom fontWeight={600}>
          {t('upload.whatHappensNext.title')}
        </Typography>
        <Typography variant="body2" paragraph>
          {t('upload.whatHappensNext.step1')}
        </Typography>
        <Typography variant="body2" paragraph>
          {t('upload.whatHappensNext.step2')}
        </Typography>
        <Typography variant="body2" paragraph>
          {t('upload.whatHappensNext.step3')}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t('upload.whatHappensNext.timeline')}
        </Typography>
      </Paper>
    </Box>
  );
};

export default UploadPage;
