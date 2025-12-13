// In production, this would be an environment variable. 
// For local dev with docker-compose, this usually points to localhost:8000
// For Docker, use: http://backend:8000/api (internal) or http://localhost:8000/api (external)
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const COLORS = {
  primary: '#2563EB', // blue-600
  secondary: '#4F46E5', // indigo-600
  accent: '#0D9488', // teal-600
  danger: '#DC2626', // red-600
  warning: '#D97706', // amber-600
  success: '#16A34A', // green-600
  background: '#F9FAFB', // gray-50
  surface: '#FFFFFF',
};

export const CHART_COLORS = [
  '#2563EB', '#7C3AED', '#DB2777', '#DC2626', '#EA580C', 
  '#D97706', '#65A30D', '#16A34A', '#059669', '#0891B2'
];