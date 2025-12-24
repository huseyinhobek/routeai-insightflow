import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Sparkles, 
  Database, 
  Settings, 
  Wand2, 
  CheckCircle,
  ChevronRight,
  ChevronLeft,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { 
  DatasetMeta, 
  ColumnAnalysisResult, 
  TransformJob, 
  TransformResult,
  ExcludeCandidate,
  DatasetRowsResponse,
  SmartFilterResponse,
  SmartFilter
} from '../types';
import { transformService } from '../services/transformService';
import { apiService } from '../services/apiService';
import ColumnAnalysis from '../components/twin/ColumnAnalysis';
import TransformSettings from '../components/twin/TransformSettings';
import LiveOutput from '../components/twin/LiveOutput';
import ResultViewer from '../components/twin/ResultViewer';
import RowTransformTable from '../components/twin/RowTransformTable';
import SettingsChangeWarning from '../components/twin/SettingsChangeWarning';
import StepChangeWarning from '../components/twin/StepChangeWarning';
import { SettingsModal } from '../components/twin/SettingsModal';
import { ColumnsModal } from '../components/twin/ColumnsModal';
import { ExportSettingsModal } from '../components/twin/ExportSettingsModal';

type WizardStep = 'dataset' | 'analysis' | 'settings' | 'output';

const STEPS: { key: WizardStep; label: string; icon: React.ReactNode }[] = [
  { key: 'dataset', label: 'Dataset', icon: <Database size={18} /> },
  { key: 'analysis', label: 'Analysis', icon: <Wand2 size={18} /> },
  { key: 'settings', label: 'Settings', icon: <Settings size={18} /> },
  { key: 'output', label: 'Output', icon: <Sparkles size={18} /> },
];

