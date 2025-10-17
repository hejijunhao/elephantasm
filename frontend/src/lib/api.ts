/**
 * API Client for Elephantasm Backend
 *
 * This module provides a centralized API client for communicating with the FastAPI backend.
 * It handles request configuration, error handling, and provides type-safe methods for
 * interacting with the LTAM (Long-Term Agentic Memory) system.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_V1 = process.env.NEXT_PUBLIC_API_V1 || '/api/v1';

export const API_ENDPOINTS = {
  health: `${API_V1}/health`,
  events: `${API_V1}/events`,
  memories: `${API_V1}/memories`,
  lessons: `${API_V1}/lessons`,
  knowledge: `${API_V1}/knowledge`,
  identity: `${API_V1}/identity`,
  packs: `${API_V1}/packs`,
  dreamer: `${API_V1}/dreamer`,
} as const;

/**
 * Base API client with common configuration
 */
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const config: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `API Error: ${response.status} ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error('API Request Error:', error);
      throw error;
    }
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async put<T>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  /**
   * Health check endpoint
   */
  async checkHealth() {
    return this.get<{ status: string; timestamp: string }>(
      API_ENDPOINTS.health
    );
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export convenience functions
export const checkBackendHealth = () => apiClient.checkHealth();
