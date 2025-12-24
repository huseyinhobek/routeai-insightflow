import { API_BASE_URL } from '../constants';
import { getCsrfToken } from './authService';

export interface UserListItem {
  id: string;
  email: string;
  name: string | null;
  role: string;
  status: string;
  created_at: string;
  last_login_at: string | null;
}

export interface AuditLogItem {
  id: number;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  user_email: string | null;
  ip_address: string | null;
  meta_json: Record<string, any> | null;
  created_at: string;
}

export interface AuditLogsResponse {
  total: number;
  offset: number;
  limit: number;
  logs: AuditLogItem[];
}

export interface OrganizationInfo {
  id: string;
  name: string;
  slug: string;
  settings: Record<string, any>;
  created_at: string;
}

// Fetch wrapper with credentials and CSRF
async function adminFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers);
  
  if (options.method && options.method !== 'GET') {
    const token = getCsrfToken();
    if (token) {
      headers.set('X-CSRF-Token', token);
    }
  }
  
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  
  return fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  });
}

class AdminService {
  // User Management
  async listUsers(): Promise<UserListItem[]> {
    const response = await adminFetch(`${API_BASE_URL}/admin/users`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to fetch users' }));
      throw new Error(error.detail);
    }
    return response.json();
  }

  async inviteUser(email: string, name?: string, role: string = 'viewer'): Promise<{ user_id: string; magic_link?: string }> {
    const response = await adminFetch(`${API_BASE_URL}/admin/users/invite`, {
      method: 'POST',
      body: JSON.stringify({ email, name, role }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to invite user' }));
      throw new Error(error.detail);
    }
    return response.json();
  }

  async updateUser(userId: string, updates: { name?: string; role?: string; status?: string }): Promise<void> {
    const response = await adminFetch(`${API_BASE_URL}/admin/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to update user' }));
      throw new Error(error.detail);
    }
  }

  async deleteUser(userId: string): Promise<void> {
    const response = await adminFetch(`${API_BASE_URL}/admin/users/${userId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to delete user' }));
      throw new Error(error.detail);
    }
  }

  // Organization Management
  async getOrganization(): Promise<OrganizationInfo | null> {
    const response = await adminFetch(`${API_BASE_URL}/admin/org`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to fetch organization' }));
      throw new Error(error.detail);
    }
    const data = await response.json();
    return data.organization;
  }

  async updateOrganizationSettings(settings: Record<string, any>): Promise<void> {
    const response = await adminFetch(`${API_BASE_URL}/admin/org/settings`, {
      method: 'PUT',
      body: JSON.stringify({ settings }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to update settings' }));
      throw new Error(error.detail);
    }
  }

  // Audit Logs
  async getAuditLogs(params: {
    offset?: number;
    limit?: number;
    action?: string;
    entity_type?: string;
    user_id?: string;
  } = {}): Promise<AuditLogsResponse> {
    const searchParams = new URLSearchParams();
    if (params.offset !== undefined) searchParams.set('offset', String(params.offset));
    if (params.limit !== undefined) searchParams.set('limit', String(params.limit));
    if (params.action) searchParams.set('action', params.action);
    if (params.entity_type) searchParams.set('entity_type', params.entity_type);
    if (params.user_id) searchParams.set('user_id', params.user_id);

    const response = await adminFetch(`${API_BASE_URL}/admin/audit-logs?${searchParams}`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to fetch audit logs' }));
      throw new Error(error.detail);
    }
    return response.json();
  }

  async getAuditLogActions(): Promise<string[]> {
    const response = await adminFetch(`${API_BASE_URL}/admin/audit-logs/actions`);
    if (!response.ok) {
      return [];
    }
    const data = await response.json();
    return data.actions || [];
  }
}

export const adminService = new AdminService();

