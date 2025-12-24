import React from 'react';
import { AlertTriangle, X, RotateCcw, Play, XCircle } from 'lucide-react';

interface SettingsChangeWarningProps {
  show: boolean;
  lastProcessedRow: number;
  onContinueWithNewSettings: () => void;
  onRestartFromBeginning: () => void;
  onCancelChanges: () => void;
  onClose: () => void;
}

const SettingsChangeWarning: React.FC<SettingsChangeWarningProps> = ({
  show,
  lastProcessedRow,
  onContinueWithNewSettings,
  onRestartFromBeginning,
  onCancelChanges,
  onClose,
}) => {
  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 bg-amber-50 rounded-t-2xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-amber-100 rounded-full">
                <AlertTriangle className="text-amber-600" size={24} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Settings Changed</h3>
                <p className="text-sm text-gray-600 mt-0.5">
                  Transformation settings have been modified
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-amber-100 rounded-lg transition-colors"
            >
              <X size={20} className="text-gray-500" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <p className="text-sm text-gray-700">
              <strong>{lastProcessedRow}</strong> rows have already been processed with the previous settings.
            </p>
          </div>

          <p className="text-gray-700 mb-6">
            What would you like to do with the new settings?
          </p>

          <div className="space-y-3">
            <button
              onClick={onContinueWithNewSettings}
              className="w-full flex items-center space-x-3 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-left"
            >
              <Play size={20} />
              <div className="flex-1">
                <div className="font-medium">Continue with new settings</div>
                <div className="text-sm text-green-100">
                  Process remaining rows from row {lastProcessedRow + 1} with new settings
                </div>
              </div>
            </button>

            <button
              onClick={onRestartFromBeginning}
              className="w-full flex items-center space-x-3 px-4 py-3 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors text-left"
            >
              <RotateCcw size={20} />
              <div className="flex-1">
                <div className="font-medium">Restart from beginning</div>
                <div className="text-sm text-amber-100">
                  Reset all progress and start over with new settings
                </div>
              </div>
            </button>

            <button
              onClick={onCancelChanges}
              className="w-full flex items-center space-x-3 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-left"
            >
              <XCircle size={20} />
              <div className="flex-1">
                <div className="font-medium">Cancel changes and resume</div>
                <div className="text-sm text-gray-600">
                  Keep previous settings and continue from where you left off
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsChangeWarning;

