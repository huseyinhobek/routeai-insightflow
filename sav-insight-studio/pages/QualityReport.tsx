import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DatasetMeta, QualityReport as QualityReportType } from '../types';
import { 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  Users, 
  BarChart3, 
  TrendingUp,
  AlertOctagon,
  Lightbulb,
  Download,
  ArrowRight
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import { apiService } from '../services/apiService';

const QualityReportPage: React.FC = () => {
  const [meta, setMeta] = useState<DatasetMeta | null>(null);
  const [report, setReport] = useState<QualityReportType | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const stored = localStorage.getItem('currentDatasetMeta');
    if (!stored) {
      navigate('/');
      return;
    }
    const data = JSON.parse(stored);
    setMeta(data);
    
    if (data.qualityReport) {
      setReport(data.qualityReport);
    }
  }, [navigate]);

  const handleDownloadSummary = async () => {
    if (!meta) return;
    try {
      await apiService.downloadExport(meta.id, 'summary');
    } catch (err) {
      console.error('Download error:', err);
      alert('İndirme başarısız');
    }
  };

  if (!meta || !report) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-gray-500">Yükleniyor...</div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'green': return 'text-green-600 bg-green-100';
      case 'yellow': return 'text-amber-600 bg-amber-100';
      case 'red': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string, size = 24) => {
    switch (status) {
      case 'green': return <CheckCircle size={size} className="text-green-600" />;
      case 'yellow': return <AlertTriangle size={size} className="text-amber-600" />;
      case 'red': return <XCircle size={size} className="text-red-600" />;
      default: return null;
    }
  };

  const varQualityData = [
    { name: 'İyi', value: report.high_quality_vars, color: '#22C55E' },
    { name: 'Orta', value: report.medium_quality_vars, color: '#F59E0B' },
    { name: 'Düşük', value: report.low_quality_vars, color: '#EF4444' },
  ];

  const metricsData = report.metrics.map(m => ({
    name: m.name === 'Completeness' ? 'Tamlık' :
          m.name === 'Validity' ? 'Geçerlilik' :
          m.name === 'Consistency' ? 'Tutarlılık' :
          m.name === 'Transformation' ? 'Dönüşüm' : m.name,
    score: m.score,
    status: m.status
  }));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <BarChart3 className="mr-3 text-blue-600" />
            Veri Kalitesi Raporu
          </h1>
          <p className="text-gray-500 mt-1">{meta.filename}</p>
        </div>
        <button
          onClick={handleDownloadSummary}
          className="flex items-center space-x-2 bg-blue-600 text-white px-5 py-2.5 rounded-xl hover:bg-blue-700 transition-colors shadow-lg shadow-blue-200"
        >
          <Download size={18} />
          <span>Excel Özet İndir</span>
        </button>
      </div>

      {/* Digital Twin Readiness Banner */}
      <div className={`p-6 rounded-2xl ${
        report.digital_twin_readiness === 'green' ? 'bg-gradient-to-r from-green-500 to-emerald-600' :
        report.digital_twin_readiness === 'yellow' ? 'bg-gradient-to-r from-amber-500 to-orange-500' :
        'bg-gradient-to-r from-red-500 to-rose-600'
      } text-white shadow-lg`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-white/20 rounded-xl">
              {report.digital_twin_readiness === 'green' ? <CheckCircle size={32} /> :
               report.digital_twin_readiness === 'yellow' ? <AlertTriangle size={32} /> :
               <XCircle size={32} />}
            </div>
            <div>
              <h2 className="text-xl font-bold">Dijital İkiz Uygunluğu</h2>
              <p className="text-white/80 mt-1">
                {report.digital_twin_readiness === 'green' 
                  ? 'Bu veri seti dijital ikiz oluşturmak için UYGUN.' 
                  : report.digital_twin_readiness === 'yellow'
                  ? 'Bu veri seti işlenebilir ancak bazı konulara DİKKAT edilmeli.'
                  : 'Bu veri seti dijital ikiz için UYGUN DEĞİL. Önemli iyileştirmeler gerekli.'}
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-4xl font-bold">%{report.overall_score.toFixed(0)}</div>
            <div className="text-white/80 text-sm">Genel Skor</div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <Users className="text-blue-600" size={24} />
            <span className="text-xs font-bold text-gray-400 uppercase">Katılımcılar</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">{report.total_participants.toLocaleString()}</div>
          <div className="text-sm text-gray-500 mt-2">
            <span className="text-green-600 font-medium">{report.complete_responses}</span> tam yanıt
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <TrendingUp className="text-green-600" size={24} />
            <span className="text-xs font-bold text-gray-400 uppercase">Tamlık</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">%{report.completeness_score.toFixed(1)}</div>
          <div className="text-sm text-gray-500 mt-2">
            <span className="text-amber-600 font-medium">%{report.dropout_rate.toFixed(1)}</span> dropout
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <BarChart3 className="text-purple-600" size={24} />
            <span className="text-xs font-bold text-gray-400 uppercase">Değişkenler</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">{report.total_variables}</div>
          <div className="text-sm text-gray-500 mt-2">
            <span className="text-green-600 font-medium">{report.high_quality_vars}</span> kaliteli
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <CheckCircle className="text-teal-600" size={24} />
            <span className="text-xs font-bold text-gray-400 uppercase">Dönüşüm</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">%{report.transformation_score.toFixed(0)}</div>
          <div className="text-sm text-gray-500 mt-2">hazırlık skoru</div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quality Metrics Bar Chart */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Kalite Metrikleri</h3>
          <div className="h-64 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%" minHeight={256}>
              <BarChart data={metricsData} layout="vertical">
                <XAxis type="number" domain={[0, 100]} />
                <YAxis type="category" dataKey="name" width={80} />
                <Tooltip 
                  formatter={(value: number) => `%${value.toFixed(1)}`}
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                />
                <Bar 
                  dataKey="score" 
                  radius={[0, 4, 4, 0]}
                  fill="#2563EB"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Variable Quality Pie Chart */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Değişken Kalite Dağılımı</h3>
          <div className="h-64 w-full min-w-0 flex items-center">
            <ResponsiveContainer width="60%" height="100%" minHeight={256}>
              <PieChart>
                <Pie
                  data={varQualityData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {varQualityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-3">
              {varQualityData.map((item, i) => (
                <div key={i} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: item.color }} />
                    <span className="text-gray-600">{item.name}</span>
                  </div>
                  <span className="font-bold text-gray-900">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Issues and Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Critical Issues */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
            <AlertOctagon className="text-red-500 mr-2" size={20} />
            Kritik Sorunlar
          </h3>
          {report.critical_issues.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <CheckCircle size={40} className="mx-auto mb-2 text-green-400" />
              <p>Kritik sorun yok!</p>
            </div>
          ) : (
            <ul className="space-y-3">
              {report.critical_issues.map((issue, i) => (
                <li key={i} className="flex items-start space-x-2 text-sm">
                  <XCircle className="text-red-500 flex-shrink-0 mt-0.5" size={16} />
                  <span className="text-gray-700">{issue}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Warnings */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
            <AlertTriangle className="text-amber-500 mr-2" size={20} />
            Uyarılar
          </h3>
          {report.warnings.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <CheckCircle size={40} className="mx-auto mb-2 text-green-400" />
              <p>Uyarı yok!</p>
            </div>
          ) : (
            <ul className="space-y-3">
              {report.warnings.map((warning, i) => (
                <li key={i} className="flex items-start space-x-2 text-sm">
                  <AlertTriangle className="text-amber-500 flex-shrink-0 mt-0.5" size={16} />
                  <span className="text-gray-700">{warning}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Recommendations */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
            <Lightbulb className="text-blue-500 mr-2" size={20} />
            Öneriler
          </h3>
          {report.recommendations.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <p>Öneri yok</p>
            </div>
          ) : (
            <ul className="space-y-3">
              {report.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start space-x-2 text-sm">
                  <ArrowRight className="text-blue-500 flex-shrink-0 mt-0.5" size={16} />
                  <span className="text-gray-700">{rec}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Variable Quality Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-6 border-b border-gray-100">
          <h3 className="text-lg font-bold text-gray-900">Değişken Bazlı Kalite Analizi</h3>
          <p className="text-gray-500 text-sm mt-1">Düşük kaliteli değişkenler en üstte</p>
        </div>
        <div className="overflow-x-auto max-h-96">
          <table className="w-full">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="text-left px-6 py-3 text-xs font-bold text-gray-500 uppercase">Değişken</th>
                <th className="text-left px-6 py-3 text-xs font-bold text-gray-500 uppercase">Etiket</th>
                <th className="text-center px-6 py-3 text-xs font-bold text-gray-500 uppercase">Tamlık</th>
                <th className="text-center px-6 py-3 text-xs font-bold text-gray-500 uppercase">Durum</th>
                <th className="text-left px-6 py-3 text-xs font-bold text-gray-500 uppercase">Sorunlar</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[...report.variable_quality]
                .sort((a, b) => a.completeness - b.completeness)
                .slice(0, 50)
                .map((v, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-mono text-sm text-gray-900">{v.code}</td>
                  <td className="px-6 py-3 text-sm text-gray-600 max-w-xs truncate">{v.label}</td>
                  <td className="px-6 py-3 text-center">
                    <span className={`font-bold ${
                      v.completeness >= 90 ? 'text-green-600' :
                      v.completeness >= 70 ? 'text-amber-600' : 'text-red-600'
                    }`}>
                      %{v.completeness.toFixed(0)}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-center">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(v.status)}`}>
                      {v.status === 'green' ? 'İyi' : v.status === 'yellow' ? 'Orta' : 'Düşük'}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-sm text-gray-500">
                    {v.issues.length > 0 ? v.issues.join('; ') : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default QualityReportPage;

