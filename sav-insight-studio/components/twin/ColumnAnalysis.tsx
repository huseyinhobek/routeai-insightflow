import React, { useMemo, useState } from 'react';
import { 
  Shield, 
  XCircle, 
  ChevronDown, 
  ChevronUp,
  ToggleLeft,
  ToggleRight,
  Search,
  Filter
} from 'lucide-react';
import { AdminColumn, ExcludeCandidate } from '../../types';

interface ColumnAnalysisProps {
  adminColumns: AdminColumn[];
  excludedByDefaultColumns?: AdminColumn[];
  excludeCandidates: ExcludeCandidate[];
  totalColumns: number;
  totalRows: number;
  // Admin columns: seçiliyse GÖNDERME demek
  selectedAdminColumns: string[];
  onAdminColumnToggle: (code: string) => void;
  onSelectAllAdmin: (select: boolean) => void;
  // Otomatik hariç sütunlar (None/All of the above checkbox kolonları vs): seçiliyse GÖNDERME demek
  excludedVariables: string[];
  onExcludedVariableToggle: (code: string) => void;
  onSelectAllExcludedVariables: (select: boolean, allCodes: string[]) => void;
  // Exclude patterns: pattern aktif mi?
  excludeConfig: Record<string, boolean>;
  onExcludeToggle: (patternKey: string) => void;
  // Pattern bazında değişken seçimi: seçiliyse o değişkende “none/dk/refused” gibi seçenekler atlanır
  excludePatternVariables: Record<string, string[]>;
  onExcludePatternVariableToggle: (patternKey: string, code: string) => void;
  onExcludePatternSelectAll: (patternKey: string, select: boolean, allVars: string[]) => void;
}

