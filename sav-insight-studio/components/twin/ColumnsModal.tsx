import React, { useState } from 'react';
import { X, Search } from 'lucide-react';
import { ColumnAnalysisResult } from '../../types';

interface ColumnsModalProps {
  show: boolean;
  onClose: () => void;
  columnAnalysis: ColumnAnalysisResult | null;
  selectedAdminColumns: string[];
  excludePatternVariables: Record<string, string[]>;
  onAdminColumnsChange: (columns: string[]) => void;
  onExcludePatternVariablesChange: (patterns: Record<string, string[]>) => void;
  onApply: () => void;
}

export const ColumnsModal: React.FC<ColumnsModalProps> = ({
  show,
  onClose,
  columnAnalysis,
  selectedAdminColumns,
  excludePatternVariables,
  onAdminColumnsChange,
  onExcludePatternVariablesChange,
  onApply
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  if (!show) return null;
  
  // If no column analysis available, show a message
  if (!columnAnalysis) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">Column Selection</h2>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
              <X size={24} />
            </button>
          </div>
          <p className="text-gray-600">
            Column analysis not available. Please complete the Analysis step first.
          </p>
          <button
            onClick={onClose}
            className="mt-4 w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  // Ensure adminColumns is an array
  const adminColumns = Array.isArray(columnAnalysis.adminColumns) ? columnAnalysis.adminColumns : [];
  const filteredAdminColumns = adminColumns.filter(col =>
    col.code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    col.label?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Convert excludeCandidates array to object for easier access
  const excludeCandidatesObj: Record<string, any[]> = {};
  if (Array.isArray(columnAnalysis.excludeCandidates)) {
    columnAnalysis.excludeCandidates.forEach((candidate: any) => {
      if (candidate.patternKey && candidate.affectedVariables) {
        excludeCandidatesObj[candidate.patternKey] = candidate.affectedVariables.map((code: string) => ({
          code,
          label: candidate.label
        }));
      }
    });
  }

  const toggleAdminColumn = (code: string) => {
    if (selectedAdminColumns.includes(code)) {
      onAdminColumnsChange(selectedAdminColumns.filter(c => c !== code));
    } else {
      onAdminColumnsChange([...selectedAdminColumns, code]);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">Column Selection</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Search */}
        <div className="p-6 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search columns..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Admin Columns */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              Admin Columns ({selectedAdminColumns.length} excluded)
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Select columns to exclude from transformation (e.g., timestamps, IDs, metadata)
            </p>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {filteredAdminColumns.map((col) => (
                <label
                  key={col.code}
                  className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedAdminColumns.includes(col.code)}
                    onChange={() => toggleAdminColumn(col.code)}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">{col.code}</div>
                    {col.label && (
                      <div className="text-sm text-gray-500">{col.label}</div>
                    )}
                  </div>
                  <div className="text-xs text-gray-400">
                    {col.responseRate !== undefined && `${(col.responseRate * 100).toFixed(0)}% response`}
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Exclude Patterns */}
          {Object.keys(excludeCandidatesObj).length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Exclude Patterns
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                Select which columns should have specific values excluded (e.g., "Don't know", "Prefer not to say")
              </p>
              <div className="space-y-4">
                {Object.entries(excludeCandidatesObj).map(([patternKey, candidates]) => (
                  <div key={patternKey} className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2 capitalize">
                      {patternKey.replace(/_/g, ' ')}
                    </h4>
                    <div className="space-y-1">
                      {Array.isArray(candidates) && candidates.map((candidate) => (
                        <label
                          key={candidate.code}
                          className="flex items-center space-x-2 text-sm"
                        >
                          <input
                            type="checkbox"
                            checked={(excludePatternVariables[patternKey] || []).includes(candidate.code)}
                            onChange={(e) => {
                              const current = excludePatternVariables[patternKey] || [];
                              const updated = e.target.checked
                                ? [...current, candidate.code]
                                : current.filter(c => c !== candidate.code);
                              onExcludePatternVariablesChange({
                                ...excludePatternVariables,
                                [patternKey]: updated
                              });
                            }}
                            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                          />
                          <span className="text-gray-700">{candidate.code}</span>
                          {candidate.label && (
                            <span className="text-gray-500">- {candidate.label}</span>
                          )}
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onApply();
              onClose();
            }}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Apply Changes
          </button>
        </div>
      </div>
    </div>
  );
};