const TwinTransformer: React.FC = () => {
  const navigate = useNavigate();
  
  // Wizard state
  const [currentStep, setCurrentStep] = useState<WizardStep>('dataset');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Dataset state
  const [datasetMeta, setDatasetMeta] = useState<DatasetMeta | null>(null);
  
  // Analysis state
  const [analysisResult, setAnalysisResult] = useState<ColumnAnalysisResult | null>(null);
  const [selectedAdminColumns, setSelectedAdminColumns] = useState<string[]>([]);
  const [excludeConfig, setExcludeConfig] = useState<Record<string, boolean>>({});
  const [excludedVariables, setExcludedVariables] = useState<string[]>([]);
  const [excludePatternVariables, setExcludePatternVariables] = useState<Record<string, string[]>>({});
  
  // Settings state
  const [chunkSize, setChunkSize] = useState(50);
  const [rowConcurrency, setRowConcurrency] = useState(10);
  const [rowLimit, setRowLimit] = useState(10); // Test için satır limiti
  const [processAllRows, setProcessAllRows] = useState(false); // Tüm satırlar için
  const [respondentIdColumn, setRespondentIdColumn] = useState<string>(''); // optional ID column for results
  
  // Job state
  const [currentJob, setCurrentJob] = useState<TransformJob | null>(null);
  const [results, setResults] = useState<TransformResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<TransformResult | null>(null);
  const [pollCleanup, setPollCleanup] = useState<(() => void) | null>(null);
  const [errorAction, setErrorAction] = useState<{ label: string; onClick: () => void } | null>(null);

  // Row table state (dataset rows + row-range results)
  const [rowsPageSize, setRowsPageSize] = useState(50);
  const [rowsPageIndex, setRowsPageIndex] = useState(0);
  const [rowsResponse, setRowsResponse] = useState<DatasetRowsResponse | null>(null);
  const [rowsLoading, setRowsLoading] = useState(false);
  const [rowsError, setRowsError] = useState<string | null>(null);
  const [tableResultsByRowIndex, setTableResultsByRowIndex] = useState<Record<number, TransformResult>>({});

  // Smart filters (from localStorage) - we show them as columns by filter title, not raw vars
  const [activeSmartFilters, setActiveSmartFilters] = useState<Array<{ id: string; title: string; sourceVars: string[]; source?: 'ai' | 'manual' }>>([]);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(0);
  const [totalResults, setTotalResults] = useState(0);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const PAGE_SIZE = 50;

  // Settings change warning state
  const [showSettingsChangeWarning, setShowSettingsChangeWarning] = useState(false);
  const [previousSettings, setPreviousSettings] = useState<{
    chunkSize: number;
    rowConcurrency: number;
    rowLimit: number;
    processAllRows: boolean;
  } | null>(null);
  // Flag to prevent settings change detection when loading settings from job
  const [isLoadingSettingsFromJob, setIsLoadingSettingsFromJob] = useState(false);

  // Modal states
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [showColumnsModal, setShowColumnsModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [showResetSuccessModal, setShowResetSuccessModal] = useState(false);
  const [exportSettings, setExportSettings] = useState({
    productId: '',
    productName: datasetMeta?.filename?.replace('.sav', '') || '',
    dataSource: datasetMeta?.filename || '',
    reviewRating: 5.0,
    reviewTitle: '', // Manual review title (optional)
    smartFilters: [] as Array<{ id: string; title: string; sourceVars: string[]; source?: 'ai' | 'manual' }>
  });

  // Step change warning state
  const [stepChangeWarning, setStepChangeWarning] = useState<{
    show: boolean;
    message: string;
    targetStep: WizardStep;
  } | null>(null);

  // Storage key helper
  const getStorageKey = (key: string) => {
    return datasetMeta ? `transform_${datasetMeta.id}_${key}` : null;
  };

  // Load dataset from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('currentDatasetMeta');
    if (!stored) {
      navigate('/');
      return;
    }
    const meta = JSON.parse(stored);
    setDatasetMeta(meta);
  }, [navigate]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollCleanup) {
        pollCleanup();
      }
    };
  }, [pollCleanup]);

  // Check for existing job FIRST - prioritize this to restore to output step if job exists
  // This runs before state loading so job takes precedence
  useEffect(() => {
    const checkExistingJob = async () => {
      if (!datasetMeta) return;
      
      try {
        const jobs = await transformService.getJobsForDataset(datasetMeta.id);
        // Check for any job (including completed) - user should see results
        const anyJob = jobs.find(j => ['running', 'paused', 'idle', 'completed'].includes(j.status));
        
        if (anyJob) {
          const jobStatus = await transformService.getJobStatus(anyJob.jobId);
          setCurrentJob(jobStatus);
          
          // If job exists (even completed), go to output step
          if (['running', 'paused', 'completed'].includes(jobStatus.status)) {
            setCurrentStep('output');
            loadResults(anyJob.jobId);
            
            if (jobStatus.status === 'running') {
              startPolling(anyJob.jobId);
            }
            // Don't load saved state if job exists - job state takes precedence
            return;
          }
        }
        
        // No active job - load saved state to restore where user left off
        const key = getStorageKey('state');
        if (key) {
          try {
            const stored = localStorage.getItem(key);
            if (stored) {
              const state = JSON.parse(stored);
              // Set flag to prevent settings change detection during loading
              setIsLoadingSettingsFromJob(true);
              if (state.step) setCurrentStep(state.step);
              if (state.analysisResult) setAnalysisResult(state.analysisResult);
              if (state.selectedAdminColumns) setSelectedAdminColumns(state.selectedAdminColumns);
              if (state.excludeConfig) setExcludeConfig(state.excludeConfig);
              if (state.excludedVariables) setExcludedVariables(state.excludedVariables);
              if (state.excludePatternVariables) setExcludePatternVariables(state.excludePatternVariables);
              if (state.chunkSize) setChunkSize(state.chunkSize);
              if (state.rowConcurrency) setRowConcurrency(state.rowConcurrency);
              if (state.rowLimit) setRowLimit(state.rowLimit);
              if (state.processAllRows !== undefined) setProcessAllRows(state.processAllRows);
              if (state.respondentIdColumn !== undefined) setRespondentIdColumn(state.respondentIdColumn);
              if (state.rowsPageSize) setRowsPageSize(state.rowsPageSize);
              if (state.rowsPageIndex) setRowsPageIndex(state.rowsPageIndex);
              setTimeout(() => setIsLoadingSettingsFromJob(false), 100);
            }
          } catch (e) {
            console.error('Failed to load state:', e);
          }
        }
      } catch (e) {
        // No existing job, try to load saved state
        const key = getStorageKey('state');
        if (key) {
          try {
            const stored = localStorage.getItem(key);
            if (stored) {
              const state = JSON.parse(stored);
              // Set flag to prevent settings change detection during loading
              setIsLoadingSettingsFromJob(true);
              if (state.step) setCurrentStep(state.step);
              if (state.analysisResult) setAnalysisResult(state.analysisResult);
              if (state.selectedAdminColumns) setSelectedAdminColumns(state.selectedAdminColumns);
              if (state.excludeConfig) setExcludeConfig(state.excludeConfig);
              if (state.excludedVariables) setExcludedVariables(state.excludedVariables);
              if (state.excludePatternVariables) setExcludePatternVariables(state.excludePatternVariables);
              if (state.chunkSize) setChunkSize(state.chunkSize);
              if (state.rowConcurrency) setRowConcurrency(state.rowConcurrency);
              if (state.rowLimit) setRowLimit(state.rowLimit);
              if (state.processAllRows !== undefined) setProcessAllRows(state.processAllRows);
              if (state.respondentIdColumn !== undefined) setRespondentIdColumn(state.respondentIdColumn);
              if (state.rowsPageSize) setRowsPageSize(state.rowsPageSize);
              if (state.rowsPageIndex) setRowsPageIndex(state.rowsPageIndex);
              setTimeout(() => setIsLoadingSettingsFromJob(false), 100);
            }
          } catch (e) {
            console.error('Failed to load state:', e);
          }
        }
      }
    };
    
    checkExistingJob();
  }, [datasetMeta?.id]); // Only when dataset ID changes

  // Load settings from job when job changes
  useEffect(() => {
    if (currentJob && currentJob.excludeOptionsConfig) {
      console.log('[Job Settings] Loading settings from job:', currentJob.excludeOptionsConfig);
      
      // Load exclude pattern variables from job
      if (currentJob.excludeOptionsConfig.excludePatternVariables) {
        setExcludePatternVariables(currentJob.excludeOptionsConfig.excludePatternVariables);
      }
      
      // Load excluded variables from job
      if (currentJob.excludeOptionsConfig.excludedVariables) {
        setExcludedVariables(currentJob.excludeOptionsConfig.excludedVariables);
      }
      
      // Load admin columns from job
      if (currentJob.adminColumns) {
        setSelectedAdminColumns(currentJob.adminColumns);
      }
      
      // Load other settings - set flag to prevent settings change detection
      setIsLoadingSettingsFromJob(true);
      if (currentJob.chunkSize) setChunkSize(currentJob.chunkSize);
      if (currentJob.rowConcurrency) setRowConcurrency(currentJob.rowConcurrency);
      if (currentJob.rowLimit) setRowLimit(currentJob.rowLimit);
      if (currentJob.respondentIdColumn) setRespondentIdColumn(currentJob.respondentIdColumn);
      // Clear flag after a short delay to allow state updates to complete
      setTimeout(() => setIsLoadingSettingsFromJob(false), 100);
    }
  }, [currentJob?.jobId]); // Only when job ID changes

  // Save state whenever relevant state changes (debounced to avoid too many writes)
  useEffect(() => {
    if (datasetMeta && currentStep !== 'dataset') {
      // Use a small timeout to batch multiple state changes
      const timeoutId = setTimeout(() => {
        const key = getStorageKey('state');
        if (key) {
          try {
            localStorage.setItem(key, JSON.stringify({
              step: currentStep,
              analysisResult,
              selectedAdminColumns,
              excludeConfig,
              excludedVariables,
              excludePatternVariables,
              chunkSize,
              rowConcurrency,
              rowLimit,
              processAllRows,
              respondentIdColumn,
              rowsPageSize,
              rowsPageIndex,
            }));
          } catch (e) {
            console.error('Failed to save state:', e);
          }
        }
      }, 300);
      return () => clearTimeout(timeoutId);
    }
  }, [currentStep, analysisResult, selectedAdminColumns, excludeConfig, excludedVariables, 
      excludePatternVariables, chunkSize, rowConcurrency, rowLimit, processAllRows, 
      respondentIdColumn, rowsPageSize, rowsPageIndex, datasetMeta?.id]);

  const loadResults = async (jobId: string, page: number = currentPage) => {
    try {
      const offset = page * PAGE_SIZE;
      const response = await transformService.getResults(jobId, offset, PAGE_SIZE);
      setResults(response.results);
      setTotalResults(response.total || response.results.length);
      setLastUpdateTime(new Date());
    } catch (e) {
      console.error('Failed to load results:', e);
    }
  };

  const loadRows = async (datasetId: string, page: number = rowsPageIndex, size: number = rowsPageSize) => {
    setRowsLoading(true);
    setRowsError(null);
    try {
      const offset = page * size;
      const response = await transformService.getDatasetRows(datasetId, offset, size);
      setRowsResponse(response);
    } catch (e) {
      setRowsError(e instanceof Error ? e.message : 'Failed to load rows');
    } finally {
      setRowsLoading(false);
    }
  };

  const loadTableResultsRange = async (jobId: string, startRow: number, limit: number) => {
    try {
      const response = await transformService.getResultsRange(jobId, startRow, limit);
      const next: Record<number, TransformResult> = {};
      response.results.forEach(r => {
        next[r.rowIndex] = r;
      });
      setTableResultsByRowIndex(next);
    } catch (e) {
      // Non-fatal (table still shows rows)
    }
  };

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    if (currentJob) {
      loadResults(currentJob.jobId, newPage);
    }
  };

  const startPolling = useCallback((jobId: string) => {
    const cleanup = transformService.pollJobStatus(
      jobId,
      (job) => {
        setCurrentJob(job);
        // Always refresh first page when running to show new results
        if (job.status === 'running') {
          setCurrentPage(0);
          loadResults(jobId, 0);
        } else {
          loadResults(jobId, currentPage);
        }
        setTotalResults(job.processedRows);

        // Keep row table in sync for the currently visible page (row-range query)
        const startRow = rowsPageIndex * rowsPageSize;
        loadTableResultsRange(jobId, startRow, rowsPageSize);
      },
      (err) => {
        console.error('Polling error:', err);
      },
      2000
    );
    setPollCleanup(() => cleanup);
  }, [currentPage, rowsPageIndex, rowsPageSize]);

  // Load active smart filters (used as columns in the results table)
  // Loads from database, with localStorage fallback for migration
  useEffect(() => {
    if (!datasetMeta?.id) return;
    
    const loadFilters = async () => {
      try {
        // Try to load from database first
        const result = await apiService.getSmartFilters(datasetMeta.id);
        if (result && result.filters && result.filters.length > 0) {
          interface ExtendedFilter {
            id: string;
            title: string;
            sourceVars: string[];
            isApplied?: boolean;
            source?: 'ai' | 'manual';
          }
          const extendedFilters = result.filters as ExtendedFilter[];
          const active = extendedFilters
            .filter(f => f.isApplied !== false) // Default to active if isApplied is not set
            .map(f => ({ id: f.id, title: f.title, sourceVars: f.sourceVars || [], source: f.source }));
          setActiveSmartFilters(active);
          return;
        }
      } catch (e) {
        console.error('Failed to load smart filters from database:', e);
      }
      
      // Fallback: try localStorage (migration support)
      try {
        const extendedRaw = localStorage.getItem(`extendedSmartFilters_${datasetMeta.id}`);
        if (extendedRaw) {
          interface ExtendedFilter {
            id: string;
            title: string;
            sourceVars: string[];
            isApplied: boolean;
            source: 'ai' | 'manual';
          }
          const extendedFilters = JSON.parse(extendedRaw) as ExtendedFilter[];
          const active = extendedFilters
            .filter(f => f.isApplied)
            .map(f => ({ id: f.id, title: f.title, sourceVars: f.sourceVars || [], source: f.source }));
          setActiveSmartFilters(active);
          return;
        }
        
        // Legacy format fallback
        const rawRecs = localStorage.getItem(`smartFilters_${datasetMeta.id}`);
        const rawActive = localStorage.getItem(`activeFilters_${datasetMeta.id}`);
        if (!rawRecs || !rawActive) {
          setActiveSmartFilters([]);
          return;
        }
        const recs = JSON.parse(rawRecs) as SmartFilterResponse;
        const activeIds = new Set<string>(JSON.parse(rawActive) as string[]);
        const filters: SmartFilter[] = (recs as any)?.filters || [];
        const active = filters
          .filter(f => activeIds.has(f.id))
          .map(f => ({ id: f.id, title: f.title, sourceVars: f.sourceVars || [] }));
        setActiveSmartFilters(active);
      } catch (e) {
        console.error('Failed to load smart filters from localStorage:', e);
        setActiveSmartFilters([]);
      }
    };
    
    loadFilters();
  }, [datasetMeta?.id]);

  // Detect settings changes when job is running
  useEffect(() => {
    // Skip detection if we're loading settings from job
    if (isLoadingSettingsFromJob) return;
    
    if (!currentJob || currentJob.status !== 'running') {
      setPreviousSettings(null);
      return;
    }

    const currentSettings = {
      chunkSize,
      rowConcurrency,
      rowLimit,
      processAllRows,
    };

    if (previousSettings) {
      const settingsChanged =
        previousSettings.chunkSize !== currentSettings.chunkSize ||
        previousSettings.rowConcurrency !== currentSettings.rowConcurrency ||
        previousSettings.rowLimit !== currentSettings.rowLimit ||
        previousSettings.processAllRows !== currentSettings.processAllRows;

      if (settingsChanged) {
        setShowSettingsChangeWarning(true);
        // Auto-pause when settings change
        handlePause();
      }
    } else {
      // Initialize previous settings
      setPreviousSettings(currentSettings);
    }
  }, [chunkSize, rowConcurrency, rowLimit, processAllRows, currentJob?.status, isLoadingSettingsFromJob]);

  // Save previous settings when job starts
  useEffect(() => {
    if (currentJob && currentJob.status === 'running' && !previousSettings) {
      setPreviousSettings({
        chunkSize,
        rowConcurrency,
        rowLimit,
        processAllRows,
      });
    }
  }, [currentJob?.status]);

  // Load dataset rows when output step is visible (and when page/pageSize changes)
  useEffect(() => {
    if (!datasetMeta?.id) return;
    if (currentStep !== 'output') return;
    loadRows(datasetMeta.id, rowsPageIndex, rowsPageSize);
  }, [datasetMeta?.id, currentStep, rowsPageIndex, rowsPageSize]);

  // Load row-range transform results for currently visible rows
  useEffect(() => {
    if (!currentJob?.jobId) return;
    if (currentStep !== 'output') return;
    const startRow = rowsPageIndex * rowsPageSize;
    loadTableResultsRange(currentJob.jobId, startRow, rowsPageSize);
  }, [currentJob?.jobId, currentStep, rowsPageIndex, rowsPageSize]);

  const handleAnalyzeColumns = async () => {
    if (!datasetMeta) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await transformService.analyzeColumns(datasetMeta.id);
      setAnalysisResult(result);
      
      // Set default selections
      setSelectedAdminColumns(result.adminColumns.map(c => c.code));
      setExcludedVariables((result.excludedByDefaultColumns || []).map(c => c.code));

      // Default respondent ID column - use suggested from backend or fallback to pattern matching
      const defaultId = result.suggestedIdColumn ||
        result.adminColumns.find(c => /id/i.test(c.code) || /id/i.test(c.label))?.code ||
        result.transformableColumns.find(c => /id/i.test(c.code) || /id/i.test(c.label))?.code ||
        '';
      setRespondentIdColumn(defaultId);
      
      const defaultExclude: Record<string, boolean> = {};
      result.excludeCandidates.forEach((c: ExcludeCandidate) => {
        defaultExclude[c.patternKey] = c.defaultExclude;
      });
      setExcludeConfig(defaultExclude);

      // Default: pattern applies to all affected variables (user can uncheck)
      const defaultPatternVars: Record<string, string[]> = {};
      result.excludeCandidates.forEach((c: ExcludeCandidate) => {
        defaultPatternVars[c.patternKey] = [...(c.affectedVariables || [])];
      });
      setExcludePatternVariables(defaultPatternVars);
      
      setCurrentStep('analysis');
      // State will be saved by useEffect
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartTransform = async (continueFromExisting: boolean = false) => {
    if (!datasetMeta) return;
    
    setIsLoading(true);
    setError(null);
    setErrorAction(null);
    
    try {
      // If continuing from existing job and row limit increased, just update and resume
      if (continueFromExisting && currentJob && currentJob.status !== 'running') {
        const newRowLimit = processAllRows ? undefined : rowLimit;
        const effectiveNewLimit = newRowLimit || datasetMeta.nRows;
        const effectiveOldLimit = currentJob.totalRows;
        
        // If new limit is higher than old limit, we can continue
        if (effectiveNewLimit > effectiveOldLimit) {
          // Update job config and resume
          const response = await transformService.startJob({
            datasetId: datasetMeta.id,
            chunkSize,
            rowConcurrency,
            excludeOptionsConfig: excludeConfig,
            excludePatternVariables,
            adminColumns: selectedAdminColumns,
            excludedVariables,
            respondentIdColumn: respondentIdColumn || undefined,
            rowLimit: newRowLimit,
          });
          
          const jobStatus = await transformService.getJobStatus(response.jobId);
          setCurrentJob(jobStatus);
          setCurrentStep('output');
          
          if (jobStatus.status === 'running') {
            startPolling(response.jobId);
          }
          setIsLoading(false);
          return;
        }
      }
      
      // UX: If user lowered rowLimit below already processed rows, require reset before starting.
      if (!processAllRows && currentJob?.processedRows && rowLimit < currentJob.processedRows) {
        setError('The selected row limit is smaller than the number of rows already processed in the current job. Please reset first to apply the new limit.');
        setErrorAction({
          label: 'Reset and Restart',
          onClick: async () => {
            if (!currentJob) return;
            setIsLoading(true);
            setError(null);
            try {
              await transformService.resetJob(currentJob.jobId, 'DELETE');
              setCurrentJob(null);
              await handleStartTransform(false);
            } finally {
              setIsLoading(false);
            }
          }
        });
        return;
      }

      const response = await transformService.startJob({
        datasetId: datasetMeta.id,
        chunkSize,
        rowConcurrency,
        excludeOptionsConfig: excludeConfig,
        excludePatternVariables,
        adminColumns: selectedAdminColumns,
        excludedVariables,
        respondentIdColumn: respondentIdColumn || undefined,
        rowLimit: processAllRows ? undefined : rowLimit,
      });
      
      const jobStatus = await transformService.getJobStatus(response.jobId);
      setCurrentJob(jobStatus);
      setCurrentStep('output');

      // Only poll while running
      if (jobStatus.status === 'running') {
        startPolling(response.jobId);
      }
    } catch (e) {
      const status = (e as any)?.status as number | undefined;
      setError(e instanceof Error ? e.message : 'Failed to start process');
      if (status === 409 && currentJob) {
        setErrorAction({
          label: 'Reset and Restart',
          onClick: async () => {
            setIsLoading(true);
            setError(null);
            try {
              await transformService.resetJob(currentJob.jobId, 'DELETE');
              setCurrentJob(null);
              await handleStartTransform(false);
            } finally {
              setIsLoading(false);
            }
          }
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handlePause = async () => {
    if (!currentJob) return;
    try {
      await transformService.pauseJob(currentJob.jobId);
      if (pollCleanup) pollCleanup();
      const status = await transformService.getJobStatus(currentJob.jobId);
      setCurrentJob(status);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to pause');
    }
  };

  const handleResume = async () => {
    if (!currentJob) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      // If job is completed and we want to continue, we need to increase row limit or restart
      if (currentJob.status === 'completed' && currentJob.processedRows < currentJob.totalRows) {
        // Stop any existing polling first
        if (pollCleanup) {
          pollCleanup();
          setPollCleanup(null);
        }
        
        // Calculate new row limit:
        // Use the user's configured rowLimit from settings modal (how many rows per batch)
        // If not set, fall back to rowConcurrency
        const userRowLimit = rowLimit || currentJob.rowConcurrency || rowConcurrency || 1;
        const jobRowConcurrency = currentJob.rowConcurrency || rowConcurrency || 1;
        
        // The increment is the user's rowLimit setting (how many more rows to process)
        const increment = userRowLimit;
        
        const newLimit = Math.min(
          currentJob.processedRows + increment,
          currentJob.totalRows
        );
        
        console.log(`[Continue] Increasing row limit from ${currentJob.rowLimit} to ${newLimit} (increment: ${increment}, userRowLimit: ${userRowLimit}, concurrency: ${jobRowConcurrency})`);
        
        // IMPORTANT: Use job settings directly, NOT state (state might be stale or not yet loaded)
        const currentExcludeConfig = currentJob.excludeOptionsConfig || {};
        const jobExcludePatternVariables = currentExcludeConfig.excludePatternVariables || {};
        const jobExcludedVariables = currentExcludeConfig.excludedVariables || [];
        const jobAdminColumns = currentJob.adminColumns || [];
        
        // Extract boolean toggles (none_of_above: true, prefer_not_to_say: true, etc.)
        const booleanToggles: Record<string, boolean> = {};
        for (const [key, value] of Object.entries(currentExcludeConfig)) {
          if (typeof value === 'boolean') {
            booleanToggles[key] = value;
          }
        }
        
        console.log('[Continue] Using job settings:', {
          excludePatternVariables: jobExcludePatternVariables,
          excludedVariables: jobExcludedVariables,
          adminColumns: jobAdminColumns,
          booleanToggles
        });
        
        // Call start endpoint with new row limit and job settings
        const response = await transformService.startJob({
          datasetId: datasetMeta!.id,
          chunkSize: currentJob.chunkSize || chunkSize,
          rowConcurrency: currentJob.rowConcurrency || rowConcurrency,
          rowLimit: newLimit,
          excludeOptionsConfig: booleanToggles,  // Include boolean toggles!
          excludePatternVariables: jobExcludePatternVariables,
          excludedVariables: jobExcludedVariables,
          adminColumns: jobAdminColumns,
          respondentIdColumn: currentJob.respondentIdColumn || respondentIdColumn,
          autoStart: true  // Start job immediately (Continue button)
        });
        
        // Get updated job status
        const jobStatus = await transformService.getJobStatus(response.jobId);
        setCurrentJob(jobStatus);
        
        // Start polling if job is running
        if (jobStatus.status === 'running') {
          startPolling(response.jobId);
        }
      } else {
        // Normal resume for paused jobs - include current settings
        // Use latest UI settings if changed, otherwise use job settings
        await transformService.resumeJob(currentJob.jobId, {
          rowConcurrency: rowConcurrency || currentJob.rowConcurrency,
          chunkSize: chunkSize || currentJob.chunkSize,
          rowLimit: rowLimit || currentJob.rowLimit || undefined,
        });
        const status = await transformService.getJobStatus(currentJob.jobId);
        setCurrentJob(status);
        startPolling(currentJob.jobId);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to resume');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    if (!currentJob) return;
    try {
      await transformService.stopJob(currentJob.jobId);
      if (pollCleanup) pollCleanup();
      const status = await transformService.getJobStatus(currentJob.jobId);
      setCurrentJob(status);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to stop');
    }
  };

  const handleCancel = async () => {
    if (!currentJob) return;
    try {
      const result = await transformService.cancelJob(currentJob.jobId);
      if (pollCleanup) pollCleanup();
      
      // Get updated job status
      const status = await transformService.getJobStatus(currentJob.jobId);
      setCurrentJob(status);
      
      // Show success message
      console.log(`Job cancelled: Kept ${result.completedKept} completed, removed ${result.waitingRemoved} waiting`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to cancel');
    }
  };

  const handleReset = async () => {
    if (!currentJob) return;
    try {
      await transformService.resetJob(currentJob.jobId, 'DELETE');
      if (pollCleanup) pollCleanup();
      setCurrentJob(null);
      setResults([]);
      
      // Clear saved state for this dataset
      if (datasetMeta) {
        const key = getStorageKey('state');
        if (key) localStorage.removeItem(key);
      }
      
      // Show success modal (don't redirect to settings)
      setShowResetSuccessModal(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to reset');
    }
  };

  const handleChangeColumns = async () => {
    // If no analysis result, try to get it from job or fetch from backend
    if (!analysisResult && datasetMeta) {
      setIsLoading(true);
      try {
        // First check if current job has cached analysis
        if (currentJob?.columnAnalysis) {
          console.log('[ChangeColumns] Using cached analysis from job');
          setAnalysisResult(currentJob.columnAnalysis);
        } else {
          // Fetch from backend (will return cached if available)
          console.log('[ChangeColumns] Fetching analysis from backend');
          const result = await transformService.analyzeColumns(datasetMeta.id);
          setAnalysisResult(result);
        }
      } catch (e) {
        console.error('Failed to load column analysis:', e);
        setError(e instanceof Error ? e.message : 'Failed to load column analysis');
        setIsLoading(false);
        return;
      } finally {
        setIsLoading(false);
      }
    }
    setShowColumnsModal(true);
  };

  const handleExportJson = async () => {
    if (!currentJob) return;
    try {
      await transformService.exportResultsJson(currentJob.jobId);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed');
    }
  };

  const handleExportCsv = async () => {
    // Show export settings modal
    setShowExportModal(true);
  };

  const handleExportWithSettings = async (settings: any) => {
    if (!currentJob) return;
    try {
      await transformService.exportResultsCsv(
        currentJob.jobId,
        settings.productId,
        settings.productName,
        settings.dataSource,
        settings.reviewRating,
        settings.reviewTitle || undefined,
        settings.smartFilters || activeSmartFilters
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed');
    }
  };

  const handleAdminColumnToggle = (code: string) => {
    setSelectedAdminColumns(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
  };

  const handleExcludedVariableToggle = (code: string) => {
    setExcludedVariables(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
  };

  const handleSelectAllExcludedVariables = (select: boolean, allCodes: string[]) => {
    setExcludedVariables(select ? [...allCodes] : []);
  };

  const handleSelectAllAdmin = (select: boolean) => {
    if (select && analysisResult) {
      setSelectedAdminColumns(analysisResult.adminColumns.map(c => c.code));
    } else {
      setSelectedAdminColumns([]);
    }
  };

  const handleExcludeToggle = (patternKey: string) => {
    setExcludeConfig(prev => ({
      ...prev,
      [patternKey]: !prev[patternKey],
    }));
  };

  const handleExcludePatternVariableToggle = (patternKey: string, code: string) => {
    setExcludePatternVariables(prev => {
      const current = new Set(prev[patternKey] || []);
      if (current.has(code)) current.delete(code);
      else current.add(code);
      return { ...prev, [patternKey]: Array.from(current) };
    });
  };

  const handleExcludePatternSelectAll = (patternKey: string, select: boolean, allVars: string[]) => {
    setExcludePatternVariables(prev => ({
      ...prev,
      [patternKey]: select ? [...allVars] : [],
    }));
  };

  const getCurrentStepIndex = () => STEPS.findIndex(s => s.key === currentStep);

  const canGoNext = () => {
    switch (currentStep) {
      case 'dataset':
        return !!datasetMeta;
      case 'analysis':
        return !!analysisResult;
      case 'settings':
        return true;
      default:
        return false;
    }
  };

  const goToNextStep = () => {
    const idx = getCurrentStepIndex();
    if (idx < STEPS.length - 1) {
      const nextStep = STEPS[idx + 1].key;
      
      if (currentStep === 'dataset' && !analysisResult) {
        handleAnalyzeColumns();
      } else if (currentStep === 'settings') {
        // Settings step handles start internally via TransformSettings component
        // This should not be called, but if it is, start with restart mode
        handleStartTransform(false);
      } else {
        setCurrentStep(nextStep);
      }
    }
  };

  const goToPreviousStep = () => {
    const idx = getCurrentStepIndex();
    if (idx > 0) {
      handleStepClick(STEPS[idx - 1].key);
    }
  };

  const handleStepClick = (targetStep: WizardStep) => {
    const currentIdx = getCurrentStepIndex();
    const targetIdx = STEPS.findIndex(s => s.key === targetStep);
    
    // İleriye gitmeye izin verme
    if (targetIdx > currentIdx) {
      return;
    }
    
    // Geriye giderken uyarı göster
    if (targetIdx < currentIdx && currentJob && currentJob.status === 'running') {
      setStepChangeWarning({
        show: true,
        targetStep,
        message: `Transformation is currently running. Going back will pause the process.`,
      });
      return;
    }
    
    // Analysis adımına dönüşte özel uyarı
    if (targetStep === 'analysis' && currentJob && currentJob.processedRows > 0) {
      setStepChangeWarning({
        show: true,
        targetStep,
        message: `${currentJob.processedRows} rows have been processed. If you change column selections, you may need to restart.`,
      });
      return;
    }
    
    // Uyarı yoksa direkt git
    setCurrentStep(targetStep);
  };

  const handleStepChangeConfirm = () => {
    if (!stepChangeWarning) return;
    
    // Pause if running
    if (currentJob && currentJob.status === 'running') {
      handlePause();
    }
    
    setCurrentStep(stepChangeWarning.targetStep);
    setStepChangeWarning(null);
  };

  const handleSettingsContinueWithNew = () => {
    setShowSettingsChangeWarning(false);
    setPreviousSettings({
      chunkSize,
      rowConcurrency,
      rowLimit,
      processAllRows,
    });
    // Resume with new settings
    handleResume();
  };

  const handleSettingsRestart = async () => {
    setShowSettingsChangeWarning(false);
    if (currentJob) {
      await handleReset();
    }
    setPreviousSettings({
      chunkSize,
      rowConcurrency,
      rowLimit,
      processAllRows,
    });
    // Start new job
    handleStartTransform(false);
  };

  const handleSettingsCancelChanges = () => {
    setShowSettingsChangeWarning(false);
    // Restore previous settings
    if (previousSettings) {
      setChunkSize(previousSettings.chunkSize);
      setRowConcurrency(previousSettings.rowConcurrency);
      setRowLimit(previousSettings.rowLimit);
      setProcessAllRows(previousSettings.processAllRows);
    }
    // Resume with old settings
    handleResume();
  };

  if (!datasetMeta) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center space-x-2">
            <Sparkles className="text-purple-600" />
            <span>Twin Transformer</span>
          </h1>
          <p className="text-gray-500 mt-1">
            {datasetMeta.filename} - Digital Twin Sentence Transformation
          </p>
        </div>
      </div>

      {/* Stepper */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <div className="flex items-center justify-between">
          {STEPS.map((step, idx) => (
            <React.Fragment key={step.key}>
              <button
                onClick={() => {
                  // Only allow going back to previous steps
                  if (idx <= getCurrentStepIndex()) {
                    handleStepClick(step.key);
                  }
                }}
                disabled={idx > getCurrentStepIndex()}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${
                  currentStep === step.key
                    ? 'bg-blue-600 text-white'
                    : idx < getCurrentStepIndex()
                    ? 'bg-green-100 text-green-700 cursor-pointer hover:bg-green-200'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                {idx < getCurrentStepIndex() ? (
                  <CheckCircle size={18} />
                ) : (
                  step.icon
                )}
                <span className="font-medium">{step.label}</span>
              </button>
              
              {idx < STEPS.length - 1 && (
                <div className={`flex-1 h-0.5 mx-2 ${
                  idx < getCurrentStepIndex() ? 'bg-green-500' : 'bg-gray-200'
                }`} />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start space-x-3">
          <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <p className="font-medium text-red-700">Error</p>
            <p className="text-red-600 text-sm mt-1">{error}</p>
            {errorAction && (
              <button
                onClick={errorAction.onClick}
                className="mt-3 inline-flex items-center px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
              >
                {errorAction.label}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Step Content */}
      <div className="min-h-[400px]">
        {/* Step 1: Dataset Selection */}
        {currentStep === 'dataset' && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <div className="text-center max-w-lg mx-auto py-8">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Database className="w-8 h-8 text-blue-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Dataset Ready
              </h2>
              <p className="text-gray-600 mb-6">
                File <strong>{datasetMeta.filename}</strong> has been loaded.
                <br />
                {datasetMeta.nRows.toLocaleString()} rows, {datasetMeta.nCols} columns
              </p>
              
              <div className="grid grid-cols-3 gap-4 mb-8">
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-2xl font-bold text-gray-900">
                    {datasetMeta.nRows.toLocaleString()}
                  </p>
                  <p className="text-sm text-gray-500">Respondents</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-2xl font-bold text-gray-900">
                    {datasetMeta.nCols}
                  </p>
                  <p className="text-sm text-gray-500">Columns</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className={`text-2xl font-bold ${
                    datasetMeta.digitalTwinReadiness === 'green' ? 'text-green-600' :
                    datasetMeta.digitalTwinReadiness === 'yellow' ? 'text-amber-600' :
                    'text-red-600'
                  }`}>
                    {datasetMeta.digitalTwinReadiness === 'green' ? 'Good' :
                     datasetMeta.digitalTwinReadiness === 'yellow' ? 'Medium' : 'Low'}
                  </p>
                  <p className="text-sm text-gray-500">Quality</p>
                </div>
              </div>

              <p className="text-sm text-gray-500">
                Start column analysis to continue
              </p>
            </div>
          </div>
        )}

        {/* Step 2: Column Analysis */}
        {currentStep === 'analysis' && analysisResult && (
          <ColumnAnalysis
            adminColumns={analysisResult.adminColumns}
            excludedByDefaultColumns={analysisResult.excludedByDefaultColumns || []}
            excludeCandidates={analysisResult.excludeCandidates}
            totalColumns={analysisResult.totalColumns}
            totalRows={analysisResult.totalRows}
            selectedAdminColumns={selectedAdminColumns}
            onAdminColumnToggle={handleAdminColumnToggle}
            onSelectAllAdmin={handleSelectAllAdmin}
            excludedVariables={excludedVariables}
            onExcludedVariableToggle={handleExcludedVariableToggle}
            onSelectAllExcludedVariables={handleSelectAllExcludedVariables}
            excludeConfig={excludeConfig}
            onExcludeToggle={handleExcludeToggle}
            excludePatternVariables={excludePatternVariables}
            onExcludePatternVariableToggle={handleExcludePatternVariableToggle}
            onExcludePatternSelectAll={handleExcludePatternSelectAll}
          />
        )}

        {/* Step 3: Settings */}
        {currentStep === 'settings' && analysisResult && (
          <TransformSettings
            chunkSize={chunkSize}
            rowConcurrency={rowConcurrency}
            rowLimit={rowLimit}
            processAllRows={processAllRows}
            onChunkSizeChange={setChunkSize}
            onRowConcurrencyChange={setRowConcurrency}
            onRowLimitChange={setRowLimit}
            onProcessAllRowsChange={setProcessAllRows}
            totalColumns={analysisResult.totalColumns}
            totalRows={analysisResult.totalRows}
            excludedColumns={selectedAdminColumns.length + excludedVariables.length}
            respondentIdColumn={respondentIdColumn}
            onRespondentIdColumnChange={setRespondentIdColumn}
            idColumnOptions={(datasetMeta.variables || []).map(v => ({ code: v.code, label: v.label }))}
            currentJob={currentJob}
            onStart={handleStartTransform}
            onReset={async () => {
              if (currentJob) {
                await transformService.resetJob(currentJob.jobId, 'DELETE');
                setCurrentJob(null);
              }
            }}
          />
        )}

        {/* Step 4: Output */}
        {currentStep === 'output' && (
          <div className="space-y-6">
            <LiveOutput
              job={currentJob}
              isLoading={isLoading}
              error={error}
              onStart={handleStartTransform}
              onPause={handlePause}
              onResume={handleResume}
              onStop={handleStop}
              onCancel={handleCancel}
              onReset={handleReset}
              onExportJson={handleExportJson}
              onExportCsv={handleExportCsv}
              onChangeSettings={() => setShowSettingsModal(true)}
              onChangeColumns={handleChangeColumns}
              results={results}
              totalResults={totalResults}
              currentPage={currentPage}
              pageSize={PAGE_SIZE}
              onPageChange={handlePageChange}
              onSelectResult={async (r) => {
                if (!currentJob) {
                  setSelectedResult(r);
                  return;
                }
                try {
                  const full = await transformService.getResultByRow(currentJob.jobId, r.rowIndex);
                  setSelectedResult(full);
                } catch {
                  setSelectedResult(r);
                }
              }}
              selectedRowIndex={selectedResult?.rowIndex ?? null}
              lastUpdateTime={lastUpdateTime}
              currentProcessingRow={currentJob?.currentRowIndex ?? currentJob?.processedRows}
              latestSentence={results.length > 0 ? results[0]?.sentences?.[0]?.sentence : null}
              customResultsView={
                <RowTransformTable
                  datasetMeta={datasetMeta}
                  rowsResponse={rowsResponse}
                  isLoadingRows={rowsLoading}
                  rowsError={rowsError}
                  pageSize={rowsPageSize}
                  pageIndex={rowsPageIndex}
                  onPageSizeChange={setRowsPageSize}
                  onPageIndexChange={setRowsPageIndex}
                  job={currentJob}
                  resultsByRowIndex={tableResultsByRowIndex}
                  smartFilters={activeSmartFilters}
                  onOpenRowDetail={async (rowIndex) => {
                    if (!currentJob) return;
                    try {
                      const full = await transformService.getResultByRow(currentJob.jobId, rowIndex);
                      setSelectedResult(full);
                    } catch (e) {
                      // ignore
                    }
                  }}
                />
              }
            />
          </div>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between">
        <button
          onClick={goToPreviousStep}
          disabled={getCurrentStepIndex() === 0}
          className="flex items-center space-x-2 px-6 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronLeft size={20} />
          <span>Back</span>
        </button>

        {currentStep === 'output' ? (
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentStep('analysis')}
              className="flex items-center space-x-2 px-4 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors"
            >
              <Wand2 size={18} />
              <span>Change Columns</span>
            </button>
            <button
              onClick={() => setCurrentStep('settings')}
              className="flex items-center space-x-2 px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
            >
              <Settings size={18} />
              <span>Change Settings</span>
            </button>
          </div>
        ) : currentStep === 'settings' ? (
          <button
            onClick={() => {
              // Eğer existing job varsa continue/restart moduna göre başlat
              // Yoksa yeni job başlat
              if (currentJob && ['completed', 'paused', 'failed'].includes(currentJob.status)) {
                // TransformSettings içindeki continueMode'a göre başlat
                // continueMode state'i TransformSettings içinde, bu yüzden direkt handleStartTransform çağırıyoruz
                // TransformSettings component'i kendi içinde continue/restart seçimini yapıyor
                handleStartTransform(false); // TransformSettings içindeki continueMode'a göre işlem yapılacak
              } else {
                handleStartTransform(false);
              }
            }}
            disabled={!canGoNext() || isLoading}
            className="flex items-center space-x-2 px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                <span>Starting...</span>
              </>
            ) : (
              <>
                <Sparkles size={20} />
                <span>Start Transformation</span>
              </>
            )}
          </button>
        ) : (
          <button
            onClick={goToNextStep}
            disabled={!canGoNext() || isLoading}
            className="flex items-center space-x-2 px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <span>
                  {currentStep === 'dataset' ? 'Start Analysis' : 'Continue'}
                </span>
                <ChevronRight size={20} />
              </>
            )}
          </button>
        )}
      </div>

      {/* Result Viewer Modal */}
      <ResultViewer
        result={selectedResult}
        datasetMeta={datasetMeta}
        rowData={selectedResult && rowsResponse?.rows 
          ? rowsResponse.rows.find(r => r.index === selectedResult.rowIndex)?.data || null
          : null}
        onClose={() => setSelectedResult(null)}
      />

      {/* Settings Change Warning */}
      <SettingsChangeWarning
        show={showSettingsChangeWarning}
        lastProcessedRow={currentJob?.processedRows || 0}
        onContinueWithNewSettings={handleSettingsContinueWithNew}
        onRestartFromBeginning={handleSettingsRestart}
        onCancelChanges={handleSettingsCancelChanges}
        onClose={() => setShowSettingsChangeWarning(false)}
      />

      {/* Step Change Warning */}
      {stepChangeWarning && (
        <StepChangeWarning
          show={stepChangeWarning.show}
          message={stepChangeWarning.message}
          targetStep={stepChangeWarning.targetStep}
          onConfirm={handleStepChangeConfirm}
          onCancel={() => setStepChangeWarning(null)}
        />
      )}

      {/* Settings Modal */}
      <SettingsModal
        show={showSettingsModal}
        onClose={() => setShowSettingsModal(false)}
        chunkSize={chunkSize}
        rowConcurrency={rowConcurrency}
        rowLimit={rowLimit}
        onChunkSizeChange={setChunkSize}
        onRowConcurrencyChange={setRowConcurrency}
        onRowLimitChange={setRowLimit}
        onApply={async () => {
          // Save settings changes to the current job
          if (currentJob && datasetMeta) {
            try {
              // Build excludeOptionsConfig with boolean toggles from current job
              const currentExcludeConfig = currentJob.excludeOptionsConfig || {};
              const booleanToggles: Record<string, boolean> = {};
              
              // Preserve boolean toggles from existing config
              for (const [key, value] of Object.entries(currentExcludeConfig)) {
                if (typeof value === 'boolean') {
                  booleanToggles[key] = value;
                }
              }
              
              console.log('[SettingsModal] Saving settings:', {
                chunkSize,
                rowConcurrency,
                rowLimit,
                excludePatternVariables,
                excludedVariables,
                adminColumns: selectedAdminColumns,
                booleanToggles
              });
              
              // Update job settings (will NOT start if completed, just updates config)
              await transformService.startJob({
                datasetId: datasetMeta.id,
                chunkSize: chunkSize,
                rowConcurrency: rowConcurrency,
                rowLimit: rowLimit,
                excludeOptionsConfig: booleanToggles,  // Include boolean toggles!
                excludePatternVariables: excludePatternVariables,
                excludedVariables: excludedVariables,
                adminColumns: selectedAdminColumns,
                respondentIdColumn: currentJob.respondentIdColumn || respondentIdColumn,
                autoStart: false  // Don't start job, just update settings
              });
              
              // Refresh job status to get updated settings
              const updatedJob = await transformService.getJobStatus(currentJob.jobId);
              setCurrentJob(updatedJob);
              
              console.log('[SettingsModal] Settings saved, updated job:', updatedJob);
            } catch (e) {
              console.error('Failed to save settings:', e);
              setError(e instanceof Error ? e.message : 'Failed to save settings');
            }
          }
        }}
      />

      {/* Columns Modal */}
      <ColumnsModal
        show={showColumnsModal}
        onClose={() => setShowColumnsModal(false)}
        columnAnalysis={analysisResult}
        selectedAdminColumns={selectedAdminColumns}
        excludePatternVariables={excludePatternVariables}
        onAdminColumnsChange={setSelectedAdminColumns}
        onExcludePatternVariablesChange={setExcludePatternVariables}
        onApply={async () => {
          // Save column changes to the current job
          if (currentJob && datasetMeta) {
            try {
              // Build excludeOptionsConfig with boolean toggles from current job
              // These control which patterns are ENABLED (true = enabled)
              const currentExcludeConfig = currentJob.excludeOptionsConfig || {};
              const booleanToggles: Record<string, boolean> = {};
              
              // Preserve boolean toggles from existing config
              for (const [key, value] of Object.entries(currentExcludeConfig)) {
                if (typeof value === 'boolean') {
                  booleanToggles[key] = value;
                }
              }
              
              console.log('[ColumnsModal] Saving columns:', {
                excludePatternVariables,
                excludedVariables,
                adminColumns: selectedAdminColumns,
                booleanToggles
              });
              
              // Update job settings with new column selections (will NOT start if completed, just updates config)
              await transformService.startJob({
                datasetId: datasetMeta.id,
                chunkSize: currentJob.chunkSize || chunkSize,
                rowConcurrency: currentJob.rowConcurrency || rowConcurrency,
                rowLimit: currentJob.rowLimit || rowLimit,
                excludeOptionsConfig: booleanToggles,  // Include boolean toggles!
                excludePatternVariables: excludePatternVariables,
                excludedVariables: excludedVariables,
                adminColumns: selectedAdminColumns,
                respondentIdColumn: currentJob.respondentIdColumn || respondentIdColumn,
                autoStart: false  // Don't start job, just update settings
              });
              
              // Refresh job status to get updated settings
              const updatedJob = await transformService.getJobStatus(currentJob.jobId);
              setCurrentJob(updatedJob);
              
              console.log('[ColumnsModal] Column settings saved, updated job:', updatedJob);
            } catch (e) {
              console.error('Failed to save column settings:', e);
              setError(e instanceof Error ? e.message : 'Failed to save column settings');
            }
          }
        }}
      />

      {/* Export Settings Modal */}
      <ExportSettingsModal
        show={showExportModal}
        onClose={() => setShowExportModal(false)}
        defaultSettings={exportSettings}
        onExport={handleExportWithSettings}
        smartFilters={activeSmartFilters.map(f => ({
          id: f.id,
          title: f.title,
          sourceVars: f.sourceVars,
          source: f.source || 'ai'
        }))}
      />

      {/* Reset Success Modal */}
      {showResetSuccessModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <div className="flex items-center space-x-3 mb-4">
                <div className="flex-shrink-0 w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-900">Transformation Reset Successfully</h3>
              </div>
              
              <div className="mb-6 space-y-3">
                <p className="text-gray-700">
                  The transformation has been reset. Before starting again, please review your settings:
                </p>
                
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-2">
                  <div className="flex items-start space-x-2">
                    <svg className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div className="text-sm text-amber-800">
                      <p className="font-medium mb-1">Settings to Review:</p>
                      <ul className="list-disc list-inside space-y-1">
                        <li>Column Analysis (admin columns, exclude patterns)</li>
                        <li>Transform Settings (chunk size, row concurrency, row limit)</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="flex space-x-3">
                <button
                  onClick={() => {
                    setShowResetSuccessModal(false);
                    setShowColumnsModal(true);
                  }}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Review Columns
                </button>
                <button
                  onClick={() => {
                    setShowResetSuccessModal(false);
                    setShowSettingsModal(true);
                  }}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Review Settings
                </button>
                <button
                  onClick={() => setShowResetSuccessModal(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TwinTransformer;

