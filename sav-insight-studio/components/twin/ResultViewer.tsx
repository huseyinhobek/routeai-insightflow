import React, { useState, useMemo } from 'react';
import { 
  MessageSquare, 
  Link2, 
  AlertCircle, 
  CheckCircle,
  XCircle,
  X,
  FileText,
  EyeOff,
  Info
} from 'lucide-react';
import { TransformResult, DatasetMeta } from '../../types';

interface ResultViewerProps {
  result: TransformResult | null;
  datasetMeta?: DatasetMeta | null;
  rowData?: Record<string, any> | null; // Raw row data to show participant's selection
  onClose: () => void;
}

const ResultViewer: React.FC<ResultViewerProps> = ({ result, datasetMeta, rowData, onClose }) => {
  // All hooks must be called before any early returns
  const [showQuestionDetails, setShowQuestionDetails] = useState(false);
  
  // Build variable lookup map
  const varByCode = useMemo(() => {
    const map = new Map<string, DatasetMeta['variables'][number]>();
    if (datasetMeta?.variables) {
      datasetMeta.variables.forEach(v => map.set(v.code, v));
    }
    return map;
  }, [datasetMeta]);

  // Early return after all hooks
  if (!result) return null;

  const totalExcluded = 
    (result.excluded?.emptyVars?.length || 0) +
    (result.excluded?.excludedByOption?.length || 0) +
    (result.excluded?.adminVars?.length || 0) +
    (result.excluded?.excludedVariables?.length || 0);

  const getVarInfo = (code: string) => {
    return varByCode.get(code);
  };

  // Get participant's selection (label value) for a variable
  const getParticipantSelection = (code: string): string | null => {
    if (!rowData || !varByCode.has(code)) return null;
    const value = rowData[code];
    if (value === null || value === undefined) return null;
    
    const varInfo = varByCode.get(code);
    if (!varInfo?.valueLabels) return String(value);
    
    // Find matching label
    const match = varInfo.valueLabels.find(vl => vl.value === value);
    if (match) return match.label;
    
    // For arrays (multi-choice)
    if (Array.isArray(value)) {
      const labels = value
        .map(v => varInfo.valueLabels.find(vl => vl.value === v)?.label || String(v))
        .filter(Boolean);
      return labels.length > 0 ? labels.join(', ') : null;
    }
    
    return String(value);
  };

  const VariableCode: React.FC<{ code: string; reason?: string }> = ({ code, reason }) => {
    const varInfo = getVarInfo(code);
    const hasInfo = Boolean(varInfo);
    const participantSelection = showQuestionDetails ? getParticipantSelection(code) : null;
    
    return (
      <div className="w-full">
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
            hasInfo 
              ? 'bg-blue-100 text-blue-700' 
              : 'bg-gray-100 text-gray-600'
          }`}
        >
          {code}
          {hasInfo && <Info size={12} className="ml-1" />}
        </span>
        
        {/* Question details below code when toggle is on */}
        {showQuestionDetails && varInfo && (
          <div className="mt-2 ml-0 text-xs text-gray-600 space-y-1">
            <div className="font-medium text-gray-700">{varInfo.label || 'No label'}</div>
            {participantSelection && (
              <div className="text-green-700">
                Participant's Selection: <span className="font-medium">{participantSelection}</span>
              </div>
            )}
            {reason && (
              <div className="text-amber-600 text-[11px]">Reason: {reason}</div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-3">
              {result.status === 'completed' ? (
                <CheckCircle className="text-green-500" size={24} />
              ) : result.status === 'failed' ? (
                <XCircle className="text-red-500" size={24} />
              ) : (
                <AlertCircle className="text-amber-500" size={24} />
              )}
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Row {result.rowIndex + 1} Details
                </h2>
                {result.respondentId && (
                  <p className="text-sm text-gray-500">ID: {result.respondentId}</p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
            >
              <X size={20} className="text-gray-500" />
            </button>
          </div>
          {/* Toggle Button */}
          <button
            onClick={() => setShowQuestionDetails(!showQuestionDetails)}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            <Info size={16} />
            <span>{showQuestionDetails ? 'Hide' : 'Show'} Question Text and Selections</span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-green-50 rounded-lg p-4 text-center">
              <MessageSquare className="w-6 h-6 mx-auto text-green-600 mb-2" />
              <p className="text-2xl font-bold text-green-600">
                {result.sentences?.length || 0}
              </p>
              <p className="text-sm text-green-700">Sentences</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <EyeOff className="w-6 h-6 mx-auto text-gray-600 mb-2" />
              <p className="text-2xl font-bold text-gray-600">{totalExcluded}</p>
              <p className="text-sm text-gray-700">Skipped</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-4 text-center">
              <FileText className="w-6 h-6 mx-auto text-purple-600 mb-2" />
              <p className="text-2xl font-bold text-purple-600">{result.retryCount}</p>
              <p className="text-sm text-purple-700">Retries</p>
            </div>
          </div>

          {/* Sentences */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center space-x-2">
              <MessageSquare size={18} />
              <span>Generated Sentences</span>
            </h3>
            
            {result.sentences && result.sentences.length > 0 ? (
              <div className="space-y-3">
                {result.sentences.map((sentence, idx) => (
                  <div
                    key={idx}
                    className="bg-gray-50 rounded-lg p-4 border border-gray-200"
                  >
                    <p className="text-gray-900 leading-relaxed">
                      "{sentence.sentence}"
                    </p>
                    <div className="mt-3 flex flex-wrap items-start gap-2">
                      <Link2 size={14} className="text-gray-400 mt-1" />
                      <div className="flex flex-wrap gap-2">
                        {sentence.sources.map((source, sIdx) => (
                          <VariableCode key={sIdx} code={source} />
                        ))}
                      </div>
                    </div>
                    {sentence.warnings && sentence.warnings.length > 0 && (
                      <div className="mt-2 flex items-start space-x-2">
                        <AlertCircle size={14} className="text-amber-500 mt-0.5" />
                        <p className="text-sm text-amber-600">
                          {sentence.warnings.join(', ')}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-gray-50 rounded-lg p-6 text-center text-gray-500">
                <MessageSquare className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                <p>No sentences generated for this row</p>
              </div>
            )}
          </div>

          {/* Excluded Variables */}
          {totalExcluded > 0 && (
            <div>
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center space-x-2">
                <EyeOff size={18} />
                <span>Skipped Variables</span>
              </h3>
              
              <div className="space-y-3">
                {result.excluded?.emptyVars && result.excluded.emptyVars.length > 0 && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm font-medium text-gray-700 mb-3">
                      Empty Values ({result.excluded.emptyVars.length})
                    </p>
                    <div className="space-y-2">
                      {result.excluded.emptyVars.map((v, idx) => (
                        <div key={idx} className="bg-white rounded border border-gray-200 p-2">
                          <VariableCode code={v} reason="Empty value" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {result.excluded?.excludedByOption && result.excluded.excludedByOption.length > 0 && (
                  <div className="bg-amber-50 rounded-lg p-4">
                    <p className="text-sm font-medium text-amber-700 mb-3">
                      Excluded Options ({result.excluded.excludedByOption.length})
                    </p>
                    <div className="space-y-2">
                      {result.excluded.excludedByOption.map((v, idx) => (
                        <div key={idx} className="bg-white rounded border border-amber-200 p-2">
                          <VariableCode code={v} reason="Excluded option (e.g., 'None of the above')" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {result.excluded?.excludedVariables && result.excluded.excludedVariables.length > 0 && (
                  <div className="bg-orange-50 rounded-lg p-4">
                    <p className="text-sm font-medium text-orange-700 mb-3">
                      User Excluded Columns ({result.excluded.excludedVariables.length})
                    </p>
                    <div className="space-y-2">
                      {result.excluded.excludedVariables.map((v, idx) => (
                        <div key={idx} className="bg-white rounded border border-orange-200 p-2">
                          <VariableCode code={v} reason="User excluded column" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {result.excluded?.adminVars && result.excluded.adminVars.length > 0 && (
                  <div className="bg-blue-50 rounded-lg p-4">
                    <p className="text-sm font-medium text-blue-700 mb-3">
                      Admin Columns ({result.excluded.adminVars.length})
                    </p>
                    <div className="space-y-2">
                      {result.excluded.adminVars.map((v, idx) => (
                        <div key={idx} className="bg-white rounded border border-blue-200 p-2">
                          <VariableCode code={v} reason="Admin/metadata column" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Error Message */}
          {result.errorMessage && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <XCircle className="text-red-500 flex-shrink-0 mt-0.5" size={18} />
                <div>
                  <p className="font-medium text-red-700">Error Details</p>
                  <p className="text-sm text-red-600 mt-1">{result.errorMessage}</p>
                </div>
              </div>
            </div>
          )}

          {/* Trace Info (Collapsed by Default) */}
          {result.rawTrace && (
            <details className="bg-gray-50 rounded-lg border border-gray-200">
              <summary className="px-4 py-3 cursor-pointer font-medium text-gray-700 hover:bg-gray-100">
                Technical Details (Debug)
              </summary>
              <div className="px-4 pb-4">
                <pre className="text-xs text-gray-600 overflow-x-auto bg-white p-3 rounded border">
                  {JSON.stringify(result.rawTrace, null, 2)}
                </pre>
              </div>
            </details>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ResultViewer;

