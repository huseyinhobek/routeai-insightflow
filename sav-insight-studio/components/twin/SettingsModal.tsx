import React from 'react';
import { X } from 'lucide-react';

interface SettingsModalProps {
  show: boolean;
  onClose: () => void;
  chunkSize: number;
  rowConcurrency: number;
  rowLimit: number | null;
  onChunkSizeChange: (value: number) => void;
  onRowConcurrencyChange: (value: number) => void;
  onRowLimitChange: (value: number | null) => void;
  onApply: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  show,
  onClose,
  chunkSize,
  rowConcurrency,
  rowLimit,
  onChunkSizeChange,
  onRowConcurrencyChange,
  onRowLimitChange,
  onApply
}) => {
  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">Transform Settings</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Chunk Size */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Chunk Size (Columns per Request)
            </label>
            <input
              type="number"
              min="10"
              max="100"
              value={chunkSize}
              onChange={(e) => onChunkSizeChange(parseInt(e.target.value) || 30)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-sm text-gray-500 mt-1">
              Number of columns to process per AI request. Lower values = more requests but smaller context.
            </p>
          </div>

          {/* Row Concurrency */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Row Concurrency (Parallel Rows)
            </label>
            <input
              type="number"
              min="1"
              max="20"
              value={rowConcurrency}
              onChange={(e) => onRowConcurrencyChange(parseInt(e.target.value) || 5)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-sm text-gray-500 mt-1">
              Number of rows to process in parallel. Higher values = faster but more resource intensive.
            </p>
          </div>

          {/* Row Limit */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Row Limit (Max Rows to Process)
            </label>
            <div className="flex items-center space-x-4">
              <input
                type="number"
                min="1"
                value={rowLimit || ''}
                placeholder="All rows"
                onChange={(e) => {
                  const val = e.target.value;
                  onRowLimitChange(val ? parseInt(val) : null);
                }}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={() => onRowLimitChange(null)}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Clear
              </button>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              Limit the number of rows to process. Leave empty to process all rows.
            </p>
          </div>
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

