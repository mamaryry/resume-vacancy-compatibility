/**
 * Определения типов запросов и ответов API
 *
 * Этот модуль содержит интерфейсы TypeScript для всех коммуникаций API
 * с backend-сервисом анализа резюме.
 */

/**
 * Ответ загрузки резюме
 */
export interface ResumeUploadResponse {
  id: string;
  filename: string;
  status: string;
  message: string;
}

/**
 * Запрос анализа резюме
 */
export interface AnalysisRequest {
  resume_id: string;
  extract_experience?: boolean;
  check_grammar?: boolean;
}

/**
 * Результаты анализа ключевых слов
 */
export interface KeywordAnalysis {
  keywords: string[];
  keyphrases: string[];
  scores: number[];
}

/**
 * Результаты анализа сущностей
 */
export interface EntityAnalysis {
  organizations: string[];
  dates: string[];
  persons?: string[];
  locations?: string[];
  technical_skills: string[];
}

/**
 * Отдельная грамматическая/орфографическая ошибка
 */
export interface GrammarError {
  type: string;
  severity: string;
  message: string;
  context: string;
  suggestions: string[];
  position: {
    start: number;
    end: number;
  };
}

/**
 * Результаты грамматического анализа
 */
export interface GrammarAnalysis {
  total_errors: number;
  errors_by_category: Record<string, number>;
  errors_by_severity: Record<string, number>;
  errors: GrammarError[];
}

/**
 * Запись о работе
 */
export interface ExperienceEntry {
  company: string;
  position: string;
  start_date: string;
  end_date: string | null;
  duration_months: number;
}

/**
 * Результаты анализа опыта
 */
export interface ExperienceAnalysis {
  total_experience_months: number;
  total_experience_summary: string;
  experiences: ExperienceEntry[];
}

/**
 * Ответ анализа резюме
 */
export interface AnalysisResponse {
  resume_id: string;
  filename: string;
  processing_time_seconds: number;
  keywords: KeywordAnalysis;
  entities: EntityAnalysis;
  grammar?: GrammarAnalysis;
  experience?: ExperienceAnalysis;
  language_detected: string;
}

/**
 * Результат совпадения отдельного навыка
 */
export interface SkillMatch {
  skill: string;
  status: 'matched' | 'missing';
  highlight: 'green' | 'red';
}

/**
 * Подтверждение опыта для определенного навыка
 */
export interface SkillExperienceVerification {
  skill: string;
  required_experience_months: number;
  candidate_experience_months: number;
  meets_requirement: boolean;
  projects: Array<{
    company: string;
    position: string;
    duration_months: number;
  }>;
}

/**
 * Ответ сопоставления вакансий
 */
export interface MatchResponse {
  resume_id: string;
  match_percentage: number;
  matched_skills: SkillMatch[];
  missing_skills: SkillMatch[];
  experience_verification: SkillExperienceVerification[];
  overall_assessment: string;
}

/**
 * Данные вакансии для сравнения
 */
export interface JobVacancy {
  uid?: string;
  data: {
    position: string;
    industry?: string;
    mandatory_requirements: string[];
    additional_requirements?: string[];
    experience_levels?: string[];
    project_tasks?: string[];
    project_description?: string[];
  };
}

/**
 * Ответ об ошибке API
 */
export interface ApiError {
  detail: string;
  status?: number;
}

/**
 * Ответ проверки работоспособности
 */
export interface HealthResponse {
  status: string;
  version?: string;
}

/**
 * Callback прогресса загрузки
 */
export type UploadProgressCallback = (progress: number) => void;

/**
 * Конфигурация API клиента
 */
export interface ApiClientConfig {
  baseURL?: string;
  timeout?: number;
  headers?: Record<string, string>;
}

/**
 * Вариант навыка для записей таксономии
 */
export interface SkillVariant {
  name: string;
  context?: string;
  variants: string[];
  metadata?: Record<string, unknown>;
  is_active: boolean;
}

/**
 * Запрос создания таксономии навыков
 */
export interface SkillTaxonomyCreate {
  industry: string;
  skills: SkillVariant[];
}

/**
 * Запрос обновления таксономии навыков
 */
export interface SkillTaxonomyUpdate {
  skill_name?: string;
  context?: string;
  variants?: string[];
  metadata?: Record<string, unknown>;
  is_active?: boolean;
}

/**
 * Ответ таксономии навыков
 */
