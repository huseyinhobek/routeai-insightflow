import { API_BASE_URL } from '../constants';
import { DatasetMeta, VariableDetail, SmartFilterResponse, QualityReport, DatasetListItem } from '../types';
import { getCsrfToken } from './authService';

/**
 * Fetch wrapper with credentials and CSRF token support
 */
async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers);
  
  // Add CSRF token for non-GET requests
  if (options.method && options.method !== 'GET') {
    const token = getCsrfToken();
    if (token) {
      headers.set('X-CSRF-Token', token);
    }
  }
  
  // Set content type if not set and body is JSON
  if (options.body && typeof options.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include', // Include cookies for session auth
  });
  
  // Handle 401 Unauthorized - redirect to login
  if (response.status === 401) {
    // Check if we're not already on the login page
    if (!window.location.hash.includes('/login') && !window.location.hash.includes('/verify')) {
      window.location.hash = '/login';
    }
  }
  
  return response;
}

class ApiService {
  async uploadDataset(file: File, codebookFile?: File): Promise<DatasetMeta> {
    const formData = new FormData();
    formData.append('file', file);
    
    // Add codebook file if provided
    if (codebookFile) {
      formData.append('codebook', codebookFile);
    }

    // For FormData, don't set Content-Type - browser will set it with boundary
    const headers: HeadersInit = {};
    const token = getCsrfToken();
    if (token) {
      headers['X-CSRF-Token'] = token;
    }

    const response = await fetch(`${API_BASE_URL}/datasets/upload`, {
      method: 'POST',
      body: formData,
      headers,
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Failed to upload dataset');
    }

    return response.json();
  }

  async listDatasets(): Promise<DatasetListItem[]> {
    const response = await apiFetch(`${API_BASE_URL}/datasets`);
    if (!response.ok) throw new Error('Failed to fetch datasets');
    return response.json();
  }

  async getDataset(id: string): Promise<DatasetMeta> {
    const response = await apiFetch(`${API_BASE_URL}/datasets/${id}`);
    if (!response.ok) throw new Error('Dataset not found');
    return response.json();
  }

  async deleteDataset(id: string): Promise<void> {
    const response = await apiFetch(`${API_BASE_URL}/datasets/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to delete dataset' }));
      throw new Error(errorData.detail || 'Failed to delete dataset');
    }
  }

  async getQualityReport(datasetId: string): Promise<QualityReport> {
    const response = await apiFetch(`${API_BASE_URL}/datasets/${datasetId}/quality`);
    if (!response.ok) throw new Error('Failed to fetch quality report');
    return response.json();
  }

  async getVariableDetail(datasetId: string, varName: string): Promise<VariableDetail> {
    const response = await apiFetch(`${API_BASE_URL}/datasets/${datasetId}/variables/${varName}`);
    if (!response.ok) throw new Error('Failed to fetch variable details');
    return response.json();
  }

  getDownloadUrl(datasetId: string, type: 'excel' | 'json' | 'report' | 'summary'): string {
    return `${API_BASE_URL}/datasets/${datasetId}/export/${type}`;
  }

  async downloadExport(datasetId: string, type: 'excel' | 'json' | 'report' | 'summary'): Promise<void> {
    const url = this.getDownloadUrl(datasetId, type);
    
    try {
      const response = await apiFetch(url);
      
      if (!response.ok) {
        throw new Error('Download failed');
      }
      
      // Get filename from Content-Disposition header or generate one
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `export_${type}.${type === 'json' ? 'json' : 'xlsx'}`;
      
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="(.+)"/);
        if (match) filename = match[1];
      }
      
      // Handle JSON response differently
      const contentType = response.headers.get('Content-Type');
      if (contentType?.includes('application/json')) {
        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        this.triggerDownload(blob, filename);
      } else {
        const blob = await response.blob();
        this.triggerDownload(blob, filename);
      }
    } catch (error) {
      console.error('Download error:', error);
      throw error;
    }
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

  async getConfig(): Promise<{ gemini_api_configured: boolean; database_url_configured: boolean }> {
    const response = await apiFetch(`${API_BASE_URL}/config`);
    if (!response.ok) throw new Error('Failed to fetch config');
    return response.json();
  }

  async generateSmartFilters(datasetId: string, maxFilters = 8): Promise<SmartFilterResponse> {
    const response = await apiFetch(`${API_BASE_URL}/smart-filters/generate`, {
      method: 'POST',
      body: JSON.stringify({ datasetId, maxFilters }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to generate smart filters' }));
      throw new Error(error.detail || 'Failed to generate smart filters');
    }

    return response.json();
  }

  async getSmartFilters(datasetId: string): Promise<SmartFilterResponse> {
    const response = await apiFetch(`${API_BASE_URL}/smart-filters/${datasetId}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to load smart filters' }));
      throw new Error(error.detail || 'Failed to load smart filters');
    }

    return response.json();
  }

  async saveSmartFilters(datasetId: string, filters: any[]): Promise<void> {
    const response = await apiFetch(`${API_BASE_URL}/smart-filters/${datasetId}`, {
      method: 'PUT',
      body: JSON.stringify({ filters }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to save smart filters' }));
      throw new Error(error.detail || 'Failed to save smart filters');
    }
  }

  async askQuestion(datasetId: string, question: string): Promise<{ answer: string }> {
    const response = await apiFetch(`${API_BASE_URL}/digital-insight/ask`, {
      method: 'POST',
      body: JSON.stringify({ datasetId, question }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to get answer' }));
      throw new Error(error.detail || 'Failed to get answer');
    }

    return response.json();
  }

  // Research Workflow APIs
  async createAudience(data: { dataset_id: string; name: string; description?: string; filter_json: any }): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/research/audiences`, {
      method: 'POST',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to create audience' }));
      throw new Error(error.detail || 'Failed to create audience');
    }

    return response.json();
  }

  async listAudiences(datasetId?: string): Promise<any[]> {
    const url = datasetId 
      ? `${API_BASE_URL}/research/audiences?dataset_id=${datasetId}`
      : `${API_BASE_URL}/research/audiences`;
    
    const response = await apiFetch(url);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to list audiences' }));
      throw new Error(error.detail || 'Failed to list audiences');
    }

    return response.json();
  }

  async getAudience(audienceId: string): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/research/audiences/${audienceId}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to get audience' }));
      throw new Error(error.detail || 'Failed to get audience');
    }

    return response.json();
  }

  async updateAudience(audienceId: string, data: { name?: string; description?: string; filter_json?: any }): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/research/audiences/${audienceId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to update audience' }));
      throw new Error(error.detail || 'Failed to update audience');
    }

    return response.json();
  }

  async deleteAudience(audienceId: string): Promise<void> {
    const response = await apiFetch(`${API_BASE_URL}/research/audiences/${audienceId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to delete audience' }));
      throw new Error(error.detail || 'Failed to delete audience');
    }
  }

  async refreshAudienceMembership(audienceId: string): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/research/audiences/${audienceId}/refresh-membership`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to refresh membership' }));
      throw new Error(error.detail || 'Failed to refresh membership');
    }

    return response.json();
  }

  async createThread(data: { dataset_id: string; audience_id?: string; title?: string }): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/research/threads`, {
      method: 'POST',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to create thread' }));
      throw new Error(error.detail || 'Failed to create thread');
    }

    return response.json();
  }

  async listThreads(datasetId?: string, audienceId?: string): Promise<any[]> {
    const params = new URLSearchParams();
    if (datasetId) params.append('dataset_id', datasetId);
    if (audienceId) params.append('audience_id', audienceId);
    
    const url = `${API_BASE_URL}/research/threads${params.toString() ? '?' + params.toString() : ''}`;
    const response = await apiFetch(url);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to list threads' }));
      throw new Error(error.detail || 'Failed to list threads');
    }

    return response.json();
  }

  async getThread(threadId: string): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/research/threads/${threadId}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to get thread' }));
      throw new Error(error.detail || 'Failed to get thread');
    }

    return response.json();
  }

