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
  value: string | number;
  label: string;
  count: number;
  percent: number;
}

export interface VariableDetail extends VariableSummary {
  frequencies: FrequencyItem[]; // For categorical
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