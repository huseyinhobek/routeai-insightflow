import React, { useState } from 'react';
import { X, Sparkles, User, Bot } from 'lucide-react';

interface SmartFilterInfo {
  id: string;
  title: string;
  sourceVars: string[];
  source?: 'ai' | 'manual';
}

interface ExportSettingsModalProps {
  show: boolean;
  onClose: () => void;
  onExport: (settings: ExportSettings) => void;
  defaultSettings: ExportSettings;
  smartFilters?: SmartFilterInfo[];
}

export interface ExportSettings {
  productId: string;
  productName: string;
  dataSource: string;
  reviewRating: number;
  reviewTitle: string; // Manual review title (optional, auto-generated if empty)
  smartFilters: SmartFilterInfo[]; // Applied smart filters to include
}

export const ExportSettingsModal: React.FC<ExportSettingsModalProps> = ({
  show,
  onClose,
  onExport,
  defaultSettings,
  smartFilters = []
}) => {
  const [settings, setSettings] = useState<ExportSettings>({
    ...defaultSettings,
    reviewTitle: defaultSettings.reviewTitle || '',
    smartFilters: smartFilters
  });

  // Update smartFilters when prop changes (e.g., when filters are added/removed)
  React.useEffect(() => {
    setSettings(prev => ({
      ...prev,
      smartFilters: smartFilters
    }));
  }, [smartFilters]);

  if (!show) return null;

  const handleExport = () => {
    onExport(settings);
    onClose();
  };

  // Generate column name preview for smart filters
  const getFilterColumnName = (title: string) => {
    return title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '') + '_sf';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">Export Settings</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">CSV Format</h3>
            <p className="text-sm text-blue-800">
              product_id, product_name, data_source, review_date, review_rating, review_content, review_title, reviewer_id, reviewer_name
              {smartFilters.length > 0 && (
                <span className="text-purple-700 font-medium">
                  , {smartFilters.map(f => getFilterColumnName(f.title)).join(', ')}
                </span>
              )}
            </p>
          </div>

          {/* Product ID */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Product ID <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={settings.productId}
              onChange={(e) => setSettings({ ...settings, productId: e.target.value })}
              placeholder="e.g., PROD-001"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-sm text-gray-500 mt-1">
              Unique identifier for the product (same for all rows)
            </p>
          </div>

          {/* Product Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Product Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={settings.productName}
              onChange={(e) => setSettings({ ...settings, productName: e.target.value })}
              placeholder="e.g., Virgin Masterbrand - USA 2024"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-sm text-gray-500 mt-1">
              Product name (same for all rows, editable)
            </p>
          </div>

          {/* Data Source */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Data Source
            </label>
            <input
              type="text"
              value={settings.dataSource}
              onChange={(e) => setSettings({ ...settings, dataSource: e.target.value })}
              placeholder="e.g., survey_data.sav"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-sm text-gray-500 mt-1">
              Source filename (defaults to uploaded file name)
            </p>
          </div>

          {/* Review Rating */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Review Rating (Default)
            </label>
            <input
              type="number"
              min="1"
              max="5"
              step="0.1"
              value={settings.reviewRating}
              onChange={(e) => setSettings({ ...settings, reviewRating: parseFloat(e.target.value) || 5.0 })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-sm text-gray-500 mt-1">
              Default rating for all reviews (1.0 - 5.0)
            </p>
          </div>

          {/* Review Title (Manual) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Review Title (Optional)
            </label>
            <input
              type="text"
              value={settings.reviewTitle}
              onChange={(e) => setSettings({ ...settings, reviewTitle: e.target.value })}
              placeholder="Leave empty for auto-generated titles"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-sm text-gray-500 mt-1">
              Same title for all rows. Leave empty to auto-generate from content (first 50 chars).
            </p>
          </div>

          {/* Smart Filters Section */}
          {smartFilters.length > 0 && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <h4 className="font-semibold text-purple-900 mb-3 flex items-center gap-2">
                <Sparkles size={16} />
                Smart Filter Columns ({smartFilters.length})
              </h4>
              <p className="text-sm text-purple-800 mb-3">
                These filters will be added as columns at the end of CSV with <code className="bg-purple-100 px-1 rounded">_sf</code> suffix:
              </p>
              <div className="space-y-2">
                {smartFilters.map(f => (
                  <div key={f.id} className="flex items-center justify-between bg-white rounded-lg p-2 border border-purple-100">
                    <div className="flex items-center gap-2">
                      {f.source === 'ai' ? (
                        <Bot size={14} className="text-purple-500" />
                      ) : (
                        <User size={14} className="text-gray-500" />
                      )}
                      <span className="text-sm font-medium text-gray-900">{f.title}</span>
                    </div>
                    <code className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-600">
                      {getFilterColumnName(f.title)}
                    </code>
                  </div>
                ))}
              </div>
              <p className="text-xs text-purple-600 mt-3">
                Values will be extracted from original dataset rows using source variables: {smartFilters.flatMap(f => f.sourceVars).slice(0, 5).join(', ')}
                {smartFilters.flatMap(f => f.sourceVars).length > 5 && '...'}
              </p>
            </div>
          )}

          {/* Info Box */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-2">Automatic Fields</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• <strong>review_date:</strong> Current date (MM-DD-YYYY format)</li>
              <li>• <strong>review_content:</strong> All transformed sentences for each row</li>
              <li>• <strong>review_title:</strong> {settings.reviewTitle ? 'Manual title (same for all)' : 'Auto-generated from content'}</li>
              <li>• <strong>reviewer_id:</strong> Selected ID column or row index</li>
              <li>• <strong>reviewer_name:</strong> Anonymous1, Anonymous2, ... (sequential)</li>
              {smartFilters.length > 0 && (
                <li>• <strong>Smart Filters:</strong> Added as lowercase columns with _sf suffix</li>
              )}
            </ul>
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
            onClick={handleExport}
            disabled={!settings.productId || !settings.productName}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Export CSV
          </button>
        </div>
      </div>
    </div>
  );
};
