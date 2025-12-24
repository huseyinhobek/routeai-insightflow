import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileType, AlertCircle, Loader2, Clock, ChevronRight, BarChart2, LogOut } from 'lucide-react';
import { apiService } from '../services/apiService';
import { DatasetListItem } from '../types';
import { useAuth } from '../contexts/AuthContext';

const UploadPage: React.FC = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentDatasets, setRecentDatasets] = useState<DatasetListItem[]>([]);
  const [loadingRecent, setLoadingRecent] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  useEffect(() => {
    loadRecentDatasets();
  }, []);

  const loadRecentDatasets = async () => {
    try {
      const datasets = await apiService.listDatasets();
      setRecentDatasets(datasets.slice(0, 5)); // Show last 5
    } catch (err) {
      console.error('Failed to load recent datasets:', err);
    } finally {
      setLoadingRecent(false);
    }
  };

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.sav')) {
      setError('Please upload a valid SPSS (.sav) file.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const dataset = await apiService.uploadDataset(file);
      localStorage.setItem('currentDatasetId', dataset.id);
      localStorage.setItem('currentDatasetMeta', JSON.stringify(dataset));
      navigate('/overview');
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Upload failed. Is the backend running?');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectRecent = async (dataset: DatasetListItem) => {
    try {
      const fullData = await apiService.getDataset(dataset.id);
      localStorage.setItem('currentDatasetId', fullData.id);
      localStorage.setItem('currentDatasetMeta', JSON.stringify(fullData));
      navigate('/overview');
    } catch (err) {
      console.error('Failed to load dataset:', err);
      setError('Could not load dataset. The file may have been deleted.');
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => setIsDragging(false);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const getStatusBadge = (status: string | null) => {
    switch (status) {
      case 'green':
        return <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">Ready</span>;
      case 'yellow':
        return <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">Caution</span>;
      case 'red':
        return <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700">Not Ready</span>;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
      {/* Top Bar - User Info & Logout */}
      {user && (
        <div className="max-w-4xl mx-auto flex justify-end mb-4">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3 bg-white px-4 py-2 rounded-lg border border-gray-200 shadow-sm">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-semibold text-sm">
                {user.name?.charAt(0).toUpperCase() || user.email.charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">{user.name || 'User'}</p>
                <p className="text-xs text-gray-500">{user.email}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-gray-200 bg-white shadow-sm"
            >
              <LogOut size={18} />
              <span className="font-medium">Sign Out</span>
            </button>
          </div>
        </div>
      )}

      <div className="max-w-4xl mx-auto py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center p-3 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl shadow-lg shadow-blue-200 mb-6">
            <BarChart2 className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-extrabold text-gray-900 mb-3 tracking-tight">
            SAV Insight Studio
          </h1>
          <p className="text-lg text-gray-500 max-w-xl mx-auto">
            Analyze your SPSS datasets, measure data quality, and evaluate digital twin readiness.
          </p>
        </div>

        {/* Upload Area */}
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`
            relative group cursor-pointer
            border-2 border-dashed rounded-3xl p-12
            flex flex-col items-center justify-center text-center
            transition-all duration-300 ease-in-out
            bg-white shadow-sm hover:shadow-lg
            ${isDragging ? 'border-blue-500 bg-blue-50 scale-[1.02]' : 'border-gray-300 hover:border-blue-400'}
            ${isLoading ? 'opacity-50 pointer-events-none' : ''}
          `}
        >
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".sav"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />

          <div className="bg-gradient-to-br from-blue-100 to-indigo-100 p-5 rounded-full mb-6 group-hover:from-blue-200 group-hover:to-indigo-200 transition-colors">
            {isLoading ? (
              <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
            ) : (
              <UploadCloud className="w-10 h-10 text-blue-600" />
            )}
          </div>

          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            {isLoading ? 'Analyzing File...' : 'Click or drag a .sav file here'}
          </h3>
          <p className="text-sm text-gray-500 max-w-sm mx-auto">
            Supported format: SPSS Statistics Data Document (.sav). 
            Recommended maximum size: 100MB.
          </p>

          {!isLoading && (
            <div className="mt-8 flex items-center space-x-2 text-sm text-gray-400">
              <FileType size={16} />
              <span>Secure processing - your data is uploaded to the server</span>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
            <div>
              <h4 className="font-semibold text-red-900">Upload Failed</h4>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Recent Datasets */}
        {!loadingRecent && recentDatasets.length > 0 && (
          <div className="mt-12">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900 flex items-center">
                <Clock className="mr-2 text-gray-400" size={20} />
                Recent Analyses
              </h2>
              <button
                onClick={() => navigate('/history')}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center"
              >
                View All
                <ChevronRight size={16} />
              </button>
            </div>
            
            <div className="space-y-3">
              {recentDatasets.map((dataset) => (
                <div
                  key={dataset.id}
                  onClick={() => handleSelectRecent(dataset)}
                  className="bg-white p-4 rounded-xl border border-gray-100 hover:border-blue-200 hover:shadow-md cursor-pointer transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center space-x-4">
                    <div className="p-2 bg-gray-100 rounded-lg group-hover:bg-blue-100 transition-colors">
                      <FileType className="text-gray-500 group-hover:text-blue-600" size={20} />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{dataset.filename}</h3>
                      <p className="text-xs text-gray-500">
                        {dataset.nRows?.toLocaleString()} respondents • {dataset.nCols} variables
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    {getStatusBadge(dataset.digitalTwinReadiness)}
                    <ChevronRight className="text-gray-400 group-hover:text-blue-600" size={20} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Features */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-6">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-green-100 rounded-xl mb-4">
              <span className="text-2xl">📊</span>
            </div>
            <h3 className="font-bold text-gray-900 mb-2">Data Quality Analysis</h3>
            <p className="text-sm text-gray-500">
              Comprehensive quality report with missing data, consistency, and validity checks
            </p>
          </div>
          <div className="text-center p-6">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 rounded-xl mb-4">
              <span className="text-2xl">🤖</span>
            </div>
            <h3 className="font-bold text-gray-900 mb-2">Digital Twin Assessment</h3>
            <p className="text-sm text-gray-500">
              Automatic evaluation of your data's suitability for digital twin creation
            </p>
          </div>
          <div className="text-center p-6">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-purple-100 rounded-xl mb-4">
              <span className="text-2xl">✨</span>
            </div>
            <h3 className="font-bold text-gray-900 mb-2">AI-Powered Filters</h3>
            <p className="text-sm text-gray-500">
              Smart segmentation and filter suggestions powered by Native AI
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadPage;
