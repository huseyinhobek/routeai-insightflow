import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DatasetMeta } from '../types';
import { Users, LayoutGrid, CheckCircle, AlertTriangle, Sparkles, Loader2 } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis } from 'recharts';
import { COLORS } from '../constants';
import { apiService } from '../services/apiService';

const DatasetOverview: React.FC = () => {
  const [meta, setMeta] = useState<DatasetMeta | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateStatus, setGenerateStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [embeddingStatus, setEmbeddingStatus] = useState<{
    utterances: { total: number; embedded: number; progress: number };
    variables: { total: number; embedded: number; progress: number };
    overall_progress: number;
    is_complete: boolean;
  } | null>(null);
  const [checkingStatus, setCheckingStatus] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const stored = localStorage.getItem('currentDatasetMeta');
    if (!stored) {
      navigate('/');
      return;
    }
    setMeta(JSON.parse(stored));
  }, [navigate]);

  // Check embedding status on mount and periodically
  useEffect(() => {
    if (!meta) return;

    let isMounted = true;
    let intervalId: NodeJS.Timeout | null = null;
    let isChecking = false;

    const checkStatus = async () => {
      if (isChecking) return;
      isChecking = true;
      setCheckingStatus(true);
      try {
        const status = await apiService.getEmbeddingStatus(meta.id);
        if (isMounted) {
          setEmbeddingStatus(status);
          // If complete, stop interval
          if (status.is_complete && intervalId) {
            clearInterval(intervalId);
            intervalId = null;
          }
        }
      } catch (error) {
        console.error('Error checking embedding status:', error);
      } finally {
        isChecking = false;
        if (isMounted) {
          setCheckingStatus(false);
        }
      }
    };

    // Initial check
    checkStatus();
    
    // Set up interval - always check, even if generating (to show progress)
    intervalId = setInterval(() => {
      if (!isChecking) {
        checkStatus();
      }
    }, 5000); // Check every 5 seconds

    return () => {
      isMounted = false;
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [meta]); // Remove generating and checkingStatus from dependencies to avoid infinite loops

  if (!meta) return null;

  // Derive stats
  const typeCounts = meta.variables.reduce((acc, v) => {
    acc[v.type] = (acc[v.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const typeData = Object.entries(typeCounts).map(([name, value]) => ({ name, value }));
  
  const avgResponseRate = Math.round(
    meta.variables.reduce((sum, v) => sum + v.responseRate, 0) / meta.variables.length
  );

  const missingHeavyVars = meta.variables
    .filter(v => v.responseRate < 80)
    .sort((a, b) => a.responseRate - b.responseRate)
    .slice(0, 5);

  const handleGenerateEmbeddings = async () => {
    if (!meta) return;
    
    setGenerating(true);
    setGenerateStatus(null);
    
    try {
      // Start populate in background (fire and forget)
      apiService.populateDatasetData(meta.id)
        .then(() => {
          // After populate completes, start embedding generation (also runs in background now)
          return apiService.generateEmbeddings(meta.id);
        })
        .then((result) => {
          // Embedding generation now runs in background, so result just confirms it started
          setGenerateStatus({
            type: 'success',
            message: 'Embedding generation started in background. Progress will be shown below.'
          });
          
          // Clear status message after 5 seconds
          setTimeout(() => setGenerateStatus(null), 5000);
          setGenerating(false);
          
          // Immediately check status to show progress bar
          apiService.getEmbeddingStatus(meta.id)
            .then((status) => {
              setEmbeddingStatus(status);
            })
            .catch((err) => {
              console.error('Error checking initial embedding status:', err);
            });
        })
        .catch((error: any) => {
          console.error('Error in populate/generate process:', error);
          setGenerateStatus({
            type: 'error',
            message: error.message || 'Failed to start embedding generation. Please check backend logs.'
          });
          setGenerating(false);
        });
      
    } catch (error: any) {
      setGenerateStatus({
        type: 'error',
        message: error.message || 'Failed to start embedding generation'
      });
      setGenerating(false);
    }
  };

  const StatCard = ({ title, value, icon, color }: any) => (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-gray-500 mb-1">{title}</p>
        <h3 className="text-3xl font-bold text-gray-900">{value}</h3>
      </div>
      <div className={`p-3 rounded-xl ${color}`}>
        {icon}
      </div>
    </div>
  );

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{meta.filename}</h1>
          <p className="text-gray-500">Dataset Overview</p>
        </div>
        <div className="flex items-center gap-3">
          {embeddingStatus && !embeddingStatus.is_complete && (
            <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-200 rounded-xl">
              <Loader2 size={16} className="animate-spin text-blue-600" />
              <div className="flex flex-col">
                <span className="text-xs font-medium text-blue-900">
                  Embedding: {embeddingStatus.overall_progress.toFixed(1)}%
                </span>
                <div className="w-32 h-1.5 bg-blue-200 rounded-full overflow-hidden mt-1">
                  <div 
                    className="h-full bg-blue-600 transition-all duration-300"
                    style={{ width: `${embeddingStatus.overall_progress}%` }}
                  />
                </div>
              </div>
            </div>
          )}
          <button
            onClick={handleGenerateEmbeddings}
            disabled={generating || (embeddingStatus && !embeddingStatus.is_complete)}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-all
              ${generating || (embeddingStatus && !embeddingStatus.is_complete)
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                : 'bg-purple-600 text-white hover:bg-purple-700 shadow-sm hover:shadow-md'
              }
            `}
          >
            {generating ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Generating...</span>
              </>
            ) : embeddingStatus && !embeddingStatus.is_complete ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Embedding in progress...</span>
              </>
            ) : (
              <>
                <Sparkles size={16} />
                <span>Generate Embeddings</span>
              </>
            )}
          </button>
        </div>
      </div>

      {generateStatus && (
        <div className={`
          p-4 rounded-xl border
          ${generateStatus.type === 'success' 
            ? 'bg-green-50 border-green-200 text-green-800' 
            : 'bg-red-50 border-red-200 text-red-800'
          }
        `}>
          <div className="flex items-center gap-2">
            {generateStatus.type === 'success' ? (
              <CheckCircle size={20} />
            ) : (
              <AlertTriangle size={20} />
            )}
            <span className="text-sm font-medium">{generateStatus.message}</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Total Respondents" 
          value={meta.nRows.toLocaleString()} 
          icon={<Users size={24} className="text-blue-600" />} 
          color="bg-blue-50"
        />
        <StatCard 
          title="Total Variables" 
          value={meta.nCols.toLocaleString()} 
          icon={<LayoutGrid size={24} className="text-purple-600" />} 
          color="bg-purple-50"
        />
        <StatCard 
          title="Avg. Completion" 
          value={`${avgResponseRate}%`} 
          icon={<CheckCircle size={24} className="text-green-600" />} 
          color="bg-green-50"
        />
        <StatCard 
          title="High Missing Vars" 
          value={missingHeavyVars.length} 
          icon={<AlertTriangle size={24} className="text-amber-600" />} 
          color="bg-amber-50"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Variable Types Distribution</h3>
          <div className="h-64 w-full min-w-0" style={{ minHeight: '256px' }}>
            <ResponsiveContainer width="100%" height="100%" minHeight={256} aspect={undefined}>
              <PieChart>
                <Pie
                  data={typeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {typeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={Object.values(COLORS)[index % 8]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-4 mt-4">
             {typeData.map((entry, index) => (
                <div key={entry.name} className="flex items-center text-sm">
                  <span className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: Object.values(COLORS)[index % 8] }}></span>
                  <span className="text-gray-600 capitalize">{entry.name.replace('_', ' ')}: {entry.value}</span>
                </div>
             ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Lowest Completion Rates</h3>
          <div className="h-64 w-full min-w-0" style={{ minHeight: '256px' }}>
            <ResponsiveContainer width="100%" height="100%" minHeight={256} aspect={undefined}>
               <BarChart data={missingHeavyVars} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                  <XAxis type="number" domain={[0, 100]} hide />
                  <YAxis dataKey="code" type="category" width={60} tick={{fontSize: 12}} />
                  <Tooltip cursor={{fill: 'transparent'}} />
                  <Bar dataKey="responseRate" fill={COLORS.danger} radius={[0, 4, 4, 0]} barSize={20} />
               </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-gray-400 mt-4 text-center">Variables with highest missing value percentage.</p>
        </div>
      </div>
    </div>
  );
};

export default DatasetOverview;