const ColumnAnalysis: React.FC<ColumnAnalysisProps> = ({
  adminColumns,
  excludedByDefaultColumns = [],
  excludeCandidates,
  totalColumns,
  totalRows,
  selectedAdminColumns,
  onAdminColumnToggle,
  onSelectAllAdmin,
  excludedVariables,
  onExcludedVariableToggle,
  onSelectAllExcludedVariables,
  excludeConfig,
  onExcludeToggle,
  excludePatternVariables,
  onExcludePatternVariableToggle,
  onExcludePatternSelectAll,
}) => {
  const [adminExpanded, setAdminExpanded] = useState(true);
  const [excludedColsExpanded, setExcludedColsExpanded] = useState(true);
  const [excludePatternsExpanded, setExcludePatternsExpanded] = useState(true);
  const [adminSearch, setAdminSearch] = useState('');
  const [excludedColsSearch, setExcludedColsSearch] = useState('');
  const [patternSearch, setPatternSearch] = useState('');

  const excludedByDefaultAllCodes = useMemo(() => excludedByDefaultColumns.map(c => c.code), [excludedByDefaultColumns]);
  const excludedByDefaultSelected = useMemo(() => new Set(excludedVariables), [excludedVariables]);

  // Detect duplicate exclusions: same column in multiple enabled patterns
  const duplicateExclusions = useMemo(() => {
    const columnToPatterns: Record<string, string[]> = {};
    const duplicates: Record<string, string> = {}; // column -> first_pattern
    
    // Only check enabled patterns
    const enabledPatterns = new Set(
      Object.entries(excludeConfig)
        .filter(([_, enabled]) => enabled === true)
        .map(([key, _]) => key)
    );
    
    // Build mapping: column -> [pattern1, pattern2, ...]
    for (const [patternKey, columns] of Object.entries(excludePatternVariables)) {
      if (!enabledPatterns.has(patternKey)) continue;
      
      const cols = Array.isArray(columns) ? columns : [];
      for (const col of cols) {
        if (!columnToPatterns[col]) {
          columnToPatterns[col] = [];
        }
        columnToPatterns[col].push(patternKey);
      }
    }
    
    // Find duplicates (columns in multiple patterns)
    for (const [col, patterns] of Object.entries(columnToPatterns)) {
      if (patterns.length > 1) {
        duplicates[col] = patterns[0]; // First pattern wins
      }
    }
    
    return duplicates;
  }, [excludeConfig, excludePatternVariables]);

  // Filtreleme
  const filteredAdminColumns = adminColumns.filter(col => 
    col.code.toLowerCase().includes(adminSearch.toLowerCase()) ||
    col.label.toLowerCase().includes(adminSearch.toLowerCase())
  );

  const filteredExcludedByDefaultColumns = excludedByDefaultColumns.filter(col =>
    col.code.toLowerCase().includes(excludedColsSearch.toLowerCase()) ||
    (col.label || '').toLowerCase().includes(excludedColsSearch.toLowerCase())
  );

  const filteredExcludeCandidates = excludeCandidates.filter(ec =>
    ec.patternKey.toLowerCase().includes(patternSearch.toLowerCase()) ||
    ec.label.toLowerCase().includes(patternSearch.toLowerCase())
  );

  // Gönderilecek sütun sayısı
  const excludedCount = selectedAdminColumns.length + excludedVariables.length;
  const sendingCount = totalColumns - excludedCount;

  return (
    <div className="space-y-6">
      {/* Özet */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600">Total {totalColumns} columns, {totalRows.toLocaleString()} rows</p>
            <p className="text-lg font-semibold text-gray-900">
              <span className="text-green-600">{sendingCount}</span> columns will be transformed,{' '}
              <span className="text-amber-600">{excludedCount}</span> will be excluded
            </p>
          </div>
        </div>
      </div>

      {/* Admin Sütunlar Bölümü */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <button
          onClick={() => setAdminExpanded(!adminExpanded)}
          className="w-full px-6 py-4 flex items-center justify-between bg-amber-50 hover:bg-amber-100 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <Shield className="text-amber-600" size={20} />
            <div className="text-left">
              <h3 className="font-semibold text-gray-900">Admin / Meta Columns</h3>
              <p className="text-sm text-gray-500">
                Data like participant ID, date, weight - will not be transformed
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className="bg-amber-100 text-amber-700 px-3 py-1 rounded-full text-sm font-medium">
              {selectedAdminColumns.length} / {adminColumns.length} excluded
            </span>
            {adminExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </div>
        </button>

        {adminExpanded && (
          <div className="p-4 border-t border-gray-100">
            {/* Arama + Tümünü Seç */}
            <div className="flex items-center justify-between mb-4">
              <div className="relative flex-1 max-w-xs">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                <input
                  type="text"
                  placeholder="Search column..."
                  value={adminSearch}
                  onChange={(e) => setAdminSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => onSelectAllAdmin(true)}
                  className="px-3 py-1.5 text-sm bg-amber-100 text-amber-700 rounded-lg hover:bg-amber-200 transition-colors"
                >
                  Exclude All
                </button>
                <button
                  onClick={() => onSelectAllAdmin(false)}
                  className="px-3 py-1.5 text-sm bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
                >
                  Include All
                </button>
              </div>
            </div>

            {/* Sütun Listesi */}
            <div className="max-h-64 overflow-y-auto space-y-1">
              {filteredAdminColumns.length === 0 ? (
                <p className="text-gray-500 text-sm text-center py-4">No admin columns found</p>
              ) : (
                filteredAdminColumns.map(col => {
                  const isExcluded = selectedAdminColumns.includes(col.code);
                  return (
                    <div
                      key={col.code}
                      className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                        isExcluded ? 'bg-amber-50 border border-amber-200' : 'bg-green-50 border border-green-200'
                      }`}
                      onClick={() => onAdminColumnToggle(col.code)}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-mono text-sm font-medium text-gray-900 truncate">{col.code}</p>
                        <p className="text-xs text-gray-500 truncate">{col.label}</p>
                      </div>
                      <div className="flex items-center space-x-2 ml-3">
                        {isExcluded ? (
                          <>
                            <span className="text-xs text-amber-600 font-medium">Excluded</span>
                            <ToggleLeft className="text-amber-500" size={24} />
                          </>
                        ) : (
                          <>
                            <span className="text-xs text-green-600 font-medium">Included</span>
                            <ToggleRight className="text-green-500" size={24} />
                          </>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      {/* Otomatik Hariç Sütunlar Bölümü (None/All of the above checkbox kolonları vb) */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <button
          onClick={() => setExcludedColsExpanded(!excludedColsExpanded)}
          className="w-full px-6 py-4 flex items-center justify-between bg-orange-50 hover:bg-orange-100 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <XCircle className="text-orange-600" size={20} />
            <div className="text-left">
              <h3 className="font-semibold text-gray-900">Automatically Excluded Columns</h3>
              <p className="text-sm text-gray-500">
                Usually checkbox columns like "None/All of the above" — you can include them if you wish
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className="bg-orange-100 text-orange-700 px-3 py-1 rounded-full text-sm font-medium">
              {excludedVariables.length} / {excludedByDefaultColumns.length} excluded
            </span>
            {excludedColsExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </div>
        </button>

        {excludedColsExpanded && (
          <div className="p-4 border-t border-gray-100">
            {/* Arama + Tümünü Seç */}
            <div className="flex items-center justify-between mb-4">
              <div className="relative flex-1 max-w-xs">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                <input
                  type="text"
                  placeholder="Search column..."
                  value={excludedColsSearch}
                  onChange={(e) => setExcludedColsSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => {
                    onSelectAllExcludedVariables(true, excludedByDefaultAllCodes);
                  }}
                  className="px-3 py-1.5 text-sm bg-orange-100 text-orange-700 rounded-lg hover:bg-orange-200 transition-colors"
                >
                  Exclude All
                </button>
                <button
                  onClick={() => {
                    onSelectAllExcludedVariables(false, excludedByDefaultAllCodes);
                  }}
                  className="px-3 py-1.5 text-sm bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
                >
                  Include All
                </button>
              </div>
            </div>

            {/* Sütun Listesi */}
            <div className="max-h-64 overflow-y-auto space-y-1">
              {filteredExcludedByDefaultColumns.length === 0 ? (
                <p className="text-gray-500 text-sm text-center py-4">No columns found</p>
              ) : (
                filteredExcludedByDefaultColumns.map((col, idx) => {
                  const isExcluded = excludedByDefaultSelected.has(col.code);
                  return (
                    <div
                      key={`${col.code}-${idx}`}
                      className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                        isExcluded ? 'bg-orange-50 border border-orange-200' : 'bg-green-50 border border-green-200'
                      }`}
                      onClick={() => onExcludedVariableToggle(col.code)}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-mono text-sm font-medium text-gray-900 truncate">{col.code}</p>
                        <p className="text-xs text-gray-500 truncate">{col.label}</p>
                      </div>
                      <div className="flex items-center space-x-2 ml-3">
                        {isExcluded ? (
                          <>
                            <span className="text-xs text-orange-600 font-medium">Excluded</span>
                            <ToggleLeft className="text-orange-500" size={24} />
                          </>
                        ) : (
                          <>
                            <span className="text-xs text-green-600 font-medium">Included</span>
                            <ToggleRight className="text-green-500" size={24} />
                          </>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      {/* Exclude Patterns (None of above / Don't know / Refused...) */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <button
          onClick={() => setExcludePatternsExpanded(!excludePatternsExpanded)}
          className="w-full px-6 py-4 flex items-center justify-between bg-red-50 hover:bg-red-100 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <Filter className="text-red-600" size={20} />
            <div className="text-left">
              <h3 className="font-semibold text-gray-900">Options to Exclude</h3>
              <p className="text-sm text-gray-500">
                Skip options like "Don't know / Prefer not to say / None of the above" on a row-by-row basis
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className="bg-red-100 text-red-700 px-3 py-1 rounded-full text-sm font-medium">
              {excludeCandidates.length} pattern
            </span>
            {excludePatternsExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </div>
        </button>

        {excludePatternsExpanded && (
          <div className="p-4 border-t border-gray-100 space-y-4">
            <div className="flex items-center justify-between">
              <div className="relative flex-1 max-w-xs">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                <input
                  type="text"
                  placeholder="Search pattern..."
                  value={patternSearch}
                  onChange={(e) => setPatternSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            {filteredExcludeCandidates.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-4">No patterns found</p>
            ) : (
              <div className="space-y-3">
                {filteredExcludeCandidates.map((ec) => {
                  const isEnabled = Boolean(excludeConfig?.[ec.patternKey]);
                  const selectedVars = new Set(excludePatternVariables?.[ec.patternKey] || []);
                  return (
                    <div key={ec.patternKey} className="border border-gray-200 rounded-xl overflow-hidden">
                      <div className="px-4 py-3 bg-gray-50 flex items-center justify-between">
                        <div className="min-w-0">
                          <p className="font-medium text-gray-900 truncate">{ec.label}</p>
                          <p className="text-xs text-gray-500 font-mono truncate">{ec.patternKey}</p>
                        </div>

                        <button
                          onClick={() => onExcludeToggle(ec.patternKey)}
                          className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            isEnabled ? 'bg-red-600 text-white hover:bg-red-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                          title="Pattern aktif/pasif"
                        >
                          {isEnabled ? <ToggleLeft size={18} /> : <ToggleRight size={18} />}
                          <span>{isEnabled ? 'Active (Skip)' : 'Inactive'}</span>
                        </button>
                      </div>

                      <div className="p-4">
                        <div className="flex items-center justify-between mb-3">
                          <p className="text-sm text-gray-600">
                            Affected columns: <span className="font-medium text-gray-900">{ec.affectedVariables?.length || 0}</span>
                          </p>
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => onExcludePatternSelectAll(ec.patternKey, true, ec.affectedVariables)}
                              className="px-3 py-1.5 text-sm bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
                            >
                              Select All
                            </button>
                            <button
                              onClick={() => onExcludePatternSelectAll(ec.patternKey, false, ec.affectedVariables)}
                              className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                            >
                              Clear
                            </button>
                          </div>
                        </div>

                        <div className="max-h-56 overflow-y-auto space-y-1">
                          {(ec.affectedVariables || []).map((code) => {
                            const checked = selectedVars.has(code);
                            const isDuplicate = duplicateExclusions[code] && duplicateExclusions[code] !== ec.patternKey;
                            const duplicatePattern = isDuplicate ? duplicateExclusions[code] : null;
                            
                            return (
                              <div
                                key={`${ec.patternKey}-${code}`}
                                className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${
                                  checked 
                                    ? isDuplicate 
                                      ? 'bg-amber-50 border border-amber-300' 
                                      : 'bg-red-50 border border-red-200'
                                    : 'bg-gray-50 border border-gray-200'
                                }`}
                                onClick={() => onExcludePatternVariableToggle(ec.patternKey, code)}
                              >
                                <div className="min-w-0 flex-1">
                                  <p className="font-mono text-xs font-medium text-gray-900 truncate">{code}</p>
                                  {isDuplicate && checked && (
                                    <p className="text-[10px] text-amber-700 mt-0.5">
                                      ⚠️ Already excluded by "{excludeCandidates.find(c => c.patternKey === duplicatePattern)?.label || duplicatePattern}"
                                    </p>
                                  )}
                                </div>
                                <div className="flex items-center space-x-2 ml-2">
                                  <span className={`text-xs font-medium ${checked ? isDuplicate ? 'text-amber-700' : 'text-red-700' : 'text-gray-500'}`}>
                                    {checked ? 'Selected' : 'Not selected'}
                                  </span>
                                  {checked ? (
                                    <ToggleLeft className={isDuplicate ? "text-amber-500" : "text-red-500"} size={20} />
                                  ) : (
                                    <ToggleRight className="text-gray-400" size={20} />
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ColumnAnalysis;
