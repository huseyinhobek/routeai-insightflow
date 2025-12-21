import { API_BASE_URL } from '../constants';
import { DatasetMeta, VariableDetail, SmartFilterResponse, QualityReport, DatasetListItem } from '../types';

class ApiService {
  async uploadDataset(file: File): Promise<DatasetMeta> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/datasets/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Failed to upload dataset');
    }

    return response.json();
  }

  async listDatasets(): Promise<DatasetListItem[]> {
    const response = await fetch(`${API_BASE_URL}/datasets`);
    if (!response.ok) throw new Error('Failed to fetch datasets');
    return response.json();
  }

  async getDataset(id: string): Promise<DatasetMeta> {
    const response = await fetch(`${API_BASE_URL}/datasets/${id}`);
    if (!response.ok) throw new Error('Dataset not found');
    return response.json();
  }

  async deleteDataset(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/datasets/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete dataset');
  }

  async getQualityReport(datasetId: string): Promise<QualityReport> {
    const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}/quality`);
    if (!response.ok) throw new Error('Failed to fetch quality report');
    return response.json();
  }

  async getVariableDetail(datasetId: string, varName: string): Promise<VariableDetail> {
    const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}/variables/${varName}`);
    if (!response.ok) throw new Error('Failed to fetch variable details');
    return response.json();
  }

  getDownloadUrl(datasetId: string, type: 'excel' | 'json' | 'report' | 'summary'): string {
    return `${API_BASE_URL}/datasets/${datasetId}/export/${type}`;
  }

  async downloadExport(datasetId: string, type: 'excel' | 'json' | 'report' | 'summary'): Promise<void> {
    const url = this.getDownloadUrl(datasetId, type);
    
    try {
      const response = await fetch(url);
      
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
    const response = await fetch(`${API_BASE_URL}/config`);
    if (!response.ok) throw new Error('Failed to fetch config');
    return response.json();
  }

  async generateSmartFilters(datasetId: string, maxFilters = 8): Promise<SmartFilterResponse> {
    const response = await fetch(`${API_BASE_URL}/smart-filters/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ datasetId, maxFilters }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to generate smart filters' }));
      throw new Error(error.detail || 'Failed to generate smart filters');
    }

    return response.json();
  }
}

export const apiService = new ApiService();