export interface SkillTaxonomyResponse {
  id: string;
  industry: string;
  skill_name: string;
  context?: string;
  variants: string[];
  metadata?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Ответ списка таксономии навыков
 */
export interface SkillTaxonomyListResponse {
  industry: string;
  skills: SkillTaxonomyResponse[];
  total_count: number;
}

/**
 * Определение записи пользовательского синонима
 */
export interface CustomSynonymEntry {
  canonical_skill: string;
  custom_synonyms: string[];
  context?: string;
  is_active: boolean;
}

/**
 * Запрос создания пользовательского синонима
 */
export interface CustomSynonymCreate {
  organization_id: string;
  created_by?: string;
  synonyms: CustomSynonymEntry[];
}

/**
 * Запрос обновления пользовательского синонима
 */
export interface CustomSynonymUpdate {
  canonical_skill?: string;
  custom_synonyms?: string[];
  context?: string;
  is_active?: boolean;
}

/**
 * Ответ пользовательского синонима
 */
export interface CustomSynonymResponse {
  id: string;
  organization_id: string;
  canonical_skill: string;
  custom_synonyms: string[];
  context?: string;
  created_by?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Ответ списка пользовательских синонимов
 */
export interface CustomSynonymListResponse {
  organization_id: string;
  synonyms: CustomSynonymResponse[];
  total_count: number;
}

/**
 * Определение записи обратной связи
 */
export interface FeedbackEntry {
  resume_id: string;
  vacancy_id: string;
  match_result_id?: string;
  skill: string;
  was_correct: boolean;
  confidence_score?: number;
  recruiter_correction?: string;
  actual_skill?: string;
  feedback_source: string;
  metadata?: Record<string, unknown>;
}

/**
 * Запрос создания обратной связи
 */
export interface FeedbackCreate {
  feedback: FeedbackEntry[];
}

/**
 * Запрос обновления обратной связи
 */
export interface FeedbackUpdate {
  was_correct?: boolean;
  confidence_score?: number;
  recruiter_correction?: string;
  actual_skill?: string;
  processed?: boolean;
  metadata?: Record<string, unknown>;
}

/**
 * Ответ обратной связи
 */
export interface FeedbackResponse {
  id: string;
  resume_id: string;
  vacancy_id: string;
  match_result_id?: string;
  skill: string;
  was_correct: boolean;
  confidence_score?: number;
  recruiter_correction?: string;
  actual_skill?: string;
  feedback_source: string;
  processed: boolean;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/**
 * Ответ списка обратной связи
 */
export interface FeedbackListResponse {
  feedback: FeedbackResponse[];
  total_count: number;
}

/**
 * Определение записи версии модели
 */
export interface ModelVersionEntry {
  model_name: string;
  version: string;
  is_active: boolean;
  is_experiment: boolean;
  experiment_config?: Record<string, unknown>;
  model_metadata?: Record<string, unknown>;
  accuracy_metrics?: Record<string, unknown>;
  file_path?: string;
  performance_score?: number;
}

/**
 * Запрос создания версии модели
 */
export interface ModelVersionCreate {
  models: ModelVersionEntry[];
}

/**
 * Запрос обновления версии модели
 */
export interface ModelVersionUpdate {
  version?: string;
  is_active?: boolean;
  is_experiment?: boolean;
  experiment_config?: Record<string, unknown>;
  model_metadata?: Record<string, unknown>;
  accuracy_metrics?: Record<string, unknown>;
  file_path?: string;
  performance_score?: number;
}

/**
 * Ответ версии модели
 */
export interface ModelVersionResponse {
  id: string;
  model_name: string;
  version: string;
  is_active: boolean;
  is_experiment: boolean;
  experiment_config?: Record<string, unknown>;
  model_metadata?: Record<string, unknown>;
  accuracy_metrics?: Record<string, unknown>;
  file_path?: string;
  performance_score?: number;
  created_at: string;
  updated_at: string;
}

/**
 * Ответ списка версий моделей
 */
export interface ModelVersionListResponse {
  models: ModelVersionResponse[];
  total_count: number;
}

/**
 * Запрос обратной связи о совпадении
 */
export interface MatchFeedbackRequest {
  match_id: string;
  skill: string;
  was_correct: boolean;
  recruiter_correction?: string;
  confidence_score?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Ответ обратной связи о совпадении
 */
export interface MatchFeedbackResponse {
  id: string;
  match_id: string;
  skill: string;
  was_correct: boolean;
  recruiter_correction?: string;
  feedback_source: string;
  processed: boolean;
  created_at: string;
}

/**
 * Результат совпадения навыка для сравнения
 */
export interface ComparisonSkillMatch {
  skill: string;
  status: 'matched' | 'missing';
  matched_as: string | null;
  highlight: 'green' | 'red';
  confidence: number;
  match_type: string;
}

/**
 * Подтверждение опыта для сравнения
 */
export interface ComparisonExperienceVerification {
  required_months: number;
  actual_months: number;
  meets_requirement: boolean;
  summary: string;
}

/**
 * Результат сравнения резюме
 */
export interface ResumeComparisonResult {
  rank: number;
  resume_id: string;
  vacancy_title: string;
  match_percentage: number;
  required_skills_match: ComparisonSkillMatch[];
  additional_skills_match: ComparisonSkillMatch[];
  experience_verification: ComparisonExperienceVerification | null;
  processing_time_ms: number;
  error?: string;
}

/**
 * Ответ данных матрицы сравнения
 */
export interface ComparisonMatrixData {
  vacancy_title: string;
  comparison_results: ResumeComparisonResult[];
  total_resumes: number;
  processing_time_ms: number;
}

/**
 * Запрос создания сравнения
 */
export interface ComparisonCreate {
  vacancy_id: string;
  resume_ids: string[];
  name?: string;
  filters?: Record<string, unknown>;
  created_by?: string;
  shared_with?: string[];
}

/**
 * Запрос обновления сравнения
 */
export interface ComparisonUpdate {
  name?: string;
  filters?: Record<string, unknown>;
  shared_with?: string[];
}

/**
 * Ответ сравнения
 */
export interface ComparisonResponse {
  id: string;
  vacancy_id: string;
  resume_ids: string[];
  name?: string;
  filters?: Record<string, unknown>;
  created_by?: string;
  shared_with?: string[];
  comparison_results?: ResumeComparisonResult[];
  created_at: string;
  updated_at: string;
}

/**
 * Ответ списка сравнений
 */
export interface ComparisonListResponse {
  comparisons: ComparisonResponse[];
  total_count: number;
  filters_applied?: {
    vacancy_id?: string;
    created_by?: string;
    min_match_percentage?: number;
    max_match_percentage?: number;
    sort_by?: string;
    order?: string;
  };
}

/**
 * Запрос сравнения нескольких резюме
 */
export interface CompareMultipleRequest {
  vacancy_id: string;
  resume_ids: string[];
}

// ==================== Типы аналитики ====================

/**
 * Метрики времени найма из backend
 */
export interface TimeToHireMetrics {
  average_days: number;
  median_days: number;
  min_days: number;
  max_days: number;
  percentile_25: number;
  percentile_75: number;
}

/**
 * Метрики обработки резюме из backend
 */
export interface ResumeMetrics {
  total_processed: number;
  processed_this_month: number;
  processed_this_week: number;
  processing_rate_avg: number;
}

/**
 * Метрики процента совпадений из backend
 */
export interface MatchRateMetrics {
  overall_match_rate: number;
  high_confidence_matches: number;
  low_confidence_matches: number;
  average_confidence: number;
}

/**
 * Ответ ключевых метрик из backend
 */
export interface KeyMetricsResponse {
  time_to_hire: TimeToHireMetrics;
  resumes: ResumeMetrics;
  match_rates: MatchRateMetrics;
}

/**
 * Интерфейс этапа воронки из backend
 */
export interface FunnelStage {
  stage_name: string;
  count: number;
  conversion_rate: number;
}

/**
 * Ответ метрик воронки из backend
 */
export interface FunnelMetricsResponse {
  stages: FunnelStage[];
  total_resumes: number;
  overall_hire_rate: number;
}

/**
 * Интерфейс элемента спроса навыков из backend
 */
export interface SkillDemandItem {
  skill_name: string;
  demand_count: number;
  demand_percentage: number;
  trend_percentage: number;
}

/**
 * Ответ спроса навыков из backend
 */
export interface SkillDemandResponse {
  skills: SkillDemandItem[];
  total_postings_analyzed: number;
}

/**
 * Интерфейс элемента отслеживания источников из backend
 */
export interface SourceTrackingItem {
  source_name: string;
  vacancy_count: number;
  percentage: number;
  average_time_to_fill: number;
}

/**
 * Ответ отслеживания источников из backend
 */
export interface SourceTrackingResponse {
  sources: SourceTrackingItem[];
  total_vacancies: number;
}

/**
 * Метрики производительности отдельного рекрутера
 */
export interface RecruiterPerformanceItem {
  recruiter_id: string;
  recruiter_name: string;
  hires: number;
  interviews_conducted: number;
  resumes_processed: number;
  average_time_to_hire: number;
  offer_acceptance_rate: number;
  candidate_satisfaction_score: number;
}

/**
 * Ответ производительности рекрутера из backend
 */
export interface RecruiterPerformanceResponse {
  recruiters: RecruiterPerformanceItem[];
  total_recruiters: number;
  period_start_date: string;
  period_end_date: string;
}

/**
 * Запрос обновления языковых предпочтений
 */
export interface LanguagePreferenceUpdate {
  language: string;
}

/**
 * Ответ языковых предпочтений
 */
export interface LanguagePreferenceResponse {
  language: string;
  updated_at: string;
}
