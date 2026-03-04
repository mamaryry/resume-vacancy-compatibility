import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import i18n from '@i18n';
import { apiClient } from '@/api/client';

/**
 * Поддерживаемые языки для приложения
 */
export type SupportedLanguage = 'en' | 'ru';

/**
 * Направление текста для языка
 */
export type TextDirection = 'ltr' | 'rtl';

/**
 * Конфигурация отображения языка
 */
export interface LanguageConfig {
  /** Код языка (ISO 639-1) */
  code: SupportedLanguage;
  /** Название языка на родном языке */
  name: string;
  /** Название языка на английском */
  nameEn: string;
  /** Код локали для форматирования */
  locale: string;
  /** Направление текста (ltr или rtl) */
  direction: TextDirection;
}

/**
 * Конфигурация поддерживаемых языков
 */
export const SUPPORTED_LANGUAGES: Record<SupportedLanguage, LanguageConfig> = {
  en: {
    code: 'en',
    name: 'English',
    nameEn: 'English',
    locale: 'en-US',
    direction: 'ltr',
  },
  ru: {
    code: 'ru',
    name: 'Русский',
    nameEn: 'Russian',
    locale: 'ru-RU',
    direction: 'ltr',
  },
} as const;

/**
 * Интерфейс состояния контекста языка
 */
interface LanguageState {
  /** Текущий код языка */
  language: SupportedLanguage;
  /** Функция изменения языка */
  setLanguage: (language: SupportedLanguage) => Promise<void>;
  /** Получить конфигурацию языка */
  getLanguageConfig: (language: SupportedLanguage) => LanguageConfig;
  /** Проверить, поддерживается ли язык */
  isLanguageSupported: (language: string) => language is SupportedLanguage;
}

/**
 * Свойства контекста языка
 */
interface LanguageProviderProps {
  /** Дочерние компоненты */
  children: ReactNode;
  /** Начальный язык (опционально, по умолчанию язык из i18n) */
  initialLanguage?: SupportedLanguage;
}

/**
 * Контекст языка
 *
 * Обеспечивает состояние языка и управление для приложения.
 * Интегрируется с i18next для перевода и сохранения языка.
 *
 * @example
 * ```tsx
 * // Оберните приложение в LanguageProvider
 * <LanguageProvider>
 *   <App />
 * </LanguageProvider>
 *
 * // Используйте в компонентах
 * const { language, setLanguage } = useLanguageContext();
 *
 * // Изменить язык
 * await setLanguage('ru');
 * ```
 */
const LanguageContext = createContext<LanguageState | undefined>(undefined);

/**
 * Компонент провайдера языка
 *
 * Управляет состоянием языка приложения и интегрируется с i18next.
 * Обрабатывает изменения языка и сохраняет предпочтения языка.
 *
 * @param props - Свойства провайдера
 * @returns Провайдер контекста языка
 */
export const LanguageProvider: React.FC<LanguageProviderProps> = ({
  children,
  initialLanguage,
}) => {
  const [language, setLanguageState] = useState<SupportedLanguage>(() => {
    // Использовать initialLanguage, если предоставлено, иначе получить из i18n
    if (initialLanguage) {
      return initialLanguage;
    }
    // Получить текущий язык из i18n, по умолчанию 'en'
    const currentLang = i18n.language as SupportedLanguage;
    return SUPPORTED_LANGUAGES[currentLang] ? currentLang : 'en';
  });

  /**
   * Обновить локальное состояние при изменении языка в i18n
   */
  useEffect(() => {
    const handleLanguageChange = (lng: string) => {
      const newLanguage = SUPPORTED_LANGUAGES[lng as SupportedLanguage]
        ? (lng as SupportedLanguage)
        : 'en';
      setLanguageState(newLanguage);
    };

    // Слушать изменения языка в i18n
    i18n.on('languageChanged', handleLanguageChange);

    // Очистить слушатель
    return () => {
      i18n.off('languageChanged', handleLanguageChange);
    };
  }, []);

  /**
   * Обновить атрибут dir HTML при изменении языка
   * Это обеспечивает правильное направление текста для языков LTR и RTL
   */
  useEffect(() => {
    const direction = SUPPORTED_LANGUAGES[language].direction;
    document.documentElement.setAttribute('dir', direction);
    document.documentElement.setAttribute('lang', language);
  }, [language]);

  /**
   * Изменить язык приложения
   *
   * Обновляет язык в i18n и запускает перерисовку всех переведенных компонентов.
   * Изменение языка сохраняется в localStorage детектором i18next
   * и синхронизируется с API предпочтений backend.
   *
   * @param newLanguage - Код языка для переключения
   * @returns Promise, который разрешается при завершении изменения языка
   */
  const setLanguage = useCallback(async (newLanguage: SupportedLanguage): Promise<void> => {
    if (!SUPPORTED_LANGUAGES[newLanguage]) {
      console.warn(`Unsupported language: ${newLanguage}. Falling back to 'en'.`);
      newLanguage = 'en';
    }

    // Обновить язык в i18n (запускает событие languageChanged)
    await i18n.changeLanguage(newLanguage);
    // Локальное состояние будет обновлено слушателем события languageChanged

    // Синхронизировать предпочтение языка с backend
    // Не давать сбоям backend заблокировать обновление UI
    try {
      await apiClient.updateLanguagePreference(newLanguage);
    } catch (error) {
      // Логировать ошибку, но не выбрасывать - UI уже обновлен локально
      console.warn('Не удалось синхронизировать предпочтение языка с backend:', error);
    }
  }, []);

  /**
   * Получить объект конфигурации языка
   *
   * @param languageCode - Код языка
   * @returns Объект конфигурации языка
   */
  const getLanguageConfig = useCallback(
    (languageCode: SupportedLanguage): LanguageConfig => {
      return SUPPORTED_LANGUAGES[languageCode] || SUPPORTED_LANGUAGES.en;
    },
    []
  );

  /**
   * Проверить, поддерживается ли код языка
   *
   * @param languageCode - Код языка для проверки
   * @returns True, если язык поддерживается
   */
  const isLanguageSupported = useCallback(
    (languageCode: string): languageCode is SupportedLanguage => {
      return languageCode in SUPPORTED_LANGUAGES;
    },
    []
  );

  const contextValue: LanguageState = {
    language,
    setLanguage,
    getLanguageConfig,
    isLanguageSupported,
  };

  return (
    <LanguageContext.Provider value={contextValue}>
      {children}
    </LanguageContext.Provider>
  );
};

/**
 * Хук useLanguageContext
 *
 * Получает доступ к состоянию и функциям контекста языка.
 * Должен использоваться внутри LanguageProvider.
 *
 * @throws Error, если используется вне LanguageProvider
 * @returns Состояние контекста языка
 *
 * @example
 * ```tsx
 * const { language, setLanguage } = useLanguageContext();
 *
 * // Отобразить текущий язык
 * <p>Текущий язык: {language}</p>
 *
 * // Изменить язык при нажатии кнопки
 * <button onClick={() => setLanguage('ru')}>
 *   Переключить на русский
 * </button>
 * ```
 */
export const useLanguageContext = (): LanguageState => {
  const context = useContext(LanguageContext);

  if (context === undefined) {
    throw new Error(
      'useLanguageContext должен использоваться внутри LanguageProvider. ' +
        'Оберните дерево компонентов в <LanguageProvider>.'
    );
  }

  return context;
};

export default LanguageContext;
