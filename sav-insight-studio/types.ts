export enum VariableType {
  SINGLE_CHOICE = 'single_choice',
  MULTI_CHOICE = 'multi_choice',
  NUMERIC = 'numeric',
  TEXT = 'text',
  DATE = 'date',
  SCALE = 'scale',
  UNKNOWN = 'unknown'
}

export enum MeasureType {
  NOMINAL = 'nominal',
  ORDINAL = 'ordinal',
  SCALE = 'scale',
  UNKNOWN = 'unknown'
}

export interface ValueLabel {
  value: number | string;
  label: string;
}

export interface MissingValues {
  systemMissing: boolean;
  userMissingValues: (number | string)[];
}

export interface VariableSummary {
  code: string;
  label: string;
  type: VariableType;
  measure: MeasureType;
  valueLabels: ValueLabel[];
  missingValues: MissingValues | null;
  cardinality: number;
  responseCount: number;
  responseRate: number;
  detectedMultiSetId?: string;
}

export interface DatasetMeta {
  id: string;
  filename: string;
  nRows: number;
  nCols: number;
  createdAt: string;
  variables: VariableSummary[];
  qualityReport?: QualityReport;
  digitalTwinReadiness?: 'green' | 'yellow' | 'red';
}

export interface DatasetListItem {
  id: string;
  filename: string;
  nRows: number;
  nCols: number;
  createdAt: string;
  dataQualityScore: number | null;
  digitalTwinReadiness: 'green' | 'yellow' | 'red' | null;
  overallCompletionRate: number | null;
}

// ==================== Dataset Rows (for preview/table) ====================

export interface DatasetRow {
  index: number;
  data: Record<string, any>;
  labeled?: Record<string, any>;
}

export interface DatasetRowsResponse {
  total: number;
  offset: number;
  limit: number;
  rows: DatasetRow[];
}

export interface QualityMetric {
  name: string;
  score: number;
  status: 'green' | 'yellow' | 'red';
}

export interface VariableQuality {
  code: string;
  label: string;
  completeness: number;
  status: 'green' | 'yellow' | 'red';
  issues: string[];
}

export interface QualityReport {
  overall_score: number;
  completeness_score: number;
  validity_score: number;
  consistency_score: number;
  digital_twin_readiness: 'green' | 'yellow' | 'red';
  
  total_participants: number;
  complete_responses: number;
  partial_responses: number;
  dropout_rate: number;
  
  total_variables: number;
  high_quality_vars: number;
  medium_quality_vars: number;
  low_quality_vars: number;
  
  metrics: QualityMetric[];
  variable_quality: VariableQuality[];
  
  critical_issues: string[];
  warnings: string[];
  recommendations: string[];
  
  transformation_score: number;
  transformation_issues: string[];
}

export interface FrequencyItem {
  value: string | number | null;
  label: string;
  count: number;
  percent?: number; // Legacy field, kept for backwards compatibility
  percentOfTotal: number;
  percentOfValid: number;
}

export interface VariableDetail extends VariableSummary {
  totalN: number;
  validN: number;
  missingN: number;
  missingPercentOfTotal: number;
  frequencies: FrequencyItem[]; // For categorical
  hasManyCategories: boolean;
  categoryCount: number;
  stats?: { // For numeric
    min: number;
    max: number;
    mean: number;
    median: number;
    std: number;
  };
}

// Smart Filters Types
export enum FilterType {
  CATEGORICAL = 'categorical',
  ORDINAL = 'ordinal',
  NUMERIC_RANGE = 'numeric_range',
  MULTI_SELECT = 'multi_select',
  DATE_RANGE = 'date_range'
}

export enum FilterControl {
  CHECKBOX_GROUP = 'checkbox_group',
  SELECT = 'select',
  RANGE_SLIDER = 'range_slider',
  DATE_PICKER = 'date_picker'
}

export interface FilterOption {
  key: string | number;
  label: string;
  count?: number;
  percent?: number;
}

export interface SmartFilter {
  id: string;
  title: string;
  description: string;
  sourceVars: string[];
  filterType: FilterType;
  ui: {
    control: FilterControl;
  };
  options: FilterOption[];
  recommendedDefault?: any;
  suitabilityScore: number;
  rationale: string;
}

export interface SmartFilterResponse {
  filters: SmartFilter[];
}

// ==================== Twin Transformer Types ====================

export type TransformJobStatus = 'idle' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';

export interface AdminColumn {
  code: string;
  label: string;
  type: string;
  reason: string;
}

export interface ExcludeCandidate {
  patternKey: string;
  label: string;
  detectedValues: { value: any; label: string }[];
  affectedVariables: string[];
  defaultExclude: boolean;
}

export interface TransformableColumn {
  code: string;
  label: string;
  type: string;
  responseRate: number;
  valueLabels: ValueLabel[];
}

export interface ColumnAnalysisResult {
  datasetId: string;
  adminColumns: AdminColumn[];
  excludeCandidates: ExcludeCandidate[];
  excludedByDefaultColumns?: AdminColumn[]; // same shape: {code,label,type,reason}
  transformableColumns: TransformableColumn[];
  totalColumns: number;
  totalRows: number;
  suggestedIdColumn?: string; // Auto-detected ID column
}

export interface TransformJobStats {
  totalColumns: number;
  processedColumns: number;
  emptySkipped: number;
  excludedSkipped: number;
  errors: number;
  retries: number;
}

export interface TransformJob {
  jobId: string;
  status: TransformJobStatus;
  totalRows: number; // Total rows in dataset
  rowLimit?: number | null; // Max rows to process (null = all rows)
  processedRows: number;
  failedRows: number;
  currentRowIndex: number;
  percentComplete: number;
  stats: TransformJobStats;
  lastError: string | null;
  startedAt: string | null;
  updatedAt: string;
  rowConcurrency?: number; // Number of rows processed in parallel
  chunkSize?: number; // Number of columns per chunk
  excludeOptionsConfig?: Record<string, any>; // Saved exclude settings
  adminColumns?: string[]; // Saved admin columns
  columnAnalysis?: ColumnAnalysisResult | null; // Cached column analysis
  respondentIdColumn?: string | null; // Respondent ID column
}

export interface TransformSentence {
  sentence: string;
  sources: string[];
  warnings?: string[];
}

export interface TransformExcluded {
  emptyVars: string[];
  excludedByOption: string[];
  adminVars: string[];
  excludedVariables?: string[];
}

export interface TransformResult {
  rowIndex: number;
  respondentId: string | null;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  sentences: TransformSentence[];
  excluded: TransformExcluded;
  rawTrace?: any;
  errorMessage: string | null;
  retryCount: number;
  processedAt: string | null;
}

export interface TransformResultsResponse {
  jobId: string;
  total: number;
  offset: number;
  limit: number;
  results: TransformResult[];
}

export interface TransformResultsRangeResponse {
  jobId: string;
  startRow: number;
  limit: number;
  results: TransformResult[];
}

export interface StartTransformRequest {
  datasetId: string;
  chunkSize?: number;
  rowConcurrency?: number;
  excludeOptionsConfig?: Record<string, boolean>;
  excludePatternVariables?: Record<string, string[]>;
  adminColumns?: string[];
  excludedVariables?: string[];
  respondentIdColumn?: string; // Which column to use as respondentId in results (optional)
  rowLimit?: number; // undefined = tüm satırlar
  autoStart?: boolean; // Whether to auto-start the job (default: true)
}

export interface StartTransformResponse {
  jobId: string;
  status: string;
  message: string;
  isExisting: boolean;
}