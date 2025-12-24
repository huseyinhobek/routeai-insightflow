import { API_BASE_URL } from '../constants';

export interface AuthUser {
  id: string;
  email: string;
  name: string | null;
  org_id: string | null;
  org_name: string | null;
  role: string;
  permissions: string[];
  status: string;
  must_change_password?: boolean;
}

export interface LoginResponse {
  message: string;
  email: string;
  requires_otp: boolean;
  otp_code?: string; // Only in dev mode
  // For direct login (demo accounts skip OTP)
  user?: AuthUser;
  access_token?: string;
}

export interface VerifyResponse {
  message: string;
  user: AuthUser;
  access_token?: string; // Only in dev mode
}

export interface AuthCheckResponse {
  authenticated: boolean;
  user: {
    id: string;
    email: string;
    name: string | null;
    role: string;
  } | null;
}

// CSRF token management
let csrfToken: string | null = null;

export function getCsrfToken(): string | null {
  if (!csrfToken) {
    // Try to get from cookie
    const match = document.cookie.match(/csrf_token=([^;]+)/);
    csrfToken = match ? match[1] : null;
  }
  return csrfToken;
}

export function setCsrfToken(token: string): void {
  csrfToken = token;
}

// Fetch wrapper with credentials and CSRF
async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers);
  
  // Add CSRF token for non-GET requests
  if (options.method && options.method !== 'GET') {
    const token = getCsrfToken();
    if (token) {
      headers.set('X-CSRF-Token', token);
    }
  }
  
  // Set content type if not set and body exists
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  
  return fetch(url, {
    ...options,
    headers,
    credentials: 'include', // Include cookies
  });
}

class AuthService {
  /**
   * Login with email and password, then receive OTP
   */
  async loginWithPassword(email: string, password: string): Promise<LoginResponse> {
    const response = await authFetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail || 'Login failed');
    }

    const result = await response.json();
    
    // If direct login (demo accounts), update CSRF token
    if (!result.requires_otp && result.user) {
      const match = document.cookie.match(/csrf_token=([^;]+)/);
      if (match) {
        setCsrfToken(match[1]);
      }
    }

    return result;
  }

  /**
   * Verify OTP code and create session
   */
  async verifyOTP(email: string, code: string): Promise<VerifyResponse> {
    const response = await authFetch(`${API_BASE_URL}/auth/verify`, {
      method: 'POST',
      body: JSON.stringify({ email, code }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Verification failed' }));
      throw new Error(error.detail || 'Verification failed');
    }

    const result = await response.json();
    
    // Update CSRF token from cookie after login
    const match = document.cookie.match(/csrf_token=([^;]+)/);
    if (match) {
      setCsrfToken(match[1]);
    }

    return result;
  }

  // Legacy methods for backward compatibility
  async requestOTP(email: string): Promise<LoginResponse> {
    // This now requires password, kept for compatibility
    return this.loginWithPassword(email, '');
  }

  async requestMagicLink(email: string): Promise<LoginResponse> {
    return this.requestOTP(email);
  }

  async verifyMagicLink(email: string, token: string): Promise<VerifyResponse> {
    return this.verifyOTP(email, token);
  }

  /**
   * Get current authenticated user
   */
  async getCurrentUser(): Promise<AuthUser | null> {
    try {
      const response = await authFetch(`${API_BASE_URL}/auth/me`);
      
      if (response.status === 401) {
        return null;
      }
      
      if (!response.ok) {
        throw new Error('Failed to get user');
      }
      
      return response.json();
    } catch (error) {
      console.error('getCurrentUser error:', error);
      return null;
    }
  }

  /**
   * Check if user is authenticated
   */
  async checkAuth(): Promise<AuthCheckResponse> {
    try {
      const response = await authFetch(`${API_BASE_URL}/auth/check`);
      
      if (!response.ok) {
        return { authenticated: false, user: null };
      }
      
      return response.json();
    } catch (error) {
      return { authenticated: false, user: null };
    }
  }

  /**
   * Logout and clear session
   */
  async logout(): Promise<void> {
    try {
      await authFetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear CSRF token
      csrfToken = null;
    }
  }

  /**
   * Refresh access token
   */
  async refreshToken(): Promise<void> {
    const response = await authFetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to refresh token');
    }

    // Update CSRF token from cookie
    const match = document.cookie.match(/csrf_token=([^;]+)/);
    if (match) {
      setCsrfToken(match[1]);
    }
  }

  /**
   * Change password for current user
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const response = await authFetch(`${API_BASE_URL}/auth/change-password`, {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to change password' }));
      throw new Error(error.detail || 'Failed to change password');
    }
  }
}

export const authService = new AuthService();

