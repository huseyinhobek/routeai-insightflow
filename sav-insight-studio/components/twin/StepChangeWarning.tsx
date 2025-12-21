import React from 'react';
import { AlertTriangle, X, ChevronLeft, ChevronRight } from 'lucide-react';

interface StepChangeWarningProps {
  show: boolean;
  message: string;
  targetStep: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const StepChangeWarning: React.FC<StepChangeWarningProps> = ({
  show,
  message,
  targetStep,
  onConfirm,
  onCancel,
}) => {
  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 bg-amber-50 rounded-t-2xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-amber-100 rounded-full">
                <AlertTriangle className="text-amber-600" size={24} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Confirm Step Change</h3>
                <p className="text-sm text-gray-600 mt-0.5">
                  Going back to: <strong>{targetStep}</strong>
                </p>
              </div>
            </div>
            <button
              onClick={onCancel}
              className="p-2 hover:bg-amber-100 rounded-lg transition-colors"
            >
              <X size={20} className="text-gray-500" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          <p className="text-gray-700 mb-6">{message}</p>

          <div className="flex space-x-3">
            <button
              onClick={onCancel}
              className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center space-x-2"
            >
              <ChevronLeft size={18} />
              <span>Cancel</span>
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors flex items-center justify-center space-x-2"
            >
              <span>Continue</span>
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StepChangeWarning;

