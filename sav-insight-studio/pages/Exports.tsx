import React, { useEffect, useState } from 'react';
import { apiService } from '../services/apiService';
import { FileSpreadsheet, FileJson, FileText, Download, ClipboardList, CheckCircle, Loader2 } from 'lucide-react';
import { DatasetMeta } from '../types';

const Exports: React.FC = () => {
  const [meta, setMeta] = useState<DatasetMeta | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [downloaded, setDownloaded] = useState<Set<string>>(new Set());

  useEffect(() => {
    const stored = localStorage.getItem('currentDatasetMeta');
    if (stored) setMeta(JSON.parse(stored));
  }, []);

  const handleDownload = async (type: 'excel' | 'json' | 'report' | 'summary') => {
    if (!meta) return;
    
    setDownloading(type);
    try {
      await apiService.downloadExport(meta.id, type);
      setDownloaded(prev => new Set([...prev, type]));
    } catch (err) {
      console.error('Download error:', err);
      alert('İndirme başarısız. Backend çalışıyor mu?');
    } finally {
      setDownloading(null);
    }
  };

  if (!meta) return null;

  const Option = ({ icon, title, desc, type, highlight }: { 
    icon: React.ReactNode; 
    title: string; 
    desc: string; 
    type: 'excel' | 'json' | 'report' | 'summary';
    highlight?: boolean;
  }) => (
    <div className={`bg-white p-6 rounded-2xl border-2 transition-all group ${
      highlight 
        ? 'border-blue-400 shadow-lg shadow-blue-100' 
        : 'border-gray-200 hover:border-blue-400 hover:shadow-lg'
    }`}>
      {highlight && (
        <div className="text-xs font-bold text-blue-600 mb-3 uppercase tracking-wider">
          ✨ Önerilen
        </div>
      )}
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 transition-colors ${
        highlight 
          ? 'bg-blue-600 text-white' 
          : 'bg-blue-50 text-blue-600 group-hover:bg-blue-600 group-hover:text-white'
      }`}>
        {icon}
      </div>
      <h3 className="text-xl font-bold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-500 mb-6 text-sm leading-relaxed">{desc}</p>
      <button 
        onClick={() => handleDownload(type)}
        disabled={downloading === type}
        className={`w-full font-medium py-3 rounded-xl flex items-center justify-center space-x-2 transition-all ${
          downloaded.has(type)
            ? 'bg-green-100 text-green-700 border border-green-300'
            : highlight
            ? 'bg-blue-600 text-white hover:bg-blue-700'
            : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
        }`}
      >
        {downloading === type ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            <span>İndiriliyor...</span>
          </>
        ) : downloaded.has(type) ? (
          <>
            <CheckCircle size={18} />
            <span>İndirildi</span>
          </>
        ) : (
          <>
            <Download size={18} />
            <span>İndir</span>
          </>
        )}
      </button>
    </div>
  );

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Dışa Aktar</h1>
      <p className="text-gray-500 mb-8">Veri setini ve analizleri çeşitli formatlarda indirin.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Option 
          icon={<ClipboardList />} 
          title="Anket Özeti" 
          desc="Katılımcı sayısı, veri kalitesi, dijital ikiz uygunluğu ve tüm değişkenlerin kalite analizi dahil kapsamlı özet raporu." 
          type="summary"
          highlight={true}
        />
        <Option 
          icon={<FileSpreadsheet />} 
          title="Veri (Excel)" 
          desc="Ham veri ve etiketli veri sayfalarını içeren Excel dosyası. Manuel analiz için idealdir." 
          type="excel"
        />
        <Option 
          icon={<FileJson />} 
          title="JSON Metadata" 
          desc="Tüm değişken metadata'sı, değer etiketleri, tipler ve kalite skorlarını içeren JSON formatı." 
          type="json"
        />
        <Option 
          icon={<FileText />} 
          title="Kalite Raporu" 
          desc="Detaylı veri kalitesi analizi, eksik veriler, tutarlılık ve dönüşüm hazırlığı raporu." 
          type="report"
        />
      </div>

      {/* Quick Stats */}
      <div className="mt-8 p-6 bg-gradient-to-r from-gray-50 to-blue-50 rounded-2xl border border-gray-100">
        <h3 className="font-bold text-gray-900 mb-4">Veri Seti Bilgileri</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Dosya Adı:</span>
            <p className="font-medium text-gray-900">{meta.filename}</p>
          </div>
          <div>
            <span className="text-gray-500">Katılımcı Sayısı:</span>
            <p className="font-medium text-gray-900">{meta.nRows.toLocaleString()}</p>
          </div>
          <div>
            <span className="text-gray-500">Değişken Sayısı:</span>
            <p className="font-medium text-gray-900">{meta.nCols.toLocaleString()}</p>
          </div>
          <div>
            <span className="text-gray-500">Dijital İkiz:</span>
            <p className={`font-medium ${
              meta.digitalTwinReadiness === 'green' ? 'text-green-600' :
              meta.digitalTwinReadiness === 'yellow' ? 'text-amber-600' : 'text-red-600'
            }`}>
              {meta.digitalTwinReadiness === 'green' ? '✅ Uygun' :
               meta.digitalTwinReadiness === 'yellow' ? '⚠️ Dikkat' : '❌ Uygun Değil'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Exports;
