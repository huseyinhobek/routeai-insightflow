import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  History, ChevronLeft, ChevronRight, Filter, RefreshCw, Loader2,
  User, Database, Cog, Download, Play, Pause, LogIn, LogOut, UserPlus
} from 'lucide-react';
import { adminService, AuditLogItem } from '../services/adminService';

const ACTION_ICONS: Record<string, React.ReactNode> = {
  'user.login': <LogIn className="w-4 h-4 text-green-600" />,
  'user.logout': <LogOut className="w-4 h-4 text-gray-600" />,
  'user.login_failed': <LogIn className="w-4 h-4 text-red-600" />,
  'user.invite': <UserPlus className="w-4 h-4 text-blue-600" />,
  'user.update': <User className="w-4 h-4 text-amber-600" />,
  'user.delete': <User className="w-4 h-4 text-red-600" />,
  'dataset.upload': <Database className="w-4 h-4 text-green-600" />,
  'dataset.delete': <Database className="w-4 h-4 text-red-600" />,
  'dataset.export': <Download className="w-4 h-4 text-blue-600" />,
  'transform.start': <Play className="w-4 h-4 text-green-600" />,
  'transform.pause': <Pause className="w-4 h-4 text-amber-600" />,
  'transform.resume': <Play className="w-4 h-4 text-blue-600" />,
  'transform.export': <Download className="w-4 h-4 text-purple-600" />,
  'smart_filter.generate': <Cog className="w-4 h-4 text-indigo-600" />,
  'org.settings_change': <Cog className="w-4 h-4 text-amber-600" />,
};

const ACTION_LABELS: Record<string, string> = {
  'user.login': 'User Login',
  'user.logout': 'User Logout',
  'user.login_failed': 'Failed Login',
  'user.magic_link_requested': 'Magic Link İstendi',
  'user.invite': 'User Invited',
  'user.update': 'User Updated',
  'user.delete': 'User Deleted',
  'dataset.upload': 'Dataset Yüklendi',
  'dataset.delete': 'Dataset Deleted',
  'dataset.export': 'Dataset Export',
  'transform.start': 'Dönüşüm Başlatıldı',
  'transform.pause': 'Dönüşüm Duraklatıldı',
  'transform.resume': 'Dönüşüm Devam Etti',
  'transform.export': 'Dönüşüm Export',
  'smart_filter.generate': 'Smart Filter Oluşturuldu',
  'org.settings_change': 'Org Ayarları Değişti',
  'org.create': 'Organization Created',
};

const AuditLogPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [limit] = useState(25);
  const [isLoading, setIsLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [availableActions, setAvailableActions] = useState<string[]>([]);

  useEffect(() => {
    loadActions();
  }, []);

  useEffect(() => {
    loadLogs();
  }, [offset, actionFilter]);

  const loadActions = async () => {
    const actions = await adminService.getAuditLogActions();
    setAvailableActions(actions);
  };

  const loadLogs = async () => {
    setIsLoading(true);
    try {
      const result = await adminService.getAuditLogs({
        offset,
        limit,
        action: actionFilter || undefined,
      });
      setLogs(result.logs);
      setTotal(result.total);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  const goToPage = (page: number) => {
    setOffset((page - 1) * limit);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('tr-TR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const renderMeta = (meta: Record<string, any> | null) => {
    if (!meta) return null;
    
    const entries = Object.entries(meta).filter(([k, v]) => v !== null && v !== undefined);
    if (entries.length === 0) return null;

    return (
      <div className="mt-2 flex flex-wrap gap-2">
        {entries.slice(0, 3).map(([key, value]) => (
          <span key={key} className="text-xs bg-gray-100 px-2 py-1 rounded">
            <span className="text-gray-500">{key}:</span>{' '}
            <span className="text-gray-700">
              {typeof value === 'object' ? JSON.stringify(value) : String(value).slice(0, 30)}
            </span>
          </span>
        ))}
        {entries.length > 3 && (
          <span className="text-xs text-gray-500">+{entries.length - 3} more</span>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/admin" className="p-2 hover:bg-white rounded-lg transition-colors">
              <ChevronLeft className="w-5 h-5 text-gray-600" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <History className="w-6 h-6" />
                Denetim Kayıtları
              </h1>
              <p className="text-gray-500">Sistem aktivitelerinin kronolojik kaydı</p>
            </div>
          </div>
          <button
            onClick={() => loadLogs()}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Yenile
          </button>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-6">
          <div className="flex items-center gap-4">
            <Filter className="w-5 h-5 text-gray-400" />
            <select
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setOffset(0);
              }}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Tüm Aksiyonlar</option>
              {availableActions.map((action) => (
                <option key={action} value={action}>
                  {ACTION_LABELS[action] || action}
                </option>
              ))}
            </select>
            <span className="text-sm text-gray-500">
              Toplam {total} kayıt
            </span>
          </div>
        </div>

        {/* Logs Table */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center py-12">
              <History className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Henüz denetim kaydı bulunmuyor</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tarih</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Aksiyon</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Varlık</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">IP</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {logs.map((log) => (
                      <tr key={log.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(log.created_at)}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            {ACTION_ICONS[log.action] || <Cog className="w-4 h-4 text-gray-400" />}
                            <span className="font-medium text-gray-900">
                              {ACTION_LABELS[log.action] || log.action}
                            </span>
                          </div>
                          {renderMeta(log.meta_json)}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-700">
                          {log.user_email || <span className="text-gray-400">-</span>}
                        </td>
                        <td className="px-6 py-4 text-sm">
                          {log.entity_type ? (
                            <div>
                              <span className="text-gray-700">{log.entity_type}</span>
                              {log.entity_id && (
                                <span className="text-gray-400 text-xs ml-1">
                                  ({log.entity_id.slice(0, 8)}...)
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500 font-mono">
                          {log.ip_address || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
                  <p className="text-sm text-gray-500">
                    Sayfa {currentPage} / {totalPages}
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => goToPage(currentPage - 1)}
                      disabled={currentPage === 1}
                      className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let page: number;
                      if (totalPages <= 5) {
                        page = i + 1;
                      } else if (currentPage <= 3) {
                        page = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        page = totalPages - 4 + i;
                      } else {
                        page = currentPage - 2 + i;
                      }
                      return (
                        <button
                          key={page}
                          onClick={() => goToPage(page)}
                          className={`px-3 py-1 rounded-lg text-sm ${
                            currentPage === page
                              ? 'bg-blue-600 text-white'
                              : 'hover:bg-gray-100 text-gray-700'
                          }`}
                        >
                          {page}
                        </button>
                      );
                    })}
                    <button
                      onClick={() => goToPage(currentPage + 1)}
                      disabled={currentPage === totalPages}
                      className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default AuditLogPage;

