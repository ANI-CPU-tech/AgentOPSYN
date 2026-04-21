
// utils/api.ts
const BASE_URL = 'http://localhost:8000/api';

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  // Handle automatic logout if token is expired/invalid
  if (response.status === 401 && typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
  }

  return response;
}
