import React, { useState, useEffect, useMemo } from 'react';
import { apiService } from '../services/apiService';
import { DatasetMeta, VariableDetail } from '../types';
import { CHART_COLORS } from '../constants';
import { Search, BarChart2, List, Info } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const VariableExplorer: React.FC = () => {
  const [meta, setMeta] = useState<DatasetMeta | null>(null);
  const [selectedVarCode, setSelectedVarCode] = useState<string | null>(null);
  const [varDetail, setVarDetail] = useState<VariableDetail | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('currentDatasetMeta');
    if (stored) {
      try {
        const data = JSON.parse(stored);
        setMeta(data);
        if (data.variables && data.variables.length > 0) {
          handleSelectVar(data.id, data.variables[0].code);
        }
      } catch (err) {
        console.error('Failed to parse dataset meta:', err);
        alert('Dataset bilgisi okunamadı. Lütfen dosyayı tekrar yükleyin.');
        window.location.href = '/#/';
      }
    } else {
      // No dataset in localStorage, redirect to upload
      window.location.href = '/#/';
    }
  }, []);

  const handleSelectVar = async (datasetId: string, code: string) => {
    setSelectedVarCode(code);
    setLoadingDetail(true);
    try {
      const detail = await apiService.getVariableDetail(datasetId, code);
      setVarDetail(detail);
    } catch (err: any) {
      console.error('Variable detail error:', err);
      // If dataset not found, redirect to upload page
      if (err.message?.includes('not found') || err.message?.includes('404')) {
        alert('Dataset bulunamadı. Lütfen dosyayı tekrar yükleyin.');
        window.location.href = '/#/';
      }
    } finally {
      setLoadingDetail(false);
    }
  };

  const filteredVars = useMemo(() => {
    if (!meta) return [];
    return meta.variables.filter(v => 
      v.code.toLowerCase().includes(searchTerm.toLowerCase()) || 
      v.label.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [meta, searchTerm]);

  if (!meta) return <div>Loading...</div>;

  return (
    <div className="flex h-[calc(100vh-100px)] gap-6">
      {/* Sidebar List */}
      <div className="w-1/3 flex flex-col bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
            <input 
              type="text"
              placeholder="Search variables..."
              className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {filteredVars.map((v) => (
             <div 
               key={v.code}
               onClick={() => handleSelectVar(meta.id, v.code)}
               className={`p-4 border-b border-gray-50 cursor-pointer hover:bg-gray-50 transition-colors ${
                 selectedVarCode === v.code ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
               }`}
             >
               <div className="flex justify-between items-start mb-1">
                 <span className="font-bold text-gray-800 text-sm">{v.code}</span>
                 <span className="text-[10px] uppercase font-bold text-gray-400 bg-gray-100 px-2 py-0.5 rounded">{v.type}</span>
               </div>
               <p className="text-xs text-gray-500 line-clamp-2">{v.label}</p>
             </div>
          ))}
        </div>
      </div>

      {/* Detail View */}
      <div className="flex-1 bg-white rounded-2xl shadow-sm border border-gray-100 flex flex-col overflow-hidden">
        {loadingDetail || !varDetail ? (
           <div className="flex-1 flex items-center justify-center text-gray-400">Loading details...</div>
        ) : (
          <div className="flex flex-col h-full">
            <div className="p-6 border-b border-gray-100 bg-gray-50/50">
              <div className="flex items-center space-x-2 text-sm text-blue-600 font-medium mb-2">
                <Info size={16} />
                <span>Variable Details</span>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">{varDetail.code}: {varDetail.label}</h2>
              <div className="flex space-x-6 text-sm text-gray-600">
                <span>Valid N: <strong>{varDetail.responseCount}</strong></span>
                <span>Missing: <strong>{varDetail.missingValues?.userMissingValues.length || 0} defs</strong></span>
                <span>Cardinality: <strong>{varDetail.cardinality}</strong></span>
              </div>
            </div>

            <div className="flex-1 p-6 overflow-y-auto">
              {/* Chart */}
              {varDetail.frequencies && varDetail.frequencies.length > 0 && (
                <div className="mb-8 h-80 w-full min-w-0">
                   <h3 className="text-lg font-semibold mb-4 flex items-center"><BarChart2 className="mr-2" size={20}/> Frequency Distribution</h3>
                   <ResponsiveContainer width="100%" height="100%" minHeight={320}>
                     <BarChart data={varDetail.frequencies} layout="vertical" margin={{ left: 40, right: 40 }}>
                       <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                       <XAxis type="number" />
                       <YAxis type="category" dataKey="label" width={150} tick={{fontSize: 11}} interval={0} />
                       <Tooltip 
                          contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'}}
                       />
                       <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                         {varDetail.frequencies.map((entry, index) => (
                           <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                         ))}
                       </Bar>
                     </BarChart>
                   </ResponsiveContainer>
                </div>
              )}

              {/* Table */}
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center"><List className="mr-2" size={20}/> Data Dictionary</h3>
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-gray-50 text-gray-600 font-medium border-b">
                      <tr>
                        <th className="px-4 py-3">Value</th>
                        <th className="px-4 py-3">Label</th>
                        <th className="px-4 py-3 text-right">Count</th>
                        <th className="px-4 py-3 text-right">Percent</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {varDetail.frequencies?.map((freq, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-4 py-2 font-mono text-gray-500">{freq.value}</td>
                          <td className="px-4 py-2 text-gray-900">{freq.label}</td>
                          <td className="px-4 py-2 text-right">{freq.count}</td>
                          <td className="px-4 py-2 text-right text-gray-500">{freq.percent.toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VariableExplorer;