  async addThreadQuestion(threadId: string, questionText: string): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/research/threads/${threadId}/questions`, {
      method: 'POST',
      body: JSON.stringify({ question_text: questionText }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to add question' }));
      throw new Error(error.detail || 'Failed to add question');
    }

    return response.json();
  }

  async getSuggestedQuestions(datasetId: string, audienceId?: string): Promise<any> {
    const url = audienceId
      ? `${API_BASE_URL}/research/suggested-questions?dataset_id=${datasetId}&audience_id=${audienceId}`
      : `${API_BASE_URL}/research/suggested-questions?dataset_id=${datasetId}`;
    
    const response = await apiFetch(url);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to get suggested questions' }));
      throw new Error(error.detail || 'Failed to get suggested questions');
    }

    return response.json();
  }

  async populateDatasetData(datasetId: string): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/research/datasets/${datasetId}/populate-data`, {
      method: 'POST',
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to populate dataset data' }));
      throw new Error(error.detail || 'Failed to populate dataset data');
    }

    return response.json();
  }

  async getEmbeddingStatus(datasetId: string, autoResume: boolean = true): Promise<any> {
    const url = `${API_BASE_URL}/research/datasets/${datasetId}/embedding-status${autoResume ? '?auto_resume=true' : ''}`;
    const response = await apiFetch(url, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error(`Failed to get embedding status: ${response.statusText}`);
    }

    return response.json();
  }

  async generateEmbeddings(datasetId: string): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/research/datasets/${datasetId}/generate-embeddings`, {
      method: 'POST',
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to generate embeddings' }));
      throw new Error(error.detail || 'Failed to generate embeddings');
    }

    return response.json();
  }
}

export const apiService = new ApiService();
export default apiService;
