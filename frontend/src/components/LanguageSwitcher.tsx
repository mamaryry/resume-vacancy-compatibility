import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box,
  FormControl,
  Select,
  MenuItem,
  Typography,
  SelectChangeEvent,
} from '@mui/material';
import { useLanguageContext, SUPPORTED_LANGUAGES } from '@/contexts/LanguageContext';

/**
 * Компонент LanguageSwitcher
 *
 * Обеспечивает раскрывающийся селектор для переключения между поддерживаемыми языками.
 * Отображает название языка со значком флага emoji для визуальной идентификации.
 *
 * Функции:
 * - Отображает текущий язык в раскрывающемся списке
 * - Отображает флаг emoji (🇺🇸 для английского, 🇷🇺 для русского)
 * - Меняет язык при выборе
 * - Интегрируется с LanguageContext для управления состоянием
 * - Использует i18next для сохранения переводов
 *
 * @example
 * ```tsx
 * // В заголовке компонента Layout
 * <LanguageSwitcher />
 * ```
 */
const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();
  const { language, setLanguage } = useLanguageContext();

  /**
   * Обработать изменение выбора языка
   *
   * Обновляет язык приложения, когда пользователь выбирает другой язык
   * из раскрывающегося списка.
   *
   * @param event - Событие изменения select
   */
  const handleLanguageChange = async (event: SelectChangeEvent<string>) => {
    const newLanguage = event.target.value as 'en' | 'ru';
    await setLanguage(newLanguage);
  };

  /**
   * Получить флаг emoji для языка
   *
   * Возвращает соответствующий флаг emoji для каждого поддерживаемого языка.
   *
   * @param langCode - Код языка ('en' или 'ru')
   * @returns Строка флага emoji
   */
  const getFlagEmoji = (langCode: string): string => {
    const flags: Record<string, string> = {
      en: '🇺🇸',
      ru: '🇷🇺',
    };
    return flags[langCode] || '🌐';
  };

  return (
    <Box sx={{ minWidth: 120 }}>
      <FormControl size="small" variant="outlined">
        <Select
          value={language}
          onChange={handleLanguageChange}
          displayEmpty
          inputProps={{
            'aria-label': i18n.t('language.switcher.ariaLabel') || 'Выбрать язык',
          }}
          sx={{
            color: 'inherit',
            bgcolor: 'rgba(255, 255, 255, 0.1)',
            borderRadius: 1,
            '& .MuiSelect-select': {
              color: 'inherit',
              py: 0.75,
              px: 1.5,
            },
            '& .MuiOutlinedInput-notchedOutline': {
              borderColor: 'rgba(255, 255, 255, 0.3)',
            },
            '&:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: 'rgba(255, 255, 255, 0.5)',
            },
            '& .MuiSvgIcon-root': {
              color: 'inherit',
            },
          }}
        >
          {Object.values(SUPPORTED_LANGUAGES).map((lang) => (
            <MenuItem
              key={lang.code}
              value={lang.code}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
              }}
            >
              <Box
                component="span"
                sx={{
                  fontSize: '1.2rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                }}
              >
                {getFlagEmoji(lang.code)}
              </Box>
              <Typography
                variant="body2"
                sx={{
                  fontWeight: language === lang.code ? 600 : 400,
                }}
              >
                {lang.nameEn}
              </Typography>
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  );
};

export default LanguageSwitcher;
