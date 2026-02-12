import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from '@components/Layout';
import HomePage from '@pages/Home';
import UploadPage from '@pages/Upload';
import ResultsPage from '@pages/Results';
import ComparePage from '@pages/Compare';
import CompareVacancyPage from '@pages/CompareVacancy';
import AdminSynonymsPage from '@pages/AdminSynonyms';
import AdminAnalyticsPage from '@pages/AdminAnalytics';
import AnalyticsDashboardPage from '@pages/AnalyticsDashboard';
import VacancyListPage from '@pages/VacancyList';
import CreateVacancyPage from '@pages/CreateVacancy';
import VacancyDetailsPage from '@pages/VacancyDetails';
import ApplicationsPage from '@pages/Applications';
import ResumeDatabasePage from '@pages/ResumeDatabase';
import CandidateSearchPage from '@pages/CandidateSearch';
import RecruiterDashboardPage from '@pages/RecruiterDashboard';

/**
 * Главный компонент приложения
 *
 * Настраивает React Router со всеми маршрутами приложения.
 * Использует компонент Layout для обеспечения последовательной навигации и структуры.
 */
function App() {

  return (
    <BrowserRouter>
      <Routes>
        {/* Корневой маршрут с Layout */}
        <Route path="/" element={<Layout />}>
          {/* Главная страница по умолчанию */}
          <Route index element={<HomePage />} />

          {/* Устаревшие маршруты - сохранены для совместимости */}
          <Route path="upload" element={<UploadPage />} />
          <Route path="results/:id" element={<ResultsPage />} />
          <Route path="compare/:resumeId/:vacancyId" element={<ComparePage />} />
          <Route path="compare-vacancy/:vacancyId" element={<CompareVacancyPage />} />

          {/* Маршруты модуля соискателя */}
          <Route path="jobs">
            <Route index element={<VacancyListPage />} />
            <Route path="upload" element={<UploadPage />} />
            <Route path="results/:id" element={<ResultsPage />} />
            <Route path="applications" element={<ApplicationsPage />} />
          </Route>

          {/* Маршруты модуля рекрутера */}
          <Route path="recruiter">
            <Route index element={<RecruiterDashboardPage />} />
            <Route path="vacancies">
              <Route index element={<VacancyListPage />} />
              <Route path="create" element={<CreateVacancyPage />} />
              <Route path=":id" element={<VacancyDetailsPage />} />
            </Route>
            <Route path="compare/:resumeId/:vacancyId" element={<ComparePage />} />
            <Route path="resumes" element={<ResumeDatabasePage />} />
            <Route path="search" element={<CandidateSearchPage />} />
            <Route path="analytics" element={<AnalyticsDashboardPage />} />
          </Route>

          {/* Страницы администратора */}
          <Route path="admin" element={<Navigate to="/admin/synonyms" replace />} />
          <Route path="admin/synonyms" element={<AdminSynonymsPage />} />
          <Route path="admin/analytics" element={<AdminAnalyticsPage />} />

          {/* Панель аналитики */}
          <Route path="analytics" element={<AnalyticsDashboardPage />} />

          {/* Перехватывающий маршрут - перенаправление на главную */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
