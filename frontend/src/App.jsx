import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Layout from './components/Layout';
import CountiesPage from './pages/CountiesPage';
import LeadReviewPage from './pages/LeadReviewPage';
import PipelinePage from './pages/PipelinePage';
import SettingsPage from './pages/SettingsPage';

function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          success: {
            duration: 3000,
            style: { background: '#10b981', color: '#fff' },
          },
          error: {
            duration: 5000,
            style: { background: '#ef4444', color: '#fff' },
          },
        }}
      />
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/counties" replace />} />
          <Route path="counties" element={<CountiesPage />} />
          <Route path="leads" element={<LeadReviewPage />} />
          <Route path="pipeline" element={<PipelinePage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </>
  );
}

export default App;
