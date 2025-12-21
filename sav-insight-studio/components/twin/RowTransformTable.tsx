import React, { useMemo, useState } from 'react';
import { DatasetMeta, DatasetRowsResponse, TransformJob, TransformResult } from '../../types';
import { ChevronLeft, ChevronRight, Loader2, Table2, RotateCcw } from 'lucide-react';
import { transformService } from '../../services/transformService';

interface RowTransformTableProps {
  datasetMeta: DatasetMeta;
  rowsResponse: DatasetRowsResponse | null;
  isLoadingRows: boolean;
  rowsError: string | null;
  pageSize: number;
  pageIndex: number;
  onPageSizeChange: (size: number) => void;
  onPageIndexChange: (page: number) => void;
  job: TransformJob | null;
  resultsByRowIndex: Record<number, TransformResult>;
  smartFilters: Array<{ id: string; title: string; sourceVars: string[] }>;
  onOpenRowDetail: (rowIndex: number) => void;
}

function defaultIdFromRow(row: Record<string, any>): string | null {
  const keys = Object.keys(row);
  const candidates = keys.filter(k => /(^|_)id$|respondent.*id|resp.*id|participant.*id|case.*id/i.test(k));
  for (const k of candidates) {
    const v = row[k];
    if (v !== null && v !== undefined && String(v).trim() !== '') return String(v);
  }
  return null;
}

function isEmptyValue(v: any): boolean {
  if (v === null || v === undefined) return true;
  if (typeof v === 'string' && v.trim() === '') return true;
  return false;
}

