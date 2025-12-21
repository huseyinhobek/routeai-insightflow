import React from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import UploadPage from './pages/UploadPage';
import DatasetOverview from './pages/DatasetOverview';
import VariableExplorer from './pages/VariableExplorer';
import SmartFilters from './pages/SmartFilters';
import Exports from './pages/Exports';
import PreviousAnalyses from './pages/PreviousAnalyses';
import QualityReport from './pages/QualityReport';
import TwinTransformer from './pages/TwinTransformer';

const App: React.FC = () => {
  return (
    <HashRouter>
      <Routes>
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
      </Routes>
    </HashRouter>
  );
};

export default App;
