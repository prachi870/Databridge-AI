/**
 * API client for backend communication.
 */
import type { RouteResponse, Config, Database, Question, Pareto, Summary, LayerData, Calibration, AblationRow } from '../types';

export const API_BASE_URL = import.meta.env.VITE_API_URL || '';
export const ACCESS_TOKEN_KEY = 'sql-router-access-token';

export async function authenticatedFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  const headers = new Headers(init?.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (response.status === 401 && token) {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.location.assign('/login');
  }
  return response;
}

export interface EvaluationSummary {
  sample_count: number;
  local_accuracy: number;
  api_accuracy: number;
  routed_accuracy: number;
  api_route_percent: number;
  estimated_cost_savings_percent: number;
  user_feedback_count: number;
  user_feedback_accuracy: number;
}

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const data = await response.json();
      const detail = data.detail;
      if (Array.isArray(detail)) {
        message = detail.map((e: any) => e.msg).join('. ');
      } else if (typeof detail === 'string') {
        message = detail;
      }
    } catch {
      // Keep status text
    }
    throw new Error(message);
  }

  return response.json();
}

export const api = {
  config: () => fetchJSON<Config>('/api/config'),

  getEvaluation: () => fetchJSON<EvaluationSummary>('/api/evaluation'),
  
  getDatabases: () => fetchJSON<Database[]>('/api/databases'),
  
  getQuestions: (db_id?: string) => {
    const query = db_id ? `?db_id=${db_id}` : '';
    return fetchJSON<Question[]>(`/api/benchmark/questions${query}`);
  },
  
  query: (body: {
    db_id: string;
    question: string;
  }) =>
    fetchJSON<RouteResponse>('/api/route', {
      method: 'POST',
      body: JSON.stringify({ ...body, mode: 'auto' }),
    }),
  
  getSummary: () => fetchJSON<Summary>('/api/metrics/summary'),
  
  getPareto: () => fetchJSON<Pareto>('/api/metrics/pareto'),
  
  getAuroc: () => fetchJSON<{ auroc: number; points: Array<{fpr: number; tpr: number}> }>('/api/metrics/auroc'),
  
  getCalibration: () => fetchJSON<Calibration>('/api/metrics/calibration'),
  
  getLayers: () => fetchJSON<LayerData[]>('/api/metrics/layers'),
  
  getAblation: () => fetchJSON<AblationRow[]>('/api/metrics/ablation'),
};
