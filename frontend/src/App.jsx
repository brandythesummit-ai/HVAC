import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import CountiesPage from './pages/CountiesPage';
import LeadsPage from './pages/LeadsPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/counties" replace />} />
        <Route path="counties" element={<CountiesPage />} />
        <Route path="leads" element={<LeadsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

export default App;
