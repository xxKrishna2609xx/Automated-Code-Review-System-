import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from '@/components/layout/Sidebar';
import DashboardPage from '@/pages/DashboardPage';
import PullRequestsPage from '@/pages/PullRequestsPage';
import PRDetailPage from '@/pages/PRDetailPage';
import AIReviewPage from '@/pages/AIReviewPage';
import AnalyticsPage from '@/pages/AnalyticsPage';
import RepositoriesPage from '@/pages/RepositoriesPage';
import RepositoryDetailPage from '@/pages/RepositoryDetailPage';
import SettingsPage from '@/pages/SettingsPage';

export default function App() {
  return (
    <Router>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'auto 1fr',
          minHeight: '100vh',
        }}
      >
        <Sidebar />
        <main style={{ minWidth: 0, width: '100%' }}>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/reviews" element={<PullRequestsPage />} />
            <Route path="/reviews/:id" element={<PRDetailPage />} />
            <Route path="/reviews/:id/review" element={<AIReviewPage />} />
            <Route path="/pull-requests" element={<PullRequestsPage />} />
            <Route path="/pull-requests/:id" element={<PRDetailPage />} />
            <Route path="/pull-requests/:id/review" element={<AIReviewPage />} />
            <Route path="/repositories" element={<RepositoriesPage />} />
            <Route path="/repositories/:id" element={<RepositoryDetailPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
