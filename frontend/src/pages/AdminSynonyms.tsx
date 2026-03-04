import React from 'react';
import { Container, Typography, Box } from '@mui/material';
import { useTranslation } from 'react-i18next';
import CustomSynonymsManager from '@components/CustomSynonymsManager';

/**
 * Страница администрирования синонимов
 *
 * Предоставляет интерфейс администратора для управления пользовательскими синонимами навыков
 * специфичными для организации.
 * Эта страница доступна по адресу /admin/synonyms и требует контекста организации.
 */
const AdminSynonymsPage: React.FC = () => {
  const { t } = useTranslation();
  // В настоящее время используется ID организации по умолчанию
  // В продакшене это будет получаться из контекста аутентификации
  const organizationId = 'org123';

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          {t('adminSynonyms.title')}
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {t('adminSynonyms.subtitle')}
        </Typography>
      </Box>

      <CustomSynonymsManager organizationId={organizationId} />
    </Container>
  );
};

export default AdminSynonymsPage;
