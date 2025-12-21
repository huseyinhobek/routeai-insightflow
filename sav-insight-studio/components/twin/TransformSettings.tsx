import React, { useState } from 'react';
import { 
  Settings, 
  Layers, 
  Users, 
  Info,
  Zap,
  TestTube,
  Rocket,
  AlertTriangle,
  Play,
  RotateCcw
} from 'lucide-react';
import { TransformJob } from '../../types';

interface TransformSettingsProps {
  chunkSize: number;
  rowConcurrency: number;
  rowLimit: number;
  processAllRows: boolean;
  onChunkSizeChange: (value: number) => void;
  onRowConcurrencyChange: (value: number) => void;
  onRowLimitChange: (value: number) => void;
  onProcessAllRowsChange: (value: boolean) => void;
  totalColumns: number;
  totalRows: number;
  excludedColumns: number;
  respondentIdColumn: string;
  onRespondentIdColumnChange: (value: string) => void;
  idColumnOptions: Array<{ code: string; label: string }>;
  currentJob?: TransformJob | null;
  onStart: (continueFromExisting: boolean) => void;
  onReset?: () => void;
}

const TransformSettings: React.FC<TransformSettingsProps> = ({
  chunkSize,
  rowConcurrency,
  rowLimit,
  processAllRows,
  onChunkSizeChange,
  onRowConcurrencyChange,
  onRowLimitChange,
  onProcessAllRowsChange,
  totalColumns,
  totalRows,
  excludedColumns,
  respondentIdColumn,
  onRespondentIdColumnChange,
  idColumnOptions,
  currentJob,
  onStart,
  onReset,
}) => {
  const [continueMode, setContinueMode] = useState<'continue' | 'restart'>('continue');
  const activeColumns = totalColumns - excludedColumns;
  const estimatedChunks = Math.ceil(activeColumns / chunkSize);
  const effectiveRows = processAllRows ? totalRows : rowLimit;
  const estimatedApiCalls = effectiveRows * estimatedChunks;
  const estimatedSeconds = Math.ceil(estimatedApiCalls * 2.5 / rowConcurrency);
  const estimatedMinutes = Math.ceil(estimatedSeconds / 60);
  
  const hasExistingJob = currentJob && ['completed', 'paused', 'failed'].includes(currentJob.status);
  const canContinue = hasExistingJob && (
    processAllRows || 
    (rowLimit > (currentJob.processedRows || 0))
  );

  return (
    <div className="space-y-6">
      {/* Respondent ID Column */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">ID Column</h3>
            <p className="text-sm text-gray-500 mt-1">
              Which column should be used as "ID" in the transformation results?
            </p>
          </div>
        </div>
        <div className="mt-4">
          <select
            value={respondentIdColumn}
            onChange={(e) => onRespondentIdColumnChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Auto-detect (recommended)</option>
            {idColumnOptions.map((opt) => {
              const isAutoDetected = opt.code === respondentIdColumn && respondentIdColumn !== '';
              return (
                <option key={opt.code} value={opt.code}>
                  {opt.code}{opt.label ? ` — ${opt.label}` : ''}
                  {isAutoDetected ? ' ⭐ (Auto-detected)' : ''}
                </option>
              );
            })}
          </select>
          {respondentIdColumn && (
            <div className="mt-2 flex items-center space-x-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg">
              <span className="text-blue-600 text-sm font-medium">✓</span>
              <span className="text-blue-700 text-sm">
                Using <strong>{respondentIdColumn}</strong> as ID column
              </span>
            </div>
          )}
          <p className="text-xs text-gray-400 mt-2">
            Note: This selection only affects the "respondentId/ID" field in results; it does not change columns sent to the model.
          </p>
        </div>
      </div>

      {/* Test Mode / Full Mode Toggle */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${processAllRows ? 'bg-green-100' : 'bg-amber-100'}`}>
              {processAllRows ? <Rocket className="text-green-600" size={20} /> : <TestTube className="text-amber-600" size={20} />}
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">
                {processAllRows ? 'Full Transformation Mode' : 'Test Mode'}
              </h3>
              <p className="text-sm text-gray-500">
                {processAllRows 
                  ? `All ${totalRows.toLocaleString()} rows will be processed` 
                  : `First ${rowLimit} rows will be processed (for testing)`}
              </p>
            </div>
          </div>
          
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={processAllRows}
              onChange={(e) => onProcessAllRowsChange(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-14 h-7 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:start-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-green-600"></div>
            <span className="ml-3 text-sm font-medium text-gray-700">
              {processAllRows ? 'All' : 'Test'}
            </span>
          </label>
        </div>

        {!processAllRows && (
          <div className="mt-4 space-y-3">
            <label className="block text-sm font-medium text-gray-700">
              Number of rows for testing
            </label>
            <div className="flex items-center space-x-3">
              <input
                type="range"
                min={1}
                max={Math.min(100, totalRows)}
                value={rowLimit}
                onChange={(e) => onRowLimitChange(parseInt(e.target.value))}
                className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-amber-500"
              />
              <input
                type="number"
                min={1}
                max={totalRows}
                value={rowLimit}
                onChange={(e) => onRowLimitChange(Math.max(1, Math.min(totalRows, parseInt(e.target.value) || 1)))}
                className="w-20 px-3 py-2 border border-gray-300 rounded-lg text-center font-semibold"
              />
            </div>
            <div className="flex space-x-2">
              {[5, 10, 25, 50, 100].map((val) => (
                <button
                  key={val}
                  onClick={() => onRowLimitChange(Math.min(val, totalRows))}
                  className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${
                    rowLimit === val
                      ? 'bg-amber-500 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {val}
                </button>
              ))}
            </div>
          </div>
        )}

        {processAllRows && totalRows > 1000 && (
          <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start space-x-2">
            <AlertTriangle className="text-amber-600 mt-0.5 flex-shrink-0" size={16} />
            <p className="text-sm text-amber-800">
              <strong>{totalRows.toLocaleString()}</strong> rows will be processed. This operation may take a long time and may incur API costs.
            </p>
          </div>
        )}
      </div>

      {/* Estimation Card */}
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-200 p-6">
        <div className="flex items-start space-x-3 mb-4">
          <Zap className="text-blue-600 mt-0.5" size={20} />
          <div>
            <h3 className="font-semibold text-gray-900">Transformation Estimate</h3>
            <p className="text-sm text-gray-600 mt-1">
              Process estimate with current settings
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white/70 rounded-lg p-3">
            <p className="text-sm text-gray-500">Rows to Process</p>
            <p className="text-xl font-bold text-gray-900">{effectiveRows.toLocaleString()}</p>
          </div>
          <div className="bg-white/70 rounded-lg p-3">
            <p className="text-sm text-gray-500">Active Columns</p>
            <p className="text-xl font-bold text-gray-900">{activeColumns}</p>
          </div>
          <div className="bg-white/70 rounded-lg p-3">
            <p className="text-sm text-gray-500">Chunks per Row</p>
            <p className="text-xl font-bold text-gray-900">{estimatedChunks}</p>
          </div>
          <div className="bg-white/70 rounded-lg p-3">
            <p className="text-sm text-gray-500">Total API Calls</p>
            <p className="text-xl font-bold text-blue-600">{estimatedApiCalls.toLocaleString()}</p>
          </div>
          <div className="bg-white/70 rounded-lg p-3">
            <p className="text-sm text-gray-500">Estimated Time</p>
            <p className="text-xl font-bold text-green-600">
              {estimatedMinutes < 60 
                ? `~${estimatedMinutes} min` 
                : `~${(estimatedMinutes / 60).toFixed(1)} hr`}
            </p>
          </div>
        </div>
      </div>

      {/* Settings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Chunk Size Setting */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Layers className="text-purple-600" size={20} />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Chunk Size</h3>
              <p className="text-sm text-gray-500">Number of columns per API request</p>
            </div>
          </div>

          <div className="space-y-4">
            <input
              type="range"
              min={10}
              max={100}
              step={10}
              value={chunkSize}
              onChange={(e) => onChunkSizeChange(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
            />

            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">10</span>
              <span className="text-2xl font-bold text-purple-600">{chunkSize}</span>
              <span className="text-sm text-gray-500">100</span>
            </div>

            <div className="flex space-x-2">
              {[20, 30, 50, 75, 100].map((val) => (
                <button
                  key={val}
                  onClick={() => onChunkSizeChange(val)}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                    chunkSize === val
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {val}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Row Concurrency Setting */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-green-100 rounded-lg">
              <Users className="text-green-600" size={20} />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Parallel Requests</h3>
              <p className="text-sm text-gray-500">Number of rows to process simultaneously</p>
            </div>
          </div>

          <div className="space-y-4">
            <input
              type="range"
              min={1}
              max={100}
              step={1}
              value={rowConcurrency}
              onChange={(e) => onRowConcurrencyChange(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-600"
            />

            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">1</span>
              <span className="text-2xl font-bold text-green-600">{rowConcurrency}</span>
              <span className="text-sm text-gray-500">100</span>
            </div>

            <div className="flex flex-wrap gap-2">
              {[1, 5, 10, 25, 50, 100].map((val) => (
                <button
                  key={val}
                  onClick={() => onRowConcurrencyChange(val)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    rowConcurrency === val
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {val}
                </button>
              ))}
            </div>

            {rowConcurrency > 50 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start space-x-2">
                <Info className="text-amber-600 mt-0.5 flex-shrink-0" size={16} />
                <p className="text-sm text-amber-800">
                  High parallel requests may hit API rate limits.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Settings className="text-blue-600" size={20} />
          </div>
          <h3 className="font-semibold text-gray-900">Settings Summary</h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500 mb-1">Mode</p>
            <p className="text-lg font-semibold text-gray-900">
              {processAllRows ? 'Full' : 'Test'}
            </p>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500 mb-1">Rows</p>
            <p className="text-lg font-semibold text-gray-900">{effectiveRows}</p>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500 mb-1">Chunk</p>
            <p className="text-lg font-semibold text-gray-900">{chunkSize}</p>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500 mb-1">Parallel</p>
            <p className="text-lg font-semibold text-gray-900">{rowConcurrency}</p>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500 mb-1">Model</p>
            <p className="text-lg font-semibold text-gray-900">GPT-5 mini</p>
          </div>
        </div>
      </div>

      {/* Continue/Restart Options */}
      {hasExistingJob && (
        <div className="bg-blue-50 rounded-xl border border-blue-200 shadow-sm p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Info className="text-blue-600" size={20} />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Existing Job Found</h3>
              <p className="text-sm text-gray-600 mt-1">
                {currentJob.processedRows} of {currentJob.totalRows} rows processed
              </p>
            </div>
          </div>
          
          <div className="space-y-3">
            <div className="flex items-center space-x-3">
              <input
                type="radio"
                id="continue-mode"
                name="job-mode"
                value="continue"
                checked={continueMode === 'continue'}
                onChange={() => setContinueMode('continue')}
                disabled={!canContinue}
                className="w-4 h-4 text-blue-600"
              />
              <label htmlFor="continue-mode" className={`flex-1 ${!canContinue ? 'opacity-50' : 'cursor-pointer'}`}>
                <div className="font-medium text-gray-900">Continue from where left off</div>
                <div className="text-sm text-gray-600">
                  {canContinue 
                    ? `Process rows ${(currentJob.processedRows || 0) + 1} to ${effectiveRows} (${effectiveRows - (currentJob.processedRows || 0)} more rows)`
                    : 'Not available: New row limit must be higher than already processed rows'}
                </div>
              </label>
            </div>
            
            <div className="flex items-center space-x-3">
              <input
                type="radio"
                id="restart-mode"
                name="job-mode"
                value="restart"
                checked={continueMode === 'restart'}
                onChange={() => setContinueMode('restart')}
                className="w-4 h-4 text-blue-600"
              />
              <label htmlFor="restart-mode" className="flex-1 cursor-pointer">
                <div className="font-medium text-gray-900">Start from beginning</div>
                <div className="text-sm text-gray-600">
                  Reset and process all {effectiveRows} rows from the start
                </div>
              </label>
            </div>
          </div>
          
          <div className="mt-4 flex items-center space-x-3">
            <button
              onClick={() => onStart(continueMode === 'continue')}
              disabled={continueMode === 'continue' && !canContinue}
              className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Play size={18} />
              <span>{continueMode === 'continue' ? 'Continue' : 'Start'}</span>
            </button>
            
            {onReset && (
              <button
                onClick={onReset}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
              >
                <RotateCcw size={18} />
                <span>Reset Job</span>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TransformSettings;
