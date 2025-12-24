import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, 
  Pause, 
  Square, 
  RotateCcw,
  Download,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Activity,
  Clock,
  Loader2,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Sparkles,
  Cpu,
  Settings,
  Wand2
} from 'lucide-react';
import { TransformJob, TransformResult } from '../../types';

interface LiveOutputProps {
  job: TransformJob | null;
  isLoading: boolean;
  error: string | null;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onCancel?: () => void;
  onChangeSettings?: () => void;
  onChangeColumns?: () => void;
  onReset: () => void;
  onExportJson: () => void;
  onExportCsv: () => void;
  results: TransformResult[];
  totalResults: number;
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onSelectResult: (result: TransformResult) => void;
  selectedRowIndex: number | null;
  lastUpdateTime: Date | null;
  currentProcessingRow?: number | null;
  latestSentence?: string | null;
  customResultsView?: React.ReactNode;
}

const LiveOutput: React.FC<LiveOutputProps> = ({
  job,
  isLoading,
  error,
  onStart,
  onPause,
  onResume,
  onStop,
  onCancel,
  onReset,
  onExportJson,
  onExportCsv,
  onChangeSettings,
  onChangeColumns,
  results,
  totalResults,
  currentPage,
  pageSize,
  onPageChange,
  onSelectResult,
  selectedRowIndex,
  lastUpdateTime,
  currentProcessingRow,
  latestSentence,
  customResultsView,
}) => {
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetConfirmText, setResetConfirmText] = useState('');
  const [newResultsCount, setNewResultsCount] = useState(0);
  const prevResultsLength = useRef(results.length);
  const logRef = useRef<HTMLDivElement>(null);

  // Track new results for animation
  useEffect(() => {
    if (results.length > prevResultsLength.current) {
      setNewResultsCount(results.length - prevResultsLength.current);
      setTimeout(() => setNewResultsCount(0), 2000);
    }
    prevResultsLength.current = results.length;
  }, [results.length]);

  // Auto-scroll only if on first page
  useEffect(() => {
    if (currentPage === 0 && logRef.current && job?.status === 'running') {
      logRef.current.scrollTop = 0; // Show newest at top
    }
  }, [results.length, currentPage, job?.status]);

  const totalPages = Math.ceil(totalResults / pageSize);
  // Calculate progress based on TOTAL dataset rows, not row limit
  const datasetProgressPercent = job ? (job.totalRows > 0 ? (job.processedRows / job.totalRows) * 100 : 0) : 0;
  const safePercent = Math.min(100, Math.max(0, datasetProgressPercent));
  const effectiveTotal = job ? (job.rowLimit || job.totalRows) : 0;
  const safeRemaining = job ? Math.max(0, effectiveTotal - job.processedRows) : 0;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-600 bg-green-100';
      case 'paused':
        return 'text-amber-600 bg-amber-100';
      case 'completed':
        return 'text-blue-600 bg-blue-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      case 'cancelled':
        return 'text-orange-600 bg-orange-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'running':
        return 'Running';
      case 'paused':
        return 'Paused';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'idle':
        return 'Idle';
      case 'cancelled':
        return 'Cancelled';
      default:
        return status;
    }
  };

  const handleResetConfirm = () => {
    if (resetConfirmText === 'DELETE') {
      onReset();
      setShowResetConfirm(false);
      setResetConfirmText('');
    }
  };

  const formatTime = (date: Date | null) => {
    if (!date) return '-';
    return date.toLocaleTimeString('tr-TR');
  };

  return (
    <div className="space-y-6">
      {/* Controls & Progress */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <Activity className="text-blue-600" size={24} />
            <div>
              <h3 className="font-semibold text-gray-900">Transformation Process</h3>
              {job && (
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-sm font-medium ${getStatusColor(job.status)}`}>
                  {job.status === 'running' && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
                  {getStatusLabel(job.status)}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {(!job || job.status === 'idle') && (
              <button
                onClick={onStart}
                disabled={isLoading}
                className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Play size={18} />
                <span>Start</span>
              </button>
            )}

            {job?.status === 'running' && (
              <>
                <button
                  onClick={onPause}
                  className="flex items-center space-x-2 px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors"
                >
                  <Pause size={18} />
                  <span>Pause</span>
                </button>
                <button
                  onClick={onStop}
                  className="flex items-center space-x-2 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
                  title="Stop - pause the job, can resume later"
                >
                  <Square size={18} />
                  <span>Stop</span>
                </button>
                {onCancel && (
                  <button
                    onClick={onCancel}
                    className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                    title="Cancel - stop and clear waiting queue, keep completed results"
                  >
                    <XCircle size={18} />
                    <span>Cancel</span>
                  </button>
                )}
              </>
            )}

            {(job?.status === 'paused' || job?.status === 'cancelled') && (
              <>
                <button
                  onClick={onResume}
                  className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  title="Resume with current or new settings"
                >
                  <Play size={18} />
                  <span>Resume</span>
                </button>
                {onChangeSettings && (
                  <button
                    onClick={onChangeSettings}
                    className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                    title="Change concurrency and other settings before resuming"
                  >
                    <Settings size={18} />
                    <span>Settings</span>
                  </button>
                )}
                {onCancel && job?.status === 'paused' && (
                  <button
                    onClick={onCancel}
                    className="flex items-center space-x-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                    title="Cancel - clear waiting queue, keep completed results"
                  >
                    <XCircle size={18} />
                    <span>Cancel Job</span>
                  </button>
                )}
                <button
                  onClick={() => setShowResetConfirm(true)}
                  className="flex items-center space-x-2 px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
                  title="Reset - delete ALL results and start fresh"
                >
                  <RotateCcw size={18} />
                  <span>Reset All</span>
                </button>
              </>
            )}

            {job?.status === 'completed' && (
              <>
                {/* Show Continue button if there are more rows in dataset to process */}
                {job.processedRows < job.totalRows && (
                  <button
                    onClick={onResume}
                    className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                    title={`Continue processing remaining rows (${job.totalRows - job.processedRows} rows left in dataset)`}
                  >
                    <Play size={18} />
                    <span>Continue ({job.totalRows - job.processedRows} rows remaining)</span>
                  </button>
                )}
                <button
                  onClick={onExportJson}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <Download size={18} />
                  <span>JSON</span>
                </button>
                <button
                  onClick={onExportCsv}
                  className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Download size={18} />
                  <span>CSV</span>
                </button>
                <button
                  onClick={() => setShowResetConfirm(true)}
                  className="flex items-center space-x-2 px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
                >
                  <RotateCcw size={18} />
                  <span>Restart</span>
                </button>
              </>
            )}

            {job?.status === 'failed' && (
              <button
                onClick={onResume}
                className="flex items-center space-x-2 px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors"
              >
                <RotateCcw size={18} />
                <span>Retry</span>
              </button>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        {job && (
          <div className="space-y-3">
            <div className="flex justify-between text-sm text-gray-600">
              <span>Progress: {job.processedRows} / {job.rowLimit || job.totalRows} rows {job.rowLimit && `(of ${job.totalRows} total)`}</span>
              <span>{safePercent.toFixed(1)}%</span>
            </div>
            <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  job.status === 'completed' ? 'bg-green-500' :
                  job.status === 'failed' ? 'bg-red-500' :
                  'bg-blue-500'
                }`}
                style={{ width: `${safePercent}%` }}
              />
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">Processed</p>
                <p className="text-lg font-semibold text-green-600">{job.processedRows}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">Failed</p>
                <p className="text-lg font-semibold text-red-600">{job.failedRows}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">Remaining</p>
                <p className="text-lg font-semibold text-gray-600">{safeRemaining}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">Errors</p>
                <p className="text-lg font-semibold text-amber-600">{job.stats?.errors || 0}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">Retries</p>
                <p className="text-lg font-semibold text-purple-600">{job.stats?.retries || 0}</p>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="mt-4 flex items-center justify-center space-x-3">
              {onChangeSettings && (
                <button
                  onClick={onChangeSettings}
                  className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <Settings size={18} />
                  <span>Change Settings</span>
                </button>
              )}
              {onChangeColumns && (
                <button
                  onClick={onChangeColumns}
                  className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <Wand2 size={18} />
                  <span>Change Columns</span>
                </button>
              )}
            </div>

            {/* Currently Processing Row - Live Animation */}
            {job.status === 'running' && (
              <div className="mt-4 bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 rounded-xl p-[2px] animate-gradient">
                <div className="bg-gray-900 rounded-xl p-4">
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="relative">
                      <Cpu className="text-blue-400" size={24} />
                      <span className="absolute -top-1 -right-1 flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                      </span>
                    </div>
                    <div>
                      <p className="text-white font-medium flex items-center">
                        <span className="mr-2">Transforming Data</span>
                        <span className="inline-flex">
                          <span className="animate-bounce">.</span>
                          <span className="animate-bounce" style={{ animationDelay: '0.1s' }}>.</span>
                          <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>.</span>
                        </span>
                      </p>
                      <p className="text-blue-300 text-sm">
                        Processing Row {(currentProcessingRow ?? job.processedRows) + 1}
                      </p>
                    </div>
                  </div>
                  
                  {latestSentence && (
                    <div className="bg-gray-800 rounded-lg p-3 border-l-4 border-green-500">
                      <div className="flex items-center space-x-2 mb-1">
                        <Sparkles className="text-yellow-400" size={14} />
                        <span className="text-green-400 text-xs font-medium uppercase tracking-wide">Latest Output</span>
                      </div>
                      <p className="text-gray-200 text-sm italic animate-fadeIn">
                        "{latestSentence}"
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Last Error */}
            {job.lastError && (
              <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-start space-x-2">
                  <AlertTriangle className="text-red-500 flex-shrink-0 mt-0.5" size={18} />
                  <div>
                    <p className="font-medium text-red-700">Last Error</p>
                    <p className="text-sm text-red-600 mt-1">{job.lastError}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start space-x-2">
              <XCircle className="text-red-500 flex-shrink-0 mt-0.5" size={18} />
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}
      </div>

      {/* Results (custom view preferred; avoids duplicate lists) */}
      {customResultsView ? (
        customResultsView
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <h3 className="font-semibold text-gray-900">Results ({totalResults})</h3>
              {newResultsCount > 0 && job?.status === 'running' && (
                <span className="inline-flex items-center px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs font-medium animate-pulse">
                  +{newResultsCount} new
                </span>
              )}
            </div>
            <div className="flex items-center space-x-4">
              {job?.status === 'running' && (
                <div className="flex items-center space-x-1 text-green-600">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                  </span>
                  <span className="text-xs font-medium">Live</span>
                </div>
              )}
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <Clock size={14} />
                <span>Last update: {formatTime(lastUpdateTime)}</span>
              </div>
            </div>
          </div>

          <div ref={logRef} className="max-h-[500px] overflow-y-auto divide-y divide-gray-100">
            {results.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Activity className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p>No results yet</p>
                <p className="text-sm mt-1">Results will appear here when transformation starts</p>
              </div>
            ) : (
              results.map((result, idx) => (
                <button
                  key={`${result.rowIndex}-${idx}`}
                  onClick={() => onSelectResult(result)}
                  className={`w-full text-left p-4 hover:bg-gray-50 transition-all duration-300 ${
                    selectedRowIndex === result.rowIndex ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
                  } ${idx < newResultsCount && currentPage === 0 ? 'animate-fadeIn bg-green-50' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {result.status === 'completed' ? (
                        <CheckCircle className="text-green-500" size={18} />
                      ) : result.status === 'failed' ? (
                        <XCircle className="text-red-500" size={18} />
                      ) : (
                        <Loader2 className="text-blue-500 animate-spin" size={18} />
                      )}
                      <div>
                        <span className="font-medium text-gray-900">Row {result.rowIndex + 1}</span>
                        {result.respondentId && (
                          <span className="text-gray-500 ml-2 text-sm">ID: {result.respondentId}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-4 text-sm">
                      <span className="text-green-600 font-medium">{result.sentences?.length || 0} sentences</span>
                      {result.excluded && (
                        <span className="text-gray-400">
                          {(result.excluded.emptyVars?.length || 0) +
                            (result.excluded.excludedByOption?.length || 0) +
                            (result.excluded.adminVars?.length || 0)}{' '}
                          skipped
                        </span>
                      )}
                    </div>
                  </div>
                  {result.sentences && result.sentences.length > 0 && (
                    <p className="mt-2 text-sm text-gray-600 line-clamp-2">
                      "{result.sentences[0].sentence}"
                      {result.sentences.length > 1 && (
                        <span className="text-gray-400 ml-1">(+{result.sentences.length - 1} more)</span>
                      )}
                    </p>
                  )}
                  {result.errorMessage && (
                    <p className="mt-2 text-sm text-red-600 truncate">⚠️ Error: {result.errorMessage}</p>
                  )}
                </button>
              ))
            )}
          </div>

          {totalPages > 1 && (
            <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between bg-gray-50">
              <p className="text-sm text-gray-600">
                Page {currentPage + 1} / {totalPages}
                <span className="text-gray-400 ml-2">
                  (Showing: {currentPage * pageSize + 1} - {Math.min((currentPage + 1) * pageSize, totalResults)})
                </span>
              </p>
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => onPageChange(0)}
                  disabled={currentPage === 0}
                  className="p-2 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  title="First page"
                >
                  <ChevronsLeft size={18} />
                </button>
                <button
                  onClick={() => onPageChange(currentPage - 1)}
                  disabled={currentPage === 0}
                  className="p-2 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  title="Previous page"
                >
                  <ChevronLeft size={18} />
                </button>

                <div className="flex items-center space-x-1 mx-2">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum;
                    if (totalPages <= 5) pageNum = i;
                    else if (currentPage < 3) pageNum = i;
                    else if (currentPage > totalPages - 4) pageNum = totalPages - 5 + i;
                    else pageNum = currentPage - 2 + i;
                    return (
                      <button
                        key={pageNum}
                        onClick={() => onPageChange(pageNum)}
                        className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                          currentPage === pageNum ? 'bg-blue-600 text-white' : 'hover:bg-gray-200 text-gray-700'
                        }`}
                      >
                        {pageNum + 1}
                      </button>
                    );
                  })}
                </div>

                <button
                  onClick={() => onPageChange(currentPage + 1)}
                  disabled={currentPage >= totalPages - 1}
                  className="p-2 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  title="Next page"
                >
                  <ChevronRight size={18} />
                </button>
                <button
                  onClick={() => onPageChange(totalPages - 1)}
                  disabled={currentPage >= totalPages - 1}
                  className="p-2 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  title="Last page"
                >
                  <ChevronsRight size={18} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Reset Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 bg-red-100 rounded-full">
                <AlertTriangle className="text-red-600" size={24} />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Reset Process</h3>
            </div>

            <p className="text-gray-600 mb-4">
              This operation will delete all transformation results and restart the process from scratch.
              This operation cannot be undone.
            </p>

            <p className="text-sm text-gray-500 mb-2">
              Type <strong>DELETE</strong> below to confirm:
            </p>
            <input
              type="text"
              value={resetConfirmText}
              onChange={(e) => setResetConfirmText(e.target.value)}
              placeholder="DELETE"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 mb-4"
            />

            <div className="flex space-x-3">
              <button
                onClick={() => {
                  setShowResetConfirm(false);
                  setResetConfirmText('');
                }}
                className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleResetConfirm}
                disabled={resetConfirmText !== 'DELETE'}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Reset
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        @keyframes gradient {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        .animate-gradient {
          background-size: 200% 200%;
          animation: gradient 3s ease infinite;
        }
      `}</style>
    </div>
  );
};

export default LiveOutput;