export default function RowTransformTable({
  datasetMeta,
  rowsResponse,
  isLoadingRows,
  rowsError,
  pageSize,
  pageIndex,
  onPageSizeChange,
  onPageIndexChange,
  job,
  resultsByRowIndex,
  smartFilters,
  onOpenRowDetail,
}: RowTransformTableProps) {
  const [retryingRows, setRetryingRows] = useState<Set<number>>(new Set());
  
  const variableByCode = useMemo(() => {
    const m = new Map<string, DatasetMeta['variables'][number]>();
    (datasetMeta.variables || []).forEach(v => m.set(v.code, v));
    return m;
  }, [datasetMeta.variables]);

  const handleRetryRow = async (rowIndex: number) => {
    if (!job?.jobId) return;
    
    setRetryingRows(prev => new Set(prev).add(rowIndex));
    try {
      await transformService.retryRow(job.jobId, rowIndex);
      // Reload results for this page
      // Note: Parent component should handle refreshing resultsByRowIndex
      // For now, we'll just show success - parent polling will update
    } catch (e) {
      console.error(`Failed to retry row ${rowIndex}:`, e);
      alert(`Failed to retry row ${rowIndex + 1}: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      setRetryingRows(prev => {
        const next = new Set(prev);
        next.delete(rowIndex);
        return next;
      });
    }
  };

  const visibleSmartFilters = useMemo(() => (smartFilters || []).filter(f => (f.sourceVars || []).length > 0), [smartFilters]);

  const totalRows = rowsResponse?.total ?? datasetMeta.nRows ?? 0;
  const totalPages = pageSize > 0 ? Math.max(1, Math.ceil(totalRows / pageSize)) : 1;

  const formatValue = (code: string, value: any) => {
    if (isEmptyValue(value)) return '';
    const varMeta = variableByCode.get(code);
    const valueLabels = varMeta?.valueLabels || [];

    const mapOne = (val: any) => {
      const match = valueLabels.find(vl => vl.value === val);
      return match ? match.label : String(val);
    };

    if (Array.isArray(value)) {
      const parts = value.filter(v => !isEmptyValue(v)).map(mapOne);
      return parts.join(', ');
    }
    return mapOne(value);
  };

  const statusLabel = (rowIndex: number) => {
    // Always check actual row result first - this is the source of truth
    const r = resultsByRowIndex[rowIndex];
    if (r) {
      if (r.status === 'completed') return { text: 'Completed', cls: 'bg-green-100 text-green-700 border border-green-300' };
      if (r.status === 'failed') return { text: 'Error', cls: 'bg-red-100 text-red-700 border border-red-300' };
      if (r.status === 'processing') return { text: 'Processing', cls: 'bg-blue-100 text-blue-700 border border-blue-300 animate-pulse' };
      return { text: r.status, cls: 'bg-gray-100 text-gray-700 border border-gray-300' };
    }
    // Fallback: if no result yet, estimate based on job status
    if (job?.status === 'running') {
      const current = job.currentRowIndex ?? job.processedRows ?? 0;
      const rowConcurrency = job.rowConcurrency ?? 5; // Get concurrency from job or default to 5
      const effectiveTotal = job.rowLimit || job.totalRows; // Use row limit if set
      
      // If row is beyond the effective total, it won't be processed
      if (rowIndex >= effectiveTotal) {
        return { text: 'Not Processed', cls: 'bg-gray-50 text-gray-400 border border-gray-200' };
      }
      
      // Show as "Processing" if this row is within the current batch being processed
      if (rowIndex >= current && rowIndex < current + rowConcurrency && rowIndex < effectiveTotal) {
        return { text: 'Processing', cls: 'bg-blue-100 text-blue-700 border border-blue-300 animate-pulse' };
      }
      
      if (rowIndex < current) return { text: 'Pending', cls: 'bg-amber-50 text-amber-600 border border-amber-200' };
      return { text: 'Waiting', cls: 'bg-gray-50 text-gray-500 border border-gray-200' };
    }
    if (job?.status === 'paused') return { text: 'Paused', cls: 'bg-amber-50 text-amber-600 border border-amber-200' };
    if (job?.status === 'completed') {
      // If job completed but no result, it might not have been processed
      return { text: 'Not Processed', cls: 'bg-gray-50 text-gray-400 border border-gray-200' };
    }
    return { text: 'Waiting', cls: 'bg-gray-50 text-gray-500 border border-gray-200' };
  };

  const rows = rowsResponse?.rows || [];

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-lg overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Table2 className="text-blue-600" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 text-lg">Transformation Results</h3>
            <p className="text-xs text-gray-500 mt-0.5">Row-level status, output, and active Smart Filter columns</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={pageSize}
            onChange={(e) => {
              const v = e.target.value;
              const nextSize = v === 'all' ? datasetMeta.nRows : parseInt(v, 10);
              onPageSizeChange(nextSize);
              onPageIndexChange(0);
            }}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
            title="Rows to display per page"
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={1000}>1000</option>
            <option value="all">All</option>
          </select>

          <div className="flex items-center space-x-1">
            <button
              onClick={() => onPageIndexChange(Math.max(0, pageIndex - 1))}
              disabled={pageIndex === 0}
              className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Previous"
            >
              <ChevronLeft size={18} />
            </button>
            <span className="text-sm text-gray-600 px-2">
              {totalRows === 0 ? '-' : `${pageIndex + 1} / ${totalPages}`}
            </span>
            <button
              onClick={() => onPageIndexChange(Math.min(totalPages - 1, pageIndex + 1))}
              disabled={pageIndex >= totalPages - 1}
              className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Next"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      </div>

      {rowsError && (
        <div className="px-6 py-3 bg-red-50 border-b border-red-100 text-sm text-red-700">
          {rowsError}
        </div>
      )}

      {visibleSmartFilters.length === 0 && (
        <div className="px-6 py-3 bg-amber-50 border-b border-amber-100 text-sm text-amber-800">
          No active Smart Filters found. Select filters from the `Smart Filters` page and click "Apply Filter" to see them as columns here.
        </div>
      )}

      <div className="relative">
        {isLoadingRows && (
          <div className="absolute inset-0 bg-white/70 flex items-center justify-center z-10">
            <div className="flex items-center space-x-2 text-gray-700">
              <Loader2 className="animate-spin" size={18} />
              <span className="text-sm">Loading rows...</span>
            </div>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="min-w-max w-full text-sm">
            <thead className="bg-gradient-to-r from-gray-50 to-gray-100 border-b-2 border-gray-300">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-800 sticky left-0 bg-gradient-to-r from-gray-50 to-gray-100 z-[1] border-r border-gray-200">Row</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-800 sticky left-[72px] bg-gradient-to-r from-gray-50 to-gray-100 z-[1] border-r border-gray-200">ID</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-800">Status</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-800 min-w-[300px]">Output (first sentence)</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-800 whitespace-nowrap text-center">Sentences</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-800 whitespace-nowrap text-center">Skipped</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-800 whitespace-nowrap text-center">Actions</th>
                {visibleSmartFilters.map(f => (
                  <th key={f.id} className="px-4 py-3 text-left font-semibold text-gray-800 whitespace-nowrap bg-blue-50/50 border-l border-blue-200">
                    <div className="flex flex-col">
                      <span className="text-xs text-blue-900 font-bold max-w-[220px] truncate">{f.title}</span>
                      <span className="text-[10px] text-blue-600 font-mono max-w-[220px] truncate mt-0.5">
                        {(f.sourceVars || []).join(', ')}
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={7 + visibleSmartFilters.length} className="px-6 py-10 text-center text-gray-500">
                    No rows found
                  </td>
                </tr>
              ) : (
                rows.map((r) => {
                  const result = resultsByRowIndex[r.index];
                  const status = statusLabel(r.index);
                  const id = (result?.respondentId || defaultIdFromRow(r.data)) ?? '-';
                  const firstSentence = result?.sentences?.[0]?.sentence || '';
                  const isClickable = Boolean(result);
                  const sentenceCount = result?.sentences?.length ?? 0;
                  const skippedCount = result?.excluded
                    ? (result.excluded.emptyVars?.length || 0) +
                      (result.excluded.excludedByOption?.length || 0) +
                      (result.excluded.adminVars?.length || 0) +
                      (result.excluded.excludedVariables?.length || 0)
                    : 0;

                  const smartCell = (filter: { id: string; title: string; sourceVars: string[] }) => {
                    const vars = filter.sourceVars || [];
                    if (vars.length === 0) return '';
                    if (vars.length === 1) return formatValue(vars[0], r.data?.[vars[0]]);
                    // If multiple vars, include code prefixes to avoid ambiguity
                    const parts = vars
                      .map(v => {
                        const val = formatValue(v, r.data?.[v]);
                        return val ? `${v}: ${val}` : '';
                      })
                      .filter(Boolean);
                    return parts.join(' | ');
                  };

                  return (
                    <tr
                      key={r.index}
                      className={`${isClickable ? 'hover:bg-blue-50 cursor-pointer transition-colors' : ''} border-b border-gray-100 ${result?.status === 'completed' ? 'bg-green-50/30' : ''}`}
                      onClick={() => {
                        if (isClickable) onOpenRowDetail(r.index);
                      }}
                    >
                      <td className="px-4 py-3 sticky left-0 bg-white z-[1] font-semibold text-gray-900 border-r border-gray-100">
                        {r.index + 1}
                      </td>
                      <td className="px-4 py-3 sticky left-[72px] bg-white z-[1] text-gray-700 font-mono text-sm border-r border-gray-100">
                        {id}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-3 py-1 rounded-lg text-xs font-semibold ${status.cls} shadow-sm`}>
                          {status.text}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-800 max-w-[420px]">
                        {firstSentence ? (
                          <span className="block truncate italic text-sm leading-relaxed">"{firstSentence}"</span>
                        ) : (
                          <span className="text-gray-400 text-sm">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {result ? (
                          <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-green-100 text-green-700 font-semibold text-sm">
                            {sentenceCount}
                          </span>
                        ) : (
                          <span className="text-gray-300">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {result ? (
                          <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-600 font-medium text-sm">
                            {skippedCount}
                          </span>
                        ) : (
                          <span className="text-gray-300">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {job?.jobId && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRetryRow(r.index);
                            }}
                            disabled={retryingRows.has(r.index)}
                            className={`inline-flex items-center justify-center w-8 h-8 rounded-lg transition-colors ${
                              retryingRows.has(r.index)
                                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                : result?.status === 'failed'
                                ? 'bg-red-100 text-red-600 hover:bg-red-200'
                                : 'bg-blue-100 text-blue-600 hover:bg-blue-200'
                            }`}
                            title={result?.status === 'failed' ? 'Retry failed row' : 'Retry transformation'}
                          >
                            {retryingRows.has(r.index) ? (
                              <Loader2 className="animate-spin" size={16} />
                            ) : (
                              <RotateCcw size={16} />
                            )}
                          </button>
                        )}
                      </td>
                      {visibleSmartFilters.map(f => (
                        <td key={`${r.index}-${f.id}`} className="px-4 py-3 text-gray-700 max-w-[280px] truncate bg-blue-50/50">
                          {smartCell(f) || <span className="text-gray-400 text-sm">-</span>}
                        </td>
                      ))}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}


