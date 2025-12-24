import React from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import VerifyPage from './pages/VerifyPage';
import SetPasswordPage from './pages/SetPasswordPage';
import UploadPage from './pages/UploadPage';
import DatasetOverview from './pages/DatasetOverview';
import VariableExplorer from './pages/VariableExplorer';
import SmartFilters from './pages/SmartFilters';
import Exports from './pages/Exports';
import PreviousAnalyses from './pages/PreviousAnalyses';
import QualityReport from './pages/QualityReport';
import TwinTransformer from './pages/TwinTransformer';
import AdminPage from './pages/AdminPage';
import AuditLogPage from './pages/AuditLogPage';
import SuperAdminPage from './pages/SuperAdminPage';
import ChangePasswordPage from './pages/ChangePasswordPage';

const App: React.FC = () => {
  return (
    <AuthProvider>
      <HashRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/verify" element={<VerifyPage />} />
          <Route path="/set-password" element={<SetPasswordPage />} />
          
          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/change-password" element={<ChangePasswordPage />} />
            <Route path="/" element={<UploadPage />} />
            <Route path="/history" element={<PreviousAnalyses />} />
            <Route element={<Layout />}>
              <Route path="/overview" element={<DatasetOverview />} />
              <Route path="/quality" element={<QualityReport />} />
              <Route path="/variables" element={<VariableExplorer />} />
              <Route path="/filters" element={<SmartFilters />} />
              <Route path="/twin-transformer" element={<TwinTransformer />} />
              <Route path="/exports" element={<Exports />} />
            </Route>
            
            {/* Admin routes - require admin role */}
            <Route element={<ProtectedRoute requiredRoles={['super_admin', 'org_admin']} />}>
              <Route path="/admin" element={<AdminPage />} />
              <Route path="/admin/audit" element={<AuditLogPage />} />
            </Route>
            
            {/* Super Admin route - require super_admin role */}
            <Route element={<ProtectedRoute requiredRoles={['super_admin']} />}>
              <Route path="/super-admin" element={<SuperAdminPage />} />
            </Route>
          </Route>
        </Routes>
      </HashRouter>
    </AuthProvider>
  );
};

export default App;
