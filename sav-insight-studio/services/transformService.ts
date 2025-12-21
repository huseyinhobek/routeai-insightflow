import { API_BASE_URL } from '../constants';
import {
  ColumnAnalysisResult,
  DatasetRowsResponse,
  TransformJob,
  TransformResult,
  TransformResultsRangeResponse,
  TransformResultsResponse,
  StartTransformRequest,
  StartTransformResponse,
} from '../types';

class TransformService {
  /**
   * Get dataset rows with pagination (for preview/table)
   */
  async getDatasetRows(datasetId: string, offset = 0, limit = 100): Promise<DatasetRowsResponse> {
    const response = await fetch(
      `${API_BASE_URL}/datasets/${datasetId}/rows?offset=${offset}&limit=${limit}`
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to get rows' }));
      throw new Error(error.detail || 'Failed to get dataset rows');
    }

    return response.json();
  }

  /**
   * Analyze columns for transformation
   * Detects admin columns and exclude candidates
   */
  async analyzeColumns(datasetId: string): Promise<ColumnAnalysisResult> {
    const response = await fetch(`${API_BASE_URL}/transform/analyze-columns`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ datasetId }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Analysis failed' }));
      throw new Error(error.detail || 'Failed to analyze columns');
    }

    return response.json();
  }

  /**
   * Start a new transformation job
   */
  async startJob(request: StartTransformRequest): Promise<StartTransformResponse> {
    const response = await fetch(`${API_BASE_URL}/transform/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to start job' }));
      const err = new Error(error.detail || 'Failed to start transformation job') as Error & { status?: number };
      err.status = response.status;
      throw err;
    }

    return response.json();
  }

  /**
   * Pause a running job
   */
  async pauseJob(jobId: string): Promise<{ jobId: string; status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/transform/pause/${jobId}`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to pause' }));
      throw new Error(error.detail || 'Failed to pause job');
    }

    return response.json();
  }

  /**
   * Resume a paused job
   */
  async resumeJob(jobId: string): Promise<{ jobId: string; status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/transform/resume/${jobId}`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to resume' }));
      throw new Error(error.detail || 'Failed to resume job');
    }

    return response.json();
  }

  /**
   * Stop a running job
   */
  async stopJob(jobId: string): Promise<{ jobId: string; status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/transform/stop/${jobId}`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to stop' }));
      throw new Error(error.detail || 'Failed to stop job');
    }

    return response.json();
  }

  /**
   * Reset a job - requires confirmation text 'DELETE'
   */
  async resetJob(jobId: string, confirmText: string): Promise<{ jobId: string; status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/transform/reset/${jobId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmText }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to reset' }));
      throw new Error(error.detail || 'Failed to reset job');
    }

    return response.json();
  }

  /**
   * Get job status and progress
   */
  async getJobStatus(jobId: string): Promise<TransformJob> {
    const response = await fetch(`${API_BASE_URL}/transform/status/${jobId}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to get status' }));
      throw new Error(error.detail || 'Failed to get job status');
    }

    const data = await response.json();
    
    // Map snake_case to camelCase
    return {
      jobId: data.job_id,
      status: data.status,
      totalRows: data.total_rows,
      rowLimit: data.row_limit,
      processedRows: data.processed_rows,
      failedRows: data.failed_rows,
      currentRowIndex: data.current_row_index,
      percentComplete: data.percent_complete,
      stats: data.stats || {},
      lastError: data.last_error,
      startedAt: data.started_at,
      updatedAt: data.updated_at,
      rowConcurrency: data.row_concurrency,
      chunkSize: data.chunk_size,
      excludeOptionsConfig: data.exclude_options_config,
      adminColumns: data.admin_columns,
      columnAnalysis: data.column_analysis,
      respondentIdColumn: data.respondent_id_column,
    };
  }

  /**
   * Get all jobs for a dataset
   */
  async getJobsForDataset(datasetId: string): Promise<{
    jobId: string;
    status: string;
    totalRows: number;
    processedRows: number;
    failedRows: number;
    createdAt: string | null;
    updatedAt: string | null;
  }[]> {
    const response = await fetch(`${API_BASE_URL}/transform/jobs/${datasetId}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to get jobs' }));
      throw new Error(error.detail || 'Failed to get jobs');
    }

    return response.json();
  }

  /**
   * Get transformation results with pagination
   */
  async getResults(jobId: string, offset = 0, limit = 50): Promise<TransformResultsResponse> {
    const response = await fetch(
      `${API_BASE_URL}/transform/results/${jobId}?offset=${offset}&limit=${limit}`
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to get results' }));
      throw new Error(error.detail || 'Failed to get results');
    }

    return response.json();
  }

  /**
   * Get transform results for a row-index range [startRow, startRow+limit)
   * (used by the row table to update displayed rows)
   */
  async getResultsRange(jobId: string, startRow = 0, limit = 50): Promise<TransformResultsRangeResponse> {
    const response = await fetch(
      `${API_BASE_URL}/transform/results-range/${jobId}?startRow=${startRow}&limit=${limit}`
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to get results range' }));
      throw new Error(error.detail || 'Failed to get results range');
    }

    return response.json();
  }

  /**
   * Get a single result by row index
   */
  async getResultByRow(jobId: string, rowIndex: number): Promise<TransformResult> {
    const response = await fetch(`${API_BASE_URL}/transform/result/${jobId}/${rowIndex}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to get result' }));
      throw new Error(error.detail || 'Failed to get result');
    }

    return response.json();
  }

  /**
   * Export results as JSON
   */
  async exportResultsJson(jobId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/transform/export/${jobId}?format=json`);

    if (!response.ok) {
      throw new Error('Failed to export results');
    }

    const data = await response.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    this.triggerDownload(blob, `twin_transform_${jobId}.json`);
  }

  /**
   * Retry transformation for a single row
   */
  async retryRow(jobId: string, rowIndex: number): Promise<{ jobId: string; rowIndex: number; status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/transform/retry-row/${jobId}/${rowIndex}`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to retry row' }));
      throw new Error(error.detail || 'Failed to retry row');
    }

    return response.json();
  }

  /**
   * Export results as CSV
   */
  async exportResultsCsv(
    jobId: string,
    productId: string,
    productName: string,
    dataSource: string,
    reviewRating: number,
    reviewTitle?: string,
    smartFilters?: Array<{ id: string; title: string; sourceVars: string[]; source?: 'ai' | 'manual' }>
  ): Promise<void> {
    // Build query params
    const params = new URLSearchParams({
      format: 'csv',
      product_id: productId,
      product_name: productName,
      data_source: dataSource,
      review_rating: String(reviewRating),
    });
    
    if (reviewTitle) {
      params.append('review_title', reviewTitle);
    }

    // Send smart filters as JSON in request body
    const response = await fetch(`${API_BASE_URL}/transform/export/${jobId}?${params.toString()}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        smart_filters: smartFilters?.map(f => ({
          id: f.id,
          title: f.title,
          source_vars: f.sourceVars,
          source: f.source || 'manual'
        })) || []
      })
    });

    if (!response.ok) {
      throw new Error('Failed to export results');
    }

    const blob = await response.blob();
    const filename = productName ? `${productName.replace(/\s+/g, '_')}_${jobId.substring(0, 8)}.csv` : `twin_transform_${jobId}.csv`;
    this.triggerDownload(blob, filename);
  }

  /**
   * Poll job status at intervals
   */
  pollJobStatus(
    jobId: string,
    onUpdate: (job: TransformJob) => void,
    onError: (error: Error) => void,
    intervalMs = 2000
  ): () => void {
    let isRunning = true;

    const poll = async () => {
      while (isRunning) {
        try {
          const status = await this.getJobStatus(jobId);
          onUpdate(status);

          // Stop polling if job is complete or failed
          // Also stop on 'paused' to avoid unnecessary network spam; UI will re-start polling on resume.
          if (status.status === 'completed' || status.status === 'failed' || status.status === 'paused') {
            isRunning = false;
            break;
          }
        } catch (error) {
          onError(error instanceof Error ? error : new Error(String(error)));
        }

        // Wait before next poll
        await new Promise((resolve) => setTimeout(resolve, intervalMs));
      }
    };

    poll();

    // Return cleanup function
    return () => {
      isRunning = false;
    };
  }

  private triggerDownload(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }
}

export const transformService = new TransformService();

