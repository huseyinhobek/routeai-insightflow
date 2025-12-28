import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, ChevronLeft, ChevronRight, RefreshCw, ToggleLeft, ToggleRight, Download } from 'lucide-react';
import { transformService } from '../services/transformService';
import { DatasetMeta, DatasetRowsResponse } from '../types';

const ParticipantDataPage: React.FC = () => {
  const navigate = useNavigate();
  const [meta, setMeta] = useState<DatasetMeta | null>(null);
  const [rowsResponse, setRowsResponse] = useState<DatasetRowsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [showLabeled, setShowLabeled] = useState(true);
  const [selectedColumns, setSelectedColumns] = useState<Set<string>>(new Set());

  useEffect(() => {
    const stored = localStorage.getItem('currentDatasetMeta');
    if (!stored) {
      navigate('/');
      return;
    }
    
    try {
      const data = JSON.parse(stored);
      setMeta(data);
      // Initially select all columns
      if (data.variables) {
        setSelectedColumns(new Set(data.variables.map((v: any) => v.code)));
      }
    } catch (err) {
      console.error('Failed to parse dataset meta:', err);
      navigate('/');
    }
  }, [navigate]);

  useEffect(() => {
    if (meta) {
      loadRows();
    }
  }, [meta, currentPage, pageSize]);

  const loadRows = async () => {
    if (!meta) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const offset = currentPage * pageSize;
      const response = await transformService.getDatasetRows(meta.id, offset, pageSize);
      setRowsResponse(response);
    } catch (err: any) {
      console.error('Failed to load rows:', err);
      setError(err.message || 'Failed to load participant data');
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 0 && rowsResponse && newPage < Math.ceil(rowsResponse.total / pageSize)) {
      setCurrentPage(newPage);
    }
  };

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setCurrentPage(0); // Reset to first page
  };

  const toggleColumn = (columnCode: string) => {
    const newSelected = new Set(selectedColumns);
    if (newSelected.has(columnCode)) {
      newSelected.delete(columnCode);
    } else {
      newSelected.add(columnCode);
    }
    setSelectedColumns(newSelected);
  };

  const selectAllColumns = () => {
    if (!meta) return;
    setSelectedColumns(new Set(meta.variables.map((v: any) => v.code)));
  };

  const deselectAllColumns = () => {
    setSelectedColumns(new Set());
  };

  // Get visible columns based on selection
  const visibleColumns = useMemo(() => {
    if (!meta) return [];
    return meta.variables.filter((v: any) => selectedColumns.has(v.code));
  }, [meta, selectedColumns]);

  if (!meta) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-gray-500">Loading dataset...</div>
      </div>
    );
  }

  const totalPages = rowsResponse ? Math.ceil(rowsResponse.total / pageSize) : 0;
  const startRow = currentPage * pageSize + 1;
  const endRow = Math.min((currentPage + 1) * pageSize, rowsResponse?.total || 0);

  return (
    <div className="flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg">
              <Users className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Katılımcı Verileri</h1>
              <p className="text-gray-600 mt-1">Raw ve labeled değerleri görüntüleyin</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowLabeled(!showLabeled)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg border transition-colors ${
                showLabeled
                  ? 'bg-blue-50 border-blue-200 text-blue-700'
                  : 'bg-gray-50 border-gray-200 text-gray-700'
              }`}
            >
              {showLabeled ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />}
              <span>{showLabeled ? 'Labeled' : 'Raw'}</span>
            </button>
            
            <button
              onClick={loadRows}
              className="flex items-center space-x-2 px-4 py-2 rounded-lg border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Yenile</span>
            </button>
          </div>
        </div>
      </div>

      {/* Column Selector */}
      <div className="mb-4 p-4 bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700">Gösterilecek Sütunlar</h3>
          <div className="flex items-center space-x-2">
            <button
              onClick={selectAllColumns}
              className="text-xs px-3 py-1 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
            >
              Tümünü Seç
            </button>
            <button
              onClick={deselectAllColumns}
              className="text-xs px-3 py-1 bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
            >
              Tümünü Kaldır
            </button>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {meta.variables.slice(0, 50).map((variable: any) => (
            <button
              key={variable.code}
              onClick={() => toggleColumn(variable.code)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                selectedColumns.has(variable.code)
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {variable.code}
            </button>
          ))}
          {meta.variables.length > 50 && (
            <span className="px-3 py-1.5 text-xs text-gray-500">
              +{meta.variables.length - 50} daha
            </span>
          )}
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex flex-col" style={{ maxHeight: 'calc(100vh - 400px)' }}>
        {error && (
          <div className="p-4 bg-red-50 border-b border-red-200">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="animate-pulse text-gray-500">Yükleniyor...</div>
          </div>
        ) : rowsResponse && rowsResponse.rows.length > 0 ? (
          <>
            {/* Table */}
            <div className="overflow-auto flex-1">
              <table className="w-full border-collapse min-w-full">
                <thead className="bg-gray-50 sticky top-0 z-10">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 border-b border-gray-200 sticky left-0 bg-gray-50 z-20 shadow-sm">
                      #
                    </th>
                    {visibleColumns.map((variable: any) => (
                      <th
                        key={variable.code}
                        className="px-4 py-3 text-left text-xs font-semibold text-gray-700 border-b border-gray-200 min-w-[280px]"
                      >
                        <div className="flex flex-col space-y-1.5">
                          <span className="font-bold text-gray-900 text-sm">{variable.code}</span>
                          <span className="text-xs text-gray-600 font-normal leading-relaxed break-words whitespace-normal" title={variable.label}>
                            {variable.label || variable.code}
                          </span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {rowsResponse.rows.map((row) => {
                    const displayData = showLabeled && row.labeled ? row.labeled : row.data;
                    return (
                      <tr key={row.index} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 border-r border-gray-200 sticky left-0 bg-white z-10 shadow-sm">
                          {row.index + 1}
                        </td>
                        {visibleColumns.map((variable: any) => {
                          const value = displayData[variable.code];
                          const rawValue = row.data[variable.code];
                          const labeledValue = showLabeled && row.labeled ? row.labeled[variable.code] : null;
                          
                          // Get value label from variable metadata
                          let valueLabel = null;
                          if (variable.valueLabels && Array.isArray(variable.valueLabels) && rawValue !== null && rawValue !== undefined) {
                            const labelObj = variable.valueLabels.find((vl: any) => 
                              String(vl.value) === String(rawValue)
                            );
                            if (labelObj) {
                              valueLabel = labelObj.label;
                            }
                          }
                          
                          // In labeled view, use valueLabel from metadata if available, otherwise use labeled value from backend
                          let displayValue: string | null = null;
                          if (showLabeled) {
                            // First try to get label from variable metadata (most accurate)
                            if (valueLabel) {
                              displayValue = valueLabel;
                            } 
                            // Fallback to labeled value from backend
                            else if (labeledValue !== null && labeledValue !== undefined && String(labeledValue) !== String(rawValue)) {
                              displayValue = String(labeledValue);
                            } 
                            // Last resort: use raw value
                            else if (value !== null && value !== undefined) {
                              displayValue = String(value);
                            }
                          } else {
                            // Raw view: show raw value
                            displayValue = value !== null && value !== undefined ? String(value) : null;
                          }
                          
                          // Show raw value if we're displaying a label and it's different from raw
                          const showRawValue = showLabeled && displayValue !== null && String(rawValue) !== displayValue && rawValue !== null && rawValue !== undefined;
                          
                          return (
                            <td
                              key={variable.code}
                              className="px-4 py-3 text-sm text-gray-700 border-r border-gray-100"
                            >
                              <div className="flex flex-col">
                                {displayValue === null || displayValue === undefined ? (
                                  <span className="text-gray-400 italic">-</span>
                                ) : (
                                  <>
                                    <span 
                                      className={showLabeled && (valueLabel || labeledValue) ? 'font-medium text-blue-700 break-words' : 'text-gray-900 break-words'}
                                      title={showLabeled ? `${variable.label || variable.code}: ${displayValue}` : `${variable.code}: ${displayValue}`}
                                    >
                                      {displayValue}
                                    </span>
                                    {showRawValue && (
                                      <span className="text-xs text-gray-400 mt-0.5">
                                        (Raw: {rawValue})
                                      </span>
                                    )}
                                  </>
                                )}
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="border-t border-gray-200 p-4 bg-gray-50 flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-700">
                  {startRow}-{endRow} / {rowsResponse.total} kayıt
                </span>
                
                <div className="flex items-center space-x-2">
                  <label className="text-sm text-gray-700">Sayfa başına:</label>
                  <select
                    value={pageSize}
                    onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                    className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handlePageChange(0)}
                  disabled={currentPage === 0}
                  className="p-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                
                <span className="text-sm text-gray-700 px-3">
                  Sayfa {currentPage + 1} / {totalPages}
                </span>
                
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 0}
                  className="p-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage >= totalPages - 1}
                  className="p-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
                
                <button
                  onClick={() => handlePageChange(totalPages - 1)}
                  disabled={currentPage >= totalPages - 1}
                  className="p-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-gray-500">Veri bulunamadı</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ParticipantDataPage;

