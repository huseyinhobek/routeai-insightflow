import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Edit, Trash2, Users, RefreshCw, Copy, Check } from 'lucide-react';
import apiService from '../services/apiService';

interface Audience {
  id: string;
  dataset_id: string;
  name: string;
  description?: string;
  size_n?: number;
  created_at?: string;
  updated_at?: string;
}

const AudiencesPage: React.FC = () => {
  const navigate = useNavigate();
  const [audiences, setAudiences] = useState<Audience[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingAudience, setEditingAudience] = useState<Audience | null>(null);
  const [copySuccess, setCopySuccess] = useState<string | null>(null);

  useEffect(() => {
    // Get dataset ID from localStorage
    const storedDatasetId = localStorage.getItem('currentDatasetId');
    if (storedDatasetId) {
      setDatasetId(storedDatasetId);
      loadAudiences(storedDatasetId);
    } else {
      setError('Veri seti seçilmedi. Lütfen önce bir veri seti yükleyin.');
      setLoading(false);
    }
  }, []);

  const loadAudiences = async (dsId: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.listAudiences(dsId);
      setAudiences(data);
    } catch (err: any) {
      setError(err.message || 'Audience listesi yüklenirken hata oluştu');
      console.error('Error loading audiences:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingAudience(null);
    setShowCreateModal(true);
  };

  const handleEdit = (audience: Audience) => {
    setEditingAudience(audience);
    setShowCreateModal(true);
  };

  const handleDelete = async (audienceId: string) => {
    if (!window.confirm('Bu audience\'ı silmek istediğinize emin misiniz?')) {
      return;
    }

    try {
      await apiService.deleteAudience(audienceId);
      if (datasetId) {
        loadAudiences(datasetId);
      }
    } catch (err: any) {
      alert('Silme hatası: ' + (err.message || 'Bilinmeyen hata'));
      console.error('Error deleting audience:', err);
    }
  };

  const handleRefreshMembership = async (audienceId: string) => {
    try {
      await apiService.refreshAudienceMembership(audienceId);
      if (datasetId) {
        loadAudiences(datasetId);
      }
      alert('Membership başarıyla yenilendi');
    } catch (err: any) {
      alert('Yenileme hatası: ' + (err.message || 'Bilinmeyen hata'));
      console.error('Error refreshing membership:', err);
    }
  };

  const handleCopyShareToken = async (audience: Audience) => {
    try {
      const fullAudience = await apiService.getAudience(audience.id);
      const shareToken = fullAudience.share_token;
      if (shareToken) {
        await navigator.clipboard.writeText(shareToken);
        setCopySuccess(audience.id);
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
                <Users className="w-8 h-8 text-purple-600" />
                Audiences
              </h1>
              <p className="text-gray-600 mt-2">Segment tanımlarınızı yönetin</p>
            </div>
            <button
              onClick={handleCreate}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 flex items-center gap-2 transition-colors"
            >
              <Plus className="w-5 h-5" />
              Yeni Audience
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Audiences Table */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    İsim
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Açıklama
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Boyut
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
                {audiences.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      Henüz audience tanımlanmamış. Yeni bir audience oluşturun.
                    </td>
                  </tr>
                ) : (
                  audiences.map((audience) => (
                    <tr key={audience.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{audience.name}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-500">
                          {audience.description || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 flex items-center gap-2">
                          <Users className="w-4 h-4 text-gray-400" />
                          {audience.size_n !== undefined ? audience.size_n.toLocaleString('tr-TR') : '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">
                          {formatDate(audience.updated_at)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end items-center gap-2">
                          <button
                            onClick={() => handleRefreshMembership(audience.id)}
                            className="text-blue-600 hover:text-blue-900 p-2 hover:bg-blue-50 rounded"
                            title="Membership'i Yenile"
                          >
                            <RefreshCw className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleCopyShareToken(audience)}
                            className="text-green-600 hover:text-green-900 p-2 hover:bg-green-50 rounded"
                            title="Share Token Kopyala"
                          >
                            {copySuccess === audience.id ? (
                              <Check className="w-4 h-4" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            onClick={() => handleEdit(audience)}
                            className="text-purple-600 hover:text-purple-900 p-2 hover:bg-purple-50 rounded"
                            title="Düzenle"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(audience.id)}
                            className="text-red-600 hover:text-red-900 p-2 hover:bg-red-50 rounded"
                            title="Sil"
                          >
                            <Trash2 className="w-4 h-4" />
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

        {/* Create/Edit Modal */}
        {showCreateModal && (
          <AudienceModal
            audience={editingAudience}
            datasetId={datasetId}
            onClose={() => {
              setShowCreateModal(false);
              setEditingAudience(null);
            }}
            onSave={() => {
              setShowCreateModal(false);
              setEditingAudience(null);
              if (datasetId) {
                loadAudiences(datasetId);
              }
            }}
          />
        )}
      </div>
    </div>
  );
};

// Audience Create/Edit Modal Component
interface AudienceModalProps {
  audience: Audience | null;
  datasetId: string | null;
  onClose: () => void;
  onSave: () => void;
}

const AudienceModal: React.FC<AudienceModalProps> = ({ audience, datasetId, onClose, onSave }) => {
  const [name, setName] = useState(audience?.name || '');
  const [description, setDescription] = useState(audience?.description || '');
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

      if (audience) {
        // Update existing audience
        await apiService.updateAudience(audience.id, { name, description });
      } else {
        // Create new audience - requires filter_json
        // For now, show a message - in production, integrate with smart filters UI
        setError('Yeni audience oluşturmak için filter_json gerekli. Lütfen Smart Filters sayfasından "Save as Audience" özelliğini kullanın.');
        return;
      }

      onSave();
    } catch (err: any) {
      setError(err.message || 'İşlem başarısız');
      console.error('Error saving audience:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          {audience ? 'Audience Düzenle' : 'Yeni Audience'}
        </h2>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              İsim *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
              required
            />
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Açıklama
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
              rows={3}
            />
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
              {loading ? 'Kaydediliyor...' : audience ? 'Güncelle' : 'Oluştur'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AudiencesPage;

