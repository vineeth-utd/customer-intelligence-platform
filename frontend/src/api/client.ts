const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

async function fetchClient<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      // Ignore if not json
    }
    throw new ApiError(
      response.status,
      errorData?.detail || `API Request failed with status ${response.status}`,
      errorData
    );
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(endpoint: string, params?: Record<string, unknown>, options?: RequestInit) => {
    let query = '';
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
      const queryString = searchParams.toString();
      if (queryString) {
        query = `?${queryString}`;
      }
    }
    return fetchClient<T>(`${endpoint}${query}`, { ...options, method: 'GET' });
  },
  post: <T>(endpoint: string, data?: unknown, options?: RequestInit) => {
    return fetchClient<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  },
  put: <T>(endpoint: string, data?: unknown, options?: RequestInit) => {
    return fetchClient<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  },
  delete: <T>(endpoint: string, options?: RequestInit) => {
    return fetchClient<T>(endpoint, { ...options, method: 'DELETE' });
  },
};
