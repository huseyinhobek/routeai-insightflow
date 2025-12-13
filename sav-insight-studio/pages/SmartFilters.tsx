import React, { useState, useEffect } from 'react';
import { geminiService } from '../services/geminiService';
import { DatasetMeta, SmartFilterResponse, SmartFilter } from '../types';
import { Sparkles, Sliders, Check, ExternalLink } from 'lucide-react';

const SmartFilters: React.FC = () => {
  const [meta, setMeta] = useState<DatasetMeta | null>(null);
  const [recommendations, setRecommendations] = useState<SmartFilterResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set());

  useEffect(() => {
    const stored = localStorage.getItem('currentDatasetMeta');
    if (stored) {
      setMeta(JSON.parse(stored));
    }
  }, []);

  const generateSuggestions = async () => {
    if (!meta) return;
    setLoading(true);
    try {
      const result = await geminiService.suggestSmartFilters(meta);
      setRecommendations(result);
    } catch (e) {
      console.error(e);
      alert('Failed to generate filters. Ensure Gemini API Key is set in env.');
    } finally {
      setLoading(false);
    }
  };

  const toggleFilter = (id: string) => {
    const next = new Set(activeFilters);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setActiveFilters(next);
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
             <Sparkles className="text-purple-500 mr-2" /> Smart Filter Suggestions
          </h1>
          <p className="text-gray-500 mt-1">AI-powered recommendations for dashboard segmentation.</p>
        </div>
        {!recommendations && (
           <button 
             onClick={generateSuggestions}
             disabled={loading}
             className="bg-purple-600 text-white px-6 py-2.5 rounded-xl font-medium shadow-lg shadow-purple-200 hover:bg-purple-700 hover:shadow-xl transition-all disabled:opacity-70 flex items-center"
           >
             {loading ? 'Analyzing Metadata...' : 'Ask AI to Suggest Filters'}
           </button>
        )}
      </div>

      {loading && (
        <div className="text-center py-20 bg-white rounded-3xl border border-gray-100 shadow-sm">
          <div className="animate-pulse flex flex-col items-center">
            <div className="h-12 w-12 bg-purple-100 rounded-full mb-4"></div>
            <div className="h-4 w-64 bg-gray-200 rounded mb-2"></div>
            <div className="h-3 w-48 bg-gray-100 rounded"></div>
          </div>
          <p className="mt-6 text-gray-500 text-sm">Gemini is analyzing {meta?.variables.length} variables...</p>
        </div>
      )}

      {recommendations && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {recommendations.filters.map((filter) => (
            <div 
              key={filter.id} 
              className={`
                group relative bg-white p-6 rounded-2xl border transition-all duration-200
                ${activeFilters.has(filter.id) ? 'border-purple-500 ring-1 ring-purple-500 shadow-md' : 'border-gray-200 hover:border-purple-300 hover:shadow-md'}
              `}
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                   <h3 className="font-bold text-gray-900 text-lg">{filter.title}</h3>
                   <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">{filter.filterType.replace('_', ' ')}</span>
                </div>
                <div className="bg-green-50 text-green-700 text-xs font-bold px-2 py-1 rounded-full">
                  Score: {filter.suitabilityScore}
                </div>
              </div>

              <p className="text-gray-600 text-sm mb-4 leading-relaxed">{filter.rationale}</p>
              
              <div className="mb-4">
                <p className="text-xs text-gray-400 font-bold mb-2">SOURCE VARIABLES:</p>
                <div className="flex flex-wrap gap-2">
                  {filter.sourceVars.map(v => (
                    <span key={v} className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs font-mono">{v}</span>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-100">
                 <button 
                   onClick={() => toggleFilter(filter.id)}
                   className={`
                     flex items-center space-x-2 text-sm font-medium px-4 py-2 rounded-lg transition-colors
                     ${activeFilters.has(filter.id) 
                       ? 'bg-purple-600 text-white' 
                       : 'bg-gray-50 text-gray-700 hover:bg-gray-100'}
                   `}
                 >
                   {activeFilters.has(filter.id) ? (
                     <><Check size={16} /> <span>Applied</span></>
                   ) : (
                     <><Sliders size={16} /> <span>Apply Filter</span></>
                   )}
                 </button>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {activeFilters.size > 0 && (
         <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white px-8 py-4 rounded-full shadow-2xl flex items-center space-x-6 z-50">
           <span className="font-medium">{activeFilters.size} filters selected</span>
           <button className="bg-white text-gray-900 px-4 py-1.5 rounded-full text-sm font-bold hover:bg-gray-200">
             Export Definition JSON
           </button>
         </div>
      )}
    </div>
  );
};

export default SmartFilters;