import React, { useState, useEffect, useMemo } from 'react';
import { apiService } from '../services/apiService';
import { DatasetMeta, VariableDetail, FrequencyItem } from '../types';
import { CHART_COLORS } from '../constants';
import { Search, BarChart2, List, Info, X, ArrowUpDown } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const VariableExplorer: React.FC = () => {
  const [meta, setMeta] = useState<DatasetMeta | null>(null);
  const [selectedVarCode, setSelectedVarCode] = useState<string | null>(null);
  const [varDetail, setVarDetail] = useState<VariableDetail | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [showFullModal, setShowFullModal] = useState(false);
  const [modalSearchTerm, setModalSearchTerm] = useState('');
  const [sortDirection, setSortDirection] = useState<'desc' | 'asc'>('desc');

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
        alert('Could not read dataset info. Please reload the file.');
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
        alert('Dataset not found. Please reload the file.');
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

  // Prepare chart data: Top 10 + Other + Missing
  const chartData = useMemo(() => {
    if (!varDetail || !varDetail.frequencies) return [];
    
    const freqs = [...varDetail.frequencies];
    const missingRow = freqs.find(f => f.value === null);
    const validFreqs = freqs.filter(f => f.value !== null);
    
    if (!varDetail.hasManyCategories) {
      // Show all categories
      return freqs;
    }
    
    // High cardinality: show top 10 + Other + Missing
    const top10 = validFreqs.slice(0, 10);
    const rest = validFreqs.slice(10);
    
    const result = [...top10];
    
    if (rest.length > 0) {
      const otherCount = rest.reduce((sum, f) => sum + (f.count || 0), 0);
      const otherPercentOfTotal = rest.reduce((sum, f) => sum + (f.percentOfTotal || 0), 0);
      const otherPercentOfValid = rest.reduce((sum, f) => sum + (f.percentOfValid || 0), 0);
      
      result.push({
        value: 'OTHER',
        label: `Other (${rest.length} categories)`,
        count: otherCount,
        percentOfTotal: otherPercentOfTotal,
        percentOfValid: otherPercentOfValid
      });
    }
    
    if (missingRow) {
      result.push(missingRow);
    }
    
    return result;
  }, [varDetail]);

  // Modal filtered and sorted frequencies
  const modalFrequencies = useMemo(() => {
    if (!varDetail || !varDetail.frequencies) return [];
    
    let filtered = varDetail.frequencies.filter(f => 
      f.label.toLowerCase().includes(modalSearchTerm.toLowerCase()) ||
      (f.value !== null && String(f.value).toLowerCase().includes(modalSearchTerm.toLowerCase()))
    );
    
    // Sort by count
    filtered.sort((a, b) => {
      if (sortDirection === 'desc') {
        return b.count - a.count;
      } else {
        return a.count - b.count;
      }
    });
    
    return filtered;
  }, [varDetail, modalSearchTerm, sortDirection]);

  const handleBarClick = () => {
    setShowFullModal(true);
    setModalSearchTerm('');
  };

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
              <h2 className="text-2xl font-bold text-gray-900 mb-3">{varDetail.code}: {varDetail.label}</h2>
              
              {/* Stats Header */}
              <div className="grid grid-cols-4 gap-4 mt-4">
                <div className="bg-white p-3 rounded-lg border border-gray-200">
                  <div className="text-xs text-gray-500 mb-1">Total N</div>
                  <div className="text-xl font-bold text-gray-900">{varDetail.totalN}</div>
                </div>
                <div className="bg-white p-3 rounded-lg border border-gray-200">
                  <div className="text-xs text-gray-500 mb-1">Valid N</div>
                  <div className="text-xl font-bold text-green-600">{varDetail.validN}</div>
                  <div className="text-xs text-gray-400">{((varDetail.validN / varDetail.totalN) * 100).toFixed(1)}%</div>
                </div>
                <div className="bg-white p-3 rounded-lg border border-gray-200">
                  <div className="text-xs text-gray-500 mb-1">Missing N</div>
                  <div className="text-xl font-bold text-red-600">{varDetail.missingN}</div>
                  <div className="text-xs text-gray-400">{(varDetail.missingPercentOfTotal ?? 0).toFixed(1)}%</div>
                </div>
                <div className="bg-white p-3 rounded-lg border border-gray-200">
                  <div className="text-xs text-gray-500 mb-1">Cardinality</div>
                  <div className="text-xl font-bold text-gray-900">{varDetail.categoryCount}</div>
                </div>
              </div>
            </div>

            <div className="flex-1 p-6 overflow-y-auto">
              {/* Chart */}
              {chartData && chartData.length > 0 && (
                <div className="mb-8">
                   <div className="flex justify-between items-center mb-4">
                     <h3 className="text-lg font-semibold flex items-center">
                       <BarChart2 className="mr-2" size={20}/> 
                       Frequency Distribution
                       {varDetail.hasManyCategories && (
                         <span className="ml-2 text-xs text-gray-500 font-normal">(Top 10 shown)</span>
                       )}
                     </h3>
                     {varDetail.hasManyCategories && (
                       <button
                         onClick={() => setShowFullModal(true)}
                         className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                       >
                         View all {varDetail.categoryCount} categories →
                       </button>
                     )}
                   </div>
                   <div className="h-80 w-full min-w-0">
                     <ResponsiveContainer width="100%" height="100%" minHeight={320}>
                       <BarChart data={chartData} layout="vertical" margin={{ left: 40, right: 40 }}>
                         <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                         <XAxis type="number" />
                         <YAxis 
                           type="category" 
                           dataKey="label" 
                           width={150} 
                           tick={{fontSize: 11}} 
                           interval={0}
                           tickFormatter={(value) => {
                             // Truncate long labels
                             return value.length > 20 ? value.substring(0, 18) + '...' : value;
                           }}
                         />
                        <Tooltip 
                           contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'}}
                           formatter={(value: any, name: string, props: any) => {
                              const item = props.payload;
                              const percentOfTotal = (item.percentOfTotal ?? 0).toFixed(1);
                              const percentOfValid = (item.percentOfValid ?? 0).toFixed(1);
                              return [
                                `Count: ${item.count} (${percentOfTotal}% of total, ${percentOfValid}% of valid)`,
                                item.label
                              ];
                            }}
                         />
                         <Bar 
                           dataKey="count" 
                           radius={[0, 4, 4, 0]}
                           onClick={handleBarClick}
                           cursor="pointer"
                         >
                           {chartData.map((entry, index) => {
                             // Special color for Missing
                             let fillColor = CHART_COLORS[index % CHART_COLORS.length];
                             if (entry.value === null) {
                               fillColor = '#ef4444'; // red for missing
                             } else if (entry.value === 'OTHER') {
                               fillColor = '#9ca3af'; // gray for other
                             }
                             return <Cell key={`cell-${index}`} fill={fillColor} />;
                           })}
                         </Bar>
                       </BarChart>
                     </ResponsiveContainer>
                   </div>
                </div>
              )}

              {/* Table Preview */}
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold flex items-center">
                    <List className="mr-2" size={20}/> 
                    Frequency Table
                  </h3>
                  {varDetail.hasManyCategories && (
                    <button
                      onClick={() => setShowFullModal(true)}
                      className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      View full table →
                    </button>
                  )}
                </div>
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-gray-50 text-gray-600 font-medium border-b">
                      <tr>
                        <th className="px-4 py-3">Value</th>
                        <th className="px-4 py-3">Label</th>
                        <th className="px-4 py-3 text-right">Count</th>
                        <th className="px-4 py-3 text-right">% of Total</th>
                        <th className="px-4 py-3 text-right">% of Valid</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {chartData.slice(0, 10).map((freq, i) => (
                        <tr key={i} className={`hover:bg-gray-50 ${freq.value === null ? 'bg-red-50' : ''}`}>
                          <td className="px-4 py-2 font-mono text-gray-500">
                            {freq.value === null ? '—' : freq.value}
                          </td>
                          <td className="px-4 py-2 text-gray-900">{freq.label}</td>
                          <td className="px-4 py-2 text-right font-medium">{freq.count}</td>
                          <td className="px-4 py-2 text-right text-gray-500">{(freq.percentOfTotal ?? 0).toFixed(1)}%</td>
                          <td className="px-4 py-2 text-right text-gray-500">{(freq.percentOfValid ?? 0).toFixed(1)}%</td>
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

      {/* Full Frequency Modal */}
      {showFullModal && varDetail && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="p-6 border-b border-gray-200 flex justify-between items-start">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-1">
                  All Frequencies: {varDetail.code}
                </h2>
                <p className="text-sm text-gray-500">{varDetail.label}</p>
                <p className="text-xs text-gray-400 mt-1">
                  {varDetail.categoryCount} categories, {varDetail.totalN} total responses
                </p>
              </div>
              <button
                onClick={() => {
                  setShowFullModal(false);
                  setModalSearchTerm('');
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={24} />
              </button>
            </div>

            {/* Search and Sort Controls */}
            <div className="p-4 border-b border-gray-200 flex gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
                <input 
                  type="text"
                  placeholder="Search by value or label..."
                  className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  value={modalSearchTerm}
                  onChange={(e) => setModalSearchTerm(e.target.value)}
                />
              </div>
              <button
                onClick={() => setSortDirection(sortDirection === 'desc' ? 'asc' : 'desc')}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium text-gray-700"
              >
                <ArrowUpDown size={16} />
                Sort: {sortDirection === 'desc' ? 'High → Low' : 'Low → High'}
              </button>
            </div>

            {/* Modal Table */}
            <div className="flex-1 overflow-y-auto p-6">
              <table className="w-full text-sm text-left">
                <thead className="bg-gray-50 text-gray-600 font-medium border-b sticky top-0">
                  <tr>
                    <th className="px-4 py-3">Value</th>
                    <th className="px-4 py-3">Label</th>
                    <th className="px-4 py-3 text-right">Count</th>
                    <th className="px-4 py-3 text-right">% of Total</th>
                    <th className="px-4 py-3 text-right">% of Valid</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {modalFrequencies.map((freq, i) => (
                    <tr key={i} className={`hover:bg-gray-50 ${freq.value === null ? 'bg-red-50' : ''}`}>
                      <td className="px-4 py-2 font-mono text-gray-500">
                        {freq.value === null ? '—' : freq.value}
                      </td>
                      <td className="px-4 py-2 text-gray-900">{freq.label}</td>
                      <td className="px-4 py-2 text-right font-medium">{freq.count}</td>
                      <td className="px-4 py-2 text-right text-gray-500">{(freq.percentOfTotal ?? 0).toFixed(1)}%</td>
                      <td className="px-4 py-2 text-right text-gray-500">{(freq.percentOfValid ?? 0).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-gray-100 font-semibold border-t-2 border-gray-300">
                  <tr>
                    <td className="px-4 py-3 text-gray-700" colSpan={2}>Total</td>
                    <td className="px-4 py-3 text-right text-gray-900">
                      {modalFrequencies.reduce((sum, f) => sum + (f.count || 0), 0)}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {modalFrequencies.reduce((sum, f) => sum + (f.percentOfTotal ?? 0), 0).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {modalFrequencies.reduce((sum, f) => sum + (f.percentOfValid ?? 0), 0).toFixed(1)}%
                    </td>
                  </tr>
                </tfoot>
              </table>
              {modalFrequencies.length === 0 && (
                <div className="text-center py-12 text-gray-400">
                  No results found
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-gray-200 flex justify-between items-center bg-gray-50">
              <div className="text-sm text-gray-600">
                Showing {modalFrequencies.length} of {varDetail.frequencies.length} rows
              </div>
              <button
                onClick={() => {
                  setShowFullModal(false);
                  setModalSearchTerm('');
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VariableExplorer;
