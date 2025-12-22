import React, { useState, useEffect, useMemo } from 'react';
import { apiService } from '../services/apiService';
import { DatasetMeta, SmartFilterResponse, SmartFilter, VariableSummary, FilterType, FilterControl } from '../types';
import { Sparkles, Sliders, Check, AlertCircle, RefreshCw, Plus, X, Search, Bot, User, ChevronDown, ChevronUp, Filter } from 'lucide-react';

// Extended SmartFilter with source tracking
interface ExtendedSmartFilter extends SmartFilter {
  source: 'ai' | 'manual';
  isApplied: boolean;
}

// Add Variable Modal Component with multi-select support
interface AddFilterModalProps {
  isOpen: boolean;
  onClose: () => void;
  variables: VariableSummary[];
  onAddFilters: (variables: VariableSummary[]) => void;
  existingFilterVars: string[];
  aiFilterVars: string[]; // Variables already used by AI filters
}

const AddFilterModal: React.FC<AddFilterModalProps> = ({ 
  isOpen, 
  onClose, 
  variables, 
  onAddFilters, 
  existingFilterVars,
  aiFilterVars 
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [selectedVars, setSelectedVars] = useState<Set<string>>(new Set());

  // Reset selection when modal closes
  React.useEffect(() => {
    if (!isOpen) {
      setSelectedVars(new Set());
      setSearchTerm('');
      setTypeFilter('all');
    }
  }, [isOpen]);

  const filteredVariables = useMemo(() => {
    return variables.filter(v => {
      // Filter by search term (code or label)
      const matchesSearch = searchTerm === '' || 
        v.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        v.label.toLowerCase().includes(searchTerm.toLowerCase());
      
      // Filter by type
      const matchesType = typeFilter === 'all' || v.type === typeFilter;
      
      return matchesSearch && matchesType;
    });
  }, [variables, searchTerm, typeFilter]);

  const toggleSelection = (code: string) => {
    setSelectedVars(prev => {
      const next = new Set(prev);
      if (next.has(code)) {
        next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  };

  const handleAddSelected = () => {
    const selectedVariables = variables.filter(v => selectedVars.has(v.code));
    onAddFilters(selectedVariables);
    onClose();
  };

  const selectAll = () => {
    const allCodes = filteredVariables
      .filter(v => !existingFilterVars.includes(v.code))
      .map(v => v.code);
    setSelectedVars(new Set(allCodes));
  };

  const clearSelection = () => {
    setSelectedVars(new Set());
  };

  if (!isOpen) return null;

  const selectedCount = selectedVars.size;
  const availableCount = filteredVariables.filter(v => !existingFilterVars.includes(v.code)).length;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-gray-100 flex-shrink-0">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <Plus className="text-purple-500" size={20} />
                Add Manual Filters
              </h2>
              <p className="text-gray-500 text-sm mt-1">Select one or more variables to create custom filters</p>
            </div>
            <button 
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-xl transition-colors"
            >
              <X size={20} className="text-gray-500" />
            </button>
          </div>
          
          {/* Search and Filter */}
          <div className="mt-4 flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                placeholder="Search by variable code or label..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm bg-white"
            >
              <option value="all">All Types</option>
              <option value="single_choice">Single Choice</option>
              <option value="multi_choice">Multi Choice</option>
              <option value="numeric">Numeric</option>
              <option value="scale">Scale</option>
              <option value="text">Text</option>
              <option value="date">Date</option>
            </select>
          </div>

          {/* Selection Controls */}
          <div className="mt-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={selectAll}
                className="text-xs text-purple-600 hover:text-purple-700 font-medium"
              >
                Select All ({availableCount})
              </button>
              <span className="text-gray-300">|</span>
              <button
                onClick={clearSelection}
                className="text-xs text-gray-500 hover:text-gray-700 font-medium"
              >
                Clear Selection
              </button>
            </div>
            {selectedCount > 0 && (
              <span className="text-sm font-medium text-purple-600">
                {selectedCount} selected
              </span>
            )}
          </div>
        </div>
        
        {/* Variable List */}
        <div className="flex-1 overflow-y-auto p-4">
          {filteredVariables.length === 0 ? (
            <div className="text-center py-12">
              <Filter className="mx-auto text-gray-300 mb-3" size={48} />
              <p className="text-gray-500">No matching variables found</p>
              <p className="text-gray-400 text-sm mt-1">Try adjusting your search or filter</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredVariables.map((variable) => {
                const isExisting = existingFilterVars.includes(variable.code);
                const isAIUsed = aiFilterVars.includes(variable.code);
                const isSelected = selectedVars.has(variable.code);
                
                return (
                  <div
                    key={variable.code}
                    onClick={() => !isExisting && toggleSelection(variable.code)}
                    className={`
                      w-full text-left p-4 rounded-xl border transition-all cursor-pointer
                      ${isExisting 
                        ? 'border-gray-200 bg-gray-50 opacity-60 cursor-not-allowed' 
                        : isSelected 
                          ? 'border-purple-500 bg-purple-50 ring-1 ring-purple-500' 
                          : 'border-gray-100 hover:border-purple-300 hover:bg-purple-50/50'
                      }
                    `}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        {/* Checkbox */}
                        <div className={`
                          w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5
                          ${isExisting 
                            ? 'border-gray-300 bg-gray-200' 
                            : isSelected 
                              ? 'border-purple-500 bg-purple-500' 
                              : 'border-gray-300 hover:border-purple-400'
                          }
                        `}>
                          {(isSelected || isExisting) && (
                            <Check size={12} className={isExisting ? 'text-gray-500' : 'text-white'} />
                          )}
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono font-semibold text-purple-600 text-sm">{variable.code}</span>
                            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                              variable.type === 'single_choice' ? 'bg-blue-100 text-blue-700' :
                              variable.type === 'multi_choice' ? 'bg-green-100 text-green-700' :
                              variable.type === 'numeric' ? 'bg-orange-100 text-orange-700' :
                              variable.type === 'scale' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {variable.type.replace('_', ' ')}
                            </span>
                            {/* AI Badge */}
                            {isAIUsed && (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 text-[9px] font-semibold uppercase">
                                <Bot size={9} />
                                AI Detected
                              </span>
                            )}
                            {/* Already Added Badge */}
                            {isExisting && (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-gray-200 text-gray-600 text-[9px] font-semibold uppercase">
                                Already Added
                              </span>
                            )}
                          </div>
                          <p className="text-gray-700 text-sm mt-1 line-clamp-1">{variable.label || 'No label'}</p>
                          {variable.valueLabels && variable.valueLabels.length > 0 && (
                            <p className="text-gray-400 text-xs mt-1">
                              {variable.valueLabels.length} options • {variable.responseCount} responses
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex-shrink-0 flex items-center justify-between">
          <p className="text-gray-500 text-sm">
            Showing {filteredVariables.length} of {variables.length} variables
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium text-sm transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleAddSelected}
              disabled={selectedCount === 0}
              className="px-6 py-2 bg-purple-600 text-white rounded-xl font-medium text-sm hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
            >
              <Plus size={16} />
              Add {selectedCount > 0 ? `${selectedCount} Filter${selectedCount > 1 ? 's' : ''}` : 'Filters'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Filter Card Component
interface FilterCardProps {
  filter: ExtendedSmartFilter;
  onToggleApply: (id: string) => void;
  onRemove: (id: string) => void;
}

const FilterCard: React.FC<FilterCardProps> = ({ filter, onToggleApply, onRemove }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div 
      className={`
        group relative bg-white p-5 rounded-2xl border transition-all duration-200
        ${filter.isApplied ? 'border-purple-500 ring-1 ring-purple-500 shadow-md' : 'border-gray-200 hover:border-purple-300 hover:shadow-md'}
      `}
    >
      {/* Remove Button */}
      <button
        onClick={() => onRemove(filter.id)}
        className="absolute -top-2 -right-2 p-1.5 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-all hover:bg-red-600 shadow-lg z-10"
        title="Remove filter"
      >
        <X size={14} />
      </button>

      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1 min-w-0 pr-2">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-bold text-gray-900 text-base truncate">{filter.title}</h3>
            {/* Source Badge */}
            {filter.source === 'ai' ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 text-[10px] font-semibold uppercase tracking-wide">
                <Bot size={10} />
                AI Suggested
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 text-[10px] font-semibold uppercase tracking-wide">
                <User size={10} />
                Manual
              </span>
            )}
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 mt-1 block">
            {filter.filterType.replace('_', ' ')}
          </span>
        </div>
        <div className={`text-xs font-bold px-2.5 py-1 rounded-full flex-shrink-0 ${
          filter.suitabilityScore >= 80 ? 'bg-green-50 text-green-700' :
          filter.suitabilityScore >= 60 ? 'bg-yellow-50 text-yellow-700' :
          'bg-gray-50 text-gray-600'
        }`}>
          Score: {filter.suitabilityScore}
        </div>
      </div>

      {/* Rationale */}
      <p className="text-gray-600 text-sm mb-3 leading-relaxed line-clamp-2">{filter.rationale}</p>
      
      {/* Source Variables (Collapsible for many) */}
      <div className="mb-3">
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-1 text-xs text-gray-400 font-bold mb-2 hover:text-gray-600 transition-colors"
        >
          SOURCE VARIABLES ({filter.sourceVars.length})
          {filter.sourceVars.length > 3 && (
            isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />
          )}
        </button>
        <div className="flex flex-wrap gap-1.5">
          {(isExpanded ? filter.sourceVars : filter.sourceVars.slice(0, 3)).map(v => (
            <span key={v} className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-xs font-mono">{v}</span>
          ))}
          {!isExpanded && filter.sourceVars.length > 3 && (
            <span className="bg-gray-100 text-gray-500 px-2 py-0.5 rounded text-xs">
              +{filter.sourceVars.length - 3} more
            </span>
          )}
        </div>
      </div>

      {/* Options Preview (if available) */}
      {filter.options && filter.options.length > 0 && (
        <div className="mb-3 p-2 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-400 font-bold mb-1.5">OPTIONS:</p>
          <div className="flex flex-wrap gap-1">
            {filter.options.slice(0, 5).map(opt => (
              <span key={opt.key} className="text-xs bg-white border border-gray-200 px-2 py-0.5 rounded">
                {opt.label}
              </span>
            ))}
            {filter.options.length > 5 && (
              <span className="text-xs text-gray-400">+{filter.options.length - 5} more</span>
            )}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <button 
          onClick={() => onToggleApply(filter.id)}
          className={`
            flex items-center space-x-2 text-sm font-medium px-4 py-2 rounded-lg transition-all
            ${filter.isApplied 
              ? 'bg-purple-600 text-white hover:bg-purple-700' 
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}
          `}
        >
          {filter.isApplied ? (
            <><Check size={16} /> <span>Applied</span></>
          ) : (
            <><Sliders size={16} /> <span>Apply Filter</span></>
          )}
        </button>
      </div>
    </div>
  );
};

const SmartFilters: React.FC = () => {
  const [meta, setMeta] = useState<DatasetMeta | null>(null);
  const [filters, setFilters] = useState<ExtendedSmartFilter[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [hasGeneratedAI, setHasGeneratedAI] = useState(false);

  // Load saved data from localStorage on mount
  useEffect(() => {
    const storedMeta = localStorage.getItem('currentDatasetMeta');
    if (storedMeta) {
      const parsedMeta = JSON.parse(storedMeta);
      setMeta(parsedMeta);
      
      // Load saved filters (extended format)
      const savedFilters = localStorage.getItem(`extendedSmartFilters_${parsedMeta.id}`);
      if (savedFilters) {
        try {
          const parsed = JSON.parse(savedFilters);
          setFilters(parsed);
          setHasGeneratedAI(parsed.some((f: ExtendedSmartFilter) => f.source === 'ai'));
        } catch (e) {
          console.error('Failed to parse saved filters:', e);
        }
      }
    }
  }, []);

  // Save filters to localStorage whenever they change
  useEffect(() => {
    if (meta?.id) {
      if (filters.length > 0) {
        localStorage.setItem(`extendedSmartFilters_${meta.id}`, JSON.stringify(filters));
      } else {
        // Remove from localStorage when all filters are deleted
        localStorage.removeItem(`extendedSmartFilters_${meta.id}`);
      }
    }
  }, [filters, meta?.id]);

  const generateAISuggestions = async () => {
    if (!meta) return;
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.generateSmartFilters(meta.id, 10);
      
      if (result && result.filters && result.filters.length > 0) {
        // Convert to extended format and add to existing manual filters
        const aiFilters: ExtendedSmartFilter[] = result.filters.map(f => ({
          ...f,
          source: 'ai' as const,
          isApplied: true // AI suggestions come pre-applied
        }));
        
        // Keep manual filters, replace AI filters
        const manualFilters = filters.filter(f => f.source === 'manual');
        setFilters([...aiFilters, ...manualFilters]);
        setHasGeneratedAI(true);
      } else {
        setError('Unable to generate suitable smart filters for this dataset. The number of categorical variables may be insufficient.');
      }
    } catch (e: any) {
      console.error('Smart filter generation error:', e);
      setError(e.message || 'Smart filter generation failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const clearAndRegenerate = () => {
    // Only clear AI filters, keep manual
    setFilters(filters.filter(f => f.source === 'manual'));
    setHasGeneratedAI(false);
    setError(null);
  };

  const toggleFilterApply = (id: string) => {
    setFilters(prev => prev.map(f => 
      f.id === id ? { ...f, isApplied: !f.isApplied } : f
    ));
  };

  const removeFilter = (id: string) => {
    setFilters(prev => {
      const updated = prev.filter(f => f.id !== id);
      // Update hasGeneratedAI if no AI filters remain
      if (!updated.some(f => f.source === 'ai')) {
        setHasGeneratedAI(false);
      }
      return updated;
    });
  };

  const addManualFilters = (selectedVariables: VariableSummary[]) => {
    const newFilters: ExtendedSmartFilter[] = selectedVariables.map(variable => {
      // Determine filter type based on variable type
      let filterType: FilterType;
      let control: FilterControl;
      
      switch (variable.type) {
        case 'single_choice':
          filterType = FilterType.CATEGORICAL;
          control = FilterControl.SELECT;
          break;
        case 'multi_choice':
          filterType = FilterType.MULTI_SELECT;
          control = FilterControl.CHECKBOX_GROUP;
          break;
        case 'numeric':
        case 'scale':
          filterType = FilterType.NUMERIC_RANGE;
          control = FilterControl.RANGE_SLIDER;
          break;
        case 'date':
          filterType = FilterType.DATE_RANGE;
          control = FilterControl.DATE_PICKER;
          break;
        default:
          filterType = FilterType.CATEGORICAL;
          control = FilterControl.CHECKBOX_GROUP;
      }

      return {
        id: `manual_${variable.code}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        title: variable.label || variable.code,
        description: `Manual filter for ${variable.code}`,
        sourceVars: [variable.code],
        filterType,
        ui: { control },
        options: variable.valueLabels?.map(vl => ({
          key: vl.value,
          label: vl.label
        })) || [],
        recommendedDefault: null,
        suitabilityScore: 75, // Default score for manual filters
        rationale: `Manually added filter for variable "${variable.code}". ${variable.label ? `Question: ${variable.label}` : ''}`,
        source: 'manual' as const,
        isApplied: true // Manual filters come pre-applied
      };
    });

    setFilters(prev => [...prev, ...newFilters]);
  };

  const appliedCount = filters.filter(f => f.isApplied).length;
  const aiFilters = filters.filter(f => f.source === 'ai');
  const manualFilters = filters.filter(f => f.source === 'manual');
  const existingFilterVars = filters.flatMap(f => f.sourceVars);
  const aiFilterVars = aiFilters.flatMap(f => f.sourceVars); // Variables used by AI filters

  return (
    <div className="max-w-6xl mx-auto pb-24">
      {/* Header */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Sparkles className="text-purple-500" /> Smart Filter Studio
          </h1>
          <p className="text-gray-500 mt-1">Create and manage filters for dashboard segmentation</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Add Manual Filter Button */}
          <button 
            onClick={() => setShowAddModal(true)}
            disabled={!meta}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium border-2 border-dashed border-gray-300 text-gray-700 hover:border-purple-400 hover:text-purple-600 hover:bg-purple-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Plus size={18} />
            Add Manual Filter
          </button>
          
          {hasGeneratedAI ? (
            <button 
              onClick={clearAndRegenerate}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 transition-all"
            >
              <RefreshCw size={16} />
              Regenerate AI
            </button>
          ) : (
            <button 
              onClick={generateAISuggestions}
              disabled={loading || !meta}
              className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-6 py-2.5 rounded-xl font-medium shadow-lg shadow-purple-200 hover:shadow-xl hover:from-purple-700 hover:to-blue-700 transition-all disabled:opacity-70 flex items-center gap-2"
            >
              <Bot size={18} />
              {loading ? 'Analyzing...' : 'Generate AI Filters'}
            </button>
          )}
        </div>
      </div>

      {/* Stats Bar */}
      {filters.length > 0 && (
        <div className="bg-gray-50 rounded-2xl p-4 mb-6 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-gradient-to-r from-purple-500 to-blue-500"></div>
              <span className="text-sm text-gray-600">
                <span className="font-bold text-gray-900">{aiFilters.length}</span> AI Suggested
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-gray-400"></div>
              <span className="text-sm text-gray-600">
                <span className="font-bold text-gray-900">{manualFilters.length}</span> Manual
              </span>
            </div>
            <div className="h-4 w-px bg-gray-300"></div>
            <div className="flex items-center gap-2">
              <Check size={14} className="text-green-600" />
              <span className="text-sm text-gray-600">
                <span className="font-bold text-gray-900">{appliedCount}</span> Applied
              </span>
            </div>
          </div>
          <button 
            onClick={() => setFilters(prev => prev.map(f => ({ ...f, isApplied: false })))}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Clear all applied
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-20 bg-white rounded-3xl border border-gray-100 shadow-sm">
          <div className="animate-pulse flex flex-col items-center">
            <div className="h-14 w-14 bg-gradient-to-r from-purple-100 to-blue-100 rounded-full mb-4 flex items-center justify-center">
              <Bot className="text-purple-500 animate-bounce" size={28} />
            </div>
            <div className="h-4 w-64 bg-gray-200 rounded mb-2"></div>
            <div className="h-3 w-48 bg-gray-100 rounded"></div>
          </div>
          <p className="mt-6 text-gray-500 text-sm">
            Analyzing {meta?.variables.length} variables, preparing AI filter suggestions...
          </p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 flex items-start gap-4 mb-6">
          <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={24} />
          <div>
            <h3 className="font-semibold text-red-900">Generation Failed</h3>
            <p className="text-red-700 text-sm mt-1">{error}</p>
            <button 
              onClick={generateAISuggestions}
              className="mt-4 bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && filters.length === 0 && (
        <div className="text-center py-20 bg-white rounded-3xl border border-gray-100 shadow-sm">
          <div className="flex flex-col items-center">
            <div className="h-16 w-16 bg-gray-100 rounded-full mb-4 flex items-center justify-center">
              <Filter className="text-gray-400" size={32} />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No Filters Yet</h3>
            <p className="text-gray-500 text-sm max-w-md mx-auto mb-6">
              Get started by generating AI-powered filter suggestions or manually adding filters based on your survey variables.
            </p>
            <div className="flex items-center gap-3">
              <button 
                onClick={() => setShowAddModal(true)}
                disabled={!meta}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 transition-all disabled:opacity-50"
              >
                <Plus size={18} />
                Add Manual Filter
              </button>
              <button 
                onClick={generateAISuggestions}
                disabled={!meta}
                className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-5 py-2.5 rounded-xl font-medium shadow-lg shadow-purple-200 hover:shadow-xl transition-all disabled:opacity-50 flex items-center gap-2"
              >
                <Bot size={18} />
                Generate AI Filters
              </button>
                </div>
                </div>
              </div>
      )}

      {/* Filter Grid */}
      {filters.length > 0 && !loading && (
        <>
          {/* AI Filters Section */}
          {aiFilters.length > 0 && (
            <div className="mb-8">
              <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Bot size={16} className="text-purple-500" />
                AI Suggested Filters
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {aiFilters.map((filter) => (
                  <FilterCard
                    key={filter.id}
                    filter={filter}
                    onToggleApply={toggleFilterApply}
                    onRemove={removeFilter}
                  />
                  ))}
                </div>
              </div>
          )}

          {/* Manual Filters Section */}
          {manualFilters.length > 0 && (
            <div className="mb-8">
              <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                <User size={16} className="text-gray-500" />
                Manual Filters
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {manualFilters.map((filter) => (
                  <FilterCard
                    key={filter.id}
                    filter={filter}
                    onToggleApply={toggleFilterApply}
                    onRemove={removeFilter}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
      
      {/* Bottom Action Bar */}
      {appliedCount > 0 && (
        <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white px-8 py-4 rounded-full shadow-2xl flex items-center space-x-6 z-40">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              {aiFilters.filter(f => f.isApplied).length > 0 && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-500/30 text-purple-200 text-xs">
                  <Bot size={10} />
                  {aiFilters.filter(f => f.isApplied).length}
                </span>
              )}
              {manualFilters.filter(f => f.isApplied).length > 0 && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-600 text-gray-200 text-xs">
                  <User size={10} />
                  {manualFilters.filter(f => f.isApplied).length}
                </span>
              )}
            </div>
            <span className="font-medium">{appliedCount} filters applied</span>
          </div>
          <button className="bg-white text-gray-900 px-4 py-1.5 rounded-full text-sm font-bold hover:bg-gray-200 transition-colors">
             Export Definition JSON
           </button>
         </div>
      )}

      {/* Add Filter Modal */}
      <AddFilterModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        variables={meta?.variables || []}
        onAddFilters={addManualFilters}
        existingFilterVars={existingFilterVars}
        aiFilterVars={aiFilterVars}
      />
    </div>
  );
};

export default SmartFilters;
