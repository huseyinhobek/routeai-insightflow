import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, MessageSquare, Search, Users, Clock, CheckCircle, XCircle, AlertCircle, Copy, Check } from 'lucide-react';
import apiService from '../services/apiService';

interface Thread {
  id: string;
  dataset_id: string;
  audience_id?: string;
  title: string;
  status: string;
  created_at?: string;
  updated_at?: string;
}

interface Audience {
  id: string;
  name: string;
}

const ThreadsPage: React.FC = () => {
  const navigate = useNavigate();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [audiences, setAudiences] = useState<Record<string, Audience>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [copySuccess, setCopySuccess] = useState<string | null>(null);

  useEffect(() => {
    // Get dataset ID from localStorage
    const storedDatasetId = localStorage.getItem('currentDatasetId');
    if (storedDatasetId) {
      setDatasetId(storedDatasetId);
      loadThreads(storedDatasetId);
      loadAudiences(storedDatasetId);
    } else {
      setError('Veri seti seçilmedi. Lütfen önce bir veri seti yükleyin.');
      setLoading(false);
    }
  }, []);

  const loadThreads = async (dsId: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.listThreads(dsId);
      setThreads(data);
    } catch (err: any) {
      setError(err.message || 'Thread listesi yüklenirken hata oluştu');
      console.error('Error loading threads:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadAudiences = async (dsId: string) => {
    try {
      const data = await apiService.listAudiences(dsId);
      const audienceMap: Record<string, Audience> = {};
      data.forEach((aud: any) => {
        audienceMap[aud.id] = { id: aud.id, name: aud.name };
      });
      setAudiences(audienceMap);
    } catch (err: any) {
      console.error('Error loading audiences:', err);
    }
  };

  const handleCreate = () => {
    setShowCreateModal(true);
  };

  const handleThreadClick = (threadId: string) => {
    navigate(`/threads/${threadId}`);
  };

  const handleCopyShareToken = async (thread: Thread) => {
    try {
      const fullThread = await apiService.getThread(thread.id);
      const shareToken = fullThread.share_token;
      if (shareToken) {
        await navigator.clipboard.writeText(shareToken);
        setCopySuccess(thread.id);
        setTimeout(() => setCopySuccess(null), 2000);
      }
    } catch (err: any) {
      alert('Token kopyalama hatası: ' + (err.message || 'Bilinmeyen hata'));
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('tr-TR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-600" />;
      case 'processing':
        return <Clock className="w-5 h-5 text-yellow-600 animate-spin" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'ready':
        return 'Hazır';
      case 'error':
        return 'Hata';
      case 'processing':
        return 'İşleniyor';
      default:
        return status;
    }
  };

  const filteredThreads = threads.filter(thread =>
    thread.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                <MessageSquare className="w-8 h-8 text-purple-600" />
                Threads
              </h1>
              <p className="text-gray-600 mt-2">Araştırma oturumlarınızı yönetin</p>
            </div>
            <button
              onClick={handleCreate}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 flex items-center gap-2 transition-colors"
            >
              <Plus className="w-5 h-5" />
              Yeni Thread
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Thread ara..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
            />
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Threads Table */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Başlık
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Audience
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Durum
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Güncelleme
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    İşlemler
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredThreads.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      {searchTerm ? 'Arama sonucu bulunamadı' : 'Henüz thread oluşturulmamış. Yeni bir thread oluşturun.'}
                    </td>
                  </tr>
                ) : (
                  filteredThreads.map((thread) => (
                    <tr
                      key={thread.id}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => handleThreadClick(thread.id)}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{thread.title}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500 flex items-center gap-2">
                          {thread.audience_id ? (
                            <>
                              <Users className="w-4 h-4 text-gray-400" />
                              {audiences[thread.audience_id]?.name || thread.audience_id}
                            </>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(thread.status)}
                          <span className="text-sm text-gray-900">{getStatusText(thread.status)}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">
                          {formatDate(thread.updated_at)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCopyShareToken(thread);
                            }}
                            className="text-green-600 hover:text-green-900 p-2 hover:bg-green-50 rounded"
                            title="Share Token Kopyala"
                          >
                            {copySuccess === thread.id ? (
                              <Check className="w-4 h-4" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Create Thread Modal */}
        {showCreateModal && (
          <ThreadCreateModal
            datasetId={datasetId}
            audiences={Object.values(audiences)}
            onClose={() => setShowCreateModal(false)}
            onSave={() => {
              setShowCreateModal(false);
              if (datasetId) {
                loadThreads(datasetId);
              }
            }}
          />
        )}
      </div>
    </div>
  );
};

// Thread Create Modal Component
interface ThreadCreateModalProps {
  datasetId: string | null;
  audiences: Audience[];
  onClose: () => void;
  onSave: () => void;
}

const ThreadCreateModal: React.FC<ThreadCreateModalProps> = ({ datasetId, audiences, onClose, onSave }) => {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [audienceId, setAudienceId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!datasetId) {
      setError('Dataset ID bulunamadı');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const data: any = {
        dataset_id: datasetId,
        title: title || `Thread ${new Date().toLocaleDateString('tr-TR')}`
      };

      if (audienceId) {
        data.audience_id = audienceId;
      }

      const newThread = await apiService.createThread(data);
      onSave();
      
      // Navigate to the new thread
      navigate(`/threads/${newThread.id}`);
    } catch (err: any) {
      setError(err.message || 'Thread oluşturulamadı');
      console.error('Error creating thread:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Yeni Thread</h2>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Başlık
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Thread başlığı (opsiyonel)"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
            />
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Audience (Opsiyonel)
            </label>
            <select
              value={audienceId}
              onChange={(e) => setAudienceId(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
            >
              <option value="">Audience seçin...</option>
              {audiences.map((aud) => (
                <option key={aud.id} value={aud.id}>
                  {aud.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              İptal
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
            >
              {loading ? 'Oluşturuluyor...' : 'Oluştur'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ThreadsPage;

