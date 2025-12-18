import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/apiService';
import { DatasetListItem } from '../types';
import { 
  Clock, 
  FileSpreadsheet, 
  Users, 
  LayoutGrid, 
  Trash2, 
  ChevronRight,
  RefreshCw,
  Search,
  CheckCircle,
  AlertTriangle,
  XCircle
} from 'lucide-react';

const PreviousAnalyses: React.FC = () => {
  const [datasets, setDatasets] = useState<DatasetListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const navigate = useNavigate();

  const loadDatasets = async () => {
    setLoading(true);
    try {
      const data = await apiService.listDatasets();
      setDatasets(data);
    } catch (err) {
      console.error('Failed to load datasets:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDatasets();
  }, []);

  const handleSelect = async (dataset: DatasetListItem) => {
    try {
      const fullData = await apiService.getDataset(dataset.id);
      localStorage.setItem('currentDatasetId', fullData.id);
      localStorage.setItem('currentDatasetMeta', JSON.stringify(fullData));
      navigate('/overview');
    } catch (err) {
      console.error('Failed to load dataset:', err);
      alert('Could not load dataset. The file may have been deleted.');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await apiService.deleteDataset(id);
      setDatasets(datasets.filter(d => d.id !== id));
      setDeleteConfirm(null);
    } catch (err) {
      console.error('Failed to delete dataset:', err);
      alert('Delete operation failed.');
    }
  };

  const getStatusIcon = (status: string | null) => {
    switch (status) {
      case 'green':
        return <CheckCircle className="text-green-500" size={20} />;
      case 'yellow':
        return <AlertTriangle className="text-amber-500" size={20} />;
      case 'red':
        return <XCircle className="text-red-500" size={20} />;
      default:
        return <Clock className="text-gray-400" size={20} />;
    }
  };

  const getStatusLabel = (status: string | null) => {
    switch (status) {
      case 'green':
        return 'Digital Twin Ready';
      case 'yellow':
        return 'Needs Attention';
      case 'red':
        return 'Not Ready';
      default:
        return 'Unknown';
    }
  };

  const filteredDatasets = datasets.filter(d => 
    d.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center">
              <Clock className="mr-3 text-blue-600" />
              Previous Analyses
            </h1>
            <p className="text-gray-500 mt-1">
              Access your previously uploaded SAV file analyses
            </p>
          </div>
          <button
            onClick={loadDatasets}
            className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-4 top-3 text-gray-400" size={20} />
          <input
            type="text"
            placeholder="Search by filename..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
          />
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-20">
            <RefreshCw className="animate-spin mx-auto mb-4 text-blue-600" size={40} />
            <p className="text-gray-500">Loading analyses...</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && datasets.length === 0 && (
          <div className="text-center py-20 bg-white rounded-2xl border border-gray-100 shadow-sm">
            <FileSpreadsheet className="mx-auto mb-4 text-gray-300" size={60} />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">No analyses yet</h3>
            <p className="text-gray-500 mb-6">
              Get started by uploading your first SAV file
            </p>
            <button
              onClick={() => navigate('/')}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Upload File
            </button>
          </div>
        )}

        {/* Dataset List */}
        {!loading && filteredDatasets.length > 0 && (
          <div className="space-y-4">
            {filteredDatasets.map((dataset) => (
              <div
                key={dataset.id}
                className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all overflow-hidden"
              >
                <div className="p-6 flex items-center justify-between">
                  <div className="flex items-center space-x-6 flex-1">
                    {/* Status Icon */}
                    <div className="flex-shrink-0">
                      {getStatusIcon(dataset.digitalTwinReadiness)}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-gray-900 truncate text-lg">
                        {dataset.filename}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {formatDate(dataset.createdAt)}
                      </p>
                    </div>

                    {/* Stats */}
                    <div className="hidden md:flex items-center space-x-8">
                      <div className="text-center">
                        <div className="flex items-center text-gray-500 text-sm mb-1">
                          <Users size={14} className="mr-1" />
                          <span>Respondents</span>
                        </div>
                        <span className="font-bold text-gray-900">{dataset.nRows?.toLocaleString()}</span>
                      </div>
                      <div className="text-center">
                        <div className="flex items-center text-gray-500 text-sm mb-1">
                          <LayoutGrid size={14} className="mr-1" />
                          <span>Variables</span>
                        </div>
                        <span className="font-bold text-gray-900">{dataset.nCols?.toLocaleString()}</span>
                      </div>
                      <div className="text-center">
                        <div className="text-gray-500 text-sm mb-1">Quality Score</div>
                        <span className={`font-bold ${
                          (dataset.dataQualityScore || 0) >= 80 ? 'text-green-600' :
                          (dataset.dataQualityScore || 0) >= 60 ? 'text-amber-600' : 'text-red-600'
                        }`}>
                          {dataset.dataQualityScore?.toFixed(0) || '-'}%
                        </span>
                      </div>
                      <div className="text-center min-w-[120px]">
                        <div className="text-gray-500 text-sm mb-1">Digital Twin</div>
                        <span className={`text-sm font-medium px-2 py-1 rounded-full ${
                          dataset.digitalTwinReadiness === 'green' ? 'bg-green-100 text-green-700' :
                          dataset.digitalTwinReadiness === 'yellow' ? 'bg-amber-100 text-amber-700' :
                          dataset.digitalTwinReadiness === 'red' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {getStatusLabel(dataset.digitalTwinReadiness)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2 ml-6">
                    {deleteConfirm === dataset.id ? (
                      <>
                        <button
                          onClick={() => handleDelete(dataset.id)}
                          className="px-3 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700"
                        >
                          Confirm
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(null)}
                          className="px-3 py-2 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => setDeleteConfirm(dataset.id)}
                          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={18} />
                        </button>
                        <button
                          onClick={() => handleSelect(dataset)}
                          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                        >
                          <span>View</span>
                          <ChevronRight size={18} />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* No Results */}
        {!loading && datasets.length > 0 && filteredDatasets.length === 0 && (
          <div className="text-center py-12 bg-white rounded-2xl border border-gray-100">
            <Search className="mx-auto mb-4 text-gray-300" size={40} />
            <p className="text-gray-500">No results found for "{searchTerm}"</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PreviousAnalyses;
