import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

import AuthGuard from './components/auth/AuthGuard';
import MapPage from './pages/MapPage';
import ListPage from './pages/ListPage';
import PlanForTodayPage from './pages/PlanForTodayPage';

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
        {/* Map is the hero surface per design doc §3. */}
        <Route path="/" element={<Navigate to="/map" replace />} />
        <Route
          path="/map"
          element={
            <AuthGuard>
              <MapPage />
            </AuthGuard>
          }
        />
        <Route
          path="/list"
          element={
            <AuthGuard>
              <ListPage />
            </AuthGuard>
          }
        />
        <Route
          path="/plan"
          element={
            <AuthGuard>
              <PlanForTodayPage />
            </AuthGuard>
          }
        />
        {/* Legacy routes removed in M15 (CountiesPage, LeadReviewPage, etc).
            Any old bookmark redirects to /map. */}
        <Route path="*" element={<Navigate to="/map" replace />} />
      </Routes>
    </>
  );
}

export default App;
